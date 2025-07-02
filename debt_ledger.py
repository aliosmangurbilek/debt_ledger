"""
Ana Veresiye Defteri Uygulaması - Veritabanı Destekli
"""

import sys
import json
from datetime import datetime
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QListWidget, QPushButton, QLabel, QStackedWidget,
                             QMessageBox, QInputDialog, QTableWidget, QTableWidgetItem,
                             QHeaderView, QDialog, QFormLayout, QLineEdit, QComboBox,
                             QDateEdit, QTextEdit, QDialogButtonBox, QApplication,
                             QProgressDialog, QSpinBox, QGroupBox)
from PyQt6.QtCore import Qt, QDate, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QAction
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping
import os
from database_manager import DatabaseManager

class DebtRecord:
    """Borç kaydı sınıfı - artık veritabanından gelecek"""
    def __init__(self, record_id, date, description, debt_amount=0, payment_amount=0, payment_status="Ödenmedi", remaining_debt=0):
        self.id = record_id
        self.date = date
        self.description = description
        self.debt_amount = float(debt_amount) if debt_amount else 0.0
        self.payment_amount = float(payment_amount) if payment_amount else 0.0
        self.payment_status = payment_status
        self.remaining_debt = float(remaining_debt) if remaining_debt else 0.0

class Creditor:
    """Borçlu sınıfı - artık veritabanından gelecek"""
    def __init__(self, creditor_id, name, db_manager):
        self.id = creditor_id
        self.name = name
        self.db_manager = db_manager
        self._records = None

    @property
    def records(self):
        """Kayıtları lazy loading ile yükle"""
        if self._records is None:
            self._records = self.load_records()
        return self._records

    def load_records(self):
        """Veritabanından kayıtları yükle"""
        records_data = self.db_manager.get_creditor_records(self.id)
        return [DebtRecord(
            record_id=r['id'],
            date=r['date'],
            description=r['description'],
            debt_amount=r['debt_amount'],
            payment_amount=r['payment_amount'],
            payment_status=r['payment_status'],
            remaining_debt=r['remaining_debt']
        ) for r in records_data]

    def refresh_records(self):
        """Kayıtları yeniden yükle"""
        self._records = None

    def add_record(self, record_data):
        """Yeni kayıt ekle"""
        record_id = self.db_manager.add_record(
            creditor_id=self.id,
            date=record_data.date,
            description=record_data.description,
            debt_amount=record_data.debt_amount,
            payment_amount=record_data.payment_amount,
            payment_status=record_data.payment_status
        )

        if record_id:
            self.refresh_records()
            return True
        return False

    def get_total_debt(self):
        """Toplam borcu hesapla"""
        records = self.records
        if not records:
            return 0.0
        return records[-1].remaining_debt

    def get_last_payment_status(self):
        """Son ödeme durumunu getir"""
        records = self.records
        if not records:
            return "Kayıt yok"

        # Son ödeme kaydını bul
        for record in reversed(records):
            if record.payment_amount > 0:
                return record.payment_status
        return "Ödeme yok"

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'records': [record.to_dict() for record in self.records]
        }

    @classmethod
    def from_dict(cls, data, db_manager):
        creditor = cls(data['id'], data['name'], db_manager)
        for record_data in data['records']:
            record = DebtRecord.from_dict(record_data)
            creditor.records.append(record)
        creditor.refresh_records()
        return creditor

