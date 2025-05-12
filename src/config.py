"""
Configuration settings for the application
"""
import os
from PyQt5.QtCore import QSize

# Application settings
APP_NAME = "Sahab IPTV"
APP_VERSION = "1.0.0"
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
CACHE_DIR = os.path.expanduser("~/.sahabiptv/cache")
FAVORITES_FILE = os.path.expanduser("~/.sahabiptv/favorites.json")
SETTINGS_FILE = os.path.expanduser("~/.sahabiptv/settings.json")

# Create cache directory if it doesn't exist
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(os.path.dirname(FAVORITES_FILE), exist_ok=True)

# API settings
API_TIMEOUT = 30  # seconds
API_RETRIES = 3

# Download settings
DOWNLOAD_CHUNK_SIZE = 8192  # bytes
