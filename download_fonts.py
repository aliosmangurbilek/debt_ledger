#!/usr/bin/env python3
"""
Font İndirme Modülü
Türkçe karakterleri destekleyen fontları Google Fonts'tan indirir.
"""

import os
import requests
from pathlib import Path
import sys
import shutil

class FontDownloader:
    """Google Fonts'tan font indirme sınıfı"""

    def __init__(self):
        # Ensure fonts directory is next to this script
        self.fonts_dir = Path(__file__).parent / 'fonts'
        self.fonts_dir.mkdir(exist_ok=True)

        # Google Fonts API kullanarak font listesi
        self.fonts = {
            "Roboto": {
                "api_url": "https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap",
                "files": ["Roboto-Regular.ttf", "Roboto-Bold.ttf"]
            },
            "Open Sans": {
                "api_url": "https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;700&display=swap",
                "files": ["OpenSans-Regular.ttf", "OpenSans-Bold.ttf"]
            },
            "Noto Sans": {
                "api_url": "https://fonts.googleapis.com/css2?family=Noto+Sans:wght@400;700&display=swap",
                "files": ["NotoSans-Regular.ttf", "NotoSans-Bold.ttf"]
            }
        }
        # Sistem fontları listesi ve dizin ayarları
        self.system_fonts = [
            "Segoe UI", "Tahoma", "Arial", "Calibri", "Verdana"
        ]
        self.windows_fonts_dir = Path(os.environ.get("WINDIR", "C:\\Windows")) / "Fonts"
        # Görünen isimden dosya adına dönüşüm
        self.system_font_filenames = {name: name.replace(" ", "") + ".ttf" for name in self.system_fonts}
        # Sistem fontları fonts sözlüğüne ekle
        for name, filename in self.system_font_filenames.items():
            self.fonts[name] = {"files": [filename]}

    def validate_font_file(self, file_path):
        """Font dosyasının geçerli bir TrueType font olup olmadığını kontrol et"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(4)
                # TrueType, OpenType veya WOFF formatlarını kontrol et
                if header == b'\x00\x01\x00\x00':  # TrueType
                    return True
                elif header == b'OTTO':  # OpenType
                    return True
                elif header == b'wOFF':  # WOFF
                    return True
                else:
                    print(f"⚠️ {file_path} geçersiz font formatı: {header.hex()}")
                    return False
        except Exception as e:
            print(f"⚠️ {file_path} doğrulama hatası: {e}")
            return False

    def download_font_from_github(self, font_name):
        """GitHub'dan font indir (alternatif yöntem)"""
        github_urls = {
            "Roboto": [
                "https://github.com/google/fonts/raw/main/apache/roboto/Roboto-Regular.ttf",
                "https://github.com/google/fonts/raw/main/apache/roboto/Roboto-Bold.ttf"
            ],
            "Open Sans": [
                "https://github.com/google/fonts/raw/main/apache/opensans/OpenSans%5Bwdth,wght%5D.ttf"
            ],
            "Noto Sans": [
                "https://github.com/google/fonts/raw/main/ofl/notosans/NotoSans%5Bwdth,wght%5D.ttf"
            ]
        }

        # Alternatif URL'ler - eğer GitHub çalışmazsa
        fallback_urls = {
            "Roboto": [
                "https://fonts.gstatic.com/s/roboto/v30/KFOmCnqEu92Fr1Mu4mxKKTU1Kg.woff2",
                "https://fonts.gstatic.com/s/roboto/v30/KFOlCnqEu92Fr1MmEU9fBBc4AMP6lQ.woff2"
            ]
        }

        if font_name not in github_urls:
            return False

        success = True

        # Önce GitHub'dan deneyelim
        for url in github_urls[font_name]:
            filename = self._get_filename_from_url(url, font_name)
            try:
                print(f"İndiriliyor: {url}")
                response = requests.get(url, stream=True, timeout=30)
                response.raise_for_status()

                file_path = self.fonts_dir / filename

                # Geçici dosya olarak indir
                temp_path = file_path.with_suffix('.tmp')

                with open(temp_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

                # Dosya boyutunu kontrol et
                file_size = temp_path.stat().st_size
                if file_size < 10000:  # 10KB'den küçükse muhtemelen hata sayfası
                    print(f"✗ {filename} çok küçük ({file_size} bytes), siliniyor")
                    temp_path.unlink()
                    continue

                # Font dosyasını doğrula
                if self.validate_font_file(temp_path):
                    # Eski dosyayı sil (varsa)
                    if file_path.exists():
                        file_path.unlink()
                    # Geçici dosyayı gerçek isme taşı
                    temp_path.rename(file_path)
                    print(f"✓ {filename} başarıyla indirildi ({file_size} bytes)")
                    return True  # En az bir font indirildiyse başarılı
                else:
                    print(f"✗ {filename} geçersiz font dosyası!")
                    temp_path.unlink()

            except Exception as e:
                print(f"✗ {filename} indirilemedi: {e}")
                continue

        # GitHub başarısızsa sistem fontlarını kullan
        print(f"⚠️ {font_name} indirilemedi, sistem fontları kullanılacak")
        return False

    def _get_filename_from_url(self, url, font_name):
        """URL'den dosya adını çıkar"""
        if "Roboto" in url:
            if "Regular" in url or "KFOmCnqEu92Fr1Mu4mxKKTU1Kg" in url:
                return "Roboto-Regular.ttf"
            elif "Bold" in url or "KFOlCnqEu92Fr1MmEU9fBBc4AMP6lQ" in url:
                return "Roboto-Bold.ttf"
        elif "opensans" in url.lower() or "Open" in font_name:
            return "OpenSans-Regular.ttf"
        elif "notosans" in url.lower() or "Noto" in font_name:
            return "NotoSans-Regular.ttf"

        # Varsayılan
        return url.split("/")[-1].replace("%5B", "[").replace("%5D", "]")

    def download_font(self, font_name, font_info):
        """Tek bir font ailesini indir"""
        print(f"{font_name} fontu indiriliyor...")
        return self.download_font_from_github(font_name)

    def download_all_fonts(self):
        """Tüm fontları indir"""
        print("Türkçe karakterleri destekleyen fontlar indiriliyor...")
        print("=" * 50)

        success_count = 0
        total_count = len(self.fonts)

        for font_name, font_info in self.fonts.items():
            if self.download_font(font_name, font_info):
                success_count += 1

        print("=" * 50)
        print(f"İndirme tamamlandı: {success_count}/{total_count} font başarıyla indirildi")

        return success_count == total_count

    def check_fonts_exist(self):
        """Fontların mevcut olup olmadığını kontrol et"""
        missing_fonts = []

        for font_name, font_info in self.fonts.items():
            for font_file in font_info["files"]:
                font_path = self.fonts_dir / font_file
                if not font_path.exists():
                    missing_fonts.append(f"{font_name}: {font_file}")

        return missing_fonts

    def copy_system_fonts(self):
        """Sistem fontlarını yerel Windows Fonts klasöründen kopyala"""
        print("Sistem fontları kopyalanıyor...")
        for name, filename in self.system_font_filenames.items():
            src = self.windows_fonts_dir / filename
            dst = self.fonts_dir / filename
            if src.exists() and not dst.exists():
                try:
                    shutil.copy(src, dst)
                    print(f"✓ {filename} kopyalandı")
                except Exception as e:
                    print(f"✗ {filename} kopyalanamadı: {e}")

    def setup_fonts(self):
        """Fontları kontrol et, sistem fontlarını kopyala ve gerekirse indir"""
        missing_fonts = self.check_fonts_exist()
        if missing_fonts:
            # Öncelikle sistem fontlarını kopyalayalım
            self.copy_system_fonts()
            missing_fonts = self.check_fonts_exist()

        if missing_fonts:
            print(f"Eksik fontlar tespit edildi: {len(missing_fonts)} dosya")
            self.download_all_fonts()
        else:
            print("Tüm fontlar mevcut ✓")

def main():
    """Ana fonksiyon"""
    downloader = FontDownloader()

    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        missing = downloader.check_fonts_exist()
        if missing:
            print("Eksik fontlar:")
            for font in missing:
                print(f"  - {font}")
            sys.exit(1)
        else:
            print("Tüm fontlar mevcut ✓")
            sys.exit(0)

    downloader.setup_fonts()

if __name__ == "__main__":
    main()
