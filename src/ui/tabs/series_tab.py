"""
Series tab for the application
"""
import time
import os
import hashlib
import threading
import heapq
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
                            QListWidget, QPushButton, QLineEdit, QMessageBox,
                            QFileDialog, QLabel, QProgressBar, QListWidgetItem, QFrame, QScrollArea, QGridLayout, QStackedWidget, QStackedLayout, QComboBox)
from PyQt5.QtCore import Qt, pyqtSignal, QMetaObject, Q_ARG
from PyQt5.QtGui import QPixmap, QFont, QIcon
from PyQt5.QtSvg import QSvgWidget
from src.ui.player import MediaPlayer
from src.utils.download import DownloadThread, BatchDownloadThread
from src.ui.widgets.dialogs import ProgressDialog
from src.utils.image_cache import ensure_cache_dir, get_cache_path

CACHE_DIR = 'assets/cache/'

def get_api_client_from_label(label, main_window):
    if main_window and hasattr(main_window, 'api_client'):
        return main_window.api_client
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
        #print(f"[DEBUG] Start loading image: {image_url}")
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
                pix.loadFromData(image_data)
                pix.save(cache_path)
                #print(f"[DEBUG] Image downloaded and cached: {cache_path}")
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
                elapsed_time = time.time() - self.time_created
                if elapsed_time > 0:
                    self.speed = downloaded_size / elapsed_time
                    remaining_bytes = total_size - downloaded_size
                    if self.speed > 0:
                        self.estimated_time = remaining_bytes / self.speed
    
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
        if self.speed == 0:
            return "0 B/s"
        
        units = ['B/s', 'KB/s', 'MB/s', 'GB/s']
        size = self.speed
        unit_index = 0
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
            
        return f"{size:.2f} {units[unit_index]}"
    
    def get_formatted_time(self):
        """Return formatted estimated time remaining"""
        if self.estimated_time <= 0:
            return "calculating..."
            
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

