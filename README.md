# 📋 Veresiye Defteri Uygulaması

Modern ve kullanıcı dostu bir veresiye/borç takip uygulaması. SQLite veritabanı ile güvenli veri saklama, PDF çıktıları ve gelişmiş arama özellikleri sunar.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![PyQt6](https://img.shields.io/badge/PyQt6-GUI-green.svg)
![SQLite](https://img.shields.io/badge/SQLite-Database-orange.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ Özellikler

### 🔍 **Gelişmiş Arama**
- **Anında filtreleme**: Yazdığınız her karakterde borçluları filtreler
- **Büyük/küçük harf duyarsız**: "ali" yazarak "Ali" veya "ALİ" bulabilirsiniz
- **Türkçe karakter desteği**: ç, ğ, ı, ö, ş, ü karakterleri desteklenir

### 💰 **Borç Yönetimi**
- Borç ve ödeme kayıtları
- Otomatik bakiye hesaplama
- Tarihli işlem geçmişi
- Detaylı açıklama alanları

### 📄 **PDF Çıktıları**
- **Fiş formatında** tekil kayıt çıktısı
- **Defter formatında** tüm kayıtlar
- Türkçe karakter desteği
- Profesyonel görünüm

### 🔒 **Güvenli Veri Saklama**
- SQLite veritabanı
- Otomatik yedekleme sistemi
- Manuel yedek oluşturma
- JSON export özelliği

### 🖨️ **Yazdırma Desteği**
- Doğrudan yazıcı desteği
- HTML tablosu formatı
- Yazdırma önizleme

## 🚀 Kurulum

### Gereksinimler
```bash
Python 3.8 veya üzeri
PyQt6
ReportLab (PDF oluşturma için)
```

### Adım 1: Depoyu klonlayın
```bash
git clone https://github.com/aliosmangurbilek/debt_ledger.git
cd veresiye-defteri
```

### Adım 2: Gerekli paketleri yükleyin
```bash
pip install -r requirements.txt
```

### Adım 3: Uygulamayı çalıştırın
```bash
python main.py
```

## 📱 Kullanım

### 🔍 **Borçlu Arama**
1. Sol paneldeki **"Borçlu Ara:"** kutusuna yazın
2. Liste otomatik olarak filtrelenir
3. Arama kutusunu temizleyince tüm borçlular görünür

### 👤 **Yeni Borçlu Ekleme**
1. **"Yeni Borçlu Ekle"** butonuna tıklayın
2. İsim girin ve onaylayın
3. Borçlu listeye eklenir

### 💳 **Kayıt İşlemleri**
1. Listeden borçluya **çift tıklayın**
2. **"Kayıt Ekle"** butonuna tıklayın
3. Formu doldurun:
   - **Tarih**: İşlem tarihi
   - **Açıklama**: İşlem açıklaması
   - **Kod1/Kod2**: Ürün/hizmet kodları
   - **Birim**: Adet, KG, M2 vb.
   - **Tür**: Borç veya Ödeme
   - **Tutar**: Miktar

### 📄 **PDF Çıktısı**
- **Defter PDF'i**: Tüm kayıtları içeren detaylı rapor
- **Fiş PDF'i**: Seçili kayıt için fiş formatı
- Desktop klasörüne otomatik kaydedilir

## 🗂️ Proje Yapısı

```
veresiye_defteri/
├── main.py                 # Ana uygulama başlatıcı
├── debt_ledger.py         # Ana uygulama sınıfları
├── database_manager.py    # Veritabanı yönetimi
├── download_fonts.py      # Font yönetimi
├── build_exe.py          # Executable oluşturucu
├── requirements.txt       # Python bağımlılıkları
├── icon.png              # Uygulama ikonu
├── README.md             # Dokümantasyon
├── veresiye_defteri.db   # SQLite veritabanı
├── backups/              # Otomatik yedekler
└── fonts/                # Font dosyaları
```

## 🗄️ Veritabanı Yapısı

### **creditors** tablosu
```sql
CREATE TABLE creditors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### **records** tablosu
```sql
CREATE TABLE records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    creditor_id INTEGER,
    date TEXT NOT NULL,
    description TEXT NOT NULL,
    debt_amount REAL DEFAULT 0,
    payment_amount REAL DEFAULT 0,
    payment_status TEXT DEFAULT 'Ödenmedi',
    remaining_debt REAL DEFAULT 0,
    kod1 TEXT DEFAULT '',
    kod2 TEXT DEFAULT '',
    birim TEXT DEFAULT '',
    iskonto REAL DEFAULT 0,
    musteri_masrafi REAL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (creditor_id) REFERENCES creditors (id)
);
```

## ⚙️ Ayarlar ve Yapılandırma

### **Veritabanı Ayarları**
- **Manuel Yedek**: İstediğiniz zaman yedek oluşturun
- **Eski Yedekleri Temizle**: Disk alanı tasarrufu için
- **Eski Kayıtları Temizle**: Belirtilen günden eski kayıtları sil
- **JSON Export**: Verileri JSON formatında dışa aktarın

### **Font Ayarları**
Uygulama Linux sistem fontlarını otomatik algılar:
1. Liberation Sans (Linux varsayılan)
2. DejaVu Sans (Yaygın Linux fontu)
3. Ubuntu (Ubuntu sistemler)
4. Noto Sans (Evrensel destek)
5. Arial/Helvetica (Fallback)

## 🔧 Geliştirme

### **Yeni Özellik Ekleme**
```python
# debt_ledger.py dosyasında yeni sınıflar oluşturun
class YeniOzellik(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()
```

### **Veritabanı Migrasyonu**
```python
# database_manager.py dosyasında
def migrate_database(self):
    # Yeni tablo veya sütun ekleyin
    pass
```

## 🐛 Sorun Giderme

### **Font Sorunları**
```bash
# Sistem fontlarını kontrol edin
fc-list | grep -i "liberation\|dejavu\|ubuntu"

# Eksikse font paketlerini yükleyin
sudo apt install fonts-liberation fonts-dejavu
```

### **PDF Oluşturma Hataları**
```bash
# ReportLab yeniden yükleyin
pip uninstall reportlab
pip install reportlab
```

### **Veritabanı Hataları**
```bash
# Yedekten geri yükleyin
cp backups/en_son_yedek.db veresiye_defteri.db
```

## 🤝 Katkıda Bulunma

1. **Fork** edin
2. **Feature branch** oluşturun (`git checkout -b feature/yeni-ozellik`)
3. **Commit** edin (`git commit -am 'Yeni özellik: açıklama'`)
4. **Push** edin (`git push origin feature/yeni-ozellik`)
5. **Pull Request** oluşturun

## 📈 Sürüm Geçmişi

### v1.0.0 (Mevcut)
- ✅ Temel borç takip sistemi
- ✅ SQLite veritabanı desteği
- ✅ PDF çıktı özellikleri
- ✅ Gelişmiş arama sistemi
- ✅ Otomatik yedekleme
- ✅ Türkçe karakter desteği

### Gelecek Güncellemeler
- 🔄 Excel import/export
- 🔄 Grafik raporlar
- 🔄 Email bildirimleri
- 🔄 Çoklu dil desteği

## 📞 Destek

Sorunlarınız için:
- **Issues**: GitHub Issues sayfasını kullanın
- **Dokümantasyon**: Bu README dosyasını inceleyin
- **Email**: [aliosmangurbil@gmail.com](mailto:destek@example.com)

---

**Geliştirici**: Ali  
**Proje**: Veresiye Defteri Uygulaması  
**Tarih**: Temmuz 2025  
**Versiyon**: 1.0.0  

*İş hayatınızı kolaylaştıran modern borç takip sistemi* 📊✨
