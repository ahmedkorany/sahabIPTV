"""
Media player widget for the application
"""
import sys
import vlc
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFrame
from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QEvent
from src.ui.widgets.controls import PlayerControls
from src.config import DEFAULT_VOLUME

class MediaPlayer(QWidget):
    """Media player widget using VLC"""
    playback_started = pyqtSignal()
    playback_stopped = pyqtSignal()
    playback_error = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_player()
        
        # Timer for updating the player state
        self.update_timer = QTimer(self)
        self.update_timer.setInterval(1000)  # Update every second
        self.update_timer.timeout.connect(self.update_player_state)
        self.play_started = False
        self.old_parent = None
        self.old_geometry = None
        
        self.is_fullscreen = False
        self.normal_parent = None
        self.normal_geometry = None
        self.normal_layout_position = None
        self.fullscreen_window = None

    def setup_ui(self):
        """Set up the UI components"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Video frame
        self.video_frame = QFrame()
        self.video_frame.setFrameShape(QFrame.StyledPanel)
        self.video_frame.setFrameShadow(QFrame.Raised)
        self.video_frame.setStyleSheet("background-color: black;")
        self.video_frame.installEventFilter(self)
        self.video_frame.setFocusPolicy(Qt.StrongFocus)
        
        # Player controls
        self.controls = PlayerControls()
        self.controls.play_pause_clicked.connect(self.play_pause)
        self.controls.stop_clicked.connect(self.stop)
        self.controls.seek_changed.connect(self.seek)
        self.controls.volume_changed.connect(self.set_volume)
        self.controls.mute_clicked.connect(self.set_mute)
        self.controls.fullscreen_clicked.connect(self.toggle_fullscreen)
        self.controls.speed_changed.connect(self.set_playback_rate)
        
        layout.addWidget(self.video_frame, 1)
        layout.addWidget(self.controls)
    
    def setup_player(self):
        """Set up the VLC player"""
        # Create VLC instance
        self.instance = vlc.Instance('--no-xlib')
        
        # Create player
        self.player = self.instance.media_player_new()
        
        # Set player to video frame
        if sys.platform == "linux" or sys.platform == "linux2":
            self.player.set_xwindow(self.video_frame.winId())
        elif sys.platform == "win32":
            self.player.set_hwnd(self.video_frame.winId())
        elif sys.platform == "darwin":
            self.player.set_nsobject(int(self.video_frame.winId()))
        
        # Set initial volume
        self.player.audio_set_volume(DEFAULT_VOLUME)
        self.controls.set_volume(DEFAULT_VOLUME)
    def play(self, url):
        """Play media from URL"""
        try:
            # Create media
            media = self.instance.media_new(url)
            
            # Set media to player
            self.player.set_media(media)
            
            # Play
            self.player.play()
            
            # Start update timer
            self.update_timer.start()
            
            # Update controls
            self.controls.set_playing(True)
            
            # Emit signal
            self.playback_started.emit()
            self.play_started = True
            return True
        except Exception as e:
            self.playback_error.emit(str(e))
            return False
    
    def play_pause(self, play):
        """Play or pause playback"""
        if play:
            self.player.play()
            self.update_timer.start()
        else:
            self.player.pause()
    
    def stop(self):
        """Stop playback"""
        self.player.stop()
        self.update_timer.stop()
        self.controls.set_playing(False)
        self.controls.set_current_time(0)
        self.playback_stopped.emit()
        self.play_started = False
    
    def seek(self, time):
        """Seek to specific time in seconds"""
        self.player.set_time(time * 1000)  # VLC uses milliseconds
    
    def set_volume(self, volume):
        """Set volume level (0-100)"""
        self.player.audio_set_volume(volume)
    
    def set_mute(self, mute):
        """Mute or unmute audio"""
        self.player.audio_set_mute(mute)
    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == Qt.Key_Escape and self.video_frame.isFullScreen():
            # Exit fullscreen mode when Escape is pressed
            print("Escape pressed")
            self.controls.set_fullscreen(False)
            self.toggle_fullscreen(False)
        else:
            super().keyPressEvent(event)
    
    def toggle_fullscreen(self, fullscreen):
        """Toggle fullscreen mode"""
        if fullscreen and not self.is_fullscreen:
            # Going to fullscreen
            self.enter_fullscreen()
        elif not fullscreen and self.is_fullscreen:
            # Exiting fullscreen
            self.exit_fullscreen()

    def enter_fullscreen(self):
        """Enter fullscreen mode"""
        if self.is_fullscreen:
            return
            
        # Save current state
        self.normal_parent = self.video_frame.parentWidget()
        self.normal_geometry = self.video_frame.geometry()
        
        # Detach the video frame from its parent
        self.video_frame.setParent(None)
        
        # Set window flags for proper fullscreen behavior
        self.video_frame.setWindowFlags(Qt.Window)
        
        # Show fullscreen
        self.video_frame.showFullScreen()
        self.video_frame.setFocus()
        
        # Update VLC player to use the new window
        if sys.platform == "linux" or sys.platform == "linux2":
            self.player.set_xwindow(self.video_frame.winId())
        elif sys.platform == "win32":
            self.player.set_hwnd(self.video_frame.winId())
        elif sys.platform == "darwin":
            self.player.set_nsobject(int(self.video_frame.winId()))
        
        self.is_fullscreen = True
        self.controls.set_fullscreen(True)
        
        # Install event filter to catch Escape key
        self.video_frame.installEventFilter(self)

        # Show ESC message overlay
        self.show_esc_message()
        # Show controls overlay initially
        self.show_controls_overlay()

    def show_esc_message(self):
        """Display 'Press ESC to return to normal view' overlay for 5 seconds in fullscreen."""
        from PyQt5.QtCore import QTimer, Qt
        # Remove previous message if exists
        if hasattr(self, '_esc_message_label') and self._esc_message_label:
            self._esc_message_label.deleteLater()
            self._esc_message_label = None
        self._esc_message_label = QLabel(self.video_frame)
        self._esc_message_label.setText("<b>Press ESC to return to normal view</b>")
        self._esc_message_label.setStyleSheet(
            "background: rgba(0,0,0,0.7); color: white; padding: 16px 32px; border-radius: 8px; font-size: 20px;"
        )
        self._esc_message_label.setAlignment(Qt.AlignCenter)
        self._esc_message_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._esc_message_label.setWindowFlags(Qt.FramelessWindowHint | Qt.ToolTip)
        self._esc_message_label.resize(self.video_frame.size())
        self._esc_message_label.move(0, int(self.video_frame.height() * 0.4))
        self._esc_message_label.show()
        self._esc_message_label.raise_()
        # Resize with video_frame
        self.video_frame.installEventFilter(self)
        # Hide after 5 seconds
        QTimer.singleShot(5000, self._esc_message_label.hide)

    def show_controls_overlay(self):
        """Show play controls overlay in fullscreen mode."""
        from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton
        from PyQt5.QtCore import Qt, QTimer
        # Remove previous overlay if exists
        if hasattr(self, '_controls_overlay') and self._controls_overlay:
            self._controls_overlay.deleteLater()
            self._controls_overlay = None
        overlay = QWidget(self.video_frame)
        overlay.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        overlay.setWindowFlags(Qt.FramelessWindowHint | Qt.ToolTip)
        overlay.setStyleSheet("background: rgba(0,0,0,0.5); border-radius: 12px;")
        layout = QHBoxLayout(overlay)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(30)
        # Play/Pause
        is_playing = self.is_playing()
        # Use a Unicode triangle for Play and a double bar for Pause
        play_icon = "\u25B6"  # Unicode black right-pointing triangle
        pause_icon = "||"  # Unicode double vertical bar
        play_pause_btn = QPushButton(play_icon if not is_playing else pause_icon)
        play_pause_btn.setToolTip("Pause" if is_playing else "Play")
        play_pause_btn.setFixedSize(48, 48)
        play_pause_btn.setStyleSheet("font-size: 36px; background: #222; color: #fff; border-radius: 24px;")
        def toggle_play_pause():
            if self.is_playing():
                self.play_pause(False)
            else:
                self.play_pause(True)
            # Refresh overlay to update icon
            self.show_controls_overlay()
        play_pause_btn.clicked.connect(toggle_play_pause)
        layout.addWidget(play_pause_btn)
        # Stop
        stop_btn = QPushButton("⏹")
        stop_btn.setToolTip("Stop")
        stop_btn.setFixedSize(48, 48)
        stop_btn.setStyleSheet("font-size: 28px; background: #222; color: #fff; border-radius: 24px;")
        def stop_and_exit():
            self.stop()
            self.exit_fullscreen()
        stop_btn.clicked.connect(stop_and_exit)
        layout.addWidget(stop_btn)
        # Fast backward
        back_btn = QPushButton("⏪")
        back_btn.setToolTip("Fast Backward")
        back_btn.setFixedSize(48, 48)
        back_btn.setStyleSheet("font-size: 28px; background: #222; color: #fff; border-radius: 24px;")
        back_btn.clicked.connect(lambda: self.seek(max(0, self.player.get_time()//1000 - 10)))
        layout.addWidget(back_btn)
        # Fast forward
        forward_btn = QPushButton("⏩")
        forward_btn.setToolTip("Fast Forward")
        forward_btn.setFixedSize(48, 48)
        forward_btn.setStyleSheet("font-size: 28px; background: #222; color: #fff; border-radius: 24px;")
        forward_btn.clicked.connect(lambda: self.seek(self.player.get_time()//1000 + 10))
        layout.addWidget(forward_btn)
        # Position overlay at bottom center
        overlay.resize(min(400, self.video_frame.width()-40), 80)
        overlay.move((self.video_frame.width() - overlay.width()) // 2, self.video_frame.height() - overlay.height() - 40)
        overlay.show()
        overlay.raise_()
        self._controls_overlay = overlay
        # Hide after 3 seconds if no interaction
        if hasattr(self, '_controls_overlay_timer') and self._controls_overlay_timer:
            self._controls_overlay_timer.stop()
        self._controls_overlay_timer = QTimer(self.video_frame)
        self._controls_overlay_timer.setSingleShot(True)
        self._controls_overlay_timer.timeout.connect(overlay.hide)
        self._controls_overlay_timer.start(3000)

    def exit_fullscreen(self):
        """Exit fullscreen mode"""
        if not self.is_fullscreen:
            return
        
        # Exit fullscreen mode
        self.video_frame.setWindowFlags(Qt.Widget)
        
        # Reparent video frame back to the original parent
        if self.normal_parent:
            # Get the layout of the normal parent
            parent_layout = self.layout()
            
            # Add video frame back to the original layout
            parent_layout.insertWidget(0, self.video_frame, 1)
            
            # Make sure the video frame is visible
            self.video_frame.show()
            
            # Update VLC player
            if sys.platform == "linux" or sys.platform == "linux2":
                self.player.set_xwindow(self.video_frame.winId())
            elif sys.platform == "win32":
                self.player.set_hwnd(self.video_frame.winId())
            elif sys.platform == "darwin":
                self.player.set_nsobject(int(self.video_frame.winId()))
        
        self.is_fullscreen = False
        self.controls.set_fullscreen(False)
        
        # Remove event filter
        self.video_frame.removeEventFilter(self)

    
    def eventFilter(self, obj, event):
        from PyQt5.QtCore import QEvent
        # Use hasattr to avoid AttributeError if is_fullscreen is not set yet
        is_fullscreen = getattr(self, 'is_fullscreen', False)
        if event.type() == QEvent.KeyPress and event.key() == Qt.Key_Escape:
            self.exit_fullscreen()
            return True
        # Resize overlays if video_frame is resized
        if obj == self.video_frame and event.type() == QEvent.Resize:
            if hasattr(self, '_esc_message_label') and self._esc_message_label and self._esc_message_label.isVisible():
                self._esc_message_label.resize(self.video_frame.size())
                self._esc_message_label.move(0, int(self.video_frame.height() * 0.4))
            if hasattr(self, '_controls_overlay') and self._controls_overlay and self._controls_overlay.isVisible():
                self._controls_overlay.resize(min(400, self.video_frame.width()-40), 80)
                self._controls_overlay.move((self.video_frame.width() - self._controls_overlay.width()) // 2, self.video_frame.height() - self._controls_overlay.height() - 40)
        # Show controls overlay on mouse click in fullscreen
        if obj == self.video_frame and is_fullscreen and event.type() == QEvent.MouseButtonPress:
            self.show_controls_overlay()
            return True
        return super().eventFilter(obj, event)
    
    def set_playback_rate(self, rate):
        """Set playback speed rate"""
        self.player.set_rate(rate)
    
    def update_player_state(self):
        """Update player state and controls"""
        # Update time
        time = self.player.get_time() // 1000  # Convert to seconds
        self.controls.set_current_time(time)
        
        # Update duration if not set
        if self.controls.duration == 0:
            duration = self.player.get_length() // 1000  # Convert to seconds
            if duration > 0:
                self.controls.set_duration(duration)
        
        # Check if playback ended
        if not self.player.is_playing() and self.controls.is_playing:
            state = self.player.get_state()
            if state == vlc.State.Ended:
                self.stop()
    
    def is_playing(self):
        """Check if player is currently playing"""
        return self.player.is_playing()
