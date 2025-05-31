from PyQt5.QtCore import pyqtSignal, Qt, pyqtSlot
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea
from PyQt5.QtGui import QPixmap, QFont
from src.utils.helpers import load_image_async, get_translations
from src.ui.widgets.cast_widget import CastWidget
from src.models import MovieItem

class MovieDetailsWidget(QWidget):
    favorite_toggled = pyqtSignal(object)
    play_clicked = pyqtSignal(object)
    trailer_clicked = pyqtSignal(str)
    toggle_favorite_movie_requested = pyqtSignal(object)  # movie data

    def __init__(self, movie, api_client=None, main_window=None, tmdb_client=None, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.tmdb_client = tmdb_client
        
        # Ensure movie is always a MovieItem instance
        if not isinstance(movie, MovieItem):
            raise ValueError("MovieDetailsWidget requires a MovieItem instance")
        
        self.stream_id = movie.stream_id
        self.tmdb_id = movie.tmdb_id
        self.movie = movie
        self.main_window = main_window
        self._is_favorite = False
        self.poseter_load_failed = False
        self.tmdb_id_for_poster_fallback = self.tmdb_id
        # Get translations from main window or default to English
        language = getattr(main_window, 'language', 'en') if main_window else 'en'
        self.translations = get_translations(language)
        self.setup_ui()
        self._set_initial_layout_direction()
        self.update_metadata_from_api()
    
    def _set_initial_layout_direction(self):
        """Set initial layout direction - always LTR for MovieDetailsWidget"""
        from PyQt5.QtCore import Qt
        
        # Always set LTR layout for MovieDetailsWidget regardless of app language
        self.setLayoutDirection(Qt.LeftToRight)
        print(f"[MovieDetailsWidget] Set LTR layout (override RTL app setting)")
    def _clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    sub_layout = item.layout()
                    if sub_layout is not None:
                        self._clear_layout(sub_layout)

    def setup_ui(self):
        # Main vertical layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(20)
        
        # Hero section with backdrop and overlay content (starts from top)
        self.hero_widget = QWidget()
        self.hero_widget.setObjectName("hero_widget")
        self.hero_widget.setFixedHeight(400)
        self.hero_widget.setStyleSheet("""
            QWidget {
                background: linear-gradient(to bottom, rgba(0,0,0,0.3), rgba(0,0,0,0.8)), 
                           url('assets/movies.png');
                background-size: cover;
                background-position: center;
                border-radius: 8px;
            }
        """)
        
        # Back button positioned in top left of hero area
        self.back_btn = QPushButton(f"\u2190 {self.translations.get('Back', 'Back')}", self.hero_widget)
        self.back_btn.setFixedSize(80, 40)
        self.back_btn.move(0, 0)  # Position at exact top left corner
        self.back_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0, 0, 0, 0.7);
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: rgba(0, 0, 0, 0.9);
            }
        """)
        self.back_btn.raise_()  # Ensure it's on top
        
        hero_layout = QHBoxLayout(self.hero_widget)
        hero_layout.setContentsMargins(40, 40, 40, 40)
        
        # Poster on the left
        self.poster = QLabel()
        self.poster.setFixedSize(200, 300)
        self.poster.setStyleSheet("""
            QLabel {
                border-radius: 8px;
                border: 3px solid white;
            }
        """)
        self.poster.setScaledContents(True)
        self.poseter_load_failed = False
        
        # Access movie data from MovieItem instance
        movie_stream_icon = self.movie.stream_icon
        movie_adult = self.movie.adult
        movie_name = self.movie.name or ''
        
        if movie_stream_icon:
            load_image_async(movie_stream_icon, self.poster, QPixmap('assets/movies.png'), update_size=(200, 300), main_window=self, on_failure=self.onPosterLoadFailed)
        else:
            self.load_poster_from_TMDB(self.tmdb_id)
            
        # Overlay rated-r icon if movie is for adults
        if movie_adult:
            rated_r_label = QLabel(self.poster)
            rated_r_pix = QPixmap('assets/rated-r.png').scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            rated_r_label.setPixmap(rated_r_pix)
            rated_r_label.setStyleSheet("background: transparent;")
            rated_r_label.move(0, 0)
            rated_r_label.raise_()
            
        hero_layout.addWidget(self.poster)
        
        # Movie info overlay on the right
        info_layout = QVBoxLayout()
        info_layout.setSpacing(16)
        
        # Title and year
        title_year_layout = QHBoxLayout()
        self.title = QLabel(movie_name)
        self.title.setFont(QFont('Arial', 32, QFont.Bold))
        self.title.setStyleSheet("color: white; background: transparent;")
        title_year_layout.addWidget(self.title)
        
        self.year_label = QLabel()
        self.year_label.setFont(QFont('Arial', 24))
        self.year_label.setStyleSheet("color: #cccccc; background: transparent;")
        title_year_layout.addWidget(self.year_label)
        title_year_layout.addStretch()
        info_layout.addLayout(title_year_layout)
        
        # Tagline/Slogan immediately under title
        self.tagline_label = QLabel()
        self.tagline_label.setFont(QFont('Arial', 16, QFont.StyleItalic))
        self.tagline_label.setStyleSheet("color: #cccccc; font-style: italic; background: transparent;")
        self.tagline_label.setWordWrap(True)
        self.tagline_label.setMaximumWidth(400)
        info_layout.addWidget(self.tagline_label)
        
        # Genre and duration
        genre_duration_layout = QHBoxLayout()
        self.genre_label = QLabel()
        self.genre_label.setFont(QFont('Arial', 16))
        self.genre_label.setStyleSheet("color: #cccccc; background: transparent;")
        genre_duration_layout.addWidget(self.genre_label)
        
        self.duration_label = QLabel()
        self.duration_label.setFont(QFont('Arial', 16))
        self.duration_label.setStyleSheet("color: #cccccc; background: transparent;")
        genre_duration_layout.addWidget(self.duration_label)
        genre_duration_layout.addStretch()
        info_layout.addLayout(genre_duration_layout)
        
        # Rating, Play and Favorite buttons
        controls_layout = QHBoxLayout()
        
        # User rating circle
        self.rating_widget = QLabel()
        self.rating_widget.setFixedSize(60, 60)
        self.rating_widget.setStyleSheet("""
            QLabel {
                background: rgba(0, 0, 0, 0.8);
                border: 3px solid #21d07a;
                border-radius: 30px;
                color: white;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        self.rating_widget.setAlignment(Qt.AlignCenter)
        controls_layout.addWidget(self.rating_widget)
        
        # Play button
        self.play_btn = QPushButton(f"▶ {self.translations.get('PLAY', 'PLAY')}")
        self.play_btn.setFont(QFont('Arial', 16, QFont.Bold))
        self.play_btn.setStyleSheet("""
            QPushButton {
                background: #e50914;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                margin-left: 16px;
            }
            QPushButton:hover {
                background: #f40612;
            }
        """)
        self.play_btn.clicked.connect(lambda: self.play_clicked.emit(self.movie))
        controls_layout.addWidget(self.play_btn)
        
        # Favorite button (using star shape like series details)
        self.favorite_btn = QPushButton()
        self.favorite_btn.setFixedSize(50, 50)
        self.favorite_btn.setFont(QFont('Arial', 16))
        self.favorite_btn.clicked.connect(self._on_favorite_clicked)
        controls_layout.addWidget(self.favorite_btn)
        
        # Trailer button if available
        self.trailer_url = self.movie.youtube_trailer
        self.current_trailer_url = self.trailer_url
        
        if self.trailer_url and self.trailer_url.strip():
            if not self.trailer_url.startswith('http'):
                self.current_trailer_url = f"https://www.youtube.com/watch?v={self.trailer_url}"
            else:
                self.current_trailer_url = self.trailer_url
                
            self.trailer_btn = QPushButton(self.translations.get("🎬 TRAILER", "🎬 TRAILER"))
            self.trailer_btn.setFont(QFont('Arial', 14))
            self.trailer_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.2);
                    color: white;
                    border: 2px solid white;
                    padding: 8px 16px;
                    border-radius: 6px;
                    margin-left: 16px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.3);
                }
            """)
            self.trailer_btn.clicked.connect(lambda: self.trailer_clicked.emit(self.current_trailer_url))
            controls_layout.addWidget(self.trailer_btn)
        else:
            self.trailer_btn = None
            
        controls_layout.addStretch()
        info_layout.addLayout(controls_layout)
        
        # Add plot/overview to hero section
        self.plot_label = QLabel()
        self.plot_label.setFont(QFont('Arial', 14))
        self.plot_label.setStyleSheet("color: white; background: transparent; line-height: 1.6;")
        self.plot_label.setWordWrap(True)
        self.plot_label.setMaximumWidth(400)  # Limit width for readability
        info_layout.addWidget(self.plot_label)
        
        # Add director to hero section
        director_layout = QHBoxLayout()
        director_header = QLabel(self.translations.get("Director", "Director: "))
        director_header.setFont(QFont('Arial', 14, QFont.Bold))
        director_header.setStyleSheet("color: #cccccc; background: transparent;")
        director_layout.addWidget(director_header)
        
        self.director_label = QLabel()
        self.director_label.setFont(QFont('Arial', 14))
        self.director_label.setStyleSheet("color: white; background: transparent;")
        director_layout.addWidget(self.director_label)
        director_layout.addStretch()
        info_layout.addLayout(director_layout)
        
        info_layout.addStretch()
        
        hero_layout.addLayout(info_layout)
        main_layout.addWidget(self.hero_widget)
        
        # Cast section fills all remaining space below hero
        #cast_header = QLabel("Cast")
        #cast_header.setFont(QFont('Arial', 20, QFont.Bold))
        #cast_header.setStyleSheet("color: #333333; margin: 0px 0px 0px 0px;")
        #main_layout.addWidget(cast_header)
        
        self.cast_scroll_area = QScrollArea()
        self.cast_scroll_area.setWidgetResizable(True)
        self.cast_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.cast_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.cast_scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
                margin: 0px 0px 0px 0px;
            }
        """)
        
        self.cast_widget = CastWidget(main_window=self.main_window)
        self.cast_scroll_area.setWidget(self.cast_widget)
        main_layout.addWidget(self.cast_scroll_area, 1)  # Stretch factor 1 to fill remaining space
        
        # Initialize labels
        self.rating_label = QLabel()
        self.releasedate_label = QLabel()
        self.meta = QLabel()
        
        self.update_favorite_btn()
        self.update_favorite_state()
        
        # Removed backdrop functionality
        
        # Create initial gradient background
        self.create_poster_gradient_background()

    @pyqtSlot()
    def load_poster_from_TMDB(self, tmdb_id=None):
        if tmdb_id and self.tmdb_client:
            # print(f"[MovieDetailsWidget] stream_icon missing, attempting to fetch poster from TMDB using tmdb_id: {tmdb_id}") # Original debug log
            try:
                details = self.tmdb_client.get_movie_details(tmdb_id)
                if details:
                    # Handle MovieDetails model or raw dict
                    if hasattr(details, 'poster_path'):
                        poster_path = details.poster_path
                    else:
                        poster_path = details.get('poster_path')
                    if poster_path:
                        tmdb_poster_url = self.tmdb_client.get_full_poster_url(poster_path)
                        if tmdb_poster_url:
                            original_stream_icon = self.movie.stream_icon
                            self.movie.stream_icon = tmdb_poster_url
                            # print(f"[MovieDetailsWidget] Found TMDB poster: {tmdb_poster_url}")

                            # --- Update movie in category cache using XtreamClient method ---
                            if hasattr(self.main_window, 'api_client') and self.main_window.api_client:
                                # Convert MovieItem to dictionary for cache update if necessary
                                movie_data_for_cache = self.movie.to_dict()
                                self.main_window.api_client.update_movie_cache(movie_data_for_cache)
                            # else:
                                # print("[MovieDetailsWidget] api_client not available for cache update.")
                            # --- End update movie in category cache ---

                            load_image_async(tmdb_poster_url, self.poster, QPixmap('assets/movies.png'), update_size=(200, 300), main_window=self.main_window, on_failure=self.onPosterLoadFailed)
                        else:
                                # print(f"[MovieDetailsWidget] Failed to construct TMDB poster URL for tmdb_id: {tmdb_id}") # Original debug log
                            self.poster.setPixmap(QPixmap('assets/movies.png').scaled(200, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    else:
                            # print(f"[MovieDetailsWidget] No poster_path found in TMDB details for tmdb_id: {tmdb_id}") # Original debug log
                        self.poster.setPixmap(QPixmap('assets/movies.png').scaled(200, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                else:
                        # print(f"[MovieDetailsWidget] Failed to fetch details from TMDB for tmdb_id: {tmdb_id}") # Original debug log
                    self.poster.setPixmap(QPixmap('assets/movies.png').scaled(200, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            except Exception as e:
                    # print(f"[MovieDetailsWidget] Error fetching details from TMDB for tmdb_id: {tmdb_id} - {e}") # Original debug log
                self.poster.setPixmap(QPixmap('assets/movies.png').scaled(200, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
                # print(f"[MovieDetailsWidget] No tmdb_id or tmdb_client available to fetch poster.") # Original debug log
            self.poster.setPixmap(QPixmap('assets/movies.png').scaled(200, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    @pyqtSlot(bool)
    def onPosterLoadFailed(self, is_network_error=False):
        if is_network_error:
            print("[MovieDetailsWidget] Poster load failed due to network error. Not re-attempting TMDB fetch.")
            self.poseter_load_failed = True
        else:
            print("[MovieDetailsWidget] Poster load failed. Will attempt to load from TMDB.")
            self.poseter_load_failed = True
            # Pass the tmdb_id to load_poster_from_TMDB when called from onPosterLoadFailed
            if hasattr(self, 'tmdb_id_for_poster_fallback') and self.tmdb_id_for_poster_fallback:
                self.load_poster_from_TMDB(self.tmdb_id_for_poster_fallback)
            else:
                print("[MovieDetailsWidget] No tmdb_id available for poster fallback.")

    def update_favorite_state(self):
        """Update favorite state by checking with main window"""
        if not self.main_window or not hasattr(self.main_window, 'favorites_manager'):
            self._is_favorite = False
            self.update_favorite_btn()
            return

        favorite_item_check = {
            'stream_id': self.movie.stream_id,
            'stream_type': 'movie'
        }

        self._is_favorite = self.main_window.favorites_manager.is_favorite(favorite_item_check)
        self.update_favorite_btn()

    def refresh_favorite_button(self):
        """Refresh the favorite button state - called by main window after favorites change"""
        self.update_favorite_state()

    # Removed backdrop loading functionality
    
    # Removed backdrop overlay functionality
    
    # Removed backdrop loading from VOD info functionality
    
    # Removed backdrop URL loading functionality
    
    # Removed backdrop image loading with callbacks functionality

    def create_poster_gradient_background(self):
        """Create a gradient background based on poster colors when backdrop is not available"""
        if not hasattr(self, 'poster') or not self.poster.pixmap():
            return
            
        try:
            # Extract dominant colors from poster
            colors = self.extract_dominant_colors(self.poster.pixmap())
            if not colors:
                return
                
            # Create gradient from colors
            gradient_colors = []
            for color in colors[:3]:  # Use up to 3 colors
                gradient_colors.append(f"rgba({color[0]}, {color[1]}, {color[2]}, 0.8)")
            
            # If we have less than 2 colors, duplicate the first one
            if len(gradient_colors) == 1:
                gradient_colors.append(gradient_colors[0])
            
            # Create gradient stylesheet
            gradient_style = f"""
            QWidget#hero_widget {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {gradient_colors[0]},
                    stop:1 {gradient_colors[-1]});
            }}
            """
            
            self.hero_widget.setStyleSheet(gradient_style)
            print(f"[MovieDetailsWidget] Applied poster gradient background with colors: {gradient_colors}")
            
        except Exception as e:
            print(f"[MovieDetailsWidget] Error creating poster gradient: {e}")
    
    def extract_dominant_colors(self, image, num_colors=2):
        """Extract dominant colors from an image"""
        try:
            from collections import Counter
            
            # Sample pixels from the image
            width = image.width()
            height = image.height()
            
            # Sample every 10th pixel to avoid processing too many pixels
            colors = []
            for x in range(0, width, 10):
                for y in range(0, height, 10):
                    pixel = image.pixel(x, y)
                    # Convert QRgb to RGB tuple
                    r = (pixel >> 16) & 0xFF
                    g = (pixel >> 8) & 0xFF
                    b = pixel & 0xFF
                    
                    # Skip very dark or very light colors
                    brightness = (r + g + b) / 3
                    if 30 < brightness < 200:
                        colors.append((r, g, b))
            
            if not colors:
                return [(50, 50, 50), (20, 20, 20)]  # Default colors
            
            # Find most common colors
            color_counts = Counter(colors)
            dominant_colors = [color for color, count in color_counts.most_common(num_colors)]
            
            # Ensure we have at least 2 colors
            while len(dominant_colors) < num_colors:
                dominant_colors.append(dominant_colors[-1] if dominant_colors else (50, 50, 50))
            
            return dominant_colors[:num_colors]
        except Exception as e:
            print(f"[MovieDetailsWidget] Error extracting colors: {e}")
            return [(50, 50, 50), (20, 20, 20)]  # Default colors
    
    def update_favorite_btn(self):
        if self._is_favorite:
            self.favorite_btn.setText("★")  # Filled star
            self.favorite_btn.setStyleSheet("""
                QPushButton {
                    color: gold;
                    background: transparent;
                    border: none;
                    margin-left: 16px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.1);
                }
            """)
            self.favorite_btn.setToolTip(self.translations.get("Remove from favorites", "Remove from favorites"))
        else:
            self.favorite_btn.setText("☆")  # Empty star
            self.favorite_btn.setStyleSheet("""
                QPushButton {
                    color: white;
                    background: transparent;
                    border: none;
                    margin-left: 16px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.1);
                }
            """)
            self.favorite_btn.setToolTip(self.translations.get("Add to favorites", "Add to favorites"))

    def _on_favorite_clicked(self):
        """Handle favorite button click - emit signal for main window to handle"""
        self.toggle_favorite_movie_requested.emit(self.movie)
        # The button text/icon update should be handled by the main window
        # or by re-checking favorite status after the signal is processed.

    def update_metadata_from_api(self):
        print(f"[MovieDetailsWidget] update_metadata_from_api for movie {self.movie}")

        if not self.api_client or not self.stream_id:
            print("[MovieDetailsWidget] No API client or stream_id, skipping VOD info fetch.")
            return
        try:
            print(f"[MovieDetailsWidget] Fetching VOD info for stream_id: {self.stream_id}")
            success, vod_info = self.api_client.get_vod_info(self.stream_id)
            if success and vod_info:
                print(f"[MovieDetailsWidget] VOD Info received: {vod_info}") # Log snippet
                tmdb_id = None
                if 'movie_data' in vod_info and isinstance(vod_info['movie_data'], dict) and 'tmdb_id' in vod_info['movie_data']:
                    self.tmdb_id = vod_info['movie_data']['tmdb_id']
                    self.tmdb_id_for_poster_fallback = self.tmdb_id
                elif 'info' in vod_info and isinstance(vod_info['info'], dict) and 'tmdb_id' in vod_info['info']:
                    self.tmdb_id = vod_info['info']['tmdb_id']
                    self.tmdb_id_for_poster_fallback = self.tmdb_id

                info_data = vod_info.get('info', {})
                
                # Update genre
                genre = info_data.get('genre', self.translations.get('N/A', 'N/A'))
                self.genre_label.setText(genre)
                
                # Update plot/overview
                plot = info_data.get('plot', self.translations.get('N/A', 'N/A'))
                self.plot_label.setText(plot)
                
                # Update rating with percentage display
                rating = info_data.get('rating', 'N/A')
                if rating and rating != 'N/A':
                    try:
                        rating_float = float(rating)
                        rating_percent = int(rating_float * 10)  # Convert to percentage
                        self.rating_widget.setText(f"{rating_percent}%")
                        self.rating_label.setText(str(rating))
                    except (ValueError, TypeError):
                        self.rating_widget.setText("N/A")
                        self.rating_label.setText(str(rating))
                else:
                    self.rating_widget.setText(self.translations.get("N/A", "N/A"))
                    self.rating_label.setText(self.translations.get("N/A", "N/A"))
                
                # Update director
                director = info_data.get('director', self.translations.get('N/A', 'N/A'))
                self.director_label.setText(director)
                
                # Update release date and extract year
                release_date = info_data.get('releasedate', self.translations.get('N/A', 'N/A'))
                self.releasedate_label.setText(release_date)
                
                # Extract year from release date
                if release_date and release_date != 'N/A':
                    try:
                        # Try to extract year from various date formats
                        import re
                        year_match = re.search(r'(\d{4})', release_date)
                        if year_match:
                            year = year_match.group(1)
                            self.year_label.setText(f"({year})")
                        else:
                            self.year_label.setText("")
                    except:
                        self.year_label.setText("")
                else:
                    self.year_label.setText("")
                
                # Update duration if available
                duration = info_data.get('duration', '') or info_data.get('runtime', '')
                if duration:
                    if 'min' not in str(duration).lower():
                        duration = f"{duration} min"
                    self.duration_label.setText(f" • {duration}")
                else:
                    self.duration_label.setText("")
                
                # Writer section removed
                
                # Update tagline if available
                tagline = info_data.get('tagline', '') or info_data.get('slogan', '')
                if tagline:
                    self.tagline_label.setText(f'"{tagline}"')
                    self.tagline_label.show()
                else:
                    self.tagline_label.hide()
                
                new_trailer_url = info_data.get('youtube_trailer')
                if new_trailer_url and new_trailer_url.strip():
                    self.trailer_url = new_trailer_url
                    # Handle YouTube video ID or full URL
                    if not new_trailer_url.startswith('http'):
                        self.current_trailer_url = f"https://www.youtube.com/watch?v={new_trailer_url}"
                    else:
                        self.current_trailer_url = new_trailer_url
                    
                    # Update trailer button if it exists, or create if it doesn't
                    if hasattr(self, 'trailer_btn') and self.trailer_btn:
                        self.trailer_btn.setEnabled(True)
                        # Ensure the lambda captures the new resolved URL
                        self.trailer_btn.clicked.disconnect()
                        self.trailer_btn.clicked.connect(lambda: self.trailer_clicked.emit(self.current_trailer_url))
                    elif not hasattr(self, 'trailer_btn') or not self.trailer_btn:
                        # This assumes btn_layout is accessible or re-created. 
                        # For simplicity, we'll assume it's fine if the button was initially created.
                        # A more robust solution might involve checking and adding the button if it wasn't there.
                        print("[MovieDetailsWidget] Trailer URL updated, but button not found to re-enable or re-create.")

                if self.tmdb_id and self.tmdb_client:
                    print(f"[MovieDetailsWidget] Found TMDB ID: {self.tmdb_id}. Fetching credits...")
                    self._fetch_tmdb_credits(self.tmdb_id)
                elif not self.tmdb_client:
                    print("[MovieDetailsWidget] TMDB client not provided. Cannot fetch cast information.")
                else:
                    print(f"[MovieDetailsWidget] TMDB ID not found in VOD info for stream_id: {self.stream_id}. VOD info: {str(vod_info)[:200]}")
                # Removed backdrop loading from VOD info
                
                if self.tmdb_id:
                    self.load_poster_from_TMDB(self.tmdb_id)
            else:
                print(f"[MovieDetailsWidget] Failed to get VOD info or VOD info is empty. Success: {success}")
        except Exception as e:
            print(f"[MovieDetailsWidget] Error in update_metadata_from_api: {e}")

    def _fetch_tmdb_credits(self, tmdb_id):
        if not self.tmdb_client:
            print("[MovieDetailsWidget] TMDB client is missing, cannot fetch credits.")
            return
        print(f"[MovieDetailsWidget] Fetching TMDB credits for TMDB ID: {tmdb_id}")
        try:
            credits_data = self.tmdb_client.get_movie_credits(tmdb_id)
            print(f"[MovieDetailsWidget] TMDB credits data received: {str(credits_data)[:200]}...")
            
            cast_list = []
            if credits_data:
                # Handle MovieCredits model
                if hasattr(credits_data, 'cast'):
                    # Convert CastMember objects to dictionaries for compatibility
                    cast_list = [cast_member.to_dict() for cast_member in credits_data.cast]
                    print(f"[MovieDetailsWidget] Found {len(cast_list)} cast members from MovieCredits model.")
                # Handle raw dictionary (fallback)
                elif isinstance(credits_data, dict) and 'cast' in credits_data:
                    cast_list = credits_data['cast']
                    print(f"[MovieDetailsWidget] Found {len(cast_list)} cast members from raw data.")
                else:
                    print("[MovieDetailsWidget] No cast data found in TMDB credits response.")
            
            if cast_list:
                self.cast_widget.set_cast(cast_list)
            else:
                print("[MovieDetailsWidget] No cast members to display.")
        except Exception as e:
            print(f"[MovieDetailsWidget] Error fetching TMDB credits: {e}")
        
        # Check if we need to fetch additional metadata (plot/overview)
        current_plot = (self.movie.plot or '').strip()
        movie_name = self.movie.name or ''
        
        needs_metadata_update = not current_plot
        
        if needs_metadata_update:
            print(f"[MovieDetailsWidget] Missing plot detected. Fetching movie details from TMDB.")
        
        # Fetch movie details if we need additional metadata
        if needs_metadata_update:
            try:
                # Try to detect movie language for localized content
                movie_language = None
                
                # Check for language indicators in movie data
                movie_name_lower = movie_name.lower()
                
                # Enhanced language detection
                # Check for Arabic characters (Unicode range for Arabic)
                import re
                arabic_pattern = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]')
                if arabic_pattern.search(movie_name):
                    movie_language = 'ar'  # Arabic
                    print(f"[MovieDetailsWidget] Detected Arabic characters in movie name: {movie_name}")
                # Check for specific Arabic keywords
                elif any(keyword in movie_name_lower for keyword in ['arabic', 'عربي', 'عرب']):
                    movie_language = 'ar'  # Arabic
                elif any(keyword in movie_name_lower for keyword in ['french', 'français', 'francais']):
                    movie_language = 'fr'  # French
                elif any(keyword in movie_name_lower for keyword in ['spanish', 'español', 'espanol']):
                    movie_language = 'es'  # Spanish
                elif any(keyword in movie_name_lower for keyword in ['german', 'deutsch']):
                    movie_language = 'de'  # German
                elif any(keyword in movie_name_lower for keyword in ['italian', 'italiano']):
                    movie_language = 'it'  # Italian
                elif any(keyword in movie_name_lower for keyword in ['turkish', 'türkçe', 'turkce']):
                    movie_language = 'tr'  # Turkish
                # Add more language detection logic as needed
                
                # Also check if there's a language field in movie data
                # MovieItem doesn't have a language field, skip this check
                movie_language_field = None
                
                if movie_language_field:
                    detected_lang = movie_language_field.lower()
                    if detected_lang in ['ar', 'arabic', 'عربي']:
                        movie_language = 'ar'
                    elif detected_lang in ['fr', 'french', 'français']:
                        movie_language = 'fr'
                    elif detected_lang in ['es', 'spanish', 'español']:
                        movie_language = 'es'
                    elif detected_lang in ['de', 'german', 'deutsch']:
                        movie_language = 'de'
                    elif detected_lang in ['it', 'italian', 'italiano']:
                        movie_language = 'it'
                    elif detected_lang in ['tr', 'turkish', 'türkçe']:
                        movie_language = 'tr'
                
                # Always set LTR layout for MovieDetailsWidget regardless of movie or app language
                from PyQt5.QtCore import Qt
                self.setLayoutDirection(Qt.LeftToRight)
                if movie_language:
                    print(f"[MovieDetailsWidget] Detected movie language: {movie_language}, but keeping LTR layout")
                
                movie_details = self.tmdb_client.get_movie_details(tmdb_id, language=movie_language)
                if movie_details:
                    updated_data = False
                    
                    # Get overview from MovieDetails model or raw dict
                    overview = None
                    if hasattr(movie_details, 'overview'):
                        overview = movie_details.overview
                    else:
                        overview = movie_details.get('overview')
                    
                    # Update plot/overview if missing or empty
                    if not current_plot and overview:
                        try:
                            overview = overview.strip()
                            if overview:
                                # If we detected a non-English language and got English overview, try to translate
                                final_overview = overview
                                if movie_language and movie_language != 'en':
                                    try:
                                        from src.utils.translator import get_translation_manager
                                        translation_manager = get_translation_manager()
                                        translated_overview = translation_manager.translate_plot(
                                            overview, 
                                            target_language=movie_language, 
                                            source_language='en'
                                        )
                                        if translated_overview and translated_overview != overview:
                                            final_overview = translated_overview
                                            print(f"[MovieDetailsWidget] Translated plot from English to {movie_language}")
                                        else:
                                            print(f"[MovieDetailsWidget] Translation not available, using English plot")
                                    except Exception as translation_error:
                                        print(f"[MovieDetailsWidget] Translation error: {translation_error}")
                                        # Continue with English overview if translation fails
                                
                                self.movie.plot = final_overview
                                self.plot_label.setText(final_overview)
                                if hasattr(self, 'desc_text'):
                                    self.desc_text.setPlainText(final_overview)
                                updated_data = True
                                print(f"[MovieDetailsWidget] Updated plot from TMDB overview")
                        except (KeyError, TypeError):
                            print(f"[MovieDetailsWidget] Could not parse overview from TMDB response")
                    
                    # Update additional TMDB data
                    tagline = None
                    if hasattr(movie_details, 'tagline'):
                        tagline = movie_details.tagline
                    else:
                        tagline = movie_details.get('tagline')
                    
                    if tagline:
                        self.tagline_label.setText(f'"{tagline}"')
                        self.tagline_label.show()
                    
                    # Update release year
                    if movie_details.get('release_date'):
                        try:
                            release_year = movie_details['release_date'][:4]
                            self.year_label.setText(f"({release_year})")
                        except:
                            pass
                    
                    # Update runtime/duration
                    if movie_details.get('runtime'):
                        runtime = movie_details['runtime']
                        self.duration_label.setText(f" • {runtime} min")
                    
                    # Update rating
                    if movie_details.get('vote_average'):
                        try:
                            rating = float(movie_details['vote_average'])
                            rating_percent = int(rating * 10)
                            self.rating_widget.setText(f"{rating_percent}%")
                        except:
                            pass
                    
                    # Update genres
                    if movie_details.get('genres'):
                        genres = [genre['name'] for genre in movie_details['genres'][:3]]  # Limit to 3 genres
                        self.genre_label.setText(', '.join(genres))
                    
                    # Cache the updated movie data if we made changes
                    if updated_data and hasattr(self.api_client, 'update_movie_cache'):
                        try:
                            # Ensure we have the necessary data for caching
                            movie_data_to_cache = self.movie.to_dict()
                            movie_name = self.movie.name
                            
                            if self.api_client.update_movie_cache(movie_data_to_cache):
                                print(f"[MovieDetailsWidget] Successfully cached updated metadata for movie: {movie_name}")
                            else:
                                print(f"[MovieDetailsWidget] Failed to cache updated metadata for movie: {movie_name}")
                        except Exception as cache_error:
                            print(f"[MovieDetailsWidget] Error caching updated metadata: {cache_error}")
                else:
                    print(f"[MovieDetailsWidget] No movie details returned from TMDB for ID: {tmdb_id}")
            except Exception as e:
                print(f"[MovieDetailsWidget] Error fetching movie details from TMDB: {e}")
