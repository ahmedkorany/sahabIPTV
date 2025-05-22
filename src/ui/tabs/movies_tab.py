"""
Movies tab for the application
"""
import time
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QListWidget, QPushButton, QLabel, QLineEdit, QMessageBox,
    QStackedWidget, QListWidgetItem, QScrollArea, QGridLayout, QComboBox, QFrame, QFileDialog
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QFont
from src.ui.player import MediaPlayer
from src.ui.widgets.movie_details_widget import MovieDetailsWidget
from src.utils.helpers import load_image_async
from src.utils.text_search import TextSearch
from src.api.tmdb import TMDBClient
from src.ui.widgets.dialogs import MovieDetailsDialog
import re

class MoviesTab(QWidget):
    """Movies tab widget"""
    add_to_favorites = pyqtSignal(dict)
    
    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.main_window = parent
        self.details_widget = None
        self.movies = []
        self.all_movies = []  # Store all movies across categories
        self.filtered_movies = []  # Store filtered movies for search
        self.current_movie = None
        
        # Pagination
        self.current_page = 1
        self.total_pages = 1
        self.page_size = 32 # Consistent page size

        # Search index attributes
        self._movie_search_index = {}  # token -> set of indices
        self._movie_lc_names = []      # lowercased names for fallback
        
        # Initialize TMDB client once for all details widgets
        self.tmdb_client = TMDBClient()  # Loads keys from .env automatically

        self.setup_ui() # self.main_window is already set from parent

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
        self.order_combo.currentIndexChanged.connect(self._handle_sort_criteria_changed)
        self.sort_toggle = QPushButton("Desc")
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
        # self.page_size is now set in __init__
        # self.current_page = 1 # Already set in __init__
        # self.total_pages = 1 # Already set in __init__
        self.update_pagination_controls()

    def on_order_changed(self):
        self.apply_sort_and_refresh()

    def on_sort_toggle(self):
        if self.sort_toggle.isChecked():
            self.sort_toggle.setText("Desc")
        else:
            self.sort_toggle.setText("Asc")
        self.apply_sort_and_refresh()

    def _handle_sort_criteria_changed(self):
        self.apply_sort_and_refresh()

    def apply_sort_and_refresh(self):
        # Determine the list to sort.
        # self.filtered_movies should hold the current set of items (e.g., search results, or all items if no search).
        if hasattr(self, 'filtered_movies') and self.filtered_movies is not None:
            items_to_sort = list(self.filtered_movies)
        elif hasattr(self, 'movies') and self.movies:
            # Fallback: if filtered_movies isn't populated, use self.movies as the base.
            items_to_sort = list(self.movies)
        else:
            items_to_sort = []

        sort_field = self.order_combo.currentText()
        reverse = self.sort_toggle.isChecked()

        if sort_field == "Default":
            # For "Default" sort, re-apply the current search.
            # search_movies will populate self.filtered_movies with (unsorted) search results from self.movies
            # and then call display_current_page.
            current_search_text = self.search_input.text() if hasattr(self, 'search_input') else ""
            self.search_movies(current_search_text)
            return # search_movies handles the display update

        # If there are no items to sort (e.g., empty category and not "Default" sort),
        # ensure the display is empty and pagination is correct.
        if not items_to_sort:
            self.filtered_movies = []
            self.current_page = 1
            self.display_current_page() # This will show "no movies" message
            return

        # For other sort fields:
        key_func = None
        if sort_field == "Date":
            key_func = lambda x: x.get('_sort_date', 0)
        elif sort_field == "Name":
            key_func = lambda x: x.get('_sort_name', '')
        elif sort_field == "Rating":
            key_func = lambda x: x.get('_sort_rating', 0)
        
        if key_func:
            sorted_items = sorted(items_to_sort, key=key_func, reverse=reverse)
        else:
            # Should not happen if ComboBox is restricted to valid sort fields.
            # If it does, treat as no-sort on the current items_to_sort.
            sorted_items = items_to_sort 
        
        self.filtered_movies = sorted_items # Update self.filtered_movies with the sorted list
        # DO NOT update self.movies here, as it's the source for the search index.
        
        self.current_page = 1
        self.display_current_page() # display_current_page uses self.filtered_movies

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
        self.build_movie_search_index() # Depends on self.movies
        self.filtered_movies = list(self.movies) # Reset filtered list to all current movies
        self.display_current_page() # Will use self.filtered_movies

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
        self.build_movie_search_index()  # Build index after loading (depends on self.movies)
        self.filtered_movies = list(self.movies) # Reset filtered list
        # display_current_page will handle pagination and display
        # It should also update total_pages based on self.movies
        self.display_current_page() # Will use self.filtered_movies

    def build_movie_search_index(self):
        """Builds a token-based search index for fast lookup using normalized text."""
        self._movie_search_index = {}  # token -> set of movie indices
        self._movie_lc_names = []      # list of normalized names for fallback search

        if not hasattr(self, 'movies') or not self.movies:
            # If self.movies is empty, _movie_search_index and _movie_lc_names will remain as initialized (empty).
            # self.filtered_movies is handled by the calling functions (e.g., load_movies, search_movies).
            return

        for idx, movie_data in enumerate(self.movies):
            original_name = movie_data.get('name', '')
            normalized_name = TextSearch.normalize_text(original_name)

            movie_data['_normalized_name'] = normalized_name
            self._movie_lc_names.append(normalized_name)

            movie_data['_sort_name'] = normalized_name # Use normalized name for 'Name' sort
            try:
                movie_data['_sort_date'] = int(movie_data.get('added', 0))
            except (ValueError, TypeError):
                movie_data['_sort_date'] = 0
            try:
                movie_data['_sort_rating'] = float(movie_data.get('rating', 0))
            except (ValueError, TypeError):
                movie_data['_sort_rating'] = 0.0

            tokens = set(normalized_name.split()) 
            for token in tokens:
                if token:  # Avoid empty tokens
                    if token not in self._movie_search_index:
                        self._movie_search_index[token] = set()
                    self._movie_search_index[token].add(idx)

    def display_movie_grid(self, movies): # movies is page_items
        """Display movies as a grid of tiles"""
        # Grid is cleared in display_current_page before this method is called
        if not movies:
            message = "This category currently has no movies." # Default message
            if hasattr(self, 'search_input') and self.search_input.text().strip():
                message = "No movies found matching your search criteria."
            
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
            name_text = movie.get('name', 'Unnamed Movie')
            name = QLabel(name_text)
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
        """Filter movies based on search text using normalized query and movie names."""
        search_term = text.strip()

        if not hasattr(self, 'movies') or not self.movies:
            self.filtered_movies = []
            self.current_page = 1
            self.display_current_page()
            return

        # TextSearch.search handles empty search_term by returning all items
        # and internal normalization. It also handles the token and substring search.
        # The key_func extracts the original name for TextSearch to normalize and search against.
        # Note: The previous implementation had a more complex token-based search (AND logic) 
        # and a fallback substring search. The current TextSearch.search is simpler (substring match).
        # If the more complex logic is strictly needed, TextSearch.search would need to be enhanced
        # or this method would need to retain some custom logic around TextSearch.normalize_text.
        # For now, we use the simpler centralized search.
        
        # Option 1: Simple search using TextSearch.search (current implementation in TextSearch class)
        # self.filtered_movies = TextSearch.search(
        #     self.movies, 
        #     search_term, 
        #     lambda item: item.get('name', '') 
        # )

        # Option 2: Using the more complex token/substring logic from movies_tab.
        normalized_query = TextSearch.normalize_text(search_term)
        if not normalized_query:
            self.filtered_movies = list(self.movies) if hasattr(self, 'movies') and self.movies else []
        else:
            matched_indices = set()
            query_tokens = set(token for token in normalized_query.split(' ') if token)
            
            if query_tokens and hasattr(self, '_movie_search_index'):
                processed_first_token = False
                current_results_token_search = set()
                # Perform token-based intersection search (AND logic for tokens)
                for i, token in enumerate(query_tokens):
                    if token in self._movie_search_index:
                        if not processed_first_token:
                            current_results_token_search = self._movie_search_index[token].copy()
                            processed_first_token = True
                        else:
                            current_results_token_search.intersection_update(self._movie_search_index[token])
                    else:
                        # If any token is not found, the AND condition fails for token search
                        current_results_token_search.clear()
                        break # No need to check further tokens
                if processed_first_token: # if at least one token was processed and found
                    matched_indices.update(current_results_token_search)
            
            # Fallback or additional: Substring search on full normalized names 
            # (self._movie_lc_names are already normalized, populated by build_movie_search_index)
            # This part can find matches even if the token search didn't, or add to them.
            if hasattr(self, '_movie_lc_names'):
                for idx, normalized_movie_name in enumerate(self._movie_lc_names):
                    if normalized_query in normalized_movie_name:
                        matched_indices.add(idx)
            
            if hasattr(self, 'movies') and self.movies:
                self.filtered_movies = [self.movies[i] for i in sorted(list(matched_indices)) if i < len(self.movies)]
            else:
                self.filtered_movies = []

        self.current_page = 1
        self.display_current_page()

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
        while self.movie_grid_layout.count() > 0:
            item = self.movie_grid_layout.takeAt(0) # takeAt removes and returns item from layout
            if item:
                widget = item.widget()
                if widget:
                    widget.setParent(None) # Disassociate widget from parent
                    widget.deleteLater()   # Schedule widget for deletion
        
        page_items, self.total_pages = self.paginate_items(self.filtered_movies, self.current_page)
        self.display_movie_grid(page_items) # This will add new widgets to the now empty layout
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
    
    def add_to_favorites_clicked(self):
        """Add current movie to favorites"""
        if not self.current_movie:
            QMessageBox.warning(self, "Error", "No movie is playing")
            return
        movie = dict(self.current_movie)
        if 'name' not in movie:
            movie['name'] = movie.get('title', 'Movie')
        self.add_to_favorites.emit(movie)
