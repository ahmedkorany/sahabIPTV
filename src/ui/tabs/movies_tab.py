"""
Movies tab for the application
"""
import time
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
                            QListWidget, QPushButton, QLineEdit, QMessageBox,
                            QFileDialog, QLabel, QProgressBar, QHeaderView, 
                            QTableWidget, QTableWidgetItem, QListWidgetItem, QFrame, QScrollArea, QGridLayout, QStackedLayout, QComboBox)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QFont
from src.ui.player import MediaPlayer
from src.utils.download import DownloadThread
from src.ui.widgets.dialogs import ProgressDialog
from src.ui.widgets.dialogs import MovieDetailsDialog
from src.ui.widgets.movie_details_widget import MovieDetailsWidget
from src.utils.helpers import load_image_async # Ensure it's imported if used elsewhere in this file
from PyQt5.QtWidgets import QPushButton
import hashlib
# import threading # No longer needed here if load_image_async is moved
# from PyQt5.QtCore import QMetaObject, Qt, Q_ARG # No longer needed here
import os
# from src.utils.image_cache import ensure_cache_dir, get_cache_path # No longer needed here
from src.utils.helpers import load_image_async # Import from helpers
from PyQt5.QtSvg import QSvgWidget
import sip # Add sip import for checking deleted QObjects
from src.api.tmdb import TMDBClient
import heapq

CACHE_DIR = 'assets/cache/images/'
LOADING_ICON = 'assets/loading.gif'

class DownloadItem:
    def __init__(self, name, save_path, download_thread=None):
        self.name = name
        self.save_path = save_path
        self
        self.status = 'active'  # active, paused, completed, error
        self.download_thread = download_thread
        self.error_message = None
        self.time_created = time.time()
        self.time_completed = None
        self.total_size = 0
        self.downloaded_size = 0
        self.speed = 0  # bytes per second
        self.estimated_time = 0  # seconds remaining
    
    def update_progress(self, progress, downloaded_size=0, total_size=0):
        self.progress = progress
        if total_size > 0:
            self.total_size = total_size
            self.downloaded_size = downloaded_size
            # Calculate download speed and estimated time
            if self.status == 'active' and progress > 0:
                now = time.time()
                elapsed_time = now - self.time_created
                # Use a moving window for speed calculation for smoother updates
                if not hasattr(self, '_last_update_time'):
                    self._last_update_time = now
                    self._last_downloaded_size = self.downloaded_size
                    self.speed = 0
                else:
                    delta_time = now - self._last_update_time
                    delta_bytes = self.downloaded_size - getattr(self, '_last_downloaded_size', 0)
                    if delta_time > 0 and delta_bytes >= 0:
                        inst_speed = delta_bytes / delta_time
                        # Use instant speed for more responsive UI
                        self.speed = inst_speed
                    self._last_update_time = now
                    self._last_downloaded_size = self.downloaded_size
                remaining_bytes = self.total_size - self.downloaded_size
                if self.speed > 0:
                    self.estimated_time = remaining_bytes / self.speed
                else:
                    self.estimated_time = 0
            else:
                self.speed = 0
                self.estimated_time = 0
        else:
            self.speed = 0
            self.estimated_time = 0

    def complete(self, save_path):
        self.status = 'completed'
        self.progress = 100
        self.time_completed = time.time()
        self.save_path = save_path
        
    def fail(self, error_message):
        self.status = 'error'
        self.error_message = error_message
        
    def pause(self):
        if self.status == 'active' and self.download_thread:
            self.status = 'paused'
            # Signal the download thread to pause
            if hasattr(self.download_thread, 'pause'):
                self.download_thread.pause()
    
    def resume(self):
        if self.status == 'paused' and self.download_thread:
            self.status = 'active'
            # Signal the download thread to resume
            if hasattr(self.download_thread, 'resume'):
                self.download_thread.resume()
    
    def cancel(self):
        if self.download_thread and hasattr(self.download_thread, 'cancel'):
            self.download_thread.cancel()
            self.status = 'cancelled'
    
    def get_formatted_speed(self):
        """Return formatted download speed (e.g., '1.2 MB/s')"""
        if self.speed == 0 or self.status in ['completed', 'error', 'cancelled']:
            return "--"
        units = ['B/s', 'KB/s', 'MB/s', 'GB/s']
        size = self.speed
        unit_index = 0
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        return f"{size:.2f} {units[unit_index]}"
    
    def get_formatted_time(self):
        """Return formatted estimated time remaining"""
        if self.estimated_time is None or self.estimated_time <= 0 or self.status in ['completed', 'error', 'cancelled']:
            return "--"
        seconds = int(self.estimated_time)
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            seconds %= 60
            return f"{minutes}m {seconds}s"
        else:
            hours = seconds // 3600
            seconds %= 3600
            minutes = seconds // 60
            return f"{hours}h {minutes}m"

