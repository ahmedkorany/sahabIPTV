from dataclasses import dataclass
from typing import List, Optional, Union
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .tmdb_models import TMDBMovieDetails


@dataclass
class SeriesItem:
    """Data model for series items received from Xtream server."""
    
    # Required fields
    num: int
    name: str
    series_id: int
    
    # Optional fields with defaults
    cover: Optional[str] = None
    plot: Optional[str] = None
    cast: Optional[str] = None
    director: Optional[str] = None
    genre: Optional[str] = None
    releaseDate: Optional[str] = None
    last_modified: Optional[str] = None
    rating: Optional[str] = None
    rating_5based: Optional[int] = None
    backdrop_path: Optional[List[str]] = None
    youtube_trailer: Optional[str] = None
    episode_run_time: Optional[str] = None
    category_id: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> 'SeriesItem':
        """Create SeriesItem instance from dictionary data."""
        return cls(
            num=data.get('num', 0),
            name=data.get('name', ''),
            series_id=data.get('series_id', 0),
            cover=data.get('cover'),
            plot=data.get('plot'),
            cast=data.get('cast'),
            director=data.get('director'),
            genre=data.get('genre'),
            releaseDate=data.get('releaseDate'),
            last_modified=data.get('last_modified'),
            rating=data.get('rating'),
            rating_5based=data.get('rating_5based'),
            backdrop_path=data.get('backdrop_path'),
            youtube_trailer=data.get('youtube_trailer'),
            episode_run_time=data.get('episode_run_time'),
            category_id=data.get('category_id')
        )
    
    def to_dict(self) -> dict:
        """Convert SeriesItem instance to dictionary."""
        return {
            'num': self.num,
            'name': self.name,
            'series_id': self.series_id,
            'cover': self.cover,
            'plot': self.plot,
            'cast': self.cast,
            'director': self.director,
            'genre': self.genre,
            'releaseDate': self.releaseDate,
            'last_modified': self.last_modified,
            'rating': self.rating,
            'rating_5based': self.rating_5based,
            'backdrop_path': self.backdrop_path,
            'youtube_trailer': self.youtube_trailer,
            'episode_run_time': self.episode_run_time,
            'category_id': self.category_id
        }
    
    def get_release_year(self) -> Optional[int]:
        """Extract release year from releaseDate."""
        if self.releaseDate:
            try:
                return int(self.releaseDate.split('-')[0])
            except (ValueError, IndexError):
                pass
        return None
    
    def has_tmdb_details(self) -> bool:
        """Check if TMDB details are available for this movie."""
        return self.tmdb_details is not None
    
    def get_tmdb_details(self) -> Optional['TMDBMovieDetails']:
        """Get TMDB details if available."""
        return self.tmdb_details
    
    def set_tmdb_details(self, details: 'TMDBMovieDetails') -> None:
        """Set TMDB details for this movie."""
        self.tmdb_details = details
    
    def get_rating_float(self) -> float:
        """Get rating as float value."""
        if self.rating:
            try:
                return float(self.rating)
            except ValueError:
                pass
        return 0.0
    
    def get_runtime_minutes(self) -> Optional[int]:
        """Get episode runtime in minutes."""
        if self.episode_run_time:
            try:
                return int(self.episode_run_time)
            except ValueError:
                pass
        return None
    
    def get_sort_date_value(self) -> int:
        """Get comparable date value for sorting (YYYYMMDD format)."""
        if self.releaseDate:
            try:
                date_parts = self.releaseDate.split('-')
                if len(date_parts) >= 1 and date_parts[0].isdigit():
                    year = int(date_parts[0])
                    month = int(date_parts[1]) if len(date_parts) > 1 and date_parts[1].isdigit() else 1
                    day = int(date_parts[2]) if len(date_parts) > 2 and date_parts[2].isdigit() else 1
                    return year * 10000 + month * 100 + day
            except (ValueError, IndexError):
                pass
        return 0
    
    def get_display_name(self) -> str:
        """Get display name for UI."""
        return self.name or f"Series {self.series_id}"
    
    def has_cover_image(self) -> bool:
        """Check if series has a cover image."""
        return bool(self.cover and self.cover.strip())
    
    def has_backdrop_images(self) -> bool:
        """Check if series has backdrop images."""
        return bool(self.backdrop_path and len(self.backdrop_path) > 0)
    
    def get_genres_list(self) -> List[str]:
        """Get list of genres from genre string."""
        if self.genre:
            return [g.strip() for g in self.genre.split('/') if g.strip()]
        return []


