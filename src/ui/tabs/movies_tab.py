"""
Movies tab for the application
"""
import time
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
                            QListWidget, QPushButton, QLineEdit, QMessageBox,
                            QFileDialog, QLabel, QProgressBar, QHeaderView, 
                            QTableWidget, QTableWidgetItem)
from PyQt5.QtCore import Qt, pyqtSignal
from src.ui.player import MediaPlayer
from src.utils.download import DownloadThread
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
        """Set up the UI components"""
        layout = QVBoxLayout(self)
        
        # Search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search movies...")
        self.search_input.textChanged.connect(self.search_movies)
        search_layout.addWidget(self.search_input)
        
        # Main content area with splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Categories and movies lists
        lists_widget = QWidget()
        lists_layout = QVBoxLayout(lists_widget)
        lists_layout.setContentsMargins(0, 0, 0, 0)
        
        self.categories_list = QListWidget()
        self.categories_list.setMinimumWidth(200)
        self.categories_list.itemClicked.connect(self.category_clicked)
        
        self.movies_list = QListWidget()
        self.movies_list.setMinimumWidth(300)
        self.movies_list.itemDoubleClicked.connect(self.movie_double_clicked)
        
        lists_layout.addWidget(QLabel("Categories"))
        lists_layout.addWidget(self.categories_list)
        lists_layout.addWidget(QLabel("Movies"))
        lists_layout.addWidget(self.movies_list)
        
        # Pagination controls
        pagination_layout = QHBoxLayout()
        self.prev_page_button = QPushButton("Previous")
        self.prev_page_button.clicked.connect(self.go_to_previous_page)
        self.page_label = QLabel("Page 1 of 1")
        self.next_page_button = QPushButton("Next")
        self.next_page_button.clicked.connect(self.go_to_next_page)
        pagination_layout.addWidget(self.prev_page_button)
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addWidget(self.next_page_button)
        lists_layout.addLayout(pagination_layout)
        
        # Player and controls
        player_widget = QWidget()
        player_layout = QVBoxLayout(player_widget)
        player_layout.setContentsMargins(0, 0, 0, 0)
        
        self.player = MediaPlayer(parent=self)
        self.player.controls.play_pause_button.clicked.connect(self.play_movie)
        self.movies_list.itemClicked.connect(self.player.controls.stop_clicked)

        # Additional controls
        controls_layout = QHBoxLayout()
        
        self.download_button = QPushButton("Download")
        self.download_button.clicked.connect(self.download_movie)
        
        self.add_favorite_button = QPushButton("Add to Favorites")
        self.add_favorite_button.clicked.connect(self.add_to_favorites_clicked)
        
        controls_layout.addWidget(self.download_button)
        controls_layout.addWidget(self.add_favorite_button)
        
        player_layout.addWidget(self.player)
        player_layout.addLayout(controls_layout)
        
        # Add widgets to splitter
        splitter.addWidget(lists_widget)
        splitter.addWidget(player_widget)
        splitter.setSizes([400, 800])
        
        # Add all components to main layout
        layout.addLayout(search_layout)
        layout.addWidget(splitter)
    
    def load_categories(self):
        """Load movie categories from the API"""
        self.categories_list.clear()
        
        success, data = self.api_client.get_vod_categories()
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
            # Load all movies across categories
            self.load_all_movies()
        else:
            # Find category ID
            success, categories = self.api_client.get_vod_categories()
            if not success:
                QMessageBox.warning(self, "Error", f"Failed to load categories: {categories}")
                return
            
            category_id = None
            for category in categories:
                if category['category_name'] == category_name:
                    category_id = category['category_id']
                    break
            
            if category_id:
                self.load_movies(category_id)
    
    def load_all_movies(self):
        """Load all movies from all categories"""
        self.movies_list.clear()
        all_movies = []
        
        # Get all categories
        success, categories = self.api_client.get_vod_categories()
        if not success:
            QMessageBox.warning(self, "Error", f"Failed to load categories: {categories}")
            return
        
        # Get movies from each category
        for category in categories:
            success, movies = self.api_client.get_vod_streams(category['category_id'])
            if success:
                all_movies.extend(movies)
        
        # Update the movies list
        self.all_movies = all_movies
        self.filtered_movies = all_movies
        self.current_page = 1
        self.display_current_page()
    
    def load_movies(self, category_id):
        """Load movies for the selected category"""
        self.movies_list.clear()
        
        success, data = self.api_client.get_vod_streams(category_id)
        if success:
            self.all_movies = data
            self.filtered_movies = data
            self.current_page = 1
            self.display_current_page()
        else:
            QMessageBox.warning(self, "Error", f"Failed to load movies: {data}")
    
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
    
    def update_pagination_controls(self):
        """Update pagination controls based on current state"""
        self.page_label.setText(f"Page {self.current_page} of {self.total_pages}")
        self.prev_page_button.setEnabled(self.current_page > 1)
        self.next_page_button.setEnabled(self.current_page < self.total_pages)
    
    def go_to_previous_page(self):
        """Go to the previous page"""
        if self.current_page > 1:
            self.current_page -= 1
            self.display_current_page()
    
    def go_to_next_page(self):
        """Go to the next page"""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.display_current_page()
    
    def display_current_page(self):
        """Display the current page of items"""
        self.movies_list.clear()
        page_items, self.total_pages = self.paginate_items(self.filtered_movies, self.current_page)
        
        for item in page_items:
            self.movies_list.addItem(item['name'])
        
        self.update_pagination_controls()
    
    def search_movies(self, text):
        """Search movies based on input text"""
        if not self.all_movies:
            return
        
        text = text.lower()
        
        if not text:
            # If search is cleared, show all items with pagination
            self.filtered_movies = self.all_movies
        else:
            # Filter items based on search text
            self.filtered_movies = [item for item in self.all_movies if text in item['name'].lower()]
        
        # Reset to first page and display results
        self.current_page = 1
        self.display_current_page()
    
    def movie_double_clicked(self, item):
        """Handle movie double-click"""
        self.play_movie()
    
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
        
        self.add_to_favorites.emit(self.current_movie)
