"""Media service for handling playback operations"""
from typing import Dict, Any, Optional, Callable
from PyQt5.QtCore import QObject, pyqtSignal

from src.constants import MediaConstants, UserMessages


class MediaService(QObject):
    """Service for handling media playback operations"""
    
    # Signals
    playback_started = pyqtSignal(dict)  # Emitted when playback starts
    playback_stopped = pyqtSignal()      # Emitted when playback stops
    playback_error = pyqtSignal(str)     # Emitted on playback error
    
    def __init__(self, player_window=None):
        super().__init__()
        self.player_window = player_window
        self.current_media = None
        self.is_playing = False
    
    def play_channel(self, channel_data: Dict[str, Any]) -> bool:
        """Play a live TV channel
        
        Args:
            channel_data: Dictionary containing channel information
            
        Returns:
            True if playback started successfully, False otherwise
        """
        try:
            if not self._validate_channel_data(channel_data):
                self.playback_error.emit("Invalid channel data")
                return False
            
            if self.player_window:
                self.player_window.play_channel(channel_data)
                self.current_media = channel_data
                self.is_playing = True
                self.playback_started.emit(channel_data)
                return True
            else:
                self.playback_error.emit("Player window not available")
                return False
                
        except Exception as e:
            self.playback_error.emit(f"Error playing channel: {str(e)}")
            return False
    
    def play_movie(self, movie_data: Dict[str, Any]) -> bool:
        """Play a movie
        
        Args:
            movie_data: Dictionary containing movie information
            
        Returns:
            True if playback started successfully, False otherwise
        """
        try:
            if not self._validate_movie_data(movie_data):
                self.playback_error.emit("Invalid movie data")
                return False
            
            if self.player_window:
                self.player_window.play_movie(movie_data)
                self.current_media = movie_data
                self.is_playing = True
                self.playback_started.emit(movie_data)
                return True
            else:
                self.playback_error.emit("Player window not available")
                return False
                
        except Exception as e:
            self.playback_error.emit(f"Error playing movie: {str(e)}")
            return False
    
    def play_series_episode(self, series_data: Dict[str, Any], episode_data: Dict[str, Any]) -> bool:
        """Play a series episode
        
        Args:
            series_data: Dictionary containing series information
            episode_data: Dictionary containing episode information
            
        Returns:
            True if playback started successfully, False otherwise
        """
        try:
            if not self._validate_series_data(series_data) or not self._validate_episode_data(episode_data):
                self.playback_error.emit("Invalid series or episode data")
                return False
            
            if self.player_window:
                self.player_window.play_series_episode(series_data, episode_data)
                self.current_media = {'series': series_data, 'episode': episode_data}
                self.is_playing = True
                self.playback_started.emit(self.current_media)
                return True
            else:
                self.playback_error.emit("Player window not available")
                return False
                
        except Exception as e:
            self.playback_error.emit(f"Error playing episode: {str(e)}")
            return False
    
    def stop_playback(self) -> bool:
        """Stop current playback
        
        Returns:
            True if stopped successfully, False otherwise
        """
        try:
            if self.player_window and hasattr(self.player_window, 'stop'):
                self.player_window.stop()
            
            self.current_media = None
            self.is_playing = False
            self.playback_stopped.emit()
            return True
            
        except Exception as e:
            self.playback_error.emit(f"Error stopping playback: {str(e)}")
            return False
    
    def pause_playback(self) -> bool:
        """Pause current playback
        
        Returns:
            True if paused successfully, False otherwise
        """
        try:
            if self.player_window and hasattr(self.player_window, 'pause'):
                self.player_window.pause()
                return True
            return False
            
        except Exception as e:
            self.playback_error.emit(f"Error pausing playback: {str(e)}")
            return False
    
    def resume_playback(self) -> bool:
        """Resume paused playback
        
        Returns:
            True if resumed successfully, False otherwise
        """
        try:
            if self.player_window and hasattr(self.player_window, 'resume'):
                self.player_window.resume()
                return True
            return False
            
        except Exception as e:
            self.playback_error.emit(f"Error resuming playback: {str(e)}")
            return False
    
    def set_volume(self, volume: int) -> bool:
        """Set playback volume
        
        Args:
            volume: Volume level (0-100)
            
        Returns:
            True if volume set successfully, False otherwise
        """
        try:
            if not 0 <= volume <= 100:
                self.playback_error.emit("Volume must be between 0 and 100")
                return False
            
            if self.player_window and hasattr(self.player_window, 'set_volume'):
                self.player_window.set_volume(volume)
                return True
            return False
            
        except Exception as e:
            self.playback_error.emit(f"Error setting volume: {str(e)}")
            return False
    
    def seek(self, position: int) -> bool:
        """Seek to position in current media
        
        Args:
            position: Position in seconds
            
        Returns:
            True if seek successful, False otherwise
        """
        try:
            if self.player_window and hasattr(self.player_window, 'seek'):
                self.player_window.seek(position)
                return True
            return False
            
        except Exception as e:
            self.playback_error.emit(f"Error seeking: {str(e)}")
            return False
    
    def get_current_media(self) -> Optional[Dict[str, Any]]:
        """Get currently playing media information
        
        Returns:
            Current media data or None if nothing is playing
        """
        return self.current_media
    
    def is_media_playing(self) -> bool:
        """Check if media is currently playing
        
        Returns:
            True if media is playing, False otherwise
        """
        return self.is_playing
    
    def _validate_channel_data(self, channel_data: Dict[str, Any]) -> bool:
        """Validate channel data structure
        
        Args:
            channel_data: Channel data to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['stream_id', 'name']
        return all(field in channel_data for field in required_fields)
    
    def _validate_movie_data(self, movie_data: Dict[str, Any]) -> bool:
        """Validate movie data structure
        
        Args:
            movie_data: Movie data to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['stream_id', 'name']
        return all(field in movie_data for field in required_fields)
    
    def _validate_series_data(self, series_data: Dict[str, Any]) -> bool:
        """Validate series data structure
        
        Args:
            series_data: Series data to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['series_id', 'name']
        return all(field in series_data for field in required_fields)
    
    def _validate_episode_data(self, episode_data: Dict[str, Any]) -> bool:
        """Validate episode data structure
        
        Args:
            episode_data: Episode data to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['id', 'title']
        return all(field in episode_data for field in required_fields)