class AddRecordDialog(QDialog):
    """Yeni borç veya ödeme kaydı ekleme dialog'u"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Yeni Kayıt Ekle")
        self.setModal(True)
        self.resize(450, 300)  # Dialog boyutu büyütüldü

        layout = QFormLayout()

        # Dialog fontunu büyüt
        dialog_font = QFont("Arial", 12)
        self.setFont(dialog_font)

        # Date input
        self.date_edit = QDateEdit()
        self.date_edit.setFont(dialog_font)
        self.date_edit.setMinimumHeight(35)  # Yükseklik artırıldı
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        layout.addRow("Tarih:", self.date_edit)

        # Description input
        self.description_edit = QLineEdit()
        self.description_edit.setFont(dialog_font)
        self.description_edit.setMinimumHeight(35)
        layout.addRow("Açıklama:", self.description_edit)

        # Record type
        self.record_type = QComboBox()
        self.record_type.setFont(dialog_font)
        self.record_type.setMinimumHeight(35)
        self.record_type.addItems(["Borç", "Ödeme"])
        layout.addRow("Tür:", self.record_type)

        # Amount input
        self.amount_edit = QLineEdit()
        self.amount_edit.setFont(dialog_font)
        self.amount_edit.setMinimumHeight(35)
        self.amount_edit.setPlaceholderText("0.00")
        layout.addRow("Tutar:", self.amount_edit)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                 QDialogButtonBox.StandardButton.Cancel)
        # Buton fontunu büyüt
        buttons.setFont(dialog_font)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        self.setLayout(layout)

    def get_record_data(self):
        """Dialog'dan veriyi al"""
        record_type = self.record_type.currentText()

        # Tutar alanını güvenli şekilde parse et
        amount_text = self.amount_edit.text().strip()
        try:
            # Türkçe virgül karakterini nokta ile değiştir
            amount_text = amount_text.replace(',', '.')
            # Boş string kontrolü
            if not amount_text:
                amount = 0.0
            else:
                amount = float(amount_text)
                # Negatif değer kontrolü
                if amount < 0:
                    QMessageBox.warning(self, "Geçersiz Tutar", "Tutar negatif olamaz!")
                    return None
        except ValueError:
            QMessageBox.warning(self, "Geçersiz Tutar",
                              f"'{amount_text}' geçerli bir sayı değil!\n\n"
                              "Lütfen sadece sayı girin (örnek: 100 veya 100.50)")
            return None

        # Açıklama alanı kontrolü
        description = self.description_edit.text().strip()
        if not description:
            QMessageBox.warning(self, "Eksik Bilgi", "Lütfen açıklama girin!")
            return None

        if record_type == "Borç":
            debt_amount = amount
            payment_amount = 0.0
            status = "Ödenmedi"
        else:
            debt_amount = 0.0
            payment_amount = amount
            status = "Ödendi"  # Ödeme girildiyse zaten ödenmiş demektir

        return DebtRecord(
            record_id=None,  # ID veritabanı tarafından atanacak
            date=self.date_edit.date().toString("yyyy-MM-dd"),
            description=description,
            debt_amount=debt_amount,
            payment_amount=payment_amount,
            payment_status=status
        )

