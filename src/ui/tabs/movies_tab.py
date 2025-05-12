"""
Movies tab for the application
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
                            QListWidget, QPushButton, QLineEdit, QMessageBox,
                            QFileDialog, QLabel)
from PyQt5.QtCore import Qt, pyqtSignal
from src.ui.player import MediaPlayer
from src.utils.download import DownloadThread
from src.utils.download_item import DownloadItem  # Ensure this path is correct or adjust it

class MoviesTab(QWidget):
    """Movies tab widget"""
    add_to_favorites = pyqtSignal(dict)
    
    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.movies = []
        self.current_movie = None
        self.download_thread = None
        self.progress_dialog = None
        self.current_page = 1
        self.total_pages = 1
        self.page_size = 30
        self.all_items = []
        self.main_window = parent
        self.setup_ui()
    
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
        
        # Player and controls
        player_widget = QWidget()
        player_layout = QVBoxLayout(player_widget)
        player_layout.setContentsMargins(0, 0, 0, 0)
        
        self.player = MediaPlayer()
        
        # Additional controls
        controls_layout = QHBoxLayout()
        
        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self.play_movie)
        
        self.download_button = QPushButton("Download")
        self.download_button.clicked.connect(self.download_movie)
        
        self.add_favorite_button = QPushButton("Add to Favorites")
        self.add_favorite_button.clicked.connect(self.add_to_favorites_clicked)
        
        controls_layout.addWidget(self.play_button)
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
        # Add pagination controls to the UI
        pagination_layout = QHBoxLayout()
        self.prev_page_button = QPushButton("Previous")
        self.prev_page_button.clicked.connect(self.go_to_previous_page)
        self.page_label = QLabel("Page 1 of 1")
        self.next_page_button = QPushButton("Next")
        self.next_page_button.clicked.connect(self.go_to_next_page)
        pagination_layout.addWidget(self.prev_page_button)
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addWidget(self.next_page_button)

    def paginate_items(self, items, page):
        """Paginate items with 30 items per page"""
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
        # For MoviesTab
        self.movies_list.clear()
        page_items, self.total_pages = self.paginate_items(self.all_items, self.current_page)
        
        for item in page_items:
            self.movies_list.addItem(item['name'])
        
        self.update_pagination_controls()

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
        self.movies = all_movies
        for movie in all_movies:
            self.movies_list.addItem(movie['name'])

    def load_movies(self, category_id):
        """Load movies for the selected category"""
        self.movies_list.clear()
        
        success, data = self.api_client.get_vod_streams(category_id)
        if success:
            self.movies = data
            for movie in data:
                self.movies_list.addItem(movie['name'])
        else:
            QMessageBox.warning(self, "Error", f"Failed to load movies: {data}")
    
    def search_movies(self, text):
        """Search movies based on input text"""
        if not hasattr(self, 'all_items') or not self.all_items:
            return
        
        text = text.lower()
        
        if not text:
            # If search is cleared, show all items with pagination
            self.current_page = 1
            self.display_current_page()
            return
        
        # Filter items based on search text
        filtered_items = [item for item in self.all_items if text in item['name'].lower()]
        
        # Display filtered items
        self.movies_list.clear()
        self.current_page = 1
        page_items, self.total_pages = self.paginate_items(filtered_items, self.current_page)
        
        for item in page_items:
            self.movies_list.addItem(item['name'])
        
        self.update_pagination_controls()


    def movie_double_clicked(self, item):
        """Handle movie double-click"""
        self.play_movie()
    
    def play_movie(self):
        """Play the selected movie"""
        if not self.movies_list.currentItem():
            QMessageBox.warning(self, "Error", "No movie selected")
            return
        
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
    
    def download_movie(self):
        """Download the selected movie"""
        if not self.movies_list.currentItem():
            QMessageBox.warning(self, "Error", "No movie selected")
            return
        
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
        
        # Start download thread
        self.download_thread = DownloadThread(stream_url, save_path, self.api_client.headers)

            # Create download item and add to downloads tab
        download_item = DownloadItem(movie_name, save_path)
        self.main_window.downloads_tab.add_download(download_item)
        
        # Connect download thread signals to update download item
        self.download_thread.progress_update.connect(
            lambda progress: self.update_download_progress(download_item, progress))
        self.download_thread.download_complete.connect(
            lambda path: self.download_finished(download_item, path))
        self.download_thread.download_error.connect(
            lambda error: self.download_error(download_item, error))
        self.download_thread.start()
    
    def update_download_progress(self, download_item, progress, downloaded_size=0, total_size=0):
        """Update download progress in the downloads tab"""
        if download_item:
            # Update the download item
            download_item.update_progress(progress, downloaded_size, total_size)
            self.main_window.downloads_tab.update_downloads_table()

    def download_finished(self, download_item, save_path):
        """Handle download completion"""
        if download_item:
            # Update the download item
            download_item.complete(save_path)
            
            # Update the UI in the downloads tab
            self.main_window.downloads_tab.update_downloads_table()
        
    def download_error(self, download_item, error_message):
        """Handle download error"""
        if download_item:
            # Update the download item
            download_item.fail(error_message)
            
            # Update the UI in the downloads tab
            self.main_window.downloads_tab.update_downloads_table()

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