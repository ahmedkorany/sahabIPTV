"""
Search Tab: Centralized search for Live, Movies, and Series.
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,QSizePolicy, QPushButton, QGridLayout,
    QScrollArea, QLabel, QFrame, QButtonGroup, QMessageBox, QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QPixmap, QFont
from src.config import DARK_MODE
from src.utils.helpers import load_image_async
from src.ui.tabs.live_tab import DebouncedLineEdit
from src.utils.text_search import TextSearch

class SearchTab(QWidget):
    """Search tab widget for global search"""
    # Signal to indicate an item should be played (similar to other tabs)
    play_item_signal = pyqtSignal(dict) # item_data contains type, id, etc.
    add_to_favorites = pyqtSignal(dict)

    def __init__(self, api_client, main_window=None, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.main_window = main_window
        self.parent_widget = parent # Main window

        self.all_live_channels = []
        self.all_movies = []
        self.all_series = []

        self.search_results = []
        self.filtered_results = [] # Results after applying type filter

        self.current_filter = "All"  # All, Live, Movies, Series

        # Pagination
        self.current_page = 1
        self.page_size = 32  # Or a configurable value
        self.total_pages = 1

        # Search index (combined for all types)
        self._search_index = {}
        self._search_lc_items = [] # List of dicts: {'item': item_data, 'normalized_name': str, 'type': str}

        self.loading_data = False
        self.initial_data_loaded = False

        self.setup_ui()
        # self.load_all_data_async() # Start loading data in the background

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # 1. Search Input
        self.search_input = DebouncedLineEdit()
        self.search_input.setPlaceholderText("Search Live, Movies, and Series...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setFixedHeight(35) # Consistent height
        self.search_input._debounced_text_changed.connect(self.perform_search)
        layout.addWidget(self.search_input)

        # 2. Filter Tags
        filter_layout = QHBoxLayout()
        self.filter_button_group = QButtonGroup(self)
        self.filter_button_group.setExclusive(True)

        self.filter_buttons = {} 
        for filter_name_display in ["All", "Live TV", "Movies", "Series"]:
            btn = QPushButton(filter_name_display)
            btn.setCheckable(True)
            btn.setFixedHeight(30)
            filter_value = filter_name_display.replace(" TV", "")
            btn.clicked.connect(lambda checked, fv=filter_value: self.set_filter(fv))
            self.filter_button_group.addButton(btn)
            filter_layout.addWidget(btn)
            self.filter_buttons[filter_value] = btn

        if self.filter_buttons.get("All"):
            self.filter_buttons["All"].setChecked(True)
        
        self.filter_button_group.buttonClicked.connect(self.update_filter_button_styles)
        self.update_filter_button_styles() # Apply initial style

        filter_layout.addStretch(1)
        layout.addLayout(filter_layout)

        # 3. Results Grid
        self.results_grid_widget = QWidget()
        self.results_grid_layout = QGridLayout(self.results_grid_widget)
        self.results_grid_layout.setSpacing(16)
        self.results_grid_layout.setContentsMargins(8, 8, 8, 8)
        # self.results_grid_widget.setStyleSheet("background: transparent;")

        self.results_scroll_area = QScrollArea()
        self.results_scroll_area.setWidgetResizable(True)
        self.results_scroll_area.setWidget(self.results_grid_widget)
        self.results_scroll_area.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(self.results_scroll_area)

        # Empty State Label
        self.empty_state_label = QLabel("No results found.")
        self.empty_state_label.setAlignment(Qt.AlignCenter)
        font = QFont('Arial', 16)
        # font.setBold(True) # Optional: make it bold
        self.empty_state_label.setFont(font)
        self.empty_state_label.setStyleSheet("color: #888;") # Adjust color as needed
        self.empty_state_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.empty_state_label.setVisible(False) # Initially hidden

        # 4. Pagination Controls
        self.pagination_panel = QWidget()
        pagination_layout = QHBoxLayout(self.pagination_panel)
        pagination_layout.setContentsMargins(0, 5, 0, 0)
        pagination_layout.setAlignment(Qt.AlignCenter)

        self.prev_page_button = QPushButton("Previous")
        self.prev_page_button.clicked.connect(self.go_to_previous_page)
        self.page_label = QLabel("Page 1 of 1")
        self.next_page_button = QPushButton("Next")
        self.next_page_button.clicked.connect(self.go_to_next_page)

        pagination_layout.addWidget(self.prev_page_button)
        pagination_layout.addSpacing(10)
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addSpacing(10)
        pagination_layout.addWidget(self.next_page_button)
        self.pagination_panel.setVisible(False) # Initially hidden
        layout.addWidget(self.pagination_panel)

        self.setLayout(layout)

    def update_filter_button_styles(self, button_clicked=None):
        base_style = "QPushButton {{ border: 1px solid #555; padding: 5px; border-radius: 4px; background-color: {}; color: {}; }}"
        hover_style_selected_str = "QPushButton:hover {{ background-color: #0056b3; }}"
        hover_style_unselected_str = "QPushButton:hover {{ background-color: #5a5a5a; }}"

        default_bg = "#444" if DARK_MODE else "#ddd"
        default_fg = "white" if DARK_MODE else "black"
        selected_bg = "#007bff" 
        selected_fg = "white"

        for btn_in_group in self.filter_button_group.buttons():
            if btn_in_group.isChecked():
                btn_in_group.setStyleSheet(base_style.format(selected_bg, selected_fg) + hover_style_selected_str)
            else:
                btn_in_group.setStyleSheet(base_style.format(default_bg, default_fg) + hover_style_unselected_str)

    def load_all_data_async(self):
        """Placeholder: Load all data for live, movies, series asynchronously."""
        # This will be implemented with a QThread or similar for non-blocking loading
        # For now, simulate loading and then build index
        print("[SearchTab] Starting to load all data...")
        self.loading_data = True
        self.clear_grid()

        # In a real scenario, use QThreads to fetch this data
        # Example: self.live_worker = LiveFetchWorker(self.api_client)
        # self.live_worker.finished.connect(self.on_live_data_loaded)
        # self.live_worker.start()
        # ... similar for movies and series

        # Simulate data loading for now
        QTimer.singleShot(100, self._fetch_live_data) # Simulate async calls

    def _fetch_live_data(self):
        print("[SearchTab] Fetching live data...")
        # Placeholder: Fetch all live channels (e.g., by iterating categories or if an 'all' endpoint exists)
        # For now, assume we get a list of channel dicts
        # This should ideally use the same logic as LiveTab's "ALL" category loading
        temp_live_channels = []
        success_cat, live_categories = self.api_client.get_live_categories()
        if success_cat:
            for cat in live_categories:
                if cat.get('category_id'): # Ensure valid category_id
                    success_streams, streams = self.api_client.get_live_streams(cat['category_id'])
                    if success_streams:
                        temp_live_channels.extend(streams)
        self.all_live_channels = temp_live_channels
        print(f"[SearchTab] Loaded {len(self.all_live_channels)} live channels.")
        QTimer.singleShot(100, self._fetch_movies_data)

    def _fetch_movies_data(self):
        print("[SearchTab] Fetching movies data...")
        # Placeholder: Fetch all movies
        temp_movies = []
        success_cat, vod_categories = self.api_client.get_vod_categories()
        if success_cat:
            for cat in vod_categories:
                if cat.get('category_id'):
                    success_streams, streams = self.api_client.get_vod_streams(cat['category_id'])
                    if success_streams:
                        temp_movies.extend(streams)
        self.all_movies = temp_movies
        print(f"[SearchTab] Loaded {len(self.all_movies)} movies.")
        QTimer.singleShot(100, self._fetch_series_data)

    def _fetch_series_data(self):
        print("[SearchTab] Fetching series data...")
        # Placeholder: Fetch all series
        temp_series = []
        success_cat, series_categories = self.api_client.get_series_categories()
        if success_cat:
            for cat in series_categories:
                if cat.get('category_id'):
                    success_streams, streams = self.api_client.get_series(cat['category_id'])
                    if success_streams:
                        temp_series.extend(streams)
        self.all_series = temp_series
        print(f"[SearchTab] Loaded {len(self.all_series)} series.")
        self._finalize_data_loading()

    def _finalize_data_loading(self):
        self.build_search_index()
        self.loading_data = False
        self.initial_data_loaded = True

        self.perform_search(self.search_input.text()) # Perform initial search if any text
        print("[SearchTab] All data loaded and index built.")

    def build_search_index(self):
        """Builds a combined search index for all item types."""
        self._search_index = {}
        self._search_lc_items = []
        current_idx = 0

        # Process Live Channels
        for channel in self.all_live_channels:
            name = channel.get('name', '')
            normalized_name = TextSearch.normalize_text(name)
            self._search_lc_items.append({'item': channel, 'normalized_name': normalized_name, 'type': 'Live'})
            tokens = set(normalized_name.split())
            for token in tokens:
                if token:
                    if token not in self._search_index:
                        self._search_index[token] = set()
                    self._search_index[token].add(current_idx)
            current_idx += 1

        # Process Movies
        for movie in self.all_movies:
            name = movie.get('name', '')
            normalized_name = TextSearch.normalize_text(name)
            self._search_lc_items.append
            tokens = set(normalized_name.split())
            for token in tokens:
                if token:
                    if token not in self._search_index:
                        self._search_index[token] = set()
                    self._search_index[token].add(current_idx)
            current_idx += 1

        # Process Series
        for series_item in self.all_series:
            name = series_item.get('name', '')
            normalized_name = TextSearch.normalize_text(name)
            self._search_lc_items.append({'item': series_item, 'normalized_name': normalized_name, 'type': 'Series'})
            tokens = set(normalized_name.split())
            for token in tokens:
                if token:
                    if token not in self._search_index:
                        self._search_index[token] = set()
                    self._search_index[token].add(current_idx)
            current_idx += 1
        print(f"[SearchTab] Search index built with {len(self._search_lc_items)} items.")

    def perform_search(self, query_text):
        self.clear_grid() # Clears grid and hides empty/loading labels

        query = query_text.strip()

        if not self.initial_data_loaded:
            if not self.loading_data:
                self.load_all_data_async()
            return
        elif self.loading_data:
            return

        if not query:
            self.search_results = []
            self.apply_type_filter_and_paginate()
            self.update_pagination_controls()
            # Show empty state if query is empty and no results (e.g. after clearing search)
            if not self.filtered_results:
                self.empty_state_label.setText("Type to search for channels, movies, or series.")
                self.clear_grid()
                self.empty_state_label.setVisible(True)
                self._add_widget_to_grid_center(self.empty_state_label)
                self.pagination_panel.setVisible(False)
            else:
                self.empty_state_label.setVisible(False)
            return

        normalized_query = TextSearch.normalize_text(query)
        # Use the TextSearch instance for searching
        if hasattr(self, 'text_search_instance') and self.text_search_instance:
            self.search_results = self.text_search_instance.search(normalized_query)
        else:
            # Fallback or handle error if text_search_instance is not ready
            self.search_results = [item_info for item_info in self._search_lc_items
                                   if normalized_query in item_info['normalized_name']]

        self.apply_type_filter_and_paginate()
        self.update_pagination_controls()

        if not self.filtered_results and query:
            self.empty_state_label.setText(f"No results found for '{query}'.")
            self._add_widget_to_grid_center(self.empty_state_label)
            self.pagination_panel.setVisible(False)
        else:
            self.empty_state_label.setVisible(False)

    def apply_type_filter_and_paginate(self):
        """Applies the current filter to search_results and displays them."""
        if self.current_filter == "All":
            self.filtered_results = list(self.search_results)
        else:
            self.filtered_results = [res for res in self.search_results if res['type'] == self.current_filter]
        
        self.display_current_page_results()

    def display_current_page_results(self):
        """Clears grid and displays items for the current page and filter."""
        self.clear_grid()


        if not self.filtered_results:
            text_to_set = f"No results found for '{self.search_input.text()}'" if self.search_input.text() else "No items to display."
            if self.current_filter != "All":
                 text_to_set = f"No {self.current_filter.lower()} items found for '{self.search_input.text()}'" if self.search_input.text() else f"No {self.current_filter.lower()} items to display."
            self.pagination_panel.setVisible(False)
            return

        # If we reach here, filtered_results is not empty.

        total_items = len(self.filtered_results)
        self.total_pages = max(1, (total_items + self.page_size - 1) // self.page_size)
        
        start_index = (self.current_page - 1) * self.page_size
        end_index = start_index + self.page_size
        page_items = self.filtered_results[start_index:end_index]

        cols = 4 # Number of columns in the grid
        row, col = 0, 0

        for item_wrapper in page_items:
            item_data = item_wrapper['item']
            item_type = item_wrapper['type']
            
            tile = QFrame()
            tile.setFrameShape(QFrame.StyledPanel)
            tile.setCursor(Qt.PointingHandCursor)
            tile.setStyleSheet("background: #222; border-radius: 12px;")
            tile_layout = QVBoxLayout(tile)
            tile_layout.setContentsMargins(0, 0, 0, 0)
            tile_layout.setSpacing(0)

            # Image/Icon
            icon_label = QLabel()
            icon_label.setAlignment(Qt.AlignCenter)
            icon_label.setFixedSize(120, 70) # Adjust size as needed
            icon_label.setStyleSheet("background-color: #222; border-radius: 4px;")
            default_pix = self.get_default_pixmap(item_type)
            
            img_url = None
            if item_type == 'Live':
                img_url = item_data.get('stream_icon')
            elif item_type == 'Movie':
                img_url = item_data.get('stream_icon') # or a poster from TMDB if integrated
            elif item_type == 'Series':
                img_url = item_data.get('cover')

            if img_url:
                load_image_async(img_url, icon_label, default_pix, update_size=(120,70), main_window=self.main_window)
            else:
                icon_label.setPixmap(default_pix.scaled(120, 70, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            tile_layout.addWidget(icon_label)

            # Name
            name_label = QLabel(item_data.get('name', 'N/A'))
            name_label.setAlignment(Qt.AlignCenter)
            name_label.setWordWrap(True)
            name_label.setFont(QFont('Arial', 10, QFont.Bold))
            name_label.setStyleSheet("color: #FFF;")
            tile_layout.addWidget(name_label)

            # Type indicator
            type_label = QLabel(item_type)
            type_label.setAlignment(Qt.AlignCenter)
            type_label.setFont(QFont('Arial', 8))
            type_label.setStyleSheet("color: #AAA; background-color: #3A3A3A; border-radius: 3px; padding: 1px 3px;")
            tile_layout.addWidget(type_label)
            tile_layout.addStretch(1)

            tile.mousePressEvent = lambda e, data=item_data, type=item_type: self.item_clicked(data, type)
            
            self.results_grid_layout.addWidget(tile, row, col)
            col += 1
            if col >= cols:
                col = 0
                row += 1
        
        # Add stretchers to align items to the top-left if grid is not full
        for c in range(col, cols):
            self.results_grid_layout.setColumnStretch(c, 1)
        if row == 0 and col < cols: # Only one row not full
             self.results_grid_layout.setRowStretch(row + 1, 1)
        elif row > 0 : # multiple rows
            self.results_grid_layout.setRowStretch(row + 1, 1)

        self.update_pagination_controls()

    def get_default_pixmap(self, item_type):
        if item_type == 'Live':
            return QPixmap('assets/live.png')
        elif item_type == 'Movie':
            return QPixmap('assets/movie.png')
        elif item_type == 'Series':
            return QPixmap('assets/series.png')
        return QPixmap('assets/default_icon.png') # Fallback

    def item_clicked(self, item_data, item_type):
        """Handle item click - emit signal to play/show details."""
        print(f"[SearchTab] Item clicked: {item_data.get('name')}, Type: {item_type}")
        # Prepare data for playing, similar to other tabs
        playback_info = {'type': item_type.lower()}

        if item_type == 'Live':
            playback_info.update({
                'name': item_data.get('name'),
                'stream_id': item_data.get('stream_id'),
                'stream_url': self.api_client.get_live_stream_url(item_data.get('stream_id')),
                'stream_type': 'live' # Consistent with player expectations
            })
        elif item_type == 'Movie':
            playback_info.update({
                'name': item_data.get('name'),
                'stream_id': item_data.get('stream_id'),
                'stream_icon': item_data.get('stream_icon'),
                'stream_url': self.api_client.get_vod_stream_url(item_data.get('stream_id'), item_data.get('container_extension', 'mp4')),
                'stream_type': 'movie', # Consistent with player expectations
                'movie_data': item_data # For details view or player context
            })
        elif item_type == 'Series':
            # For series, clicking a search result should probably go to the series detail view
            # in the SeriesTab, or a dedicated series detail view if SearchTab handles it.
            # For now, let's assume main_window can handle this navigation.
            if self.main_window and hasattr(self.main_window, 'show_series_details_from_search'):
                self.main_window.show_series_details_from_search(item_data)
                return # Handled by main window
            else:
                QMessageBox.information(self, "Series", f"Series '{item_data.get('name')}' selected. Detail view not implemented directly in search yet.")
                return

        if 'stream_url' in playback_info and playback_info['stream_url']:
            if self.main_window and hasattr(self.main_window, 'player_window'):
                self.main_window.player_window.play(playback_info['stream_url'], playback_info)
                self.main_window.player_window.show()
                self.main_window.player_window.raise_()
                self.main_window.player_window.activateWindow()
            else:
                QMessageBox.warning(self, "Playback Error", "Player window not available.")
        else:
            QMessageBox.warning(self, "Playback Error", f"Could not get stream URL for {playback_info.get('name')}.")

    def clear_grid(self):
        for i in reversed(range(self.results_grid_layout.count())):
            item = self.results_grid_layout.itemAt(i)
            widget = item.widget() if item else None
        # Reset stretch factors
        for i in range(self.results_grid_layout.columnCount()):
            self.results_grid_layout.setColumnStretch(i, 0)
        for i in range(self.results_grid_layout.rowCount()):
            self.results_grid_layout.setRowStretch(i, 0)

    def _add_widget_to_grid_center(self, widget):
        """Show the given widget (usually empty_state_label) in the center of the grid."""
        self.clear_grid()
        widget.setVisible(True)
        self.results_grid_layout.addWidget(widget, 0, 0, 1, 4)

    def update_pagination_controls(self):
        """Update the pagination controls (buttons and label) based on current page and total pages."""
        if self.total_pages > 1:
            self.page_label.setText(f"Page {self.current_page} of {self.total_pages}")
            self.prev_page_button.setEnabled(self.current_page > 1)
            self.next_page_button.setEnabled(self.current_page < self.total_pages)
            self.pagination_panel.setVisible(True)
        else:
            self.pagination_panel.setVisible(False)

    def go_to_previous_page(self):
        """Navigate to the previous page of results."""
        if self.current_page > 1:
            self.current_page -= 1
            self.display_current_page_results()

    def go_to_next_page(self):
        """Navigate to the next page of results."""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.display_current_page_results()