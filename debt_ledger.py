"""
Ana Veresiye Defteri Uygulaması - Veritabanı Destekli
"""

import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QListWidget, QPushButton, QLabel, QStackedWidget,
                             QMessageBox, QInputDialog, QTableWidget, QTableWidgetItem,
                             QHeaderView, QDialog, QFormLayout, QLineEdit, QComboBox,
                             QDateEdit, QTextEdit, QDialogButtonBox, QApplication,
                             QProgressDialog, QSpinBox, QGroupBox, QDoubleSpinBox)
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
from download_fonts import FontDownloader

class PDFGenerator:
    """Ortak PDF oluşturucu sınıfı - hem defter hem fiş çıktısı için kullanılır"""

    def __init__(self):
        self.title_font = None
        self.regular_font = None
        self._setup_fonts()

    def _setup_fonts(self):
        """Font ayarlarını yap"""
        try:
            fonts_dir = os.path.join(os.path.dirname(__file__), 'fonts')

            # Öncelikle Roboto'yu deneyelim
            if os.path.exists(os.path.join(fonts_dir, 'Roboto-Regular.ttf')):
                pdfmetrics.registerFont(TTFont('Roboto', os.path.join(fonts_dir, 'Roboto-Regular.ttf')))
                pdfmetrics.registerFont(TTFont('Roboto-Bold', os.path.join(fonts_dir, 'Roboto-Bold.ttf')))
                addMapping('Roboto', 0, 0, 'Roboto')
                addMapping('Roboto', 1, 0, 'Roboto-Bold')
                self.title_font = 'Roboto-Bold'
                self.regular_font = 'Roboto'
            else:
                # Roboto yoksa sistem fontlarından birini kullan
                fallback_fonts = ['NotoSans-Regular.ttf', 'Arial.ttf', 'Calibri.ttf', 'Tahoma.ttf', 'Verdana.ttf', 'SegoeUI.ttf']
                for fname in fallback_fonts:
                    path = os.path.join(fonts_dir, fname)
                    if os.path.exists(path):
                        font_name = os.path.splitext(fname)[0].replace('-Regular', '').replace('-Bold', '')
                        pdfmetrics.registerFont(TTFont(font_name, path))
                        self.title_font = font_name
                        self.regular_font = font_name
                        break
                else:
                    raise Exception("Local fonts not found")
        except Exception as e:
            print(f"⚠️ Font yükleme hatası: {e}")
            print("⚠️ Standart fontlar kullanılacak")
            self.title_font = 'Helvetica-Bold'
            self.regular_font = 'Helvetica'

    def _split_text_lines(self, text, max_length=8):
        """Metni belirtilen karakter sayısında satırlara böl"""
        if not text:
            return [""]
        return [text[i:i+max_length] for i in range(0, len(text), max_length)]

    def _draw_receipt_format(self, c, width, height, creditor_name, record, receipt_number=None, y_start=None):
        """Tek bir fiş formatını çiz - hem tekil fiş hem defter için kullanılır"""

        # Başlangıç Y koordinatı
        if y_start is None:
            y_start = height - 50

        # Fiş numarası oluştur
        if not receipt_number:
            receipt_number = f"B{record.id:011d}"

        # Başlık Bilgileri
        c.setFont(self.title_font, 16)
        c.drawCentredString(width/2, y_start, "GÜRBİLEK OTO TAMİR")

        # Fiş bilgileri
        c.setFont(self.regular_font, 11)
        c.drawString(50, y_start - 30, f"Fiş No: {receipt_number}")

        # Tarih formatını düzelt
        try:
            date_obj = datetime.strptime(record.date, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%d.%m.%Y')
        except:
            formatted_date = record.date

        c.drawString(400, y_start - 30, f"Tarih: {formatted_date}")
        c.drawString(50, y_start - 45, f"Müşteri: {creditor_name}")

        # Tablo başlıkları
        table_start_y = y_start - 80
        c.setFont(self.title_font, 9)

        # Metinleri satırlara böl
        description_lines = self._split_text_lines(record.description, 12)  # Açıklama için biraz daha uzun
        kod1_lines = self._split_text_lines(record.kod1, 8)
        kod2_lines = self._split_text_lines(record.kod2, 8)
        max_lines = max(len(description_lines), len(kod1_lines), len(kod2_lines), 1)

        # Tablo yüksekliğini hesapla
        table_height = 40 + (max_lines * 12)

        # Tablo çizgilerini çiz
        c.line(50, table_start_y, width - 50, table_start_y)  # Üst çizgi
        c.line(50, table_start_y - 15, width - 50, table_start_y - 15)  # Başlık alt çizgisi

        # Dikey çizgiler
        col_positions = [50, 150, 220, 290, 360, 450, width - 50]
        for x in col_positions:
            c.line(x, table_start_y, x, table_start_y - table_height)

        # Başlık metinleri
        headers = ["Cinsi", "Kod1", "Kod2", "Miktar", "Birim", "Tutar"]
        header_x_positions = [60, 160, 230, 300, 370, 460]
        for i, header in enumerate(headers):
            c.drawString(header_x_positions[i], table_start_y - 12, header)

        # Kayıt verilerini yazdır
        c.setFont(self.regular_font, 8)
        data_y = table_start_y - 25

        # Miktar ve tutar hesapla
        if record.debt_amount > 0:
            miktar = "1"
            tutar = record.debt_amount
        else:
            miktar = "-"
            tutar = record.payment_amount

        birim = record.birim if record.birim else "Adet"

        # Satır verilerini yazdır
        for line_idx in range(max_lines):
            y = data_y - (line_idx * 12)

            # Açıklama (sadece ilk satırda)
            if line_idx < len(description_lines):
                c.drawString(header_x_positions[0], y, description_lines[line_idx])

            # Kod1
            if line_idx < len(kod1_lines):
                c.drawString(header_x_positions[1], y, kod1_lines[line_idx])

            # Kod2
            if line_idx < len(kod2_lines):
                c.drawString(header_x_positions[2], y, kod2_lines[line_idx])

            # Miktar, Birim, Tutar (sadece ilk satırda)
            if line_idx == 0:
                c.drawString(header_x_positions[3], y, miktar)
                c.drawString(header_x_positions[4], y, birim)
                c.drawString(header_x_positions[5], y, f"₺{tutar:.2f}")

        # Alt çizgi
        alt_cizgi_y = table_start_y - table_height
        c.line(50, alt_cizgi_y, width - 50, alt_cizgi_y)

        # Alt Bilgiler - Sadeleştirilmiş
        c.setFont(self.regular_font, 10)
        bottom_y = alt_cizgi_y - 25

        # Sadece toplam tutar ve bakiye bilgisi
        c.drawString(400, bottom_y, f"Toplam: ₺{tutar:.2f}")

        # Yeni bakiye bilgisi
        c.setFont(self.title_font, 11)
        yeni_bakiye = record.remaining_debt
        bakiye_renk = "Alacak" if yeni_bakiye > 0 else "Bakiye Sıfır" if yeni_bakiye == 0 else "Borç"
        c.drawString(400, bottom_y - 20, f"Kalan Bakiye: ₺{abs(yeni_bakiye):.2f} ({bakiye_renk})")

        # Bu fişin kapladığı toplam yüksekliği döndür
        return y_start - (bottom_y - 50)  # 50 piksel alt boşluk

    def create_ledger_pdf(self, filepath, creditor_name, records):
        """Defter çıktısı PDF'i oluştur - tüm fişleri alt alta"""
        c = canvas.Canvas(filepath, pagesize=letter)
        width, height = letter

        # Ana başlık
        c.setFont(self.title_font, 18)
        c.drawCentredString(width/2, height - 30, f"{creditor_name} - Alacak Verecek Defteri")

        current_y = height - 70

        for i, record in enumerate(records):
            # Sayfa sonu kontrolü
            if current_y < 200:  # En az 200px boş alan gerekli
                c.showPage()
                current_y = height - 30
                # Sayfa başlığını tekrar yaz
                c.setFont(self.title_font, 16)
                c.drawCentredString(width/2, current_y, f"{creditor_name} - Alacak Verecek Defteri (devam)")
                current_y -= 40

            # Fiş çiz ve kullanılan yüksekliği al
            used_height = self._draw_receipt_format(
                c, width, height, creditor_name, record,
                receipt_number=f"B{record.id:011d}",
                y_start=current_y
            )

            current_y -= used_height + 20  # 20px fişler arası boşluk

            # Fişler arası ayırıcı çizgi
            if i < len(records) - 1:  # Son fiş değilse
                c.setLineWidth(0.5)
                c.line(50, current_y + 10, width - 50, current_y + 10)
                current_y -= 10

        c.save()

    def create_receipt_pdf(self, filepath, creditor_name, record, receipt_number=None):
        """Fiş çıktısı PDF'i oluştur - tek fiş"""
        c = canvas.Canvas(filepath, pagesize=letter)
        width, height = letter

        # Tek fiş çiz
        self._draw_receipt_format(
            c, width, height, creditor_name, record, receipt_number
        )

        # Alt bilgi
        c.setFont(self.regular_font, 7)
        c.drawString(50, 30, f"Bu fiş {datetime.now().strftime('%d.%m.%Y %H:%M')} tarihinde oluşturulmuştur.")

        c.save()

class DebtRecord:
    """Borç kaydı sınıfı - artık veritabanından gelecek"""
    def __init__(self, record_id, date, description, debt_amount=0, payment_amount=0, payment_status="Ödenmedi", remaining_debt=0, kod1="", kod2="", birim="", iskonto=0.0, musteri_masrafi=0.0):
        self.id = record_id
        self.date = date
        self.description = description
        self.debt_amount = float(debt_amount) if debt_amount else 0.0
        self.payment_amount = float(payment_amount) if payment_amount else 0.0
        self.payment_status = payment_status
        self.remaining_debt = float(remaining_debt) if remaining_debt else 0.0
        self.kod1 = kod1
        self.kod2 = kod2
        self.birim = birim
        self.iskonto = float(iskonto) if iskonto else 0.0
        self.musteri_masrafi = float(musteri_masrafi) if musteri_masrafi else 0.0

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date,
            'description': self.description,
            'debt_amount': self.debt_amount,
            'payment_amount': self.payment_amount,
            'payment_status': self.payment_status,
            'remaining_debt': self.remaining_debt,
            'kod1': self.kod1,
            'kod2': self.kod2,
            'birim': self.birim,
            'iskonto': self.iskonto,
            'musteri_masrafi': self.musteri_masrafi
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            record_id=data.get('id'),
            date=data.get('date'),
            description=data.get('description'),
            debt_amount=data.get('debt_amount', 0),
            payment_amount=data.get('payment_amount', 0),
            payment_status=data.get('payment_status', "Ödenmedi"),
            remaining_debt=data.get('remaining_debt', 0),
            kod1=data.get('kod1', ""),
            kod2=data.get('kod2', ""),
            birim=data.get('birim', ""),
            iskonto=data.get('iskonto', 0.0),
            musteri_masrafi=data.get('musteri_masrafi', 0.0)
        )

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
            remaining_debt=r['remaining_debt'],
            kod1=r.get('kod1', ''),
            kod2=r.get('kod2', ''),
            birim=r.get('birim', ''),
            iskonto=r.get('iskonto', 0.0),
            musteri_masrafi=r.get('musteri_masrafi', 0.0)
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
            payment_status=record_data.payment_status,
            kod1=record_data.kod1,
            kod2=record_data.kod2,
            birim=record_data.birim
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
        self.resize(450, 450)  # Dialog boyutu büyütüldü

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

        # Kod1 input
        self.kod1_edit = QLineEdit()
        self.kod1_edit.setFont(dialog_font)
        self.kod1_edit.setMinimumHeight(35)
        self.kod1_edit.setPlaceholderText("Ürün/Hizmet Kodu 1")
        layout.addRow("Kod1:", self.kod1_edit)

        # Kod2 input
        self.kod2_edit = QLineEdit()
        self.kod2_edit.setFont(dialog_font)
        self.kod2_edit.setMinimumHeight(35)
        self.kod2_edit.setPlaceholderText("Ürün/Hizmet Kodu 2")
        layout.addRow("Kod2:", self.kod2_edit)

        # Birim input
        self.birim_edit = QLineEdit()
        self.birim_edit.setFont(dialog_font)
        self.birim_edit.setMinimumHeight(35)
        self.birim_edit.setPlaceholderText("Adet, KG, M2 vb.")
        layout.addRow("Birim:", self.birim_edit)

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
            payment_status=status,
            kod1=self.kod1_edit.text().strip(),
            kod2=self.kod2_edit.text().strip(),
            birim=self.birim_edit.text().strip()
        )

