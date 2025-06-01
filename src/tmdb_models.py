"""TMDB API data models for movie and series details and credits."""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class Genre:
    """TMDB Genre model."""
    id: int
    name: str
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Genre':
        """Create Genre instance from dictionary data."""
        return cls(
            id=data.get('id', 0),
            name=data.get('name', '')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert Genre instance to dictionary."""
        return {
            'id': self.id,
            'name': self.name
        }


@dataclass
class ProductionCompany:
    """TMDB Production Company model."""
    id: int
    name: str
    logo_path: Optional[str] = None
    origin_country: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProductionCompany':
        """Create ProductionCompany instance from dictionary data."""
        return cls(
            id=data.get('id', 0),
            name=data.get('name', ''),
            logo_path=data.get('logo_path'),
            origin_country=data.get('origin_country')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ProductionCompany instance to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'logo_path': self.logo_path,
            'origin_country': self.origin_country
        }


@dataclass
class ProductionCountry:
    """TMDB Production Country model."""
    iso_3166_1: str
    name: str
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProductionCountry':
        """Create ProductionCountry instance from dictionary data."""
        return cls(
            iso_3166_1=data.get('iso_3166_1', ''),
            name=data.get('name', '')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ProductionCountry instance to dictionary."""
        return {
            'iso_3166_1': self.iso_3166_1,
            'name': self.name
        }


@dataclass
class SpokenLanguage:
    """TMDB Spoken Language model."""
    english_name: str
    iso_639_1: str
    name: str
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SpokenLanguage':
        """Create SpokenLanguage instance from dictionary data."""
        return cls(
            english_name=data.get('english_name', ''),
            iso_639_1=data.get('iso_639_1', ''),
            name=data.get('name', '')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert SpokenLanguage instance to dictionary."""
        return {
            'english_name': self.english_name,
            'iso_639_1': self.iso_639_1,
            'name': self.name
        }


@dataclass
class TMDBMovieDetails:
    """TMDB Movie Details model."""
    id: int
    title: str
    original_title: str
    overview: str
    adult: bool = False
    backdrop_path: Optional[str] = None
    belongs_to_collection: Optional[Dict[str, Any]] = None
    budget: int = 0
    genres: List[Genre] = None
    homepage: str = ''
    imdb_id: Optional[str] = None
    origin_country: List[str] = None
    original_language: str = ''
    popularity: float = 0.0
    poster_path: Optional[str] = None
    production_companies: List[ProductionCompany] = None
    production_countries: List[ProductionCountry] = None
    release_date: str = ''
    revenue: int = 0
    runtime: Optional[int] = None
    spoken_languages: List[SpokenLanguage] = None
    status: str = ''
    tagline: str = ''
    video: bool = False
    vote_average: float = 0.0
    vote_count: int = 0
    
    def __post_init__(self):
        """Initialize default values for list fields."""
        if self.genres is None:
            self.genres = []
        if self.origin_country is None:
            self.origin_country = []
        if self.production_companies is None:
            self.production_companies = []
        if self.production_countries is None:
            self.production_countries = []
        if self.spoken_languages is None:
            self.spoken_languages = []
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TMDBMovieDetails':
        """Create MovieDetails instance from dictionary data."""
        return cls(
            id=data.get('id', 0),
            title=data.get('title', ''),
            original_title=data.get('original_title', ''),
            overview=data.get('overview', ''),
            adult=data.get('adult', False),
            backdrop_path=data.get('backdrop_path'),
            belongs_to_collection=data.get('belongs_to_collection'),
            budget=data.get('budget', 0),
            genres=[Genre.from_dict(g) for g in data.get('genres', [])],
            homepage=data.get('homepage', ''),
            imdb_id=data.get('imdb_id'),
            origin_country=data.get('origin_country', []),
            original_language=data.get('original_language', ''),
            popularity=data.get('popularity', 0.0),
            poster_path=data.get('poster_path'),
            production_companies=[ProductionCompany.from_dict(pc) for pc in data.get('production_companies', [])],
            production_countries=[ProductionCountry.from_dict(pc) for pc in data.get('production_countries', [])],
            release_date=data.get('release_date', ''),
            revenue=data.get('revenue', 0),
            runtime=data.get('runtime'),
            spoken_languages=[SpokenLanguage.from_dict(sl) for sl in data.get('spoken_languages', [])],
            status=data.get('status', ''),
            tagline=data.get('tagline', ''),
            video=data.get('video', False),
            vote_average=data.get('vote_average', 0.0),
            vote_count=data.get('vote_count', 0)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert MovieDetails instance to dictionary."""
        return {
            'id': self.id,
            'title': self.title,
            'original_title': self.original_title,
            'overview': self.overview,
            'adult': self.adult,
            'backdrop_path': self.backdrop_path,
            'belongs_to_collection': self.belongs_to_collection,
            'budget': self.budget,
            'genres': [g.to_dict() for g in self.genres],
            'homepage': self.homepage,
            'imdb_id': self.imdb_id,
            'origin_country': self.origin_country,
            'original_language': self.original_language,
            'popularity': self.popularity,
            'poster_path': self.poster_path,
            'production_companies': [pc.to_dict() for pc in self.production_companies],
            'production_countries': [pc.to_dict() for pc in self.production_countries],
            'release_date': self.release_date,
            'revenue': self.revenue,
            'runtime': self.runtime,
            'spoken_languages': [sl.to_dict() for sl in self.spoken_languages],
            'status': self.status,
            'tagline': self.tagline,
            'video': self.video,
            'vote_average': self.vote_average,
            'vote_count': self.vote_count
        }
    
    def get_release_year(self) -> Optional[int]:
        """Extract release year from release_date."""
        if self.release_date:
            try:
                return int(self.release_date.split('-')[0])
            except (ValueError, IndexError):
                pass
        return None
    
    def get_runtime_hours_minutes(self) -> str:
        """Get runtime formatted as hours and minutes."""
        if self.runtime:
            hours = self.runtime // 60
            minutes = self.runtime % 60
            if hours > 0:
                return f"{hours}h {minutes}m"
            return f"{minutes}m"
        return "Unknown"
    
    def get_genres_string(self) -> str:
        """Get genres as comma-separated string."""
        return ", ".join([g.name for g in self.genres])
    
    def get_production_companies_string(self) -> str:
        """Get production companies as comma-separated string."""
        return ", ".join([pc.name for pc in self.production_companies])


@dataclass
class CastMember:
    """TMDB Cast Member model."""
    id: int
    name: str
    character: str
    adult: bool = False
    gender: Optional[int] = None
    known_for_department: str = ''
    original_name: str = ''
    popularity: float = 0.0
    profile_path: Optional[str] = None
    cast_id: Optional[int] = None
    credit_id: str = ''
    order: int = 0
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CastMember':
        """Create CastMember instance from dictionary data."""
        return cls(
            id=data.get('id', 0),
            name=data.get('name', ''),
            character=data.get('character', ''),
            adult=data.get('adult', False),
            gender=data.get('gender'),
            known_for_department=data.get('known_for_department', ''),
            original_name=data.get('original_name', ''),
            popularity=data.get('popularity', 0.0),
            profile_path=data.get('profile_path'),
            cast_id=data.get('cast_id'),
            credit_id=data.get('credit_id', ''),
            order=data.get('order', 0)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert CastMember instance to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'character': self.character,
            'adult': self.adult,
            'gender': self.gender,
            'known_for_department': self.known_for_department,
            'original_name': self.original_name,
            'popularity': self.popularity,
            'profile_path': self.profile_path,
            'cast_id': self.cast_id,
            'credit_id': self.credit_id,
            'order': self.order
        }


@dataclass
class CrewMember:
    """TMDB Crew Member model."""
    id: int
    name: str
    job: str
    department: str
    adult: bool = False
    gender: Optional[int] = None
    known_for_department: str = ''
    original_name: str = ''
    popularity: float = 0.0
    profile_path: Optional[str] = None
    credit_id: str = ''
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CrewMember':
        """Create CrewMember instance from dictionary data."""
        return cls(
            id=data.get('id', 0),
            name=data.get('name', ''),
            job=data.get('job', ''),
            department=data.get('department', ''),
            adult=data.get('adult', False),
            gender=data.get('gender'),
            known_for_department=data.get('known_for_department', ''),
            original_name=data.get('original_name', ''),
            popularity=data.get('popularity', 0.0),
            profile_path=data.get('profile_path'),
            credit_id=data.get('credit_id', '')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert CrewMember instance to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'job': self.job,
            'department': self.department,
            'adult': self.adult,
            'gender': self.gender,
            'known_for_department': self.known_for_department,
            'original_name': self.original_name,
            'popularity': self.popularity,
            'profile_path': self.profile_path,
            'credit_id': self.credit_id
        }


@dataclass
class MovieCredits:
    """TMDB Movie Credits model."""
    id: int
    cast: List[CastMember] = None
    crew: List[CrewMember] = None
    
    def __post_init__(self):
        """Initialize default values for list fields."""
        if self.cast is None:
            self.cast = []
        if self.crew is None:
            self.crew = []
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MovieCredits':
        """Create MovieCredits instance from dictionary data."""
        return cls(
            id=data.get('id', 0),
            cast=[CastMember.from_dict(c) for c in data.get('cast', [])],
            crew=[CrewMember.from_dict(c) for c in data.get('crew', [])]
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert MovieCredits instance to dictionary."""
        return {
            'id': self.id,
            'cast': [c.to_dict() for c in self.cast],
            'crew': [c.to_dict() for c in self.crew]
        }
    
    def get_main_cast(self, limit: int = 10) -> List[CastMember]:
        """Get main cast members (limited by order)."""
        return sorted(self.cast, key=lambda x: x.order)[:limit]
    
    def get_directors(self) -> List[CrewMember]:
        """Get directors from crew."""
        return [c for c in self.crew if c.job.lower() == 'director']
    
    def get_writers(self) -> List[CrewMember]:
        """Get writers from crew."""
        return [c for c in self.crew if 'writer' in c.job.lower() or 'screenplay' in c.job.lower()]
    
    def get_producers(self) -> List[CrewMember]:
        """Get producers from crew."""
        return [c for c in self.crew if 'producer' in c.job.lower()]


@dataclass
class Creator:
    """TMDB Series Creator model."""
    id: int
    name: str
    credit_id: str
    original_name: str = ''
    gender: Optional[int] = None
    profile_path: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Creator':
        """Create Creator instance from dictionary data."""
        return cls(
            id=data.get('id', 0),
            name=data.get('name', ''),
            credit_id=data.get('credit_id', ''),
            original_name=data.get('original_name', ''),
            gender=data.get('gender'),
            profile_path=data.get('profile_path')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert Creator instance to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'credit_id': self.credit_id,
            'original_name': self.original_name,
            'gender': self.gender,
            'profile_path': self.profile_path
        }


@dataclass
class Episode:
    """TMDB Episode model."""
    id: int
    name: str
    overview: str
    air_date: str
    episode_number: int
    season_number: int
    vote_average: float = 0.0
    vote_count: int = 0
    episode_type: str = ''
    production_code: str = ''
    runtime: Optional[int] = None
    still_path: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Episode':
        """Create Episode instance from dictionary data."""
        return cls(
            id=data.get('id', 0),
            name=data.get('name', ''),
            overview=data.get('overview', ''),
            air_date=data.get('air_date', ''),
            episode_number=data.get('episode_number', 0),
            season_number=data.get('season_number', 0),
            vote_average=data.get('vote_average', 0.0),
            vote_count=data.get('vote_count', 0),
            episode_type=data.get('episode_type', ''),
            production_code=data.get('production_code', ''),
            runtime=data.get('runtime'),
            still_path=data.get('still_path')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert Episode instance to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'overview': self.overview,
            'air_date': self.air_date,
            'episode_number': self.episode_number,
            'season_number': self.season_number,
            'vote_average': self.vote_average,
            'vote_count': self.vote_count,
            'episode_type': self.episode_type,
            'production_code': self.production_code,
            'runtime': self.runtime,
            'still_path': self.still_path
        }


@dataclass
class Network:
    """TMDB Network model."""
    id: int
    name: str
    logo_path: Optional[str] = None
    origin_country: str = ''
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Network':
        """Create Network instance from dictionary data."""
        return cls(
            id=data.get('id', 0),
            name=data.get('name', ''),
            logo_path=data.get('logo_path'),
            origin_country=data.get('origin_country', '')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert Network instance to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'logo_path': self.logo_path,
            'origin_country': self.origin_country
        }


@dataclass
class Season:
    """TMDB Season model."""
    id: int
    name: str
    season_number: int
    episode_count: int
    air_date: Optional[str] = None
    overview: str = ''
    poster_path: Optional[str] = None
    vote_average: float = 0.0
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Season':
        """Create Season instance from dictionary data."""
        return cls(
            id=data.get('id', 0),
            name=data.get('name', ''),
            season_number=data.get('season_number', 0),
            episode_count=data.get('episode_count', 0),
            air_date=data.get('air_date'),
            overview=data.get('overview', ''),
            poster_path=data.get('poster_path'),
            vote_average=data.get('vote_average', 0.0)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert Season instance to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'season_number': self.season_number,
            'episode_count': self.episode_count,
            'air_date': self.air_date,
            'overview': self.overview,
            'poster_path': self.poster_path,
            'vote_average': self.vote_average
        }


@dataclass
class TMDBSeriesDetails:
    """TMDB Series Details model."""
    id: int
    name: str
    original_name: str
    overview: str
    adult: bool = False
    backdrop_path: Optional[str] = None
    created_by: List[Creator] = None
    episode_run_time: List[int] = None
    first_air_date: str = ''
    genres: List[Genre] = None
    homepage: str = ''
    in_production: bool = False
    languages: List[str] = None
    last_air_date: str = ''
    last_episode_to_air: Optional[Episode] = None
    networks: List[Network] = None
    next_episode_to_air: Optional[Episode] = None
    number_of_episodes: int = 0
    number_of_seasons: int = 0
    origin_country: List[str] = None
    original_language: str = ''
    popularity: float = 0.0
    poster_path: Optional[str] = None
    production_companies: List[ProductionCompany] = None
    production_countries: List[ProductionCountry] = None
    seasons: List[Season] = None
    spoken_languages: List[SpokenLanguage] = None
    status: str = ''
    tagline: str = ''
    type: str = ''
    vote_average: float = 0.0
    vote_count: int = 0
    
    def __post_init__(self):
        """Initialize default values for list fields."""
        if self.created_by is None:
            self.created_by = []
        if self.episode_run_time is None:
            self.episode_run_time = []
        if self.genres is None:
            self.genres = []
        if self.languages is None:
            self.languages = []
        if self.networks is None:
            self.networks = []
        if self.origin_country is None:
            self.origin_country = []
        if self.production_companies is None:
            self.production_companies = []
        if self.production_countries is None:
            self.production_countries = []
        if self.seasons is None:
            self.seasons = []
        if self.spoken_languages is None:
            self.spoken_languages = []
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TMDBSeriesDetails':
        """Create SeriesDetails instance from dictionary data."""
        last_episode = data.get('last_episode_to_air')
        next_episode = data.get('next_episode_to_air')
        
        return cls(
            id=data.get('id', 0),
            name=data.get('name', ''),
            original_name=data.get('original_name', ''),
            overview=data.get('overview', ''),
            adult=data.get('adult', False),
            backdrop_path=data.get('backdrop_path'),
            created_by=[Creator.from_dict(c) for c in data.get('created_by', [])],
            episode_run_time=data.get('episode_run_time', []),
            first_air_date=data.get('first_air_date', ''),
            genres=[Genre.from_dict(g) for g in data.get('genres', [])],
            homepage=data.get('homepage', ''),
            in_production=data.get('in_production', False),
            languages=data.get('languages', []),
            last_air_date=data.get('last_air_date', ''),
            last_episode_to_air=Episode.from_dict(last_episode) if last_episode else None,
            networks=[Network.from_dict(n) for n in data.get('networks', [])],
            next_episode_to_air=Episode.from_dict(next_episode) if next_episode else None,
            number_of_episodes=data.get('number_of_episodes', 0),
            number_of_seasons=data.get('number_of_seasons', 0),
            origin_country=data.get('origin_country', []),
            original_language=data.get('original_language', ''),
            popularity=data.get('popularity', 0.0),
            poster_path=data.get('poster_path'),
            production_companies=[ProductionCompany.from_dict(pc) for pc in data.get('production_companies', [])],
            production_countries=[ProductionCountry.from_dict(pc) for pc in data.get('production_countries', [])],
            seasons=[Season.from_dict(s) for s in data.get('seasons', [])],
            spoken_languages=[SpokenLanguage.from_dict(sl) for sl in data.get('spoken_languages', [])],
            status=data.get('status', ''),
            tagline=data.get('tagline', ''),
            type=data.get('type', ''),
            vote_average=data.get('vote_average', 0.0),
            vote_count=data.get('vote_count', 0)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert SeriesDetails instance to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'original_name': self.original_name,
            'overview': self.overview,
            'adult': self.adult,
            'backdrop_path': self.backdrop_path,
            'created_by': [c.to_dict() for c in self.created_by],
            'episode_run_time': self.episode_run_time,
            'first_air_date': self.first_air_date,
            'genres': [g.to_dict() for g in self.genres],
            'homepage': self.homepage,
            'in_production': self.in_production,
            'languages': self.languages,
            'last_air_date': self.last_air_date,
            'last_episode_to_air': self.last_episode_to_air.to_dict() if self.last_episode_to_air else None,
            'networks': [n.to_dict() for n in self.networks],
            'next_episode_to_air': self.next_episode_to_air.to_dict() if self.next_episode_to_air else None,
            'number_of_episodes': self.number_of_episodes,
            'number_of_seasons': self.number_of_seasons,
            'origin_country': self.origin_country,
            'original_language': self.original_language,
            'popularity': self.popularity,
            'poster_path': self.poster_path,
            'production_companies': [pc.to_dict() for pc in self.production_companies],
            'production_countries': [pc.to_dict() for pc in self.production_countries],
            'seasons': [s.to_dict() for s in self.seasons],
            'spoken_languages': [sl.to_dict() for sl in self.spoken_languages],
            'status': self.status,
            'tagline': self.tagline,
            'type': self.type,
            'vote_average': self.vote_average,
            'vote_count': self.vote_count
        }
    
    def get_first_air_year(self) -> Optional[int]:
        """Extract first air year from first_air_date."""
        if self.first_air_date:
            try:
                return int(self.first_air_date.split('-')[0])
            except (ValueError, IndexError):
                pass
        return None
    
    def get_average_episode_runtime(self) -> Optional[int]:
        """Get average episode runtime in minutes."""
        if self.episode_run_time:
            return sum(self.episode_run_time) // len(self.episode_run_time)
        return None
    
    def get_genres_string(self) -> str:
        """Get genres as comma-separated string."""
        return ", ".join([g.name for g in self.genres])
    
    def get_creators_string(self) -> str:
        """Get creators as comma-separated string."""
        return ", ".join([c.name for c in self.created_by])
    
    def get_networks_string(self) -> str:
        """Get networks as comma-separated string."""
        return ", ".join([n.name for n in self.networks])
    
    def is_currently_airing(self) -> bool:
        """Check if series is currently airing."""
        return self.status.lower() in ['returning series', 'in production'] and self.in_production


@dataclass
class SeriesCredits:
    """TMDB Series Credits model."""
    cast: List[CastMember] = None
    crew: List[CrewMember] = None
    id: Optional[int] = None
    
    def __post_init__(self):
        """Initialize default values for list fields."""
        if self.cast is None:
            self.cast = []
        if self.crew is None:
            self.crew = []
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SeriesCredits':
        """Create SeriesCredits instance from dictionary data."""
        return cls(
            cast=[CastMember.from_dict(c) for c in data.get('cast', [])],
            crew=[CrewMember.from_dict(c) for c in data.get('crew', [])],
            id=data.get('id')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert SeriesCredits instance to dictionary."""
        result = {
            'cast': [c.to_dict() for c in self.cast],
            'crew': [c.to_dict() for c in self.crew]
        }
        if self.id is not None:
            result['id'] = self.id
        return result
    
    def get_main_cast(self, limit: int = 10) -> List[CastMember]:
        """Get main cast members (limited by order)."""
        return sorted(self.cast, key=lambda x: x.order)[:limit]
    
    def get_creators(self) -> List[CrewMember]:
        """Get creators from crew."""
        return [c for c in self.crew if c.job.lower() in ['creator', 'executive producer']]
    
    def get_directors(self) -> List[CrewMember]:
        """Get directors from crew."""
        return [c for c in self.crew if c.job.lower() == 'director']
    
    def get_writers(self) -> List[CrewMember]:
        """Get writers from crew."""
        return [c for c in self.crew if 'writer' in c.job.lower() or 'screenplay' in c.job.lower()]


@dataclass
class TMDBCacheData:
    """Wrapper for TMDB cache data with timestamp."""
    timestamp: float
    data: Dict[str, Any]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TMDBCacheData':
        """Create TMDBCacheData instance from dictionary data."""
        return cls(
            timestamp=data.get('timestamp', 0.0),
            data=data.get('data', {})
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert TMDBCacheData instance to dictionary."""
        return {
            'timestamp': self.timestamp,
            'data': self.data
        }
    
    def is_expired(self, max_age_seconds: int = 86400) -> bool:
        """Check if cache data is expired (default: 24 hours)."""
        current_time = datetime.now().timestamp()
        return (current_time - self.timestamp) > max_age_seconds