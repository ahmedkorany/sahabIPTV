"""
Xtream Codes API client
"""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from src.config import API_TIMEOUT, API_RETRIES
import time
import pickle
import os
import hashlib

CACHE_DIR = os.path.join(os.path.dirname(__file__), '../../assets/cache/data')
CACHE_EXPIRATION_SECONDS = 24 * 60 * 60  # 1 day

def _get_cache_path(key):
    # Use MD5 hash of the key to create a safe filename
    key_hash = hashlib.md5(key.encode('utf-8')).hexdigest()
    return os.path.join(CACHE_DIR, f"xtream_{key_hash}.pkl")

def _load_cache(key):
    path = _get_cache_path(key)
    print(f"[CACHE] Loading cache from: {path}")
    if not os.path.exists(path):
        print(f"[CACHE] Cache file does not exist: {path}")
        return None
    try:
        with open(path, 'rb') as f:
            data = pickle.load(f)
        if time.time() - data['timestamp'] < CACHE_EXPIRATION_SECONDS:
            print(f"[CACHE] Cache hit for key: {key}")
            return data['value']
        else:
            print(f"[CACHE] Cache expired for key: {key}")
    except Exception as e:
        print(f"[CACHE] Error loading cache for key {key}: {e}")
    return None

def _save_cache(key, value):
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
    path = _get_cache_path(key)
    print(f"[CACHE] Saving cache to: {path}")
    try:
        with open(path, 'wb') as f:
            pickle.dump({'timestamp': time.time(), 'value': value}, f)
        print(f"[CACHE] Cache saved for key: {key}")
    except Exception as e:
        print(f"[CACHE] Error saving cache for key {key}: {e}")

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
        cache_key = f'live_categories_{self.server_url}_{self.username}'
        cached = _load_cache(cache_key)
        if cached is not None:
            return True, cached
        try:
            url = f"{self.server_url}/player_api.php?username={self.username}&password={self.password}&action=get_live_categories"
            response = self.session.get(url, headers=self.headers, timeout=API_TIMEOUT)
            
            if response.status_code != 200:
                return False, f"Server returned status code {response.status_code}"
            
            data = response.json()
            _save_cache(cache_key, data)
            return True, data
        except Exception as e:
            return False, str(e)
    
    def get_live_streams(self, category_id=None):
        """Get live streams for a category"""
        key = f'live_streams_{self.server_url}_{self.username}_{category_id or "all"}'
        cached = _load_cache(key)
        if cached is not None:
            return True, cached
        try:
            url = f"{self.server_url}/player_api.php?username={self.username}&password={self.password}&action=get_live_streams"
            if category_id:
                url += f"&category_id={category_id}"
                
            response = self.session.get(url, headers=self.headers, timeout=API_TIMEOUT)
            
            if response.status_code != 200:
                return False, f"Server returned status code {response.status_code}"
            
            data = response.json()
            _save_cache(key, data)
            return True, data
        except Exception as e:
            return False, str(e)
    
    def get_vod_categories(self):
        """Get VOD (movie) categories"""
        cache_key = f'vod_categories_{self.server_url}_{self.username}'
        cached = _load_cache(cache_key)
        if cached is not None:
            return True, cached
        try:
            url = f"{self.server_url}/player_api.php?username={self.username}&password={self.password}&action=get_vod_categories"
            response = self.session.get(url, headers=self.headers, timeout=API_TIMEOUT)
            
            if response.status_code != 200:
                return False, f"Server returned status code {response.status_code}"
            
            data = response.json()
            _save_cache(cache_key, data)
            return True, data
        except Exception as e:
            return False, str(e)
    
    def get_vod_streams(self, category_id=None):
        """Get VOD (movie) streams for a category"""
        key = f'vod_streams_{self.server_url}_{self.username}_{category_id or "all"}'
        cached = _load_cache(key)
        if cached is not None:
            return True, cached
        try:
            url = f"{self.server_url}/player_api.php?username={self.username}&password={self.password}&action=get_vod_streams"
            if category_id:
                url += f"&category_id={category_id}"
                
            response = self.session.get(url, headers=self.headers, timeout=API_TIMEOUT)
            
            if response.status_code != 200:
                return False, f"Server returned status code {response.status_code}"
            
            data = response.json()
            _save_cache(key, data)
            return True, data
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
        cache_key = f'series_categories_{self.server_url}_{self.username}'
        cached = _load_cache(cache_key)
        if cached is not None:
            return True, cached
        try:
            url = f"{self.server_url}/player_api.php?username={self.username}&password={self.password}&action=get_series_categories"
            response = self.session.get(url, headers=self.headers, timeout=API_TIMEOUT)
            
            if response.status_code != 200:
                return False, f"Server returned status code {response.status_code}"
            
            data = response.json()
            _save_cache(cache_key, data)
            return True, data
        except Exception as e:
            return False, str(e)
    
    def get_series(self, category_id=None):
        """Get series for a category"""
        key = f'series_{self.server_url}_{self.username}_{category_id or "all"}'
        cached = _load_cache(key)
        if cached is not None:
            return True, cached
        try:
            url = f"{self.server_url}/player_api.php?username={self.username}&password={self.password}&action=get_series"
            if category_id:
                url += f"&category_id={category_id}"
                
            response = self.session.get(url, headers=self.headers, timeout=API_TIMEOUT)
            
            if response.status_code != 200:
                return False, f"Server returned status code {response.status_code}"
            
            data = response.json()
            _save_cache(key, data)
            return True, data
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
    
    def get_image_data(self, url):
        """Download image data from a URL and return bytes (for QPixmap)"""
        try:
            import requests
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                return resp.content
            return b''
        except Exception:
            return b''
    
    def invalidate_cache(self):
        """Delete all .pkl cache files in the cache directory."""
        if not os.path.exists(CACHE_DIR):
            return
        for fname in os.listdir(CACHE_DIR):
            if fname.endswith('.pkl'):
                try:
                    os.remove(os.path.join(CACHE_DIR, fname))
                    print(f"[CACHE] Deleted cache file: {fname}")
                except Exception as e:
                    print(f"[CACHE] Error deleting cache file {fname}: {e}")
