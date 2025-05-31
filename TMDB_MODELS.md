# TMDB Data Models

This document describes the TMDB (The Movie Database) API data models implemented for the sahabIPTV application.

## Overview

The TMDB models are designed to handle data from The Movie Database API, providing structured representations of movies, TV series, cast, crew, and related metadata. These models follow clean code principles with proper encapsulation, type hints, and comprehensive documentation.

## Model Categories

### Core Models

#### MovieDetails
Represents detailed information about a movie from TMDB.

**Key Fields:**
- `id`: TMDB movie ID
- `title`: Movie title
- `overview`: Plot summary
- `release_date`: Release date (YYYY-MM-DD)
- `runtime`: Duration in minutes
- `genres`: List of Genre objects
- `production_companies`: List of ProductionCompany objects
- `vote_average`: TMDB rating (0-10)
- `poster_path`: Poster image path
- `backdrop_path`: Backdrop image path

**Usage Example:**
```python
from src.tmdb_models import MovieDetails

# From API response
movie_data = api_response['data']
movie = MovieDetails.from_dict(movie_data)

# Access properties
print(f"Title: {movie.title}")
print(f"Year: {movie.get_release_year()}")
print(f"Runtime: {movie.get_runtime_hours_minutes()}")
print(f"Genres: {movie.get_genres_string()}")
```

#### SeriesDetails
Represents detailed information about a TV series from TMDB.

**Key Fields:**
- `id`: TMDB series ID
- `name`: Series name
- `overview`: Series description
- `first_air_date`: First air date
- `number_of_seasons`: Total seasons
- `number_of_episodes`: Total episodes
- `created_by`: List of Creator objects
- `networks`: List of Network objects
- `seasons`: List of Season objects

**Usage Example:**
```python
from src.tmdb_models import SeriesDetails

series_data = api_response['data']
series = SeriesDetails.from_dict(series_data)

print(f"Series: {series.name}")
print(f"Seasons: {series.number_of_seasons}")
print(f"Status: {series.status}")
print(f"Currently Airing: {series.is_currently_airing()}")
```

#### MovieCredits
Represents cast and crew information for a movie.

**Key Fields:**
- `id`: TMDB movie ID
- `cast`: List of CastMember objects
- `crew`: List of CrewMember objects

**Usage Example:**
```python
from src.tmdb_models import MovieCredits

credits_data = api_response['data']
credits = MovieCredits.from_dict(credits_data)

# Get main cast (first 5)
main_cast = credits.get_main_cast(5)
for actor in main_cast:
    print(f"{actor.name} as {actor.character}")

# Get directors
directors = credits.get_directors()
for director in directors:
    print(f"Director: {director.name}")
```

#### SeriesCredits
Represents cast and crew information for a TV series.

**Key Fields:**
- `cast`: List of CastMember objects
- `crew`: List of CrewMember objects
- `id`: Optional TMDB series ID

### Supporting Models

#### Genre
Represents a movie/series genre.
- `id`: TMDB genre ID
- `name`: Genre name (e.g., "Action", "Comedy")

#### CastMember
Represents an actor in a movie/series.
- `name`: Actor's name
- `character`: Character name
- `profile_path`: Actor's photo path
- `order`: Billing order

#### CrewMember
Represents a crew member (director, writer, etc.).
- `name`: Person's name
- `job`: Job title (e.g., "Director", "Writer")
- `department`: Department (e.g., "Directing", "Writing")

#### ProductionCompany
Represents a production company.
- `name`: Company name
- `logo_path`: Company logo path
- `origin_country`: Country of origin

#### Network
Represents a TV network.
- `name`: Network name
- `logo_path`: Network logo path
- `origin_country`: Country of origin

#### Season
Represents a TV series season.
- `season_number`: Season number
- `episode_count`: Number of episodes
- `air_date`: Season air date
- `poster_path`: Season poster path

#### Episode
Represents a TV series episode.
- `episode_number`: Episode number
- `season_number`: Season number
- `name`: Episode title
- `air_date`: Episode air date
- `runtime`: Episode duration

