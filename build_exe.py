import os
import subprocess
import sys
import shutil

def install_pyinstaller():
    """PyInstaller'ı yükle"""
    print("PyInstaller kuruluyor...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    print("✅ PyInstaller başarıyla kuruldu!")

def check_fonts():
    """Font dosyalarının varlığını kontrol et"""
    fonts_dir = "fonts"
    required_fonts = [
        "Roboto-Regular.ttf",
        "Roboto-Bold.ttf",
        "NotoSans-Regular.ttf",
        "NotoSans-Bold.ttf",
        "OpenSans-Regular.ttf",
        "OpenSans-Bold.ttf"
    ]

    missing_fonts = []
    for font in required_fonts:
        font_path = os.path.join(fonts_dir, font)
        if not os.path.exists(font_path):
            missing_fonts.append(font)

    if missing_fonts:
        print(f"⚠️ Eksik fontlar: {', '.join(missing_fonts)}")
        return False
    else:
        print("✅ Tüm fontlar mevcut")
        return True

def create_exe():
    """EXE dosyası oluştur"""
    print("\n🚀 EXE dosyası oluşturuluyor...")

    # Font kontrolü
    if not check_fonts():
        print("❌ Fontlar eksik! Önce fontları indirin.")
        return False

    # Windows için ayraç karakteri
    sep = ";" if sys.platform.startswith("win") else ":"

    # PyInstaller komutunu oluştur
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",  # Tek dosya halinde
        "--windowed",  # Windows GUI uygulaması (konsol penceresi açılmasın)
        "--name=VeresiyeDefteri",  # EXE dosya adı
        "--icon=icon.png",  # İkon dosyası
        "--clean",  # Önceki build dosyalarını temizle
        "--noconfirm",  # Onay istemeden üzerine yaz

        # Daha iyi bir yol belirtme yaklaşımı
        f"--add-data=fonts{sep}fonts",

        # Gerekli modülleri dahil et
        "--hidden-import=PyQt6",
        "--hidden-import=PyQt6.QtCore",
        "--hidden-import=PyQt6.QtGui",
        "--hidden-import=PyQt6.QtWidgets",
        "--hidden-import=PyQt6.QtPrintSupport",
        "--hidden-import=reportlab",
        "--hidden-import=reportlab.pdfgen",
        "--hidden-import=reportlab.pdfgen.canvas",
        "--hidden-import=reportlab.lib.pagesizes",
        "--hidden-import=reportlab.pdfbase",
        "--hidden-import=reportlab.pdfbase.pdfmetrics",
        "--hidden-import=reportlab.pdfbase.ttfonts",
        "--hidden-import=reportlab.lib.fonts",
        "--hidden-import=sqlite3",

        # Gereksiz modülleri hariç tut
        "--exclude-module=tkinter",
        "--exclude-module=matplotlib",
        "--exclude-module=scipy",
        "--exclude-module=numpy",

        # Ana dosya
        "debt_ledger.py"
    ]

    try:
        subprocess.check_call(cmd)
        print("✅ EXE dosyası başarıyla oluşturuldu!")
        print("📁 EXE dosyası: dist/VeresiyeDefteri.exe")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ EXE oluşturma hatası: {e}")
        return False

def clean_build_files():
    """Build klasörlerini temizle"""
    dirs_to_clean = ["build", "dist", "__pycache__"]
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"🗑️ {dir_name} klasörü temizlendi")

def main():
    """Ana fonksiyon"""
    print("🔧 Veresiye Defteri EXE Builder")
    print("=" * 40)

    # PyInstaller kurulu mu kontrol et
    try:
        subprocess.check_call(["pyinstaller", "--version"],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
        print("✅ PyInstaller zaten kurulu")
    except (subprocess.CalledProcessError, FileNotFoundError):
        install_pyinstaller()

    # Fontları kontrol et ve indir
    if not check_fonts():
        print("\n📥 Fontlar indiriliyor...")
        try:
            import download_fonts
            download_fonts.main()
        except Exception as e:
            print(f"❌ Font indirme hatası: {e}")
            print("Manuel olarak download_fonts.py çalıştırın")
            return

    # Önceki build dosyalarını temizle
    clean_build_files()

    # EXE oluştur
    if create_exe():
        print("\n🎉 Başarılı! EXE dosyası hazır.")
        print("📋 Test etmek için dist/VeresiyeDefteri.exe dosyasını çalıştırın")
    else:
        print("\n❌ EXE oluşturma başarısız!")

if __name__ == "__main__":
    main()
