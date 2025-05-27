from PyQt5.QtCore import pyqtSignal, Qt, pyqtSlot
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton, QScrollArea, QGridLayout
from PyQt5.QtGui import QPixmap, QFont
from src.utils.helpers import load_image_async
from PyQt5.QtNetwork import QNetworkAccessManager
from src.ui.widgets.cast_widget import CastWidget
from src.api.xtream import _save_cache, _load_cache # Added _load_cache for future use

class MovieDetailsWidget(QWidget):
    favorite_toggled = pyqtSignal(object)
    play_clicked = pyqtSignal(object)
    trailer_clicked = pyqtSignal(str)
    poster_updated = pyqtSignal(str, str) # stream_id, new_poster_url

    def __init__(self, movie, api_client=None, main_window=None, tmdb_client=None, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.tmdb_client = tmdb_client
        self.stream_id = movie.get('stream_id')
        self.movie = movie
        self.main_window = main_window
        self._is_favorite = False
        self.poseter_load_failed = False
        self.tmdb_id = movie.get('tmdb_id')
        self.tmdb_id_for_poster_fallback = self.tmdb_id
        self.setup_ui()
        self.update_metadata_from_api()
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
        layout = QHBoxLayout(self)
        left_layout = QVBoxLayout()
        self.back_btn = QPushButton("\u2190 Back")
        self.back_btn.setFixedWidth(80)
        left_layout.addWidget(self.back_btn, alignment=Qt.AlignLeft)
        self.poster = QLabel()
        self.poster.setAlignment(Qt.AlignTop)
        self.poseter_load_failed = False
        if self.movie.get('stream_icon'):
            load_image_async(self.movie['stream_icon'], self.poster, QPixmap('assets/movies.png'), update_size=(180, 260), main_window=self, on_failure=self.onPosterLoadFailed)
        else:
            self.load_poster_from_TMDB(self.tmdb_id)
        # Overlay rated-r icon if movie is for adults
        if self.movie.get('adult'):
            rated_r_label = QLabel(self.poster)
            rated_r_pix = QPixmap('assets/rated-r.png').scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            rated_r_label.setPixmap(rated_r_pix)
            rated_r_label.setStyleSheet("background: transparent;")
            rated_r_label.move(0, 0)
            rated_r_label.raise_()
        left_layout.addWidget(self.poster)
        # --- Favorites button under poster ---
        self.favorite_btn = QPushButton()
        self.favorite_btn.setFont(QFont('Arial', 16))
        self.favorite_btn.setStyleSheet("QPushButton { background: transparent; }")
        self.favorite_btn.clicked.connect(self._on_favorite_clicked)
        left_layout.addWidget(self.favorite_btn, alignment=Qt.AlignHCenter)
        layout.addLayout(left_layout)
        # --- Right: Metadata and actions ---
        right_layout = QVBoxLayout()
        self.title = QLabel(self.movie.get('name', ''))
        self.title.setFont(QFont('Arial', 16, QFont.Bold))
        right_layout.addWidget(self.title)

        # Metadata labels
        self.genre_label = QLabel()
        self.plot_label = QTextEdit()
        self.plot_label.setReadOnly(True)
        self.plot_label.setStyleSheet("background: transparent; border: none;") # Make it look like a label
        self.rating_label = QLabel()
        self.director_label = QLabel()
        self.releasedate_label = QLabel()

        # Add metadata labels to layout
        meta_layout = QGridLayout()
        meta_layout.addWidget(QLabel("Genre:"), 0, 0)
        meta_layout.addWidget(self.genre_label, 0, 1)
        meta_layout.addWidget(QLabel("Rating:"), 1, 0)
        meta_layout.addWidget(self.rating_label, 1, 1)
        meta_layout.addWidget(QLabel("Director:"), 2, 0)
        meta_layout.addWidget(self.director_label, 2, 1)
        meta_layout.addWidget(QLabel("Release Date:"), 3, 0)
        meta_layout.addWidget(self.releasedate_label, 3, 1)
        right_layout.addLayout(meta_layout)

        right_layout.addWidget(QLabel("Plot:"))
        right_layout.addWidget(self.plot_label)
        self.meta = QLabel() # Kept if used elsewhere, otherwise can be removed

        # --- Cast Section --- 
        cast_header = QLabel("Cast")
        cast_header.setFont(QFont('Arial', 14, QFont.Bold))
        right_layout.addWidget(cast_header)

        self.cast_scroll_area = QScrollArea()
        self.cast_scroll_area.setWidgetResizable(True)
        self.cast_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.cast_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.cast_scroll_area.setMinimumHeight(450)

        self.cast_widget = CastWidget(main_window=self.main_window)
        self.cast_scroll_area.setWidget(self.cast_widget)
        right_layout.addWidget(self.cast_scroll_area)
        # --- End Cast Section ---

        btn_layout = QHBoxLayout()
        self.play_btn = QPushButton("PLAY")
        self.play_btn.clicked.connect(lambda: self.play_clicked.emit(self.movie))
        btn_layout.addWidget(self.play_btn)
        self.trailer_url = self.movie.get('trailer_url') # This might be from the initial movie object
        self.stream_id = self.movie.get('stream_id')
        if self.trailer_url:
            self.trailer_btn = QPushButton("WATCH TRAILER")
            self.trailer_btn.clicked.connect(lambda: self.trailer_clicked.emit(self.trailer_url))
            btn_layout.addWidget(self.trailer_btn)
        right_layout.addLayout(btn_layout)
        # self.director_label = None # Now part of meta_layout
        # self.cast_label = None # Removed as we now have a dedicated cast poster section
        layout.addLayout(right_layout)
        self.update_favorite_btn()
        self.update_favorite_state()

    @pyqtSlot()
    def load_poster_from_TMDB(self, tmdb_id=None):
        if tmdb_id and self.tmdb_client:
            # print(f"[MovieDetailsWidget] stream_icon missing, attempting to fetch poster from TMDB using tmdb_id: {tmdb_id}") # Original debug log
            try:
                details = self.tmdb_client.get_movie_details(tmdb_id)
                if details:
                    poster_path = details.get('poster_path')
                    if poster_path:
                        tmdb_poster_url = self.tmdb_client.get_full_poster_url(poster_path)
                        if tmdb_poster_url:
                            original_stream_icon = self.movie.get('stream_icon')
                            self.movie['stream_icon'] = tmdb_poster_url
                            # print(f"[MovieDetailsWidget] Found TMDB poster: {tmdb_poster_url}")

                            # --- Update movie in category cache using XtreamClient method ---
                            if hasattr(self.main_window, 'api_client') and self.main_window.api_client:
                                # self.movie dictionary should already contain category_id, stream_id, and the new stream_icon
                                self.main_window.api_client.update_movie_cache(self.movie)
                                self.poster_updated.emit(str(self.movie.get('stream_id')), tmdb_poster_url) # Emit signal
                            # else:
                                # print("[MovieDetailsWidget] api_client not available for cache update.")
                            # --- End update movie in category cache ---

                            load_image_async(tmdb_poster_url, self.poster, QPixmap('assets/movies.png'), update_size=(180, 260), main_window=self.main_window, on_failure=self.onPosterLoadFailed)
                        else:
                                # print(f"[MovieDetailsWidget] Failed to construct TMDB poster URL for tmdb_id: {tmdb_id}") # Original debug log
                            self.poster.setPixmap(QPixmap('assets/movies.png').scaled(180, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    else:
                            # print(f"[MovieDetailsWidget] No poster_path found in TMDB details for tmdb_id: {tmdb_id}") # Original debug log
                        self.poster.setPixmap(QPixmap('assets/movies.png').scaled(180, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                else:
                        # print(f"[MovieDetailsWidget] Failed to fetch details from TMDB for tmdb_id: {tmdb_id}") # Original debug log
                    self.poster.setPixmap(QPixmap('assets/movies.png').scaled(180, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            except Exception as e:
                    # print(f"[MovieDetailsWidget] Error fetching details from TMDB for tmdb_id: {tmdb_id} - {e}") # Original debug log
                self.poster.setPixmap(QPixmap('assets/movies.png').scaled(180, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
                # print(f"[MovieDetailsWidget] No tmdb_id or tmdb_client available to fetch poster.") # Original debug log
            self.poster.setPixmap(QPixmap('assets/movies.png').scaled(180, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    @pyqtSlot()
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
        main_window = self.main_window
        favs = getattr(main_window, 'favorites', []) if main_window else []
        self._is_favorite = any(fav.get('stream_id') == self.movie.get('stream_id') for fav in favs)
        self.update_favorite_btn()

    def update_favorite_btn(self):
        if self._is_favorite:
            self.favorite_btn.setText("★")
            self.favorite_btn.setStyleSheet("QPushButton { color: gold; background: transparent; }")
            self.favorite_btn.setToolTip("Remove from favorites")
        else:
            self.favorite_btn.setText("☆")
            self.favorite_btn.setStyleSheet("QPushButton { color: white; background: transparent; }")
            self.favorite_btn.setToolTip("Add to favorites")

    def _on_favorite_clicked(self):
        main_window = self.main_window
        if main_window and hasattr(main_window, 'toggle_favorite'):
            main_window.toggle_favorite(self.movie)
        else:
            self.favorite_toggled.emit(self.movie)
        self.update_favorite_state()

    def update_metadata_from_api(self):
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
                self.genre_label.setText(info_data.get('genre', 'N/A'))
                self.plot_label.setText(info_data.get('plot', 'N/A'))
                self.rating_label.setText(str(info_data.get('rating', 'N/A')))
                self.director_label.setText(info_data.get('director', 'N/A'))
                self.releasedate_label.setText(info_data.get('releasedate', 'N/A'))
                
                new_trailer_url = info_data.get('youtube_trailer')
                if new_trailer_url:
                    if not new_trailer_url.startswith('http'):
                        self.trailer_url = f"https://www.youtube.com/watch?v={new_trailer_url}"
                    else:
                        self.trailer_url = new_trailer_url
                    # Update trailer button if it exists, or create if it doesn't
                    if hasattr(self, 'trailer_btn') and self.trailer_btn:
                        self.trailer_btn.setEnabled(True)
                        # Ensure the lambda captures the new URL
                        self.trailer_btn.clicked.disconnect()
                        self.trailer_btn.clicked.connect(lambda: self.trailer_clicked.emit(self.trailer_url))
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
            if 'cast' in credits_data and credits_data['cast']:
                print(f"[MovieDetailsWidget] Found {len(credits_data['cast'])} cast members.")
                self.cast_widget.set_cast(credits_data['cast'])
            else:
                print("[MovieDetailsWidget] 'cast' key not found or empty in TMDB credits response.")
        except Exception as e:
            print(f"[MovieDetailsWidget] Error fetching TMDB credits: {e}")
