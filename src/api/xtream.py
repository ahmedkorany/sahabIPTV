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
    def update_movie_cache(self, movie_to_update):
        """Updates a specific movie's details within its cached category list."""
        category_id = movie_to_update.get('category_id')
        stream_id_to_update = movie_to_update.get('stream_id')
        new_stream_icon = movie_to_update.get('stream_icon') # Assuming this is the primary field to update

        if not (category_id and stream_id_to_update and self.server_url and self.username):
            # print(f"[XtreamClient.update_movie_cache] Missing necessary data: category_id='{category_id}', stream_id='{stream_id_to_update}', server_url, or username.")
            return False

        cache_key = f'vod_streams_{self.server_url}_{self.username}_{category_id}'
        # print(f"[XtreamClient.update_movie_cache] Attempting to update movie in category cache. Key: {cache_key}")
        
        cached_category_movies = _load_cache(cache_key)
        
        if isinstance(cached_category_movies, list):
            updated = False
            for i, movie_in_cache in enumerate(cached_category_movies):
                if isinstance(movie_in_cache, dict) and movie_in_cache.get('stream_id') == stream_id_to_update:
                    # Update the specific movie's details
                    # For now, primarily stream_icon. Extend if other fields in movie_to_update need to be synced.
                    movie_in_cache['stream_icon'] = new_stream_icon 
                    # Example: movie_in_cache.update({k: v for k, v in movie_to_update.items() if k in movie_in_cache}) # More generic update
                    cached_category_movies[i] = movie_in_cache # Ensure the list is updated with the modified dict
                    updated = True
                    break
            
            if updated:
                _save_cache(cache_key, cached_category_movies)
                # print(f"[XtreamClient.update_movie_cache] Updated movie (ID: {stream_id_to_update}) in cached category '{category_id}'.")
                return True
            else:
                # print(f"[XtreamClient.update_movie_cache] Movie (ID: {stream_id_to_update}) not found in cached category '{category_id}'.")
                return False
        else:
            # print(f"[XtreamClient.update_movie_cache] No cached data or invalid format for category '{category_id}'. Key: {cache_key}")
            return False

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
    
    def populate_full_cache(self, progress_callback=None):
        """Fetch and cache all categories and their items (live, VOD, series), reporting progress."""
        if not self.server_url or not self.username or not self.password:
            if progress_callback:
                progress_callback(0, 1, "Error: Missing credentials", True)
            return False, "Missing credentials"

        actions = []
        # Phase 1: Plan actions to determine total steps
        # Live Categories and Streams
        actions.append({'type': 'get_live_categories', 'id': None, 'desc': 'Fetching Live Categories'})
        # VOD Categories and Streams
        actions.append({'type': 'get_vod_categories', 'id': None, 'desc': 'Fetching VOD Categories'})
        # Series Categories and Series
        actions.append({'type': 'get_series_categories', 'id': None, 'desc': 'Fetching Series Categories'})

        # Placeholder for dynamic steps (streams/series per category)
        # This will be expanded after fetching categories
        planned_actions = list(actions) # Copy initial actions
        
        # Estimate total steps (initial categories + a guess for items per category, will be refined)
        # This is a rough estimate for now, will be more accurate after fetching categories
        # For now, let's assume an initial 3 steps for categories, and then we'll add more dynamically.
        
        total_steps = 0
        current_step = 0
        detailed_actions = []

        # Step 1: Fetch Live Categories
        if progress_callback: progress_callback(current_step, len(planned_actions) * 2, "Fetching live categories...", False) # Rough estimate
        live_cat_success, live_categories = self.get_live_categories()
        if live_cat_success and isinstance(live_categories, list):
            detailed_actions.append({'type': 'live_categories_fetched', 'data': live_categories, 'desc': 'Fetched Live Categories'})
            for cat in live_categories:
                detailed_actions.append({'type': 'get_live_streams', 'id': cat.get('category_id'), 'desc': f"Fetching Live Streams for {cat.get('category_name')}"}) 
        else:
            if progress_callback: progress_callback(current_step, len(planned_actions) * 2, f"Failed to fetch live categories: {live_categories}", True)
            # Optionally, decide if to stop or continue

        # Step 2: Fetch VOD Categories
        if progress_callback: progress_callback(current_step, len(planned_actions) * 2 + len(detailed_actions), "Fetching VOD categories...", False)
        vod_cat_success, vod_categories = self.get_vod_categories()
        if vod_cat_success and isinstance(vod_categories, list):
            detailed_actions.append({'type': 'vod_categories_fetched', 'data': vod_categories, 'desc': 'Fetched VOD Categories'})
            for cat in vod_categories:
                detailed_actions.append({'type': 'get_vod_streams', 'id': cat.get('category_id'), 'desc': f"Fetching VOD Streams for {cat.get('category_name')}"})
        else:
            if progress_callback: progress_callback(current_step, len(planned_actions) * 2 + len(detailed_actions), f"Failed to fetch VOD categories: {vod_categories}", True)

        # Step 3: Fetch Series Categories
        if progress_callback: progress_callback(current_step, len(planned_actions) * 2 + len(detailed_actions), "Fetching series categories...", False)
        series_cat_success, series_categories = self.get_series_categories()
        if series_cat_success and isinstance(series_categories, list):
            detailed_actions.append({'type': 'series_categories_fetched', 'data': series_categories, 'desc': 'Fetched Series Categories'})
            for cat in series_categories:
                detailed_actions.append({'type': 'get_series', 'id': cat.get('category_id'), 'desc': f"Fetching Series for {cat.get('category_name')}"})
        else:
            if progress_callback: progress_callback(current_step, len(planned_actions) * 2 + len(detailed_actions), f"Failed to fetch series categories: {series_categories}", True)

        total_steps = len(detailed_actions)
        
        # Phase 2: Execute all detailed actions
        for i, action_info in enumerate(detailed_actions):
            current_step = i + 1
            action_type = action_info['type']
            action_id = action_info.get('id')
            action_desc = action_info['desc']

            if progress_callback:
                progress_callback(current_step, total_steps, action_desc, False)
            
            success = False
            result_data = None
            error_message = ""

            try:
                if action_type == 'get_live_streams':
                    # Force fetch by invalidating potential existing cache for this specific item
                    # This is tricky as _save_cache is global. We rely on get_live_streams to handle its own caching.
                    # For a full refresh, we'd ideally clear specific keys or all cache before this method.
                    # However, the current get_live_streams will fetch if not cached or expired.
                    success, result_data = self.get_live_streams(category_id=action_id)
                elif action_type == 'get_vod_streams':
                    success, result_data = self.get_vod_streams(category_id=action_id)
                elif action_type == 'get_series':
                    success, result_data = self.get_series(category_id=action_id)
                elif action_type.endswith('_fetched'): # these are just markers, no API call
                    success = True # Already fetched
                    pass 
                else:
                    # This case should ideally not be hit if detailed_actions is built correctly
                    print(f"[CACHE POPULATE] Unknown action type: {action_type}")
                    error_message = f"Unknown action type: {action_type}"
                    success = False

                if not success and not action_type.endswith('_fetched'):
                    error_message = result_data if isinstance(result_data, str) else "Unknown error during fetch"
                    print(f"[CACHE POPULATE] Failed: {action_desc} - {error_message}")
                    if progress_callback:
                        # Update progress with error for this specific step
                        progress_callback(current_step, total_steps, f"Error - {action_desc}: {error_message}", True)
                # If successful, data is already cached by the respective get_* methods.

            except Exception as e:
                print(f"[CACHE POPULATE] Exception during {action_desc}: {e}")
                if progress_callback:
                    progress_callback(current_step, total_steps, f"Exception - {action_desc}: {e}", True)
        
        if progress_callback:
            progress_callback(total_steps, total_steps, "Cache population complete.", False)
        return True, "Full cache population process initiated."

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
        """Delete all .pkl cache files in the cache directory. Does NOT touch user favorites file."""
        if not os.path.exists(CACHE_DIR):
            return
        for fname in os.listdir(CACHE_DIR):
            if fname.endswith('.pkl'):
                try:
                    os.remove(os.path.join(CACHE_DIR, fname))
                    print(f"[CACHE] Deleted cache file: {fname}")
                except Exception as e:
                    print(f"[CACHE] Error deleting cache file {fname}: {e}")
        # Do NOT touch favorites file here!