class MoviesTab(QWidget):
    """Movies tab widget"""
    add_to_favorites = pyqtSignal(dict)
    add_to_downloads = pyqtSignal(object)  # Signal to add download to downloads tab
    
    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.main_window = parent
        self.details_widget = None
        self.movies = []
        self.all_movies = []  # Store all movies across categories
        self.filtered_movies = []  # Store filtered movies for search
        self.current_movie = None
        self.download_thread = None
        
        # Pagination
        self.current_page = 1
        self.total_pages = 1
        self.page_size = 30

        # Search index attributes
        self._movie_search_index = {}  # token -> set of indices
        self._movie_lc_names = []      # lowercased names for fallback
        
        self.setup_ui()
        self.main_window = None  # Will be set by the main window
    
        # Initialize TMDB client once for all details widgets
        self.tmdb_client = TMDBClient()  # Loads keys from .env automatically
    def setup_ui(self):
        layout = QVBoxLayout(self)
        # Search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search movies...")
        self.search_input.textChanged.connect(self.search_movies)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # Stacked widget for grid/details views
        from PyQt5.QtWidgets import QStackedWidget
        self.stacked_widget = QStackedWidget()

        # --- Left: Categories ---
        self.categories_list = QListWidget()
        self.categories_list.setMinimumWidth(220)
        self.categories_list.itemClicked.connect(self.category_clicked)
        self.categories_list.setStyleSheet("QListWidget::item:selected { background: #444; color: #fff; font-weight: bold; }")
        left_panel = QVBoxLayout()
        left_panel.addWidget(QLabel("Categories"))
        left_panel.addWidget(self.categories_list)
        left_widget = QWidget()
        left_widget.setLayout(left_panel)
        left_widget.setMaximumWidth(300)

        # --- Movie Grid ---
        self.movie_grid_widget = QWidget()
        self.movie_grid_layout = QGridLayout(self.movie_grid_widget)
        self.movie_grid_layout.setSpacing(16)
        self.movie_grid_layout.setContentsMargins(8, 8, 8, 8)
        self.movie_grid_widget.setStyleSheet("background: transparent;")
        self.movie_grid_scroll = QScrollArea()
        self.movie_grid_scroll.setWidgetResizable(True)
        self.movie_grid_scroll.setWidget(self.movie_grid_widget)
        grid_panel = QVBoxLayout()
        grid_panel.addWidget(QLabel("Movies"))
        grid_panel.addWidget(self.movie_grid_scroll)
        grid_widget = QWidget()
        grid_widget.setLayout(grid_panel)

        # Sorting panel (initially hidden)
        self.order_panel = QWidget()
        order_layout = QHBoxLayout(self.order_panel)
        order_label = QLabel("Order by:")
        self.order_combo = QComboBox()
        self.order_combo.addItems(["Default", "Date", "Rating", "Name"])
        self.order_combo.setCurrentIndex(0)
        self.order_combo.currentIndexChanged.connect(self.on_order_changed)
        self.sort_toggle = QPushButton("Desc")
        self.sort_toggle.setCheckable(True)
        self.sort_toggle.setChecked(True)
        self.sort_toggle.clicked.connect(self.on_sort_toggle)
        order_layout.addWidget(order_label)
        order_layout.addWidget(self.order_combo)
        order_layout.addWidget(self.sort_toggle)
        order_layout.addStretch(1)
        self.order_panel.setVisible(False)
        # Insert sorting panel just above the grid (movie_grid_scroll)
        grid_parent_layout = self.movie_grid_scroll.parentWidget().layout() if self.movie_grid_scroll.parentWidget() else self.layout()
        grid_parent_layout.insertWidget(grid_parent_layout.indexOf(self.movie_grid_scroll), self.order_panel)

        # Splitter for left (categories) and right (grid/details)
        from PyQt5.QtWidgets import QSplitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(grid_widget)
        splitter.setSizes([300, 900])
        splitter_widget = QWidget()
        splitter_layout = QVBoxLayout(splitter_widget)
        splitter_layout.setContentsMargins(0, 0, 0, 0)
        splitter_layout.addWidget(splitter)

        self.stacked_widget.addWidget(splitter_widget)  # Index 0: grid view
        self.details_widget = None
        self.stacked_widget.addWidget(QWidget())  # Placeholder for details

        layout.addWidget(self.stacked_widget)
        self.setup_pagination_controls()
        grid_panel.addWidget(self.pagination_panel)
        self.page_size = 32
        self.current_page = 1
        self.total_pages = 1
        self.update_pagination_controls()

    def on_order_changed(self):
        self.apply_sort_and_refresh()

    def on_sort_toggle(self):
        if self.sort_toggle.isChecked():
            self.sort_toggle.setText("Desc")
        else:
            self.sort_toggle.setText("Asc")
        self.apply_sort_and_refresh()

    def apply_sort_and_refresh(self):
        items = list(self.movies) if hasattr(self, 'movies') else []
        sort_field = self.order_combo.currentText()
        reverse = self.sort_toggle.isChecked()
        if sort_field == "Default":
            sorted_items = items
        else:
            if sort_field == "Date":
                key = lambda x: x.get('_sort_date', 0)
            elif sort_field == "Name":
                key = lambda x: x.get('_sort_name', '')
            elif sort_field == "Rating":
                key = lambda x: x.get('_sort_rating', 0)
            else:
                key = None
            if key:
                sorted_items = sorted(items, key=key, reverse=reverse)
            else:
                sorted_items = items
        # Update self.movies to the sorted list so pagination always follows the sort
        self.movies = sorted_items
        self.current_page = 1  # Reset to first page after sort
        self.display_current_page()

    def setup_pagination_controls(self):
        self.pagination_panel = QWidget()
        nav_layout = QHBoxLayout(self.pagination_panel)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setAlignment(Qt.AlignCenter)
        self.prev_page_button = QPushButton("Previous")
        self.next_page_button = QPushButton("Next")
        self.page_label = QLabel()
        self.prev_page_button.clicked.connect(self.go_to_previous_page)
        self.next_page_button.clicked.connect(self.go_to_next_page)
        nav_layout.addWidget(self.prev_page_button)
        nav_layout.addWidget(self.page_label)
        nav_layout.addWidget(self.next_page_button)
        self.pagination_panel.setVisible(False)

    def load_categories(self):
        """Load movie categories from the API"""
        if sip.isdeleted(self.categories_list):
            print("[MoviesTab] categories_list widget has been deleted, skipping clear().")
            return
        self.categories_list.clear()
        self.categories = []
        success, data = self.api_client.get_vod_categories()
        if success:
            self.categories = data
            # Add "ALL" category at the top
            all_item = QListWidgetItem("ALL")
            all_item.setData(Qt.UserRole, None) # None for ALL category_id
            self.categories_list.addItem(all_item)

            # Add "Favorites" category
            favorites_item = QListWidgetItem("Favorites")
            favorites_item.setData(Qt.UserRole, "favorites") # Special ID for favorites
            self.categories_list.addItem(favorites_item)

            for category in data:
                count = category.get('num', '')
                if count and str(count).strip() not in ('', '0'):
                    item = QListWidgetItem(f"{category['category_name']} ({count})")
                else:
                    item = QListWidgetItem(f"{category['category_name']}")
                item.setData(Qt.UserRole, category['category_id'])
                self.categories_list.addItem(item)
        else:
            QMessageBox.warning(self, "Error", f"Failed to load categories: {data}")

    def category_clicked(self, item):
        category_id = item.data(Qt.UserRole)
        # Reset sorting controls to default
        self.order_combo.setCurrentIndex(0)  # Default
        self.sort_toggle.setChecked(True)    # Desc
        self.sort_toggle.setText("Desc")
        if category_id == "favorites":
            self.load_favorite_movies()
        else:
            self.load_movies(category_id)
        # Show sorting panel for all except 'favorites'
        self.order_panel.setVisible(category_id != "favorites")

    def load_movies(self, category_id):
        """Load movies for the selected category and display as grid"""
        self.movies = []
        for i in reversed(range(self.movie_grid_layout.count())):
            widget = self.movie_grid_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        if category_id is None:
            # ALL category: load all movies
            if not self.all_movies: # Check if all_movies is already populated
                all_movies_temp = []
                for cat in self.categories:
                    # Ensure category_id is not None or 'favorites' before fetching
                    # self.categories contains API category dicts, so cat['category_id'] won't be 'favorites'.
                    # This check is harmless but redundant for 'favorites' if self.categories is clean.
                    if cat.get('category_id') is not None and cat.get('category_id') != 'favorites':
                        success, data = self.api_client.get_vod_streams(cat['category_id'])
                        if success:
                            all_movies_temp.extend(data)
                self.all_movies = all_movies_temp # Store all movies
            self.movies = list(self.all_movies) # Use a copy for current display
        else:
            # This branch handles specific category_id (not None and not 'favorites')
            success, data = self.api_client.get_vod_streams(category_id)
            if success:
                self.movies = data
            else:
                QMessageBox.warning(self, "Error", f"Failed to load movies: {data}")
        self.current_page = 1
        self.build_movie_search_index()
        self.display_current_page()

    def load_favorite_movies(self):
        """Load and display favorite movies using the SeriesTab approach."""
        if not self.main_window or not hasattr(self.main_window, 'favorites'):
            QMessageBox.warning(self, "Error", "Favorites list not available.")
            self.movies = []
            self.current_page = 1
            self.display_current_page()
            return

        # Filter favorite items that are movies
        self.movies = [
            fav for fav in self.main_window.favorites
            if fav.get('stream_type') == 'movie'
        ]

        self.current_page = 1  # Reset to first page for favorites
        self.build_movie_search_index()  # Build index after loading
        # display_current_page will handle pagination and display
        # It should also update total_pages based on self.movies
        self.display_current_page()

    def build_movie_search_index(self):
        """Builds a token-based search index for fast lookup."""
        import unicodedata
        self._movie_search_index = {}
        self._movie_lc_names = []
        # Precompute sort keys for each movie
        for mv in self.movies:
            # Normalize name for sorting as well, though primary use is search
            normalized_sort_name = unicodedata.normalize('NFKD', mv.get('name', '').lower())
            mv['_sort_name'] = normalized_sort_name
            try:
                mv['_sort_date'] = int(mv.get('added', 0))
            except Exception:
                mv['_sort_date'] = 0
            try:
                mv['_sort_rating'] = float(mv.get('rating', 0))
            except Exception:
                mv['_sort_rating'] = 0.0
        for idx, mv in enumerate(self.movies):
            name_lc_normalized = unicodedata.normalize('NFKD', mv.get('name', '').lower())
            self._movie_lc_names.append(name_lc_normalized) # Store normalized names
            tokens = set(name_lc_normalized.split()) # Tokenize normalized name
            for token in tokens:
                if token not in self._movie_search_index:
                    self._movie_search_index[token] = set()
                self._movie_search_index[token].add(idx)

    def display_movie_grid(self, movies):
        """Display movies as a grid of tiles"""
        # Clear previous grid
        for i in reversed(range(self.movie_grid_layout.count())):
            widget = self.movie_grid_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        if not movies:
            empty_label = QLabel("This category doesn't contain any Movie")
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setStyleSheet("color: #aaa; font-size: 18px; padding: 40px;")
            self.movie_grid_layout.addWidget(empty_label, 0, 0, 1, 4)
            # Hide sorting panel if no movies to show
            self.order_panel.setVisible(False)
            return
        cols = 4
        row = 0
        col = 0
        main_window = self.main_window if hasattr(self, 'main_window') else None
        for movie in movies:
            tile = QFrame()
            tile.setFrameShape(QFrame.StyledPanel)
            tile.setStyleSheet("background: #222; border-radius: 12px;")
            tile_layout = QVBoxLayout(tile)
            tile_layout.setContentsMargins(0, 0, 0, 0)
            tile_layout.setSpacing(0)
            # Movie poster with overlay using absolute positioning
            poster_container = QWidget()
            poster_container.setFixedSize(100, 140)
            poster = QLabel(poster_container)
            poster.setAlignment(Qt.AlignCenter)
            poster.setGeometry(0, 0, 100, 140)
            default_pix = QPixmap('assets/movies.png')
            if movie.get('stream_icon'):
                load_image_async(movie['stream_icon'], poster, default_pix, update_size=(100, 140), main_window=main_window)
            else:
                poster.setPixmap(default_pix.scaled(100, 140, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            # Overlay 'new.png' if the movie is new
            is_recent = False
            if movie.get('added'):
                from datetime import datetime, timedelta
                try:
                    added_time = datetime.fromtimestamp(int(movie['added']))
                    if (datetime.now() - added_time) < timedelta(days=7):
                        is_recent = True
                except Exception:
                    pass
            if is_recent:
                new_icon = QLabel(poster_container)
                new_icon.setPixmap(QPixmap('assets/new.png').scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                new_icon.setStyleSheet("background: transparent;")
                new_icon.move(0, 0)
                new_icon.raise_()
            tile_layout.addWidget(poster_container, alignment=Qt.AlignCenter)
            # Movie name
            name = QLabel(movie['name'])
            name.setAlignment(Qt.AlignCenter)
            name.setWordWrap(True)
            name.setFont(QFont('Arial', 11, QFont.Bold))
            name.setStyleSheet("color: #fff;")
            tile_layout.addWidget(name)
            # Rating (if available)
            if movie.get('rating'):
                rating = QLabel(f"★ {movie['rating']}")
                rating.setAlignment(Qt.AlignCenter)
                rating.setStyleSheet("color: gold;")
                tile_layout.addWidget(rating)
            tile.mousePressEvent = lambda e, mv=movie: self.movie_tile_clicked(mv)
            self.movie_grid_layout.addWidget(tile, row, col)
            col += 1
            if col >= cols:
                col = 0
                row += 1
        # Hide sorting panel if no movies to show
        self.order_panel.setVisible(bool(movies))

    def show_movie_details(self, movie):
        # Remove old details widget if present
        if self.details_widget:
            self.stacked_widget.removeWidget(self.details_widget)
            self.details_widget.deleteLater()
            self.details_widget = None
        # Create a new details widget using MovieDetailsWidget
        self.details_widget = MovieDetailsWidget(
            movie,
            api_client=self.api_client,
            main_window=self.main_window,
            tmdb_client=self.tmdb_client,
            parent=self
        )
        self.details_widget.back_btn.clicked.connect(self.show_movie_grid)
        self.details_widget.play_clicked.connect(self._play_movie_from_details)
        self.details_widget.trailer_clicked.connect(self._play_trailer)
        self.details_widget.favorite_toggled.connect(self.add_to_favorites.emit)
        self.stacked_widget.addWidget(self.details_widget)
        self.stacked_widget.setCurrentWidget(self.details_widget)

    def show_movie_grid(self):
        self.stacked_widget.setCurrentIndex(0)

    def movie_tile_clicked(self, movie):
        """Handle movie tile click"""
        self.current_movie = movie
        self.show_movie_details(movie)

    def _play_movie_from_details(self, movie):
        # Reuse the logic from the dialog, but adapted for tab context
        main_window = self.window()
        from src.ui.widgets.dialogs import MovieDetailsDialog
        dlg = MovieDetailsDialog(movie, self.api_client, parent=self, main_window=main_window)
        # Create movie item with necessary information for favorites
        movie_item = {
            'name': movie['name'],
            'stream_id': movie['stream_id'],
            'container_extension': movie['container_extension'],
            'stream_type': 'movie'
        }
        dlg.play_movie(movie_item)  # Play directly, don't show dialog

    def _play_trailer(self, trailer_url):
        main_window = self.window()
        if hasattr(main_window, 'player_window'):
            player_window = main_window.player_window
            player_window.play(trailer_url, {'name': 'Trailer', 'stream_type': 'trailer'})
            player_window.show()
        else:
            QMessageBox.warning(self, "Error", "Player window not available.")

    def search_movies(self, text):
        import unicodedata
        # Only search if 3+ chars, otherwise always show full list for the current category
        if not self.movies:
            return
        
        normalized_text = unicodedata.normalize('NFKD', text.strip().lower())
        
        if len(normalized_text) < 1: # Allow searching for single Arabic characters if needed, adjust if 3 char min is strict
            self.display_current_page()
            return
            
        # Token search: Use normalized_text for token lookup
        # We assume tokens in _movie_search_index are already normalized from build_movie_search_index
        # If the normalized_text itself is a single token and exists in the index:
        if ' ' not in normalized_text and normalized_text in self._movie_search_index:
            indices = self._movie_search_index[normalized_text]
            filtered = [self.movies[i] for i in indices]
        else:
            # Fallback: substring search using normalized text and normalized names
            # _movie_lc_names should contain pre-normalized names from build_movie_search_index
            max_results = 200
            filtered = []
            for mv, normalized_movie_name in zip(self.movies, self._movie_lc_names):
                if normalized_text in normalized_movie_name:
                    filtered.append(mv)
                    if len(filtered) >= max_results:
                        break
        self.display_movie_grid(filtered)

    def paginate_items(self, items, page):
        total_items = len(items)
        total_pages = max(1, (total_items + self.page_size - 1) // self.page_size)
        if page < 1:
            page = 1
        if page > total_pages:
            page = total_pages
        start = (page - 1) * self.page_size
        end = min(start + self.page_size, total_items)
        return items[start:end], total_pages

    def update_pagination_controls(self):
        if self.total_pages > 1:
            self.page_label.setText(f"Page {self.current_page} of {self.total_pages}")
            self.prev_page_button.setEnabled(self.current_page > 1)
            self.next_page_button.setEnabled(self.current_page < self.total_pages)
            self.pagination_panel.setVisible(True)
        else:
            self.pagination_panel.setVisible(False)
        # Update pagination controls visibility
        if hasattr(self, 'prev_page_button') and hasattr(self, 'next_page_button'):
            self.prev_page_button.setVisible(self.current_page > 1)
            self.next_page_button.setVisible(self.current_page < self.total_pages)

    def go_to_previous_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.display_current_page()

    def go_to_next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.display_current_page()

    def display_current_page(self):
        for i in reversed(range(self.movie_grid_layout.count())):
            widget = self.movie_grid_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        page_items, self.total_pages = self.paginate_items(self.movies, self.current_page)
        self.display_movie_grid(page_items)
        self.update_pagination_controls()

    def movie_double_clicked(self, item):
        """Handle movie double-click"""
        movie_item = {
            'name': item['name'],
            'stream_id': item['stream_id'],
            'container_extension': item['container_extension'],
            'stream_url': item['stream_url'],
            'stream_type': 'movie'
        }
        self.play_movie(movie_item)
    
    def play_movie(self):
        if(self.player.play_started == False):
            """Play the selected movie"""
            if not self.movies_list.currentItem():
                QMessageBox.warning(self, "Error", "No movie selected")
                return
            
            movie_name = self.movies_list.currentItem().text()
            movie = None
            for m in self.filtered_movies:
                if m['name'] == movie_name:
                    movie = m
                    break
            
            if not movie:
                return
            
            stream_id = movie['stream_id']
            
            # Get container extension from VOD info
            container_extension = "mp4"  # Default extension
            success, vod_info = self.api_client.get_vod_info(stream_id)
            if success and 'movie_data' in vod_info and 'container_extension' in vod_info['movie_data']:
                container_extension = vod_info['movie_data']['container_extension']
            
            stream_url = self.api_client.get_movie_url(stream_id, container_extension)
            
            if self.player.play(stream_url):
                self.current_movie = {
                    'name': movie['name'],
                    'stream_url': stream_url,
                    'stream_id': stream_id,
                    'stream_type': 'movie',
                    'container_extension': container_extension
                }
                self.player.controls.play_pause_button.clicked.connect(self.play_movie)
            else:
                self.player.play_pause(False)
    
    def download_movie(self):
        """Download the selected movie"""
        if not self.movies_list.currentItem():
            QMessageBox.warning(self, "Error", "No movie selected")
            return
        
        movie_name = self.movies_list.currentItem().text()
        movie = None
        for m in self.filtered_movies:
            if m['name'] == movie_name:
                movie = m
                break
        
        if not movie:
            return
        
        stream_id = movie['stream_id']
        
        # Get container extension from VOD info
        container_extension = "mp4"  # Default extension
        success, vod_info = self.api_client.get_vod_info(stream_id)
        if success and 'movie_data' in vod_info and 'container_extension' in vod_info['movie_data']:
            container_extension = vod_info['movie_data']['container_extension']
        
        stream_url = self.api_client.get_movie_url(stream_id, container_extension)
        
        # Ask for save location
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Movie", f"{movie_name}.{container_extension}", f"Video Files (*.{container_extension})"
        )
        
        if not save_path:
            return
        
        # Create download item
        download_item = DownloadItem(movie_name, save_path)
        
        # Start download thread
        self.download_thread = DownloadThread(stream_url, save_path, self.api_client.headers)
        download_item.download_thread = self.download_thread
        
        # Connect signals
        self.download_thread.progress_update.connect(
            lambda progress, downloaded=0, total=0: self.update_download_progress(download_item, progress, downloaded, total))
        self.download_thread.download_complete.connect(
            lambda path: self.download_finished(download_item, path))
        self.download_thread.download_error.connect(
            lambda error: self.download_error(download_item, error))
        
        # Add to downloads tab
        if self.main_window and hasattr(self.main_window, 'downloads_tab'):
            self.main_window.downloads_tab.add_download(download_item)
        
        self.download_thread.start()
    
    def update_download_progress(self, download_item, progress, downloaded_size=0, total_size=0):
        """Update download progress in the downloads tab"""
        if download_item:
            # Update the download item
            download_item.update_progress(progress, downloaded_size, total_size)
            
            # Update the UI in the downloads tab
            if self.main_window and hasattr(self.main_window, 'downloads_tab'):
                self.main_window.downloads_tab.update_download_item(download_item)
            
    
    def download_finished(self, download_item, save_path):
        """Handle download completion"""
        if download_item:
            # Update the download item
            download_item.complete(save_path)
            
            # Update the UI in the downloads tab
            if self.main_window and hasattr(self.main_window, 'downloads_tab'):
                self.main_window.downloads_tab.update_download_item(download_item)
        
        
        QMessageBox.information(self, "Download Complete", f"File saved to: {save_path}")
    
    def download_error(self, download_item, error_message):
        """Handle download error"""
        if download_item:
            # Update the download item
            download_item.fail(error_message)
            
            # Update the UI in the downloads tab
            if self.main_window and hasattr(self.main_window, 'downloads_tab'):
                self.main_window.downloads_tab.update_download_item(download_item)
        
        
        QMessageBox.critical(self, "Download Error", error_message)
    
    def cancel_download(self):
        """Cancel the current download"""
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.cancel()
    
    def add_to_favorites_clicked(self):
        """Add current movie to favorites"""
        if not self.current_movie:
            QMessageBox.warning(self, "Error", "No movie is playing")
            return
        movie = dict(self.current_movie)
        if 'name' not in movie:
            movie['name'] = movie.get('title', 'Movie')
        self.add_to_favorites.emit(movie)
