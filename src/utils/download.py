"""
Download functionality for the application
"""
import os
import requests
from PyQt5.QtCore import QThread, pyqtSignal
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from src.config import DOWNLOAD_CHUNK_SIZE, API_TIMEOUT, API_RETRIES

class DownloadThread(QThread):
    """Thread for downloading content"""
    progress_update = pyqtSignal(int)
    download_complete = pyqtSignal(str)
    download_error = pyqtSignal(str)
    
    def __init__(self, url, save_path, headers):
        super().__init__()
        self.url = url
        self.save_path = save_path
        self.headers = headers
        self.is_cancelled = False
    
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
            
            # First make a HEAD request to get the content length
            try:
                head_response = session.head(self.url, headers=self.headers, timeout=API_TIMEOUT)
                total_size = int(head_response.headers.get('content-length', 0))
            except:
                total_size = 0
            
            # If HEAD request fails or doesn't provide content length, try a GET request
            if total_size == 0:
                response = session.get(self.url, stream=True, headers=self.headers, timeout=API_TIMEOUT)
                total_size = int(response.headers.get('content-length', 0))
            else:
                response = session.get(self.url, stream=True, headers=self.headers, timeout=API_TIMEOUT)
            
            downloaded = 0
            with open(self.save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
                    if self.is_cancelled:
                        break
                    
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        progress = int((downloaded / total_size) * 100) if total_size > 0 else 0
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
    """Thread for downloading multiple episodes"""
    progress_update = pyqtSignal(int, int)  # episode_index, progress
    download_complete = pyqtSignal()
    download_error = pyqtSignal(str)
    
    def __init__(self, api_client, episodes, save_dir, series_name):
        super().__init__()
        self.api_client = api_client
        self.episodes = episodes
        self.save_dir = save_dir
        self.series_name = series_name
        self.is_cancelled = False
    
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
            
            total_episodes = len(self.episodes)
            
            for i, episode in enumerate(self.episodes):
                if self.is_cancelled:
                    break
                
                episode_id = episode['id']
                episode_title = episode['title']
                episode_number = episode['episode_num']
                season_number = episode['season']
                
                # Get container extension (default to mp4 if not specified)
                container_extension = episode.get('container_extension', 'mp4')
                
                # Create filename
                filename = f"{self.series_name} - S{season_number}E{episode_number} - {episode_title}.{container_extension}"
                save_path = os.path.join(self.save_dir, filename)
                
                # Get stream URL with correct extension
                stream_url = self.api_client.get_series_url(episode_id, container_extension)
                
                # Download episode
                response = session.get(stream_url, stream=True, headers=self.api_client.headers, timeout=API_TIMEOUT)
                total_size = int(response.headers.get('content-length', 0))
                
                downloaded = 0
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
                        if self.is_cancelled:
                            break
                        
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            progress = int((downloaded / total_size) * 100) if total_size > 0 else 0
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