class RecordingService(QObject):
    """Service for handling media recording operations"""
    
    # Signals
    recording_started = pyqtSignal(str)  # Emitted when recording starts
    recording_stopped = pyqtSignal(str)  # Emitted when recording stops
    recording_error = pyqtSignal(str)    # Emitted on recording error
    
    def __init__(self):
        super().__init__()
        self.active_recordings = {}
    
    def start_recording(self, media_data: Dict[str, Any], output_path: str) -> bool:
        """Start recording media
        
        Args:
            media_data: Media information to record
            output_path: Path where to save the recording
            
        Returns:
            True if recording started successfully, False otherwise
        """
        try:
            # Implementation would depend on the recording backend
            # This is a placeholder for the recording logic
            recording_id = f"{media_data.get('stream_id', 'unknown')}_{int(time.time())}"
            
            # Start recording thread/process here
            # self.active_recordings[recording_id] = recording_thread
            
            self.recording_started.emit(recording_id)
            return True
            
        except Exception as e:
            self.recording_error.emit(f"Error starting recording: {str(e)}")
            return False
    
    def stop_recording(self, recording_id: str) -> bool:
        """Stop an active recording
        
        Args:
            recording_id: ID of the recording to stop
            
        Returns:
            True if stopped successfully, False otherwise
        """
        try:
            if recording_id in self.active_recordings:
                # Stop the recording thread/process
                # recording_thread = self.active_recordings[recording_id]
                # recording_thread.stop()
                del self.active_recordings[recording_id]
                self.recording_stopped.emit(recording_id)
                return True
            return False
            
        except Exception as e:
            self.recording_error.emit(f"Error stopping recording: {str(e)}")
            return False
    
    def get_active_recordings(self) -> Dict[str, Any]:
        """Get list of active recordings
        
        Returns:
            Dictionary of active recordings
        """
        return self.active_recordings.copy()