import os
import json
import time
from pathlib import Path
import requests
from dotenv import load_dotenv

class TMDBClient:
    BASE_URL = "https://api.themoviedb.org/3"
    IMAGE_BASE_URL = "https://image.tmdb.org/t/p/"
    CACHE_DURATION = 365 * 24 * 60 * 60  # 1 year in seconds

    def __init__(self, api_key=None, read_access_token=None):
        # Load from .env if not provided
        load_dotenv()
        self.api_key = api_key or os.getenv("TMDB_APIACCESS_TOKEN")
        self.read_access_token = read_access_token or os.getenv("TMDB_READACCESS_TOKEN")
        if not self.api_key and not self.read_access_token:
            raise ValueError("TMDB API key or Read Access Token must be set in .env or passed to TMDBClient.")
        
        # Setup cache directory
        self.cache_dir = Path("assets/cache/tmdb")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_file_path(self, cache_key):
        """Get the cache file path for a given cache key."""
        return self.cache_dir / f"{cache_key}.json"
    
    def _is_cache_valid(self, cache_file_path):
        """Check if cache file exists and is still valid."""
        if not cache_file_path.exists():
            return False
        
        try:
            with open(cache_file_path, 'r') as f:
                cache_data = json.load(f)
            
            cache_time = cache_data.get('timestamp', 0)
            return (time.time() - cache_time) < self.CACHE_DURATION
        except (json.JSONDecodeError, KeyError, OSError):
            return False
    
    def _load_from_cache(self, cache_file_path):
        """Load data from cache file."""
        try:
            with open(cache_file_path, 'r') as f:
                cache_data = json.load(f)
            return cache_data.get('data')
        except (json.JSONDecodeError, KeyError, OSError):
            return None
    
    def _save_to_cache(self, cache_file_path, data):
        """Save data to cache file."""
        try:
            cache_data = {
                'timestamp': time.time(),
                'data': data
            }
            with open(cache_file_path, 'w') as f:
                json.dump(cache_data, f, indent=2)
        except OSError as e:
            print(f"[TMDB Cache] Warning: Could not save cache: {e}")
    
    def get_movie_credits(self, tmdb_id):
        # Check cache first
        cache_key = f"movie_credits_{tmdb_id}"
        cache_file_path = self._get_cache_file_path(cache_key)
        
        if self._is_cache_valid(cache_file_path):
            cached_data = self._load_from_cache(cache_file_path)
            if cached_data is not None:
                print(f"[TMDB Cache] Using cached movie credits for ID: {tmdb_id}")
                return cached_data
        
        # Fetch from API
        url = f"{self.BASE_URL}/movie/{tmdb_id}/credits"
        headers = {}
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        elif self.read_access_token:
            headers["Authorization"] = f"Bearer {self.read_access_token}"
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Save to cache
        self._save_to_cache(cache_file_path, data)
        print(f"[TMDB Cache] Cached movie credits for ID: {tmdb_id}")
        
        return data

    def get_full_poster_url(self, poster_path: str, size: str = 'w500') -> str | None:
        if not poster_path:
            return None
        # Ensure poster_path does not start with a slash if IMAGE_BASE_URL ends with one.
        if poster_path.startswith('/'):
            poster_path = poster_path[1:]
        return f"{self.IMAGE_BASE_URL}{size}/{poster_path}"

    def get_movie_details(self, tmdb_id):
        """Fetch movie details from TMDB by tmdb_id with retry logic and caching."""
        # Check cache first
        cache_key = f"movie_details_{tmdb_id}"
        cache_file_path = self._get_cache_file_path(cache_key)
        
        if self._is_cache_valid(cache_file_path):
            cached_data = self._load_from_cache(cache_file_path)
            if cached_data is not None:
                print(f"[TMDB Cache] Using cached movie details for ID: {tmdb_id}")
                return cached_data
        
        # Fetch from API with retry logic
        url = f"{self.BASE_URL}/movie/{tmdb_id}"
        headers = {}
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        elif self.read_access_token:
            headers["Authorization"] = f"Bearer {self.read_access_token}"
        
        max_retries = 2
        base_delay = 0.5  # Shorter delay for API calls
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    delay = base_delay * (2 ** (attempt - 1))  # 0.5s, 1s
                    print(f"[TMDB] Retry attempt {attempt + 1}/{max_retries} after {delay}s delay")
                    import time
                    time.sleep(delay)
                
                response = requests.get(url, params=params, headers=headers, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                # Save to cache
                self._save_to_cache(cache_file_path, data)
                print(f"[TMDB Cache] Cached movie details for ID: {tmdb_id}")
                
                return data
                
            except requests.RequestException as e:
                print(f"[TMDB] Request error on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt == max_retries - 1:  # Last attempt
                    raise e
                # Continue to next retry attempt
            except Exception as e:
                print(f"[TMDB] Unexpected error: {e}")
                raise e