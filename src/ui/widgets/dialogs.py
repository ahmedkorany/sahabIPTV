"""
Custom dialog widgets for the application
"""
import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QLineEdit, QPushButton, QProgressBar, QMessageBox,
                            QCheckBox, QFileDialog, QComboBox, QTextEdit, QListWidget, QListWidgetItem, QTabWidget)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QFont
from src.ui.player import MediaPlayer, PlayerWindow
from src.utils.image_cache import ImageCache

class LoginDialog(QDialog):
    """Dialog for entering IPTV server credentials"""
    
    def __init__(self, parent=None, server="", username="", password="", remember=True):
        super().__init__(parent)
        self.setWindowTitle("Connect to IPTV Server")
        self.setMinimumWidth(400)
        
        self.setup_ui(server, username, password, remember)
    
    def setup_ui(self, server, username, password, remember):
        """Set up the UI components"""
        layout = QVBoxLayout(self)
        
        # Server URL
        server_layout = QHBoxLayout()
        server_label = QLabel("Server URL:")
        self.server_input = QLineEdit(server)
        self.server_input.setPlaceholderText("http://example.com")
        server_layout.addWidget(server_label)
        server_layout.addWidget(self.server_input)
        
        # Username
        username_layout = QHBoxLayout()
        username_label = QLabel("Username:")
        self.username_input = QLineEdit(username)
        username_layout.addWidget(username_label)
        username_layout.addWidget(self.username_input)
        
        # Password
        password_layout = QHBoxLayout()
        password_label = QLabel("Password:")
        self.password_input = QLineEdit(password)
        self.password_input.setEchoMode(QLineEdit.Password)
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_input)
        
        # Remember checkbox
        self.remember_checkbox = QCheckBox("Remember credentials")
        self.remember_checkbox.setChecked(remember)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.connect_button)
        buttons_layout.addWidget(self.cancel_button)
        
        # Add all layouts to main layout
        layout.addLayout(server_layout)
        layout.addLayout(username_layout)
        layout.addLayout(password_layout)
        layout.addWidget(self.remember_checkbox)
        layout.addLayout(buttons_layout)
    
    def get_credentials(self):
        """Get the entered credentials"""
        return {
            'server': self.server_input.text(),
            'username': self.username_input.text(),
            'password': self.password_input.text(),
            'remember': self.remember_checkbox.isChecked()
        }


class ProgressDialog(QDialog):
    """Dialog for showing progress of operations"""
    cancelled = pyqtSignal()
    
    def __init__(self, parent=None, title="Progress", text="Please wait..."):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.CustomizeWindowHint)
        
        self.setup_ui(text)
    
    def setup_ui(self, text):
        """Set up the UI components"""
        layout = QVBoxLayout(self)
        
        self.text_label = QLabel(text)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel)
        
        layout.addWidget(self.text_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.cancel_button, alignment=Qt.AlignRight)
    
    def set_progress(self, value):
        """Set the progress bar value"""
        self.progress_bar.setValue(value)
    
    def set_text(self, text):
        """Set the dialog text"""
        self.text_label.setText(text)
    
    def cancel(self):
        """Emit the cancelled signal"""
        self.cancelled.emit()


