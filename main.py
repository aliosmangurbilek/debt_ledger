#!/usr/bin/env python3
"""
Debt Ledger Application
A PyQt6 application for managing creditor debts and payments.
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont, QFontDatabase
from debt_ledger import DebtLedgerApp

def setup_turkish_fonts():
    """Türkçe karakterler için sistem fontlarını ayarla"""
    try:
        # Linux sistem fontlarını öncelikle dene
        system_fonts = [
            "Liberation Sans",  # Linux varsayılan
            "DejaVu Sans",      # Linux yaygın font
            "Ubuntu",           # Ubuntu font
            "Noto Sans",        # Google Noto
            "Arial",            # Fallback
            "Helvetica",        # Fallback
            "Sans Serif"        # Son çare
        ]

        font_db = QFontDatabase()

        for font_name in system_fonts:
            # Mevcut fontları listele ve kontrol et
            available_families = font_db.families()
            if font_name in available_families:
                app_font = QFont(font_name, 10)
                app_font.setStyleHint(QFont.StyleHint.SansSerif)
                app = QApplication.instance()
                if app:
                    app.setFont(app_font)
                    print(f"✓ {font_name} sistem fontu başarıyla ayarlandı")
                    return

        # Hiçbir font bulunamazsa varsayılan Qt fontu kullan
        print("⚠️ Hiçbir sistem fontu bulunamadı, Qt varsayılanı kullanılacak")
        default_font = QFont()
        default_font.setPointSize(10)
        default_font.setStyleHint(QFont.StyleHint.SansSerif)
        app = QApplication.instance()
        if app:
            app.setFont(default_font)

    except Exception as e:
        print(f"⚠️ Font ayarlama hatası: {e}")
        print("⚠️ Standart fontlar kullanılacak")
        # En güvenli seçenek - varsayılan font kullan
        try:
            default_font = QFont()
            default_font.setPointSize(10)
            app = QApplication.instance()
            if app:
                app.setFont(default_font)
        except:
            pass

def main():
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Debt Ledger")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("Personal Finance")
    
    # Setup Turkish character support
    setup_turkish_fonts()

    # Create and show the main window
    ledger_app = DebtLedgerApp()
    ledger_app.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