## Cache Integration

#### TMDBCacheData
Wrapper for cached TMDB data with timestamp.

**Usage Example:**
```python
from src.tmdb_models import TMDBCacheData
import json

# Load from cache file
with open('assets/cache/tmdb/movie_details_123.json', 'r') as f:
    cache_data = json.load(f)

cache = TMDBCacheData.from_dict(cache_data)

# Check if expired (default: 24 hours)
if cache.is_expired():
    print("Cache expired, need to refresh")
else:
    movie = MovieDetails.from_dict(cache.data)
```

## Design Principles

### Clean Code Implementation

1. **Single Responsibility**: Each model represents one specific entity
2. **Encapsulation**: Private data with public methods for access
3. **Type Safety**: Comprehensive type hints throughout
4. **Immutability**: Dataclasses with frozen=False for flexibility
5. **Documentation**: Comprehensive docstrings for all classes and methods

### Error Handling

- Graceful handling of missing or invalid data
- Default values for optional fields
- Type conversion with fallbacks
- Validation in `from_dict` methods

### Performance Considerations

- Lazy initialization of list fields in `__post_init__`
- Efficient sorting and filtering methods
- Minimal memory footprint with optional fields

## Integration with Existing Code

The TMDB models are designed to integrate seamlessly with the existing codebase:

1. **API Integration**: Use with `src/api/tmdb.py`
2. **Cache Management**: Compatible with `src/services/cache_manager.py`
3. **UI Components**: Provide data for movie/series detail widgets
4. **Search Functionality**: Enhance search results with rich metadata

## File Structure

```
src/
├── tmdb_models.py          # TMDB data models
├── models.py               # Existing Xtream models
├── api/
│   └── tmdb.py            # TMDB API client
└── services/
    └── cache_manager.py    # Cache management
```

## Usage Patterns

### Loading Movie Details
```python
# From cache
cache_data = load_cache_file('movie_details_123.json')
cache = TMDBCacheData.from_dict(cache_data)
movie = MovieDetails.from_dict(cache.data)

# From API
api_response = tmdb_client.get_movie_details(123)
movie = MovieDetails.from_dict(api_response)
```

### Loading Series with Credits
```python
# Load series details
series_data = load_cache_file('series_details_456.json')
series = SeriesDetails.from_dict(series_data['data'])

# Load series credits
credits_data = load_cache_file('series_credits_456.json')
credits = SeriesCredits.from_dict(credits_data['data'])

# Combine information
print(f"Series: {series.name}")
print(f"Created by: {series.get_creators_string()}")
print(f"Main cast: {', '.join([c.name for c in credits.get_main_cast(3)])}")
```

### Converting to Display Format
```python
# For UI display
movie_display = {
    'title': movie.title,
    'year': movie.get_release_year(),
    'runtime': movie.get_runtime_hours_minutes(),
    'genres': movie.get_genres_string(),
    'rating': f"{movie.vote_average:.1f}/10",
    'poster_url': f"https://image.tmdb.org/t/p/w500{movie.poster_path}"
}
```

## Future Enhancements

1. **Validation**: Add field validation decorators
2. **Serialization**: Add JSON schema validation
3. **Caching**: Implement automatic cache refresh
4. **Localization**: Support for multiple languages
5. **Images**: Add image URL generation helpers
6. **Search**: Add search-specific model variants

## Testing

The models include comprehensive test coverage:

```python
# Example test
def test_movie_details_from_dict():
    data = {
        'id': 123,
        'title': 'Test Movie',
        'runtime': 120,
        'genres': [{'id': 1, 'name': 'Action'}]
    }
    
    movie = MovieDetails.from_dict(data)
    assert movie.id == 123
    assert movie.title == 'Test Movie'
    assert movie.get_runtime_hours_minutes() == '2h 0m'
    assert len(movie.genres) == 1
    assert movie.genres[0].name == 'Action'
```

This comprehensive model system provides a robust foundation for handling TMDB data throughout the application while maintaining clean code principles and ensuring type safety.