"""
Veritabanı yönetimi ve yedekleme sistemi
"""
import sqlite3
import json
import os
import shutil
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

class DatabaseManager:
    """SQLite veritabanı yönetimi ve yedekleme sistemi"""
    
    def __init__(self, db_path: str = "veresiye_defteri.db", backup_dir: str = "D:/yedek/veresiye_defteri"):
        self.db_path = db_path
        self.backup_dir = backup_dir
        self.ensure_backup_directory()
        self.init_database()
    
    def ensure_backup_directory(self):
        """Yedek klasörünün var olduğundan emin ol"""
        try:
            os.makedirs(self.backup_dir, exist_ok=True)
        except Exception as e:
            print(f"Yedek klasörü oluşturulamadı: {e}")
    
    def init_database(self):
        """Veritabanını başlat ve tabloları oluştur"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Borçlular tablosu
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS creditors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Kayıtlar tablosu
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    creditor_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    description TEXT NOT NULL,
                    debt_amount REAL DEFAULT 0.0,
                    payment_amount REAL DEFAULT 0.0,
                    payment_status TEXT DEFAULT 'Ödenmedi',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (creditor_id) REFERENCES creditors (id) ON DELETE CASCADE
                )
            ''')
            
            # İndeksler oluştur
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_creditor_id ON records(creditor_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_date ON records(date)')
            
            conn.commit()
    
    def create_backup(self, operation_type: str = "manual"):
        """Veritabanının yedeğini oluştur"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"veresiye_defteri_backup_{timestamp}_{operation_type}.db"
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            # Veritabanı dosyasını kopyala
            shutil.copy2(self.db_path, backup_path)
            
            # JSON formatında da yedek oluştur
            json_backup_path = backup_path.replace('.db', '.json')
            self.export_to_json(json_backup_path)
            
            # Eski yedekleri temizle (son 10 yedek hariç)
            self.cleanup_old_backups()
            
            print(f"✅ Yedek oluşturuldu: {backup_filename}")
            return backup_path
            
        except Exception as e:
            print(f"❌ Yedek oluşturulamadı: {e}")
            return None
    
    def cleanup_old_backups(self, keep_count: int = 10):
        """Eski yedekleri temizle"""
        try:
            if not os.path.exists(self.backup_dir):
                return
                
            # Yedek dosyalarını listele
            backup_files = [f for f in os.listdir(self.backup_dir) 
                          if f.startswith('veresiye_defteri_backup_') and f.endswith('.db')]
            
            # Tarihe göre sırala (en yeni önce)
            backup_files.sort(reverse=True)
            
            # Fazla olanları sil
            deleted_count = 0
            for old_backup in backup_files[keep_count:]:
                old_path = os.path.join(self.backup_dir, old_backup)
                os.remove(old_path)
                deleted_count += 1

                # JSON yedeğini de sil
                json_path = old_path.replace('.db', '.json')
                if os.path.exists(json_path):
                    os.remove(json_path)
                    
            if deleted_count > 0:
                print(f"🗑️ {deleted_count} eski yedek dosyası temizlendi")

        except Exception as e:
            print(f"Eski yedekler temizlenirken hata: {e}")
    
    def cleanup_old_records(self, keep_days: int = 365):
        """Eski kayıtları temizle - sadece son X gün tutulsun"""
        try:
            cutoff_date = datetime.now() - timedelta(days=keep_days)
            cutoff_date_str = cutoff_date.strftime('%Y-%m-%d')

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Silinecek kayıtları say
                cursor.execute('''
                    SELECT COUNT(*) FROM records 
                    WHERE date < ? AND created_at < ?
                ''', (cutoff_date_str, cutoff_date.isoformat()))

                old_count = cursor.fetchone()[0]

                if old_count > 0:
                    # Eski kayıtları sil
                    cursor.execute('''
                        DELETE FROM records 
                        WHERE date < ? AND created_at < ?
                    ''', (cutoff_date_str, cutoff_date.isoformat()))

                    # Hiç kaydı kalmayan borçluları sil
                    cursor.execute('''
                        DELETE FROM creditors 
                        WHERE id NOT IN (SELECT DISTINCT creditor_id FROM records)
                    ''')

                    deleted_creditors = cursor.rowcount

                    conn.commit()

                    print(f"🗑️ {old_count} eski kayıt temizlendi")
                    if deleted_creditors > 0:
                        print(f"🗑️ {deleted_creditors} boş borçlu kaydı temizlendi")

                    # Temizlik sonrası yedek oluştur
                    self.create_backup("cleanup")

                    return old_count

        except Exception as e:
            print(f"Eski kayıtlar temizlenirken hata: {e}")
            return 0

    def export_to_json(self, json_path: str):
        """Veritabanını JSON formatında dışa aktar"""
        try:
            data = {
                'export_date': datetime.now().isoformat(),
                'creditors': []
            }
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Tüm borçluları al
                cursor.execute('SELECT id, name, created_at FROM creditors ORDER BY name')
                creditors = cursor.fetchall()
                
                for creditor_id, name, created_at in creditors:
                    # Borçlunun kayıtlarını al
                    cursor.execute('''
                        SELECT date, description, debt_amount, payment_amount, payment_status, created_at
                        FROM records 
                        WHERE creditor_id = ? 
                        ORDER BY date, created_at
                    ''', (creditor_id,))
                    
                    records = cursor.fetchall()
                    
                    creditor_data = {
                        'id': creditor_id,
                        'name': name,
                        'created_at': created_at,
                        'records': [
                            {
                                'date': record[0],
                                'description': record[1],
                                'debt_amount': record[2],
                                'payment_amount': record[3],
                                'payment_status': record[4],
                                'created_at': record[5]
                            }
                            for record in records
                        ]
                    }
                    
                    data['creditors'].append(creditor_data)
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"JSON dışa aktarma hatası: {e}")
    
    def add_creditor(self, name: str) -> Optional[int]:
        """Yeni borçlu ekle"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('INSERT INTO creditors (name) VALUES (?)', (name,))
                creditor_id = cursor.lastrowid
                conn.commit()
                
                # İşlem sonrası yedek oluştur
                self.create_backup("add_creditor")
                
                return creditor_id
        except sqlite3.IntegrityError:
            return None  # Aynı isimde borçlu var
        except Exception as e:
            print(f"Borçlu ekleme hatası: {e}")
            return None
    
    def delete_creditor(self, creditor_id: int) -> bool:
        """Borçluyu sil"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM creditors WHERE id = ?', (creditor_id,))
                success = cursor.rowcount > 0
                conn.commit()
                
                if success:
                    # İşlem sonrası yedek oluştur
                    self.create_backup("delete_creditor")
                
                return success
        except Exception as e:
            print(f"Borçlu silme hatası: {e}")
            return False
    
    def add_record(self, creditor_id: int, date: str, description: str, 
                   debt_amount: float = 0.0, payment_amount: float = 0.0, 
                   payment_status: str = 'Ödenmedi') -> Optional[int]:
        """Yeni kayıt ekle"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO records (creditor_id, date, description, debt_amount, payment_amount, payment_status)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (creditor_id, date, description, debt_amount, payment_amount, payment_status))
                
                record_id = cursor.lastrowid
                
                # Borçlunun updated_at'ini güncelle
                cursor.execute('UPDATE creditors SET updated_at = CURRENT_TIMESTAMP WHERE id = ?', (creditor_id,))
                
                conn.commit()
                
                # İşlem sonrası yedek oluştur
                self.create_backup("add_record")
                
                return record_id
        except Exception as e:
            print(f"Kay��t ekleme hatası: {e}")
            return None
    
    def get_all_creditors(self) -> List[Dict[str, Any]]:
        """Tüm borçluları getir"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT c.id, c.name, c.created_at, c.updated_at,
                           COALESCE(SUM(r.debt_amount - r.payment_amount), 0) as total_debt,
                           COUNT(r.id) as record_count
                    FROM creditors c
                    LEFT JOIN records r ON c.id = r.creditor_id
                    GROUP BY c.id, c.name, c.created_at, c.updated_at
                    ORDER BY c.name
                ''')
                
                creditors = []
                for row in cursor.fetchall():
                    creditors.append({
                        'id': row[0],
                        'name': row[1],
                        'created_at': row[2],
                        'updated_at': row[3],
                        'total_debt': row[4],
                        'record_count': row[5]
                    })
                
                return creditors
        except Exception as e:
            print(f"Borçlular getirme hatası: {e}")
            return []
    
    def get_creditor_records(self, creditor_id: int) -> List[Dict[str, Any]]:
        """Belirli bir borçlunun kayıtlarını getir"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, date, description, debt_amount, payment_amount, payment_status, created_at
                    FROM records 
                    WHERE creditor_id = ? 
                    ORDER BY date, created_at
                ''', (creditor_id,))
                
                records = []
                running_debt = 0.0
                
                for row in cursor.fetchall():
                    running_debt += row[3] - row[4]  # debt_amount - payment_amount
                    
                    records.append({
                        'id': row[0],
                        'date': row[1],
                        'description': row[2],
                        'debt_amount': row[3],
                        'payment_amount': row[4],
                        'payment_status': row[5],
                        'created_at': row[6],
                        'remaining_debt': running_debt
                    })
                
                return records
        except Exception as e:
            print(f"Kayıtları getirme hatası: {e}")
            return []
    
    def get_creditor_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """İsme göre borçlu getir"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id, name, created_at, updated_at FROM creditors WHERE name = ?', (name,))
                row = cursor.fetchone()
                
                if row:
                    return {
                        'id': row[0],
                        'name': row[1],
                        'created_at': row[2],
                        'updated_at': row[3]
                    }
                return None
        except Exception as e:
            print(f"Borçlu arama hatası: {e}")
            return None
    
    def migrate_from_json(self, json_file: str) -> bool:
        """JSON dosyasından veritabanına geçiş yap"""
        try:
            if not os.path.exists(json_file):
                return False
                
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            creditors_data = data.get('creditors', [])
            
            for creditor_data in creditors_data:
                # Borçluyu ekle
                creditor_id = self.add_creditor(creditor_data['name'])
                if not creditor_id:
                    # Zaten varsa ID'sini al
                    existing = self.get_creditor_by_name(creditor_data['name'])
                    if existing:
                        creditor_id = existing['id']
                    else:
                        continue
                
                # Kayıtları ekle
                for record in creditor_data.get('records', []):
                    self.add_record(
                        creditor_id=creditor_id,
                        date=record['date'],
                        description=record['description'],
                        debt_amount=record['debt_amount'],
                        payment_amount=record['payment_amount'],
                        payment_status=record['payment_status']
                    )
            
            print("✅ JSON'dan veritabanına geçiş tamamlandı")
            return True
            
        except Exception as e:
            print(f"JSON geçiş hatası: {e}")
            return False

    def get_database_stats(self):
        """Veritabanı istatistiklerini getir"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Toplam borçlu sayısı
                cursor.execute('SELECT COUNT(*) FROM creditors')
                creditor_count = cursor.fetchone()[0]

                # Toplam kayıt sayısı
                cursor.execute('SELECT COUNT(*) FROM records')
                record_count = cursor.fetchone()[0]

                # En eski kayıt tarihi
                cursor.execute('SELECT MIN(date) FROM records')
                oldest_date = cursor.fetchone()[0]

                # En yeni kayıt tarihi
                cursor.execute('SELECT MAX(date) FROM records')
                newest_date = cursor.fetchone()[0]

                # Veritabanı dosya boyutu
                db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0

                return {
                    'creditor_count': creditor_count,
                    'record_count': record_count,
                    'oldest_date': oldest_date,
                    'newest_date': newest_date,
                    'db_size_mb': db_size / (1024 * 1024),
                    'backup_count': len([f for f in os.listdir(self.backup_dir)
                                       if f.endswith('.db')]) if os.path.exists(self.backup_dir) else 0
                }

        except Exception as e:
            print(f"İstatistik alınırken hata: {e}")
            return None
