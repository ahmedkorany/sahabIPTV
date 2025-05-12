"""
Recording functionality for the application
"""
import cv2
from PyQt5.QtCore import QThread, pyqtSignal
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from src.config import API_RETRIES

class RecordingThread(QThread):
    """Thread for recording live streams"""
    recording_started = pyqtSignal()
    recording_error = pyqtSignal(str)
    recording_stopped = pyqtSignal()
    
    def __init__(self, stream_url, save_path, headers):
        super().__init__()
        self.stream_url = stream_url
        self.save_path = save_path
        self.headers = headers
        self.is_recording = False
    
    def run(self):
        try:
            # Setup session with retry logic
            session = requests.Session()
            retry_strategy = Retry(
                total=API_RETRIES,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            session.mount("http://", adapter)
            session.mount("https://", adapter)
            
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
