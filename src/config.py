"""
Configuration settings for the application
"""
import os
from PyQt5.QtCore import QSize

# Application settings
APP_NAME = "Sahab IPTV"
APP_VERSION = "2.0.0"
DARK_MODE = True
DEFAULT_LANGUAGE = "en"  # en or ar

# Player settings
DEFAULT_VOLUME = 70
SEEK_STEP = 10  # seconds
VOLUME_STEP = 5  # percent

# UI settings
WINDOW_SIZE = (1280, 800)
PLAYER_CONTROLS_HEIGHT = 60
SIDEBAR_WIDTH = 250
LIST_ITEM_HEIGHT = 40
ICON_SIZE = QSize(24, 24)

# Cache settings
CONFIG_DIR = os.path.expanduser("~/.sahabiptv") # Base dir for config files
CACHE_DIR = os.path.join(CONFIG_DIR, "cache")
OFFLINE_MOVIES_DIR = os.path.join(CACHE_DIR, "offline_movies")
OFFLINE_METADATA_FILE = os.path.join(CONFIG_DIR, "offline_movies.json")
FAVORITES_FILE = os.path.join(CONFIG_DIR, "favorites.json") # Updated to use CONFIG_DIR
SETTINGS_FILE = os.path.join(CONFIG_DIR, "settings.json") # Updated to use CONFIG_DIR

# Create directories if they don't exist
os.makedirs(CONFIG_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(OFFLINE_MOVIES_DIR, exist_ok=True)
# os.makedirs(os.path.dirname(FAVORITES_FILE), exist_ok=True) # No longer needed as CONFIG_DIR is created

# API settings
API_TIMEOUT = 30  # seconds
API_RETRIES = 3

# Download settings
DOWNLOAD_CHUNK_SIZE = 8192  # bytes