@dataclass
class MovieItem:
    """Data model for movie items received from Xtream server."""
    
    # Required fields
    num: int
    name: str
    stream_id: int
    
    # Optional fields with defaults
    stream_icon: Optional[str] = None
    plot: Optional[str] = None
    cast: Optional[str] = None
    director: Optional[str] = None
    genre: Optional[str] = None
    releaseDate: Optional[str] = None
    added: Optional[str] = None
    rating: Optional[str] = None
    rating_5based: Optional[int] = None
    backdrop_path: Optional[List[str]] = None
    youtube_trailer: Optional[str] = None
    duration: Optional[str] = None
    category_id: Optional[str] = None
    container_extension: Optional[str] = None
    tmdb_id: Optional[str] = None
    year: Optional[str] = None
    adult: Optional[bool] = None
    tmdb_details: Optional['TMDBMovieDetails'] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> 'MovieItem':
        """Create MovieItem instance from dictionary data."""
        from .tmdb_models import TMDBMovieDetails
        
        # Handle TMDB details if present in cache
        tmdb_details = None
        if 'tmdb_details' in data and data['tmdb_details']:
            tmdb_details = TMDBMovieDetails.from_dict(data['tmdb_details'])
        
        return cls(
            num=data.get('num', 0),
            name=data.get('name', ''),
            stream_id=data.get('stream_id', 0),
            stream_icon=data.get('stream_icon'),
            plot=data.get('plot'),
            cast=data.get('cast'),
            director=data.get('director'),
            genre=data.get('genre'),
            releaseDate=data.get('releaseDate'),
            added=data.get('added'),
            rating=data.get('rating'),
            rating_5based=data.get('rating_5based'),
            backdrop_path=data.get('backdrop_path'),
            youtube_trailer=data.get('youtube_trailer'),
            duration=data.get('duration'),
            category_id=data.get('category_id'),
            container_extension=data.get('container_extension'),
            tmdb_id=data.get('tmdb_id'),
            year=data.get('year'),
            adult=data.get('adult'),
            tmdb_details=tmdb_details
        )
    
    def to_dict(self) -> dict:
        """Convert MovieItem instance to dictionary."""
        result = {
            'num': self.num,
            'name': self.name,
            'stream_id': self.stream_id,
            'stream_icon': self.stream_icon,
            'plot': self.plot,
            'cast': self.cast,
            'director': self.director,
            'genre': self.genre,
            'releaseDate': self.releaseDate,
            'added': self.added,
            'rating': self.rating,
            'rating_5based': self.rating_5based,
            'backdrop_path': self.backdrop_path,
            'youtube_trailer': self.youtube_trailer,
            'duration': self.duration,
            'category_id': self.category_id,
            'container_extension': self.container_extension,
            'tmdb_id': self.tmdb_id,
            'year': self.year,
            'adult': self.adult
        }
        
        # Include TMDB details if available
        if self.tmdb_details:
            result['tmdb_details'] = self.tmdb_details.to_dict()
        
        return result
    
    def get_release_year(self) -> Optional[int]:
        """Extract release year from releaseDate or year field."""
        # Try year field first
        if self.year:
            try:
                return int(self.year)
            except (ValueError, TypeError):
                pass
        
        # Fallback to releaseDate
        if self.releaseDate:
            try:
                return int(self.releaseDate.split('-')[0])
            except (ValueError, IndexError):
                pass
        return None
    
    def has_tmdb_details(self) -> bool:
        """Check if TMDB details are available for this movie."""
        return self.tmdb_details is not None
    
    def get_tmdb_details(self) -> Optional['TMDBMovieDetails']:
        """Get TMDB details if available."""
        return self.tmdb_details
    
    def set_tmdb_details(self, details: 'TMDBMovieDetails') -> None:
        """Set TMDB details for this movie."""
        self.tmdb_details = details
    
    def get_rating_float(self) -> float:
        """Get rating as float value."""
        if self.rating:
            try:
                return float(self.rating)
            except (ValueError, TypeError):
                pass
        return 0.0
    
    def get_duration_minutes(self) -> Optional[int]:
        """Get movie duration in minutes."""
        if self.duration:
            try:
                return int(self.duration)
            except (ValueError, TypeError):
                pass
        return None
    
    def get_sort_date_value(self) -> int:
        """Get comparable date value for sorting (timestamp or YYYYMMDD format)."""
        # Try added timestamp first
        if self.added:
            try:
                return int(self.added)
            except (ValueError, TypeError):
                pass
        
        # Fallback to release date
        if self.releaseDate:
            try:
                date_parts = self.releaseDate.split('-')
                if len(date_parts) >= 1 and date_parts[0].isdigit():
                    year = int(date_parts[0])
                    month = int(date_parts[1]) if len(date_parts) > 1 and date_parts[1].isdigit() else 1
                    day = int(date_parts[2]) if len(date_parts) > 2 and date_parts[2].isdigit() else 1
                    return year * 10000 + month * 100 + day
            except (ValueError, IndexError):
                pass
        return 0
    
    def get_display_name(self) -> str:
        """Get display name for UI."""
        return self.name or f"Movie {self.stream_id}"
    
    def has_poster_image(self) -> bool:
        """Check if movie has a poster image."""
        return bool(self.stream_icon and self.stream_icon.strip())
    
    def has_backdrop_images(self) -> bool:
        """Check if movie has backdrop images."""
        return bool(self.backdrop_path and len(self.backdrop_path) > 0)
    
    def get_genres_list(self) -> List[str]:
        """Get list of genres from genre string."""
        if self.genre:
            return [g.strip() for g in self.genre.split('/') if g.strip()]
        return []
    
    def get_cast_list(self) -> List[str]:
        """Get list of cast members from cast string."""
        if self.cast:
            return [c.strip() for c in self.cast.split(',') if c.strip()]
        return []
    
    def is_adult_content(self) -> bool:
        """Check if movie is adult content."""
        return bool(self.adult)
    
    def get_stream_url(self, api_client, container_extension: Optional[str] = None) -> Optional[str]:
        """Get the streaming URL for this movie."""
        if not api_client:
            return None
        
        extension = container_extension or self.container_extension or 'mp4'
        return api_client.get_movie_url(self.stream_id, extension)
    
    def is_adult_content(self) -> bool:
        """Check if movie is adult content."""
        return bool(self.adult)