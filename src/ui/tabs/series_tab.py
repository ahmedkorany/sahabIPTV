"""
Series tab for the application
"""
import time
import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
                            QListWidget, QPushButton, QLineEdit, QMessageBox,
                            QFileDialog, QLabel, QProgressBar)
from PyQt5.QtCore import Qt, pyqtSignal
from src.ui.player import MediaPlayer
from src.utils.download import DownloadThread, BatchDownloadThread
from src.ui.widgets.dialogs import ProgressDialog

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
    """Series tab widget"""
    add_to_favorites = pyqtSignal(dict)
    add_to_downloads = pyqtSignal(object)  # Signal to add download to downloads tab
    
    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.series_data = []
        self.all_series = []  # Store all series across categories
        self.filtered_series = []  # Store filtered series for search
        self.current_series = None
        self.current_episodes = []
        self.current_episode = None
        self.download_thread = None
        self.batch_download_thread = None
        
        # Pagination
        self.current_page = 1
        self.total_pages = 1
        self.page_size = 30
        
        self.setup_ui()
        self.main_window = None  # Will be set by the main window
    
    def setup_ui(self):
        """Set up the UI components"""
        layout = QVBoxLayout(self)
        
        # Search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search series...")
        self.search_input.textChanged.connect(self.search_series)
        search_layout.addWidget(self.search_input)
        
        # Main content area with splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Lists widget
        lists_widget = QWidget()
        lists_layout = QHBoxLayout(lists_widget)
        lists_layout.setContentsMargins(0, 0, 0, 0)
        
        # Categories, series, seasons, episodes
        categories_widget = QWidget()
        categories_layout = QVBoxLayout(categories_widget)
        categories_layout.setContentsMargins(0, 0, 0, 0)
        
        self.categories_list = QListWidget()
        self.categories_list.setMinimumWidth(150)
        self.categories_list.itemClicked.connect(self.category_clicked)
        
        categories_layout.addWidget(QLabel("Categories"))
        categories_layout.addWidget(self.categories_list)
        
        series_widget = QWidget()
        series_layout = QVBoxLayout(series_widget)
        series_layout.setContentsMargins(0, 0, 0, 0)
        
        self.series_list = QListWidget()
        self.series_list.setMinimumWidth(200)
        self.series_list.itemClicked.connect(self.series_clicked)
        
        # Pagination controls for series
        series_pagination_layout = QHBoxLayout()
        self.series_prev_button = QPushButton("Previous")
        self.series_prev_button.clicked.connect(self.go_to_previous_series_page)
        self.series_page_label = QLabel("Page 1 of 1")
        self.series_next_button = QPushButton("Next")
        self.series_next_button.clicked.connect(self.go_to_next_series_page)
        series_pagination_layout.addWidget(self.series_prev_button)
        series_pagination_layout.addWidget(self.series_page_label)
        series_pagination_layout.addWidget(self.series_next_button)
        
        series_layout.addWidget(QLabel("Series"))
        series_layout.addWidget(self.series_list)
        series_layout.addLayout(series_pagination_layout)
        
        seasons_widget = QWidget()
        seasons_layout = QVBoxLayout(seasons_widget)
        seasons_layout.setContentsMargins(0, 0, 0, 0)
        
        self.seasons_list = QListWidget()
        self.seasons_list.setMinimumWidth(100)
        self.seasons_list.itemClicked.connect(self.season_clicked)
        
        seasons_layout.addWidget(QLabel("Seasons"))
        seasons_layout.addWidget(self.seasons_list)
        
        episodes_widget = QWidget()
        episodes_layout = QVBoxLayout(episodes_widget)
        episodes_layout.setContentsMargins(0, 0, 0, 0)
        
        self.episodes_list = QListWidget()
        self.episodes_list.setMinimumWidth(200)
        self.episodes_list.itemDoubleClicked.connect(self.episode_double_clicked)
        
        episodes_layout.addWidget(QLabel("Episodes"))
        episodes_layout.addWidget(self.episodes_list)
        
        lists_layout.addWidget(categories_widget)
        lists_layout.addWidget(series_widget)
        lists_layout.addWidget(seasons_widget)
        lists_layout.addWidget(episodes_widget)
        
        # Player and controls
        player_widget = QWidget()
        player_layout = QVBoxLayout(player_widget)
        player_layout.setContentsMargins(0, 0, 0, 0)
        
        self.player = MediaPlayer(parent=self)
        self.player.controls.play_pause_button.clicked.connect(self.play_episode)
        self.episodes_list.itemClicked.connect(self.player.controls.stop_clicked)

        # Additional controls
        controls_layout = QHBoxLayout()
        
        self.download_episode_button = QPushButton("Download Episode")
        self.download_episode_button.clicked.connect(self.download_episode)
        
        self.download_season_button = QPushButton("Download Season")
        self.download_season_button.clicked.connect(self.download_season)

        self.export_season_button = QPushButton("Export Season")
        self.export_season_button.clicked.connect(self.export_season)
        
        self.add_favorite_button = QPushButton("Add to Favorites")
        self.add_favorite_button.clicked.connect(self.add_to_favorites_clicked)
        
        controls_layout.addWidget(self.download_episode_button)
        controls_layout.addWidget(self.download_season_button)
        controls_layout.addWidget(self.export_season_button)
        controls_layout.addWidget(self.add_favorite_button)
        
        player_layout.addWidget(self.player)
        player_layout.addLayout(controls_layout)
        
        # Add widgets to splitter
        splitter.addWidget(lists_widget)
        splitter.addWidget(player_widget)
        splitter.setSizes([600, 800])
        
        # Add all components to main layout
        layout.addLayout(search_layout)
        layout.addWidget(splitter)
    
    def load_categories(self):
        """Load series categories from the API"""
        self.categories_list.clear()
        
        success, data = self.api_client.get_series_categories()
        if success:
            # Add "All" category at the beginning
            self.categories_list.addItem("All")
            
            # Add the rest of the categories
            for category in data:
                self.categories_list.addItem(category['category_name'])
        else:
            QMessageBox.warning(self, "Error", f"Failed to load categories: {data}")
    
    def category_clicked(self, item):
        """Handle category selection"""
        category_name = item.text()
        
        if category_name == "All":
            # Load all series across categories
            self.load_all_series()
        else:
            # Find category ID
            success, categories = self.api_client.get_series_categories()
            if not success:
                QMessageBox.warning(self, "Error", f"Failed to load categories: {categories}")
                return
            
            category_id = None
            for category in categories:
                if category['category_name'] == category_name:
                    category_id = category['category_id']
                    break
            
            if category_id:
                self.load_series(category_id)
    
    def load_all_series(self):
        """Load all series from all categories"""
        self.series_list.clear()
        self.seasons_list.clear()
        self.episodes_list.clear()
        all_series = []
        
        # Get all categories
        success, categories = self.api_client.get_series_categories()
        if not success:
            QMessageBox.warning(self, "Error", f"Failed to load categories: {categories}")
            return
        
        # Get series from each category
        for category in categories:
            success, series = self.api_client.get_series(category['category_id'])
            if success:
                all_series.extend(series)
        
        # Update the series list
        self.all_series = all_series
        self.filtered_series = all_series
        self.current_page = 1
        self.display_current_series_page()
    
    def load_series(self, category_id):
        """Load series for the selected category"""
        self.series_list.clear()
        self.seasons_list.clear()
        self.episodes_list.clear()
        
        success, data = self.api_client.get_series(category_id)
        if success:
            self.all_series = data
            self.filtered_series = data
            self.current_page = 1
            self.display_current_series_page()
        else:
            QMessageBox.warning(self, "Error", f"Failed to load series: {data}")
    
    def paginate_items(self, items, page):
        """Paginate items with specified items per page"""
        total_items = len(items)
        total_pages = max(1, (total_items + self.page_size - 1) // self.page_size)
        
        if page < 1:
            page = 1
        if page > total_pages:
            page = total_pages
        
        start = (page - 1) * self.page_size
        end = min(start + self.page_size, total_items)
        
        return items[start:end], total_pages
    
    def update_series_pagination_controls(self):
        """Update series pagination controls based on current state"""
        self.series_page_label.setText(f"Page {self.current_page} of {self.total_pages}")
        self.series_prev_button.setEnabled(self.current_page > 1)
        self.series_next_button.setEnabled(self.current_page < self.total_pages)
    
    def go_to_previous_series_page(self):
        """Go to the previous page of series"""
        if self.current_page > 1:
            self.current_page -= 1
            self.display_current_series_page()
    
    def go_to_next_series_page(self):
        """Go to the next page of series"""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.display_current_series_page()
    
    def display_current_series_page(self):
        """Display the current page of series"""
        self.series_list.clear()
        page_items, self.total_pages = self.paginate_items(self.filtered_series, self.current_page)
        
        for item in page_items:
            self.series_list.addItem(item['name'])
        
        self.update_series_pagination_controls()
    
    def search_series(self, text):
        """Search series based on input text"""
        if not self.all_series:
            return
        
        text = text.lower()
        
        if not text:
            # If search is cleared, show all items with pagination
            self.filtered_series = self.all_series
        else:
            # Filter items based on search text
            self.filtered_series = [item for item in self.all_series if text in item['name'].lower()]
        
        # Reset to first page and display results
        self.current_page = 1
        self.display_current_series_page()
    
    def series_clicked(self, item):
        """Handle series selection"""
        series_name = item.text()
        
        # Find series in data
        series = None
        for s in self.filtered_series:
            if s['name'] == series_name:
                series = s
                break
        
        if not series:
            return
        
        self.current_series = series
        self.load_seasons(series['series_id'])
    
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
        self.play_episode()
    
    def play_episode(self):
        if(self.player.play_started == False):
            """Play the selected episode"""
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
            
            # Get container extension (default to mp4)
            container_extension = episode.get('container_extension', 'mp4')
            
            stream_url = self.api_client.get_series_url(episode_id, container_extension)
            
            if self.player.play(stream_url):
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
                self.player.controls.play_pause_button.clicked.disconnect(self.play_episode)
        else:
                self.player.play_pause(True)

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
        if not self.current_episode:
            QMessageBox.warning(self, "Error", "No episode is playing")
            return
        
        self.add_to_favorites.emit(self.current_episode)
