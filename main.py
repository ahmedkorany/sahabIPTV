import sys
import os
import requests
import json
import m3u8
import time
import locale
import vlc
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, 
                            QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QLineEdit, QLabel, QListWidget,
                            QMessageBox, QFileDialog, QProgressBar,
                            QSplitter, QComboBox, QCheckBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QUrl, QSettings, QSize
from PyQt5.QtGui import QIcon, QColor, QPalette
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Set locale to C for VLC compatibility
locale.setlocale(locale.LC_NUMERIC, 'C')

class IPTVPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Python IPTV Xtream Player")
        self.setGeometry(100, 100, 1200, 800)
        
        # Initialize settings
        self.settings = QSettings("SahabIPTV", "IPTVPlayer")
        
        # Initialize session for API requests with retry logic
        self.setup_session()
        
        # Setup UI components
        self.setup_ui()
        
        # Initialize data storage
        self.favorites = []
        self.load_favorites()
        
        # Load saved credentials
        self.load_credentials()
        
    def setup_session(self):
        """Setup requests session with retry logic and headers"""
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Add headers that mimic a common media player
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': '*/*',
            'Connection': 'keep-alive'
        }
    
    def setup_ui(self):
        """Setup main UI components"""
        # Create main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        
        # Create connection section
        connection_layout = QHBoxLayout()
        self.server_input = QLineEdit()
        self.server_input.setPlaceholderText("Server URL")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.remember_credentials = QCheckBox("Remember")
        self.remember_credentials.setChecked(True)
        connect_button = QPushButton("Connect")
        connect_button.clicked.connect(self.connect_to_server)
        
        # Language selector
        self.language_selector = QComboBox()
        self.language_selector.addItem("English")
        self.language_selector.addItem("العربية")
        self.language_selector.currentIndexChanged.connect(self.change_language)
        
        connection_layout.addWidget(self.server_input)
        connection_layout.addWidget(self.username_input)
        connection_layout.addWidget(self.password_input)
        connection_layout.addWidget(self.remember_credentials)
        connection_layout.addWidget(connect_button)
        connection_layout.addWidget(self.language_selector)
        
        # Create tabs
        self.tabs = QTabWidget()
        self.live_tv_tab = QWidget()
        self.movies_tab = QWidget()
        self.series_tab = QWidget()
        self.favorites_tab = QWidget()
        
        self.setup_live_tv_tab()
        self.setup_movies_tab()
        self.setup_series_tab()
        self.setup_favorites_tab()
        
        self.tabs.addTab(self.live_tv_tab, "Live TV")
        self.tabs.addTab(self.movies_tab, "Movies")
        self.tabs.addTab(self.series_tab, "Series")
        self.tabs.addTab(self.favorites_tab, "Favorites")
        
        # Add layouts to main layout
        main_layout.addLayout(connection_layout)
        main_layout.addWidget(self.tabs)
        
        # Set main layout
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
    def setup_live_tv_tab(self):
        """Setup Live TV tab UI"""
        layout = QVBoxLayout()
        
        # Search bar
        search_layout = QHBoxLayout()
        self.live_search = QLineEdit()
        self.live_search.setPlaceholderText("Search channels...")
        self.live_search.textChanged.connect(self.search_live_channels)
        search_layout.addWidget(self.live_search)
        
        # Channel categories and list
        splitter = QSplitter(Qt.Horizontal)
        self.categories_list = QListWidget()
        self.categories_list.setMinimumWidth(200)
        self.channels_list = QListWidget()
        self.channels_list.setMinimumWidth(300)
        
        splitter.addWidget(self.categories_list)
        splitter.addWidget(self.channels_list)
        splitter.setSizes([200, 400])
        
        # Player section
        player_layout = QVBoxLayout()
        self.player_frame = QWidget()
        self.player_frame.setStyleSheet("background-color: black;")
        self.player_frame.setMinimumHeight(400)
        
        # Controls
        controls_layout = QHBoxLayout()
        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self.play_channel)
        self.record_button = QPushButton("Record")
        self.record_button.clicked.connect(self.record_live_stream)
        self.stop_record_button = QPushButton("Stop Recording")
        self.stop_record_button.clicked.connect(self.stop_recording)
        self.stop_record_button.setEnabled(False)
        self.add_to_favorites_button = QPushButton("Add to Favorites")
        self.add_to_favorites_button.clicked.connect(self.add_channel_to_favorites)
        
        controls_layout.addWidget(self.play_button)
        controls_layout.addWidget(self.record_button)
        controls_layout.addWidget(self.stop_record_button)
        controls_layout.addWidget(self.add_to_favorites_button)
        
        player_layout.addWidget(self.player_frame, 4)
        player_layout.addLayout(controls_layout, 1)
        
        # Combine layouts
        content_layout = QHBoxLayout()
        content_layout.addWidget(splitter, 1)
        
        right_widget = QWidget()
        right_widget.setLayout(player_layout)
        content_layout.addWidget(right_widget, 2)
        
        layout.addLayout(search_layout)
        layout.addLayout(content_layout)
        self.live_tv_tab.setLayout(layout)
        
    def setup_movies_tab(self):
        """Setup Movies tab UI"""
        layout = QVBoxLayout()
        
        # Search bar
        search_layout = QHBoxLayout()
        self.movie_search = QLineEdit()
        self.movie_search.setPlaceholderText("Search movies...")
        self.movie_search.textChanged.connect(self.search_movies)
        search_layout.addWidget(self.movie_search)
        
        # Movie categories and list
        splitter = QSplitter(Qt.Horizontal)
        self.movie_categories_list = QListWidget()
        self.movie_categories_list.setMinimumWidth(200)
        self.movies_list = QListWidget()
        self.movies_list.setMinimumWidth(300)
        
        splitter.addWidget(self.movie_categories_list)
        splitter.addWidget(self.movies_list)
        splitter.setSizes([200, 400])
        
        # Player section
        player_layout = QVBoxLayout()
        self.movie_player_frame = QWidget()
        self.movie_player_frame.setStyleSheet("background-color: black;")
        self.movie_player_frame.setMinimumHeight(400)
        
        # Controls
        controls_layout = QHBoxLayout()
        self.play_movie_button = QPushButton("Play")
        self.play_movie_button.clicked.connect(self.play_movie)
        self.download_movie_button = QPushButton("Download")
        self.download_movie_button.clicked.connect(self.download_movie)
        self.add_movie_to_favorites_button = QPushButton("Add to Favorites")
        self.add_movie_to_favorites_button.clicked.connect(self.add_movie_to_favorites)
        
        controls_layout.addWidget(self.play_movie_button)
        controls_layout.addWidget(self.download_movie_button)
        controls_layout.addWidget(self.add_movie_to_favorites_button)
        
        player_layout.addWidget(self.movie_player_frame, 4)
        player_layout.addLayout(controls_layout, 1)
        
        # Combine layouts
        content_layout = QHBoxLayout()
        content_layout.addWidget(splitter, 1)
        
        right_widget = QWidget()
        right_widget.setLayout(player_layout)
        content_layout.addWidget(right_widget, 2)
        
        layout.addLayout(search_layout)
        layout.addLayout(content_layout)
        self.movies_tab.setLayout(layout)
        
    def setup_series_tab(self):
        """Setup Series tab UI"""
        layout = QVBoxLayout()
        
        # Search bar
        search_layout = QHBoxLayout()
        self.series_search = QLineEdit()
        self.series_search.setPlaceholderText("Search series...")
        self.series_search.textChanged.connect(self.search_series)
        search_layout.addWidget(self.series_search)
        
        # Series navigation layout
        splitter = QSplitter(Qt.Horizontal)
        self.series_categories_list = QListWidget()
        self.series_categories_list.setMinimumWidth(150)
        self.series_list = QListWidget()
        self.series_list.setMinimumWidth(200)
        self.seasons_list = QListWidget()
        self.seasons_list.setMinimumWidth(100)
        self.episodes_list = QListWidget()
        self.episodes_list.setMinimumWidth(200)
        
        splitter.addWidget(self.series_categories_list)
        splitter.addWidget(self.series_list)
        splitter.addWidget(self.seasons_list)
        splitter.addWidget(self.episodes_list)
        splitter.setSizes([150, 200, 100, 200])
        
        # Player section
        player_layout = QVBoxLayout()
        self.series_player_frame = QWidget()
        self.series_player_frame.setStyleSheet("background-color: black;")
        self.series_player_frame.setMinimumHeight(400)
        
        # Controls
        controls_layout = QHBoxLayout()
        self.play_episode_button = QPushButton("Play")
        self.play_episode_button.clicked.connect(self.play_episode)
        self.download_episode_button = QPushButton("Download Episode")
        self.download_episode_button.clicked.connect(self.download_episode)
        self.download_season_button = QPushButton("Download Season")
        self.download_season_button.clicked.connect(self.download_season)
        self.add_episode_to_favorites_button = QPushButton("Add to Favorites")
        self.add_episode_to_favorites_button.clicked.connect(self.add_episode_to_favorites)
        
        controls_layout.addWidget(self.play_episode_button)
        controls_layout.addWidget(self.download_episode_button)
        controls_layout.addWidget(self.download_season_button)
        controls_layout.addWidget(self.add_episode_to_favorites_button)
        
        player_layout.addWidget(self.series_player_frame, 4)
        player_layout.addLayout(controls_layout, 1)
        
        # Combine layouts
        content_layout = QHBoxLayout()
        content_layout.addWidget(splitter, 2)
        
        right_widget = QWidget()
        right_widget.setLayout(player_layout)
        content_layout.addWidget(right_widget, 3)
        
        layout.addLayout(search_layout)
        layout.addLayout(content_layout)
        self.series_tab.setLayout(layout)
        
    def setup_favorites_tab(self):
        """Setup Favorites tab UI"""
        layout = QVBoxLayout()
        
        # Search bar
        search_layout = QHBoxLayout()
        self.favorites_search = QLineEdit()
        self.favorites_search.setPlaceholderText("Search favorites...")
        self.favorites_search.textChanged.connect(self.search_favorites)
        search_layout.addWidget(self.favorites_search)
        
        # Favorites sections
        self.favorites_list = QListWidget()
        self.favorites_list.setMinimumWidth(300)
        
        # Player section
        player_layout = QVBoxLayout()
        self.favorites_player_frame = QWidget()
        self.favorites_player_frame.setStyleSheet("background-color: black;")
        self.favorites_player_frame.setMinimumHeight(400)
        
        # Controls
        controls_layout = QHBoxLayout()
        self.play_favorite_button = QPushButton("Play")
        self.play_favorite_button.clicked.connect(self.play_favorite)
        self.remove_favorite_button = QPushButton("Remove from Favorites")
        self.remove_favorite_button.clicked.connect(self.remove_favorite)
        
        controls_layout.addWidget(self.play_favorite_button)
        controls_layout.addWidget(self.remove_favorite_button)
        
        player_layout.addWidget(self.favorites_player_frame, 4)
        player_layout.addLayout(controls_layout, 1)
        
        # Combine layouts
        content_layout = QHBoxLayout()
        content_layout.addWidget(self.favorites_list, 1)
        
        right_widget = QWidget()
        right_widget.setLayout(player_layout)
        content_layout.addWidget(right_widget, 2)
        
        layout.addLayout(search_layout)
        layout.addLayout(content_layout)
        self.favorites_tab.setLayout(layout)
    
    def load_credentials(self):
        """Load saved credentials from settings"""
        server = self.settings.value("server", "")
        username = self.settings.value("username", "")
        password = self.settings.value("password", "")
        
        if server and username and password:
            self.server_input.setText(server)
            self.username_input.setText(username)
            self.password_input.setText(password)
    
    def save_credentials(self):
        """Save credentials to settings"""
        if self.remember_credentials.isChecked():
            self.settings.setValue("server", self.server_input.text())
            self.settings.setValue("username", self.username_input.text())
            self.settings.setValue("password", self.password_input.text())
        else:
            self.settings.remove("server")
            self.settings.remove("username")
            self.settings.remove("password")
    
    def load_favorites(self):
        """Load favorites from settings"""
        favorites_data = self.settings.value("favorites", "")
        if favorites_data:
            try:
                self.favorites = json.loads(favorites_data)
                self.update_favorites_list()
            except:
                self.favorites = []
    
    def save_favorites(self):
        """Save favorites to settings"""
        self.settings.setValue("favorites", json.dumps(self.favorites))
    
    def change_language(self, index):
        """Change application language"""
        if index == 0:  # English
            self.setLayoutDirection(Qt.LeftToRight)
            self.translate_ui("en")
        elif index == 1:  # Arabic
            self.setLayoutDirection(Qt.RightToLeft)
            self.translate_ui("ar")
    
    def translate_ui(self, lang):
        """Translate UI elements based on selected language"""
        translations = {
            "en": {
                "Live TV": "Live TV",
                "Movies": "Movies",
                "Series": "Series",
                "Favorites": "Favorites",
                "Play": "Play",
                "Record": "Record",
                "Stop Recording": "Stop Recording",
                "Add to Favorites": "Add to Favorites",
                "Download": "Download",
                "Download Episode": "Download Episode",
                "Download Season": "Download Season",
                "Remove from Favorites": "Remove from Favorites",
                "Connect": "Connect",
                "Server URL": "Server URL",
                "Username": "Username",
                "Password": "Password",
                "Remember": "Remember",
                "Search channels...": "Search channels...",
                "Search movies...": "Search movies...",
                "Search series...": "Search series...",
                "Search favorites...": "Search favorites..."
            },
            "ar": {
                "Live TV": "البث المباشر",
                "Movies": "الأفلام",
                "Series": "المسلسلات",
                "Favorites": "المفضلة",
                "Play": "تشغيل",
                "Record": "تسجيل",
                "Stop Recording": "إيقاف التسجيل",
                "Add to Favorites": "إضافة إلى المفضلة",
                "Download": "تحميل",
                "Download Episode": "تحميل الحلقة",
                "Download Season": "تحميل الموسم",
                "Remove from Favorites": "إزالة من المفضلة",
                "Connect": "اتصال",
                "Server URL": "عنوان الخادم",
                "Username": "اسم المستخدم",
                "Password": "كلمة المرور",
                "Remember": "تذكر",
                "Search channels...": "البحث في القنوات...",
                "Search movies...": "البحث في الأفلام...",
                "Search series...": "البحث في المسلسلات...",
                "Search favorites...": "البحث في المفضلة..."
            }
        }
        
        # Set tab names
        for i, name in enumerate(["Live TV", "Movies", "Series", "Favorites"]):
            self.tabs.setTabText(i, translations[lang][name])
        
        # Update button texts
        self.play_button.setText(translations[lang]["Play"])
        self.record_button.setText(translations[lang]["Record"])
        self.stop_record_button.setText(translations[lang]["Stop Recording"])
        self.add_to_favorites_button.setText(translations[lang]["Add to Favorites"])
        
        self.play_movie_button.setText(translations[lang]["Play"])
        self.download_movie_button.setText(translations[lang]["Download"])
        self.add_movie_to_favorites_button.setText(translations[lang]["Add to Favorites"])
        
        self.play_episode_button.setText(translations[lang]["Play"])
        self.download_episode_button.setText(translations[lang]["Download Episode"])
        self.download_season_button.setText(translations[lang]["Download Season"])
        self.add_episode_to_favorites_button.setText(translations[lang]["Add to Favorites"])
        
        self.play_favorite_button.setText(translations[lang]["Play"])
        self.remove_favorite_button.setText(translations[lang]["Remove from Favorites"])
        
        # Update placeholders
        self.server_input.setPlaceholderText(translations[lang]["Server URL"])
        self.username_input.setPlaceholderText(translations[lang]["Username"])
        self.password_input.setPlaceholderText(translations[lang]["Password"])
        self.remember_credentials.setText(translations[lang]["Remember"])
        
        self.live_search.setPlaceholderText(translations[lang]["Search channels..."])
        self.movie_search.setPlaceholderText(translations[lang]["Search movies..."])
        self.series_search.setPlaceholderText(translations[lang]["Search series..."])
        self.favorites_search.setPlaceholderText(translations[lang]["Search favorites..."])
    
    def connect_to_server(self):
        """Connect to IPTV server using provided credentials"""
        server_url = self.server_input.text()
        username = self.username_input.text()
        password = self.password_input.text()
        
        if not server_url or not username or not password:
            QMessageBox.warning(self, "Connection Error", "Please fill in all fields")
            return
        
        try:
            # Remove trailing slash if present
            if server_url.endswith('/'):
                server_url = server_url[:-1]
            
            # Get user info
            user_info_url = f"{server_url}/player_api.php?username={username}&password={password}"
            response = self.session.get(user_info_url, headers=self.headers, timeout=30)
            
            if response.status_code != 200:
                QMessageBox.warning(self, "Connection Error", f"Failed to connect to server: Status code {response.status_code}")
                return
            
            user_data = response.json()
            
            if 'user_info' not in user_data:
                QMessageBox.warning(self, "Authentication Error", "Invalid credentials")
                return
            
            self.server_url = server_url
            self.username = username
            self.password = password
            
            # Save credentials if remember is checked
            self.save_credentials()
            
            # Load data
            self.load_live_categories()
            self.load_movie_categories()
            self.load_series_categories()
            
            QMessageBox.information(self, "Connection Success", "Successfully connected to IPTV server")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Connection error: {str(e)}")
    
    def load_live_categories(self):
        """Load live TV categories from server"""
        try:
            url = f"{self.server_url}/player_api.php?username={self.username}&password={self.password}&action=get_live_categories"
            response = self.session.get(url, headers=self.headers, timeout=30)
            categories = response.json()
            
            self.categories_list.clear()
            for category in categories:
                self.categories_list.addItem(category['category_name'])
            
            # Connect selection change event
            self.categories_list.itemClicked.connect(self.load_live_channels)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load live categories: {str(e)}")
    
    def load_live_channels(self, item):
        """Load channels for selected category"""
        try:
            category_name = item.text()
            
            # Find category ID
            url = f"{self.server_url}/player_api.php?username={self.username}&password={self.password}&action=get_live_categories"
            response = self.session.get(url, headers=self.headers, timeout=30)
            categories = response.json()
            
            category_id = None
            for category in categories:
                if category['category_name'] == category_name:
                    category_id = category['category_id']
                    break
            
            if category_id:
                # Get channels for this category
                url = f"{self.server_url}/player_api.php?username={self.username}&password={self.password}&action=get_live_streams&category_id={category_id}"
                response = self.session.get(url, headers=self.headers, timeout=30)
                channels = response.json()
                
                self.channels_list.clear()
                self.live_channels = channels  # Store for later use
                
                for channel in channels:
                    self.channels_list.addItem(channel['name'])
                
                # Apply search filter if there's text in the search box
                if self.live_search.text():
                    self.search_live_channels(self.live_search.text())
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load channels: {str(e)}")
    
    def load_movie_categories(self):
        """Load movie categories from server"""
        try:
            url = f"{self.server_url}/player_api.php?username={self.username}&password={self.password}&action=get_vod_categories"
            response = self.session.get(url, headers=self.headers, timeout=30)
            categories = response.json()
            
            self.movie_categories_list.clear()
            for category in categories:
                self.movie_categories_list.addItem(category['category_name'])
            
            # Connect selection change event
            self.movie_categories_list.itemClicked.connect(self.load_movies)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load movie categories: {str(e)}")
    
    def load_movies(self, item):
        """Load movies for selected category"""
        try:
            category_name = item.text()
            
            # Find category ID
            url = f"{self.server_url}/player_api.php?username={self.username}&password={self.password}&action=get_vod_categories"
            response = self.session.get(url, headers=self.headers, timeout=30)
            categories = response.json()
            
            category_id = None
            for category in categories:
                if category['category_name'] == category_name:
                    category_id = category['category_id']
                    break
            
            if category_id:
                # Get movies for this category
                url = f"{self.server_url}/player_api.php?username={self.username}&password={self.password}&action=get_vod_streams&category_id={category_id}"
                response = self.session.get(url, headers=self.headers, timeout=30)
                movies = response.json()
                
                self.movies_list.clear()
                self.movies = movies  # Store for later use
                
                for movie in movies:
                    self.movies_list.addItem(movie['name'])
                
                # Apply search filter if there's text in the search box
                if self.movie_search.text():
                    self.search_movies(self.movie_search.text())
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load movies: {str(e)}")
    
    def load_series_categories(self):
        """Load series categories from server"""
        try:
            url = f"{self.server_url}/player_api.php?username={self.username}&password={self.password}&action=get_series_categories"
            response = self.session.get(url, headers=self.headers, timeout=30)
            categories = response.json()
            
            self.series_categories_list.clear()
            for category in categories:
                self.series_categories_list.addItem(category['category_name'])
            
            # Connect selection change event
            self.series_categories_list.itemClicked.connect(self.load_series)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load series categories: {str(e)}")
    
    def load_series(self, item):
        """Load series for selected category"""
        try:
            category_name = item.text()
            
            # Find category ID
            url = f"{self.server_url}/player_api.php?username={self.username}&password={self.password}&action=get_series_categories"
            response = self.session.get(url, headers=self.headers, timeout=30)
            categories = response.json()
            
            category_id = None
            for category in categories:
                if category['category_name'] == category_name:
                    category_id = category['category_id']
                    break
            
            if category_id:
                # Get series for this category
                url = f"{self.server_url}/player_api.php?username={self.username}&password={self.password}&action=get_series&category_id={category_id}"
                response = self.session.get(url, headers=self.headers, timeout=30)
                series_list = response.json()
                
                self.series_list.clear()
                self.series_data = series_list  # Store for later use
                
                for series in series_list:
                    self.series_list.addItem(series['name'])
                
                # Apply search filter if there's text in the search box
                if self.series_search.text():
                    self.search_series(self.series_search.text())
                
                # Connect selection change event
                self.series_list.itemClicked.connect(self.load_seasons)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load series: {str(e)}")
    
    def load_seasons(self, item):
        """Load seasons for selected series"""
        try:
            series_name = item.text()
            
            # Find series ID
            series_id = None
            for series in self.series_data:
                if series['name'] == series_name:
                    series_id = series['series_id']
                    self.current_series = series
                    break
            
            if series_id:
                # Get series info
                url = f"{self.server_url}/player_api.php?username={self.username}&password={self.password}&action=get_series_info&series_id={series_id}"
                response = self.session.get(url, headers=self.headers, timeout=30)
                series_info = response.json()
                
                if 'episodes' in series_info:
                    self.seasons_list.clear()
                    self.series_info = series_info
                    
                    for season_number in sorted(series_info['episodes'].keys(), key=int):
                        self.seasons_list.addItem(f"Season {season_number}")
                    
                    # Connect selection change event
                    self.seasons_list.itemClicked.connect(self.load_episodes)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load seasons: {str(e)}")
    
    def load_episodes(self, item):
        """Load episodes for selected season"""
        try:
            season_text = item.text()
            season_number = season_text.replace("Season ", "")
            
            if hasattr(self, 'series_info') and 'episodes' in self.series_info and season_number in self.series_info['episodes']:
                episodes = self.series_info['episodes'][season_number]
                
                self.episodes_list.clear()
                self.current_episodes = episodes
                self.current_season = season_number
                
                for episode in sorted(episodes, key=lambda x: int(x['episode_num'])):
                    self.episodes_list.addItem(f"E{episode['episode_num']} - {episode['title']}")
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load episodes: {str(e)}")
    
    def search_live_channels(self, text):
        """Search live channels based on input text"""
        if not hasattr(self, 'live_channels'):
            return
        
        text = text.lower()
        self.channels_list.clear()
        
        for channel in self.live_channels:
            if text in channel['name'].lower():
                self.channels_list.addItem(channel['name'])
    
    def search_movies(self, text):
        """Search movies based on input text"""
        if not hasattr(self, 'movies'):
            return
        
        text = text.lower()
        self.movies_list.clear()
        
        for movie in self.movies:
            if text in movie['name'].lower():
                self.movies_list.addItem(movie['name'])
    
    def search_series(self, text):
        """Search series based on input text"""
        if not hasattr(self, 'series_data'):
            return
        
        text = text.lower()
        self.series_list.clear()
        
        for series in self.series_data:
            if text in series['name'].lower():
                self.series_list.addItem(series['name'])
    
    def search_favorites(self, text):
        """Search favorites based on input text"""
        text = text.lower()
        self.favorites_list.clear()
        
        for favorite in self.favorites:
            if text in favorite['name'].lower():
                self.favorites_list.addItem(favorite['name'])
    
    def play_channel(self):
        """Play selected live TV channel"""
        if not hasattr(self, 'live_channels') or not self.channels_list.currentItem():
            return
        
        selected_index = self.channels_list.currentRow()
        if selected_index < 0:
            return
        
        # Find the channel in the filtered list
        channel_name = self.channels_list.currentItem().text()
        channel = None
        for ch in self.live_channels:
            if ch['name'] == channel_name:
                channel = ch
                break
        
        if not channel:
            return
        
        stream_id = channel['stream_id']
        
        # Get stream URL
        stream_url = f"{self.server_url}/live/{self.username}/{self.password}/{stream_id}.ts"
        
        # Initialize VLC player if not already done
        if not hasattr(self, 'instance'):
            self.instance = vlc.Instance('--no-xlib')
            self.player = self.instance.media_player_new()
            
            if sys.platform == "linux" or sys.platform == "linux2":
                self.player.set_xwindow(self.player_frame.winId())
            elif sys.platform == "win32":
                self.player.set_hwnd(self.player_frame.winId())
            elif sys.platform == "darwin":
                self.player.set_nsobject(int(self.player_frame.winId()))
        
        # Play the stream
        media = self.instance.media_new(stream_url)
        self.player.set_media(media)
        self.player.play()
        
        # Store current channel for recording
        self.current_channel = {
            'name': channel['name'],
            'stream_url': stream_url,
            'stream_id': stream_id,
            'stream_type': 'live'
        }
    
   

        """Play selected series episode"""
        if not hasattr(self, 'current_episodes') or not self.episodes_list.currentItem():
            return
        
        selected_index = self.episodes_list.currentRow()
        if selected_index < 0:
            return
        
        # Get the episode info from the text
        episode_text = self.episodes_list.currentItem().text()
        episode = None
        for ep in self.current_episodes:
            if episode_text.startswith(f"E{ep['episode_num']}"):
                episode = ep
                break
        
        if not episode:
            return
        
        episode_id = episode['id']
        
        # Try different URL format - some providers use /series/ while others use /episode/
        stream_url = f"{self.server_url}/series/{self.username}/{self.password}/{episode_id}.mp4"
        
        # First validate if the URL is accessible
        try:
            response = self.session.head(stream_url, headers=self.headers, timeout=10)
            if response.status_code != 200:
                # Try alternative URL format if the first one fails
                stream_url = f"{self.server_url}/movie/{self.username}/{self.password}/{episode_id}.mp4"
                response = self.session.head(stream_url, headers=self.headers, timeout=10)
                if response.status_code != 200:
                    QMessageBox.warning(self, "Error", f"Stream not available (Status code: {response.status_code})")
                    return
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to validate stream: {str(e)}")
            return
        
        print(f"Attempting to play episode URL: {stream_url}")
        
        # Initialize VLC player with more options for better streaming
        if not hasattr(self, 'series_instance'):
            vlc_args = [
                '--no-xlib',                # Improve compatibility
                '--network-caching=3000',   # Increase network buffer
                '--live-caching=3000',      # Increase live stream buffer
                '--file-caching=3000',      # Increase file buffer
                '--http-reconnect',         # Enable reconnection
                '--http-continuous',        # Keep connection alive
                '--adaptive-logic=highest', # Use highest quality
                '--input-timeshift-granularity=1000', # Improve timeshift
                '--input-fast-seek',        # Enable fast seeking
                '--sout-mux-caching=3000'   # Muxer caching value
            ]
            self.series_instance = vlc.Instance(' '.join(vlc_args))
            self.series_player = self.series_instance.media_player_new()
            
            if sys.platform == "linux" or sys.platform == "linux2":
                self.series_player.set_xwindow(self.series_player_frame.winId())
            elif sys.platform == "win32":
                self.series_player.set_hwnd(self.series_player_frame.winId())
            elif sys.platform == "darwin":
                self.series_player.set_nsobject(int(self.series_player_frame.winId()))
        
        # Create media with additional options
        media = self.series_instance.media_new(stream_url)
        
        # Add HTTP headers to the request
        media.add_option(f":http-user-agent={self.headers['User-Agent']}")
        media.add_option(f":http-referrer={self.server_url}")  # Add referrer
        media.add_option(":http-reconnect")
        media.add_option(":network-caching=3000")
        media.add_option(":file-caching=3000")
        media.add_option(":live-caching=3000")
        
        # Set media to player and play
        self.series_player.set_media(media)
        self.series_player.play()
        
        # Store current episode
        self.current_episode = {
            'name': f"{self.current_series['name']} - S{episode['season']}E{episode['episode_num']} - {episode['title']}",
            'stream_url': stream_url,
            'episode_id': episode_id,
            'stream_type': 'series',
            'series_id': self.current_series['series_id'],
            'season': episode['season'],
            'episode_num': episode['episode_num'],
            'title': episode['title']
        }

        
    def play_favorite(self):
        """Play selected favorite item"""
        if not self.favorites or not self.favorites_list.currentItem():
            return
        
        favorite_name = self.favorites_list.currentItem().text()
        favorite = None
        for fav in self.favorites:
            if fav['name'] == favorite_name:
                favorite = fav
                break
        
        if not favorite:
            return
        
        # Initialize VLC player if not already done
        if not hasattr(self, 'favorites_instance'):
            self.favorites_instance = vlc.Instance('--no-xlib')
            self.favorites_player = self.favorites_instance.media_player_new()
            
            if sys.platform == "linux" or sys.platform == "linux2":
                self.favorites_player.set_xwindow(self.favorites_player_frame.winId())
            elif sys.platform == "win32":
                self.favorites_player.set_hwnd(self.favorites_player_frame.winId())
            elif sys.platform == "darwin":
                self.favorites_player.set_nsobject(int(self.favorites_player_frame.winId()))
        
        # Play based on stream type
        media = self.favorites_instance.media_new(favorite['stream_url'])
        self.favorites_player.set_media(media)
        self.favorites_player.play()

    def play_movie(self):
        """Play selected movie"""
        if not hasattr(self, 'movies') or not self.movies_list.currentItem():
            return
        
        # Find the movie in the filtered list
        movie_name = self.movies_list.currentItem().text()
        movie = None
        for m in self.movies:
            if m['name'] == movie_name:
                movie = m
                break
        
        if not movie:
            return
        
        stream_id = movie['stream_id']
        
        # Get container extension from VOD info
        container_extension = "mp4"  # Default extension
        try:
            info_url = f"{self.server_url}/player_api.php?username={self.username}&password={self.password}&action=get_vod_info&vod_id={stream_id}"
            info_response = self.session.get(info_url, headers=self.headers, timeout=10)
            
            if info_response.status_code == 200:
                print(f"VOD info response content: {info_response.content}")
                vod_info = info_response.json()
                if 'movie_data' in vod_info and 'container_extension' in vod_info['movie_data']:
                    container_extension = vod_info['movie_data']['container_extension']
                    print(f"Found container extension: {container_extension}")
        except Exception as e:
            print(f"Error getting VOD info: {str(e)}")
        
        # Get stream URL with correct extension
        stream_url = f"{self.server_url}/movie/{self.username}/{self.password}/{stream_id}.{container_extension}"
        print(f"Attempting to play movie URL: {stream_url}")
        
        # Initialize VLC player
        if not hasattr(self, 'movie_instance'):
            self.movie_instance = vlc.Instance('--no-xlib')
            self.movie_player = self.movie_instance.media_player_new()
            
            if sys.platform == "linux" or sys.platform == "linux2":
                self.movie_player.set_xwindow(self.movie_player_frame.winId())
            elif sys.platform == "win32":
                self.movie_player.set_hwnd(self.movie_player_frame.winId())
            elif sys.platform == "darwin":
                self.movie_player.set_nsobject(int(self.movie_player_frame.winId()))
        
        # Play the stream
        media = self.movie_instance.media_new(stream_url)
        self.movie_player.set_media(media)
        self.movie_player.play()
        
        # Store current movie with correct URL
        self.current_movie = {
            'name': movie['name'],
            'stream_url': stream_url,
            'stream_id': stream_id,
            'stream_type': 'movie',
            'container_extension': container_extension
        }

    def play_episode(self):
        """Play selected series episode"""
        if not hasattr(self, 'current_episodes') or not self.episodes_list.currentItem():
            return
        
        selected_index = self.episodes_list.currentRow()
        if selected_index < 0:
            return
        
        # Get the episode info from the text
        episode_text = self.episodes_list.currentItem().text()
        episode = None
        for ep in self.current_episodes:
            if episode_text.startswith(f"E{ep['episode_num']}"):
                episode = ep
                break
        
        if not episode:
            return
        
        episode_id = episode['id']
        
        # Get container extension from episode info
        container_extension = "mp4"  # Default extension
        try:
            # Try to get episode info for container extension
            info_url = f"{self.server_url}/player_api.php?username={self.username}&password={self.password}&action=get_series_info&series_id={self.current_series['series_id']}"
            info_response = self.session.get(info_url, headers=self.headers, timeout=10)
            
            if info_response.status_code == 200:
                print(f"Series info response content: {info_response.content}")
                series_info = info_response.json()
                
                # Look for container_extension in episode info
                if 'episodes' in series_info:
                    for season in series_info['episodes']:
                        for ep in series_info['episodes'][season]:
                            if ep['id'] == episode_id and 'container_extension' in ep:
                                container_extension = ep['container_extension']
                                print(f"Found container extension: {container_extension}")
                                break
        except Exception as e:
            print(f"Error getting series info: {str(e)}")
        
        # Get stream URL with correct extension
        stream_url = f"{self.server_url}/series/{self.username}/{self.password}/{episode_id}.{container_extension}"
        print(f"Attempting to play episode URL: {stream_url}")
        
        # Initialize VLC player
        if not hasattr(self, 'series_instance'):
            self.series_instance = vlc.Instance('--no-xlib')
            self.series_player = self.series_instance.media_player_new()
            
            if sys.platform == "linux" or sys.platform == "linux2":
                self.series_player.set_xwindow(self.series_player_frame.winId())
            elif sys.platform == "win32":
                self.series_player.set_hwnd(self.series_player_frame.winId())
            elif sys.platform == "darwin":
                self.series_player.set_nsobject(int(self.series_player_frame.winId()))
        
        # Play the stream
        media = self.series_instance.media_new(stream_url)
        self.series_player.set_media(media)
        self.series_player.play()
        
        # Store current episode with correct URL
        self.current_episode = {
            'name': f"{self.current_series['name']} - S{episode['season']}E{episode['episode_num']} - {episode['title']}",
            'stream_url': stream_url,
            'episode_id': episode_id,
            'stream_type': 'series',
            'series_id': self.current_series['series_id'],
            'season': episode['season'],
            'episode_num': episode['episode_num'],
            'title': episode['title'],
            'container_extension': container_extension
        }

    def download_movie(self):
        """Download selected movie"""
        if not hasattr(self, 'current_movie'):
            if not hasattr(self, 'movies') or not self.movies_list.currentItem():
                QMessageBox.warning(self, "Error", "No movie selected")
                return
            
            # Get the selected movie
            movie_name = self.movies_list.currentItem().text()
            movie = None
            for m in self.movies:
                if m['name'] == movie_name:
                    movie = m
                    break
            
            if not movie:
                return
            
            stream_id = movie['stream_id']
            movie_name = movie['name']
            
            # Get container extension from VOD info
            container_extension = "mp4"  # Default extension
            try:
                info_url = f"{self.server_url}/player_api.php?username={self.username}&password={self.password}&action=get_vod_info&vod_id={stream_id}"
                info_response = self.session.get(info_url, headers=self.headers, timeout=10)
                
                if info_response.status_code == 200:
                    vod_info = info_response.json()
                    if 'movie_data' in vod_info and 'container_extension' in vod_info['movie_data']:
                        container_extension = vod_info['movie_data']['container_extension']
                        print(f"Found container extension: {container_extension}")
            except Exception as e:
                print(f"Error getting VOD info: {str(e)}")
            
            # Get stream URL with correct extension
            stream_url = f"{self.server_url}/movie/{self.username}/{self.password}/{stream_id}.{container_extension}"
        else:
            movie_name = self.current_movie['name']
            stream_url = self.current_movie['stream_url']
            container_extension = self.current_movie.get('container_extension', 'mp4')
        
        # Ask for save location
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Movie", f"{movie_name}.{container_extension}", f"Video Files (*.{container_extension})"
        )
        
        if not save_path:
            return
        
        print(f"Downloading movie from URL: {stream_url}")
        
        # Start download thread
        self.download_thread = DownloadThread(stream_url, save_path, self.headers)
        self.download_thread.progress_update.connect(self.update_download_progress)
        self.download_thread.download_complete.connect(self.download_finished)
        self.download_thread.download_error.connect(self.download_error)
        
        # Create progress dialog
        self.progress_dialog = QMessageBox()
        self.progress_dialog.setWindowTitle("Downloading")
        self.progress_dialog.setText(f"Downloading {movie_name}...")
        self.progress_bar = QProgressBar(self.progress_dialog)
        self.progress_bar.setGeometry(30, 40, 300, 20)
        self.progress_dialog.setStandardButtons(QMessageBox.Cancel)
        self.progress_dialog.buttonClicked.connect(self.cancel_download)
        self.progress_dialog.show()
        
        self.download_thread.start()

    def download_episode(self):
        """Download selected episode"""
        if not hasattr(self, 'current_episodes') or not self.episodes_list.currentItem():
            QMessageBox.warning(self, "Error", "No episode selected")
            return
        
        # Get the episode info from the text
        episode_text = self.episodes_list.currentItem().text()
        episode = None
        for ep in self.current_episodes:
            if episode_text.startswith(f"E{ep['episode_num']}"):
                episode = ep
                break
        
        if not episode:
            return
        
        episode_id = episode['id']
        episode_title = episode['title']
        season_number = episode['season']
        episode_number = episode['episode_num']
        
        # Get container extension from episode info
        container_extension = "mp4"  # Default extension
        if hasattr(self, 'current_episode') and self.current_episode.get('episode_id') == episode_id:
            container_extension = self.current_episode.get('container_extension', 'mp4')
        else:
            try:
                # Try to get episode info for container extension
                info_url = f"{self.server_url}/player_api.php?username={self.username}&password={self.password}&action=get_series_info&series_id={self.current_series['series_id']}"
                info_response = self.session.get(info_url, headers=self.headers, timeout=10)
                
                if info_response.status_code == 200:
                    series_info = info_response.json()
                    
                    # Look for container_extension in episode info
                    if 'episodes' in series_info:
                        for season in series_info['episodes']:
                            for ep in series_info['episodes'][season]:
                                if ep['id'] == episode_id and 'container_extension' in ep:
                                    container_extension = ep['container_extension']
                                    print(f"Found container extension: {container_extension}")
                                    break
            except Exception as e:
                print(f"Error getting series info: {str(e)}")
        
        # Create filename
        filename = f"{self.current_series['name']} - S{season_number}E{episode_number} - {episode_title}.{container_extension}"
        
        # Get stream URL with correct extension
        stream_url = f"{self.server_url}/series/{self.username}/{self.password}/{episode_id}.{container_extension}"
        print(f"Downloading episode from URL: {stream_url}")
        
        # Ask for save location
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Episode", filename, f"Video Files (*.{container_extension})"
        )
        
        if not save_path:
            return
        
        # Start download thread
        self.download_thread = DownloadThread(stream_url, save_path, self.headers)
        self.download_thread.progress_update.connect(self.update_download_progress)
        self.download_thread.download_complete.connect(self.download_finished)
        self.download_thread.download_error.connect(self.download_error)
        
        # Create progress dialog
        self.progress_dialog = QMessageBox()
        self.progress_dialog.setWindowTitle("Downloading")
        self.progress_dialog.setText(f"Downloading {filename}...")
        self.progress_bar = QProgressBar(self.progress_dialog)
        self.progress_bar.setGeometry(30, 40, 300, 20)
        self.progress_dialog.setStandardButtons(QMessageBox.Cancel)
        self.progress_dialog.buttonClicked.connect(self.cancel_download)
        self.progress_dialog.show()
        
        self.download_thread.start()

    def download_season(self):
        """Download complete season of series"""
        if not hasattr(self, 'current_series') or not self.seasons_list.currentItem():
            QMessageBox.warning(self, "Error", "No season selected")
            return
        
        series_id = self.current_series['series_id']
        series_name = self.current_series['name']
        season_number = self.seasons_list.currentItem().text().replace("Season ", "")
        
        # Get episodes for this season
        if hasattr(self, 'series_info') and 'episodes' in self.series_info and season_number in self.series_info['episodes']:
            episodes = self.series_info['episodes'][season_number]
        else:
            QMessageBox.warning(self, "Error", "Failed to get season information")
            return
        
        # Try to get container extension information for episodes
        try:
            info_url = f"{self.server_url}/player_api.php?username={self.username}&password={self.password}&action=get_series_info&series_id={series_id}"
            info_response = self.session.get(info_url, headers=self.headers, timeout=10)
            
            if info_response.status_code == 200:
                print(f"Series info response content: {info_response.content}")
                series_info = info_response.json()
                
                # Update episodes with container extension if available
                if 'episodes' in series_info and season_number in series_info['episodes']:
                    for i, ep in enumerate(episodes):
                        for server_ep in series_info['episodes'][season_number]:
                            if server_ep['id'] == ep['id'] and 'container_extension' in server_ep:
                                episodes[i]['container_extension'] = server_ep['container_extension']
                                break
        except Exception as e:
            print(f"Error getting series info: {str(e)}")
        
        # Ask for save directory
        save_dir = QFileDialog.getExistingDirectory(
            self, "Select Directory to Save Season"
        )
        
        if not save_dir:
            return
        
        # Create season directory
        season_dir = os.path.join(save_dir, f"{series_name} - Season {season_number}")
        os.makedirs(season_dir, exist_ok=True)
        
        # Start batch download
        self.batch_download_thread = BatchDownloadThread(
            self.server_url, self.username, self.password, 
            episodes, season_dir, series_name, self.headers
        )
        self.batch_download_thread.progress_update.connect(self.update_batch_progress)
        self.batch_download_thread.download_complete.connect(self.batch_download_finished)
        self.batch_download_thread.download_error.connect(self.batch_download_error)
        
        # Create progress dialog
        self.batch_progress_dialog = QMessageBox()
        self.batch_progress_dialog.setWindowTitle("Downloading Season")
        self.batch_progress_dialog.setText(f"Downloading {series_name} - Season {season_number}...")
        self.batch_progress_bar = QProgressBar(self.batch_progress_dialog)
        self.batch_progress_bar.setGeometry(30, 40, 300, 20)
        self.batch_progress_dialog.setStandardButtons(QMessageBox.Cancel)
        self.batch_progress_dialog.buttonClicked.connect(self.cancel_batch_download)
        self.batch_progress_dialog.show()
        
        self.batch_download_thread.start()

    def record_live_stream(self):
        """Record current live stream"""
        if not hasattr(self, 'current_channel'):
            QMessageBox.warning(self, "Error", "No channel selected")
            return
        
        # Ask for save location
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Recording", f"{self.current_channel['name']}.mp4", "MP4 Files (*.mp4)"
        )
        
        if not save_path:
            return
        
        # Start recording thread
        self.recording_thread = RecordingThread(self.current_channel['stream_url'], save_path, self.headers)
        self.recording_thread.recording_started.connect(self.recording_started)
        self.recording_thread.recording_error.connect(self.recording_error)
        self.recording_thread.recording_stopped.connect(self.recording_stopped)
        
        self.recording_thread.start()
        
        # Update UI
        self.record_button.setEnabled(False)
        self.stop_record_button.setEnabled(True)
    
    def stop_recording(self):
        """Stop current recording"""
        if hasattr(self, 'recording_thread') and self.recording_thread.isRunning():
            self.recording_thread.stop_recording()
        
        # Update UI will be handled by the recording_stopped signal
    
    def add_channel_to_favorites(self):
        """Add current channel to favorites"""
        if not hasattr(self, 'current_channel'):
            QMessageBox.warning(self, "Error", "No channel selected")
            return
        
        # Check if already in favorites
        for favorite in self.favorites:
            if favorite['stream_type'] == 'live' and favorite['stream_id'] == self.current_channel['stream_id']:
                QMessageBox.information(self, "Info", "This channel is already in favorites")
                return
        
        # Add to favorites
        self.favorites.append(self.current_channel)
        self.update_favorites_list()
        self.save_favorites()
        
        QMessageBox.information(self, "Success", f"Added {self.current_channel['name']} to favorites")
    
    def add_movie_to_favorites(self):
        """Add current movie to favorites"""
        if not hasattr(self, 'current_movie'):
            QMessageBox.warning(self, "Error", "No movie selected")
            return
        
        # Check if already in favorites
        for favorite in self.favorites:
            if favorite['stream_type'] == 'movie' and favorite['stream_id'] == self.current_movie['stream_id']:
                QMessageBox.information(self, "Info", "This movie is already in favorites")
                return
        
        # Add to favorites
        self.favorites.append(self.current_movie)
        self.update_favorites_list()
        self.save_favorites()
        
        QMessageBox.information(self, "Success", f"Added {self.current_movie['name']} to favorites")
    
    def add_episode_to_favorites(self):
        """Add current episode to favorites"""
        if not hasattr(self, 'current_episode'):
            QMessageBox.warning(self, "Error", "No episode selected")
            return
        
        # Check if already in favorites
        for favorite in self.favorites:
            if favorite['stream_type'] == 'series' and favorite.get('episode_id') == self.current_episode['episode_id']:
                QMessageBox.information(self, "Info", "This episode is already in favorites")
                return
        
        # Add to favorites
        self.favorites.append(self.current_episode)
        self.update_favorites_list()
        self.save_favorites()
        
        QMessageBox.information(self, "Success", f"Added {self.current_episode['name']} to favorites")
    
    def remove_favorite(self):
        """Remove selected item from favorites"""
        if not self.favorites or not self.favorites_list.currentItem():
            return
        
        favorite_name = self.favorites_list.currentItem().text()
        favorite_index = None
        for i, fav in enumerate(self.favorites):
            if fav['name'] == favorite_name:
                favorite_index = i
                break
        
        if favorite_index is not None:
            del self.favorites[favorite_index]
            self.update_favorites_list()
            self.save_favorites()
            
            QMessageBox.information(self, "Success", f"Removed {favorite_name} from favorites")
    
    def update_favorites_list(self):
        """Update the favorites list widget"""
        self.favorites_list.clear()
        for favorite in self.favorites:
            self.favorites_list.addItem(favorite['name'])
    
    def update_download_progress(self, progress):
        """Update download progress bar"""
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setValue(progress)
    
    def download_finished(self, save_path):
        """Handle download completion"""
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.close()
        QMessageBox.information(self, "Download Complete", f"File saved to: {save_path}")
    
    def download_error(self, error_message):
        """Handle download error"""
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.close()
        QMessageBox.critical(self, "Download Error", error_message)
    
    def cancel_download(self, button):
        """Cancel current download"""
        if hasattr(self, 'download_thread') and self.download_thread.isRunning():
            self.download_thread.cancel()
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.close()
    
    def update_batch_progress(self, episode_index, progress):
        """Update batch download progress"""
        if hasattr(self, 'batch_progress_bar'):
            self.batch_progress_dialog.setText(f"Downloading episode {episode_index+1}... {progress}%")
            self.batch_progress_bar.setValue(progress)
    
    def batch_download_finished(self):
        """Handle batch download completion"""
        if hasattr(self, 'batch_progress_dialog'):
            self.batch_progress_dialog.close()
        QMessageBox.information(self, "Download Complete", "Season download completed")
    
    def batch_download_error(self, error_message):
        """Handle batch download error"""
        if hasattr(self, 'batch_progress_dialog'):
            self.batch_progress_dialog.close()
        QMessageBox.critical(self, "Download Error", error_message)
    
    def cancel_batch_download(self, button):
        """Cancel current batch download"""
        if hasattr(self, 'batch_download_thread') and self.batch_download_thread.isRunning():
            self.batch_download_thread.cancel()
        if hasattr(self, 'batch_progress_dialog'):
            self.batch_progress_dialog.close()
    
    def recording_started(self):
        """Handle recording started event"""
        QMessageBox.information(self, "Recording", "Recording started successfully")
    
    def recording_error(self, error_message):
        """Handle recording error"""
        QMessageBox.critical(self, "Recording Error", error_message)
        self.record_button.setEnabled(True)
        self.stop_record_button.setEnabled(False)
    
    def recording_stopped(self):
        """Handle recording stopped event"""
        QMessageBox.information(self, "Recording", "Recording stopped successfully")
        self.record_button.setEnabled(True)
        self.stop_record_button.setEnabled(False)


class DownloadThread(QThread):
    """Thread for downloading content"""
    progress_update = pyqtSignal(int)
    download_complete = pyqtSignal(str)
    download_error = pyqtSignal(str)
    
    def __init__(self, url, save_path, headers):
        super().__init__()
        self.url = url
        self.save_path = save_path
        self.headers = headers
        self.is_cancelled = False
    
    def run(self):
        try:
            # Setup session with retry logic
            session = requests.Session()
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            session.mount("http://", adapter)
            session.mount("https://", adapter)
            
            # First make a HEAD request to get the content length
            head_response = session.head(self.url, headers=self.headers, timeout=30)
            total_size = int(head_response.headers.get('content-length', 0))
            
            if total_size == 0:
                # If HEAD request doesn't provide content length, try a GET request with stream=True
                response = session.get(self.url, stream=True, headers=self.headers, timeout=30)
                total_size = int(response.headers.get('content-length', 0))
                
                if total_size == 0:
                    # If still can't determine size, proceed anyway but without progress tracking
                    self.download_error.emit("Unable to determine file size, downloading without progress tracking")
                    with open(self.save_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if self.is_cancelled:
                                break
                            if chunk:
                                f.write(chunk)
                    
                    if not self.is_cancelled:
                        self.download_complete.emit(self.save_path)
                    else:
                        os.remove(self.save_path)
                    return
            else:
                # If we got the content length from HEAD request, make a new GET request
                response = session.get(self.url, stream=True, headers=self.headers, timeout=30)
            
            downloaded = 0
            with open(self.save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if self.is_cancelled:
                        break
                    
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        progress = int((downloaded / total_size) * 100) if total_size > 0 else 0
                        self.progress_update.emit(progress)
            
            if self.is_cancelled:
                # Delete partial file
                os.remove(self.save_path)
            else:
                self.download_complete.emit(self.save_path)
                
        except Exception as e:
            self.download_error.emit(str(e))
    
    def cancel(self):
        self.is_cancelled = True


class BatchDownloadThread(QThread):
    """Thread for downloading multiple episodes"""
    progress_update = pyqtSignal(int, int)  # episode_index, progress
    download_complete = pyqtSignal()
    download_error = pyqtSignal(str)
    
    def __init__(self, server_url, username, password, episodes, save_dir, series_name, headers):
        super().__init__()
        self.server_url = server_url
        self.username = username
        self.password = password
        self.episodes = episodes
        self.save_dir = save_dir
        self.series_name = series_name
        self.headers = headers
        self.is_cancelled = False
    
    def run(self):
        try:
            # Setup session with retry logic
            session = requests.Session()
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            session.mount("http://", adapter)
            session.mount("https://", adapter)
            
            total_episodes = len(self.episodes)
            
            for i, episode in enumerate(self.episodes):
                if self.is_cancelled:
                    break
                
                episode_id = episode['id']
                episode_title = episode['title']
                episode_number = episode['episode_num']
                
                # Get container extension (default to mp4 if not specified)
                container_extension = episode.get('container_extension', 'mp4')
                
                # Create filename
                filename = f"{self.series_name} - S{episode['season']}E{episode_number} - {episode_title}.{container_extension}"
                save_path = os.path.join(self.save_dir, filename)
                
                # Get stream URL with correct extension
                stream_url = f"{self.server_url}/series/{self.username}/{self.password}/{episode_id}.{container_extension}"
                print(f"Downloading episode from URL: {stream_url}")
                
                # Download episode
                response = session.get(stream_url, stream=True, headers=self.headers, timeout=30)
                total_size = int(response.headers.get('content-length', 0))
                
                if total_size == 0:
                    print(f"Warning: Unable to determine file size for episode {episode_number}")
                
                downloaded = 0
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if self.is_cancelled:
                            break
                        
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            progress = int((downloaded / total_size) * 100) if total_size > 0 else 0
                            self.progress_update.emit(i, progress)
                
                if self.is_cancelled:
                    # Delete partial file
                    if os.path.exists(save_path):
                        os.remove(save_path)
                    break
            
            if not self.is_cancelled:
                self.download_complete.emit()
                
        except Exception as e:
            self.download_error.emit(str(e))
    
    def cancel(self):
        self.is_cancelled = True



class RecordingThread(QThread):
    """Thread for recording live streams"""
    recording_started = pyqtSignal()
    recording_error = pyqtSignal(str)
    recording_stopped = pyqtSignal()
    
    def __init__(self, stream_url, save_path, headers):
        super().__init__()
        self.stream_url = stream_url
        self.save_path = save_path
        self.headers = headers
        self.is_recording = False
    
    def run(self):
        try:
            # Setup session with retry logic
            session = requests.Session()
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            session.mount("http://", adapter)
            session.mount("https://", adapter)
            
            # Open stream
            cap = cv2.VideoCapture(self.stream_url)
            
            if not cap.isOpened():
                self.recording_error.emit("Failed to open stream")
                return
            
            # Get video properties
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            if fps <= 0:
                fps = 25  # Default to 25 fps if not detected
            
            # Create VideoWriter
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(self.save_path, fourcc, fps, (width, height))
            
            self.is_recording = True
            self.recording_started.emit()
            
            while self.is_recording:
                ret, frame = cap.read()
                
                if not ret:
                    break
                
                out.write(frame)
            
            # Release resources
            cap.release()
            out.release()
            
            self.recording_stopped.emit()
            
        except Exception as e:
            self.recording_error.emit(str(e))
    
    def stop_recording(self):
        self.is_recording = False

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion') # Modern look
    # Set dark theme
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.WindowText, Qt.white)
    dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
    dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
    dark_palette.setColor(QPalette.ToolTipText, Qt.white)
    dark_palette.setColor(QPalette.Text, Qt.white)
    dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ButtonText, Qt.white)
    dark_palette.setColor(QPalette.BrightText, Qt.red)
    dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(dark_palette)

    window = IPTVPlayer()
    window.show()

    sys.exit(app.exec_())
