"""Constants for the IPTV application following Clean Code principles"""

class UIConstants:
    """UI-related constants"""
    DEFAULT_PAGE_SIZE = 32
    DEBOUNCE_DELAY_MS = 200
    IMAGE_SIZE = (100, 140)
    SIDEBAR_MIN_WIDTH = 220
    STATUS_BAR_ICON_SIZE = 24
    LIST_ITEM_HEIGHT = 40
    PLAYER_CONTROLS_HEIGHT = 60
    SIDEBAR_WIDTH = 250
    
class CacheConstants:
    """Cache-related constants"""
    EXPIRATION_SECONDS = 24 * 60 * 60  # 1 day
    CHUNK_SIZE = 8192
    
class APIConstants:
    """API-related constants"""
    TIMEOUT_SECONDS = 30
    MAX_RETRIES = 3
    
class MediaConstants:
    """Media playback constants"""
    DEFAULT_VOLUME = 70
    SEEK_STEP_SECONDS = 10
    VOLUME_STEP_PERCENT = 5
    
class FileConstants:
    """File and path constants"""
    IMAGE_CACHE_EXTENSION = ".jpg"
    CONFIG_DIR_NAME = ".sahabiptv"
    CACHE_SUBDIR = "cache"
    IMAGES_SUBDIR = "images"
    DATA_SUBDIR = "data"
    
class ErrorMessages:
    """Centralized error messages"""
    MISSING_CREDENTIALS = "Missing credentials"
    INVALID_CREDENTIALS = "Invalid credentials"
    SERVER_ERROR = "Server returned status code {}"
    CONNECTION_ERROR = "Connection error: {}"
    CACHE_LOAD_ERROR = "Failed to load cache: {}"
    CACHE_SAVE_ERROR = "Failed to save cache: {}"
    IMAGE_LOAD_ERROR = "Failed to load image: {}"
    
class UserMessages:
    """User-facing messages"""
    LOADING = "Loading..."
    READY = "Ready"
    LOADING_IMAGES = "Loading images..."
    NAVIGATION_ERROR = "Navigation Error"
    TAB_NOT_AVAILABLE = "{} tab is not available."