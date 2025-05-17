"""
Movies tab for the application
"""
import time
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
                            QListWidget, QPushButton, QLineEdit, QMessageBox,
                            QFileDialog, QLabel, QProgressBar, QHeaderView, 
                            QTableWidget, QTableWidgetItem, QListWidgetItem, QFrame, QScrollArea, QGridLayout, QStackedLayout)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QFont
from src.ui.player import MediaPlayer
from src.utils.download import DownloadThread
from src.ui.widgets.dialogs import ProgressDialog
from src.ui.widgets.dialogs import MovieDetailsDialog
from PyQt5.QtWidgets import QPushButton
import hashlib
import threading
from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
import os
from src.utils.image_cache import ensure_cache_dir, get_cache_path
from PyQt5.QtSvg import QSvgWidget

CACHE_DIR = 'assets/cache/'
LOADING_ICON = 'assets/loading.gif'

def get_api_client_from_label(label, main_window):
    # Try to get api_client from main_window, fallback to traversing parents
    if main_window and hasattr(main_window, 'api_client'):
        return main_window.api_client
    # Fallback: traverse up the parent chain
    parent = label.parent()
    for _ in range(5):
        if parent is None:
            break
        if hasattr(parent, 'api_client'):
            return parent.api_client
        parent = parent.parent() if hasattr(parent, 'parent') else None
    return None

