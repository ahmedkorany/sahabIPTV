"""
Series Details Widget for the application
"""
import os
import time
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton, QMessageBox, QComboBox, QScrollArea, QGridLayout)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QPixmap, QFont
from src.api.tmdb import TMDBClient # Added import
from src.ui.widgets.cast_widget import CastWidget
from src.utils.helpers import get_translations
from src.models import SeriesItem

class SeriesDetailsWidget(QWidget):
    back_clicked = pyqtSignal()
    play_episode_requested = pyqtSignal(object)  # episode data
    toggle_favorite_series_requested = pyqtSignal(object) # series data
    # Signals for download/export actions, will need to be connected in SeriesTab
    # download_episode_requested = pyqtSignal(object) # episode data # Removed
    # download_season_requested = pyqtSignal(str) # season number # Removed
    export_season_requested = pyqtSignal(str) # season number

    def __init__(self, series_data, api_client, main_window, parent=None):
        super().__init__(parent)
        self.series_data = series_data
        self.api_client = api_client
        self.main_window = main_window # For accessing player, favorites status etc.
        self.current_episodes = []
        self.current_season = None
        self.series_info = {} # To store detailed series info including episodes
        self.tmdb_client = TMDBClient() # Initialize TMDBClient
        # Get translations from main window or default to English
        language = getattr(main_window, 'language', 'en') if main_window else 'en'
        self.translations = get_translations(language)

        self._setup_ui()
        self._set_initial_layout_direction()
        self._load_initial_data()
    
    def _set_initial_layout_direction(self):
        """Set initial layout direction - always LTR for SeriesDetailsWidget"""
        from PyQt5.QtCore import Qt
        
        # Always set LTR layout for SeriesDetailsWidget regardless of app language
        self.setLayoutDirection(Qt.LeftToRight)
        print(f"[SeriesDetailsWidget] Set LTR layout (override RTL app setting)")

    def _setup_ui(self):
        layout = QHBoxLayout(self)

        # --- Left: Poster, Back button, Favorite button, SEASONS DROPDOWN --- 
        left_layout = QVBoxLayout()
        
        self.back_btn = QPushButton(f"← {self.translations.get('Back', 'Back')}")
        self.back_btn.setFixedWidth(80)
        self.back_btn.clicked.connect(self.back_clicked.emit)
        left_layout.addWidget(self.back_btn, alignment=Qt.AlignLeft)

        self.poster_label = QLabel()
        self.poster_label.setAlignment(Qt.AlignTop)
        left_layout.addWidget(self.poster_label)

        # Seasons ComboBox and Label
        self.seasons_label = QLabel() # For "{x} seasons"
        self.seasons_label.setAlignment(Qt.AlignCenter)
        self.seasons_label.setVisible(False) # Initially hidden
        left_layout.addWidget(self.seasons_label)

        self.seasons_combo = QComboBox()
        self.seasons_combo.setFixedWidth(180) # Match poster width
        self.seasons_combo.setVisible(False) # Initially hidden until seasons are loaded
        # self.seasons_combo.currentIndexChanged.connect(self._on_season_selected) # Connect after populating
        left_layout.addWidget(self.seasons_combo)

        self.favorite_series_btn = QPushButton()
        self.favorite_series_btn.setFixedWidth(180) # Match poster width
        self.favorite_series_btn.clicked.connect(self._on_toggle_favorite_series)
        left_layout.addWidget(self.favorite_series_btn)
        
        self.export_season_btn = QPushButton(self.translations.get("Export Season URLs", "Export Season URLs"))
        self.export_season_btn.setVisible(False)
        self.export_season_btn.clicked.connect(self._on_export_season)
        left_layout.addWidget(self.export_season_btn)

        left_layout.addStretch() # Pushes buttons to the top
        layout.addLayout(left_layout)

        # --- Right: Metadata, episodes --- 
        right_layout = QVBoxLayout()
        self.title_label = QLabel()
        self.title_label.setFont(QFont('Arial', 16, QFont.Bold))
        right_layout.addWidget(self.title_label)

        self.meta_label = QLabel()
        right_layout.addWidget(self.meta_label)

        self.desc_text = QTextEdit()
        self.desc_text.setReadOnly(True)
        self.desc_text.setMaximumHeight(100) # Increased height
        right_layout.addWidget(self.desc_text)

        # --- Cast Section --- 
        cast_header = QLabel(self.translations.get("Cast", "Cast"))
        cast_header.setFont(QFont('Arial', 14, QFont.Bold))
        right_layout.addWidget(cast_header)

        self.cast_scroll_area = QScrollArea()
        self.cast_scroll_area.setWidgetResizable(True)
        self.cast_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.cast_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # Set cast widget height to 1.25 times poster height (260 * 1.25 = 325)
        self.cast_scroll_area.setMinimumHeight(325)
        self.cast_scroll_area.setMaximumHeight(325)

        self.cast_widget = CastWidget(main_window=self.main_window)
        self.cast_scroll_area.setWidget(self.cast_widget)
        
        # Ensure visibility
        self.cast_scroll_area.setVisible(True)
        self.cast_widget.setVisible(True)
        
        right_layout.addWidget(self.cast_scroll_area)
        print(f"[SeriesDetailsWidget] Cast widget and scroll area added to layout")
        print(f"[SeriesDetailsWidget] Cast scroll area visible: {self.cast_scroll_area.isVisible()}")
        print(f"[SeriesDetailsWidget] Cast widget visible: {self.cast_widget.isVisible()}")
        # --- End Cast Section ---

        # Episodes section with two-column layout
        episodes_header = QLabel(self.translations.get("Episodes", "Episodes"))
        episodes_header.setFont(QFont('Arial', 14, QFont.Bold))
        right_layout.addWidget(episodes_header)
        
        # Create scroll area for episodes with increased height
        self.episodes_scroll_area = QScrollArea()
        self.episodes_scroll_area.setWidgetResizable(True)
        self.episodes_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.episodes_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.episodes_scroll_area.setMinimumHeight(250)  # Reduced height to show play button
        
        # Create episodes widget with grid layout for two columns
        self.episodes_widget = QWidget()
        self.episodes_grid_layout = QGridLayout(self.episodes_widget)
        self.episodes_grid_layout.setAlignment(Qt.AlignTop)
        self.episodes_grid_layout.setSpacing(5)
        
        self.episodes_scroll_area.setWidget(self.episodes_widget)
        right_layout.addWidget(self.episodes_scroll_area)
        
        # Keep track of episode buttons for interaction
        self.episode_buttons = []
        self.selected_episode_button = None

        # Action buttons for episodes
        episode_actions_layout = QHBoxLayout()
        self.play_episode_btn = QPushButton(self.translations.get("Play", "Play"))
        self.play_episode_btn.setEnabled(False)
        self.play_episode_btn.setVisible(False)
        self.play_episode_btn.clicked.connect(self._on_play_selected_episode)
        episode_actions_layout.addWidget(self.play_episode_btn)

        # self.download_episode_btn = QPushButton("Download Episode") # Removed
        # self.download_episode_btn.setEnabled(False) # Removed
        # self.download_episode_btn.setVisible(False) # Removed
        # self.download_episode_btn.clicked.connect(self._on_download_episode) # Removed
        # episode_actions_layout.addWidget(self.download_episode_btn) # Removed
        right_layout.addLayout(episode_actions_layout)

        self.trailer_btn = QPushButton(self.translations.get("WATCH TRAILER", "WATCH TRAILER"))
        self.trailer_btn.setVisible(False) # Initially hidden
        self.trailer_btn.clicked.connect(self._on_play_trailer)
        right_layout.addWidget(self.trailer_btn)

        layout.addLayout(right_layout)
        self.setLayout(layout)

    def _load_initial_data(self):
        # Handle both SeriesItem objects and dict objects
        if isinstance(self.series_data, SeriesItem):
            series_id = self.series_data.series_id
            series_name = self.series_data.name
            series_year = self.series_data.get_release_year()
            series_genre = self.series_data.genre
            series_plot = self.series_data.plot
            series_cover_url = self.series_data.cover
        else:
            series_id = self.series_data.get('series_id')
            series_name = self.series_data.get('name', '')
            series_year = self.series_data.get('year', '--')
            series_genre = self.series_data.get('genre', '--')
            series_plot = self.series_data.get('plot', '')
            series_cover_url = self.series_data.get('cover')
        
        self.title_label.setText(series_name)
        self.meta_label.setText(f"Year: {series_year} | Genre: {series_genre}")
        self.desc_text.setPlainText(series_plot)

        
        if series_cover_url:
            from src.utils.helpers import load_image_async
            self.poster_label.setPixmap(QPixmap('assets/series.png'))
            load_image_async(series_cover_url, self.poster_label, QPixmap('assets/series.png'), update_size=(200, 300), main_window=self.main_window, on_failure=self.onPosterLoadFailed)
        
        
        self._update_favorite_series_button_text()

        # Always attempt to get TMDB ID for credits, even if poster loaded successfully
        final_tmdb_id = getattr(self.series_data, 'tmdb_id', None) if isinstance(self.series_data, SeriesItem) else self.series_data.get('tmdb_id')
        if not final_tmdb_id:
            print(f"[SeriesDetailsWidget] No TMDB ID in series data, searching TMDB for credits")
            # Search TMDB for this series to get an ID for credits
            # series_name and series_year already extracted above
            if series_name:
                try:
                    results = self.tmdb_client.search_series(series_name, year=self.series_data.get_release_year())
                    # Handle search results (always returns raw dict)
                    if results and results.get('results'):
                        first_result = results['results'][0]
                        final_tmdb_id = first_result.get('id')
                        if final_tmdb_id:
                            print(f"[SeriesDetailsWidget] Found TMDB ID from search: {final_tmdb_id}")
                            # Only update dict objects, not SeriesItem objects
                            if not isinstance(self.series_data, SeriesItem):
                                self.series_data['tmdb_id'] = final_tmdb_id
                except Exception as e:
                    print(f"[SeriesDetailsWidget] Error searching TMDB for '{series_name}': {e}")
        
        if final_tmdb_id:
            print(f"[SeriesDetailsWidget] Fetching credits with TMDB ID: {final_tmdb_id}")
            self._fetch_tmdb_credits(final_tmdb_id)
        else:
            print(f"[SeriesDetailsWidget] No TMDB ID available for credits fetching")

        # Fetch detailed series info for trailer, seasons, and potentially more accurate metadata
        if series_id:
            try:
                success, series_info_full = self.api_client.get_series_info(series_id)
                if success and series_info_full:
                    self.series_info = series_info_full # Store for season/episode loading
                    info_dict = series_info_full.get('info', {})
                    
                    # Update metadata from detailed info if available
                    # Update metadata from detailed info if available, but preserve TMDB data if it exists
                    if isinstance(self.series_data, SeriesItem):
                        year_to_display = self.series_data.get_release_year() or info_dict.get('releaseDate', '--')
                        genre_to_display = self.series_data.genre or info_dict.get('genre', '--')
                        plot_to_display = self.series_data.plot or info_dict.get('plot', '')
                    else:
                        year_to_display = self.series_data.get('year', info_dict.get('releaseDate', '--'))
                        genre_to_display = self.series_data.get('genre', info_dict.get('genre', '--'))
                        plot_to_display = self.series_data.get('plot', info_dict.get('plot', ''))
                    
                    self.meta_label.setText(f"Year: {year_to_display} | Genre: {genre_to_display}")
                    
                    # Update description, but preserve TMDB plot data if it exists
                    self.desc_text.setPlainText(plot_to_display)
                    
                    # Update poster if a better one is in detailed info
                    if 'cover' in info_dict and info_dict['cover']:
                        detailed_cover_data = self.api_client.get_image_data(info_dict['cover'])
                        if detailed_cover_data:
                            detailed_pix = QPixmap()
                            detailed_pix.loadFromData(detailed_cover_data)
                            if not detailed_pix.isNull():
                                self.poster_label.setPixmap(detailed_pix.scaled(180, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation))

                    trailer_url = info_dict.get('youtube_trailer') or info_dict.get('trailer_url') # Prioritize youtube_trailer
                    if trailer_url and trailer_url.strip():  # Check for non-empty and non-whitespace
                        # Check if it's a full URL or just a YouTube video ID
                        if not trailer_url.startswith('http'):
                            # Assume it's a YouTube video ID and construct the full URL
                            trailer_url = f"https://www.youtube.com/watch?v={trailer_url}"
                        self.trailer_url = trailer_url # Store for the button
                        self.trailer_btn.setVisible(True)
                    else:
                        self.trailer_btn.setVisible(False)

                    # Load seasons using the fetched series_info
                    self._load_seasons_from_info()
                    
                    # Fetch TMDB credits if tmdb_id is available
                    tmdb_id = getattr(self.series_data, 'tmdb_id', None) if isinstance(self.series_data, SeriesItem) else self.series_data.get('tmdb_id')
                    if tmdb_id:
                        self._fetch_tmdb_credits(tmdb_id)
                else:
                    QMessageBox.warning(self, "Error", f"Failed to load detailed series information: {series_info_full}")
                    self._load_seasons_from_info() # Attempt to load seasons even if full info fails, if series_info has episodes

            except Exception as e:
                print(f"Error fetching detailed series metadata: {e}")
                QMessageBox.warning(self, "Error", f"Error fetching detailed series metadata: {str(e)}")
                self._load_seasons_from_info() # Fallback
        else:
             QMessageBox.warning(self, "Error", "Series ID is missing, cannot load details.")
    
    def Load_cover_from_TMDB(self, series_name, series_year, series_cover_url=None):
        """Load cover image from TMDB and update series data.
        
        Args:
            series_name (str): Name of the series
            series_year (str): Year of the series
            series_cover_url (str, optional): Original cover URL that failed to load
            
        Returns:
            QPixmap or None: The loaded pixmap if successful, None otherwise
        """
        if not series_cover_url:
            print(f"Initial cover URL missing for {series_name}. Attempting TMDB fallback.")
        else:
            # This case means a cover URL was present but failed to load. 
            # Depending on desired behavior, one might choose *not* to fallback immediately
            # or to have a more nuanced check. For now, we proceed with TMDB fallback as per original intent if load failed.
            print(f"Initial poster load failed for {series_name}. Attempting TMDB fallback.")

        tmdb_poster_url = None
        tmdb_id = getattr(self.series_data, 'tmdb_id', None) if isinstance(self.series_data, SeriesItem) else self.series_data.get('tmdb_id')
        new_tmdb_id_found = None

        if tmdb_id:
            try:
                details = self.tmdb_client.get_series_details(tmdb_id)
                if details:
                    # Handle SeriesDetails model or raw dict
                    poster_path = None
                    if hasattr(details, 'poster_path'):
                        poster_path = details.poster_path
                    else:
                        poster_path = details.get('poster_path')
                    
                    if poster_path:
                        tmdb_poster_url = self.tmdb_client.get_full_poster_url(poster_path)
            except Exception as e:
                print(f"Error fetching series details from TMDB by ID {tmdb_id}: {e}")
        
        if not tmdb_poster_url:
            # series_name and series_year already extracted above
            search_year = series_year if series_year != '--' else None
            try:
                results = self.tmdb_client.search_series(series_name, year=search_year)
                # Handle search results (always returns raw dict)
                if results and results.get('results'):
                    first_result = results['results'][0]
                    if first_result.get('poster_path'):
                        tmdb_poster_url = self.tmdb_client.get_full_poster_url(first_result['poster_path'])
                        new_tmdb_id_found = first_result.get('id')
            except Exception as e:
                print(f"Error searching series '{series_name}' on TMDB: {e}")

        if tmdb_poster_url:
            print(f"Found TMDB poster: {tmdb_poster_url}")
            tmdb_image_data = self.api_client.get_image_data(tmdb_poster_url)
            if tmdb_image_data:
                # Create a new QPixmap for TMDB image to avoid issues if original pix was somehow corrupted
                tmdb_pix = QPixmap()
                tmdb_pix.loadFromData(tmdb_image_data)
                if not tmdb_pix.isNull():
                    # Update series_data and cache
                    self.series_data['cover'] = tmdb_poster_url
                    if new_tmdb_id_found:
                         self.series_data['tmdb_id'] = new_tmdb_id_found
                         print(f"[SeriesDetailsWidget] Found new TMDB ID: {new_tmdb_id_found}, fetching credits")
                         # Fetch TMDB credits with the new ID
                         self._fetch_tmdb_credits(new_tmdb_id_found)
                    elif tmdb_id: # Ensure existing tmdb_id is preserved if used
                        self.series_data['tmdb_id'] = tmdb_id
                        print(f"[SeriesDetailsWidget] Using existing TMDB ID: {tmdb_id}, fetching credits")
                        # Fetch TMDB credits with the existing ID
                        self._fetch_tmdb_credits(tmdb_id)
                    
                    if hasattr(self.api_client, 'update_series_cache'):
                        if isinstance(self.series_data, SeriesItem):
                            # Convert SeriesItem to dictionary for caching
                            series_data_to_cache = {
                                'series_id': self.series_data.series_id,
                                'name': self.series_data.name,
                                'cover': self.series_data.cover,
                                'plot': self.series_data.plot,
                                'genre': self.series_data.genre,
                                'year': self.series_data.get_release_year(),
                                'tmdb_id': getattr(self.series_data, 'tmdb_id', None)
                            }
                        else:
                            series_data_to_cache = self.series_data.copy()
                        
                        if 'category_id' not in series_data_to_cache and hasattr(self, 'main_window') and hasattr(self.main_window, 'current_category_id_for_details'):
                            series_data_to_cache['category_id'] = self.main_window.current_category_id_for_details

                        self.api_client.update_series_cache(series_data_to_cache)
                        series_name = self.series_data.name if isinstance(self.series_data, SeriesItem) else self.series_data.get('name')
                        print(f"Updated cache for {series_name} with new TMDB poster.")
                    else:
                        print("api_client does not have update_series_cache method.")
                    
                    return tmdb_pix
        
        return None

    @pyqtSlot(bool)
    def onPosterLoadFailed(self, is_network_error=False):
        if is_network_error:
            print("[MovieDetailsWidget] Poster load failed due to network error. Not re-attempting TMDB fetch.")
            self.poseter_load_failed = True
        else:
            tmdb_result = self.Load_cover_from_TMDB(self.series_data.series_name, self.series_data.series_year, self.series_data.series_cover_url)
            if tmdb_result:
                pix = tmdb_result
                poster_loaded_successfully = True
            
        if not poster_loaded_successfully:
            # Fallback to local placeholder if all attempts fail
            print(f"All poster loading attempts failed for {self.series_data.series_name}. Using default placeholder.")
            pix = QPixmap('assets/series.png') 
        
        if not pix.isNull():
            self.poster_label.setPixmap(pix.scaled(180, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    def _load_seasons_from_info(self):
        self.seasons_combo.clear()
        self._clear_episodes()
        self.seasons_label.setVisible(False)
        self.seasons_combo.setVisible(False)

        if 'episodes' in self.series_info and self.series_info['episodes']:
            try:
                sorted_season_numbers = sorted(self.series_info['episodes'].keys(), key=int)
            except ValueError:
                sorted_season_numbers = sorted(self.series_info['episodes'].keys())

            if not sorted_season_numbers:
                return

            # Disconnect signal before populating to avoid premature triggers
            try:
                self.seasons_combo.currentIndexChanged.disconnect(self._on_season_selected)
            except TypeError: # Signal not connected yet
                pass

            for season_number_str in sorted_season_numbers:
                self.seasons_combo.addItem(f"Season {season_number_str}", userData=season_number_str)
            
            self.seasons_combo.setVisible(True)
            if len(sorted_season_numbers) > 1:
                self.seasons_label.setText(f"{len(sorted_season_numbers)} seasons")
                self.seasons_label.setVisible(True)
            else:
                self.seasons_label.setVisible(False)

            # Connect signal after populating
            self.seasons_combo.currentIndexChanged.connect(self._on_season_selected)
            
            if self.seasons_combo.count() > 0:
                self.seasons_combo.setCurrentIndex(0) # Select first season by default
                self._on_season_selected(0) # Trigger episode load for the first season
        else:
            # Optionally, display a message if no seasons/episodes are found
            # self.seasons_label.setText("No seasons available")
            # self.seasons_label.setVisible(True)
            self.export_season_btn.setVisible(False)

    def _on_season_selected(self, index):
        if index < 0: # No item selected or combo is empty
            self._clear_episodes()
            self.export_season_btn.setVisible(False)
            self._update_play_and_download_buttons_state()
            return

        season_number_str = self.seasons_combo.itemData(index)
        
        if hasattr(self, 'series_info') and 'episodes' in self.series_info and season_number_str in self.series_info['episodes']:
            self.export_season_btn.setVisible(True)
            episodes_data = self.series_info['episodes'][season_number_str]
            self._clear_episodes()
            self.current_episodes = episodes_data
            self.current_season = season_number_str
            
            try:
                sorted_episodes = sorted(episodes_data, key=lambda x: int(x.get('episode_num', 0)))
            except ValueError:
                sorted_episodes = episodes_data # Fallback if episode_num is not int

            self._populate_episodes_grid(sorted_episodes)
        else:
            self._clear_episodes()
            self.export_season_btn.setVisible(False)

        self._update_play_and_download_buttons_state() # Update button states after loading episodes

    # Remove old _on_season_clicked method if it exists, or ensure it's not used
    # def _on_season_clicked(self, item): ... (This method is now replaced by _on_season_selected)

    def _clear_episodes(self):
        """Clear all episode buttons from the grid layout."""
        for button in self.episode_buttons:
            button.setParent(None)
            button.deleteLater()
        self.episode_buttons.clear()
        self.selected_episode_button = None
        
        # Clear the grid layout
        while self.episodes_grid_layout.count():
            child = self.episodes_grid_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
    def _populate_episodes_grid(self, episodes):
        """Populate episodes in a two-column grid layout."""
        for i, episode in enumerate(episodes):
            episode_title = episode.get('title', 'Unnamed Episode')
            episode_text = f"E{episode.get('episode_num', '?')} - {episode_title}"
            
            episode_button = QPushButton(episode_text)
            episode_button.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 8px;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    background-color: transparent;
                    color: white;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.1);
                }
                QPushButton:pressed {
                    background-color: rgba(255, 255, 255, 0.2);
                }
                QPushButton[selected="true"] {
                    background-color: #007acc;
                    color: white;
                }
            """)
            episode_button.setProperty('episode_data', episode)
            episode_button.clicked.connect(lambda checked, btn=episode_button: self._on_episode_button_clicked(btn))
            
            # Add double-click functionality
            def make_double_click_handler(btn):
                def handler(event):
                    if event.type() == event.MouseButtonDblClick:
                        self._on_episode_double_clicked(btn)
                return handler
            
            episode_button.mouseDoubleClickEvent = make_double_click_handler(episode_button)
            
            # Add to grid: row = i // 2, column = i % 2
            row = i // 2
            col = i % 2
            self.episodes_grid_layout.addWidget(episode_button, row, col)
            self.episode_buttons.append(episode_button)
    
    def _on_episode_button_clicked(self, button):
        """Handle episode button click for selection."""
        # Deselect previous button
        if self.selected_episode_button:
            self.selected_episode_button.setProperty('selected', 'false')
            self.selected_episode_button.setStyle(self.selected_episode_button.style())
        
        # Select new button
        self.selected_episode_button = button
        button.setProperty('selected', 'true')
        button.setStyle(button.style())
        
        self._update_play_and_download_buttons_state()
    
    def _update_play_and_download_buttons_state(self):
        is_episode_selected = self.selected_episode_button is not None
        self.play_episode_btn.setEnabled(is_episode_selected)
        # self.download_episode_btn.setEnabled(is_episode_selected) # Removed
        self.play_episode_btn.setVisible(is_episode_selected)
        # self.download_episode_btn.setVisible(is_episode_selected) # Removed

    def _on_episode_double_clicked(self, button):
        """Handle double-click on episode button to play immediately."""
        self._play_episode_from_button(button)

    def _on_play_selected_episode(self):
        """Play the currently selected episode."""
        if self.selected_episode_button:
            self._play_episode_from_button(self.selected_episode_button)

    def _play_episode_from_button(self, button):
        """Play episode from button data."""
        episode_data = button.property('episode_data')
        if episode_data:
            self.play_episode_requested.emit(episode_data)
        else:
            QMessageBox.warning(self, "Error", "Episode data not found.")

    def _on_toggle_favorite_series(self):
        self.toggle_favorite_series_requested.emit(self.series_data)
        # The button text/icon update should be handled by the main window
        # or by re-checking favorite status after the signal is processed.
        # For immediate feedback, we can call _update_favorite_series_button_text here,
        # but it's better if the source of truth (main_window) drives this.
        # self._update_favorite_series_button_text() # Re-query status

    def _update_favorite_series_button_text(self):
        # This method now relies on main_window to check favorite status
        if not self.main_window or not hasattr(self.main_window, 'favorites_manager'):
            self.favorite_series_btn.setText(self.translations.get("Favorite N/A", "Favorite N/A"))
            return

        # Handle both SeriesItem objects and dict objects
        series_id = self.series_data.series_id if isinstance(self.series_data, SeriesItem) else self.series_data.get('series_id')
        
        favorite_item_check = {
            'series_id': series_id,
            'stream_type': 'series'
        }

        if self.main_window.favorites_manager.is_favorite(favorite_item_check):
            self.favorite_series_btn.setText("★") # Or use an icon
            self.favorite_series_btn.setStyleSheet("QPushButton { color: gold; background: transparent; font-size: 16px; }")
            self.favorite_series_btn.setToolTip(self.translations.get("Remove from favorites", "Remove from favorites"))
        else:
            self.favorite_series_btn.setText("☆") # Or use an icon
            self.favorite_series_btn.setStyleSheet("QPushButton { color: white; background: transparent; font-size: 16px; }")
            self.favorite_series_btn.setToolTip(self.translations.get("Add to favorites", "Add to favorites"))

    def _on_play_trailer(self):
        if hasattr(self, 'trailer_url') and self.trailer_url:
            if self.main_window and hasattr(self.main_window, 'player_window'):
                # The player_window.play method expects a dictionary for the second argument
                # For trailers, it's simpler, but good to maintain consistency if possible
                trailer_info = {'name': f"{self.series_data.get('name', 'Series')} Trailer", 'stream_type': 'trailer'}
                self.main_window.player_window.play(self.trailer_url, trailer_info)
                self.main_window.player_window.show()
            else:
                QMessageBox.warning(self, "Error", "Player window not available.")
        else:
            QMessageBox.information(self, "Trailer", "No trailer URL available for this series.")

    def _on_download_episode(self):
        # This method is no longer needed as download functionality is removed.
        # QMessageBox.information(self, "Info", "Download functionality is currently disabled.")
        pass

    def _on_download_season(self):
        # This method is no longer needed as download functionality is removed.
        # QMessageBox.information(self, "Info", "Download functionality is currently disabled.")
        pass

    def _on_export_season(self):
        if self.seasons_combo.currentIndex() < 0:
            QMessageBox.warning(self, "Error", "No season selected to export.")
            return
        season_number = self.seasons_combo.itemData(self.seasons_combo.currentIndex())
        self.export_season_requested.emit(season_number)

    # Public method to be called by SeriesTab after favorite status changes
    def refresh_favorite_button(self):
        self._update_favorite_series_button_text()

    # Placeholder for current_detailed_series if SeriesTab needs it
    # This widget itself is the detail view, so series_data is its primary data
    def get_current_detailed_series(self):
        return self.series_data

    # Placeholder for series_info if SeriesTab needs it
    def get_series_info(self):
        return self.series_info

    # Placeholder for current_episodes if SeriesTab needs it
    def get_current_episodes(self):
        return self.current_episodes

    # Placeholder for current_season if SeriesTab needs it
    def get_current_season(self):
        return self.current_season

    def _fetch_tmdb_credits(self, tmdb_id):
        """Fetch TMDB credits for the series and populate the cast widget asynchronously.
        Also fetch missing metadata (year, genre) and update the series cache."""
        if not self.tmdb_client:
            print("[SeriesDetailsWidget] TMDB client is missing, cannot fetch credits.")
            return
        print(f"[SeriesDetailsWidget] Starting async TMDB credits fetch for TMDB ID: {tmdb_id}")
        
        # Check if we need to fetch additional metadata
        needs_metadata_update = False
        # Handle both SeriesItem objects and dict objects
        current_year = self.series_data.get_release_year() if isinstance(self.series_data, SeriesItem) else self.series_data.get('year')
        current_genre = self.series_data.genre if isinstance(self.series_data, SeriesItem) else self.series_data.get('genre')
        
        # Check if year or genre is missing or empty
        if not current_year or current_year == '--' or not current_genre or current_genre == '--':
            needs_metadata_update = True
            print(f"[SeriesDetailsWidget] Missing metadata detected. Year: '{current_year}', Genre: '{current_genre}'")
        
        # Fetch series details if we need additional metadata
        if needs_metadata_update:
            try:
                # Try to detect series language for localized content
                series_language = None
                
                # Check for language indicators in series data
                series_name = self.series_data.get('name', '')
                series_name_lower = series_name.lower()
                
                # Enhanced language detection
                # Check for Arabic characters (Unicode range for Arabic)
                import re
                arabic_pattern = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]')
                if arabic_pattern.search(series_name):
                    series_language = 'ar'  # Arabic
                    print(f"[SeriesDetailsWidget] Detected Arabic characters in series name: {series_name}")
                # Check for specific Arabic keywords
                elif any(keyword in series_name_lower for keyword in ['arabic', 'عربي', 'عرب']):
                    series_language = 'ar'  # Arabic
                elif any(keyword in series_name_lower for keyword in ['french', 'français', 'francais']):
                    series_language = 'fr'  # French
                elif any(keyword in series_name_lower for keyword in ['spanish', 'español', 'espanol']):
                    series_language = 'es'  # Spanish
                elif any(keyword in series_name_lower for keyword in ['german', 'deutsch']):
                    series_language = 'de'  # German
                elif any(keyword in series_name_lower for keyword in ['italian', 'italiano']):
                    series_language = 'it'  # Italian
                elif any(keyword in series_name_lower for keyword in ['turkish', 'türkçe', 'turkce']):
                    series_language = 'tr'  # Turkish
                # Add more language detection logic as needed
                
                # Also check if there's a language field in series_data
                if 'language' in self.series_data:
                    detected_lang = self.series_data['language'].lower()
                    if detected_lang in ['ar', 'arabic', 'عربي']:
                        series_language = 'ar'
                    elif detected_lang in ['fr', 'french', 'français']:
                        series_language = 'fr'
                    elif detected_lang in ['es', 'spanish', 'español']:
                        series_language = 'es'
                    elif detected_lang in ['de', 'german', 'deutsch']:
                        series_language = 'de'
                    elif detected_lang in ['it', 'italian', 'italiano']:
                        series_language = 'it'
                    elif detected_lang in ['tr', 'turkish', 'türkçe']:
                        series_language = 'tr'
                
                if series_language:
                    print(f"[SeriesDetailsWidget] Detected series language: {series_language}")
                
                series_details = self.tmdb_client.get_series_details(tmdb_id, language=series_language)
                if series_details:
                    updated_data = False
                    
                    # Get first_air_date from SeriesDetails model or raw dict
                    first_air_date = None
                    if hasattr(series_details, 'first_air_date'):
                        first_air_date = series_details.first_air_date
                    else:
                        first_air_date = series_details.get('first_air_date')
                    
                    # Update year if missing
                    if (not current_year or current_year == '--') and first_air_date:
                        try:
                            year = first_air_date[:4]  # Extract year from date
                            self.series_data['year'] = year
                            if isinstance(self.series_data, SeriesItem):
                                # For SeriesItem, we can't directly update attributes, so just update the display
                                current_genre_display = self.series_data.genre or '--'
                                self.meta_label.setText(f"Year: {year} | Genre: {current_genre_display}")
                            else:
                                self.series_data['year'] = year
                                self.meta_label.setText(f"Year: {year} | Genre: {self.series_data.get('genre', '--')}")
                            updated_data = True
                            print(f"[SeriesDetailsWidget] Updated year to: {year}")
                        except (ValueError, IndexError):
                            print(f"[SeriesDetailsWidget] Could not parse year from: {first_air_date}")
                    
                    # Get genres from SeriesDetails model or raw dict
                    genres_data = None
                    if hasattr(series_details, 'genres'):
                        genres_data = series_details.genres
                    else:
                        genres_data = series_details.get('genres')
                    
                    # Update genre if missing
                    if (not current_genre or current_genre == '--') and genres_data:
                        try:
                            # Handle Genre objects or raw dicts
                            if genres_data and hasattr(genres_data[0], 'name'):
                                # Genre model objects
                                genres = [genre.name for genre in genres_data[:3]]  # Take first 3 genres
                            else:
                                # Raw dict format
                                genres = [genre['name'] for genre in genres_data[:3]]  # Take first 3 genres
                            genre_string = ', '.join(genres)
                            if isinstance(self.series_data, SeriesItem):
                                # For SeriesItem, we can't directly update attributes, so just update the display
                                current_year_display = self.series_data.get_release_year() or '--'
                                self.meta_label.setText(f"Year: {current_year_display} | Genre: {genre_string}")
                            else:
                                self.series_data['genre'] = genre_string
                                self.meta_label.setText(f"Year: {self.series_data.get('year', '--')} | Genre: {genre_string}")
                            updated_data = True
                            print(f"[SeriesDetailsWidget] Updated genre to: {genre_string}")
                        except (KeyError, TypeError):
                            print(f"[SeriesDetailsWidget] Could not parse genres from TMDB response")
                    
                    # Update plot/overview if missing or empty
                    if isinstance(self.series_data, SeriesItem):
                        current_plot = (self.series_data.plot or '').strip()
                    else:
                        current_plot = self.series_data.get('plot', '').strip()
                    # Get overview from SeriesDetails model or raw dict
                    overview = None
                    if hasattr(series_details, 'overview'):
                        overview = series_details.overview
                    else:
                        overview = series_details.get('overview')
                    
                    if not current_plot and overview:
                        try:
                            overview = overview.strip()
                            if overview:
                                # If we detected a non-English language and got English overview, try to translate
                                final_overview = overview
                                if series_language and series_language != 'en':
                                    try:
                                        from src.utils.translator import get_translation_manager
                                        translation_manager = get_translation_manager()
                                        translated_overview = translation_manager.translate_plot(
                                            overview, 
                                            target_language=series_language, 
                                            source_language='en'
                                        )
                                        if translated_overview and translated_overview != overview:
                                            final_overview = translated_overview
                                            print(f"[SeriesDetailsWidget] Translated plot from English to {series_language}")
                                        else:
                                            print(f"[SeriesDetailsWidget] Translation not available, using English plot")
                                    except Exception as translation_error:
                                        print(f"[SeriesDetailsWidget] Translation error: {translation_error}")
                                        # Continue with English overview if translation fails
                                
                                if isinstance(self.series_data, SeriesItem):
                                    # For SeriesItem, we can't directly update attributes, so just update the display
                                    self.desc_text.setPlainText(final_overview)
                                else:
                                    self.series_data['plot'] = final_overview
                                    self.desc_text.setPlainText(final_overview)
                                updated_data = True
                                print(f"[SeriesDetailsWidget] Updated plot from TMDB overview")
                        except (KeyError, TypeError):
                            print(f"[SeriesDetailsWidget] Could not parse overview from TMDB response")
                    
                    # Cache the updated series data if we made changes
                    if updated_data and hasattr(self.api_client, 'update_series_cache'):
                        try:
                            # Ensure we have the necessary data for caching
                            if isinstance(self.series_data, SeriesItem):
                                # Convert SeriesItem to dictionary for caching
                                series_data_to_cache = {
                                    'series_id': self.series_data.series_id,
                                    'name': self.series_data.name,
                                    'cover': self.series_data.cover,
                                    'plot': self.series_data.plot,
                                    'genre': self.series_data.genre,
                                    'year': self.series_data.get_release_year(),
                                    'tmdb_id': getattr(self.series_data, 'tmdb_id', None)
                                }
                            else:
                                series_data_to_cache = self.series_data.copy()
                            if self.api_client.update_series_cache(series_data_to_cache):
                                series_name = self.series_data.name if isinstance(self.series_data, SeriesItem) else self.series_data.get('name')
                                print(f"[SeriesDetailsWidget] Successfully cached updated metadata for series: {series_name}")
                            else:
                                series_name = self.series_data.name if isinstance(self.series_data, SeriesItem) else self.series_data.get('name')
                                print(f"[SeriesDetailsWidget] Failed to cache updated metadata for series: {series_name}")
                        except Exception as cache_error:
                            print(f"[SeriesDetailsWidget] Error caching updated series data: {cache_error}")
                            
            except Exception as e:
                print(f"[SeriesDetailsWidget] Error fetching series details from TMDB: {e}")
        
        # Use the new async cast loading method
        self.cast_widget.load_cast_async(self.tmdb_client, tmdb_id)
