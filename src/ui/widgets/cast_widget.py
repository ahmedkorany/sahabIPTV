from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame, QSizePolicy
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject
from src.utils.helpers import load_image_async, get_translations
import requests

class CastDataWorker(QObject):
    """Worker thread for fetching cast data asynchronously."""
    cast_data_ready = pyqtSignal(list)  # Signal emitted when cast data is ready
    error_occurred = pyqtSignal(str)    # Signal emitted when an error occurs
    
    def __init__(self, tmdb_client, tmdb_id):
        super().__init__()
        self.tmdb_client = tmdb_client
        self.tmdb_id = tmdb_id
    
    def fetch_cast_data(self):
        """Fetch cast data from TMDB API."""
        try:
            print(f"[CastDataWorker] Fetching cast data for TMDB ID: {self.tmdb_id}")
            credits_data = self.tmdb_client.get_series_credits(self.tmdb_id)
            if credits_data and 'cast' in credits_data:
                cast_list = credits_data['cast']
                print(f"[CastDataWorker] Successfully fetched {len(cast_list)} cast members")
                self.cast_data_ready.emit(cast_list)
            else:
                print("[CastDataWorker] No cast data found in TMDB response")
                self.cast_data_ready.emit([])
        except Exception as e:
            error_msg = f"Error fetching cast data: {str(e)}"
            print(f"[CastDataWorker] {error_msg}")
            self.error_occurred.emit(error_msg)

