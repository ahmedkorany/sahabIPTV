"""
Search tab for the application
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QGridLayout, QScrollArea, QFrame, QPushButton, QComboBox)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QRect # Added QRect
from PyQt5.QtGui import QFont, QPixmap
from src.utils.text_search import search_all_data
from src.utils.image_cache import ImageCache
from src.utils.helpers import load_image_async, get_translations
# Import other necessary widgets or details views if items are clickable
# from src.ui.widgets.movie_details_widget import MovieDetailsWidget
# from src.ui.widgets.series_details_widget import SeriesDetailsWidget

class SearchTab(QWidget):
    # Signals for when an item is clicked, to show details in main window or a dialog
    movie_selected = pyqtSignal(dict)
    series_selected = pyqtSignal(dict)
    channel_selected = pyqtSignal(dict)

    def __init__(self, api_client, main_window=None, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.main_window = main_window
        self.search_results = []
        self.current_page = 1
        self.page_size = 32  # Max 32 items per page
        self.total_pages = 1
        self.current_filter = "All"
        self.image_cache = ImageCache() # Or get from main_window if it's shared
        # Get translations from main window
        self.translations = getattr(main_window, 'translations', {}) if main_window else {}

        # Timer for debouncing search input
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.perform_search)

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # --- Search Input and Filters ---
        search_panel = QWidget()
        search_layout = QHBoxLayout(search_panel)
        search_layout.setContentsMargins(0,0,0,0)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.translations.get("Search Live, Movies, and Series...", "Search Live, Movies, and Series..."))
        self.search_input.setFixedHeight(35)
        self.search_input.textChanged.connect(self.on_search_text_changed)
        search_layout.addWidget(self.search_input, 1) # Stretch input

        self.filter_combo = QComboBox()
        self.filter_combo.addItems([self.translations.get("All", "All"), self.translations.get("Live", "Live"), self.translations.get("Movies", "Movies"), self.translations.get("Series", "Series")])
        self.filter_combo.setFixedWidth(100)
        self.filter_combo.currentIndexChanged.connect(self.on_filter_changed)
        search_layout.addWidget(self.filter_combo)

        layout.addWidget(search_panel)

        # --- Search Results Grid ---
        self.results_grid_widget = QWidget()
        self.results_grid_layout = QGridLayout(self.results_grid_widget)
        self.results_grid_layout.setSpacing(15)
        self.results_grid_layout.setContentsMargins(5, 5, 5, 5)

        self.results_scroll_area = QScrollArea()
        self.results_scroll_area.setWidgetResizable(True)
        self.results_scroll_area.setWidget(self.results_grid_widget)
        self.results_scroll_area.setStyleSheet("background-color: transparent; border: none;")

        layout.addWidget(self.results_scroll_area, 1) # Stretch scroll area

        # --- Pagination Controls ---
        self.pagination_panel = QWidget()
        pagination_layout = QHBoxLayout(self.pagination_panel)
        pagination_layout.setContentsMargins(0, 5, 0, 0)
        pagination_layout.setAlignment(Qt.AlignCenter)

        self.prev_page_button = QPushButton(self.translations.get("Previous", "Previous"))
        self.prev_page_button.clicked.connect(self.go_to_previous_page)
        self.page_label = QLabel(self.translations.get("Page 1 of 1", "Page 1 of 1"))
        self.next_page_button = QPushButton(self.translations.get("Next", "Next"))
        self.next_page_button.clicked.connect(self.go_to_next_page)

        pagination_layout.addWidget(self.prev_page_button)
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addWidget(self.next_page_button)
        layout.addWidget(self.pagination_panel)

        self.setLayout(layout)
        self.update_grid_display() # Initial state

    def on_search_text_changed(self, text):
        # Debounce search: wait 500ms after user stops typing
        self.search_timer.start(500)

    def on_filter_changed(self, index):
        self.current_filter = self.filter_combo.currentText()
        self.current_page = 1 # Reset to first page on filter change
        # Re-filter and display current search_results or perform search if query exists
        self.perform_search(force_search=bool(self.search_input.text().strip()))


    def perform_search(self, force_search=False):
        query = self.search_input.text().strip()

        if not query and not force_search:
            self.search_results = []
            self.current_page = 1
            self.update_grid_display()
            return

        if len(query) < 3 and not force_search: # Only search if query is 3+ chars or forced (e.g. by filter change)
            if not query: # If query became empty and was not forced, clear results
                 self.search_results = []
                 self.current_page = 1
                 self.update_grid_display()
            # If query is <3 but not empty, do nothing yet, wait for more input
            return

        # Perform search using the search_all_data function
        print(f"Searching for: '{query}' with filter: '{self.current_filter}'")
        
        try:
            # Call the search function from text_search.py
            all_raw_results = search_all_data(self.api_client, query)
            
            # Filter results based on self.current_filter
            if self.current_filter == "All":
                self.search_results = all_raw_results
            else:
                filter_value = self.current_filter.lower()
                if filter_value == "movies": # Adjust for the 'Movies' filter selection
                    filter_value = "movie"
                self.search_results = []
                for item in all_raw_results:
                    # Handle both dictionary and object types
                    if hasattr(item, 'stream_type'):
                        item_type = getattr(item, 'stream_type', '').lower()
                    elif isinstance(item, dict):
                        item_type = item.get('stream_type', '').lower() or item.get('type', '').lower()
                    else:
                        item_type = ''
                    
                    if item_type == filter_value:
                        self.search_results.append(item)

        except Exception as e:
            print(f"Error during search: {e}")
            self.search_results = []


        self.current_page = 1
        self.update_grid_display()


    def update_grid_display(self):
        # Clear previous items
        for i in reversed(range(self.results_grid_layout.count())):
            widget = self.results_grid_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

        query = self.search_input.text().strip()

        if not query:
            self.show_message_in_grid("Search Live, Movies, and Series by typing in the text box ☝️")
            self.update_pagination_controls(0)
            return

        if len(query) > 0 and len(query) < 3: # Query entered but too short
            self.show_message_in_grid(f"Please enter at least 3 characters to search.")
            self.update_pagination_controls(0)
            return
            
        if not self.search_results and query: # Searched but no results
            self.show_message_in_grid(f"No results found for '{query}'")
            self.update_pagination_controls(0)
            return

        # Paginate results
        start_index = (self.current_page - 1) * self.page_size
        end_index = start_index + self.page_size
        page_items = self.search_results[start_index:end_index]

        if not page_items and self.current_page == 1 and query: # No items for the query after filtering
             self.show_message_in_grid(f"No results found for '{query}' with filter '{self.current_filter}'.")
             self.update_pagination_controls(len(self.search_results))
             return
        elif not page_items and self.current_page > 1: # Should not happen if pagination is correct
            self.show_message_in_grid("No more results on this page.")
            self.update_pagination_controls(len(self.search_results))
            return


        cols = 8 # Number of items per row (as per spec "Number of items per column is 8" - assuming this means row)
        row, col = 0, 0

        for item_index, item_data in enumerate(page_items):
            item_widget = self.create_item_widget(item_data)
            if item_widget:
                self.results_grid_layout.addWidget(item_widget, row, col)
                col += 1
                if col >= cols:
                    col = 0
                    row += 1
        
        # Add spacer to push items to the top-left if grid is not full
        if page_items:
             # Add row stretch if there are items, after the last row of items
            if col != 0: # If last row was not full, stretch starts from next row
                self.results_grid_layout.setRowStretch(row + 1, 1)
            else: # If last row was full, stretch starts from current row (which is now empty)
                 self.results_grid_layout.setRowStretch(row, 1)
            # Add column stretch after the last column of items
            self.results_grid_layout.setColumnStretch(cols, 1)


        self.update_pagination_controls(len(self.search_results))

    def show_message_in_grid(self, message):
        # Clear previous items first
        for i in reversed(range(self.results_grid_layout.count())):
            widget = self.results_grid_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

        message_label = QLabel(message)
        message_label.setAlignment(Qt.AlignCenter)
        message_label.setFont(QFont("Arial", 16))
        message_label.setStyleSheet("color: #888;")
        message_label.setWordWrap(True)
        self.results_grid_layout.addWidget(message_label, 0, 0, 1, self.results_grid_layout.columnCount() or 1)
        # Ensure the message label spans across a few columns if columnCount is 0 initially
        if self.results_grid_layout.columnCount() == 0:
            self.results_grid_layout.setColumnStretch(0,1)


    def create_item_widget(self, item_data):
        item_frame = QFrame()
        item_frame.setFrameShape(QFrame.StyledPanel) # Optional: for border/styling
        item_frame.setFixedWidth(120 + 10) # Poster width + padding
        item_frame.setFixedHeight(180 + 50) # Approx poster height + title + rating + padding
        item_layout = QVBoxLayout(item_frame)
        item_layout.setContentsMargins(5,5,5,5)
        item_layout.setSpacing(5)

        # --- Poster ---
        poster_width = 120
        # Preserve aspect ratio, assuming common poster aspect ratio (e.g., 2:3)
        # If original dimensions are known, use them. For now, let's estimate height.
        # Example: if typical poster is 500x750, then height = 120 * (750/500) = 120 * 1.5 = 180
        poster_height = int(poster_width * 1.5)

        poster_container = QWidget()
        poster_container.setFixedSize(poster_width, poster_height)
        
        poster_label = QLabel(poster_container)
        poster_label.setFixedSize(poster_width, poster_height)
        poster_label.setAlignment(Qt.AlignCenter)
        poster_label.setStyleSheet("background-color: #333; border-radius: 5px;") # Placeholder bg

        # Handle both object and dictionary types for getting values
        def get_value(item, key, default=''):
            if hasattr(item, key):
                return getattr(item, key, default)
            elif isinstance(item, dict):
                return item.get(key, default)
            return default
        
        # Prioritize TMDB poster if available for MovieItem instances
        cover_url = None
        if hasattr(item_data, 'tmdb_details') and item_data.tmdb_details:
            if hasattr(item_data.tmdb_details, 'poster_path') and item_data.tmdb_details.poster_path:
                cover_url = f"https://image.tmdb.org/t/p/w500{item_data.tmdb_details.poster_path}"
            elif isinstance(item_data.tmdb_details, dict) and item_data.tmdb_details.get('poster_path'):
                cover_url = f"https://image.tmdb.org/t/p/w500{item_data.tmdb_details['poster_path']}"
        
        # Fall back to existing cover sources if no TMDB poster
        if not cover_url:
            cover_url = get_value(item_data, 'cover') or get_value(item_data, 'stream_icon') or get_value(item_data, 'movie_image')
        
        # Determine item type and default icon
        item_type_str = get_value(item_data, 'stream_type', 'unknown').lower()
        if get_value(item_data, 'series_id'): 
            item_type_str = 'series'
        elif get_value(item_data, 'stream_id') and item_type_str in ['movie', 'unknown']: 
            item_type_str = 'movie' # Movies have stream_id
        elif 'live' in get_value(item_data, 'category_name', '').lower() or get_value(item_data, 'is_live'): 
            item_type_str = 'live'


        default_icon_path = f"assets/{item_type_str}.png" if item_type_str in ['live', 'movie', 'series'] else "assets/movies.png" # Fallback
        default_pixmap = QPixmap(default_icon_path)

        if cover_url:
            # Use main_window's image_cache if available and it's an instance of ImageCache
            # cache_to_use = self.main_window.image_cache if hasattr(self.main_window, 'image_cache') and isinstance(self.main_window.image_cache, ImageCache) else self.image_cache # Removed cache_to_use
            load_image_async(cover_url, poster_label, default_pixmap.scaled(poster_width, poster_height, Qt.KeepAspectRatio, Qt.SmoothTransformation),
                             update_size=(poster_width, poster_height), main_window=self.main_window) # Removed cache argument
        else:
            poster_label.setPixmap(default_pixmap.scaled(poster_width, poster_height, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        # --- Title Overlay ---
        title_text = get_value(item_data, 'name', 'Unknown Title')
        title_overlay = QLabel(title_text, poster_container)
        title_overlay.setFont(QFont("Arial", 14, QFont.Bold))
        title_overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0.7); color: white; padding: 3px; border-radius: 0px;")
        title_overlay.setAlignment(Qt.AlignCenter)
        title_overlay.setWordWrap(True)
        
        # Calculate title height (max 2 lines)
        font_metrics = title_overlay.fontMetrics()
        text_rect = font_metrics.boundingRect(QRect(0,0, poster_width - 6, poster_height), Qt.AlignLeft | Qt.TextWordWrap, title_text)
        title_height = min(text_rect.height() + 6, font_metrics.height() * 2 + 6) # Max 2 lines + padding
        title_overlay.setGeometry(0, poster_height - title_height, poster_width, title_height)
        title_overlay.raise_()

        # --- Type Icon (Top Left) ---
        type_icon_label = QLabel(poster_container)
        type_icon_path = f"assets/{item_type_str}.png" # live.png, movies.png, series.png
        type_pixmap = QPixmap(type_icon_path)
        if not type_pixmap.isNull():
            type_icon_label.setPixmap(type_pixmap.scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            type_icon_label.setStyleSheet("background-color: transparent;")
            type_icon_label.setGeometry(5, 5, 24, 24) # Position top-left with padding
            type_icon_label.raise_()

        item_layout.addWidget(poster_container)

        # --- Rating ---
        rating_val = get_value(item_data, 'rating', 0)
        if isinstance(rating_val, str):
            try:
                rating_val = float(rating_val)
            except ValueError:
                rating_val = 0
        
        # If no rating and TMDB details available, use TMDB rating
        if rating_val == 0 and hasattr(item_data, 'tmdb_details') and item_data.tmdb_details:
            if hasattr(item_data.tmdb_details, 'vote_average') and item_data.tmdb_details.vote_average > 0:
                rating_val = item_data.tmdb_details.vote_average
            elif isinstance(item_data.tmdb_details, dict) and item_data.tmdb_details.get('vote_average', 0) > 0:
                rating_val = item_data.tmdb_details['vote_average']
        
        rating_text = f"★ {rating_val:.1f}/10" if rating_val > 0 else "No rating"
        rating_label = QLabel(rating_text)
        rating_label.setAlignment(Qt.AlignCenter)
        rating_label.setFont(QFont("Arial", 10))
        rating_label.setStyleSheet("color: #ddd;")
        item_layout.addWidget(rating_label)

        item_frame.mousePressEvent = lambda event, data=item_data: self.on_item_clicked(data)
        return item_frame

    def on_item_clicked(self, item_data):
        # Helper function for getting values (redefine here since it's in a different method)
        def get_value(item, key, default=''):
            if hasattr(item, key):
                return getattr(item, key, default)
            elif isinstance(item, dict):
                return item.get(key, default)
            return default
            
        item_type = get_value(item_data, 'stream_type', '').lower()
        if get_value(item_data, 'series_id') or item_type == 'series':
            print(f"Series clicked: {get_value(item_data, 'name')}")
            # self.series_selected.emit(item_data) # TODO: Connect this signal in main_window
            if self.main_window and hasattr(self.main_window, 'show_series_details_from_search'):
                self.main_window.show_series_details_from_search(item_data)
            else:
                print("Main window does not have show_series_details_from_search method.")
        elif get_value(item_data, 'stream_id') and item_type == 'movie':
            print(f"Movie clicked: {get_value(item_data, 'name')}")
            # self.movie_selected.emit(item_data) # TODO: Connect this signal
            if self.main_window and hasattr(self.main_window, 'show_movie_details_from_search'):
                self.main_window.show_movie_details_from_search(item_data)
            else:
                print("Main window does not have show_movie_details_from_search method.")
        elif item_type == 'live':
            print(f"Live channel clicked: {get_value(item_data, 'name')}")
            # self.channel_selected.emit(item_data) # TODO: Connect this signal
            if self.main_window and hasattr(self.main_window, 'play_channel_from_search'):
                 self.main_window.play_channel_from_search(item_data)
            else:
                print("Main window does not have play_channel_from_search method.")
        else:
            print(f"Unknown item type clicked: {get_value(item_data, 'name')}")


    def update_pagination_controls(self, total_items):
        if total_items == 0:
            self.pagination_panel.setVisible(False)
            return

        self.total_pages = (total_items + self.page_size - 1) // self.page_size
        if self.total_pages <= 1:
            self.pagination_panel.setVisible(False)
        else:
            self.pagination_panel.setVisible(True)
            self.page_label.setText(f"Page {self.current_page} of {self.total_pages}")
            self.prev_page_button.setEnabled(self.current_page > 1)
            self.next_page_button.setEnabled(self.current_page < self.total_pages)

    def go_to_previous_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.update_grid_display()

    def go_to_next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.update_grid_display()

    def refresh_search(self):
        """Public method to trigger a search, e.g., when tab becomes visible."""
        # This can be called if data sources might have changed
        # For now, it just re-triggers the current query if any
        if self.search_input.text().strip():
            self.perform_search(force_search=True)
        else:
            self.search_results = []
            self.update_grid_display()
            
    def clear_search(self):
        """Clears the search input and results."""
        self.search_input.clear()
        self.search_results = []
        self.current_page = 1
        self.update_grid_display()