class CreditorDetailWidget(QWidget):
    """Borçlu detayları ve kayıtları görüntüleme widget'ı"""
    def __init__(self, creditor, parent_app):
        super().__init__()
        self.creditor = creditor
        self.parent_app = parent_app
        self.setup_ui()
        self.populate_table()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Header
        header_layout = QHBoxLayout()
        title = QLabel(f"Borçlu: {self.creditor.name}")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))  # 16'dan 20'ye çıkarıldı
        header_layout.addWidget(title)

        # Total debt display
        self.total_debt_label = QLabel()
        self.update_total_debt_display()
        self.total_debt_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))  # 12'den 16'ya çıkarıldı
        header_layout.addWidget(self.total_debt_label)

        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Action buttons
        button_layout = QHBoxLayout()

        # Buton fontlarını büyüt
        button_font = QFont("Arial", 12)  # Butonlar için 12pt font

        add_record_btn = QPushButton("Kayıt Ekle")
        add_record_btn.setFont(button_font)
        add_record_btn.setMinimumHeight(40)  # Buton yüksekliği artırıldı
        add_record_btn.clicked.connect(self.add_record)
        button_layout.addWidget(add_record_btn)

        refresh_btn = QPushButton("Yenile")
        refresh_btn.setFont(button_font)
        refresh_btn.setMinimumHeight(40)
        refresh_btn.clicked.connect(self.refresh_data)
        button_layout.addWidget(refresh_btn)

        print_btn = QPushButton("Defter Yazdır")
        print_btn.setFont(button_font)
        print_btn.setMinimumHeight(40)
        print_btn.clicked.connect(self.print_ledger)
        button_layout.addWidget(print_btn)

        export_pdf_btn = QPushButton("PDF'ye Aktar")
        export_pdf_btn.setFont(button_font)
        export_pdf_btn.setMinimumHeight(40)
        export_pdf_btn.clicked.connect(self.export_to_pdf)
        button_layout.addWidget(export_pdf_btn)

        backup_btn = QPushButton("Yedek Oluştur")
        backup_btn.setFont(button_font)
        backup_btn.setMinimumHeight(40)
        backup_btn.clicked.connect(self.create_manual_backup)
        button_layout.addWidget(backup_btn)

        back_btn = QPushButton("Ana Sayfaya Dön")
        back_btn.setFont(button_font)
        back_btn.setMinimumHeight(40)
        back_btn.clicked.connect(self.parent_app.show_main_page)
        button_layout.addWidget(back_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        # Records table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Tarih", "Açıklama", "Borç Tutarı", "Ödeme Tutarı",
            "Kalan Borç", "İşlem Türü"
        ])

        # Tablo başlık fontunu büyüt
        header_font = QFont("Arial", 12, QFont.Weight.Bold)
        self.table.horizontalHeader().setFont(header_font)
        self.table.horizontalHeader().setMinimumHeight(35)  # Başlık yüksekliği

        # Tablo içerik fontunu büyüt
        table_font = QFont("Arial", 11)
        self.table.setFont(table_font)

        # Satır yüksekliğini artır
        self.table.verticalHeader().setDefaultSectionSize(30)

        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self.table)
        self.setLayout(layout)

    def refresh_data(self):
        """Verileri yenile"""
        self.creditor.refresh_records()
        self.populate_table()
        self.update_total_debt_display()
        self.parent_app.update_creditor_list()
        QMessageBox.information(self, "Yenileme", "Veriler başarıyla yenilendi!")

    def create_manual_backup(self):
        """Manuel yedek oluştur"""
        try:
            backup_path = self.parent_app.db_manager.create_backup("manual")
            if backup_path:
                QMessageBox.information(self, "Yedekleme Başarılı",
                                      f"Yedek başarıyla oluşturuldu!")
            else:
                QMessageBox.warning(self, "Yedekleme Hatası",
                                  "Yedek oluşturulamadı!")
        except Exception as e:
            QMessageBox.critical(self, "Yedekleme Hatası",
                               f"Yedek oluşturulurken hata: {str(e)}")

    def update_total_debt_display(self):
        """Toplam borç görüntüsünü güncelle"""
        total = self.creditor.get_total_debt()
        color = "red" if total > 0 else "green"
        self.total_debt_label.setText(f"<span style='color: {color}'>Toplam Borç: ₺{total:.2f}</span>")

    def populate_table(self):
        """Tabloyu borçlu kayıtlarıyla doldur"""
        self.table.setRowCount(len(self.creditor.records))

        for row, record in enumerate(self.creditor.records):
            self.table.setItem(row, 0, QTableWidgetItem(record.date))
            self.table.setItem(row, 1, QTableWidgetItem(record.description))
            self.table.setItem(row, 2, QTableWidgetItem(f"₺{record.debt_amount:.2f}"))
            self.table.setItem(row, 3, QTableWidgetItem(f"₺{record.payment_amount:.2f}"))
            self.table.setItem(row, 4, QTableWidgetItem(f"₺{record.remaining_debt:.2f}"))

            # İşlem türünü belirle
            if record.debt_amount > 0 and record.payment_amount == 0:
                transaction_type = "Borç"
            elif record.payment_amount > 0 and record.debt_amount == 0:
                transaction_type = "Ödeme"
            elif record.debt_amount > 0 and record.payment_amount > 0:
                transaction_type = "Borç + Ödeme"
            else:
                transaction_type = "Düzenleme"

            self.table.setItem(row, 5, QTableWidgetItem(transaction_type))

            # Color code the remaining debt
            remaining_item = self.table.item(row, 4)
            if record.remaining_debt > 0:
                remaining_item.setBackground(Qt.GlobalColor.lightGray)

    def add_record(self):
        """Borçluya yeni kayıt ekle"""
        dialog = AddRecordDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            record_data = dialog.get_record_data()

            # Validation başarısız olduysa işlemi durdur
            if record_data is None:
                return

            # Veritabanına ekle
            success = self.creditor.add_record(record_data)

            if success:
                self.populate_table()
                self.update_total_debt_display()
                self.parent_app.update_creditor_list()
                QMessageBox.information(self, "Başarılı", "Kayıt başarıyla eklendi!")
            else:
                QMessageBox.critical(self, "Hata", "Kayıt eklenirken hata oluştu!")

    def print_ledger(self):
        """Borçlunun defterini yazdır"""
        printer = QPrinter()
        dialog = QPrintDialog(printer, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.render_to_printer(printer)

    def export_to_pdf(self):
        """Borçlunun defterini PDF'ye aktar"""
        filename = f"{self.creditor.name}_defter.pdf"
        filepath = os.path.join(os.path.expanduser("~"), "Desktop", filename)

        try:
            self.create_pdf(filepath)
            QMessageBox.information(self, "Dışa Aktarma Başarılı",
                                  f"Defter şu konuma aktarıldı: {filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Dışa Aktarma Hatası",
                               f"PDF dışa aktarma başarısız: {str(e)}")

    def create_pdf(self, filepath):
        """Borçlunun defterinin PDF'ini oluştur"""
        c = canvas.Canvas(filepath, pagesize=letter)
        width, height = letter

        # Register fonts for Turkish characters
        try:
            # First try project fonts directory
            fonts_dir = os.path.join(os.path.dirname(__file__), 'fonts')

            if os.path.exists(os.path.join(fonts_dir, 'Roboto-Regular.ttf')):
                pdfmetrics.registerFont(TTFont('Roboto', os.path.join(fonts_dir, 'Roboto-Regular.ttf')))
                pdfmetrics.registerFont(TTFont('Roboto-Bold', os.path.join(fonts_dir, 'Roboto-Bold.ttf')))

                addMapping('Roboto', 0, 0, 'Roboto')
                addMapping('Roboto', 1, 0, 'Roboto-Bold')

                title_font = 'Roboto-Bold'
                regular_font = 'Roboto'
                print("✅ Roboto fontları kullanılıyor")
            else:
                raise Exception("Local fonts not found")

        except:
            try:
                # Try to use DejaVu fonts (commonly available on Linux)
                pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
                pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))

                addMapping('DejaVuSans', 0, 0, 'DejaVuSans')
                addMapping('DejaVuSans', 1, 0, 'DejaVuSans-Bold')

                title_font = 'DejaVuSans-Bold'
                regular_font = 'DejaVuSans'
                print("✅ DejaVu fontları kullanılıyor")
            except:
                try:
                    # Fallback: try Liberation fonts
                    pdfmetrics.registerFont(TTFont('LiberationSans', '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'))
                    pdfmetrics.registerFont(TTFont('LiberationSans-Bold', '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'))

                    addMapping('LiberationSans', 0, 0, 'LiberationSans')
                    addMapping('LiberationSans', 1, 0, 'LiberationSans-Bold')

                    title_font = 'LiberationSans-Bold'
                    regular_font = 'LiberationSans'
                    print("✅ Liberation fontları kullanılıyor")
                except:
                    # Last fallback: use built-in fonts (may not support Turkish characters fully)
                    title_font = 'Helvetica-Bold'
                    regular_font = 'Helvetica'
                    print("⚠️ Standart fontlar kullanılıyor - Türkçe karakterler d��zgün görünmeyebilir")

        # Title
        c.setFont(title_font, 16)
        c.drawString(50, height - 50, f"{self.creditor.name} için Alacak Verecek Çıktısı")

        # Total debt
        c.setFont(title_font, 12)
        total_debt = self.creditor.get_total_debt()
        c.drawString(50, height - 80, f"Toplam Ödenmemiş Borç: ₺{total_debt:.2f}")

        # Table headers
        y_position = height - 120
        headers = ["Tarih", "Açıklama", "Borç", "Ödeme", "Kalan", "İşlem Türü"]
        x_positions = [50, 120, 250, 320, 390, 470]

        c.setFont(title_font, 10)
        for i, header in enumerate(headers):
            c.drawString(x_positions[i], y_position, header)

        # Draw line under headers
        c.line(50, y_position - 5, 550, y_position - 5)

        # Table data
        c.setFont(regular_font, 9)
        y_position -= 20

        for record in self.creditor.records:
            if y_position < 50:  # Start new page if needed
                c.showPage()
                c.setFont(regular_font, 9)
                y_position = height - 50

            # Convert payment status to Turkish if needed
            status = record.payment_status
            if status == "Paid":
                status = "Ödendi"
            elif status == "Unpaid":
                status = "Ödenmedi"

            data = [
                record.date,
                record.description[:20] if len(record.description) > 20 else record.description,
                f"₺{record.debt_amount:.2f}",
                f"₺{record.payment_amount:.2f}",
                f"₺{record.remaining_debt:.2f}",
                status
            ]

            for i, item in enumerate(data):
                try:
                    c.drawString(x_positions[i], y_position, str(item))
                except UnicodeEncodeError:
                    # If there's an encoding issue, try to handle it
                    try:
                        # Convert Turkish characters to ASCII equivalents as fallback
                        turkish_chars = {'ç': 'c', 'Ç': 'C', 'ğ': 'g', 'Ğ': 'G', 'ı': 'i', 'İ': 'I', 'ö': 'o', 'Ö': 'O', 'ş': 's', 'Ş': 'S', 'ü': 'u', 'Ü': 'U', '₺': 'TL'}
                        clean_item = str(item)
                        for tr_char, en_char in turkish_chars.items():
                            clean_item = clean_item.replace(tr_char, en_char)
                        c.drawString(x_positions[i], y_position, clean_item)
                    except:
                        # Last resort: remove problematic characters
                        clean_item = ''.join(char for char in str(item) if ord(char) < 128)
                        c.drawString(x_positions[i], y_position, clean_item)

            y_position -= 15

        c.save()

    def render_to_printer(self, printer):
        """Defteri yazıcıya gönder"""
        # This is a simplified version - in a real application,
        # you might want to use QPainter for more sophisticated printing
        pass

