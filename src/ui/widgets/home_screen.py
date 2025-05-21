from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame, QSizePolicy
from PyQt5.QtGui import QIcon, QPixmap, QFont, QLinearGradient, QBrush, QPalette, QColor
from PyQt5.QtCore import Qt, QSize, pyqtSignal
import os

class HomeScreenWidget(QWidget):
    """Custom home screen with tiles and navigation bar"""
    reload_requested = pyqtSignal()
    def __init__(self, parent=None, on_tile_clicked=None, user_info=None, expiry_date=None):
        super().__init__(parent)
        self.on_tile_clicked = on_tile_clicked
        self.user_info = user_info or {}
        self.expiry_date = expiry_date
        self.setup_ui()

    def setup_ui(self):
        # Set dark gradient background
        palette = QPalette()
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0.0, QColor(30, 30, 40))
        gradient.setColorAt(1.0, QColor(10, 10, 20))
        palette.setBrush(QPalette.Window, QBrush(gradient))
        self.setAutoFillBackground(True)
        self.setPalette(palette)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        # Top navigation bar
        nav_bar = QHBoxLayout()
        nav_bar.addStretch()
        reload_btn = QPushButton()
        reload_btn.setIcon(QIcon(os.path.join('assets', 'reload.svg')))
        reload_btn.setIconSize(QSize(48, 48))
        reload_btn.setToolTip('Reload Data')
        reload_btn.setFlat(True)
        reload_btn.clicked.connect(self.reload_requested.emit)
        nav_bar.addWidget(reload_btn)
        search_btn = QPushButton()
        search_btn.setIcon(QIcon(os.path.join('assets', 'search.png')))
        search_btn.setIconSize(QSize(48, 48))
        search_btn.setToolTip('Search')
        search_btn.setFlat(True)
        nav_bar.addWidget(search_btn)
        settings_btn = QPushButton()
        settings_btn.setIcon(QIcon(os.path.join('assets', 'settings.png')))
        settings_btn.setIconSize(QSize(48, 48))
        settings_btn.setToolTip('Settings')
        settings_btn.setFlat(True)
        nav_bar.addWidget(settings_btn)
        account_btn = QPushButton()
        account_btn.setIcon(QIcon(os.path.join('assets', 'account.png')))
        account_btn.setIconSize(QSize(48, 48))
        account_btn.setToolTip('Switch Account')
        account_btn.setFlat(True)
        account_btn.clicked.connect(self.handle_switch_account)
        nav_bar.addWidget(account_btn)
        main_layout.addLayout(nav_bar)

        # Center tiles
        tile_layout = QHBoxLayout()
        tile_layout.setSpacing(40)
        for name, icon, key in [
            ("Live", 'live.png', 'live'),
            ("Movies", 'movies.png', 'movies'),
            ("Series", 'series.png', 'series')
        ]:
            btn = QPushButton()
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.setMinimumSize(200, 200)
            btn.setIcon(QIcon(os.path.join('assets', icon)))
            btn.setIconSize(QSize(120, 120))
            btn.setText(name)
            btn.setFont(QFont('Arial', 22, QFont.Bold))
            btn.setStyleSheet("QPushButton { color: white; background: rgba(40,40,60,0.8); border-radius: 24px; padding: 24px; } QPushButton:hover { background: #444466; }")
            # btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)  # Removed: QPushButton does not support this method
            btn.clicked.connect(lambda checked, k=key: self.handle_tile_click(k))
            tile_layout.addWidget(btn)
        main_layout.addStretch()
        main_layout.addLayout(tile_layout)
        main_layout.addStretch()

        # Bottom info bar
        info_bar = QHBoxLayout()
        self.user_label = QLabel(f"User: {self.user_info.get('username', 'N/A')}")
        self.user_label.setStyleSheet("color: #aaa; font-size: 16px;")
        info_bar.addWidget(self.user_label)
        info_bar.addStretch()
        self.expiry_label = QLabel(f"Subscription expires: {self.expiry_date or 'N/A'}")
        self.expiry_label.setStyleSheet("color: #aaa; font-size: 16px;")
        info_bar.addWidget(self.expiry_label)
        main_layout.addLayout(info_bar)
    def update_user_info(self, user_name):
        self.user_info.update({'username': user_name})
        self.user_label.setText(f"User: {self.user_info.get('username', 'N/A')}")
    def handle_tile_click(self, key):
        if self.on_tile_clicked:
            self.on_tile_clicked(key)
    def update_expiry_date(self, expiry_date):
        if not hasattr(self, 'expiry_label') or self.expiry_label is None or not self.expiry_label.isVisible():
            print("Warning: expiry_label is not available or has been deleted.")
            return
        self.expiry_date = expiry_date
        self.expiry_label.setText(f"Subscription expires: {self.expiry_date or 'N/A'}")

    def handle_switch_account(self):
        # Show the account management screen via parent MainWindow
        main_window = self.window()
        if hasattr(main_window, 'show_account_management_screen'):
            main_window.show_account_management_screen()