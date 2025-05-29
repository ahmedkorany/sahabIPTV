"""Media player controls widget"""
from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QPushButton, 
                            QSlider, QLabel, QComboBox, QStyle)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QIcon, QFont
from src.config import SEEK_STEP, DEFAULT_VOLUME, ICON_SIZE
from src.utils.helpers import format_duration, get_translations

class PlayerControls(QWidget):
    """Media player controls widget"""
    play_pause_clicked = pyqtSignal(bool)  # True for play, False for pause
    stop_clicked = pyqtSignal()
    seek_changed = pyqtSignal(int)
    volume_changed = pyqtSignal(int)
    mute_clicked = pyqtSignal(bool)  # True for mute, False for unmute
    fullscreen_clicked = pyqtSignal(bool)  # True for fullscreen, False for windowed
    speed_changed = pyqtSignal(float)
    favorite_clicked = pyqtSignal(bool)  # True for add to favorites, False for remove from favorites
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_playing = False
        self.is_muted = False
        self.is_fullscreen = False
        self.is_favorite = False
        self.duration = 0
        self.current_time = 0
        # Get translations from parent or default to English
        language = getattr(parent, 'language', 'en') if hasattr(parent, 'language') else 'en'
        self.translations = get_translations(language)
        self.setup_ui()
        
        # Timer for updating the seek slider
        self.timer = QTimer(self)
        self.timer.setInterval(1000)  # Update every second
        self.timer.timeout.connect(self.update_ui)
    
    def setup_ui(self):
        """Set up the UI components"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Seek slider
        seek_layout = QHBoxLayout()
        self.current_time_label = QLabel("00:00")
        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.setRange(0, 100)
        self.seek_slider.setValue(0)
        self.seek_slider.setTracking(False)
        self.seek_slider.sliderMoved.connect(self.seek_slider_moved)
        self.seek_slider.sliderReleased.connect(self.seek_slider_released)
        self.duration_label = QLabel("00:00")
        
        seek_layout.addWidget(self.current_time_label)
        seek_layout.addWidget(self.seek_slider)
        seek_layout.addWidget(self.duration_label)
        
        # Control buttons
        controls_layout = QHBoxLayout()
        
        self.play_pause_button = QPushButton()
        self.play_pause_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.play_pause_button.setIconSize(ICON_SIZE)
        self.play_pause_button.clicked.connect(self.play_pause_clicked_handler)
        
        self.stop_button = QPushButton()
        self.stop_button.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        self.stop_button.setIconSize(ICON_SIZE)
        self.stop_button.clicked.connect(self.stop_clicked)
        
        self.rewind_button = QPushButton()
        self.rewind_button.setIcon(self.style().standardIcon(QStyle.SP_MediaSeekBackward))
        self.rewind_button.setIconSize(ICON_SIZE)
        self.rewind_button.clicked.connect(self.rewind_clicked)
        
        self.forward_button = QPushButton()
        self.forward_button.setIcon(self.style().standardIcon(QStyle.SP_MediaSeekForward))
        self.forward_button.setIconSize(ICON_SIZE)
        self.forward_button.clicked.connect(self.forward_clicked)
        
        self.mute_button = QPushButton()
        self.mute_button.setIcon(self.style().standardIcon(QStyle.SP_MediaVolume))
        self.mute_button.setIconSize(ICON_SIZE)
        self.mute_button.clicked.connect(self.mute_clicked_handler)
        
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(DEFAULT_VOLUME)
        self.volume_slider.valueChanged.connect(self.volume_changed)
        self.volume_slider.setMaximumWidth(100)
        
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.25x", "0.5x", "0.75x", "1.0x", "1.25x", "1.5x", "2.0x"])
        self.speed_combo.setCurrentIndex(3)  # 1.0x is default
        self.speed_combo.currentIndexChanged.connect(self.speed_changed_handler)
        
        self.fullscreen_button = QPushButton()
        self.fullscreen_button.setIcon(self.style().standardIcon(QStyle.SP_TitleBarMaxButton))
        self.fullscreen_button.setIconSize(ICON_SIZE)
        self.fullscreen_button.clicked.connect(self.fullscreen_clicked_handler)
        
        # Favorite button
        self.favorite_button = QPushButton()
        self.favorite_button.setText("☆")
        self.favorite_button.setFont(QFont('Arial', 16))
        self.favorite_button.setStyleSheet("QPushButton { color: white; background: transparent; }")
        self.favorite_button.setToolTip(self.translations.get("Add to favorites", "Add to favorites"))
        self.favorite_button.clicked.connect(self.favorite_clicked_handler)
        
        controls_layout.addWidget(self.play_pause_button)
        controls_layout.addWidget(self.stop_button)
        controls_layout.addWidget(self.rewind_button)
        controls_layout.addWidget(self.forward_button)
        controls_layout.addStretch()
        controls_layout.addWidget(QLabel(self.translations.get("Speed", "Speed:")))
        controls_layout.addWidget(self.speed_combo)
        controls_layout.addStretch()
        controls_layout.addWidget(self.mute_button)
        controls_layout.addWidget(self.volume_slider)
        controls_layout.addWidget(self.favorite_button)
        controls_layout.addWidget(self.fullscreen_button)
        
        main_layout.addLayout(seek_layout)
        main_layout.addLayout(controls_layout)
        
        # Set play control buttons (play, stop, fast forward, backward) to white (icon and text)
        for btn in [self.play_pause_button, self.stop_button, self.rewind_button, self.forward_button, self.fullscreen_button, self.favorite_button]:
            btn.setStyleSheet("color: white; background: transparent;")
            icon = btn.icon()
            if not icon.isNull():
                pixmap = icon.pixmap(btn.iconSize())
                from PyQt5.QtGui import QPainter, QColor
                white_pixmap = pixmap.copy()
                painter = QPainter(white_pixmap)
                painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
                painter.fillRect(white_pixmap.rect(), QColor('white'))
                painter.end()
                btn.setIcon(QIcon(white_pixmap))

    def play_pause_clicked_handler(self):
        """Handle play/pause button click"""
        self.is_playing = not self.is_playing
        self.update_play_pause_button()
        self.play_pause_clicked.emit(self.is_playing)
        
        if self.is_playing:
            self.timer.start()
        else:
            self.timer.stop()
    
    def update_play_pause_button(self):
        """Update play/pause button icon based on state"""
        from PyQt5.QtGui import QPainter, QColor
        if self.is_playing:
            icon = self.style().standardIcon(QStyle.SP_MediaPause)
        else:
            icon = self.style().standardIcon(QStyle.SP_MediaPlay)
        pixmap = icon.pixmap(self.play_pause_button.iconSize())
        white_pixmap = pixmap.copy()
        painter = QPainter(white_pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(white_pixmap.rect(), QColor('white'))
        painter.end()
        self.play_pause_button.setIcon(QIcon(white_pixmap))
    
    def mute_clicked_handler(self):
        """Handle mute button click"""
        self.is_muted = not self.is_muted
        self.update_mute_button()
        self.mute_clicked.emit(self.is_muted)
    
    def update_mute_button(self):
        """Update mute button icon based on state"""
        if self.is_muted:
            self.mute_button.setIcon(self.style().standardIcon(QStyle.SP_MediaVolumeMuted))
        else:
            self.mute_button.setIcon(self.style().standardIcon(QStyle.SP_MediaVolume))
    
    def fullscreen_clicked_handler(self):
        """Handle fullscreen button click"""
        self.is_fullscreen = not self.is_fullscreen
        self.update_fullscreen_button()
        self.fullscreen_clicked.emit(self.is_fullscreen)
    
    def update_fullscreen_button(self):
        """Update fullscreen button icon based on state"""
        if self.is_fullscreen:
            self.fullscreen_button.setIcon(self.style().standardIcon(QStyle.SP_TitleBarNormalButton))
        else:
            self.fullscreen_button.setIcon(self.style().standardIcon(QStyle.SP_TitleBarMaxButton))
    
    def favorite_clicked_handler(self):
        """Handle favorite button click"""
        self.is_favorite = not self.is_favorite
        self.update_favorite_button()
        self.favorite_clicked.emit(self.is_favorite)
    
    def update_favorite_button(self):
        """Update favorite button icon based on state"""
        # Create star icon (filled or outline)
        if self.is_favorite:
            # Use a filled star with yellow color
            self.favorite_button.setStyleSheet("QPushButton { color: gold; background: transparent; }")
            self.favorite_button.setText("★")
            self.favorite_button.setFont(QFont('Arial', 16))
            self.favorite_button.setToolTip(self.translations.get("Remove from favorites", "Remove from favorites"))
        else:
            # Use an outline star with white color
            self.favorite_button.setStyleSheet("QPushButton { color: white; background: transparent; }")
            self.favorite_button.setText("☆")
            self.favorite_button.setFont(QFont('Arial', 16))
            self.favorite_button.setToolTip(self.translations.get("Add to favorites", "Add to favorites"))
    
    def set_favorite(self, is_favorite):
        """Set favorite state"""
        if self.is_favorite != is_favorite:
            self.is_favorite = is_favorite
            self.update_favorite_button()
    
    def rewind_clicked(self):
        """Handle rewind button click"""
        new_time = max(0, self.current_time - SEEK_STEP)
        self.seek_changed.emit(new_time)
    
    def forward_clicked(self):
        """Handle forward button click"""
        new_time = min(self.duration, self.current_time + SEEK_STEP)
        self.seek_changed.emit(new_time)
    
    def seek_slider_moved(self, position):
        """Handle seek slider moved"""
        if self.duration > 0:
            self.current_time_label.setText(format_duration(int(position * self.duration / 100)))
    
    def seek_slider_released(self):
        """Handle seek slider released"""
        if self.duration > 0:
            position = self.seek_slider.value()
            time = int(position * self.duration / 100)
            self.seek_changed.emit(time)
    
    def speed_changed_handler(self, index):
        """Handle speed combo box change"""
        speed_text = self.speed_combo.currentText()
        speed = float(speed_text.replace('x', ''))
        self.speed_changed.emit(speed)
    
    def set_duration(self, duration):
        """Set the media duration"""
        self.duration = duration
        self.duration_label.setText(format_duration(duration))
    
    def set_current_time(self, time):
        """Set the current playback time"""
        self.current_time = time
        self.current_time_label.setText(format_duration(time))
        
        if self.duration > 0:
            position = int(time * 100 / self.duration)
            self.seek_slider.setValue(position)
    
    def set_playing(self, is_playing):
        """Set the playing state"""
        self.is_playing = is_playing
        self.update_play_pause_button()
        
        if self.is_playing:
            self.timer.start()
        else:
            self.timer.stop()
    
    def set_muted(self, is_muted):
        """Set the muted state"""
        self.is_muted = is_muted
        self.update_mute_button()
    
    def set_volume(self, volume):
        """Set the volume level"""
        self.volume_slider.setValue(volume)
    
    def set_fullscreen(self, is_fullscreen):
        """Set the fullscreen state"""
        self.is_fullscreen = is_fullscreen
        self.update_fullscreen_button()
    
    def update_ui(self):
        """Update UI based on current playback state"""
        # This method is called by the timer and should be overridden
        # by the parent class to update the current time
        pass
