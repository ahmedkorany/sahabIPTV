"""
Live TV tab for the application
"""
import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
                            QListWidget, QPushButton, QLineEdit, QMessageBox,
                            QFileDialog, QLabel, QListWidgetItem, QFrame, QScrollArea, QGridLayout)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QObject, QMetaObject, Q_ARG, QTimer
from PyQt5.QtGui import QPixmap, QFont
from src.utils.text_search import TextSearch
import sip # Add sip import for checking deleted QObjects
from src.ui.player import MediaPlayer
from src.utils.recorder import RecordingThread
from src.ui.widgets.dialogs import ProgressDialog
from src.utils.image_cache import ImageCache
from src.utils.helpers import get_api_client_from_label
import threading

class DebouncedLineEdit(QLineEdit):
    _debounced_text_changed = pyqtSignal(str)
    def __init__(self, delay=200, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._emit_debounced_text_changed)
        self.textChanged.connect(self._on_text_changed)
        self._debounce_delay = delay
    def _on_text_changed(self, text):
        self._debounce_timer.start(self._debounce_delay)
    def _emit_debounced_text_changed(self):
        self._debounced_text_changed.emit(self.text())

def load_image_async(image_url, label, default_pixmap, update_size=(100, 140), main_window=None, loading_counter=None):
    ImageCache.ensure_cache_dir()
    cache_path = ImageCache.get_cache_path(image_url)
    def set_pixmap(pixmap):
        label.setPixmap(pixmap.scaled(*update_size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    def worker():
        from PyQt5.QtGui import QPixmap
        if main_window and hasattr(main_window, 'loading_icon_controller'):
            main_window.loading_icon_controller.show_icon.emit()
        pix = QPixmap()
        if os.path.exists(cache_path):
            pix.load(cache_path)
        else:
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
                        pix.save(cache_path)
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

class ChannelLoaderWorker(QObject):
    channels_loaded = pyqtSignal(list)
    loading_failed = pyqtSignal(str)

    def __init__(self, api_client, category_id, page, page_size):
        super().__init__()
        self.api_client = api_client
        self.category_id = category_id
        self.page = page
        self.page_size = page_size

    def run(self):
        try:
            success, data = self.api_client.get_live_streams(self.category_id)
            if not success:
                self.loading_failed.emit(str(data))
                return
            # Paginate
            start = (self.page - 1) * self.page_size
            end = start + self.page_size
            self.channels_loaded.emit(data[start:end])
        except Exception as e:
            self.loading_failed.emit(str(e))

class LiveTab(QWidget):
    """Live TV tab widget"""
    add_to_favorites = pyqtSignal(dict)
    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.live_channels = []
        self.all_channels = []  # Store all channels across categories
        self.categories_api_data = [] # Store raw API category data
        self.current_channel = None
        self.recording_thread = None
        self.page_size = 32
        self.current_page = 1
        self.total_pages = 1
        self.setup_ui()
        self.main_window = None  # Will be set by the main window
    
    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Main content area with splitter
        splitter = QSplitter(Qt.Horizontal)

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

        # --- Right: Channel Grid ---
        self.channel_grid_widget = QWidget()
        self.channel_grid_layout = QGridLayout(self.channel_grid_widget)
        self.channel_grid_layout.setSpacing(16)
        self.channel_grid_layout.setContentsMargins(8, 8, 8, 8)
        self.channel_grid_widget.setStyleSheet("background: transparent;")
        self.channel_grid_scroll = QScrollArea()
        self.channel_grid_scroll.setWidgetResizable(True)
        self.channel_grid_scroll.setWidget(self.channel_grid_widget)

        right_panel = QVBoxLayout()
        right_panel.addWidget(QLabel("Channels"))
        right_panel.addWidget(self.channel_grid_scroll)
        self.loading_label = QLabel("Loading...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet("color: #fff; font-size: 18px; background: #222;")
        self.loading_label.hide()
        self.setup_pagination_controls()
        right_panel.addWidget(self.loading_label)
        right_panel.addWidget(self.pagination_panel)  # Always add pagination panel
        right_widget = QWidget()
        right_widget.setLayout(right_panel)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([300, 900])

        # Add all components to main layout
        layout.addWidget(splitter)
        self.display_current_page()
        self.page_size = 32
        self.current_page = 1
        self.loaded_pages = set()
        self.loading = False
        self.all_channels = []

    def load_categories(self):
        """Load live TV categories from the API"""
        if sip.isdeleted(self.categories_list):
            print("[LiveTab] categories_list widget has been deleted, skipping clear().")
            return
        self.categories_list.clear()
        self.categories_api_data = []
        success, data = self.api_client.get_live_categories()
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
        if category_id == "favorites":
            self.load_favorite_channels()
        else:
            self.load_channels(category_id)

    def load_channels(self, category_id):
        """Load channels for the selected category and display as grid (synchronously, like movies tab)"""
        self.live_channels = []
        self.current_category_id = category_id
        self.current_page = 1
        self.loaded_pages = set()
        for i in reversed(range(self.channel_grid_layout.count())):
            widget = self.channel_grid_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        self.show_loading(True)
        if category_id is None:  # ALL category
            if not self.all_channels:
                temp_all_channels = []
                for cat in self.categories_api_data:
                    if cat.get('category_id'): # Ensure valid category_id
                        success, data = self.api_client.get_live_streams(cat['category_id'])
                        if success:
                            temp_all_channels.extend(data)
                self.all_channels = temp_all_channels
            self.live_channels = list(self.all_channels)
        else: # Specific category
            success, data = self.api_client.get_live_streams(category_id)
            if success:
                self.live_channels = data
            else:
                QMessageBox.warning(self, "Error", f"Failed to load channels: {data}")
        self.display_current_page()
        self.show_loading(False)

    def load_favorite_channels(self):
        """Load and display favorite live channels using the SeriesTab approach."""
        if not self.main_window or not hasattr(self.main_window, 'favorites'):
            QMessageBox.warning(self, "Error", "Favorites list not available.")
            self.live_channels = []
            self.current_page = 1
            self.display_current_page()
            return

        # Filter favorite items that are live channels
        self.live_channels = [
            fav for fav in self.main_window.favorites
            if fav.get('stream_type') == 'live'
        ]

        self.current_page = 1  # Reset to first page for favorites
        # display_current_page will handle pagination and display
        # It should also update total_pages based on self.live_channels
        self.display_current_page()

    def search_channels(self, text):
        """Fast search using index, similar to movies/series."""
        from src.utils.text_search import TextSearch
        search_term = text.strip()
        if not self.live_channels:
            self.display_channel_grid([])
            return
        if not search_term:
            self.display_channel_grid(self.live_channels)
            return
        query_tokens = TextSearch.normalize_text(search_term).split()
        matched_indices = set()
        processed_first_token = False
        for token in query_tokens:
            if token in self._live_search_index:
                if not processed_first_token:
                    matched_indices = self._live_search_index[token].copy()
                    processed_first_token = True
                else:
                    matched_indices.intersection_update(self._live_search_index[token])
            else:
                matched_indices.clear()
                break
        # Fallback: substring search
        if not matched_indices:
            for idx, name in enumerate(self._live_lc_names):
                if search_term.lower() in name:
                    matched_indices.add(idx)
        filtered = [self.live_channels[i] for i in sorted(matched_indices)]
        self.display_channel_grid(filtered)
    
    def channel_double_clicked(self, item):
        """Handle channel double-click"""
        # Find the channel object from the item
        channel_name = item.text()
        channel = next((ch for ch in self.live_channels if ch['name'] == channel_name), None)
        if channel:
            self.play_channel(channel)
    
    def play_channel(self, channel=None):
        """Play the selected channel"""
        if channel is not None:
            self.current_channel = {
                'name': channel['name'],
                'stream_url': self.api_client.get_live_stream_url(channel['stream_id']),
                'stream_id': channel['stream_id'],
                'stream_type': 'live'
            }
        if not self.current_channel:
            QMessageBox.warning(self, "Error", "No channel selected")
            return
        stream_url = self.current_channel.get('stream_url')
        main_window = self.main_window if hasattr(self, 'main_window') else None
        try:
            if main_window and hasattr(main_window, 'player_window'):
                player_window = main_window.player_window
                player_window.play(stream_url, self.current_channel)
                player_window.show()
                player_window.raise_()
                player_window.activateWindow()
            else:
                if not hasattr(self, 'player'):
                    self.player = MediaPlayer()
                self.player.play(stream_url)
        except Exception as e:
            QMessageBox.critical(self, "Playback Error", f"Could not open the stream. The channel may be temporarily unavailable.\n\nError: {str(e)}")
        # Optionally update current_channel again if needed
    
    def record_channel(self):
        """Record the current channel"""
        if not self.current_channel:
            QMessageBox.warning(self, "Error", "No channel is playing")
            return
        
        # Ask for save location
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Recording", f"{self.current_channel['name']}.mp4", "MP4 Files (*.mp4)"
        )
        
        if not save_path:
            return
        
        # Start recording thread
        self.recording_thread = RecordingThread(
            self.current_channel['stream_url'], 
            save_path, 
            self.api_client.headers
        )
        self.recording_thread.recording_started.connect(self.recording_started)
        self.recording_thread.recording_error.connect(self.recording_error)
        self.recording_thread.recording_stopped.connect(self.recording_stopped)
        
        self.recording_thread.start()
        
        # Update UI
        self.record_button.setEnabled(False)
        self.stop_record_button.setEnabled(True)
    
    def stop_recording(self):
        """Stop the current recording"""
        if self.recording_thread and self.recording_thread.isRunning():
            self.recording_thread.stop_recording()
    
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
    
    def add_to_favorites_clicked(self):
        """Add current channel to favorites"""
        if not self.current_channel:
            QMessageBox.warning(self, "Error", "No channel is playing")
            return
        channel = dict(self.current_channel)
        if 'name' not in channel:
            channel['name'] = channel.get('title', channel.get('name', 'Channel'))
        self.add_to_favorites.emit(channel)

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

    def go_to_previous_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.display_current_page()

    def go_to_next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.display_current_page()

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

    def display_current_page(self):
        # Clear previous grid items
        for i in reversed(range(self.channel_grid_layout.count())):
            widget = self.channel_grid_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        page_items, self.total_pages = self.paginate_items(self.live_channels, self.current_page)
        # Show empty state label if no items
        if not page_items:
            if not hasattr(self, 'empty_state_label'):
                self.empty_state_label = QLabel()
                self.empty_state_label.setAlignment(Qt.AlignCenter)
                self.empty_state_label.setStyleSheet("color: #888; font-size: 18px; padding: 40px;")
                self.empty_state_label.setWordWrap(True)
            query = self.search_input.text().strip() if hasattr(self, 'search_input') else ''
            if query:
                self.empty_state_label.setText(f"No results found for '{query}'.")
            else:
                self.empty_state_label.setText("No channels to display.")
            self.channel_grid_layout.addWidget(self.empty_state_label, 0, 0, 1, 4)
            self.pagination_panel.setVisible(False)
            return
        else:
            if hasattr(self, 'empty_state_label'):
                self.empty_state_label.hide()
        self.display_channel_grid(page_items)
        self.update_pagination_controls()

    def display_channel_grid(self, channels):
        """Display channels as a grid of tiles"""
        # Clear previous grid
        for i in reversed(range(self.channel_grid_layout.count())):
            widget = self.channel_grid_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        self.channel_tiles = []
        # Remove the empty state label if present
        if hasattr(self, 'empty_state_label'):
            self.empty_state_label.hide()
        if not channels:
            # This logic is now handled in display_current_page
            return
        cols = 4
        row = 0
        col = 0
        main_window = self.main_window if hasattr(self, 'main_window') else None
        loading_counter = getattr(main_window, 'loading_counter', None) if main_window else None
        for channel in channels:
            tile = QFrame()
            tile.setFrameShape(QFrame.StyledPanel)
            tile.setStyleSheet("background: #222; border-radius: 12px;")
            tile_layout = QVBoxLayout(tile)
            # Channel logo
            logo = QLabel()
            logo.setAlignment(Qt.AlignCenter)
            default_pix = QPixmap('assets/live.png')
            if channel.get('stream_icon'):
                load_image_async(channel['stream_icon'], logo, default_pix, update_size=(80, 80), main_window=main_window, loading_counter=loading_counter)
            else:
                logo.setPixmap(default_pix.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            tile_layout.addWidget(logo)
            # Channel name
            name = QLabel(channel['name'])
            name.setAlignment(Qt.AlignCenter)
            name.setWordWrap(True)
            name.setFont(QFont('Arial', 11, QFont.Bold))
            name.setStyleSheet("color: #fff;")
            tile_layout.addWidget(name)
            tile.mousePressEvent = lambda e, ch=channel, t=tile: self.channel_tile_clicked(ch, t)
            self.channel_grid_layout.addWidget(tile, row, col)
            self.channel_tiles.append(tile)
            col += 1
            if col >= cols:
                col = 0
                row += 1
        self.pagination_panel.setVisible(True)

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

    def show_loading(self, show):
        if hasattr(self, 'loading_label'):
            self.loading_label.setVisible(show)

    def channel_tile_clicked(self, channel, tile=None):
        self.current_channel = {
            'name': channel['name'],
            'stream_url': self.api_client.get_live_stream_url(channel['stream_id']),
            'stream_id': channel['stream_id'],
            'stream_type': 'live'
        }
        # Highlight selected tile
        for t in getattr(self, 'channel_tiles', []):
            t.setStyleSheet("background: #222; border-radius: 12px;")
        if tile:
            tile.setStyleSheet("background: #0057d8; border-radius: 12px; border: 2px solid #fff;")
        self.play_channel(channel)
