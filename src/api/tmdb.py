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
        print(f"[TMDBClient] Initialized with api_key: {'Yes' if self.api_key else 'No'}, read_access_token: {'Yes' if self.read_access_token else 'No'}")
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

    def get_series_credits(self, tmdb_id):
        """Get series credits from TMDB with caching."""
        print(f"[TMDBClient] get_series_credits called with tmdb_id: {tmdb_id}")
        cache_file = self._get_cache_file_path(f"series_credits_{tmdb_id}")
        
        # Check cache first
        if self._is_cache_valid(cache_file):
            cached_data = self._load_from_cache(cache_file)
            if cached_data:
                print(f"[TMDBClient] Returning cached series credits for {tmdb_id}")
                return cached_data
        
        # Fetch from API
        url = f"{self.BASE_URL}/tv/{tmdb_id}/credits"
        headers = {}
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        elif self.read_access_token:
            headers["Authorization"] = f"Bearer {self.read_access_token}"
        
        print(f"[TMDBClient] Fetching series credits from API: {url}")
        
        max_retries = 2
        base_delay = 0.5
        
        for attempt in range(max_retries):
            try:
                response = requests.get(url, params=params, headers=headers, timeout=10)
                print(f"[TMDBClient] API response status: {response.status_code}")
                response.raise_for_status()
                data = response.json()
                print(f"[TMDBClient] API response data keys: {list(data.keys()) if data else 'None'}")
                if 'cast' in data:
                    print(f"[TMDBClient] Found {len(data['cast'])} cast members in API response")
                
                # Save to cache
                self._save_to_cache(cache_file, data)
                return data
                
            except requests.RequestException as e:
                print(f"[TMDBClient] API request failed (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    time.sleep(delay)
                    continue
                else:
                    raise e
        
        return None

    def get_full_poster_url(self, poster_path: str, size: str = 'w500') -> str | None:
        if not poster_path:
            return None
        # Ensure poster_path does not start with a slash if IMAGE_BASE_URL ends with one.
        if poster_path.startswith('/'):
            poster_path = poster_path[1:]
        return f"{self.IMAGE_BASE_URL}{size}/{poster_path}"

    def get_movie_details(self, tmdb_id, language=None):
        """Fetch movie details from TMDB by tmdb_id with retry logic and caching."""
        # Include language in cache key if specified
        cache_key = f"movie_details_{tmdb_id}_{language}" if language else f"movie_details_{tmdb_id}"
        cache_file_path = self._get_cache_file_path(cache_key)
        
        if self._is_cache_valid(cache_file_path):
            cached_data = self._load_from_cache(cache_file_path)
            if cached_data is not None:
                print(f"[TMDB Cache] Using cached movie details for ID: {tmdb_id} (language: {language or 'default'})")
                return cached_data
        
        url = f"{self.BASE_URL}/movie/{tmdb_id}"
        headers = {}
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        elif self.read_access_token:
            headers["Authorization"] = f"Bearer {self.read_access_token}"
        
        # Add language parameter if specified
        if language:
            params["language"] = language
            print(f"[TMDB] Fetching movie details with language: {language}")
        
        max_retries = 2
        base_delay = 0.5
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    delay = base_delay * (2 ** (attempt - 1))
                    print(f"[TMDB] Retry attempt {attempt + 1}/{max_retries} for movie details after {delay}s delay")
                    time.sleep(delay)
                
                response = requests.get(url, params=params, headers=headers, timeout=10)
                response.raise_for_status()
                data = response.json()
                self._save_to_cache(cache_file_path, data)
                print(f"[TMDB Cache] Cached movie details for ID: {tmdb_id} (language: {language or 'default'})")
                return data
            except requests.RequestException as e:
                print(f"[TMDB] Request error on movie details attempt {attempt + 1}/{max_retries}: {e}")
                if attempt == max_retries - 1:
                    raise e
            except Exception as e:
                print(f"[TMDB] Unexpected error during movie details: {e}")
                raise e

    def search_series(self, query, year=None):
        """Search for series on TMDB by query and optional year."""
        cache_key = f"series_search_{query.replace(' ', '_').lower()}_{year or 'anyyear'}"
        cache_file_path = self._get_cache_file_path(cache_key)

        if self._is_cache_valid(cache_file_path):
            cached_data = self._load_from_cache(cache_file_path)
            if cached_data is not None:
                print(f"[TMDB Cache] Using cached series search results for query: {query}")
                return cached_data
        
        url = f"{self.BASE_URL}/search/tv"
        headers = {}
        params = {"query": query}
        if self.api_key:
            params["api_key"] = self.api_key
        elif self.read_access_token:
            headers["Authorization"] = f"Bearer {self.read_access_token}"
        
        if year:
            params["first_air_date_year"] = year

        max_retries = 2
        base_delay = 0.5

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    delay = base_delay * (2 ** (attempt - 1))
                    print(f"[TMDB] Retry attempt {attempt + 1}/{max_retries} for series search after {delay}s delay")
                    time.sleep(delay)
                
                response = requests.get(url, params=params, headers=headers, timeout=10)
                response.raise_for_status()
                data = response.json()
                self._save_to_cache(cache_file_path, data)
                print(f"[TMDB Cache] Cached series search results for query: {query}")
                return data
            except requests.RequestException as e:
                print(f"[TMDB] Request error on series search attempt {attempt + 1}/{max_retries}: {e}")
                if attempt == max_retries - 1:
                    raise e
            except Exception as e:
                print(f"[TMDB] Unexpected error during series search: {e}")
                raise e
        return None # Should not be reached if retries exhausted and exception raised

    def get_series_details(self, tmdb_id, language=None):
        """Fetch series details from TMDB by tmdb_id with retry logic and caching."""
        # Include language in cache key if specified
        cache_key = f"series_details_{tmdb_id}_{language}" if language else f"series_details_{tmdb_id}"
        cache_file_path = self._get_cache_file_path(cache_key)
        
        if self._is_cache_valid(cache_file_path):
            cached_data = self._load_from_cache(cache_file_path)
            if cached_data is not None:
                print(f"[TMDB Cache] Using cached series details for ID: {tmdb_id} (language: {language or 'default'})")
                return cached_data
        
        url = f"{self.BASE_URL}/tv/{tmdb_id}"
        headers = {}
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        elif self.read_access_token:
            headers["Authorization"] = f"Bearer {self.read_access_token}"
        
        # Add language parameter if specified
        if language:
            params["language"] = language
            print(f"[TMDB] Fetching series details with language: {language}")
        
        max_retries = 2
        base_delay = 0.5
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    delay = base_delay * (2 ** (attempt - 1))
                    print(f"[TMDB] Retry attempt {attempt + 1}/{max_retries} for series details after {delay}s delay")
                    time.sleep(delay)
                
                response = requests.get(url, params=params, headers=headers, timeout=10)
                response.raise_for_status()
                data = response.json()
                self._save_to_cache(cache_file_path, data)
                print(f"[TMDB Cache] Cached series details for ID: {tmdb_id} (language: {language or 'default'})")
                return data
            except requests.RequestException as e:
                print(f"[TMDB] Request error on series details attempt {attempt + 1}/{max_retries}: {e}")
                if attempt == max_retries - 1:
                    raise e
            except Exception as e:
                print(f"[TMDB] Unexpected error during series details: {e}")
                raise e
        return None # Should not be reached


    def search_series(self, query, year=None):
        """Search for series on TMDB by query and optional year."""
        cache_key = f"series_search_{query.replace(' ', '_').lower()}_{year or 'anyyear'}"
        cache_file_path = self._get_cache_file_path(cache_key)

        if self._is_cache_valid(cache_file_path):
            cached_data = self._load_from_cache(cache_file_path)
            if cached_data is not None:
                print(f"[TMDB Cache] Using cached series search results for query: {query}")
                return cached_data
        
        url = f"{self.BASE_URL}/search/tv"
        headers = {}
        params = {"query": query}
        if self.api_key:
            params["api_key"] = self.api_key
        elif self.read_access_token:
            headers["Authorization"] = f"Bearer {self.read_access_token}"
        
        if year:
            params["first_air_date_year"] = year

        max_retries = 2
        base_delay = 0.5

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    delay = base_delay * (2 ** (attempt - 1))
                    print(f"[TMDB] Retry attempt {attempt + 1}/{max_retries} for series search after {delay}s delay")
                    time.sleep(delay)
                
                response = requests.get(url, params=params, headers=headers, timeout=10)
                response.raise_for_status()
                data = response.json()
                self._save_to_cache(cache_file_path, data)
                print(f"[TMDB Cache] Cached series search results for query: {query}")
                return data
            except requests.RequestException as e:
                print(f"[TMDB] Request error on series search attempt {attempt + 1}/{max_retries}: {e}")
                if attempt == max_retries - 1:
                    raise e
            except Exception as e:
                print(f"[TMDB] Unexpected error during series search: {e}")
                raise e
        return None # Should not be reached if retries exhausted and exception raised