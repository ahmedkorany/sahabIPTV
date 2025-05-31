"""
Movies tab for the application
"""
from operator import contains
from functools import partial
from PyQt5.QtGui import QFontMetrics
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QLabel, QMessageBox, QListWidgetItem, QScrollArea, QGridLayout, QComboBox, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QPixmap, QFont, QFontMetrics
from PyQt5.QtCore import QRect
from src.ui.widgets.movie_details_widget import MovieDetailsWidget
from src.utils.helpers import load_image_async, get_translations
from src.api.tmdb import TMDBClient
from src.ui.widgets.dialogs import MovieDetailsDialog
from src.models import MovieItem

class MoviesTab(QWidget):
    """Movies tab widget"""
    add_to_favorites = pyqtSignal(dict)
    
    def __init__(self, api_client, favorites_manager=None, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.favorites_manager = favorites_manager
        self.main_window = parent
        self.details_widget = None
        self.movies = []
        self.all_movies = []  # Store all movies across categories
        self._opened_from_search = False
        self.filtered_movies = []  # Store filtered movies for search (now just a copy of movies)
        self.current_movie = None
        self.poster_labels = {} # To store poster labels by stream_id
        
        # Pagination
        self.current_page = 1
        self.total_pages = 1
        self.page_size = 32 # Consistent page size

        # Search index attributes (no longer used)
        self._movie_search_index = {}  # token -> set of indices
        self._movie_lc_names = []      # lowercased names for fallback
        
        # Initialize TMDB client once for all details widgets
        self.tmdb_client = TMDBClient()  # Loads keys from .env automatically
        
        # Get translations from main window
        self.translations = get_translations(parent.language if parent and hasattr(parent, 'language') else 'en')

        self.setup_ui() # self.main_window is already set from parent

    def setup_ui(self):
        layout = QVBoxLayout(self)
        # Search bar (removed)
        # search_layout = QHBoxLayout()
        # self.search_input = QLineEdit()
        # self.search_input.setPlaceholderText("Search movies...")
        # self.search_input.textChanged.connect(self.search_movies)
        # search_layout.addWidget(self.search_input)
        # layout.addLayout(search_layout)

        # Stacked widget for grid/details views
        from PyQt5.QtWidgets import QStackedWidget
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
        grid_panel.addWidget(QLabel(self.translations.get("Movies", "Movies")))
        grid_panel.addWidget(self.movie_grid_scroll)
        grid_widget = QWidget()
        grid_widget.setLayout(grid_panel)

        # Sorting panel (initially hidden)
        self.order_panel = QWidget()
        order_layout = QHBoxLayout(self.order_panel)
        order_label = QLabel(self.translations.get("Order by", "Order by:"))
        self.order_combo = QComboBox()
        self.order_combo.addItems([self.translations.get("Default", "Default"), self.translations.get("Date", "Date"), self.translations.get("Rating", "Rating"), self.translations.get("Name", "Name")])
        self.order_combo.setCurrentIndex(0)
        self.order_combo.currentIndexChanged.connect(self._handle_sort_criteria_changed)
        self.sort_toggle = QPushButton(self.translations.get("Desc", "Desc"))
        self.sort_toggle.setCheckable(True)
        self.sort_toggle.setChecked(True)
        self.sort_toggle.clicked.connect(self._handle_sort_criteria_changed)
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
        self.update_pagination_controls()

    def on_order_changed(self):
        self.apply_sort_and_refresh()

    def on_sort_toggle(self):
        if self.sort_toggle.isChecked():
            self.sort_toggle.setText(self.translations.get("Desc", "Desc"))
        else:
            self.sort_toggle.setText(self.translations.get("Asc", "Asc"))
        self.apply_sort_and_refresh()

    def _handle_sort_criteria_changed(self):
        self.apply_sort_and_refresh()

    def apply_sort_and_refresh(self):
        # Determine the list to sort.
        if hasattr(self, 'filtered_movies') and self.filtered_movies is not None:
            items_to_sort = list(self.filtered_movies)
        elif hasattr(self, 'movies') and self.movies:
            items_to_sort = list(self.movies)
        else:
            items_to_sort = []

        sort_field = self.order_combo.currentText()
        reverse = self.sort_toggle.isChecked()

        if sort_field == self.translations.get("Default", "Default"):
            # For "Default" sort, just reset filtered_movies to movies
            self.filtered_movies = list(self.movies) if hasattr(self, 'movies') and self.movies else []
            self.current_page = 1
            self.display_current_page()
            return

        if not items_to_sort:
            self.filtered_movies = []
            self.current_page = 1
            self.display_current_page()
            return

        key_func = None
        if sort_field == self.translations.get("Date", "Date"):
            key_func = lambda x: getattr(x, '_sort_date', 0) if isinstance(x, MovieItem) else x.get('_sort_date', 0)
        elif sort_field == self.translations.get("Name", "Name"):
            key_func = lambda x: getattr(x, '_sort_name', '') if isinstance(x, MovieItem) else x.get('_sort_name', '')
        elif sort_field == self.translations.get("Rating", "Rating"):
            key_func = lambda x: getattr(x, '_sort_rating', 0) if isinstance(x, MovieItem) else x.get('_sort_rating', 0)
        
        if key_func:
            sorted_items = sorted(items_to_sort, key=key_func, reverse=reverse)
        else:
            sorted_items = items_to_sort 
        
        self.filtered_movies = sorted_items
        self.current_page = 1
        self.display_current_page()

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

    def load_categories(self):
        """Load movie categories from the API"""
        self.categories_list.clear()
        self.categories = []
        success, data = self.api_client.get_vod_categories()
        if success:
            self.categories = data
            # Add "ALL" category at the top
            all_item = QListWidgetItem(self.translations.get("All", "ALL"))
            all_item.setData(Qt.UserRole, None) # None for ALL category_id
            self.categories_list.addItem(all_item)

            # Add "Favorites" category
            favorites_item = QListWidgetItem(self.translations.get("Favorites", "Favorites"))
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
            QMessageBox.warning(self, self.translations.get("Error", "Error"), f"{self.translations.get('Failed to load categories', 'Failed to load categories')}: {data}")

    def category_clicked(self, item):
        category_id = item.data(Qt.UserRole)
        # Reset sorting controls to default
        self.order_combo.setCurrentIndex(0)  # Default
        self.sort_toggle.setChecked(True)    # Desc
        self.sort_toggle.setText(self.translations.get("Desc", "Desc"))
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
                self.all_movies = [MovieItem.from_dict(item) for item in all_movies_temp] # Store all movies
            self.movies = list(self.all_movies) # Use a copy for current display
        else:
            # This branch handles specific category_id (not None and not 'favorites')
            success, data = self.api_client.get_vod_streams(category_id)
            if success:
                self.movies = [MovieItem.from_dict(item) for item in data]
            else:
                QMessageBox.warning(self, self.translations.get("Error", "Error"), f"{self.translations.get('Failed to load movies', 'Failed to load movies')}: {data}")
        self.current_page = 1
        self.build_movie_search_index() # Still needed for sort fields
        self.filtered_movies = list(self.movies) # Reset filtered list to all current movies
        self.display_current_page() # Will use self.filtered_movies

    def load_favorite_movies(self):
        """Load and display favorite movies using the favorites_manager."""
        if not self.favorites_manager:
            QMessageBox.warning(self, self.translations.get("Error", "Error"), self.translations.get("Favorites manager not available.", "Favorites manager not available."))
            self.movies = []
            self.current_page = 1
            self.display_current_page()
            return

        # Get favorites from the favorites manager and filter for movies
        all_favorites = self.favorites_manager.get_favorites()
        movie_favorites = [
            fav for fav in all_favorites
            if fav.get('stream_type') == 'movie'
        ]
        self.movies = [MovieItem.from_dict(item) for item in movie_favorites]

        self.current_page = 1  # Reset to first page for favorites
        self.build_movie_search_index()  # Build index after loading (depends on self.movies)
        self.filtered_movies = list(self.movies) # Reset filtered list
        # display_current_page will handle pagination and display
        # It should also update total_pages based on self.movies
        self.display_current_page() # Will use self.filtered_movies

    def build_movie_search_index(self):
        """Builds sort fields for movies (search index logic removed)."""
        self._movie_search_index = {}
        self._movie_lc_names = []
        if not hasattr(self, 'movies') or not self.movies:
            return
        for idx, movie_data in enumerate(self.movies):
            if isinstance(movie_data, MovieItem):
                original_name = movie_data.name or ''
                normalized_name = original_name.lower().strip()
                movie_data._normalized_name = normalized_name
                self._movie_lc_names.append(normalized_name)
                movie_data._sort_name = normalized_name
                try:
                    movie_data._sort_date = int(movie_data.added or 0)
                except (ValueError, TypeError):
                    movie_data._sort_date = 0
                try:
                    movie_data._sort_rating = float(movie_data.rating or 0)
                except (ValueError, TypeError):
                    movie_data._sort_rating = 0.0
            else:
                # Fallback for dictionary format
                original_name = movie_data.get('name', '')
                normalized_name = original_name.lower().strip()
                movie_data['_normalized_name'] = normalized_name
                self._movie_lc_names.append(normalized_name)
                movie_data['_sort_name'] = normalized_name
                try:
                    movie_data['_sort_date'] = int(movie_data.get('added', 0))
                except (ValueError, TypeError):
                    movie_data['_sort_date'] = 0
                try:
                    movie_data['_sort_rating'] = float(movie_data.get('rating', 0))
                except (ValueError, TypeError):
                    movie_data['_sort_rating'] = 0.0

    def display_movie_grid(self, movies):
        """Display movies as a grid of tiles"""
        # Grid is cleared in display_current_page before this method is called
        if not movies:
            message = self.translations.get("This category currently has no movies.", "This category currently has no movies.") # Default message
            empty_label = QLabel(message)
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setStyleSheet("color: #aaa; font-size: 18px; padding: 40px;")
            self.movie_grid_layout.addWidget(empty_label, 0, 0, 1, 4) # Add to grid
            if hasattr(self, 'order_panel'):
                self.order_panel.setVisible(False)
            return
        # Ensure order_panel visibility is correctly set when movies are present
        if hasattr(self, 'order_panel') and hasattr(self, 'categories_list'):
            current_category_item = self.categories_list.currentItem()
            is_favorites_category = False
            if current_category_item:
                category_id = current_category_item.data(Qt.UserRole)
                if category_id == "favorites":
                    is_favorites_category = True
            # Show order panel if there are movies to display AND it's not the favorites category
            self.order_panel.setVisible(bool(movies) and not is_favorites_category)

        cols = 4
        row = 0
        col = 0
        main_window = self.main_window if hasattr(self, 'main_window') else None
        for movie in movies:
            tile = QFrame()
            tile.setFrameShape(QFrame.StyledPanel)
            tile.setStyleSheet("background: #222;")
            tile_layout = QVBoxLayout(tile)
            tile_layout.setContentsMargins(0, 0, 0, 0)
            tile_layout.setSpacing(4) # Adjust spacing for rating below poster
            # Movie poster with overlay using absolute positioning
            poster_container = QWidget()
            poster_width = 125
            poster_height = 188 # Approx 1.5 aspect ratio (125 * 1.5 = 187.5)
            poster_container.setFixedSize(poster_width, poster_height)
            
            poster_label_widget = QLabel(poster_container) 
            poster_label_widget.setAlignment(Qt.AlignCenter)
            poster_label_widget.setGeometry(0, 0, poster_width, poster_height)
            poster_label_widget.setStyleSheet("background-color: #111111;") # Dark placeholder background

            # Store the label for potential updates
            if isinstance(movie, MovieItem):
                stream_id_str = str(movie.stream_id)
                movie_name = movie.name or 'Unnamed Movie'
                movie_icon = movie.stream_icon
            else:
                stream_id_str = str(movie.get('stream_id'))
                movie_name = movie.get('name', 'Unnamed Movie')
                movie_icon = movie.get('stream_icon')
            
            self.poster_labels[stream_id_str] = poster_label_widget

            default_pix = QPixmap('assets/movies.png')
            if movie_icon:
                load_image_async(movie_icon, poster_label_widget, default_pix.scaled(poster_width, poster_height, Qt.KeepAspectRatio, Qt.SmoothTransformation), update_size=(poster_width, poster_height), main_window=main_window, on_failure=partial(self.onPosterDownloadFailed, movie))
            else:
                poster_label_widget.setPixmap(default_pix.scaled(poster_width, poster_height, Qt.KeepAspectRatio, Qt.SmoothTransformation))

            # Title overlay
            title_text_label = QLabel(movie_name, poster_container) 
            title_text_label.setWordWrap(True)
            title_text_label.setAlignment(Qt.AlignCenter) 
            title_text_label.setFont(QFont('Arial', 14, QFont.Bold)) # User requested font 14px and bold
            title_text_label.setStyleSheet("background-color: rgba(0, 0, 0, 0.7); color: white; padding: 5px; border-radius: 0px;") 
            
            font_metrics = QFontMetrics(title_text_label.font())
            max_title_width = poster_width - 10 # 5px padding on each side for text
            text_rect = font_metrics.boundingRect(QRect(0, 0, max_title_width, poster_height), Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap, movie_name)
            single_line_height = font_metrics.height()
            estimated_title_height = min(text_rect.height(), single_line_height * 2) 
            title_box_height = estimated_title_height + 10 

            title_text_label.setGeometry(0, poster_height - title_box_height, poster_width, title_box_height)
            title_text_label.raise_() 

            # Overlay 'new.png' if the movie is new
            is_recent = False
            movie_added = movie.added if isinstance(movie, MovieItem) else movie.get('added')
            if movie_added:
                from datetime import datetime, timedelta # Import here is fine as it's conditional
                try:
                    added_time = datetime.fromtimestamp(int(movie_added))
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
            # Original movie name QLabel is removed, title is now an overlay.
            # name_text = movie.get('name', 'Unnamed Movie')
            # name = QLabel(name_text)
            # name.setAlignment(Qt.AlignCenter)
            # name.setWordWrap(True)
            # name.setFont(QFont('Arial', 11, QFont.Bold))
            # name.setStyleSheet("color: #fff;")
            # tile_layout.addWidget(name)
            # Rating (if available)
            movie_rating = movie.rating if isinstance(movie, MovieItem) else movie.get('rating')
            if movie_rating:
                rating = QLabel(f"★ {movie_rating}")
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
        self.details_widget.back_btn.clicked.connect(self._handle_back_from_details)
        self.details_widget.play_clicked.connect(self._play_movie_from_details)
        self.details_widget.trailer_clicked.connect(self._play_trailer)
        self.details_widget.toggle_favorite_movie_requested.connect(self._handle_toggle_favorite_request)
        # Connect to main window's favorites_changed signal to refresh button state
        if hasattr(self.main_window, 'favorites_changed'):
            self.main_window.favorites_changed.connect(self._on_favorites_changed)
        self.stacked_widget.addWidget(self.details_widget)
        self.stacked_widget.setCurrentWidget(self.details_widget)

    def show_movie_grid(self):
        self.stacked_widget.setCurrentIndex(0)

    def _handle_back_from_details(self):
        if self._opened_from_search:
            if self.main_window and hasattr(self.main_window, 'search_tab') and self.main_window.search_tab:
                self.main_window.tabs.setCurrentWidget(self.main_window.search_tab)
            self._opened_from_search = False # Reset flag
            # Ensure the movie tab is reset to grid view for future navigation to it
            self.show_movie_grid()
        else:
            self.show_movie_grid()
            # Check if favorites category is selected and refresh if needed
            current_category_item = self.categories_list.currentItem()
            if current_category_item:
                category_id = current_category_item.data(Qt.UserRole)
                if category_id == "favorites":
                    # Refresh favorites grid in case favorite state changed
                    self.load_favorite_movies()
                else:
                    self.display_current_page()
            else:
                self.display_current_page()

    def show_movie_details_by_data(self, movie_data):
        """Show movie details from search data"""
        self._opened_from_search = True
        
        # Validate and convert movie data if necessary
        if not movie_data:
            QMessageBox.warning(self, "Error", "Invalid movie data provided.")
            return
            
        # Ensure movie_data is a MovieItem instance for consistent handling
        if not isinstance(movie_data, MovieItem):
            try:
                movie_data = MovieItem.from_dict(movie_data)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to process movie data: {str(e)}")
                return
        
        # Remove old details widget if present
        if self.details_widget:
            self.stacked_widget.removeWidget(self.details_widget)
            self.details_widget.deleteLater()
            self.details_widget = None
        
        # Create a new details widget using MovieDetailsWidget
        self.details_widget = MovieDetailsWidget(
            movie_data,
            api_client=self.api_client,
            main_window=self.main_window,
            tmdb_client=self.tmdb_client,
            parent=self
        )
        self.details_widget.back_btn.clicked.connect(self._handle_back_from_details)
        self.details_widget.play_clicked.connect(self._play_movie_from_details)
        self.details_widget.trailer_clicked.connect(self._play_trailer)
        self.details_widget.toggle_favorite_movie_requested.connect(self._handle_toggle_favorite_request)
        # Connect to main window's favorites_changed signal to refresh button state
        if hasattr(self.main_window, 'favorites_changed'):
            self.main_window.favorites_changed.connect(self._on_favorites_changed)
        self.stacked_widget.addWidget(self.details_widget)
        self.stacked_widget.setCurrentWidget(self.details_widget)

    def movie_tile_clicked(self, movie):
        """Handle movie tile click"""
        self._opened_from_search = False
        self.current_movie = movie
        self.show_movie_details(movie)

    def _play_movie_from_details(self, movie):
        # Reuse the logic from the dialog, but adapted for tab context
        main_window = self.window()
        dlg = MovieDetailsDialog(movie, self.api_client, parent=self, main_window=main_window)
        # Create movie item with necessary information for favorites
        if isinstance(movie, MovieItem):
            movie_item = {
                'name': movie.name,
                'stream_id': movie.stream_id,
                'container_extension': movie.container_extension,
                'stream_type': 'movie'
            }
        else:
            movie_item = {
                'name': movie['name'],
                'stream_id': movie['stream_id'],
                'container_extension': movie.get('container_extension', ''),
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
            QMessageBox.warning(self, self.translations.get("Error", "Error"), self.translations.get("Player window not available.", "Player window not available."))

    def _handle_toggle_favorite_request(self, movie_data):
        """Handle toggle favorite request from details widget"""
        main_window = self.main_window
        if not main_window or not hasattr(main_window, 'favorites_manager'):
            # Fallback to signal emission if main window favorites manager is not available
            self.add_to_favorites.emit(movie_data)
            return

        # Convert MovieItem to dictionary if needed
        if isinstance(movie_data, MovieItem):
            movie_dict = movie_data.to_dict()
            movie_dict['stream_type'] = 'movie'
            favorite_item = movie_dict
        else:
            # Ensure 'stream_type' is present in movie_data
            if 'stream_type' not in movie_data:
                movie_data['stream_type'] = 'movie'

            # Create favorite item with required fields
            favorite_item = {
                'stream_id': movie_data.get('stream_id'),
                'stream_type': 'movie',
                'name': movie_data.get('name', ''),
                'cover': movie_data.get('stream_icon', ''),
                'category_id': movie_data.get('category_id', ''),
                'added': movie_data.get('added', ''),
                'rating': movie_data.get('rating', ''),
                'rating_5based': movie_data.get('rating_5based', ''),
                'container_extension': movie_data.get('container_extension', '')
            }

            # Add other fields as expected by favorites manager
            for key, value in movie_data.items():
                if key not in favorite_item:
                    favorite_item[key] = value

        # Use favorites manager to toggle favorite status
        main_window.favorites_manager.toggle_favorite(favorite_item)

        # Refresh the favorite button in the details widget
        if hasattr(self.details_widget, 'refresh_favorite_button'):
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
                self.load_favorite_movies()

    def paginate_items(self, items_to_paginate, page):
        """Paginate a list of items."""
        total_items = len(items_to_paginate)
        if total_items == 0:
            return [], 1
        total_pages = max(1, (total_items + self.page_size - 1) // self.page_size)
        if page < 1:
            page = 1
        if page > total_pages:
            page = total_pages
        start = (page - 1) * self.page_size
        end = min(start + self.page_size, total_items)
        return items_to_paginate[start:end], total_pages

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
        # Clear previous grid items more thoroughly
        self.poster_labels.clear() # Clear the poster_labels dictionary as well
        while self.movie_grid_layout.count() > 0:
            item = self.movie_grid_layout.takeAt(0)
            if item:
                widget = item.widget()
                if widget:
                    widget.setParent(None)
                    widget.deleteLater()
        
        # Reset empty_state_label reference since it may have been deleted
        if hasattr(self, 'empty_state_label'):
            delattr(self, 'empty_state_label')
        
        page_items, self.total_pages = self.paginate_items(self.filtered_movies, self.current_page)
        # Show empty state label if no items
        if not page_items:
            self.empty_state_label = QLabel()
            self.empty_state_label.setAlignment(Qt.AlignCenter)
            self.empty_state_label.setStyleSheet("color: #888; font-size: 18px; padding: 40px;")
            self.empty_state_label.setWordWrap(True)
            self.empty_state_label.setText(self.translations.get("No movies to display", "No movies to display."))
            self.movie_grid_layout.addWidget(self.empty_state_label, 0, 0, 1, 4)
            if hasattr(self, 'order_panel'):
                self.order_panel.setVisible(False)
            self.update_pagination_controls()
            return
        else:
            if hasattr(self, 'empty_state_label'):
                self.empty_state_label.hide()
        self.display_movie_grid(page_items)
        self.update_pagination_controls()

    def movie_double_clicked(self, item):
        """Handle movie double-click"""
        if isinstance(item, MovieItem):
            movie_item = {
                'name': item.name,
                'stream_id': item.stream_id,
                'container_extension': item.container_extension,
                'stream_url': getattr(item, 'stream_url', ''),
                'stream_type': 'movie'
            }
        else:
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
                QMessageBox.warning(self, self.translations.get("Error", "Error"), self.translations.get("No movie selected", "No movie selected"))
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
    
    def add_to_favorites_clicked(self):
        """Add current movie to favorites"""
        if not self.current_movie:
            QMessageBox.warning(self, self.translations.get("Error", "Error"), self.translations.get("No movie is playing", "No movie is playing"))
            return
        
        movie = dict(self.current_movie)
        if 'name' not in movie:
            movie['name'] = movie.get('title', 'Movie')
        
        # Ensure stream_type is set
        if 'stream_type' not in movie:
            movie['stream_type'] = 'movie'
        
        # Use the main window's favorites manager directly if available
        if self.main_window and hasattr(self.main_window, 'favorites_manager'):
            self.main_window.favorites_manager.add_to_favorites(movie)
        else:
            # Fallback to signal emission
            self.add_to_favorites.emit(movie)

    @pyqtSlot(dict)
    def onPosterDownloadFailed(self, movie=None):
        if movie:
            # Handle both MovieItem and dictionary formats
            if isinstance(movie, MovieItem):
                stream_icon = movie.stream_icon or ''
                movie_name = movie.name or 'Unknown'
                movie_tmdb_id = movie.tmdb_id
                movie_stream_id = movie.stream_id
            else:
                stream_icon = movie.get('stream_icon', '')
                movie_name = movie.get('name', 'Unknown')
                movie_tmdb_id = movie.get('tmdb_id')
                movie_stream_id = movie.get('stream_id')
            
            if 'tmdb' in stream_icon:
                print(f"[MovieTab] Failed to download poster from TMDB {stream_icon}. Using default poster.")
                return
            else:
                #print(f"[MovieTab] Failed to download poster from Xtream server {stream_icon}. Using default poster.")
                pass
            tmdb_id = None
            if movie_tmdb_id:
                tmdb_id = movie_tmdb_id
            else:
                try:
                    success, vod_info = self.api_client.get_vod_info(movie_stream_id)
                    if 'movie_data' in vod_info and isinstance(vod_info['movie_data'], dict) and 'tmdb_id' in vod_info['movie_data']:
                        tmdb_id = vod_info['movie_data']['tmdb_id']
                    elif 'info' in vod_info and isinstance(vod_info['info'], dict) and 'tmdb_id' in vod_info['info']:
                        tmdb_id = vod_info['info']['tmdb_id']
                except Exception as e:
                    print(f"[MovieTab] Error getting VOD info for TMDB fallback: {e}")
            
            if tmdb_id:
                try:
                    details = self.tmdb_client.get_movie_details(tmdb_id)
                    # print(f"[MovieTab >>>] got details of movie with TMDB ID: {tmdb_id} and stream icon: {details.get('poster_path')}")
                    if details:
                        # Handle MovieDetails model or raw dict
                        poster_path = None
                        if hasattr(details, 'poster_path'):
                            poster_path = details.poster_path
                        else:
                            poster_path = details.get('poster_path')
                        tmdb_poster_url = self.tmdb_client.get_full_poster_url(poster_path)
                        if tmdb_poster_url:
                            orriginal_stream = str(movie_stream_id)
                            #print(f"[MovieTab] Failed to download poster from {stream_icon}. Using TMDB poster instead: {tmdb_poster_url}")
                            
                            # Update movie data with TMDB info
                            if isinstance(movie, MovieItem):
                                # For MovieItem, we need to update the cache with dictionary format
                                movie_dict = movie.to_dict()
                                movie_dict['tmdb_id'] = tmdb_id
                                movie_dict['stream_icon'] = tmdb_poster_url
                                self.api_client.update_movie_cache(movie_dict)
                                # Also update the MovieItem object
                                movie.tmdb_id = tmdb_id
                                movie.stream_icon = tmdb_poster_url
                            else:
                                movie['tmdb_id'] = tmdb_id
                                movie['stream_icon'] = tmdb_poster_url
                                self.api_client.update_movie_cache(movie)
                            
                            if orriginal_stream in self.poster_labels:
                                poster_label_widget = self.poster_labels[orriginal_stream]
                                poster_width = 125
                                poster_height = 188
                                default_pix = QPixmap('assets/movies.png')
                                # Add final fallback callback for TMDB failures
                                print(f"[MovieTab >>>] Updated movie {orriginal_stream} cache stream icon: {tmdb_poster_url}")
                                load_image_async(tmdb_poster_url, poster_label_widget, 
                                               default_pix.scaled(poster_width, poster_height, Qt.KeepAspectRatio, Qt.SmoothTransformation), 
                                               update_size=(poster_width, poster_height), 
                                               main_window=self.main_window)
                            return
                except Exception as e:
                    print(f"[MovieTab] Error getting TMDB details: {e}")
            