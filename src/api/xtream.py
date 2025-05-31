"""Xtream Codes API client"""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Tuple, Optional, Dict, Any

from src.config import API_TIMEOUT, API_RETRIES
from src.constants import APIConstants, ErrorMessages
from src.services.cache_manager import XtreamCacheManager

class XtreamClient:
    def update_movie_cache(self, movie_to_update):
        """Updates a specific movie's details within its cached category list."""
        if not self.cache_manager:
            return False
            
        category_id = movie_to_update.get('category_id')
        stream_id_to_update = movie_to_update.get('stream_id')
        new_stream_icon = movie_to_update.get('stream_icon') # Assuming this is the primary field to update

        if not (category_id and stream_id_to_update and self.server_url and self.username):
            return False

        cache_key = f'vod_streams_{self.server_url}_{self.username}_{category_id}'
        
        cached_category_movies = self.cache_manager.get(cache_key)
        
        if isinstance(cached_category_movies, list):
            updated = False
            for i, movie_in_cache in enumerate(cached_category_movies):
                if isinstance(movie_in_cache, dict) and movie_in_cache.get('stream_id') == stream_id_to_update:
                    # Update the specific movie's details
                    movie_in_cache['stream_icon'] = new_stream_icon 
                    cached_category_movies[i] = movie_in_cache
                    updated = True
                    break
            
            if updated:
                self.cache_manager.set(cache_key, cached_category_movies)
                return True
            else:
                return False
        else:
            return False

    def update_series_cache(self, series_to_update):
        """Updates a specific series' details within its cached category list."""
        if not self.cache_manager:
            return False
            
        category_id = series_to_update.get('category_id')
        # Series are identified by 'series_id' in Xtream Codes, not 'stream_id'
        series_id_to_update = series_to_update.get('series_id') 
        new_cover_url = series_to_update.get('cover') # 'cover' is used for series posters

        if not (category_id and series_id_to_update and self.server_url and self.username):
            return False

        # Cache key for series lists within a category
        cache_key = f'series_{self.server_url}_{self.username}_{category_id}'
        
        cached_category_series = self.cache_manager.get(cache_key)
        
        if isinstance(cached_category_series, list):
            updated = False
            for i, series_in_cache in enumerate(cached_category_series):
                if isinstance(series_in_cache, dict) and series_in_cache.get('series_id') == series_id_to_update:
                    # Update the specific series' details
                    if new_cover_url is not None: # Only update if a new cover is provided
                        series_in_cache['cover'] = new_cover_url
                    # Update tmdb_id if it's part of series_to_update and potentially new
                    if 'tmdb_id' in series_to_update:
                        series_in_cache['tmdb_id'] = series_to_update['tmdb_id']
                    
                    cached_category_series[i] = series_in_cache # Ensure the list is updated
                    updated = True
                    break
            
            if updated:
                self.cache_manager.set(cache_key, cached_category_series)
                return True
            else:
                return False
        else:
            return False


    """Client for Xtream Codes API"""
    
    def __init__(self, cache_manager: Optional[XtreamCacheManager] = None):
        self.server_url = None
        self.username = None
        self.password = None
        self.session = self._create_session()
        self.cache_manager = cache_manager
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
    
    def set_credentials(self, server_url: str, username: str, password: str) -> None:
        """Set server credentials"""
        self.server_url = server_url.rstrip('/')
        self.username = username
        self.password = password
    
    def _has_credentials(self) -> bool:
        """Check if all required credentials are set"""
        return bool(self.server_url and self.username and self.password)
    
    def _build_api_url(self, action: str = "", **params) -> str:
        """Build API URL with parameters"""
        base_url = f"{self.server_url}/player_api.php?username={self.username}&password={self.password}"
        if action:
            base_url += f"&action={action}"
        for key, value in params.items():
            if value is not None:
                base_url += f"&{key}={value}"
        return base_url
    
    def authenticate(self) -> Tuple[bool, Any]:
        """Authenticate with the server and get user info
        
        Returns:
            Tuple of (success: bool, data: dict or error_message: str)
        """
        if not self._has_credentials():
            return False, ErrorMessages.MISSING_CREDENTIALS
        
        try:
            url = self._build_api_url()
            response = self.session.get(url, headers=self.headers, timeout=API_TIMEOUT)
            
            if response.status_code != 200:
                return False, ErrorMessages.SERVER_ERROR.format(response.status_code)
            
            data = response.json()
            
            if 'user_info' not in data:
                return False, ErrorMessages.INVALID_CREDENTIALS
            
            return True, data
        except Exception as e:
            return False, ErrorMessages.CONNECTION_ERROR.format(str(e))
    
    def get_live_categories(self) -> Tuple[bool, Any]:
        """Get live TV categories
        
        Returns:
            Tuple of (success: bool, data: list or error_message: str)
        """
        if not self._has_credentials():
            return False, ErrorMessages.MISSING_CREDENTIALS
        
        cache_key = f"live_categories_{self.username}_{self.server_url}"
        
        # Try cache first if cache manager is available
        if self.cache_manager:
            cached_data = self.cache_manager.get(cache_key)
            if cached_data is not None:
                return True, cached_data
        
        try:
            url = self._build_api_url(action="get_live_categories")
            response = self.session.get(url, headers=self.headers, timeout=API_TIMEOUT)
            
            if response.status_code == 200:
                data = response.json()
                # Cache the result if cache manager is available
                if self.cache_manager:
                    self.cache_manager.set(cache_key, data)
                return True, data
            else:
                return False, ErrorMessages.SERVER_ERROR.format(response.status_code)
        except Exception as e:
            return False, ErrorMessages.CONNECTION_ERROR.format(str(e))
    
    def get_live_streams(self, category_id: Optional[str] = None) -> Tuple[bool, Any]:
        """Get live streams for a category
        
        Args:
            category_id: Optional category ID to filter streams
            
        Returns:
            Tuple of (success: bool, data: list or error_message: str)
        """
        if not self._has_credentials():
            return False, ErrorMessages.MISSING_CREDENTIALS
        
        cache_key = f'live_streams_{self.username}_{self.server_url}_{category_id or "all"}'
        
        # Try cache first if cache manager is available
        if self.cache_manager:
            cached_data = self.cache_manager.get(cache_key)
            if cached_data is not None:
                return True, cached_data
        
        try:
            url = self._build_api_url(action="get_live_streams", category_id=category_id)
            response = self.session.get(url, headers=self.headers, timeout=API_TIMEOUT)
            
            if response.status_code != 200:
                return False, ErrorMessages.SERVER_ERROR.format(response.status_code)
            
            data = response.json()
            # Cache the result if cache manager is available
            if self.cache_manager:
                self.cache_manager.set(cache_key, data)
            return True, data
        except Exception as e:
            return False, ErrorMessages.CONNECTION_ERROR.format(str(e))
    
    def get_vod_categories(self) -> Tuple[bool, Any]:
        """Get VOD (movie) categories
        
        Returns:
            Tuple of (success: bool, data: list or error_message: str)
        """
        if not self._has_credentials():
            return False, ErrorMessages.MISSING_CREDENTIALS
        
        cache_key = f'vod_categories_{self.username}_{self.server_url}'
        
        # Try cache first if cache manager is available
        if self.cache_manager:
            cached_data = self.cache_manager.get(cache_key)
            if cached_data is not None:
                return True, cached_data
        
        try:
            url = self._build_api_url(action="get_vod_categories")
            response = self.session.get(url, headers=self.headers, timeout=API_TIMEOUT)
            
            if response.status_code != 200:
                return False, ErrorMessages.SERVER_ERROR.format(response.status_code)
            
            data = response.json()
            # Cache the result if cache manager is available
            if self.cache_manager:
                self.cache_manager.set(cache_key, data)
            return True, data
        except Exception as e:
            return False, ErrorMessages.CONNECTION_ERROR.format(str(e))
    
    def get_vod_streams(self, category_id: Optional[str] = None) -> Tuple[bool, Any]:
        """Get VOD (movie) streams for a category
        
        Args:
            category_id: Optional category ID to filter streams
            
        Returns:
            Tuple of (success: bool, data: list or error_message: str)
        """
        if not self._has_credentials():
            return False, ErrorMessages.MISSING_CREDENTIALS
        
        cache_key = f'vod_streams_{self.username}_{self.server_url}_{category_id or "all"}'
        
        # Try cache first if cache manager is available
        if self.cache_manager:
            cached_data = self.cache_manager.get(cache_key)
            if cached_data is not None:
                return True, cached_data
        
        try:
            url = self._build_api_url(action="get_vod_streams", category_id=category_id)
            response = self.session.get(url, headers=self.headers, timeout=API_TIMEOUT)
            
            if response.status_code != 200:
                return False, ErrorMessages.SERVER_ERROR.format(response.status_code)
            
            data = response.json()
            # Cache the result if cache manager is available
            if self.cache_manager:
                self.cache_manager.set(cache_key, data)
            return True, data
        except Exception as e:
            return False, ErrorMessages.CONNECTION_ERROR.format(str(e))
    
    def get_vod_info(self, vod_id: str) -> Tuple[bool, Any]:
        """Get detailed information for a VOD (movie)
        
        Args:
            vod_id: The VOD ID to get information for
            
        Returns:
            Tuple of (success: bool, data: dict or error_message: str)
        """
        if not self._has_credentials():
            return False, ErrorMessages.MISSING_CREDENTIALS
        
        try:
            url = self._build_api_url(action="get_vod_info", vod_id=vod_id)
            response = self.session.get(url, headers=self.headers, timeout=API_TIMEOUT)
            
            if response.status_code != 200:
                return False, ErrorMessages.SERVER_ERROR.format(response.status_code)
            
            return True, response.json()
        except Exception as e:
            return False, ErrorMessages.CONNECTION_ERROR.format(str(e))
    
    def get_series_categories(self) -> Tuple[bool, Any]:
        """Get series categories
        
        Returns:
            Tuple of (success: bool, data: list or error_message: str)
        """
        if not self._has_credentials():
            return False, ErrorMessages.MISSING_CREDENTIALS
        
        cache_key = f'series_categories_{self.username}_{self.server_url}'
        
        # Try cache first if cache manager is available
        if self.cache_manager:
            cached_data = self.cache_manager.get(cache_key)
            if cached_data is not None:
                return True, cached_data
        
        try:
            url = self._build_api_url(action="get_series_categories")
            response = self.session.get(url, headers=self.headers, timeout=API_TIMEOUT)
            
            if response.status_code != 200:
                return False, ErrorMessages.SERVER_ERROR.format(response.status_code)
            
            data = response.json()
            # Cache the result if cache manager is available
            if self.cache_manager:
                self.cache_manager.set(cache_key, data)
            return True, data
        except Exception as e:
            return False, ErrorMessages.CONNECTION_ERROR.format(str(e))
    
    def get_series(self, category_id: Optional[str] = None) -> Tuple[bool, Any]:
        """Get series for a category
        
        Args:
            category_id: Optional category ID to filter series
            
        Returns:
            Tuple of (success: bool, data: list or error_message: str)
        """
        if not self._has_credentials():
            return False, ErrorMessages.MISSING_CREDENTIALS
        
        cache_key = f'series_{self.username}_{self.server_url}_{category_id or "all"}'
        
        # Try cache first if cache manager is available
        if self.cache_manager:
            cached_data = self.cache_manager.get(cache_key)
            if cached_data is not None:
                return True, cached_data
        
        try:
            url = self._build_api_url(action="get_series", category_id=category_id)
            response = self.session.get(url, headers=self.headers, timeout=API_TIMEOUT)
            
            if response.status_code != 200:
                return False, ErrorMessages.SERVER_ERROR.format(response.status_code)
            
            data = response.json()
            # Cache the result if cache manager is available
            if self.cache_manager:
                self.cache_manager.set(cache_key, data)
            return True, data
        except Exception as e:
            return False, ErrorMessages.CONNECTION_ERROR.format(str(e))
    
    def get_series_info(self, series_id: str) -> Tuple[bool, Any]:
        """Get detailed information for a series
        
        Args:
            series_id: The series ID to get information for
            
        Returns:
            Tuple of (success: bool, data: dict or error_message: str)
        """
        if not self._has_credentials():
            return False, ErrorMessages.MISSING_CREDENTIALS
        
        try:
            url = self._build_api_url(action="get_series_info", series_id=series_id)
            response = self.session.get(url, headers=self.headers, timeout=API_TIMEOUT)
            
            if response.status_code != 200:
                return False, ErrorMessages.SERVER_ERROR.format(response.status_code)
            
            return True, response.json()
        except Exception as e:
            return False, ErrorMessages.CONNECTION_ERROR.format(str(e))
    
    def get_live_stream_url(self, stream_id: str) -> Optional[str]:
        """Get the URL for a live stream
        
        Args:
            stream_id: The stream ID
            
        Returns:
            Stream URL or None if credentials are missing
        """
        if not self._has_credentials():
            return None
        return f"{self.server_url}/live/{self.username}/{self.password}/{stream_id}.ts"
    
    def get_movie_url(self, stream_id: str, container_extension: str = "mp4") -> Optional[str]:
        """Get the URL for a movie
        
        Args:
            stream_id: The movie stream ID
            container_extension: File extension (default: mp4)
            
        Returns:
            Movie URL or None if credentials are missing
        """
        if not self._has_credentials():
            return None
        return f"{self.server_url}/movie/{self.username}/{self.password}/{stream_id}.{container_extension}"
    
    def get_series_url(self, episode_id: str, container_extension: str = "mp4") -> Optional[str]:
        """Get the URL for a series episode
        
        Args:
            episode_id: The episode ID
            container_extension: File extension (default: mp4)
            
        Returns:
            Episode URL or None if credentials are missing
        """
        if not self._has_credentials():
            return None
        return f"{self.server_url}/series/{self.username}/{self.password}/{episode_id}.{container_extension}"
    
    def populate_full_cache(self, progress_callback=None) -> Tuple[bool, str]:
        """Fetch and cache all categories and their items (live, VOD, series), reporting progress.
        
        Args:
            progress_callback: Optional callback function for progress updates
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        if not self._has_credentials():
            if progress_callback:
                progress_callback(0, 1, ErrorMessages.MISSING_CREDENTIALS, True)
            return False, ErrorMessages.MISSING_CREDENTIALS

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
        if progress_callback: 
            progress_callback(current_step, len(planned_actions) * 2, "Fetching live categories...", False)
        
        live_categories = self.get_live_categories()
        if isinstance(live_categories, list) and live_categories:
            detailed_actions.append({'type': 'live_categories_fetched', 'data': live_categories, 'desc': 'Fetched Live Categories'})
            for cat in live_categories:
                detailed_actions.append({'type': 'get_live_streams', 'id': cat.get('category_id'), 'desc': f"Fetching Live Streams for {cat.get('category_name')}"})
        else:
            if progress_callback: 
                progress_callback(current_step, len(planned_actions) * 2, "Failed to fetch live categories", True)

        # Step 2: Fetch VOD Categories
        if progress_callback: 
            progress_callback(current_step, len(planned_actions) * 2 + len(detailed_actions), "Fetching VOD categories...", False)
        
        vod_cat_success, vod_categories = self.get_vod_categories()
        if vod_cat_success and isinstance(vod_categories, list):
            detailed_actions.append({'type': 'vod_categories_fetched', 'data': vod_categories, 'desc': 'Fetched VOD Categories'})
            for cat in vod_categories:
                detailed_actions.append({'type': 'get_vod_streams', 'id': cat.get('category_id'), 'desc': f"Fetching VOD Streams for {cat.get('category_name')}"})
        else:
            if progress_callback: 
                progress_callback(current_step, len(planned_actions) * 2 + len(detailed_actions), f"Failed to fetch VOD categories: {vod_categories if not vod_cat_success else 'Unknown error'}", True)

        # Step 3: Fetch Series Categories
        if progress_callback: 
            progress_callback(current_step, len(planned_actions) * 2 + len(detailed_actions), "Fetching series categories...", False)
        
        series_cat_success, series_categories = self.get_series_categories()
        if series_cat_success and isinstance(series_categories, list):
            detailed_actions.append({'type': 'series_categories_fetched', 'data': series_categories, 'desc': 'Fetched Series Categories'})
            for cat in series_categories:
                detailed_actions.append({'type': 'get_series', 'id': cat.get('category_id'), 'desc': f"Fetching Series for {cat.get('category_name')}"})
        else:
            if progress_callback: 
                progress_callback(current_step, len(planned_actions) * 2 + len(detailed_actions), f"Failed to fetch series categories: {series_categories if not series_cat_success else 'Unknown error'}", True)

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

    def get_image_data(self, url: str) -> bytes:
        """Download image data from a URL and return bytes (for QPixmap)
        
        Args:
            url: Image URL to download
            
        Returns:
            Image data as bytes or empty bytes if failed
        """
        try:
            response = self.session.get(url, timeout=APIConstants.IMAGE_TIMEOUT)
            if response.status_code == 200:
                return response.content
            return b''
        except Exception:
            return b''
    
    def invalidate_cache(self) -> None:
        """Delete all cache files. Uses cache manager if available."""
        if self.cache_manager:
            self.cache_manager.clear_all()
        else:
            # Fallback for when no cache manager is available
            import os
            cache_dir = os.path.join(os.path.dirname(__file__), '../../assets/cache/data')
            if os.path.exists(cache_dir):
                for fname in os.listdir(cache_dir):
                    if fname.endswith('.pkl') and fname.startswith('xtream_'):
                        try:
                            os.remove(os.path.join(cache_dir, fname))
                        except Exception as e:
                            print(f"Error deleting cache file {fname}: {e}")
        # Do NOT touch favorites file here!
