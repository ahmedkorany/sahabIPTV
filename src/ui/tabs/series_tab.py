"""
Series tab for the application
"""
import time
from PyQt5.QtGui import QFontMetrics
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
                            QListWidget, QPushButton, QLineEdit, QMessageBox,
                            QFileDialog, QLabel, QListWidgetItem, QFrame, QScrollArea, QGridLayout, QStackedWidget, QComboBox)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QFont, QFontMetrics
from PyQt5.QtCore import QRect
from src.utils.helpers import load_image_async
from src.ui.widgets.series_details_widget import SeriesDetailsWidget
from src.api.tmdb import TMDBClient

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

from src.utils.helpers import load_image_async, get_translations

class SeriesTab(QWidget):
    add_to_favorites = pyqtSignal(dict)
    # add_to_downloads = pyqtSignal(object) # Removed

    def __init__(self, api_client, favorites_manager=None, main_window=None, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.favorites_manager = favorites_manager
        self.series = []
        self.filtered_series = []
        self.all_series = []  # Store all series across categories
        self.current_series = None
        self._opened_from_search = False
        # Get translations from main window
        self.translations = getattr(main_window, 'translations', {}) if main_window else {}
        self.setup_ui()
        self.api_client = api_client
        self.main_window = main_window
        self.tmdb_client = TMDBClient() # Initialize TMDBClient
        self._series_sort_cache = {}  # (sort_field, reverse) -> sorted list

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.translations.get("Search series...", "Search series..."))
        self.search_input.textChanged.connect(self.on_search_text_changed)
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
        left_panel.addWidget(QLabel(self.translations.get("Categories", "Categories")))
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
        grid_panel.addWidget(QLabel(self.translations.get("Series", "Series")))
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
        self.grid_view_widget = splitter_widget  # Store reference to grid view widget
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
        order_label = QLabel(self.translations.get("Order by", "Order by:"))
        self.order_combo = QComboBox()
        self.order_combo.addItems([self.translations.get("Default", "Default"), self.translations.get("Date", "Date"), self.translations.get("Rating", "Rating"), self.translations.get("Name", "Name")])
        self.order_combo.setCurrentIndex(0)
        self.order_combo.currentIndexChanged.connect(self.on_order_changed)
        self.sort_toggle = QPushButton(self.translations.get("Desc", "Desc"))
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

    def on_search_text_changed(self, text):
        """Handle search input text changes"""
        self.search_series(text)

    def _show_grid_view(self):
        # Assuming grid view is at index 0 of the stacked_widget
        self.stacked_widget.setCurrentIndex(0)
        # Clean up details widget if it exists to free resources
        if self.details_widget:
            self.stacked_widget.removeWidget(self.details_widget)
            self.details_widget.deleteLater()
            self.details_widget = None

    def _handle_back_from_details(self):
        if self._opened_from_search:
            if self.main_window and hasattr(self.main_window, 'search_tab') and self.main_window.search_tab:
                self.main_window.tabs.setCurrentWidget(self.main_window.search_tab)
            self._opened_from_search = False # Reset flag
            # Ensure the series tab is reset to grid view for future navigation to it
            self._show_grid_view()
        else:
            self._show_grid_view()
            # Check if favorites category is selected and refresh if needed
            current_category_item = self.categories_list.currentItem()
            if current_category_item:
                category_id = current_category_item.data(Qt.UserRole)
                if category_id == "favorites":
                    # Refresh favorites grid in case favorite state changed
                    self.load_favorite_series()
                else:
                    self.display_current_page()
            else:
                self.display_current_page()

    def show_series_details(self, series_data):
        if self.details_widget:
            self.stacked_widget.removeWidget(self.details_widget)
            self.details_widget.deleteLater()
            self.details_widget = None

        self.current_series = series_data # Keep track of the series being detailed
        self.details_widget = SeriesDetailsWidget(
            series_data=series_data,
            api_client=self.api_client,
            main_window=self.window(), # Or self.main_window if set
            parent=self # Parent for the widget itself
        )

        # Connect signals from SeriesDetailsWidget to handlers in SeriesTab
        self.details_widget.back_clicked.connect(self._handle_back_from_details)
        self.details_widget.play_episode_requested.connect(self._handle_play_episode_request)
        self.details_widget.toggle_favorite_series_requested.connect(self._handle_toggle_favorite_request)
        # self.details_widget.download_episode_requested.connect(self._handle_download_episode_request) # Removed
        # self.details_widget.download_season_requested.connect(self._handle_download_season_request) # Removed
        self.details_widget.export_season_requested.connect(self._handle_export_season_request)
        
        # Connect to main window's favorites_changed signal to refresh button state
        if hasattr(self.main_window, 'favorites_changed'):
            self.main_window.favorites_changed.connect(self._on_favorites_changed)

        # Add the new details widget to the stacked_widget (if not already added as a placeholder)
        # It's common to add it once and then show/hide, or remove/add like here.
        # If a placeholder was used at index 1:
        if self.stacked_widget.widget(1) is not None and self.stacked_widget.widget(1) != self.details_widget:
             # Remove placeholder if it's a generic QWidget before adding the real one
            old_placeholder = self.stacked_widget.widget(1)
            if old_placeholder:
                self.stacked_widget.removeWidget(old_placeholder)
                old_placeholder.deleteLater()
        
        # Ensure details_widget is added if no placeholder or placeholder was removed
        if self.stacked_widget.indexOf(self.details_widget) == -1:
            self.stacked_widget.addWidget(self.details_widget) # Adds to the end, usually index 1 if grid is 0

        self.stacked_widget.setCurrentWidget(self.details_widget)

    def show_series_details_by_data(self, series_data):
        """Shows series details based on provided series_data, typically from an external source like search."""
        self._opened_from_search = True
        # This method is similar to show_series_details but callable with data directly.
        if not series_data or not isinstance(series_data, dict):
            QMessageBox.warning(self, "Error", "Invalid series data provided.")
            return

        # Clear existing details widget if any
        if self.details_widget:
            self.stacked_widget.removeWidget(self.details_widget)
            self.details_widget.deleteLater()
            self.details_widget = None

        self.current_series = series_data  # Set current series context
        self.details_widget = SeriesDetailsWidget(
            series_data=series_data,
            api_client=self.api_client,
            main_window=self.main_window, # Ensure main_window is passed
            parent=self
        )

        # Connect signals from SeriesDetailsWidget
        self.details_widget.back_clicked.connect(self._handle_back_from_details)
        self.details_widget.play_episode_requested.connect(self._handle_play_episode_request)
        self.details_widget.toggle_favorite_series_requested.connect(self._handle_toggle_favorite_request)
        self.details_widget.export_season_requested.connect(self._handle_export_season_request)
        
        # Connect to main window's favorites_changed signal to refresh button state
        if hasattr(self.main_window, 'favorites_changed'):
            self.main_window.favorites_changed.connect(self._on_favorites_changed)

        # Add and show the details widget
        if self.stacked_widget.indexOf(self.details_widget) == -1:
            # If a placeholder was at index 1, remove it first
            old_widget_at_1 = self.stacked_widget.widget(1)
            if old_widget_at_1 and old_widget_at_1 != self.grid_view_widget: # Check it's not the grid view itself
                self.stacked_widget.removeWidget(old_widget_at_1)
                old_widget_at_1.deleteLater()
            self.stacked_widget.addWidget(self.details_widget) # Add to index 1 (or next available)
        
        self.stacked_widget.setCurrentWidget(self.details_widget)

    # --- New/Adapted Signal Handlers ---
    def _handle_play_episode_request(self, episode_data):
        # This will replace the logic of the old _play_episode method
        # For now, just a placeholder
        print(f"SeriesTab: Play episode requested: {episode_data.get('title')}")
        # Actual play logic will be added in a subsequent step
        main_window = self.window()
        if hasattr(main_window, 'player_window') and episode_data:
            stream_id = episode_data.get('id') or episode_data.get('stream_id')
            container_extension = episode_data.get('container_extension', 'mp4')
            
            # Ensure current_series is set if needed by get_series_url or for context
            if not hasattr(self, 'current_series') or not self.current_series:
                # This might happen if show_series_details wasn't called or series context is lost
                # Try to get series_id from episode_data if possible, though it's not standard
                # QMessageBox.warning(self, "Error", "Series context not found for playing episode.")
                # return
                # Fallback: if series_id is in episode_data (not typical but as a safeguard)
                series_id_for_url = episode_data.get('series_id') 
            else:
                series_id_for_url = self.current_series.get('series_id')

            # The get_series_url might need series_id if it's not part of episode's stream_id logic
            # Assuming get_series_url can derive necessary info from stream_id and container_extension
            stream_url = self.api_client.get_series_url(stream_id, container_extension)

            if stream_url:
                episode_name = episode_data.get('title', 'Episode')
                series_name = self.current_series.get('name', 'Series') if hasattr(self, 'current_series') and self.current_series else ''
                
                player_item_info = {
                    'name': f"{series_name} - {episode_name}",
                    'stream_id': stream_id,
                    'stream_url': stream_url,
                    'container_extension': container_extension,
                    'stream_type': 'episode', # or 'series' depending on player's expectation
                    'series_id': series_id_for_url, # For context, like adding to history/watched status
                    'episode_num': episode_data.get('episode_num'),
                    'season_num': episode_data.get('season_num')
                }
                main_window.player_window.play(stream_url, player_item_info)
                main_window.player_window.show()
            else:
                QMessageBox.warning(self, "Error", "Could not retrieve stream URL for the episode.")
        else:
            QMessageBox.warning(self, "Error", "Player window or episode data not available.")

    def _handle_toggle_favorite_request(self, series_data):
        # This will replace the logic of the old _toggle_favorite_series method
        print(f"SeriesTab: Toggle favorite requested for: {series_data.get('name')}")
        if not self.favorites_manager:
            QMessageBox.warning(self, "Error", "Favorite functionality not available.")
            return

        series_id = series_data.get('series_id')
        series_name = series_data.get('name')
        # Ensure 'cover' is present in series_data if needed by favorites manager
        series_cover = series_data.get('cover') 

        if not series_id or not series_name:
            QMessageBox.warning(self, "Error", "Series data is incomplete for favorites.")
            return

        favorite_item = {
            'name': series_name,
            'series_id': series_id,
            'cover': series_cover, 
            'stream_type': 'series',
            # Add other fields as expected by favorites manager
        }
        
        # Add any additional fields from series_data
        for key, value in series_data.items():
            if key not in favorite_item:
                favorite_item[key] = value

        # Use favorites manager to toggle favorite status
        self.favorites_manager.toggle_favorite(favorite_item)
        
        # Refresh the button in SeriesDetailsWidget
        if self.details_widget and self.stacked_widget.currentWidget() == self.details_widget:
            self.details_widget.refresh_favorite_button()
    
    def _on_favorites_changed(self):
        """Handle favorites changed signal from main window"""
        if hasattr(self.details_widget, 'refresh_favorite_button'):
            self.details_widget.refresh_favorite_button()
        
        # Refresh favorites grid if favorites category is currently selected
        current_category_item = self.categories_list.currentItem()
        if current_category_item:
            category_id = current_category_item.data(Qt.UserRole)
            if category_id == "favorites":
                self.load_favorite_series()

    def _handle_download_episode_request(self, episode_data):
        if not episode_data or not self.current_series:
            QMessageBox.warning(self, "Error", "Episode or series data not found for download.")
            return

        series_name = self.current_series.get('name', 'Series')
        episode_title = episode_data.get('title', 'Episode')
        episode_num = episode_data.get('episode_num', 'UnknownEpisode')
        season_num = episode_data.get('season_num', self.details_widget.get_current_season() if self.details_widget else 'UnknownSeason')

        default_filename = f"{series_name} - S{str(season_num).zfill(2)}E{str(episode_num).zfill(2)} - {episode_title}.{episode_data.get('container_extension', 'mp4')}"
        # Sanitize filename (basic example, consider a more robust function)
        default_filename = default_filename.replace('/', '-').replace('\\', '-').replace(':', '-').replace('*', '-').replace('?', '-').replace('"', '-').replace('<', '-').replace('>', '-').replace('|', '-')

        save_path, _ = QFileDialog.getSaveFileName(self, "Save Episode", default_filename, "Video Files (*.mp4 *.mkv *.avi *.ts);;All Files (*)")
        if not save_path:
            return

        stream_id = episode_data.get('id') or episode_data.get('stream_id')
        container_extension = episode_data.get('container_extension', 'mp4')
        download_url = self.api_client.get_series_url(stream_id, container_extension)

        if not download_url:
            QMessageBox.warning(self, "Error", "Could not retrieve download URL for the episode.")
            return

        download_item = DownloadItem(name=default_filename, save_path=save_path)
        # The DownloadThread will be created and managed by the DownloadsTab or a central download manager
        # For now, we just prepare the DownloadItem
        # download_item.download_thread = DownloadThread(download_url, save_path, download_item) # Example if thread created here
        
        # self.add_to_downloads.emit(download_item) # DownloadsTab will handle this # Removed
        QMessageBox.information(self, "Download Started", f"{default_filename} has been added to downloads.")

    def _handle_download_season_request(self, season_number):
        # This method is no longer needed as download functionality is removed.
        # QMessageBox.information(self, "Info", "Download functionality is currently disabled.")
        pass


    def _handle_export_season_request(self, season_number):
        if not self.current_series or not self.details_widget:
            QMessageBox.warning(self, "Error", "Series data not available for season export.")
            return

        series_info = self.details_widget.get_series_info()
        if not series_info or 'episodes' not in series_info or season_number not in series_info['episodes']:
            QMessageBox.warning(self, "Error", f"No episodes found for Season {season_number} to export.")
            return

        episodes_to_export = series_info['episodes'][season_number]
        if not episodes_to_export:
            QMessageBox.warning(self, "Error", f"No episodes found for Season {season_number} to export.")
            return

        series_name = self.current_series.get('name', 'Series')
        sane_series_name = series_name.replace('/', '-').replace('\\', '-').replace(':', '-').replace('*', '-').replace('?', '-').replace('"', '-').replace('<', '-').replace('>', '-').replace('|', '-')
        default_m3u_filename = f"{sane_series_name} - Season {str(season_number).zfill(2)}.m3u"

        save_path, _ = QFileDialog.getSaveFileName(self, "Export Season URLs", default_m3u_filename, "M3U Playlist (*.m3u);;All Files (*)")
        if not save_path:
            return

        m3u_content = ["#EXTM3U"]
        for episode_data in episodes_to_export:
            episode_title = episode_data.get('title', 'Episode')
            episode_id = episode_data.get('id') or episode_data.get('stream_id')
            container_extension = episode_data.get('container_extension', 'mp4')
            stream_url = self.api_client.get_series_url(episode_id, container_extension)

            if stream_url:
                # Basic M3U format, can be extended with #EXTINF if more metadata is needed
                m3u_content.append(f"#EXTINF:-1 tvg-id=\"{episode_id}\" tvg-name=\"{episode_title}\" group-title=\"Season {season_number}\",{episode_title}")
                m3u_content.append(stream_url)
            else:
                print(f"Could not get stream URL for {episode_title}")

        if len(m3u_content) > 1: # Has at least one episode
            try:
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write("\n".join(m3u_content))
                QMessageBox.information(self, "Export Successful", f"Season {season_number} URLs exported to {save_path}")
            except IOError as e:
                QMessageBox.warning(self, "Export Error", f"Could not write to file: {save_path}\n{e}")
        else:
            QMessageBox.warning(self, "Export Failed", f"No stream URLs could be retrieved for Season {season_number}.")


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
        self.sort_toggle.setText(self.translations.get("Desc", "Desc"))
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
        self.display_current_page() # Refresh display after loading series

    def load_favorite_series(self):
        if not self.favorites_manager:
            self.series = []
            self.current_page = 1
            self.total_pages = 1
            self.display_series_grid(self.series) # Pass the series list to display # Display empty page
            self.update_pagination_controls()
            QMessageBox.information(self, "Favorites", "Could not load favorites from favorites manager.")
            return

        # Get favorites from the favorites manager and filter for series
        all_favorites = self.favorites_manager.get_favorites()
        self.series = [
            fav for fav in all_favorites
            if fav.get('stream_type') == 'series' and fav.get('series_id')
        ]

        self.current_page = 1
        self.total_pages = (len(self.series) + self.page_size - 1) // self.page_size
        if self.total_pages == 0:
            self.total_pages = 1 # Ensure at least one page if series list is empty
        
        self._series_sort_cache.clear()  # Clear cache on reload
        self.build_series_search_index() # Populates _normalized_name
        self.search_series(self.search_input.text()) # Apply current search or show all

    def build_series_search_index(self):
        """Build search index for series with normalized names and sorting keys."""
        self._series_search_index = {}
        self._series_lc_names = []
        if not hasattr(self, 'series') or not self.series:
            return
        for idx, series_data in enumerate(self.series):
            original_name = series_data.get('name', '')
            normalized_name = original_name.lower().strip()
            series_data['_normalized_name'] = normalized_name
            self._series_lc_names.append(normalized_name)
            series_data['_sort_name'] = normalized_name
            try:
                series_data['_sort_date'] = int(series_data.get('added', 0))
            except (ValueError, TypeError):
                series_data['_sort_date'] = 0
            try:
                series_data['_sort_rating'] = float(series_data.get('rating', 0))
            except (ValueError, TypeError):
                 series_data['_sort_rating'] = 0.0

    def search_series(self, text):
        """Fast search using index, similar to movies/channels."""
        from src.utils.text_search import TextSearch
        search_term = text.strip()
        if not self.series:
            self.display_series_grid([])
            return
        if not search_term:
            self.display_series_grid(self.series)
            return
        query_tokens = TextSearch.normalize_text(search_term).split()
        matched_indices = set()
        processed_first_token = False
        for token in query_tokens:
            if hasattr(self, '_series_search_index') and token in self._series_search_index:
                if not processed_first_token:
                    matched_indices = self._series_search_index[token].copy()
                    processed_first_token = True
                else:
                    matched_indices.intersection_update(self._series_search_index[token])
            else:
                matched_indices.clear()
                break
        # Fallback: substring search
        if not matched_indices:
            for idx, name in enumerate(self._series_lc_names):
                if search_term.lower() in name:
                    matched_indices.add(idx)
        filtered = [self.series[i] for i in sorted(matched_indices)]
        self.display_series_grid(filtered)

        if not self.series:
            # Optionally, show a message in the grid area if no favorites
            # For now, an empty grid will be shown by display_series_grid
            pass

    def display_series_grid(self, series_list):
        self.order_panel.setVisible(True if series_list else False)
        # Clear previous grid
        for i in reversed(range(self.series_grid_layout.count())):
            widget = self.series_grid_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        if not series_list:
            empty_label = QLabel(self.translations.get("This category doesn't contain any Series", "This category doesn't contain any Series"))
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
            tile.setStyleSheet("background: #222;")
            tile_layout = QVBoxLayout(tile)
            tile_layout.setContentsMargins(0, 0, 0, 0)
            tile_layout.setSpacing(4) # Adjust spacing for rating below poster
            # Series poster with overlay using absolute positioning
            poster_container = QWidget()
            poster_width = 125
            poster_height = 188 # Approx 1.5 aspect ratio (125 * 1.5 = 187.5)
            poster_container.setFixedSize(poster_width, poster_height)
            
            poster_label_widget = QLabel(poster_container) 
            poster_label_widget.setAlignment(Qt.AlignCenter)
            poster_label_widget.setGeometry(0, 0, poster_width, poster_height)
            poster_label_widget.setStyleSheet("background-color: #111111;") # Dark placeholder background

            default_pix = QPixmap('assets/series.png')
            if series.get('cover'):
                # Pass a lambda that calls onPosterDownloadFailed with series data and the label
                on_failure_callback = lambda s=series, lbl=poster_label_widget: self.onPosterDownloadFailed(s, lbl)
                load_image_async(series['cover'], poster_label_widget, default_pix.scaled(poster_width, poster_height, Qt.KeepAspectRatio, Qt.SmoothTransformation), update_size=(poster_width, poster_height), main_window=main_window, loading_counter=loading_counter, on_failure=on_failure_callback)
            else:
                poster_label_widget.setPixmap(default_pix.scaled(poster_width, poster_height, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                # Call fallback directly if no cover URL is provided initially
                self.onPosterDownloadFailed(series, poster_label_widget)

            # Title overlay
            title_text_label = QLabel(series['name'], poster_container) 
            title_text_label.setWordWrap(True)
            title_text_label.setAlignment(Qt.AlignCenter) 
            title_text_label.setFont(QFont('Arial', 14, QFont.Bold)) # User requested font 14px and bold
            title_text_label.setStyleSheet("background-color: rgba(0, 0, 0, 0.7); color: white; padding: 5px; border-radius: 0px;") 
            
            font_metrics = QFontMetrics(title_text_label.font())
            max_title_width = poster_width - 10 # 5px padding on each side for text
            # Calculate height for up to two lines of text.
            text_rect = font_metrics.boundingRect(QRect(0, 0, max_title_width, poster_height), Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap, series['name'])
            # Ensure title_height is at least one line, max two lines, plus padding.
            single_line_height = font_metrics.height()
            estimated_title_height = min(text_rect.height(), single_line_height * 2) # Cap actual text height at 2 lines
            title_box_height = estimated_title_height + 10 # Add 5px padding top/bottom

            title_text_label.setGeometry(0, poster_height - title_box_height, poster_width, title_box_height)
            title_text_label.raise_() 

            # Overlay 'new.png' if the series is new
            is_recent = False
            if series.get('added'):
                from datetime import datetime, timedelta # Import here is fine as it's conditional
                try:
                    added_time = datetime.fromtimestamp(int(series['added']))
                    if (datetime.now() - added_time) < timedelta(days=7):
                        is_recent = True
                except Exception:
                    pass 
            
            if is_recent:
                new_icon_size = 24 
                new_icon_padding = 5 
                new_icon_label = QLabel(poster_container) 
                new_icon_label.setPixmap(QPixmap('assets/new.png').scaled(new_icon_size, new_icon_size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                new_icon_label.setStyleSheet("background: transparent;")
                new_icon_label.setGeometry(poster_width - new_icon_size - new_icon_padding, new_icon_padding, new_icon_size, new_icon_size)
                new_icon_label.raise_() 
            
            tile_layout.addWidget(poster_container, alignment=Qt.AlignCenter)
            # Original series name QLabel is removed, title is now an overlay.
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
        self._opened_from_search = False
        self.current_series = series
        self.show_series_details(series)

    def onPosterDownloadFailed(self, series_data, poster_label_widget):
        """Callback function for when a poster download fails."""
        print(f"Poster download failed for series: {series_data.get('name')}. Attempting TMDB fallback.")
        # Implementation will follow: search TMDB, get poster, reload image
        # For now, just a placeholder
        series_name = series_data.get('name')
        tmdb_id = series_data.get('tmdb_id') # Assuming tmdb_id might exist
        series_year = None
        if series_data.get('releaseDate'):
            try:
                series_year = series_data.get('releaseDate').split('-')[0]
            except:
                pass # Ignore if year cannot be parsed

        tmdb_poster_path = None

        try:
            if tmdb_id:
                print(f"Attempting to fetch series details from TMDB with id: {tmdb_id}")
                series_details_tmdb = self.tmdb_client.get_series_details(tmdb_id)
                if series_details_tmdb and series_details_tmdb.get('poster_path'):
                    tmdb_poster_path = series_details_tmdb['poster_path']
                    print(f"Found poster via TMDB ID: {tmdb_poster_path}")

            if not tmdb_poster_path and series_name:
                print(f"Attempting to search series on TMDB with name: {series_name}, year: {series_year}")
                search_results = self.tmdb_client.search_series(series_name, year=series_year)
                if search_results and search_results.get('results'):
                    # Try to find a match, potentially based on name and year if available
                    # For simplicity, taking the first result for now
                    first_result = search_results['results'][0]
                    if first_result.get('poster_path'):
                        tmdb_poster_path = first_result['poster_path']
                        print(f"Found poster via TMDB search: {tmdb_poster_path}")
            
            if tmdb_poster_path:
                full_poster_url = self.tmdb_client.get_full_poster_url(tmdb_poster_path)
                print(f"Loading new poster from TMDB: {full_poster_url}")

                # Prepare data for cache update
                series_data_to_cache = series_data.copy() # Avoid modifying the original dict directly if it's a reference
                series_data_to_cache['cover'] = full_poster_url
                # If tmdb_id was found and used, or found via search, ensure it's in the data for caching
                if tmdb_id: # This would be the one from series_data initially
                    series_data_to_cache['tmdb_id'] = tmdb_id
                elif search_results and search_results.get('results') and search_results['results'][0].get('id'): # from name search
                    series_data_to_cache['tmdb_id'] = search_results['results'][0]['id']
                
                # Update the cache
                if hasattr(self.api_client, 'update_series_cache'):
                    print(f"Updating series cache for: {series_data_to_cache.get('name')} with new poster and TMDB ID.")
                    self.api_client.update_series_cache(series_data_to_cache)
                else:
                    print("api_client does not have update_series_cache method.")

                # Load the image
                poster_width = poster_label_widget.width() if poster_label_widget.width() > 0 else 125
                poster_height = poster_label_widget.height() if poster_label_widget.height() > 0 else 188
                default_pix = QPixmap('assets/series.png')
                load_image_async(full_poster_url, poster_label_widget, default_pix.scaled(poster_width, poster_height, Qt.KeepAspectRatio, Qt.SmoothTransformation), update_size=(poster_width, poster_height), main_window=self.main_window)
            else:
                print(f"No poster found on TMDB for series: {series_name}")
        except Exception as e:
            print(f"Error during TMDB fallback for series {series_name}: {e}")



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
        # self.download_thread.progress_update.connect( # Removed
        #     lambda progress, downloaded=0, total=0: self.update_download_progress(download_item, progress, downloaded, total)) # Removed
        # self.download_thread.download_complete.connect( # Removed
        #     lambda path: self.download_finished(download_item, path)) # Removed
        # self.download_thread.download_error.connect( # Removed
        #     lambda error: self.download_error(download_item, error)) # Removed
        
        # Add to downloads tab # Removed
        # if self.main_window and hasattr(self.main_window, 'downloads_tab'): # Removed
            # self.main_window.downloads_tab.add_download(download_item) # Removed
        
        # self.download_thread.start() # Removed
        pass # Download functionality removed
    
    def download_season(self):
        # This method is no longer needed as download functionality is removed.
        # QMessageBox.information(self, "Info", "Download functionality is currently disabled.")
        pass

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
        
        # Ensure stream_type is set for episodes
        if 'stream_type' not in episode:
            episode['stream_type'] = 'live'  # Episodes are typically treated as live streams
        
        # Use the main window's favorites manager directly if available
        main_window = self.window()
        if main_window and hasattr(main_window, 'favorites_manager'):
            main_window.favorites_manager.add_to_favorites(episode)
        else:
            # Fallback to signal emission
            self.add_to_favorites.emit(episode)

    # --- Pagination for series grid ---
    def setup_pagination_controls(self):
        self.pagination_panel = QWidget()
        nav_layout = QHBoxLayout(self.pagination_panel)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setAlignment(Qt.AlignCenter)
        self.prev_page_button = QPushButton(self.translations.get("Previous", "Previous"))
        self.next_page_button = QPushButton(self.translations.get("Next", "Next"))
        self.page_label = QLabel()
        self.prev_page_button.clicked.connect(self.go_to_previous_page)
        self.next_page_button.clicked.connect(self.go_to_next_page)
        nav_layout.addWidget(self.prev_page_button)
        nav_layout.addWidget(self.page_label)
        nav_layout.addWidget(self.next_page_button)
        self.pagination_panel.setVisible(False)

    def update_pagination_controls(self):
        if self.total_pages > 1:
            self.page_label.setText(f"{self.translations.get('Page', 'Page')} {self.current_page} {self.translations.get('of', 'of')} {self.total_pages}")
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
        # Clear existing grid items
        for i in reversed(range(self.series_grid_layout.count())):
            widget = self.series_grid_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        
        # Reset empty_state_label reference since it may have been cleared
        if hasattr(self, 'empty_state_label'):
            delattr(self, 'empty_state_label')
        
        # Create empty_state_label for empty results
        self.empty_state_label = QLabel()
        self.empty_state_label.setAlignment(Qt.AlignCenter)
        self.empty_state_label.setStyleSheet("color: #888; font-size: 18px; padding: 40px;")
        self.empty_state_label.setWordWrap(True)
        
        source_list = []
        search_active = hasattr(self, 'search_input') and self.search_input.text().strip()
        if search_active:
            if hasattr(self, 'filtered_series') and self.filtered_series is not None:
                source_list = self.filtered_series
        elif hasattr(self, 'series') and self.series is not None:
            source_list = self.series
        
        page_items, self.total_pages = self.paginate_items(source_list, self.current_page)
        if not page_items:
            # Show empty state label in the grid
            if search_active:
                query = self.search_input.text().strip()
                self.empty_state_label.setText(f"No results found for '{query}'.")
            else:
                self.empty_state_label.setText(self.translations.get("No items to display.", "No items to display."))
            self.series_grid_layout.addWidget(self.empty_state_label, 0, 0, 1, 4)
            self.update_pagination_controls()
            return
        else:
            self.empty_state_label.hide()
        self.display_series_grid(page_items) # display_series_grid takes the paginated items
        self.update_pagination_controls() # update_pagination_controls uses self.total_pages

    def on_order_changed(self):
        self.apply_sort_and_refresh()

    def on_sort_toggle(self):
        if self.sort_toggle.isChecked():
            self.sort_toggle.setText(self.translations.get("Desc", "Desc"))
        else:
            self.sort_toggle.setText(self.translations.get("Asc", "Asc"))
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
        self.build_series_search_index() # Rebuild index/normalized names if series order changed
        self.current_page = 1  # Reset to first page after sort
        self.search_series(self.search_input.text()) # Re-apply search to the sorted list
