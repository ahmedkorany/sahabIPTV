from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSizePolicy
from PyQt5.QtGui import QIcon, QFont, QLinearGradient, QBrush, QPalette, QColor
from PyQt5.QtCore import QSize, pyqtSignal
from src.utils.helpers import get_translations
import os

class HomeScreenWidget(QWidget):
    """Custom home screen with tiles and navigation bar"""
    reload_requested = pyqtSignal()
    def __init__(self, parent=None, on_tile_clicked=None, user_info=None, expiry_date=None):
        super().__init__(parent)
        self.on_tile_clicked = on_tile_clicked
        self.user_info = user_info or {}
        self.expiry_date = expiry_date
        # Get translations from parent or default to English
        self.translations = get_translations(parent.language if parent and hasattr(parent, 'language') else 'en')
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
        reload_btn.setToolTip(self.translations.get('Reload Data', 'Reload Data'))
        reload_btn.setFlat(True)
        reload_btn.clicked.connect(self.reload_requested.emit)
        nav_bar.addWidget(reload_btn)
        search_btn = QPushButton()
        search_btn.setObjectName("search_btn") # Added object name
        search_btn.setIcon(QIcon(os.path.join('assets', 'search.png')))
        search_btn.setIconSize(QSize(48, 48))
        search_btn.setToolTip(self.translations.get('Search', 'Search'))
        search_btn.setFlat(True)
        search_btn.clicked.connect(lambda: self.handle_tile_click('search')) # Connect to handle_tile_click
        nav_bar.addWidget(search_btn)
        settings_btn = QPushButton()
        settings_btn.setIcon(QIcon(os.path.join('assets', 'settings.png')))
        settings_btn.setIconSize(QSize(48, 48))
        settings_btn.setToolTip(self.translations.get('Settings', 'Settings'))
        settings_btn.setFlat(True)
        nav_bar.addWidget(settings_btn)
        account_btn = QPushButton()
        account_btn.setIcon(QIcon(os.path.join('assets', 'account.png')))
        account_btn.setIconSize(QSize(48, 48))
        account_btn.setToolTip(self.translations.get('Switch Account', 'Switch Account'))
        account_btn.setFlat(True)
        account_btn.clicked.connect(self.handle_switch_account)
        nav_bar.addWidget(account_btn)
        main_layout.addLayout(nav_bar)

        # Center tiles
        tile_layout = QHBoxLayout()
        tile_layout.setSpacing(40)
        for name, icon, key in [
            (self.translations.get("Live", "Live"), 'live.png', 'live'),
            (self.translations.get("Movies", "Movies"), 'movies.png', 'movies'),
            (self.translations.get("Series", "Series"), 'series.png', 'series')
        ]:
            btn = QPushButton()
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.setMinimumSize(200, 200)
            btn.setIcon(QIcon(os.path.join('assets', icon)))
            btn.setIconSize(QSize(120, 120))
            btn.setText(name)
            btn.setFont(QFont('Arial', 22, QFont.Bold))
            btn.setStyleSheet("QPushButton { color: white; background: rgba(40,40,60,0.8); border-radius: 24px; padding: 24px; } QPushButton:hover { background: #444466; }")
            btn.clicked.connect(lambda checked, k=key: self.handle_tile_click(k))
            tile_layout.addWidget(btn)
        main_layout.addStretch()
        main_layout.addLayout(tile_layout)
        main_layout.addStretch()

        # Bottom info bar
        info_bar = QHBoxLayout()
        self.user_label = QLabel(f"{self.translations.get('User', 'User:')}: {self.user_info.get('username', self.translations.get('N/A', 'N/A'))}")
        self.user_label.setStyleSheet("color: #aaa; font-size: 16px;")
        info_bar.addWidget(self.user_label)
        info_bar.addStretch()
        self.expiry_label = QLabel(f"{self.translations.get('Subscription expires', 'Subscription expires:')}: {self.expiry_date or self.translations.get('N/A', 'N/A')}")
        self.expiry_label.setStyleSheet("color: #aaa; font-size: 16px;")
        info_bar.addWidget(self.expiry_label)
        main_layout.addLayout(info_bar)
    def update_user_info(self, user_name):
        self.user_info.update({'username': user_name})
        self.user_label.setText(f"{self.translations.get('User', 'User')}: {self.user_info.get('username', self.translations.get('N/A', 'N/A'))}")
    def handle_tile_click(self, key):
        if self.on_tile_clicked:
            self.on_tile_clicked(key)
    def update_expiry_date(self, expiry_date):
        if not hasattr(self, 'expiry_label') or self.expiry_label is None or not self.expiry_label.isVisible():
            print("Warning: expiry_label is not available or has been deleted.")
            return
        self.expiry_date = expiry_date
        self.expiry_label.setText(f"{self.translations.get('Subscription expires', 'Subscription expires')}: {self.expiry_date or self.translations.get('N/A', 'N/A')}")

    def update_translations(self, translations):
        """Update translations and refresh text content without recreating UI"""
        self.translations = translations
        
        # Update tooltips for navigation buttons
        reload_btn = self.findChild(QPushButton)
        if reload_btn:
            reload_btn.setToolTip(self.translations.get('Reload Data', 'Reload Data'))
        
        search_btn = self.findChild(QPushButton, "search_btn")
        if search_btn:
            search_btn.setToolTip(self.translations.get('Search', 'Search'))
        
        # Update tile button texts
        tile_buttons = self.findChildren(QPushButton)
        tile_texts = [
            self.translations.get("Live", "Live"),
            self.translations.get("Movies", "Movies"),
            self.translations.get("Series", "Series")
        ]
        
        # Find and update the main tile buttons (they have larger icon sizes)
        for btn in tile_buttons:
            if btn.iconSize().width() == 120:  # Main tile buttons have 120x120 icons
                current_text = btn.text()
                if "Live" in current_text or "مباشر" in current_text:
                    btn.setText(tile_texts[0])
                elif "Movies" in current_text or "أفلام" in current_text:
                    btn.setText(tile_texts[1])
                elif "Series" in current_text or "مسلسلات" in current_text:
                    btn.setText(tile_texts[2])
        
        # Update user and expiry labels
        if hasattr(self, 'user_label') and self.user_label:
            self.user_label.setText(f"{self.translations.get('User', 'User:')}: {self.user_info.get('username', self.translations.get('N/A', 'N/A'))}")
        
        if hasattr(self, 'expiry_label') and self.expiry_label:
            self.expiry_label.setText(f"{self.translations.get('Subscription expires', 'Subscription expires:')}: {self.expiry_date or self.translations.get('N/A', 'N/A')}")

    def handle_switch_account(self):
        # Show the account management screen via parent MainWindow
        main_window = self.window()
        if hasattr(main_window, 'show_account_management_screen'):
            main_window.show_account_management_screen()
