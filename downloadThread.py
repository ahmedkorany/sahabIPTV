from PyQt5.QtCore import QThread, pyqtSignal
import requests

class DownloadThread(QThread):
    progress_update = pyqtSignal(int)
    download_complete = pyqtSignal(str)
    download_error = pyqtSignal(str)
    
    def __init__(self, url, save_path):
        super().__init__()
        self.url = url
        self.save_path = save_path
        self.is_cancelled = False
    
    def run(self):
        try:
            response = requests.get(self.url, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            
            if total_size == 0:
                self.download_error.emit("Unable to determine file size")
                return
            
            downloaded = 0
            with open(self.save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if self.is_cancelled:
                        break
                    
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        progress = int((downloaded / total_size) * 100)
                        self.progress_update.emit(progress)
            
            if self.is_cancelled:
                # Delete partial file
                os.remove(self.save_path)
            else:
                self.download_complete.emit(self.save_path)
                
        except Exception as e:
            self.download_error.emit(str(e))
    
    def cancel(self):
        self.is_cancelled = True

class BatchDownloadThread(QThread):
    progress_update = pyqtSignal(int, int)  # episode_index, progress
    download_complete = pyqtSignal()
    download_error = pyqtSignal(str)
    
    def __init__(self, server_url, username, password, episodes, save_dir, series_name):
        super().__init__()
        self.server_url = server_url
        self.username = username
        self.password = password
        self.episodes = episodes
        self.save_dir = save_dir
        self.series_name = series_name
        self.is_cancelled = False
    
    def run(self):
        try:
            total_episodes = len(self.episodes)
            
            for i, episode in enumerate(self.episodes):
                if self.is_cancelled:
                    break
                
                episode_id = episode['id']
                episode_title = episode['title']
                episode_number = episode['episode_num']
                
                # Create filename
                filename = f"{self.series_name} - S{episode['season']}E{episode_number} - {episode_title}.mp4"
                save_path = os.path.join(self.save_dir, filename)
                
                # Get stream URL
                stream_url = f"{self.server_url}/series/{self.username}/{self.password}/{episode_id}.mp4"
                
                # Download episode
                response = requests.get(stream_url, stream=True)
                total_size = int(response.headers.get('content-length', 0))
                
                if total_size == 0:
                    continue
                
                downloaded = 0
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if self.is_cancelled:
                            break
                        
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            progress = int((downloaded / total_size) * 100)
                            self.progress_update.emit(i, progress)
                
                if self.is_cancelled:
                    # Delete partial file
                    if os.path.exists(save_path):
                        os.remove(save_path)
                    break
            
            if not self.is_cancelled:
                self.download_complete.emit()
                
        except Exception as e:
            self.download_error.emit(str(e))
    
    def cancel(self):
        self.is_cancelled = True

class RecordingThread(QThread):
    recording_started = pyqtSignal()
    recording_error = pyqtSignal(str)
    recording_stopped = pyqtSignal()
    
    def __init__(self, stream_url, save_path):
        super().__init__()
        self.stream_url = stream_url
        self.save_path = save_path
        self.is_recording = False
    
    def run(self):
        try:
            import cv2
            
            # Open stream
            cap = cv2.VideoCapture(self.stream_url)
            
            if not cap.isOpened():
                self.recording_error.emit("Failed to open stream")
                return
            
            # Get video properties
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            if fps <= 0:
                fps = 25  # Default to 25 fps if not detected
            
            # Create VideoWriter
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(self.save_path, fourcc, fps, (width, height))
            
            self.is_recording = True
            self.recording_started.emit()
            
            while self.is_recording:
                ret, frame = cap.read()
                
                if not ret:
                    break
                
                out.write(frame)
            
            # Release resources
            cap.release()
            out.release()
            
            self.recording_stopped.emit()
            
        except Exception as e:
            self.recording_error.emit(str(e))
    
    def stop_recording(self):
        self.is_recording = False