class DatabaseSettingsDialog(QDialog):
    """Veritabanı ayarları ve temizlik dialog'u"""
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("Veritabanı Ayarları ve Temizlik")
        self.setModal(True)
        self.resize(500, 400)
        self.setup_ui()
        self.load_stats()

    def setup_ui(self):
        layout = QVBoxLayout()

        # İstatistikler grubu
        stats_group = QGroupBox("Veritabanı İstatistikleri")
        stats_layout = QFormLayout()

        self.creditor_count_label = QLabel()
        self.record_count_label = QLabel()
        self.oldest_date_label = QLabel()
        self.newest_date_label = QLabel()
        self.db_size_label = QLabel()
        self.backup_count_label = QLabel()

        stats_layout.addRow("Toplam Borçlu Sayısı:", self.creditor_count_label)
        stats_layout.addRow("Toplam Kayıt Sayısı:", self.record_count_label)
        stats_layout.addRow("En Eski Kayıt:", self.oldest_date_label)
        stats_layout.addRow("En Yeni Kayıt:", self.newest_date_label)
        stats_layout.addRow("Veritabanı Boyutu:", self.db_size_label)
        stats_layout.addRow("Yedek Sayısı:", self.backup_count_label)

        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        # Temizlik grubu
        cleanup_group = QGroupBox("Temizlik Ayarları")
        cleanup_layout = QVBoxLayout()

        # Eski kayıtları temizle
        records_layout = QHBoxLayout()
        records_layout.addWidget(QLabel("Eski kayıtları temizle (günden eski):"))
        self.keep_days_spin = QSpinBox()
        self.keep_days_spin.setRange(30, 3650)  # 1 ay ile 10 yıl arası
        self.keep_days_spin.setValue(365)  # Varsayılan 1 yıl
        self.keep_days_spin.setSuffix(" gün")
        records_layout.addWidget(self.keep_days_spin)

        cleanup_records_btn = QPushButton("Eski Kayıtları Temizle")
        cleanup_records_btn.clicked.connect(self.cleanup_old_records)
        records_layout.addWidget(cleanup_records_btn)

        cleanup_layout.addLayout(records_layout)

        # Yedek dosyalarını temizle
        backup_layout = QHBoxLayout()
        backup_layout.addWidget(QLabel("Tutulacak yedek sayısı:"))
        self.keep_backups_spin = QSpinBox()
        self.keep_backups_spin.setRange(5, 50)
        self.keep_backups_spin.setValue(10)
        self.keep_backups_spin.setSuffix(" adet")
        backup_layout.addWidget(self.keep_backups_spin)

        cleanup_backups_btn = QPushButton("Eski Yedekleri Temizle")
        cleanup_backups_btn.clicked.connect(self.cleanup_old_backups)
        backup_layout.addWidget(cleanup_backups_btn)

        cleanup_layout.addLayout(backup_layout)

        cleanup_group.setLayout(cleanup_layout)
        layout.addWidget(cleanup_group)

        # Yedekleme grubu
        backup_group = QGroupBox("Yedekleme İşlemleri")
        backup_layout = QHBoxLayout()

        create_backup_btn = QPushButton("Manuel Yedek Oluştur")
        create_backup_btn.clicked.connect(self.create_manual_backup)
        backup_layout.addWidget(create_backup_btn)

        refresh_stats_btn = QPushButton("İstatistikleri Yenile")
        refresh_stats_btn.clicked.connect(self.load_stats)
        backup_layout.addWidget(refresh_stats_btn)

        backup_group.setLayout(backup_layout)
        layout.addWidget(backup_group)

        # Butonlar
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.accept)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def load_stats(self):
        """İstatistikleri yükle"""
        stats = self.db_manager.get_database_stats()
        if stats:
            self.creditor_count_label.setText(str(stats['creditor_count']))
            self.record_count_label.setText(str(stats['record_count']))
            self.oldest_date_label.setText(stats['oldest_date'] or "Kayıt yok")
            self.newest_date_label.setText(stats['newest_date'] or "Kayıt yok")
            self.db_size_label.setText(f"{stats['db_size_mb']:.2f} MB")
            self.backup_count_label.setText(str(stats['backup_count']))
        else:
            # Hata durumunda varsayılan değerler
            for label in [self.creditor_count_label, self.record_count_label,
                         self.oldest_date_label, self.newest_date_label,
                         self.db_size_label, self.backup_count_label]:
                label.setText("Hata")

    def cleanup_old_records(self):
        """Eski kayıtları temizle"""
        keep_days = self.keep_days_spin.value()

        reply = QMessageBox.question(
            self, "Eski Kayıtları Temizle",
            f"{keep_days} günden eski tüm kayıtlar silinecek!\n\n"
            "Bu işlem geri alınamaz. Devam edilsin mi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                deleted_count = self.db_manager.cleanup_old_records(keep_days)
                if deleted_count > 0:
                    QMessageBox.information(
                        self, "Temizlik Tamamlandı",
                        f"{deleted_count} eski kayıt başarıyla silindi!"
                    )
                else:
                    QMessageBox.information(
                        self, "Temizlik Tamamlandı",
                        "Silinecek eski kayıt bulunamadı."
                    )
                self.load_stats()  # İstatistikleri güncelle
            except Exception as e:
                QMessageBox.critical(
                    self, "Temizlik Hatası",
                    f"Eski kayıtlar temizlenirken hata oluştu: {str(e)}"
                )

    def cleanup_old_backups(self):
        """Eski yedekleri temizle"""
        keep_count = self.keep_backups_spin.value()

        reply = QMessageBox.question(
            self, "Eski Yedekleri Temizle",
            f"En son {keep_count} yedek hariç tüm eski yedekler silinecek!\n\n"
            "Devam edilsin mi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.db_manager.cleanup_old_backups(keep_count)
                QMessageBox.information(
                    self, "Temizlik Tamamlandı",
                    "Eski yedekler başarıyla temizlendi!"
                )
                self.load_stats()  # İstatistikleri güncelle
            except Exception as e:
                QMessageBox.critical(
                    self, "Temizlik Hatası",
                    f"Eski yedekler temizlenirken hata oluştu: {str(e)}"
                )

    def create_manual_backup(self):
        """Manuel yedek oluştur"""
        try:
            backup_path = self.db_manager.create_backup("manual_settings")
            if backup_path:
                QMessageBox.information(
                    self, "Yedekleme Başarılı",
                    "Manuel yedek başarıyla oluşturuldu!"
                )
                self.load_stats()  # İstatistikleri güncelle
            else:
                QMessageBox.warning(
                    self, "Yedekleme Hatası",
                    "Yedek oluşturulamadı!"
                )
        except Exception as e:
            QMessageBox.critical(
                self, "Yedekleme Hatası",
                f"Yedek oluşturulurken hata: {str(e)}"
            )

class DebtLedgerApp(QMainWindow):
    """Ana uygulama penceresi"""
    def __init__(self):
        super().__init__()

        # Veritabanı yöneticisini başlat
        self.db_manager = DatabaseManager()

        # Eski JSON dosyasından geçiş yap
        self.migrate_from_old_format()

        self.setWindowTitle("Veresiye Defteri Uygulaması - Veritabanı Destekli")
        self.setGeometry(100, 100, 1200, 800)

        self.setup_ui()
        self.update_creditor_list()

    def migrate_from_old_format(self):
        """Eski JSON formatından veritabanına geçiş"""
        old_json_file = "debt_ledger_data.json"
        if os.path.exists(old_json_file):
            reply = QMessageBox.question(
                self, "Veri Geçişi",
                "Eski JSON formatında veriler bulundu. Veritabanına aktarılsın mı?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                if self.db_manager.migrate_from_json(old_json_file):
                    # Eski dosyayı yedekle ve sil
                    backup_name = f"debt_ledger_data_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    os.rename(old_json_file, backup_name)
                    QMessageBox.information(self, "Geçiş Tamamlandı",
                                          f"Veriler başarıyla aktarıldı! Eski dosya '{backup_name}' olarak yedeklendi.")
                else:
                    QMessageBox.warning(self, "Geçiş Hatası", "Veri geçişi sırasında hata oluştu!")

    def setup_ui(self):
        """Kullanıcı arayüzünü ayarla"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QHBoxLayout()

        # Left panel - creditor list
        left_panel = QWidget()
        left_panel.setMaximumWidth(350)  # Genişlik artırıldı
        left_layout = QVBoxLayout()

        # Title
        title = QLabel("Borçlular")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))  # 14'ten 18'e çıkarıldı
        left_layout.addWidget(title)

        # Sol panel butonları için font
        left_button_font = QFont("Arial", 12)

        # Add creditor button
        add_creditor_btn = QPushButton("Yeni Borçlu Ekle")
        add_creditor_btn.setFont(left_button_font)
        add_creditor_btn.setMinimumHeight(45)  # Yükseklik artırıldı
        add_creditor_btn.clicked.connect(self.add_creditor)
        left_layout.addWidget(add_creditor_btn)

        # Creditor list
        self.creditor_list = QListWidget()
        # Liste fontunu büyüt
        list_font = QFont("Arial", 12)
        self.creditor_list.setFont(list_font)
        # Liste item yüksekliğini artır
        self.creditor_list.setStyleSheet("QListWidget::item { padding: 8px; }")
        self.creditor_list.itemDoubleClicked.connect(self.show_creditor_details)
        left_layout.addWidget(self.creditor_list)

        # Delete creditor button
        delete_creditor_btn = QPushButton("Seçili Borçluyu Sil")
        delete_creditor_btn.setFont(left_button_font)
        delete_creditor_btn.setMinimumHeight(45)
        delete_creditor_btn.clicked.connect(self.delete_creditor)
        left_layout.addWidget(delete_creditor_btn)

        # Spacer
        left_layout.addStretch()

        # Database settings button
        db_settings_btn = QPushButton("Veritabanı Ayarları")
        db_settings_btn.setFont(left_button_font)
        db_settings_btn.setMinimumHeight(45)
        db_settings_btn.clicked.connect(self.show_database_settings)
        left_layout.addWidget(db_settings_btn)

        left_panel.setLayout(left_layout)
        layout.addWidget(left_panel)

        # Right panel - stacked widget for different views
        self.stacked_widget = QStackedWidget()

        # Main page
        main_page = QWidget()
        main_layout = QVBoxLayout()
        welcome_label = QLabel("Veresiye Defteri'ne Hoş Geldiniz")
        welcome_label.setFont(QFont("Arial", 24))  # 18'den 24'e çıkarıldı
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(welcome_label)

        instructions = QLabel(
            "Kullanım Talimatları:\n"
            "• Bir borçlunun detaylarını görmek için çift tıklayın\n"
            "• Yeni borçlu eklemek için 'Yeni Borçlu Ekle' butonunu kullanın\n"
            "• Borçlu detaylarında borç ve ödeme ekleyebilirsiniz\n"
            "• Defterleri PDF'ye aktarabilir veya yazdırabilirsiniz"
        )
        instructions.setFont(QFont("Arial", 14))  # Talimatlar için font eklendi
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(instructions)
        main_layout.addStretch()

        main_page.setLayout(main_layout)
        self.stacked_widget.addWidget(main_page)

        layout.addWidget(self.stacked_widget)
        central_widget.setLayout(layout)

    def add_creditor(self):
        """Yeni borçlu ekle"""
        name, ok = QInputDialog.getText(self, "Borçlu Ekle", "Borçlu adını girin:")
        if ok and name.strip():
            creditor_id = self.db_manager.add_creditor(name.strip())

            if creditor_id:
                self.update_creditor_list()
                QMessageBox.information(self, "Başarılı", f"'{name.strip()}' başarıyla eklendi!")
            else:
                QMessageBox.warning(self, "Hata",
                                  "Bu isimde bir borçlu zaten mevcut veya ekleme sırasında hata oluştu!")

    def delete_creditor(self):
        """Seçili borçluyu sil"""
        current_item = self.creditor_list.currentItem()
        if current_item:
            # Borçlu adını al (format: "Ad - ₺tutar - durum")
            creditor_name = current_item.text().split(" - ")[0]

            reply = QMessageBox.question(
                self, "Borçlu Sil",
                f"'{creditor_name}' ve tüm kayıtlarını silmek istediğinizden emin misiniz?\n\n"
                "Bu işlem geri alınamaz!",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                # Borçlu ID'sini bul
                creditor_data = self.db_manager.get_creditor_by_name(creditor_name)
                if creditor_data:
                    success = self.db_manager.delete_creditor(creditor_data['id'])
                    if success:
                        self.update_creditor_list()
                        self.show_main_page()
                        QMessageBox.information(self, "Başarılı", f"'{creditor_name}' başarıyla silindi!")
                    else:
                        QMessageBox.critical(self, "Hata", "Borçlu silinirken hata oluştu!")

    def update_creditor_list(self):
        """Borçlu listesi görüntüsünü güncelle"""
        self.creditor_list.clear()

        creditors_data = self.db_manager.get_all_creditors()

        for creditor_data in creditors_data:
            total_debt = creditor_data['total_debt']
            record_count = creditor_data['record_count']

            # Son ödeme durumunu belirle
            if record_count == 0:
                last_payment_status = "Kayıt yok"
            else:
                # Veritabanından son ödeme durumunu al
                creditor = Creditor(creditor_data['id'], creditor_data['name'], self.db_manager)
                last_payment_status = creditor.get_last_payment_status()

            item_text = f"{creditor_data['name']} - ₺{total_debt:.2f} - {last_payment_status}"
            self.creditor_list.addItem(item_text)

    def show_creditor_details(self, item):
        """Seçili borçlunun detaylarını göster"""
        creditor_name = item.text().split(" - ")[0]

        # Veritabanından borçlu bilgilerini al
        creditor_data = self.db_manager.get_creditor_by_name(creditor_name)

        if creditor_data:
            # Remove existing creditor detail widgets
            while self.stacked_widget.count() > 1:
                widget = self.stacked_widget.widget(1)
                self.stacked_widget.removeWidget(widget)
                widget.deleteLater()

            # Add new creditor detail widget
            creditor = Creditor(creditor_data['id'], creditor_data['name'], self.db_manager)
            detail_widget = CreditorDetailWidget(creditor, self)
            self.stacked_widget.addWidget(detail_widget)
            self.stacked_widget.setCurrentWidget(detail_widget)

    def show_main_page(self):
        """Ana sayfayı göster"""
        self.stacked_widget.setCurrentIndex(0)

    def show_database_settings(self):
        """Veritabanı ayarları dialog'unu göster"""
        dialog = DatabaseSettingsDialog(self.db_manager, self)
        dialog.exec()
        # Dialog kapatıldıktan sonra borçlu listesini güncelle
        self.update_creditor_list()

    def closeEvent(self, event):
        """Uygulama kapatma olayını işle"""
        # Kapanırken otomatik yedek oluştur
        try:
            self.db_manager.create_backup("app_close")
        except Exception as e:
            print(f"Kapanış yedeği oluşturulamadı: {e}")

        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DebtLedgerApp()
    window.show()
    sys.exit(app.exec())
