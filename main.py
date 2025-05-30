#!/usr/bin/env python3
import sys
import locale
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from src.ui.main_window import MainWindow
from src.config import DARK_MODE

# Set locale to C for VLC compatibility
locale.setlocale(locale.LC_NUMERIC, 'C')

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setWindowIcon(QIcon('assets/sahab_icon.png'))
    app.setApplicationName("Sahab IPTV")
    app.setOrganizationName("EFHAM Labs")
    if DARK_MODE:
        from src.utils.helpers import apply_dark_theme
        apply_dark_theme(app)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
