from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton
from PyQt5.QtGui import QPixmap, QFont

class MovieDetailsWidget(QWidget):
    favorite_toggled = pyqtSignal(object)
    play_clicked = pyqtSignal(object)
    trailer_clicked = pyqtSignal(str)

    def __init__(self, movie, is_favorite=False, parent=None):
        super().__init__(parent)
        self.movie = movie
        self._is_favorite = is_favorite
        self.setup_ui()

    def setup_ui(self):
        from src.ui.tabs.movies_tab import load_image_async  # moved import here to avoid circular import
        layout = QHBoxLayout(self)
        # --- Left: Poster and Back button ---
        left_layout = QVBoxLayout()
        self.back_btn = QPushButton("← Back")
        self.back_btn.setFixedWidth(80)
        left_layout.addWidget(self.back_btn, alignment=Qt.AlignLeft)
        # Poster
        self.poster = QLabel()
        self.poster.setAlignment(Qt.AlignTop)
        if self.movie.get('stream_icon'):
            load_image_async(self.movie['stream_icon'], self.poster, QPixmap('assets/movies.png'), update_size=(180, 260))
        else:
            self.poster.setPixmap(QPixmap('assets/movies.png').scaled(180, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        left_layout.addWidget(self.poster)
        # --- Favorites button under poster ---
        self.favorite_btn = QPushButton()
        self.favorite_btn.setFont(QFont('Arial', 16))
        self.favorite_btn.setStyleSheet("QPushButton { background: transparent; }")
        self.update_favorite_btn()
        self.favorite_btn.clicked.connect(self._on_favorite_clicked)
        left_layout.addWidget(self.favorite_btn, alignment=Qt.AlignHCenter)
        layout.addLayout(left_layout)
        # --- Right: Metadata and actions ---
        right_layout = QVBoxLayout()
        title = QLabel(self.movie.get('name', ''))
        title.setFont(QFont('Arial', 16, QFont.Bold))
        right_layout.addWidget(title)
        self.meta = QLabel()
        self.meta.setText(f"Year: {self.movie.get('year', '--')} | Genre: {self.movie.get('genre', '--')} | Duration: {self.movie.get('duration', '--')} min")
        right_layout.addWidget(self.meta)
        rating = self.movie.get('rating', '--')
        if rating and rating != '--':
            right_layout.addWidget(QLabel(f"User's rating: ★ {rating}"))
        self.desc = QTextEdit(self.movie.get('plot', ''))
        self.desc.setReadOnly(True)
        self.desc.setMaximumHeight(80)
        right_layout.addWidget(self.desc)
        cast_photos = self.movie.get('cast_photos', [])
        cast = self.movie.get('cast', '--')
        if cast_photos:
            cast_layout = QHBoxLayout()
            for cast_member in cast_photos:
                vbox = QVBoxLayout()
                photo_label = QLabel()
                if cast_member.get('photo_url'):
                    load_image_async(cast_member['photo_url'], photo_label, QPixmap(), update_size=(48, 48))
                name_label = QLabel(cast_member.get('name', ''))
                name_label.setAlignment(Qt.AlignCenter)
                vbox.addWidget(photo_label)
                vbox.addWidget(name_label)
                cast_layout.addLayout(vbox)
            right_layout.addLayout(cast_layout)
        elif cast and cast != '--':
            right_layout.addWidget(QLabel(f"Cast: {cast}"))
        btn_layout = QHBoxLayout()
        self.play_btn = QPushButton("PLAY")
        self.play_btn.clicked.connect(lambda: self.play_clicked.emit(self.movie))
        btn_layout.addWidget(self.play_btn)
        trailer_url = self.movie.get('trailer_url')
        if trailer_url:
            self.trailer_btn = QPushButton("WATCH TRAILER")
            self.trailer_btn.clicked.connect(lambda: self.trailer_clicked.emit(trailer_url))
            btn_layout.addWidget(self.trailer_btn)
        right_layout.addLayout(btn_layout)
        layout.addLayout(right_layout)

    def set_favorite(self, is_favorite):
        self._is_favorite = is_favorite
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
        self.favorite_toggled.emit(self.movie)
