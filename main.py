#!/usr/bin/env python3
"""
Debt Ledger Application
A PyQt6 application for managing creditor debts and payments.
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont, QFontDatabase, QTextDocument
from debt_ledger import DebtLedgerApp

def setup_turkish_fonts():
    """Türkçe karakterler için sistem fontlarını ayarla"""
    try:
        # Sistem fontlarını dene (en güvenli seçenek)
        system_fonts = [
            "Segoe UI",    # Windows 10/11 varsayılan fontu
            "Tahoma",      # Windows eski sürümler
            "Arial",       # Evrensel font
            "Calibri",     # Office fontu
            "Verdana"      # Web güvenli font
        ]

        font_db = QFontDatabase()

        for font_name in system_fonts:
            if font_db.hasFamily(font_name):
                app_font = QFont(font_name, 10)
                QApplication.instance().setFont(app_font)
                print(f"✓ {font_name} sistem fontu başarıyla ayarlandı")
                return

        # Hiçbir font bulunamazsa varsayılan Qt fontu kullan
        print("⚠️ Hiçbir sistem fontu bulunamadı, Qt varsayılanı kullanılacak")

    except Exception as e:
        print(f"⚠️ Font ayarlama hatası: {e}")
        print("⚠️ Standart fontlar kullanılacak")
        # En güvenli seçenek - hiçbir font ayarlaması yapma
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