class SeriesDetailsDialog(QDialog):
    """Dialog for displaying series details, seasons, and episodes"""
    def __init__(self, series, api_client, parent=None):
        super().__init__(parent)
        self.setWindowTitle(series.get('name', 'Series Details'))
        self.setMinimumWidth(700)
        self.series = series
        self.api_client = api_client
        self.seasons = []
        self.episodes = []
        self.setup_ui()
        self.load_seasons()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        # Poster
        poster = QLabel()
        poster.setAlignment(Qt.AlignTop)
        pix = QPixmap()
        if self.series.get('cover'):
            image_data = self.api_client.get_image_data(self.series['cover'])
            if image_data:
                pix.loadFromData(image_data)
        if not pix or pix.isNull():
            pix = QPixmap('assets/series.png')
        if not pix.isNull():
            poster.setPixmap(pix.scaled(180, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        layout.addWidget(poster)
        # Metadata and episodes
        right_layout = QVBoxLayout()
        # Title
        title = QLabel(self.series.get('name', ''))
        title.setFont(QFont('Arial', 16, QFont.Bold))
        right_layout.addWidget(title)
        # Metadata
        meta = QLabel()
        meta.setText(f"Year: {self.series.get('year', '--')} | Genre: {self.series.get('genre', '--')}")
        right_layout.addWidget(meta)
        # Description
        desc = QTextEdit(self.series.get('plot', ''))
        desc.setReadOnly(True)
        desc.setMaximumHeight(80)
        right_layout.addWidget(desc)
        # Season selector
        self.season_combo = QComboBox()
        self.season_combo.currentIndexChanged.connect(self.season_changed)
        right_layout.addWidget(self.season_combo)
        # Episodes list
        self.episodes_list = QListWidget()
        self.episodes_list.itemDoubleClicked.connect(self.episode_double_clicked)
        right_layout.addWidget(self.episodes_list)
        layout.addLayout(right_layout)

    def load_seasons(self):
        # Get seasons from API (series_id)
        series_id = self.series.get('series_id')
        success, data = self.api_client.get_series_info(series_id)
        if success and data and 'seasons' in data:
            self.seasons = data['seasons']
            self.season_combo.clear()
            for season in self.seasons:
                # Defensive: support both 'season_num' and 'season_number' keys
                season_num = season.get('season_num') or season.get('season_number') or season.get('name') or str(season)
                self.season_combo.addItem(str(season_num))
            if self.seasons:
                # Use the same key as above
                first_season_num = self.seasons[0].get('season_num') or self.seasons[0].get('season_number') or self.seasons[0].get('name') or str(self.seasons[0])
                self.load_episodes(first_season_num)
        else:
            self.season_combo.clear()
            self.episodes_list.clear()

    def season_changed(self, idx):
        if idx >= 0 and idx < len(self.seasons):
            season = self.seasons[idx]
            season_num = season.get('season_num') or season.get('season_number') or season.get('name') or str(season)
            self.load_episodes(season_num)

    def load_episodes(self, season_num):
        # Get episodes for the selected season
        series_id = self.series.get('series_id')
        success, data = self.api_client.get_series_info(series_id)
        self.episodes_list.clear()
        if success and data and 'episodes' in data and isinstance(data['episodes'], list):
            # Defensive: flatten if episodes is a list of lists
            episodes_flat = []
            for ep in data['episodes']:
                if isinstance(ep, list):
                    episodes_flat.extend(ep)
                else:
                    episodes_flat.append(ep)
            episodes = [ep for ep in episodes_flat if isinstance(ep, dict) and str(ep.get('season')) == str(season_num)]
            for ep in episodes:
                title = ep.get('title', ep.get('name', ''))
                duration = ep.get('duration', '--')
                item = QListWidgetItem(f"Ep {ep.get('episode_num', '--')}: {title} ({duration} min)")
                item.setData(Qt.UserRole, ep)
                self.episodes_list.addItem(item)
        else:
            # Defensive: show all episodes if structure is unexpected
            if success and data and 'episodes' in data and isinstance(data['episodes'], (list, dict)):
                episodes = data['episodes']
                if isinstance(episodes, dict):
                    episodes = list(episodes.values())
                for ep in episodes:
                    if isinstance(ep, dict):
                        title = ep.get('title', ep.get('name', ''))
                        duration = ep.get('duration', '--')
                        item = QListWidgetItem(f"Ep {ep.get('episode_num', '--')}: {title} ({duration} min)")
                        item.setData(Qt.UserRole, ep)
                        self.episodes_list.addItem(item)

    def episode_double_clicked(self, item):
        ep = item.data(Qt.UserRole)
        # TODO: Play episode or show episode details
        QMessageBox.information(self, "Play Episode", f"Play: {ep['title']}")

class MovieDetailsDialog(QDialog):
    """Dialog for displaying movie details and playback options"""
    import os
    from src.utils.image_cache import ImageCache

    def __init__(self, movie, api_client, parent=None, main_window=None):
        super().__init__(parent)
        self.setWindowTitle(movie.get('name', 'Movie Details'))
        self.setMinimumWidth(900)
        self.movie = movie
        self.api_client = api_client
        self.main_window = main_window  # Reference to MainWindow
        self.setup_ui()

    def get_cached_pixmap(self, image_url, fallback_path):
        from PyQt5.QtGui import QPixmap
        from src.utils.image_cache import ImageCache
        ImageCache.ensure_cache_dir()
        cache_path = ImageCache.get_cache_path(image_url)
        pix = QPixmap()
        if os.path.exists(cache_path):
            pix.load(cache_path)
        else:
            image_data = None
            api_client = getattr(self, 'api_client', None)
            if not api_client and hasattr(self, 'main_window'):
                api_client = getattr(self.main_window, 'api_client', None)
            try:
                if api_client:
                    image_data = api_client.get_image_data(image_url)
                else:
                    print("[DEBUG] Could not find api_client for image download in details dialog!")
            except Exception as e:
                print(f"[DEBUG] Error downloading image for details: {e}")
            if image_data:
                pix.loadFromData(image_data)
                pix.save(cache_path)
        # If pix is still null, try to load the grid's cached image (if any)
        if pix.isNull():
            pix = QPixmap(fallback_path)
        return pix

    def setup_ui(self):
        layout = QHBoxLayout(self)
        # Poster
        poster = QLabel()
        poster.setAlignment(Qt.AlignTop)
        pix = QPixmap()
        # Try all possible image keys in order of preference
        image_url = self.movie.get('stream_icon') or self.movie.get('movie_image') or self.movie.get('cover_big')
        if image_url:
            pix = self.get_cached_pixmap(image_url, 'assets/movies.png')
        else:
            pix = QPixmap('assets/movies.png')
        if not pix.isNull():
            poster.setPixmap(pix.scaled(180, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        layout.addWidget(poster)
        # --- Favorites button under poster ---
        favorite_btn = QPushButton()
        favorite_btn.setFont(QFont('Arial', 16))
        favorite_btn.setStyleSheet("QPushButton { background: transparent; }")
        # Determine favorite state
        is_favorite = False
        main_window = self.main_window if hasattr(self, 'main_window') else None
        if main_window and hasattr(main_window, 'favorites'):
            favs = main_window.favorites
            is_favorite = any(fav.get('stream_id') == self.movie.get('stream_id') for fav in favs)
        def update_favorite_btn():
            if is_favorite:
                favorite_btn.setText("★")
                favorite_btn.setStyleSheet("QPushButton { color: gold; background: transparent; }")
                favorite_btn.setToolTip("Remove from favorites")
            else:
                favorite_btn.setText("☆")
                favorite_btn.setStyleSheet("QPushButton { color: white; background: transparent; }")
                favorite_btn.setToolTip("Add to favorites")
        update_favorite_btn()
        def on_favorite_clicked():
            nonlocal is_favorite
            if main_window and hasattr(main_window, 'toggle_favorite'):
                main_window.toggle_favorite(self.movie)
            else:
                # Fallback: emit signal if available
                if hasattr(self, 'add_to_favorites'):
                    if not is_favorite:
                        self.add_to_favorites.emit(self.movie)
                    else:
                        if hasattr(main_window, 'remove_from_favorites'):
                            main_window.remove_from_favorites(self.movie)
            is_favorite = not is_favorite
            update_favorite_btn()
        favorite_btn.clicked.connect(on_favorite_clicked)
        layout.addWidget(favorite_btn)
        # Metadata and actions
        right_layout = QVBoxLayout()
        # Title
        title = QLabel(self.movie.get('name', ''))
        title.setFont(QFont('Arial', 16, QFont.Bold))
        right_layout.addWidget(title)
        # Metadata
        meta = QLabel()
        meta.setText(f"Year: {self.movie.get('year', '--')} | Genre: {self.movie.get('genre', '--')} | Duration: {self.movie.get('duration', '--')} min")
        right_layout.addWidget(meta)
        # Director, cast, rating
        director = self.movie.get('director', '--')
        cast = self.movie.get('cast', '--')
        rating = self.movie.get('rating', '--')
        right_layout.addWidget(QLabel(f"Director: {director}"))
        if rating and rating != '--':
            right_layout.addWidget(QLabel(f"★ {rating}"))
        # Description
        desc = QTextEdit(self.movie.get('plot', ''))
        desc.setReadOnly(True)
        desc.setMaximumHeight(80)
        right_layout.addWidget(desc)
        # Cast photos (if available)
        cast_photos = self.movie.get('cast_photos', [])
        if cast_photos:
            cast_layout = QHBoxLayout()
            for cast_member in cast_photos:
                vbox = QVBoxLayout()
                photo_label = QLabel()
                photo_pix = QPixmap()
                if cast_member.get('photo_url'):
                    image_data = self.api_client.get_image_data(cast_member['photo_url'])
                    if image_data:
                        photo_pix.loadFromData(image_data)
                if not photo_pix.isNull():
                    photo_label.setPixmap(photo_pix.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                name_label = QLabel(cast_member.get('name', ''))
                name_label.setAlignment(Qt.AlignCenter)
                vbox.addWidget(photo_label)
                vbox.addWidget(name_label)
                cast_layout.addLayout(vbox)
            right_layout.addLayout(cast_layout)
        elif cast and cast != '--':
            right_layout.addWidget(QLabel(f"Cast: {cast}"))
        # Action buttons
        btn_layout = QHBoxLayout()
        play_btn = QPushButton("PLAY")
        play_btn.clicked.connect(self.play_movie)
        trailer_btn = QPushButton("WATCH TRAILER")
        trailer_btn.clicked.connect(self.watch_trailer)
        btn_layout.addWidget(play_btn)
        btn_layout.addWidget(trailer_btn)
        right_layout.addLayout(btn_layout)
        layout.addLayout(right_layout)

    def play_movie(self, movie_item):
        stream_id = movie_item.get('stream_id')
        container_extension = "mp4"
        try:
            success, vod_info = self.api_client.get_vod_info(stream_id)
            if (success and 'movie_data' in vod_info and 
                'container_extension' in vod_info['movie_data']):
                container_extension = vod_info['movie_data']['container_extension']
        except Exception:
            pass
        stream_url = self.api_client.get_movie_url(stream_id, container_extension)
        if stream_url:
            # Use the persistent player window from MainWindow
            if self.main_window and hasattr(self.main_window, 'player_window'):
                player_window = self.main_window.player_window
                # Pass the movie item to the player so it can handle favorites
                player_window.play(stream_url, movie_item)
                player_window.show()
                self.hide()
            else:
                QMessageBox.warning(self, "Error", "Player window not available.")
        else:
            QMessageBox.warning(self, "Error", "Unable to get movie stream URL.")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            # If player is in fullscreen, close dialog (which will also close fullscreen)
            if self.player.is_fullscreen:
                self.accept()
            else:
                # Otherwise, let default behavior happen
                super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)

    def watch_trailer(self):
        # TODO: Implement trailer playback if available
        QMessageBox.information(self, "Trailer", "Trailer playback not implemented.")
