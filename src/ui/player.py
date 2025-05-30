"""
Media player widget for the application
"""
import sys
import os # Added
import vlc
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFrame
from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from src.ui.widgets.controls import PlayerControls
from src.config import DEFAULT_VOLUME
from PyQt5.QtWidgets import QMainWindow
from src.utils.youtube_resolver import youtube_resolver
from src.utils.helpers import get_translations

class MediaPlayer(QWidget):
    """Media player widget using VLC"""
    playback_started = pyqtSignal()
    playback_stopped = pyqtSignal()
    playback_error = pyqtSignal(str)
    add_to_favorites = pyqtSignal(dict)  # Signal to add current item to favorites
    playback_position_updated = pyqtSignal(str, int, int) # Added: stream_id, position_ms, duration_ms
    
    def __init__(self, parent=None, favorites_manager=None):
        super().__init__(parent)
        # Get translations from parent or default to English
        language = getattr(parent, 'language', 'en') if parent else 'en'
        self.translations = get_translations(language)
        self.setup_ui()
        self.setup_player()
        self._pending_start_time_ms = 0
        
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
        
        # Current media item being played
        self.current_item = None
        self.is_favorite = False
        
        # Favorites manager for direct dependency injection
        self.favorites_manager = favorites_manager

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
        self.controls.favorite_clicked.connect(self.toggle_favorite)
        
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

        # Attach to events
        self.vlc_event_manager = self.player.event_manager()
        self.vlc_event_manager.event_attach(vlc.EventType.MediaPlayerPlaying, self._on_media_player_playing, self.player)
        
        # Set initial volume
        self.player.audio_set_volume(DEFAULT_VOLUME)
        self.controls.set_volume(DEFAULT_VOLUME)

    def play(self, media_source, item=None, start_position_ms=0):
        """Play media from URL or local file path"""
        try:
            self.current_item = item
            self._pending_start_time_ms = start_position_ms

            if item is not None:
                self.is_favorite = self.check_if_favorite(item)
                self.controls.set_favorite(self.is_favorite)
            else:
                self.is_favorite = False
                self.controls.set_favorite(False)

            media = None
            if isinstance(media_source, str) and media_source.startswith(('http://', 'https://', 'rtmp://', 'rtsp://')):
                resolved_media_source = youtube_resolver.resolve_url(media_source)
                print(f"[MediaPlayer] Playing URL: {resolved_media_source}")
                media = self.instance.media_new(resolved_media_source)
            elif isinstance(media_source, str) and os.path.exists(media_source):
                print(f"[MediaPlayer] Playing local file: {media_source}")
                media = self.instance.media_new_path(media_source)
            else:
                error_msg = f"Invalid media source: {media_source}"
                print(f"[MediaPlayer] {error_msg}")
                self.playback_error.emit(error_msg)
                return False

            if not media:
                error_msg = f"Could not create media from source: {media_source}"
                print(f"[MediaPlayer] {error_msg}")
                self.playback_error.emit(error_msg)
                return False

            self.player.set_media(media)
            media.release()
            
            self.player.play()
            self.update_timer.start()
            self.controls.set_playing(True)
            self.playback_started.emit()
            self.play_started = True
            return True

        except Exception as e:
            self.playback_error.emit(str(e))
            print(f"[MediaPlayer] Error in play: {e}")
            return False

    def _on_media_player_playing(self, event, player_instance):
        if self._pending_start_time_ms > 0 and player_instance == self.player:
            # Ensure player is in a good state and media has duration
            if self.player.get_length() > 0 : # get_length() returns msec
                self.player.set_time(self._pending_start_time_ms)
                print(f"[MediaPlayer] Event: MediaPlayerPlaying - Seeked to {self._pending_start_time_ms} ms")
                self._pending_start_time_ms = 0 # Reset after seeking
            else:
                # If duration is not yet known, try again with a short delay
                QTimer.singleShot(200, lambda: self._ensure_seek_after_playing(self._pending_start_time_ms))

    def _ensure_seek_after_playing(self, time_ms):
       if time_ms > 0 and (self.player.is_playing() or self.player.get_state() == vlc.State.Playing):
           if self.player.get_length() > 0:
               self.player.set_time(time_ms)
               print(f"[MediaPlayer] Seek (ensure_seek): Seeked to {time_ms} ms")
               if self._pending_start_time_ms == time_ms: # Clear if this was the pending one
                    self._pending_start_time_ms = 0
           else:
               # Still no length, this is problematic. Log it.
               print(f"[MediaPlayer] Warning: Could not seek to {time_ms}ms, media length unknown even after playing.")
               if self._pending_start_time_ms == time_ms: # Avoid repeated attempts
                    self._pending_start_time_ms = 0
       elif time_ms > 0 : # Not playing or in a valid seekable state, clear pending time
            print(f"[MediaPlayer] Warning: Player not in seekable state for time {time_ms}ms. Clearing pending seek.")
            if self._pending_start_time_ms == time_ms:
                self._pending_start_time_ms = 0


    def check_if_favorite(self, item):
        """Check if the current item is in favorites"""
        if self.favorites_manager and item:
            return self.favorites_manager.is_favorite(item)
        return False
        
    def toggle_favorite(self, add_to_favorites):
        """Toggle favorite status for current item"""
        if self.current_item is None:
            print("[DEBUG] toggle_favorite called but current_item is None")
            return
        print(f"[DEBUG] toggle_favorite: add_to_favorites={add_to_favorites}, current_item={self.current_item}")
        
        if self.favorites_manager:
            if add_to_favorites:
                # Add to favorites
                self.favorites_manager.add_to_favorites(self.current_item)
            else:
                # Remove from favorites
                self.favorites_manager.remove_from_favorites(self.current_item)
        else:
            # Fallback: emit signal for backward compatibility
            if add_to_favorites:
                self.add_to_favorites.emit(self.current_item)
    
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
        # Create a new top-level window for fullscreen
        from PyQt5.QtWidgets import QMainWindow, QApplication
        screen = QApplication.primaryScreen().geometry()
        self.fullscreen_window = QMainWindow()
        self.fullscreen_window.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.fullscreen_window.setGeometry(screen)
        self.fullscreen_window.setCentralWidget(self.video_frame)
        self.fullscreen_window.showFullScreen()
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
        self.video_frame.installEventFilter(self)
        self.show_esc_message()
        self.show_controls_overlay()

    def show_esc_message(self):
        """Display 'Press ESC to return to normal view' overlay for 5 seconds in fullscreen."""
        from PyQt5.QtCore import QTimer, Qt
        # Remove previous message if exists
        if hasattr(self, '_esc_message_label') and self._esc_message_label:
            self._esc_message_label.deleteLater()
            self._esc_message_label = None
        self._esc_message_label = QLabel(self.video_frame)
        self._esc_message_label.setText(f"<b>{self.translations.get('Press ESC to return to normal view', 'Press ESC to return to normal view')}</b>")
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
        play_pause_btn.setToolTip(self.translations.get("Pause", "Pause") if is_playing else self.translations.get("Play", "Play"))
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
        stop_btn.setToolTip(self.translations.get("Stop", "Stop"))
        stop_btn.setFixedSize(48, 48)
        stop_btn.setStyleSheet("font-size: 28px; background: #222; color: #fff; border-radius: 24px;")
        def stop_and_exit():
            self.stop()
            self.exit_fullscreen()
        stop_btn.clicked.connect(stop_and_exit)
        layout.addWidget(stop_btn)
        # Fast backward
        back_btn = QPushButton("⏪")
        back_btn.setToolTip(self.translations.get("Fast Backward", "Fast Backward"))
        back_btn.setFixedSize(48, 48)
        back_btn.setStyleSheet("font-size: 28px; background: #222; color: #fff; border-radius: 24px;")
        back_btn.clicked.connect(lambda: self.seek(max(0, self.player.get_time()//1000 - 10)))
        layout.addWidget(back_btn)
        # Fast forward
        forward_btn = QPushButton("⏩")
        forward_btn.setToolTip(self.translations.get("Fast Forward", "Fast Forward"))
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
        # Remove event filter
        self.video_frame.removeEventFilter(self)
        # Reparent video frame back to the original parent
        if self.normal_parent:
            parent_layout = self.layout()
            parent_layout.insertWidget(0, self.video_frame, 1)
            self.video_frame.setGeometry(self.normal_geometry)
            self.video_frame.show()
            if sys.platform == "linux" or sys.platform == "linux2":
                self.player.set_xwindow(self.video_frame.winId())
            elif sys.platform == "win32":
                self.player.set_hwnd(self.video_frame.winId())
            elif sys.platform == "darwin":
                self.player.set_nsobject(int(self.video_frame.winId()))
        # Close and delete the fullscreen window
        if hasattr(self, 'fullscreen_window') and self.fullscreen_window:
            self.fullscreen_window.close()
            self.fullscreen_window = None
        self.is_fullscreen = False
        self.controls.set_fullscreen(False)

    
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
        current_time_ms = self.player.get_time()
        duration_ms = self.player.get_length()

        time_sec = current_time_ms // 1000
        self.controls.set_current_time(time_sec)
        
        if self.controls.duration == 0:
            duration_sec = duration_ms // 1000
            if duration_sec > 0:
                self.controls.set_duration(duration_sec)
        
        # Emit position update for offline items
        if self.current_item:
            stream_id = self.current_item.get('stream_id')
            # Consider adding an 'is_offline' flag to current_item if differentiation is needed
            # For now, assume any item with stream_id might be tracked.
            if stream_id is not None and duration_ms > 0 : # Only emit if duration is known (meaning media is loaded)
                self.playback_position_updated.emit(str(stream_id), current_time_ms, duration_ms)

        # Check if playback ended
        if not self.player.is_playing() and self.controls.is_playing:
            state = self.player.get_state()
            if state == vlc.State.Ended:
                self.stop()
    
    def is_playing(self):
        """Check if player is currently playing"""
        return self.player.is_playing()

class PlayerWindow(QMainWindow):
    """Top-level window for video playback using MediaPlayer"""
    add_to_favorites = pyqtSignal(dict)  # Signal to add current item to favorites
    
    def __init__(self, parent=None, favorites_manager=None):
        super().__init__(parent)
        # Get translations from parent or default to English
        language = getattr(parent, 'language', 'en') if parent else 'en'
        self.translations = get_translations(language)
        self.setWindowTitle(self.translations.get("Player", "Player"))
        self.setMinimumSize(800, 450)
        self.favorites_manager = favorites_manager
        self.media_player = MediaPlayer(self, favorites_manager) # Renamed for clarity from self.player
        self.setCentralWidget(self.media_player)
        self.media_player.playback_stopped.connect(self.close)
        self.media_player.add_to_favorites.connect(self.handle_add_to_favorites)
        self._was_closed = False
        self.current_item_info = None # Renamed for clarity

    def play_media(self, media_source, media_type=None, metadata=None, is_offline=False, start_position_ms=0):
        """ Plays media. Replaces the old play() method.
            media_source: URL or local filepath
            media_type: 'movie', 'series', 'live' (can be used by player for context)
            metadata: Dictionary with item details (e.g. stream_id, name, etc.)
            is_offline: Boolean indicating if playing from offline storage
            start_position_ms: Position to start playback from (in milliseconds)
        """
        if self._was_closed: # If window was closed, recreate player part
            if self.centralWidget():
                self.centralWidget().deleteLater()
            self.media_player = MediaPlayer(self, self.favorites_manager)
            self.setCentralWidget(self.media_player)
            self.media_player.playback_stopped.connect(self.close)
            self.media_player.add_to_favorites.connect(self.handle_add_to_favorites)
            self._was_closed = False

        self.media_player.stop() # Stop previous playback
        self.current_item_info = metadata # Store metadata (formerly item)

        # Update window title based on what's playing
        title = self.translations.get("Player", "Player")
        if metadata and metadata.get('name'):
            title = f"{metadata.get('name')} - {title}"
        elif metadata and metadata.get('title'): # some items use 'title'
             title = f"{metadata.get('title')} - {title}"
        self.setWindowTitle(title)

        self.show()
        self.raise_()
        self.activateWindow()
        
        # Pass all relevant info to MediaPlayer's play method
        self.media_player.play(media_source, item=metadata, start_position_ms=start_position_ms)

    # Keep old play method for a while for compatibility, mark as deprecated or update calls
    def play(self, url, item=None, start_position_ms=0): # Added start_position_ms for compatibility if direct calls exist
        # This method now delegates to play_media
        # item is equivalent to metadata here.
        # media_type could be inferred or passed if available. For now, assume 'movie' or 'live' based on context.
        media_type = item.get('stream_type', 'movie') if item else 'live' # Basic inference
        is_offline_playback = os.path.exists(url) if isinstance(url, str) else False # Basic inference

        self.play_media(
            media_source=url,
            media_type=media_type,
            metadata=item,
            is_offline=is_offline_playback,
            start_position_ms=start_position_ms
        )

    def handle_add_to_favorites(self, item):
        """Handle add to favorites signal from player"""
        self.add_to_favorites.emit(item)

    def closeEvent(self, event):
        if hasattr(self, 'media_player') and self.media_player: # Check if media_player exists
            self.media_player.stop()
        self._was_closed = True
        event.accept()
