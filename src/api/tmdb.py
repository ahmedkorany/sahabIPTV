import os
import requests
from dotenv import load_dotenv

class TMDBClient:
    BASE_URL = "https://api.themoviedb.org/3"
    IMAGE_BASE_URL = "https://image.tmdb.org/t/p/"

    def __init__(self, api_key=None, read_access_token=None):
        # Load from .env if not provided
        load_dotenv()
        self.api_key = api_key or os.getenv("TMDB_APIACCESS_TOKEN")
        self.read_access_token = read_access_token or os.getenv("TMDB_READACCESS_TOKEN")
        if not self.api_key and not self.read_access_token:
            raise ValueError("TMDB API key or Read Access Token must be set in .env or passed to TMDBClient.")

    def get_movie_credits(self, tmdb_id):
        url = f"{self.BASE_URL}/movie/{tmdb_id}/credits"
        headers = {}
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        elif self.read_access_token:
            headers["Authorization"] = f"Bearer {self.read_access_token}"
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()

    def get_full_poster_url(self, poster_path: str, size: str = 'w500') -> str | None:
        if not poster_path:
            return None
        # Ensure poster_path does not start with a slash if IMAGE_BASE_URL ends with one.
        if poster_path.startswith('/'):
            poster_path = poster_path[1:]
        return f"{self.IMAGE_BASE_URL}{size}/{poster_path}"

    def get_movie_details(self, tmdb_id):
        """Fetch movie details from TMDB by tmdb_id with retry logic."""
        url = f"{self.BASE_URL}/movie/{tmdb_id}"
        headers = {}
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        elif self.read_access_token:
            headers["Authorization"] = f"Bearer {self.read_access_token}"
        
        # Retry logic for TMDB API calls
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
                return response.json()
                
            except requests.RequestException as e:
                print(f"[TMDB] Request error on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt == max_retries - 1:  # Last attempt
                    raise e
                # Continue to next retry attempt
            except Exception as e:
                print(f"[TMDB] Unexpected error: {e}")
                raise e