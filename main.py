#!/usr/bin/env python3
"""
Debt Ledger Application
A PyQt6 application for managing creditor debts and payments.
"""

import sys
from PyQt6.QtWidgets import QApplication
from debt_ledger import DebtLedgerApp

def main():
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Debt Ledger")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("Personal Finance")
    
    # Create and show the main window
    ledger_app = DebtLedgerApp()
    ledger_app.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