class CastWidget(QWidget):
    def __init__(self, main_window=None, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        # Get translations from parent or default to English
        language = getattr(parent, 'language', 'en') if hasattr(parent, 'language') else 'en'
        self.translations = get_translations(language)
        
        # Create main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create scroll area for horizontal cast layout
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setFixedHeight(250)  # Fixed height for cast area
        
        # Create container widget for cast members
        self.cast_container = QWidget()
        self.cast_layout = QHBoxLayout(self.cast_container)
        self.cast_layout.setAlignment(Qt.AlignLeft)
        self.cast_layout.setSpacing(10)
        self.cast_layout.setContentsMargins(10, 10, 10, 10)
        
        # Set the container as the scroll area's widget
        self.scroll_area.setWidget(self.cast_container)
        main_layout.addWidget(self.scroll_area)
        
        # Async loading components
        self.cast_worker = None
        self.cast_thread = None
        self.loading_label = None
        
        # Show loading indicator initially
        self._show_loading_indicator()

    def _show_loading_indicator(self):
        """Show a loading indicator while cast data is being fetched."""
        self.clear()
        self.loading_label = QLabel(self.translations.get("Loading cast...", "Loading cast..."))
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet("color: gray; font-size: 14px;")
        self.cast_layout.addWidget(self.loading_label)

    def load_cast_async(self, tmdb_client, tmdb_id):
        """Load cast data asynchronously."""
        print(f"[CastWidget] Starting async cast loading for TMDB ID: {tmdb_id}")
        
        # Clean up any existing worker/thread
        if self.cast_thread and self.cast_thread.isRunning():
            self.cast_thread.quit()
            self.cast_thread.wait()
        
        # Show loading indicator
        self._show_loading_indicator()
        
        # Create worker and thread
        self.cast_worker = CastDataWorker(tmdb_client, tmdb_id)
        self.cast_thread = QThread()
        
        # Move worker to thread
        self.cast_worker.moveToThread(self.cast_thread)
        
        # Connect signals
        self.cast_thread.started.connect(self.cast_worker.fetch_cast_data)
        self.cast_worker.cast_data_ready.connect(self._on_cast_data_ready)
        self.cast_worker.error_occurred.connect(self._on_cast_error)
        self.cast_worker.cast_data_ready.connect(self.cast_thread.quit)
        self.cast_worker.error_occurred.connect(self.cast_thread.quit)
        self.cast_thread.finished.connect(self.cast_worker.deleteLater)
        
        # Start the thread
        self.cast_thread.start()

    def _on_cast_data_ready(self, cast_data):
        """Handle when cast data is ready."""
        print(f"[CastWidget] Cast data ready with {len(cast_data)} members")
        self.set_cast(cast_data)

    def _on_cast_error(self, error_message):
        """Handle cast data loading errors."""
        print(f"[CastWidget] Cast loading error: {error_message}")
        self.clear()
        error_label = QLabel(f"Failed to load cast: {error_message}")
        error_label.setAlignment(Qt.AlignCenter)
        error_label.setStyleSheet("color: red; font-size: 12px;")
        self.cast_layout.addWidget(error_label)

    def clear(self):
        while self.cast_layout.count():
            item = self.cast_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            else:
                sub_layout = item.layout()
                if sub_layout is not None:
                    self._clear_layout(sub_layout)

    def set_cast(self, cast_data):
        """Set the cast data and populate the widget."""
        print(f"[CastWidget] set_cast called with {len(cast_data) if cast_data else 0} cast members")
        
        # Clear any loading indicators
        self.clear()
        
        if not cast_data:
            no_cast_label = QLabel(self.translations.get("No cast information available", "No cast information available"))
            no_cast_label.setAlignment(Qt.AlignCenter)
            no_cast_label.setStyleSheet("color: gray; font-size: 12px;")
            self.cast_layout.addWidget(no_cast_label)
            return
        
        # Ensure widget is visible
        self.setVisible(True)
        if self.parent():
            self.parent().setVisible(True)
        MAX_CAST_MEMBERS = 24
        placeholder_pixmap = QPixmap('assets/person.png')
        if placeholder_pixmap.isNull():
            placeholder_pixmap = QPixmap(125, 188)
            placeholder_pixmap.fill(Qt.lightGray)
        loading_counter = {'count': 0}
        for i, member in enumerate(cast_data):
            if i >= MAX_CAST_MEMBERS:
                break
            member_name = member.get('name', 'N/A')
            character_name = member.get('character', '')
            profile_path = member.get('profile_path')
            gender = member.get('gender', 0)
            if gender == 2:
                gender_placeholder = QPixmap('assets/actor.png')
            elif gender == 1:
                gender_placeholder = QPixmap('assets/actress.png')
            else:
                gender_placeholder = QPixmap('assets/person.png')
            if gender_placeholder.isNull():
                gender_placeholder = QPixmap(125, 188)
                gender_placeholder.fill(Qt.lightGray)
            item_widget = QWidget()
            item_layout = QVBoxLayout(item_widget)
            item_layout.setContentsMargins(5, 5, 5, 5)
            item_layout.setSpacing(2)
            poster_with_overlay_container = QWidget()
            poster_with_overlay_container.setFixedSize(125, 188)
            poster_label = QLabel(poster_with_overlay_container)
            poster_label.setGeometry(0, 0, 125, 188)
            poster_label.setAlignment(Qt.AlignCenter)
            if profile_path:
                full_image_url = f"https://image.tmdb.org/t/p/w185{profile_path}"
                load_image_async(full_image_url, poster_label, gender_placeholder.scaled(125, 188, Qt.KeepAspectRatio, Qt.SmoothTransformation), update_size=(125,188), main_window=self.main_window, loading_counter=loading_counter)
            else:
                poster_label.setPixmap(gender_placeholder.scaled(125, 188, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            overlay_height = 35
            name_overlay_widget = QWidget(poster_with_overlay_container)
            name_overlay_widget.setGeometry(0, 188 - overlay_height, 125, overlay_height)
            name_overlay_widget.setStyleSheet("background-color: rgba(0, 0, 0, 180);")
            name_overlay_layout = QVBoxLayout()
            name_overlay_layout.setContentsMargins(2, 2, 2, 2)
            name_overlay_layout.setAlignment(Qt.AlignCenter)
            actor_name_label = QLabel(member_name)
            actor_name_label.setAlignment(Qt.AlignCenter)
            actor_name_label.setWordWrap(True)
            actor_name_label.setFont(QFont('Arial', 14))
            actor_name_label.setStyleSheet("color: white; background-color: transparent;")
            name_overlay_layout.addWidget(actor_name_label)
            name_overlay_widget.setLayout(name_overlay_layout)
            item_layout.addWidget(poster_with_overlay_container)
            if character_name:
                character_label = QLabel(f"as {character_name}")
                character_label.setFixedWidth(125)
                character_label.setAlignment(Qt.AlignCenter)
                character_label.setWordWrap(True)
                character_label.setFont(QFont('Arial', 10, italic=True))
                character_label.setStyleSheet("color: lightgray;")
                item_layout.addWidget(character_label)
            item_layout.addStretch(1)
            item_widget.setFixedWidth(135)
            item_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.cast_layout.addWidget(item_widget)
        
        # Add stretch to push cast members to the left
        self.cast_layout.addStretch()
