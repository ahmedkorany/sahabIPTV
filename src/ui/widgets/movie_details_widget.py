import requests
from PyQt5.QtCore import pyqtSignal, Qt, QUrl
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton, QScrollArea, QGridLayout, QSizePolicy
from PyQt5.QtGui import QPixmap, QFont
from src.utils.helpers import load_image_async # Updated import
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from src.api.tmdb import TMDBClient
from src.ui.widgets.cast_widget import CastWidget

class MovieDetailsWidget(QWidget):
    favorite_toggled = pyqtSignal(object)
    play_clicked = pyqtSignal(object)
    trailer_clicked = pyqtSignal(str)

    def __init__(self, movie, api_client=None, main_window=None, tmdb_client=None, parent=None):
        super().__init__(parent)
        self.movie = movie
        self.api_client = api_client
        self.main_window = main_window
        self._is_favorite = False
        # Remove dotenv and os.getenv for TMDB key
        self.tmdb_client = tmdb_client
        self.network_manager = QNetworkAccessManager() # For image loading, if load_image_async needs it directly
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
        # --- Left: Poster and Back button ---
        left_layout = QVBoxLayout()
        self.back_btn = QPushButton("\u2190 Back")
        self.back_btn.setFixedWidth(80)
        left_layout.addWidget(self.back_btn, alignment=Qt.AlignLeft)
        # Poster
        self.poster = QLabel()
        self.poster.setAlignment(Qt.AlignTop)
        if self.movie.get('stream_icon'):
            load_image_async(self.movie['stream_icon'], self.poster, QPixmap('assets/movies.png'), update_size=(180, 260))
        else:
            self.poster.setPixmap(QPixmap('assets/movies.png').scaled(180, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation))
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
                    tmdb_id = vod_info['movie_data']['tmdb_id']
                elif 'info' in vod_info and isinstance(vod_info['info'], dict) and 'tmdb_id' in vod_info['info']:
                    tmdb_id = vod_info['info']['tmdb_id']

                # Update other metadata from vod_info['info']
                info_data = vod_info.get('info', {})
                self.genre_label.setText(info_data.get('genre', 'N/A'))
                self.plot_label.setText(info_data.get('plot', 'N/A'))
                self.rating_label.setText(str(info_data.get('rating', 'N/A')))
                self.director_label.setText(info_data.get('director', 'N/A'))
                self.releasedate_label.setText(info_data.get('releasedate', 'N/A'))
                
                # Update trailer URL if available in VOD info (might be more up-to-date)
                new_trailer_url = info_data.get('youtube_trailer')
                if new_trailer_url:
                    # Construct full YouTube URL if only ID is provided
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

                if tmdb_id and self.tmdb_client:
                    print(f"[MovieDetailsWidget] Found TMDB ID: {tmdb_id}. Fetching credits...")
                    self._fetch_tmdb_credits(tmdb_id)
                elif not self.tmdb_client:
                    print("[MovieDetailsWidget] TMDB client not provided. Cannot fetch cast information.")
                else:
                    print(f"[MovieDetailsWidget] TMDB ID not found in VOD info for stream_id: {self.stream_id}. VOD info: {str(vod_info)[:200]}")
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
