from dataclasses import dataclass
from typing import List, Optional, Union
from datetime import datetime


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
    
    def get_cast_list(self) -> List[str]:
        """Get list of cast members from cast string."""
        if self.cast:
            return [c.strip() for c in self.cast.split(',') if c.strip()]
        return []