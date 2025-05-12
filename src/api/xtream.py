"""
Xtream Codes API client
"""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from src.config import API_TIMEOUT, API_RETRIES

class XtreamClient:
    """Client for Xtream Codes API"""
    
    def __init__(self):
        self.server_url = None
        self.username = None
        self.password = None
        self.session = self._create_session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': '*/*',
            'Connection': 'keep-alive'
        }
    
    def _create_session(self):
        """Create a requests session with retry logic"""
        session = requests.Session()
        retry_strategy = Retry(
            total=API_RETRIES,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
    
    def set_credentials(self, server_url, username, password):
        """Set credentials for API requests"""
        # Remove trailing slash if present
        if server_url.endswith('/'):
            server_url = server_url[:-1]
            
        self.server_url = server_url
        self.username = username
        self.password = password
    
    def authenticate(self):
        """Authenticate with the server and get user info"""
        if not self.server_url or not self.username or not self.password:
            return False, "Missing credentials"
        
        try:
            url = f"{self.server_url}/player_api.php?username={self.username}&password={self.password}"
            response = self.session.get(url, headers=self.headers, timeout=API_TIMEOUT)
            
            if response.status_code != 200:
                return False, f"Server returned status code {response.status_code}"
            
            data = response.json()
            
            if 'user_info' not in data:
                return False, "Invalid credentials"
            
            return True, data
        except Exception as e:
            return False, str(e)
    
    def get_live_categories(self):
        """Get live TV categories"""
        try:
            url = f"{self.server_url}/player_api.php?username={self.username}&password={self.password}&action=get_live_categories"
            response = self.session.get(url, headers=self.headers, timeout=API_TIMEOUT)
            
            if response.status_code != 200:
                return False, f"Server returned status code {response.status_code}"
            
            return True, response.json()
        except Exception as e:
            return False, str(e)
    
    def get_live_streams(self, category_id=None):
        """Get live streams for a category"""
        try:
            url = f"{self.server_url}/player_api.php?username={self.username}&password={self.password}&action=get_live_streams"
            if category_id:
                url += f"&category_id={category_id}"
                
            response = self.session.get(url, headers=self.headers, timeout=API_TIMEOUT)
            
            if response.status_code != 200:
                return False, f"Server returned status code {response.status_code}"
            
            return True, response.json()
        except Exception as e:
            return False, str(e)
    
    def get_vod_categories(self):
        """Get VOD (movie) categories"""
        try:
            url = f"{self.server_url}/player_api.php?username={self.username}&password={self.password}&action=get_vod_categories"
            response = self.session.get(url, headers=self.headers, timeout=API_TIMEOUT)
            
            if response.status_code != 200:
                return False, f"Server returned status code {response.status_code}"
            
            return True, response.json()
        except Exception as e:
            return False, str(e)
    
    def get_vod_streams(self, category_id=None):
        """Get VOD (movie) streams for a category"""
        try:
            url = f"{self.server_url}/player_api.php?username={self.username}&password={self.password}&action=get_vod_streams"
            if category_id:
                url += f"&category_id={category_id}"
                
            response = self.session.get(url, headers=self.headers, timeout=API_TIMEOUT)
            
            if response.status_code != 200:
                return False, f"Server returned status code {response.status_code}"
            
            return True, response.json()
        except Exception as e:
            return False, str(e)
    
    def get_vod_info(self, vod_id):
        """Get detailed information for a VOD (movie)"""
        try:
            url = f"{self.server_url}/player_api.php?username={self.username}&password={self.password}&action=get_vod_info&vod_id={vod_id}"
            response = self.session.get(url, headers=self.headers, timeout=API_TIMEOUT)
            
            if response.status_code != 200:
                return False, f"Server returned status code {response.status_code}"
            
            return True, response.json()
        except Exception as e:
            return False, str(e)
    
    def get_series_categories(self):
        """Get series categories"""
        try:
            url = f"{self.server_url}/player_api.php?username={self.username}&password={self.password}&action=get_series_categories"
            response = self.session.get(url, headers=self.headers, timeout=API_TIMEOUT)
            
            if response.status_code != 200:
                return False, f"Server returned status code {response.status_code}"
            
            return True, response.json()
        except Exception as e:
            return False, str(e)
    
    def get_series(self, category_id=None):
        """Get series for a category"""
        try:
            url = f"{self.server_url}/player_api.php?username={self.username}&password={self.password}&action=get_series"
            if category_id:
                url += f"&category_id={category_id}"
                
            response = self.session.get(url, headers=self.headers, timeout=API_TIMEOUT)
            
            if response.status_code != 200:
                return False, f"Server returned status code {response.status_code}"
            
            return True, response.json()
        except Exception as e:
            return False, str(e)
    
    def get_series_info(self, series_id):
        """Get detailed information for a series"""
        try:
            url = f"{self.server_url}/player_api.php?username={self.username}&password={self.password}&action=get_series_info&series_id={series_id}"
            response = self.session.get(url, headers=self.headers, timeout=API_TIMEOUT)
            
            if response.status_code != 200:
                return False, f"Server returned status code {response.status_code}"
            
            return True, response.json()
        except Exception as e:
            return False, str(e)
    
    def get_live_stream_url(self, stream_id):
        """Get the URL for a live stream"""
        return f"{self.server_url}/live/{self.username}/{self.password}/{stream_id}.ts"
    
    def get_movie_url(self, stream_id, container_extension="mp4"):
        """Get the URL for a movie"""
        return f"{self.server_url}/movie/{self.username}/{self.password}/{stream_id}.{container_extension}"
    
    def get_series_url(self, episode_id, container_extension="mp4"):
        """Get the URL for a series episode"""
        return f"{self.server_url}/series/{self.username}/{self.password}/{episode_id}.{container_extension}"
