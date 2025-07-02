#!/usr/bin/env python3
"""
Windows için .exe oluşturma scripti
"""

import os
import subprocess
import sys

def install_pyinstaller():
    """PyInstaller'ı yükle"""
    print("PyInstaller kuruluyor...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    print("✅ PyInstaller başarıyla kuruldu!")

def create_exe():
    """EXE dosyası oluştur"""
    print("\n🚀 EXE dosyası oluşturuluyor...")
    
    # PyInstaller komutunu oluştur
    cmd = [
        "pyinstaller",
        "--onefile",  # Tek dosya halinde
        "--windowed",  # Windows GUI uygulaması (konsol penceresi açılmasın)
        "--name=VeresiyeDefteri",  # EXE dosya adı
        "--icon=icon.ico",  # İkon dosyası (varsa)
        "--add-data=database_manager.py;.",  # Ek dosyalar
        "--hidden-import=PyQt6.QtCore",
        "--hidden-import=PyQt6.QtGui", 
        "--hidden-import=PyQt6.QtWidgets",
        "--hidden-import=PyQt6.QtPrintSupport",
        "--hidden-import=reportlab.pdfgen.canvas",
        "--hidden-import=reportlab.lib.pagesizes",
        "--hidden-import=reportlab.pdfbase.pdfmetrics",
        "--hidden-import=reportlab.pdfbase.ttfonts",
        "--hidden-import=reportlab.lib.fonts",
        "debt_ledger.py"
    ]
    
    try:
        subprocess.check_call(cmd)
        print("✅ EXE dosyası başarıyla oluşturuldu!")
        print("📁 Dosya konumu: dist/VeresiyeDefteri.exe")
        
        # Dosya boyutunu kontrol et
        exe_path = "dist/VeresiyeDefteri.exe"
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"📊 Dosya boyutu: {size_mb:.1f} MB")
            
    except subprocess.CalledProcessError as e:
        print(f"❌ EXE oluşturma hatası: {e}")
        return False
        
    return True

def create_spec_file():
    """Özelleştirilmiş .spec dosyası oluştur"""
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['debt_ledger.py'],
    pathex=[],
    binaries=[],
    datas=[('database_manager.py', '.')],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui', 
        'PyQt6.QtWidgets',
        'PyQt6.QtPrintSupport',
        'reportlab.pdfgen.canvas',
        'reportlab.lib.pagesizes',
        'reportlab.pdfbase.pdfmetrics',
        'reportlab.pdfbase.ttfonts',
        'reportlab.lib.fonts',
        'sqlite3',
        'datetime',
        'os',
        'shutil'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='VeresiyeDefteri',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='version_info.txt',
    icon='icon.ico'
)
'''
    
    with open('VeresiyeDefteri.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print("✅ .spec dosyası oluşturuldu!")

def create_version_info():
    """Sürüm bilgi dosyası oluştur"""
    version_content = '''# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
  ffi=FixedFileInfo(
# filevers and prodvers should be always a tuple with four items: (1, 2, 3, 4)
# Set not needed items to zero 0.
filevers=(1,0,0,0),
prodvers=(1,0,0,0),
# Contains a bitmask that specifies the valid bits 'flags'r
mask=0x3f,
# Contains a bitmask that specifies the Boolean attributes of the file.
flags=0x0,
# The operating system for which this file was designed.
# 0x4 - NT and there is no need to change it.
OS=0x4,
# The general type of file.
# 0x1 - the file is an application.
fileType=0x1,
# The function of the file.
# 0x0 - the function is not defined for this fileType
subtype=0x0,
# Creation date and time stamp.
date=(0, 0)
),
  kids=[
StringFileInfo(
  [
  StringTable(
    u'040904B0',
    [StringStruct(u'CompanyName', u''),
    StringStruct(u'FileDescription', u'Veresiye Defteri - Alacak Verecek Takip Uygulaması'),
    StringStruct(u'FileVersion', u'1.0.0'),
    StringStruct(u'InternalName', u'VeresiyeDefteri'),
    StringStruct(u'LegalCopyright', u'© 2025'),
    StringStruct(u'OriginalFilename', u'VeresiyeDefteri.exe'),
    StringStruct(u'ProductName', u'Veresiye Defteri'),
    StringStruct(u'ProductVersion', u'1.0.0')])
  ]), 
VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
'''
    
    with open('version_info.txt', 'w', encoding='utf-8') as f:
        f.write(version_content)
    
    print("✅ Sürüm bilgi dosyası oluşturuldu!")

def main():
    """Ana fonksiyon"""
    print("🔧 Windows EXE Oluşturma Aracı")
    print("=" * 40)
    
    # PyInstaller kontrolü
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "show", "pyinstaller"], 
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("✅ PyInstaller zaten kurulu!")
    except subprocess.CalledProcessError:
        install_pyinstaller()
    
    # Dosyaları oluştur
    create_version_info()
    create_spec_file()
    
    # EXE oluştur
    if create_exe():
        print("\n🎉 İşlem başarıyla tamamlandı!")
        print("\n📋 Oluşturulan dosyalar:")
        print("   📁 dist/VeresiyeDefteri.exe - Ana uygulama")
        print("   📄 VeresiyeDefteri.spec - PyInstaller yapılandırması")
        print("   📄 version_info.txt - Sürüm bilgileri")
        
        print("\n💡 Kullanım:")
        print("   • VeresiyeDefteri.exe dosyasını Windows bilgisayara kopyalayın")
        print("   • Çift tıklayarak çalıştırın")
        print("   • Veritabanı dosyası otomatik oluşturulacaktır")
        
    else:
        print("\n❌ EXE oluşturma başarısız!")
        sys.exit(1)

if __name__ == "__main__":
    main()