class CreditorDetailWidget(QWidget):
    """Borçlu detayları ve kayıtları görüntüleme widget'ı"""
    def __init__(self, creditor, parent_app):
        super().__init__()
        self.creditor = creditor
        self.parent_app = parent_app
        self.pdf_generator = PDFGenerator()  # PDF oluşturucu örneği
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

        receipt_btn = QPushButton("Fiş Çıktısı Al")
        receipt_btn.setFont(button_font)
        receipt_btn.setMinimumHeight(40)
        receipt_btn.clicked.connect(self.export_receipt_for_record)
        button_layout.addWidget(receipt_btn)

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
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
                 "Tarih", "Açıklama", "Kod1", "Kod2", "Birim",
                 "Borç Tutarı", "Ödeme Tutarı", "Kalan Borç", "İşlem Türü"
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
                                      "Yedek başarıyla oluşturuldu!")
            else:
                QMessageBox.warning(self, "Yedekleme Hatası",
                                  "Yedek oluşturulamadı!")
        except Exception as e:
            QMessageBox.critical(self, "Yedekleme Hatası",
                               f"Yedek oluşturulurken hata: {str(e)}")

    def update_total_debt_display(self):
        """Toplam bor���� görüntüsünü güncelle"""
        total = self.creditor.get_total_debt()
        color = "red" if total > 0 else "green"
        self.total_debt_label.setText(f"<span style='color: {color}'>Toplam Borç: ₺{total:.2f}</span>")

    def populate_table(self):
        """Tabloyu borçlu kayıtlarıyla doldur"""
        self.table.setRowCount(len(self.creditor.records))

        for row, record in enumerate(self.creditor.records):
            self.table.setItem(row, 0, QTableWidgetItem(record.date))
            self.table.setItem(row, 1, QTableWidgetItem(record.description))
            self.table.setItem(row, 2, QTableWidgetItem(record.kod1))  # Kod1
            self.table.setItem(row, 3, QTableWidgetItem(record.kod2))  # Kod2
            self.table.setItem(row, 4, QTableWidgetItem(record.birim))  # Birim
            self.table.setItem(row, 5, QTableWidgetItem(f"₺{record.debt_amount:.2f}"))  # Borç Tutarı
            self.table.setItem(row, 6, QTableWidgetItem(f"₺{record.payment_amount:.2f}"))  # Ödeme Tutarı
            self.table.setItem(row, 7, QTableWidgetItem(f"₺{record.remaining_debt:.2f}"))  # Kalan Borç

            # İşlem türünü belirle
            if record.debt_amount > 0 and record.payment_amount == 0:
                transaction_type = "Borç"
            elif record.payment_amount > 0 and record.debt_amount == 0:
                transaction_type = "Ödeme"
            elif record.debt_amount > 0 and record.payment_amount > 0:
                transaction_type = "Borç + Ödeme"
            else:
                transaction_type = "Düzenleme"

            self.table.setItem(row, 8, QTableWidgetItem(transaction_type))  # İşlem Türü

            # Color code the remaining debt
            remaining_item = self.table.item(row, 7)  # Kalan borç sütunu artık 7. sütun
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

    def render_to_printer(self, printer):
        """Yazıcıya render et"""
        try:
            # Basit bir HTML tablosu oluştur ve yazdır
            from PyQt6.QtGui import QTextDocument
            from PyQt6.QtPrintSupport import QPrinter

            html_content = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; font-size: 10pt; }}
                    h1 {{ text-align: center; color: #333; }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; font-weight: bold; }}
                    .debt {{ color: red; }}
                    .payment {{ color: green; }}
                </style>
            </head>
            <body>
                <h1>{self.creditor.name} - Veresiye Defteri</h1>
                <p><strong>Toplam Borç:</strong> ₺{self.creditor.get_total_debt():.2f}</p>
                <table>
                    <tr>
                        <th>Tarih</th>
                        <th>Açıklama</th>
                        <th>Kod1</th>
                        <th>Kod2</th>
                        <th>Birim</th>
                        <th>Borç</th>
                        <th>Ödeme</th>
                        <th>Kalan</th>
                        <th>İşlem</th>
                    </tr>
            """

            for record in self.creditor.records:
                debt_class = "debt" if record.debt_amount > 0 else ""
                payment_class = "payment" if record.payment_amount > 0 else ""

                html_content += f"""
                    <tr>
                        <td>{record.date}</td>
                        <td>{record.description}</td>
                        <td>{record.kod1}</td>
                        <td>{record.kod2}</td>
                        <td>{record.birim}</td>
                        <td class="{debt_class}">₺{record.debt_amount:.2f}</td>
                        <td class="{payment_class}">₺{record.payment_amount:.2f}</td>
                        <td>₺{record.remaining_debt:.2f}</td>
                        <td>{record.payment_status}</td>
                    </tr>
                """

            html_content += """
                </table>
            </body>
            </html>
            """

            document = QTextDocument()
            document.setHtml(html_content)
            document.print(printer)

        except Exception as e:
            QMessageBox.critical(self, "Yazdırma Hatası",
                               f"Yazdırma sırasında hata oluştu: {str(e)}")

    def export_to_pdf(self):
        """Borçlunun defterini PDF'ye aktar"""
        filename = f"{self.creditor.name}_defter.pdf"
        filepath = os.path.join(os.path.expanduser("~"), "Desktop", filename)

        try:
            # Yeni PDFGenerator sınıfını kullan
            self.pdf_generator.create_ledger_pdf(filepath, self.creditor.name, self.creditor.records)
            QMessageBox.information(self, "Dışa Aktarma Başarılı",
                                  f"Defter şu konuma aktarıldı: {filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Dışa Aktarma Hatası",
                               f"PDF dışa aktarma başarısız: {str(e)}")

    def create_pdf(self, filepath):
        """Eski fonksiyon - artık PDFGenerator kullanıyor"""
        self.pdf_generator.create_ledger_pdf(filepath, self.creditor.name, self.creditor.records)

    def create_receipt_pdf(self, record, receipt_number=None):
        """Tek bir kayıt için fiş formatında PDF oluştur"""
        # Fiş numarası oluştur
        if not receipt_number:
            receipt_number = f"B{record.id:011d}"
        filename = f"fis_{receipt_number}_{self.creditor.name}.pdf"
        filepath = os.path.join(os.path.expanduser("~"), "Desktop", filename)

        # Yeni PDFGenerator sınıfını kullan
        self.pdf_generator.create_receipt_pdf(filepath, self.creditor.name, record, receipt_number)
        return filepath

    def export_receipt_for_record(self):
        """Seçili kayıt için fiş çıktısı al"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Seçim Hatası", "Lütfen fiş çıktısı almak istediğiniz kaydı seçin!")
            return
        if current_row >= len(self.creditor.records):
            QMessageBox.warning(self, "Hata", "Geçersiz kayıt seçimi!")
            return
        record = self.creditor.records[current_row]

        try:
            filepath = self.create_receipt_pdf(record)
            QMessageBox.information(self, "Fiş Oluşturuldu",
                                  f"Fiş başarıyla oluşturuldu: {filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Fiş Oluşturma Hatası",
                               f"Fiş oluşturulurken hata: {str(e)}")

class ReceiptOptionsDialog(QDialog):
    """Fiş çıktısı için iskonto ve müşteri masrafı girişi"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Fiş Çıktısı Ayarları")
        self.setModal(True)
        self.resize(350, 180)
        layout = QFormLayout()
        font = QFont("Arial", 12)
        self.setFont(font)
        self.iskonto_spin = QDoubleSpinBox()
        self.iskonto_spin.setFont(font)
        self.iskonto_spin.setMinimum(0)
        self.iskonto_spin.setMaximum(9999999)
        self.iskonto_spin.setDecimals(2)
        self.iskonto_spin.setSuffix(" ₺")
        layout.addRow("İskonto Toplamı:", self.iskonto_spin)
        self.masraf_spin = QDoubleSpinBox()
        self.masraf_spin.setFont(font)
        self.masraf_spin.setMinimum(0)
        self.masraf_spin.setMaximum(9999999)
        self.masraf_spin.setDecimals(2)
        self.masraf_spin.setSuffix(" ₺")
        layout.addRow("Müşteri Masrafı:", self.masraf_spin)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.setFont(font)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        self.setLayout(layout)
    def get_values(self):
        return self.iskonto_spin.value(), self.masraf_spin.value()

class DatabaseSettingsDialog(QDialog):
    """Veritabanı ayarları ve yönetimi dialog'u"""
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("Veritabanı Ayarları")
        self.setModal(True)
        self.resize(600, 500)

        # Dialog fontunu ayarla
        dialog_font = QFont("Arial", 12)
        self.setFont(dialog_font)

        self.setup_ui()
        self.update_stats()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Başlık
        title = QLabel("Veritabanı Yönetimi")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # İstatistikler grubu
        stats_group = QGroupBox("Veritabanı İstatistikleri")
        stats_layout = QVBoxLayout()

        self.stats_label = QLabel()
        self.stats_label.setWordWrap(True)
        stats_layout.addWidget(self.stats_label)

        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        # Yedekleme grubu
        backup_group = QGroupBox("Yedekleme İşlemleri")
        backup_layout = QVBoxLayout()

        # Manuel yedek oluştur
        manual_backup_btn = QPushButton("Manuel Yedek Oluştur")
        manual_backup_btn.setMinimumHeight(35)
        manual_backup_btn.clicked.connect(self.create_manual_backup)
        backup_layout.addWidget(manual_backup_btn)

        # Eski yedekleri temizle
        cleanup_backups_layout = QHBoxLayout()
        cleanup_backups_btn = QPushButton("Eski Yedekleri Temizle")
        cleanup_backups_btn.setMinimumHeight(35)
        cleanup_backups_btn.clicked.connect(self.cleanup_old_backups)
        cleanup_backups_layout.addWidget(cleanup_backups_btn)

        self.backup_count_spin = QSpinBox()
        self.backup_count_spin.setMinimum(1)
        self.backup_count_spin.setMaximum(100)
        self.backup_count_spin.setValue(10)
        self.backup_count_spin.setSuffix(" adet sakla")
        cleanup_backups_layout.addWidget(self.backup_count_spin)

        backup_layout.addLayout(cleanup_backups_layout)
        backup_group.setLayout(backup_layout)
        layout.addWidget(backup_group)

        # Temizlik grubu
        cleanup_group = QGroupBox("Veritabanı Temizliği")
        cleanup_layout = QVBoxLayout()

        # Eski kayıtları temizle
        cleanup_records_layout = QHBoxLayout()
        cleanup_records_btn = QPushButton("Eski Kayıtları Temizle")
        cleanup_records_btn.setMinimumHeight(35)
        cleanup_records_btn.clicked.connect(self.cleanup_old_records)
        cleanup_records_layout.addWidget(cleanup_records_btn)

        self.days_spin = QSpinBox()
        self.days_spin.setMinimum(30)
        self.days_spin.setMaximum(3650)
        self.days_spin.setValue(365)
        self.days_spin.setSuffix(" günden eski")
        cleanup_records_layout.addWidget(self.days_spin)

        cleanup_layout.addLayout(cleanup_records_layout)
        cleanup_group.setLayout(cleanup_layout)
        layout.addWidget(cleanup_group)

        # JSON dışa aktarma
        export_group = QGroupBox("Dışa Aktarma")
        export_layout = QVBoxLayout()

        export_json_btn = QPushButton("Verileri JSON'a Aktar")
        export_json_btn.setMinimumHeight(35)
        export_json_btn.clicked.connect(self.export_to_json)
        export_layout.addWidget(export_json_btn)

        export_group.setLayout(export_layout)
        layout.addWidget(export_group)

        # İstatistikleri yenile butonu
        refresh_btn = QPushButton("İstatistikleri Yenile")
        refresh_btn.setMinimumHeight(35)
        refresh_btn.clicked.connect(self.update_stats)
        layout.addWidget(refresh_btn)

        # Kapat butonu
        close_btn = QPushButton("Kapat")
        close_btn.setMinimumHeight(35)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        self.setLayout(layout)

    def update_stats(self):
        """Veritabanı istatistiklerini güncelle"""
        try:
            stats = self.db_manager.get_database_stats()
            stats_text = f"""
Toplam Borçlu Sayısı: {stats['creditor_count']}
Toplam Kayıt Sayısı: {stats['record_count']}
Toplam Borç: ₺{stats['total_debt']:.2f}
Toplam Ödeme: ₺{stats['total_payment']:.2f}
Net Bakiye: ₺{stats['net_balance']:.2f}

Veritabanı Boyutu: {stats['db_size_mb']:.2f} MB
Son Güncelleme: {datetime.now().strftime('%d.%m.%Y %H:%M')}
            """.strip()
            self.stats_label.setText(stats_text)
        except Exception as e:
            self.stats_label.setText(f"İstatistik yüklenirken hata: {str(e)}")

    def create_manual_backup(self):
        """Manuel yedek oluştur"""
        try:
            backup_path = self.db_manager.create_backup("manual")
            if backup_path:
                QMessageBox.information(self, "Yedekleme Başarılı",
                                      f"Yedek başarıyla oluşturuldu!\n\n{backup_path}")
                self.update_stats()
            else:
                QMessageBox.warning(self, "Yedekleme Hatası",
                                  "Yedek oluşturulamadı!")
        except Exception as e:
            QMessageBox.critical(self, "Yedekleme Hatası",
                               f"Yedek oluşturulurken hata: {str(e)}")

    def cleanup_old_backups(self):
        """Eski yedekleri temizle"""
        keep_count = self.backup_count_spin.value()
        reply = QMessageBox.question(self, "Yedek Temizliği",
                                   f"En son {keep_count} yedek hariç diğerleri silinecek.\n"
                                   "Devam etmek istiyor musunuz?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            try:
                deleted_count = self.db_manager.cleanup_old_backups(keep_count)
                QMessageBox.information(self, "Temizlik Tamamlandı",
                                      f"{deleted_count} eski yedek dosyası silindi.")
                self.update_stats()
            except Exception as e:
                QMessageBox.critical(self, "Temizlik Hatası",
                                   f"Yedek temizliği sırasında hata: {str(e)}")

    def cleanup_old_records(self):
        """Eski kayıtları temizle"""
        keep_days = self.days_spin.value()
        cutoff_date = datetime.now() - timedelta(days=keep_days)

        reply = QMessageBox.question(self, "Kayıt Temizliği",
                                   f"{cutoff_date.strftime('%d.%m.%Y')} tarihinden önceki kayıtlar silinecek.\n"
                                   "Bu işlem geri alınamaz!\n\n"
                                   "Devam etmek istiyor musunuz?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Önce yedek oluştur
                backup_path = self.db_manager.create_backup("before_cleanup")
                if not backup_path:
                    QMessageBox.warning(self, "Yedekleme Hatası",
                                      "Güvenlik yedeği oluşturulamadı! İşlem iptal edildi.")
                    return

                deleted_count = self.db_manager.cleanup_old_records(keep_days)
                QMessageBox.information(self, "Temizlik Tamamlandı",
                                      f"{deleted_count} eski kayıt silindi.\n"
                                      f"Güvenlik yedeği: {backup_path}")
                self.update_stats()
            except Exception as e:
                QMessageBox.critical(self, "Temizlik Hatası",
                                   f"Kayıt temizliği sırasında hata: {str(e)}")

    def export_to_json(self):
        """Verileri JSON formatında dışa aktar"""
        try:
            filename = f"veresiye_defteri_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = os.path.join(os.path.expanduser("~"), "Desktop", filename)

            self.db_manager.export_to_json(filepath)
            QMessageBox.information(self, "Dışa Aktarma Başarılı",
                                  f"Veriler başarıyla dışa aktarıldı:\n\n{filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Dışa Aktarma Hatası",
                               f"JSON dışa aktarma sırasında hata: {str(e)}")

class DebtLedgerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        FontDownloader().setup_fonts()

        self.setWindowTitle("Veresiye Defteri Uygulaması")
        self.setGeometry(100, 100, 1400, 1000)

        self.setup_ui()
        self.update_creditor_list()

    # ---------- YARDIMCI METOTLAR ----------
    # DebtLedgerApp i��inde  ───────────────────────────────────────────────���
    def setup_ui(self):
        """Sol panel (butonlar + liste) ve sağ panel (stacked widget)"""
        central = QWidget();
        layout = QHBoxLayout(central)

        # --- Sol panel ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        title = QLabel("Borçlular")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        left_layout.addWidget(title)

        btn_font = QFont("Arial", 12)

        # Yeni borçlu ekle
        add_btn = QPushButton("Yeni Borçlu Ekle")
        add_btn.setFont(btn_font);
        add_btn.setMinimumHeight(40)
        add_btn.clicked.connect(self.add_creditor)
        left_layout.addWidget(add_btn)

        # Borçlu listesi
        self.creditor_list = QListWidget()
        self.creditor_list.setFont(QFont("Arial", 12))
        self.creditor_list.setStyleSheet("QListWidget::item { padding: 6px }")
        self.creditor_list.itemDoubleClicked.connect(self.show_creditor_details)
        left_layout.addWidget(self.creditor_list, 1)  # stretch

        # Seçili borçluyu sil
        del_btn = QPushButton("Seçili Borçluyu Sil")
        del_btn.setFont(btn_font);
        del_btn.setMinimumHeight(40)
        del_btn.clicked.connect(self.delete_creditor)
        left_layout.addWidget(del_btn)

        # Spacer
        left_layout.addStretch()

        # Veritabanı ayarları (yedek, temizlik)
        db_btn = QPushButton("Veritabanı Ayarları")
        db_btn.setFont(btn_font);
        db_btn.setMinimumHeight(40)
        db_btn.clicked.connect(self.show_database_settings)
        left_layout.addWidget(db_btn)

        layout.addWidget(left_panel, 0)  # sabit genişlik

        # --- Sağ panel (stacked widget) ---
        self.stacked_widget = QStackedWidget()
        main_page = QWidget()
        v = QVBoxLayout(main_page)
        welcome = QLabel("Veresiye Defteri'ne Hoş Geldiniz")
        welcome.setFont(QFont("Arial", 24));
        welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(welcome)
        info = QLabel("• Soldan borçlu ekleyin / seçin\n• Çift tıklayarak detaylara gidin")
        info.setFont(QFont("Arial", 14));
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(info);
        v.addStretch()
        self.stacked_widget.addWidget(main_page)  # index 0
        layout.addWidget(self.stacked_widget, 1)

        self.setCentralWidget(central)

    # ───────────────────────────────────────────────────────────────��──────

    # Yardımcı metotlar  (aynı sınıfa ekle) ───────────────────────────────
    def add_creditor(self):
        name, ok = QInputDialog.getText(self, "Borçlu Ekle", "Borçlu adını girin:")
        if ok and name.strip():
            if self.db_manager.add_creditor(name.strip()):
                self.update_creditor_list()
            else:
                QMessageBox.warning(self, "Hata", "Bu isimde borçlu zaten var!")

    def delete_creditor(self):
        item = self.creditor_list.currentItem()
        if not item: return
        name = item.text().split(" - ")[0]
        if QMessageBox.question(
                self, "Borçlu Sil",
                f"'{name}' ve tüm kayıtlarını silmek istediğinizden emin misiniz?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:

            data = self.db_manager.get_creditor_by_name(name)
            if data and self.db_manager.delete_creditor(data['id']):
                self.update_creditor_list()
                self.show_main_page()

    def show_database_settings(self):
        dlg = DatabaseSettingsDialog(self.db_manager, self)
        dlg.exec()
        self.update_creditor_list()

    # ─────────────────────────────────────────────────────────────────────

    def update_creditor_list(self):
        self.creditor_list.clear()
        for c in self.db_manager.get_all_creditors():
            total = c["total_debt"]
            self.creditor_list.addItem(f"{c['name']} - ₺{total:.2f}")

    def show_creditor_details(self, item):
        # Borçlu adı, listede "Ad - ₺tutar" formatında → adı al
        creditor_name = item.text().split(" - ")[0]
        creditor_data = self.db_manager.get_creditor_by_name(creditor_name)
        if not creditor_data:
            QMessageBox.warning(self, "Hata", "Borçlu bulunamadı!")
            return

        # Daha önce eklenmiş detay sayfasını temizle
        while self.stacked_widget.count() > 1:
            old = self.stacked_widget.widget(1)
            self.stacked_widget.removeWidget(old)
            old.deleteLater()

        # Yeni detay sayfasını ekle
        creditor = Creditor(creditor_data["id"], creditor_data["name"], self.db_manager)
        detail_widget = CreditorDetailWidget(creditor, self)
        self.stacked_widget.addWidget(detail_widget)
        self.stacked_widget.setCurrentWidget(detail_widget)

    def show_main_page(self):
        self.stacked_widget.setCurrentIndex(0)