def load_image_async(image_url, label, default_pixmap, update_size=(100, 140), main_window=None, loading_counter=None):
    ensure_cache_dir()
    cache_path = get_cache_path(image_url)
    def set_pixmap(pixmap):
        label.setPixmap(pixmap.scaled(*update_size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    def worker():
        from PyQt5.QtGui import QPixmap
       # print(f"[DEBUG] Start loading image: {image_url}")
        if main_window and hasattr(main_window, 'loading_icon_controller'):
            main_window.loading_icon_controller.show_icon.emit()
        pix = QPixmap()
        if os.path.exists(cache_path):
            #print(f"[DEBUG] Image found in cache: {cache_path}")
            pix.load(cache_path)
        else:
            #print(f"[DEBUG] Downloading image: {image_url}")
            image_data = None
            api_client = get_api_client_from_label(label, main_window)
            try:
                if api_client:
                    image_data = api_client.get_image_data(image_url)
                else:
                    print("[DEBUG] Could not find api_client for image download!")
            except Exception as e:
                print(f"[DEBUG] Error downloading image: {e}")
            if image_data:
                loaded = pix.loadFromData(image_data)
                if loaded and not pix.isNull():
                    try:
                        saved = pix.save(cache_path)
                        #print(f"[DEBUG] Image downloaded and cached: {cache_path}, save result: {saved}")
                    except Exception as e:
                        print(f"[DEBUG] Error saving image to cache: {e}")
                else:
                    print(f"[DEBUG] Failed to load image from data for: {image_url}")
        if not pix or pix.isNull():
            pix = default_pixmap
        QMetaObject.invokeMethod(label, "setPixmap", Qt.QueuedConnection, Q_ARG(QPixmap, pix.scaled(*update_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)))
        if loading_counter is not None:
            loading_counter['count'] -= 1
            if loading_counter['count'] <= 0 and main_window and hasattr(main_window, 'loading_icon_controller'):
                main_window.loading_icon_controller.hide_icon.emit()
        else:
            if main_window and hasattr(main_window, 'loading_icon_controller'):
                main_window.loading_icon_controller.hide_icon.emit()
        #print(f"[DEBUG] Finished loading image: {image_url}")
    # Set cached or placeholder immediately
    if os.path.exists(cache_path):
        pix = QPixmap()
        pix.load(cache_path)
        set_pixmap(pix)
    else:
        set_pixmap(default_pixmap)
        if loading_counter is not None:
            loading_counter['count'] += 1
        threading.Thread(target=worker, daemon=True).start()

class DownloadItem:
    def __init__(self, name, save_path, download_thread=None):
        self.name = name
        self.save_path = save_path
        self.progress = 0
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
        self.movies = []
        self.all_movies = []  # Store all movies across categories
        self.filtered_movies = []  # Store filtered movies for search
        self.current_movie = None
        self.download_thread = None
        
        # Pagination
        self.current_page = 1
        self.total_pages = 1
        self.page_size = 30
        
        self.setup_ui()
        self.main_window = None  # Will be set by the main window
    
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
        self.categories_list.clear()
        self.categories = []
        success, data = self.api_client.get_vod_categories()
        if success:
            self.categories = data
            # Add "ALL" category at the top
            all_item = QListWidgetItem("ALL")
            all_item.setData(Qt.UserRole, None)
            self.categories_list.addItem(all_item)
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
        self.load_movies(category_id)

    def load_movies(self, category_id):
        """Load movies for the selected category and display as grid"""
        self.movies = []
        for i in reversed(range(self.movie_grid_layout.count())):
            widget = self.movie_grid_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        if category_id is None:
            # ALL category: load all movies
            all_movies = []
            for cat in self.categories:
                success, data = self.api_client.get_vod_streams(cat['category_id'])
                if success:
                    all_movies.extend(data)
            self.movies = all_movies
        else:
            success, data = self.api_client.get_vod_streams(category_id)
            if success:
                self.movies = data
            else:
                QMessageBox.warning(self, "Error", f"Failed to load movies: {data}")
        self.current_page = 1
        self.display_current_page()

    def display_movie_grid(self, movies):
        """Display movies as a grid of tiles"""
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

    def show_movie_details(self, movie):
        # Remove old details widget if present
        if self.details_widget:
            self.stacked_widget.removeWidget(self.details_widget)
            self.details_widget.deleteLater()
            self.details_widget = None
        # Create a new details widget (not a dialog)
        self.details_widget = self._create_details_widget(movie)
        self.stacked_widget.addWidget(self.details_widget)
        self.stacked_widget.setCurrentWidget(self.details_widget)

    def _create_details_widget(self, movie):
        from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QTextEdit
        from PyQt5.QtGui import QPixmap, QFont
        details = QWidget()
        layout = QHBoxLayout(details)
        # --- Left: Poster and Back button ---
        left_layout = QVBoxLayout()
        # Back button at the top of the poster list
        back_btn = QPushButton("← Back")
        back_btn.setFixedWidth(80)
        back_btn.clicked.connect(self.show_movie_grid)
        left_layout.addWidget(back_btn, alignment=Qt.AlignLeft)
        # Poster
        poster = QLabel()
        poster.setAlignment(Qt.AlignTop)
        pix = QPixmap()
        if movie.get('stream_icon'):
            load_image_async(movie['stream_icon'], poster, QPixmap('assets/movies.png'), update_size=(180, 260))
        else:
            poster.setPixmap(QPixmap('assets/movies.png').scaled(180, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        left_layout.addWidget(poster)
        layout.addLayout(left_layout)
        # --- Right: Metadata and actions ---
        right_layout = QVBoxLayout()
        # Title
        title = QLabel(movie.get('name', ''))
        title.setFont(QFont('Arial', 16, QFont.Bold))
        right_layout.addWidget(title)
        # Metadata
        meta = QLabel()
        meta.setText(f"Year: {movie.get('year', '--')} | Genre: {movie.get('genre', '--')} | Duration: {movie.get('duration', '--')} min")
        right_layout.addWidget(meta)
        # Director, cast, rating
        director = movie.get('director', '--')
        cast = movie.get('cast', '--')
        rating = movie.get('rating', '--')
        right_layout.addWidget(QLabel(f"Director: {director}"))
        if rating and rating != '--':
            right_layout.addWidget(QLabel(f"★ {rating}"))
        # Description
        desc = QTextEdit(movie.get('plot', ''))
        desc.setReadOnly(True)
        desc.setMaximumHeight(80)
        right_layout.addWidget(desc)
        # Cast photos (if available)
        cast_photos = movie.get('cast_photos', [])
        if cast_photos:
            cast_layout = QHBoxLayout()
            for cast_member in cast_photos:
                vbox = QVBoxLayout()
                photo_label = QLabel()
                photo_pix = QPixmap()
                if cast_member.get('photo_url'):
                    load_image_async(cast_member['photo_url'], photo_label, QPixmap(), update_size=(48, 48))
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
        play_btn.clicked.connect(lambda: self._play_movie_from_details(movie))
        btn_layout.addWidget(play_btn)
        # Show trailer button only if available
        trailer_url = movie.get('trailer_url')
        # Try to get trailer_url from detailed info if not present
        stream_id = movie.get('stream_id')
        try:
            success, vod_info = self.api_client.get_vod_info(stream_id)
            if success and vod_info:
                movie_info = vod_info.get('info', {})
                if not trailer_url:
                    trailer_url = movie_info.get('trailer_url')
        except Exception:
            pass
        if trailer_url:
            trailer_btn = QPushButton("WATCH TRAILER")
            trailer_btn.clicked.connect(lambda: self._play_trailer(trailer_url))
            btn_layout.addWidget(trailer_btn)
        right_layout.addLayout(btn_layout)
        
        # Fetch detailed metadata
        stream_id = movie.get('stream_id')
        #print(f"Debug: Fetching detailed metadata for stream_id: {stream_id}")  # Log to console for debugging
        try:
            success, vod_info = self.api_client.get_vod_info(stream_id)
            #print(f"Debug: vod_info: {vod_info}")  # Log to console for debugging
            if success and vod_info:
                movie_info = vod_info['info']
                #print("Detailed Movie info Metadata:", movie_info)  # Log to console for debugging

                # Update UI with detailed metadata
                meta.setText(f"Year: {movie_info.get('releasedate', '--')} \nGenre: {movie_info.get('genre', '--')} \nDuration: {movie_info.get('duration', '--')}")
                director = movie_info.get('director', '--')
                cast = ', '.join(movie_info.get('cast', [])) if isinstance(movie_info.get('cast'), list) else movie_info.get('cast', '--')
                desc.setPlainText(movie_info.get('plot', ''))

                # Update director and cast labels
                right_layout.addWidget(QLabel(f"Director: {director}"))
                right_layout.addWidget(QLabel(f"Cast: {cast}"))

                # Update poster if available
                if 'movie_image' in vod_info['info']:
                    image_data = self.api_client.get_image_data(vod_info['info']['movie_image'])
                    if image_data:
                        pix = QPixmap()
                        pix.loadFromData(image_data)
                        if not pix.isNull():
                            poster.setPixmap(pix.scaled(180, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception as e:
            print("Error fetching detailed metadata:", e)
        
        layout.addLayout(right_layout)
        return details

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
        """Search movies based on input text (grid view)"""
        if not self.movies:
            return
        text = text.lower()
        filtered = [mv for mv in self.movies if text in mv['name'].lower()]
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