class SeriesTab(QWidget):
    add_to_favorites = pyqtSignal(dict)
    add_to_downloads = pyqtSignal(object)

    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.series = []
        self.all_series = []  # Store all series across categories
        self.current_series = None
        self.setup_ui()
        self.main_window = None
        self._series_search_index = {}  # token -> set of indices
        self._series_lc_names = []      # lowercased names for fallback
        self._series_sort_cache = {}  # (sort_field, reverse) -> sorted list

    def setup_ui(self):
        layout = QVBoxLayout(self)
        # Search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search series...")
        self.search_input.textChanged.connect(self.search_series)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # Stacked widget for grid/details views
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

        # --- Series Grid ---
        self.series_grid_widget = QWidget()
        self.series_grid_layout = QGridLayout(self.series_grid_widget)
        self.series_grid_layout.setSpacing(16)
        self.series_grid_layout.setContentsMargins(8, 8, 8, 8)
        self.series_grid_widget.setStyleSheet("background: transparent;")
        self.series_grid_scroll = QScrollArea()
        self.series_grid_scroll.setWidgetResizable(True)
        self.series_grid_scroll.setWidget(self.series_grid_widget)
        grid_panel = QVBoxLayout()
        grid_panel.addWidget(QLabel("Series"))
        grid_panel.addWidget(self.series_grid_scroll)
        self.setup_pagination_controls()
        grid_panel.addWidget(self.pagination_panel)
        grid_widget = QWidget()
        grid_widget.setLayout(grid_panel)

        # Splitter for left (categories) and right (grid/details)
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
        self.page_size = 32
        self.current_page = 1
        self.total_pages = 1
        self.update_pagination_controls()
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
        # Insert sorting panel just above the grid (series_grid_scroll)
        grid_parent_layout = self.series_grid_scroll.parentWidget().layout() if self.series_grid_scroll.parentWidget() else self.layout()
        grid_parent_layout.insertWidget(grid_parent_layout.indexOf(self.series_grid_scroll), self.order_panel)

        self.setLayout(layout)

    def show_series_details(self, series):
        # Remove old details widget if present
        if self.details_widget:
            self.stacked_widget.removeWidget(self.details_widget)
            self.details_widget.deleteLater()
            self.details_widget = None
        # Create a new details widget (not a dialog)
        self.details_widget = self._create_details_widget(series)
        self.stacked_widget.addWidget(self.details_widget)
        self.stacked_widget.setCurrentWidget(self.details_widget)

    def _create_details_widget(self, series):
        from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton, QListWidget
        from PyQt5.QtGui import QPixmap, QFont
        details = QWidget()
        layout = QHBoxLayout(details)
        # --- Left: Poster and Back button ---
        left_layout = QVBoxLayout()
        back_btn = QPushButton("← Back")
        back_btn.setFixedWidth(80)
        back_btn.clicked.connect(self.show_series_grid)
        left_layout.addWidget(back_btn, alignment=Qt.AlignLeft)
        # Poster
        poster = QLabel()
        poster.setAlignment(Qt.AlignTop)
        pix = QPixmap()
        series_cover_url = series.get('cover') # Store for favorite item
        if series_cover_url:
            image_data = self.api_client.get_image_data(series_cover_url)
            if image_data:
                pix.loadFromData(image_data)
        if not pix or pix.isNull():
            pix = QPixmap('assets/series.png')
        if not pix.isNull():
            poster.setPixmap(pix.scaled(180, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        left_layout.addWidget(poster)

        # Favorite button
        self.favorite_series_btn = QPushButton()
        self.favorite_series_btn.setFixedWidth(180) # Match poster width
        # Pass the original series dict from the grid, which includes 'cover'
        self._update_favorite_series_button_text(series) 
        self.favorite_series_btn.clicked.connect(lambda _, s=series: self._toggle_favorite_series(s))
        left_layout.addWidget(self.favorite_series_btn)

        layout.addLayout(left_layout)
        # --- Right: Metadata, seasons, episodes ---
        right_layout = QVBoxLayout()
        # Title
        title = QLabel(series.get('name', ''))
        title.setFont(QFont('Arial', 16, QFont.Bold))
        right_layout.addWidget(title)
        # Metadata
        meta = QLabel()
        meta.setText(f"Year: {series.get('year', '--')} | Genre: {series.get('genre', '--')}")
        right_layout.addWidget(meta)
        # Description
        desc = QTextEdit(series.get('plot', ''))
        desc.setReadOnly(True)
        desc.setMaximumHeight(80)
        right_layout.addWidget(desc)
        # Seasons and episodes
        self.seasons_list = QListWidget()
        self.episodes_list = QListWidget()
        self.seasons_list.itemClicked.connect(self.season_clicked)
        self.episodes_list.itemDoubleClicked.connect(self.episode_double_clicked)
        right_layout.addWidget(QLabel("Seasons"))
        right_layout.addWidget(self.seasons_list)
        right_layout.addWidget(QLabel("Episodes"))
        right_layout.addWidget(self.episodes_list)
        # Play button for selected episode
        self.play_episode_btn = QPushButton("Play Episode")
        self.play_episode_btn.setEnabled(False)
        self.play_episode_btn.clicked.connect(self.play_selected_episode)
        right_layout.addWidget(self.play_episode_btn)
        self.episodes_list.currentItemChanged.connect(self.update_play_button_state)

        # --- Add trailer button if available ---
        trailer_url = series.get('trailer_url')
        # Try to get trailer_url from detailed info if not present
        series_id = series.get('series_id')
        try:
            success, series_info = self.api_client.get_series_info(series_id)
            if success and series_info:
                info = series_info.get('info', {})
                if not trailer_url:
                    trailer_url = info.get('trailer_url')
                # ...existing code for updating meta, desc, poster...
                meta.setText(f"Year: {info.get('releaseDate', '--')} | Genre: {info.get('genre', '--')}")
                desc.setPlainText(info.get('plot', ''))
                if 'cover' in info:
                    image_data = self.api_client.get_image_data(info['cover'])
                    if image_data:
                        pix = QPixmap()
                        pix.loadFromData(image_data)
                        if not pix.isNull():
                            poster.setPixmap(pix.scaled(180, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception as e:
            print("Error fetching detailed metadata:", e)

        # Add trailer button if trailer_url is available
        if trailer_url:
            trailer_btn = QPushButton("WATCH TRAILER")
            trailer_btn.clicked.connect(lambda: self._play_trailer(trailer_url))
            right_layout.addWidget(trailer_btn)

        layout.addLayout(right_layout)
        # Load seasons for this series
        self.load_seasons(series['series_id'])
        self.current_detailed_series = series # Store for reference if needed
        return details

    def _update_favorite_series_button_text(self, series_data):
        main_window = self.window()
        if not main_window or not hasattr(main_window, 'is_favorite') or not hasattr(self, 'favorite_series_btn'):
            if hasattr(self, 'favorite_series_btn'): self.favorite_series_btn.setText("Favorite N/A")
            return

        # Use series_id and stream_type for checking favorite status
        favorite_item_check = {
            'series_id': series_data.get('series_id'),
            'stream_type': 'series'
        }

        if main_window.is_favorite(favorite_item_check):
            self.favorite_series_btn.setText("★")
            self.favorite_series_btn.setStyleSheet("QPushButton { color: gold; background: transparent; font-size: 16px; }")
            self.favorite_series_btn.setToolTip("Remove from favorites")
        else:
            self.favorite_series_btn.setText("☆")
            self.favorite_series_btn.setStyleSheet("QPushButton { color: white; background: transparent; font-size: 16px; }")
            self.favorite_series_btn.setToolTip("Add to favorites")

    def _toggle_favorite_series(self, series_data):
        main_window = self.window()
        if not main_window or not hasattr(main_window, 'add_to_favorites') or not hasattr(main_window, 'remove_from_favorites'):
            QMessageBox.warning(self, "Error", "Favorite functionality not available in main window.")
            return

        series_id = series_data.get('series_id')
        series_name = series_data.get('name')
        series_cover = series_data.get('cover') # Get cover from the series_data passed

        if not series_id or not series_name:
            QMessageBox.warning(self, "Error", "Series data is incomplete for favorites.")
            return

        favorite_item = {
            'name': series_name,
            'series_id': series_id,
            'cover': series_cover, # Ensure cover is included
            'stream_type': 'series',
            'stream_url': '',  # As per example
            'stream_id': ''    # As per example, or use series_id if preferred for consistency
        }
        
        # Check item for is_favorite should only contain identifying keys
        favorite_item_check = {'series_id': series_id, 'stream_type': 'series'}

        if main_window.is_favorite(favorite_item_check):
            main_window.remove_from_favorites(favorite_item) # Pass full item for potential name display in status
        else:
            main_window.add_to_favorites(favorite_item)
        
        self._update_favorite_series_button_text(series_data) # Update button after action

    def _play_trailer(self, trailer_url):
        main_window = self.window()
        if hasattr(main_window, 'player_window'):
            player_window = main_window.player_window
            player_window.play(trailer_url, {'name': 'Trailer', 'stream_type': 'trailer'})
            player_window.show()
        else:
            QMessageBox.warning(self, "Error", "Player window not available.")

    def update_play_button_state(self):
        # Enable play button if an episode is selected and set the user role data
        item = self.episodes_list.currentItem()
        self.play_episode_btn.setEnabled(item is not None)
        if item and hasattr(self, 'current_episodes'):
            # Find the episode dict and set as user data
            ep_num = item.text().split(' ')[0].lstrip('E')
            for ep in self.current_episodes:
                if str(ep.get('episode_num')) == ep_num:
                    item.setData(Qt.UserRole, ep)
                    break

    def play_selected_episode(self):
        item = self.episodes_list.currentItem()
        if item:
            self._play_episode(item)

    def episode_double_clicked(self, item):
        # Ensure user role data is set
        self.update_play_button_state()
        self._play_episode(item)

    def _play_episode(self, item):
        ep = item.data(Qt.UserRole)
        if not ep:
            QMessageBox.warning(self, "Error", "Episode data not found.")
            return
        main_window = self.window()
        if hasattr(main_window, 'player_window'):
            stream_id = ep.get('id') or ep.get('stream_id')
            container_extension = ep.get('container_extension', 'mp4')
            try:
                # Try to get container extension from episode info (if available)
                success, info = self.api_client.get_episode_info(stream_id)
                if success and 'container_extension' in info:
                    container_extension = info['container_extension']
            except Exception:
                pass
            # Use the correct method for series/episodes
            stream_url = self.api_client.get_series_url(stream_id, container_extension)
            if stream_url:
                self.current_episode = ep  # Track the current episode for favorites
                self.current_series = getattr(self, 'current_series', None) or getattr(self, 'series', None)
                self.episode_num = getattr(self, 'episode_num', None) or getattr(self, 'episode', None)
                self.season = getattr(self, 'season_num', None) or getattr(self, 'season', None)
                episode_item = {
                    'name': f"{self.current_series['name']}-{self.current_episode['title']}",
                    'stream_id': stream_id,
                    'stream_url': stream_url,
                    'container_extension': container_extension,
                    'stream_type': 'episode'
                }
                main_window.player_window.play(stream_url, episode_item)
                # Provide the current episode to the player window for favorites context
                if hasattr(main_window.player_window, 'set_current_episode'):
                    main_window.player_window.set_current_episode(ep)
            else:
                QMessageBox.warning(self, "Error", "Unable to get episode stream URL.")
        else:
            QMessageBox.warning(self, "Error", "Player window not available.")

    def show_series_grid(self):
        self.stacked_widget.setCurrentIndex(0)

    def load_categories(self):
        self.categories_list.clear()
        self.categories_api_data = [] # To store raw API category data
        success, data = self.api_client.get_series_categories()
        if success:
            self.categories_api_data = data
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
            self.load_favorite_series()
        else:
            self.load_series(category_id)
        # Show sorting panel for all except 'favorites'
        self.order_panel.setVisible(category_id != "favorites")

    def load_series(self, category_id):
        self.series = []
        for i in reversed(range(self.series_grid_layout.count())):
            widget = self.series_grid_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        if category_id is None:
            # ALL category: load all series
            if not self.all_series: # Check if all_series is already populated
                temp_all_series = []
                # Use self.categories_api_data which stores the raw category list from the API
                for cat in self.categories_api_data:
                    if cat.get('category_id'): # Ensure valid category_id
                        # Changed from get_series_streams to get_series
                        success, data = self.api_client.get_series(cat['category_id'])
                        if success:
                            temp_all_series.extend(data)
                self.all_series = temp_all_series # Store all series
            all_series = list(self.all_series) # Use a copy for current display
            self.series = all_series
            if not self.all_series: # Populate self.all_series if it's empty and ALL was clicked
                self.all_series = list(self.series)
        else:
            success, data = self.api_client.get_series(category_id) # Changed from get_series_streams
            if success:
                self.series = data
            else:
                QMessageBox.warning(self, "Error", f"Failed to load series: {data}")
        self.current_page = 1
        self._series_sort_cache.clear()  # Clear cache on reload
        self.build_series_search_index()  # Build index after loading
        self.display_current_page()

    def load_favorite_series(self):
        main_window = self.window()
        if not main_window or not hasattr(main_window, 'favorites'):
            self.series = []
            self.current_page = 1
            self.total_pages = 1
            self.display_series_grid(self.series) # Pass the series list to display # Display empty page
            self.update_pagination_controls()
            QMessageBox.information(self, "Favorites", "Could not load favorites from main window.")
            return

        # Filter favorite items that are series and have a series_id
        # These items should already have 'name', 'cover', 'series_id', 'stream_type'
        self.series = [
            fav for fav in main_window.favorites
            if fav.get('stream_type') == 'series' and fav.get('series_id')
        ]

        self.current_page = 1
        self.total_pages = (len(self.series) + self.page_size - 1) // self.page_size
        if self.total_pages == 0:
            self.total_pages = 1 # Ensure at least one page if series list is empty
        
        self._series_sort_cache.clear()  # Clear cache on reload
        self.build_series_search_index()
        self.display_series_grid(self.series) # Pass the series list to display
        self.update_pagination_controls()
        if not self.series:
            # Optionally, show a message in the grid area if no favorites
            # For now, an empty grid will be shown by display_series_page
            pass

    def display_series_grid(self, series_list):
        self.order_panel.setVisible(True if series_list else False)
        # Clear previous grid
        for i in reversed(range(self.series_grid_layout.count())):
            widget = self.series_grid_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        if not series_list:
            empty_label = QLabel("This category doesn't contain any Series")
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setStyleSheet("color: #aaa; font-size: 18px; padding: 40px;")
            self.series_grid_layout.addWidget(empty_label, 0, 0, 1, 4)
            return
        cols = 4
        row = 0
        col = 0
        main_window = self.main_window if hasattr(self, 'main_window') else None
        loading_counter = getattr(main_window, 'loading_counter', None) if main_window else None
        for series in series_list:
            tile = QFrame()
            tile.setFrameShape(QFrame.StyledPanel)
            tile.setStyleSheet("background: #222; border-radius: 12px;")
            tile_layout = QVBoxLayout(tile)
            tile_layout.setContentsMargins(0, 0, 0, 0)
            tile_layout.setSpacing(0)
            # Series poster with overlay using absolute positioning
            poster_container = QWidget()
            poster_container.setFixedSize(100, 140)
            poster = QLabel(poster_container)
            poster.setAlignment(Qt.AlignCenter)
            poster.setGeometry(0, 0, 100, 140)
            default_pix = QPixmap('assets/series.png')
            if series.get('cover'):
                load_image_async(series['cover'], poster, default_pix, update_size=(100, 140), main_window=main_window, loading_counter=loading_counter)
            else:
                poster.setPixmap(default_pix.scaled(100, 140, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            # Overlay 'new.png' if the series is new
            is_recent = False
            if series.get('added'):
                from datetime import datetime, timedelta
                try:
                    added_time = datetime.fromtimestamp(int(series['added']))
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
            # Series name
            name = QLabel(series['name'])
            name.setAlignment(Qt.AlignCenter)
            name.setWordWrap(True)
            name.setFont(QFont('Arial', 11, QFont.Bold))
            name.setStyleSheet("color: #fff;")
            tile_layout.addWidget(name)
            # Rating (if available)
            if series.get('rating'):
                rating = QLabel(f"★ {series['rating']}")
                rating.setAlignment(Qt.AlignCenter)
                rating.setStyleSheet("color: gold;")
                tile_layout.addWidget(rating)
            tile.mousePressEvent = lambda e, s=series: self.series_tile_clicked(s)
            self.series_grid_layout.addWidget(tile, row, col)
            col += 1
            if col >= cols:
                col = 0
                row += 1

    def series_tile_clicked(self, series):
        self.current_series = series
        self.show_series_details(series)

    def build_series_search_index(self):
        """Builds a token-based search index for fast lookup."""
        self._series_search_index = {}
        self._series_lc_names = []
        # Precompute sort keys for each series
        for s in self.series:
            s['_sort_name'] = s.get('name', '').lower()
            try:
                s['_sort_date'] = int(s.get('added', 0))
            except Exception:
                s['_sort_date'] = 0
            try:
                s['_sort_rating'] = float(s.get('rating', 0))
            except Exception:
                s['_sort_rating'] = 0.0
        for idx, s in enumerate(self.series):
            name_lc = s.get('name', '').lower()
            self._series_lc_names.append(name_lc)
            tokens = set(name_lc.split())
            for token in tokens:
                if token not in self._series_search_index:
                    self._series_search_index[token] = set()
                self._series_search_index[token].add(idx)

    def search_series(self, text):
        # Only search if 3+ chars, otherwise always show full list for the current category
        if not self.series:
            return
        text = text.strip().lower()
        if len(text) < 3:
            # Always show the full list for the current category
            self.display_current_page()
            return
        # Token search
        if ' ' not in text and text in self._series_search_index:
            indices = self._series_search_index[text]
            filtered = [self.series[i] for i in indices]
        else:
            # Fallback: substring search
            filtered = [s for s, name in zip(self.series, self._series_lc_names) if text in name]
        self.display_series_grid(filtered)

    def load_seasons(self, series_id):
        """Load seasons for the selected series"""
        self.seasons_list.clear()
        self.episodes_list.clear()
        
        success, data = self.api_client.get_series_info(series_id)
        if success:
            self.series_info = data
            if 'episodes' in data:
                for season_number in sorted(data['episodes'].keys(), key=int):
                    self.seasons_list.addItem(f"Season {season_number}")
        else:
            QMessageBox.warning(self, "Error", f"Failed to load seasons: {data}")
    
    def season_clicked(self, item):
        """Handle season selection"""
        season_text = item.text()
        season_number = season_text.replace("Season ", "")
        
        if hasattr(self, 'series_info') and 'episodes' in self.series_info and season_number in self.series_info['episodes']:
            episodes = self.series_info['episodes'][season_number]
            
            self.episodes_list.clear()
            self.current_episodes = episodes
            self.current_season = season_number
            
            for episode in sorted(episodes, key=lambda x: int(x['episode_num'])):
                self.episodes_list.addItem(f"E{episode['episode_num']} - {episode['title']}")
    
    def episode_double_clicked(self, item):
        """Handle episode double-click"""
        self._play_episode(item)
    
    def download_episode(self):
        """Download the selected episode"""
        if not self.episodes_list.currentItem():
            QMessageBox.warning(self, "Error", "No episode selected")
            return
        
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
        
        # Get container extension (default to mp4)
        container_extension = episode.get('container_extension', 'mp4')
        
        # Create filename
        filename = f"{self.current_series['name']} - S{season_number}E{episode_number} - {episode_title}.{container_extension}"
        
        stream_url = self.api_client.get_series_url(episode_id, container_extension)
        
        # Ask for save location
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Episode", filename, f"Video Files (*.{container_extension})"
        )
        
        if not save_path:
            return
        
        
        # Create download item
        download_item = DownloadItem(filename, save_path)
        
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
    
    def download_season(self):
        """Download the complete season"""
        if not self.seasons_list.currentItem():
            QMessageBox.warning(self, "Error", "No season selected")
            return
        
        season_text = self.seasons_list.currentItem().text()
        season_number = season_text.replace("Season ", "")
        
        if not hasattr(self, 'series_info') or 'episodes' not in self.series_info or season_number not in self.series_info['episodes']:
            QMessageBox.warning(self, "Error", "Failed to get season information")
            return
        
        episodes = self.series_info['episodes'][season_number]
        
        # Ask for save directory
        save_dir = QFileDialog.getExistingDirectory(self, "Select Directory to Save Season")
        
        if not save_dir:
            return
        
        # Create season directory
        series_name = self.current_series['name']
        season_dir = os.path.join(save_dir, f"{series_name} - Season {season_number}")
        os.makedirs(season_dir, exist_ok=True)
        
        # Create download item for the whole season
        download_item = DownloadItem(
            f"{series_name} - Season {season_number} (Complete)",
            season_dir
        )
        
        # Start batch download thread
        self.batch_download_thread = BatchDownloadThread(
            self.api_client, episodes, season_dir, series_name
        )
        download_item.download_thread = self.batch_download_thread
        
        # Connect signals
        self.batch_download_thread.progress_update.connect(
            lambda episode_idx, progress: self.update_batch_progress(download_item, episode_idx, progress))
        self.batch_download_thread.download_complete.connect(
            lambda: self.batch_download_finished(download_item))
        self.batch_download_thread.download_error.connect(
            lambda error: self.batch_download_error(download_item, error))
        
        # Add to downloads tab
        if self.main_window and hasattr(self.main_window, 'downloads_tab'):
            self.main_window.downloads_tab.add_download(download_item)
        
        self.batch_download_thread.start()
    
    def export_season(self):
        """Export all episode URLs of the selected season to a text file"""
        if not self.seasons_list.currentItem():
            QMessageBox.warning(self, "Error", "No season selected")
            return

        season_text = self.seasons_list.currentItem().text()
        season_number = season_text.replace("Season ", "")

        if not hasattr(self, 'series_info') or 'episodes' not in self.series_info or season_number not in self.series_info['episodes']:
            QMessageBox.warning(self, "Error", "Failed to get season information")
            return

        episodes = self.series_info['episodes'][season_number]

        # Ask for save location
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Export Season URLs", f"{self.current_series['name']} - Season {season_number}.txt", "Text Files (*.txt)"
        )

        if not save_path:
            return

        try:
            with open(save_path, 'w') as file:
                for episode in episodes:
                    episode_id = episode['id']
                    container_extension = episode.get('container_extension', 'mp4')
                    stream_url = self.api_client.get_series_url(episode_id, container_extension)
                    file.write(f"{stream_url}\n")

            QMessageBox.information(self, "Export Complete", f"Season URLs exported to: {save_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export season URLs: {str(e)}")
        return
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
    
    def update_batch_progress(self, download_item, episode_index, progress):
        """Update batch download progress dialog"""
        if download_item:
            # For batch downloads, we'll use the episode index and progress to calculate overall progress
            if hasattr(self, 'current_episodes'):
                total_episodes = len(self.current_episodes)
                if total_episodes > 0:
                    overall_progress = int((episode_index * 100 + progress) / total_episodes)
                    download_item.update_progress(overall_progress)
                    
                    # Update the UI in the downloads tab
                    if self.main_window and hasattr(self.main_window, 'downloads_tab'):
                        self.main_window.downloads_tab.update_download_item(download_item)
        
    def batch_download_finished(self, download_item):
        """Handle batch download completion"""
        if download_item:
            # Update the download item
            download_item.complete(download_item.save_path)
            
            # Update the UI in the downloads tab
            if self.main_window and hasattr(self.main_window, 'downloads_tab'):
                self.main_window.downloads_tab.update_download_item(download_item)
        
        
        QMessageBox.information(self, "Download Complete", "Season download completed")
    
    def batch_download_error(self, download_item, error_message):
        """Handle batch download error"""
        if download_item:
            # Update the download item
            download_item.fail(error_message)
            
            # Update the UI in the downloads tab
            if self.main_window and hasattr(self.main_window, 'downloads_tab'):
                self.main_window.downloads_tab.update_download_item(download_item)
        
        
        QMessageBox.critical(self, "Download Error", error_message)
    
    def cancel_batch_download(self):
        """Cancel the current batch download"""
        if self.batch_download_thread and self.batch_download_thread.isRunning():
            self.batch_download_thread.cancel()
    
    def add_to_favorites_clicked(self):
        """Add current episode to favorites"""
        episode = dict(self.current_episode)
        if 'name' not in episode:
            # Use title, season, and episode number for name
            title = episode.get('title', episode.get('name', 'Episode'))
            season = episode.get('season') or episode.get('season_number')
            episode_num = episode.get('episode_num')
            # Fallback to series name if available
            series_name = self.current_series['name'] if hasattr(self, 'current_series') and self.current_series else ''
            if series_name:
                episode['name'] = f"{series_name} - {title} S{season}E{episode_num}" if season and episode_num else f"{series_name} - {title}"
            else:
                episode['name'] = f"{title} S{season}E{episode_num}" if season and episode_num else title
        self.add_to_favorites.emit(episode)

    # --- Pagination for series grid ---
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

    def update_pagination_controls(self):
        if self.total_pages > 1:
            self.page_label.setText(f"Page {self.current_page} of {self.total_pages}")
            self.prev_page_button.setEnabled(self.current_page > 1)
            self.next_page_button.setEnabled(self.current_page < self.total_pages)
            self.pagination_panel.setVisible(True)
        else:
            self.pagination_panel.setVisible(False)
        if hasattr(self, 'prev_button') and hasattr(self, 'next_button'):
            self.prev_button.setVisible(self.current_page > 1)
            self.next_button.setVisible(self.current_page < self.total_pages)

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

    def go_to_previous_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.display_current_page()

    def go_to_next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.display_current_page()

    def display_current_page(self):
        for i in reversed(range(self.series_grid_layout.count())):
            widget = self.series_grid_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        page_items, self.total_pages = self.paginate_items(self.series, self.current_page)
        self.display_series_grid(page_items)
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
        items = list(self.series) if hasattr(self, 'series') else []
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
        # Update self.series to the sorted list so pagination always follows the sort
        self.series = sorted_items
        self.current_page = 1  # Reset to first page after sort
        self.display_current_page()
