#!/usr/bin/env python3
import sys
import locale
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from src.ui.main_window import MainWindow
from src.config import DARK_MODE

# Set locale to C for VLC compatibilityp
locale.setlocale(locale.LC_NUMERIC, 'C')

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Set application icon
    app.setWindowIcon(QIcon('assets/sahab_icon.png'))
    
    # Set application name and organization
    app.setApplicationName("Sahab IPTV")
    app.setOrganizationName("SahabIPTV")
    
    # Apply dark theme if enabled
    if DARK_MODE:
        from src.utils.helpers import apply_dark_theme
        apply_dark_theme(app)
    
    # Create and show the main window
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())
