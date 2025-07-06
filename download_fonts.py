#!/usr/bin/env python3
"""
Font Ayarlama Modülü - Basitleştirilmiş Versiyon
Sistem fontlarını kullanır, internet gerektirmez.
"""

import os
from pathlib import Path
import shutil

class FontDownloader:
    """Basitleştirilmiş font yöneticisi - sistem fontlarını kullanır"""

    def __init__(self):
        self.fonts_dir = Path(__file__).parent / 'fonts'
        self.fonts_dir.mkdir(exist_ok=True)

        # Sistem font dizinleri (Linux)
        self.system_font_paths = [
            "/usr/share/fonts/truetype/",
            "/usr/share/fonts/TTF/",
            "/usr/local/share/fonts/",
            "/usr/share/fonts/opentype/",
            "~/.fonts/",
            "~/.local/share/fonts/"
        ]

    def setup_fonts(self):
        """Font ayarlarını yap - basit ve güvenilir"""
        try:
            print("Font sistemi hazırlanıyor...")

            # Zaten mevcut fontları kontrol et
            existing_fonts = list(self.fonts_dir.glob("*.ttf"))
            if existing_fonts:
                print(f"✓ {len(existing_fonts)} font mevcut: {[f.name for f in existing_fonts]}")
                return True

            # Sistem fontlarından kopyala (opsiyonel)
            self._copy_system_fonts()

            print("✓ Font sistemi hazır")
            return True

        except Exception as e:
            print(f"⚠️ Font ayarlama uyarısı: {e}")
            print("⚠️ Sistem varsayılan fontları kullanılacak")
            return False

    def _copy_system_fonts(self):
        """Sistem fontlarından bazılarını kopyala (opsiyonel)"""
        try:
            # Yaygın Linux font isimlerini ara
            font_patterns = [
                "DejaVu*Sans*.ttf",
                "Liberation*Sans*.ttf",
                "Ubuntu*.ttf",
                "Noto*Sans*.ttf"
            ]

            copied_count = 0
            for font_path in self.system_font_paths:
                expanded_path = Path(font_path).expanduser()
                if not expanded_path.exists():
                    continue

                for pattern in font_patterns:
                    for font_file in expanded_path.rglob(pattern):
                        if font_file.is_file() and copied_count < 3:  # Maksimum 3 font kopyala
                            try:
                                dest = self.fonts_dir / font_file.name
                                if not dest.exists():
                                    shutil.copy2(font_file, dest)
                                    print(f"✓ {font_file.name} kopyalandı")
                                    copied_count += 1
                            except Exception as e:
                                continue

            if copied_count == 0:
                print("⚠️ Sistem fontları bulunamadı, varsayılan fontlar kullanılacak")

        except Exception as e:
            print(f"⚠️ Sistem font kopyalama hatası: {e}")

    def get_available_fonts(self):
        """Kullanılabilir fontları listele"""
        fonts = list(self.fonts_dir.glob("*.ttf"))
        return [f.stem for f in fonts]

def main():
    """Ana fonksiyon"""
    downloader = FontDownloader()
    downloader.setup_fonts()

if __name__ == "__main__":
    main()
