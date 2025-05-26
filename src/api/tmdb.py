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
        """Fetch movie details from TMDB by tmdb_id."""
        url = f"{self.BASE_URL}/movie/{tmdb_id}"
        headers = {}
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        elif self.read_access_token:
            headers["Authorization"] = f"Bearer {self.read_access_token}"
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()