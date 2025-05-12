"""
Media player widget for the application
"""
import sys
import vlc
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFrame
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
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
    
    def toggle_fullscreen(self, fullscreen):
        """Toggle fullscreen mode"""
        self.player.set_fullscreen(fullscreen)
    
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
