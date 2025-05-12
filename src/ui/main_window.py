"""
Main application window
"""
import os
from PyQt5.QtWidgets import (QMainWindow, QTabWidget, QMessageBox, 
                            QAction, QMenu, QMenuBar, QToolBar, QStatusBar)
from PyQt5.QtCore import Qt, QSettings, QSize
from PyQt5.QtGui import QIcon
from src.api.xtream import XtreamClient
from src.ui.tabs.live_tab import LiveTab
from src.ui.tabs.movies_tab import MoviesTab
from src.ui.tabs.series_tab import SeriesTab
from src.ui.tabs.favorites_tab import FavoritesTab
from src.ui.tabs.downloads_tab import DownloadsTab  # Import DownloadsTab
from src.ui.widgets.dialogs import LoginDialog
from src.utils.helpers import load_json_file, save_json_file, get_translations
from src.config import FAVORITES_FILE, SETTINGS_FILE, DEFAULT_LANGUAGE, WINDOW_SIZE, ICON_SIZE

class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.api_client = XtreamClient()
        self.favorites = []
        self.settings = QSettings()
        self.language = self.settings.value("language", DEFAULT_LANGUAGE)
        self.translations = get_translations(self.language)
        
        self.setup_ui()
        self.load_favorites()
        self.load_settings()
        
        # Show login dialog on startup
        self.show_login_dialog()
        self.downloads_tab = DownloadsTab()
        self.tabs.addTab(self.downloads_tab, self.translations["Downloads"])

        
    def setup_ui(self):
        """Set up the UI components"""
        self.setWindowTitle("Sahab Xtream IPTV")
        self.resize(*WINDOW_SIZE)
        
        # Create central widget with tabs
        self.tabs = QTabWidget()
        
        # Create tabs
        self.live_tab = LiveTab(self.api_client, parent=self)
        self.movies_tab = MoviesTab(self.api_client, parent=self)
        self.series_tab = SeriesTab(self.api_client, parent=self)
        self.favorites_tab = FavoritesTab(self.api_client, parent=self)
        
        # Connect signals
        self.live_tab.add_to_favorites.connect(self.add_to_favorites)
        self.movies_tab.add_to_favorites.connect(self.add_to_favorites)
        self.series_tab.add_to_favorites.connect(self.add_to_favorites)
        self.favorites_tab.remove_from_favorites.connect(self.remove_from_favorites)
        
        # Add tabs to tab widget
        self.tabs.addTab(self.live_tab, self.translations["Live TV"])
        self.tabs.addTab(self.movies_tab, self.translations["Movies"])
        self.tabs.addTab(self.series_tab, self.translations["Series"])
        self.tabs.addTab(self.favorites_tab, self.translations["Favorites"])
        
        self.setCentralWidget(self.tabs)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")
    
    def create_menu_bar(self):
        """Create the menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        connect_action = QAction("Connect", self)
        connect_action.triggered.connect(self.show_login_dialog)
        file_menu.addAction(connect_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Settings menu
        settings_menu = menubar.addMenu("Settings")
        
        language_menu = QMenu("Language", self)
        
        english_action = QAction("English", self)
        english_action.setCheckable(True)
        english_action.setChecked(self.language == "en")
        english_action.triggered.connect(lambda: self.change_language("en"))
        
        arabic_action = QAction("العربية", self)
        arabic_action.setCheckable(True)
        arabic_action.setChecked(self.language == "ar")
        arabic_action.triggered.connect(lambda: self.change_language("ar"))
        
        language_menu.addAction(english_action)
        language_menu.addAction(arabic_action)
        
        settings_menu.addMenu(language_menu)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)
    
    def show_login_dialog(self):
        """Show the login dialog"""
        # Get saved credentials
        server = self.settings.value("server", "")
        username = self.settings.value("username", "")
        password = self.settings.value("password", "")
        remember = self.settings.value("remember_credentials", True, type=bool)
        
        dialog = LoginDialog(self, server, username, password, remember)
        if dialog.exec_():
            credentials = dialog.get_credentials()
            
            # Save credentials if remember is checked
            if credentials['remember']:
                self.settings.setValue("server", credentials['server'])
                self.settings.setValue("username", credentials['username'])
                self.settings.setValue("password", credentials['password'])
                self.settings.setValue("remember_credentials", True)
            else:
                self.settings.remove("server")
                self.settings.remove("username")
                self.settings.remove("password")
                self.settings.setValue("remember_credentials", False)
            
            # Connect to server
            self.connect_to_server(
                credentials['server'],
                credentials['username'],
                credentials['password']
            )
    
    def connect_to_server(self, server, username, password):
        """Connect to the IPTV server"""
        self.statusBar.showMessage("Connecting to server...")
        
        # Set credentials
        self.api_client.set_credentials(server, username, password)
        
        # Authenticate
        success, data = self.api_client.authenticate()
        
        if success:
            self.statusBar.showMessage("Connected successfully")
            
            # Load data
            self.live_tab.load_categories()
            self.movies_tab.load_categories()
            self.series_tab.load_categories()
            
            QMessageBox.information(self, "Connection Success", "Successfully connected to IPTV server")
        else:
            self.statusBar.showMessage("Connection failed")
            QMessageBox.critical(self, "Connection Error", f"Failed to connect: {data}")
    
    def load_favorites(self):
        """Load favorites from file"""
        self.favorites = load_json_file(FAVORITES_FILE, [])
        self.favorites_tab.set_favorites(self.favorites)
    
    def save_favorites(self):
        """Save favorites to file"""
        save_json_file(FAVORITES_FILE, self.favorites)
    
    def add_to_favorites(self, item):
        """Add an item to favorites"""
        # Check if already in favorites
        for favorite in self.favorites:
            if (favorite['stream_type'] == item['stream_type'] and
                ((item['stream_type'] == 'live' and favorite.get('stream_id') == item.get('stream_id')) or
                 (item['stream_type'] == 'movie' and favorite.get('stream_id') == item.get('stream_id')) or
                 (item['stream_type'] == 'series' and favorite.get('episode_id') == item.get('episode_id')))):
                QMessageBox.information(self, "Already in Favorites", f"{item['name']} is already in your favorites")
                return
        
        # Add to favorites
        self.favorites.append(item)
        self.favorites_tab.set_favorites(self.favorites)
        self.save_favorites()
        
        QMessageBox.information(self, "Added to Favorites", f"{item['name']} has been added to your favorites")
    
    def remove_from_favorites(self, index):
        """Remove an item from favorites"""
        if 0 <= index < len(self.favorites):
            del self.favorites[index]
            self.favorites_tab.set_favorites(self.favorites)
            self.save_favorites()
    
    def load_settings(self):
        """Load application settings"""
        self.language = self.settings.value("language", DEFAULT_LANGUAGE)
        self.translations = get_translations(self.language)
        
        # Apply language
        self.apply_language()
    
    def save_settings(self):
        """Save application settings"""
        self.settings.setValue("language", self.language)
    
    def change_language(self, language):
        """Change the application language"""
        if language != self.language:
            self.language = language
            self.translations = get_translations(language)
            self.apply_language()
            self.save_settings()
    
    def apply_language(self):
        """Apply language to UI elements"""
        # Set tab titles
        self.tabs.setTabText(0, self.translations["Live TV"])
        self.tabs.setTabText(1, self.translations["Movies"])
        self.tabs.setTabText(2, self.translations["Series"])
        self.tabs.setTabText(3, self.translations["Favorites"])
        
        # Set layout direction
        if self.language == "ar":
            self.setLayoutDirection(Qt.RightToLeft)
        else:
            self.setLayoutDirection(Qt.LeftToRight)
    
    def show_about_dialog(self):
        """Show the about dialog"""
        QMessageBox.about(
            self, "About Sahab IPTV",
            "Sahab IPTV Player\n\n"
            "A modern IPTV player for Xtream Codes API\n\n"
            "Features:\n"
            "- Live TV streaming\n"
            "- Movies and Series playback\n"
            "- Download functionality\n"
            "- Recording capability\n"
            "- Favorites management\n\n"
            "Version 1.0.0"
        )
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Save settings and favorites
        self.save_settings()
        self.save_favorites()
        event.accept()
