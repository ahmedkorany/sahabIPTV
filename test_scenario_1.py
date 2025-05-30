import sys
import os
# Set Qt platform to offscreen BEFORE importing any Qt modules
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

# Add src to path to allow imports like src.api.tmdb
sys.path.insert(0, '/app')

from PyQt5.QtWidgets import QApplication, QLabel
from PyQt5.QtGui import QPixmap
from src.ui.widgets.movie_details_widget import MovieDetailsWidget
from src.api.tmdb import TMDBClient
from src.utils.image_cache import ImageCache # Import ImageCache to use its methods

# Ensure TMDB_READACCESS_TOKEN is set for the test if TMDB_API_KEY is not
os.environ['TMDB_READACCESS_TOKEN'] = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJjYjI5ZWU1NzcxMDIxZmNhNWE4NTE5YWRkMGE1NTQxMiIsInN1YiI6IjY2MjY1NTVjMzY2ODc1MDE3ZDNlNzM2YiIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.7L6FpWp0U5XQ89J1W8fBq_kYc8dJq0pkp0j77O_uYdM"


# Mock main_window and api_client
class MockLoadingIconController:
    def __init__(self):
        self.show_icon = self._create_mock_signal("show_icon")
        self.hide_icon = self._create_mock_signal("hide_icon")

    def _create_mock_signal(self, name):
        mock_signal_object = lambda: None 
        mock_signal_object.emit = lambda: print(f"[TEST_LOG_MOCK] MockLoadingIconController.{name}.emit() called")
        return mock_signal_object

class MockMainWindow:
    def __init__(self):
        self.loading_icon_controller = MockLoadingIconController()
        self.api_client = None

# Initialize QApplication
app = QApplication.instance() if QApplication.instance() else QApplication(sys.argv)

print("[TEST_SCENARIO_1] START")

movie_data_1 = {
    'name': 'Fight Club',
    'tmdb_id': 550 
}
print(f"[TEST_SCENARIO_1] Initial movie_data_1: {movie_data_1}")

tmdb_client = TMDBClient() 
mock_main_window = MockMainWindow()
poster_label_container = QLabel() 

widget_1 = MovieDetailsWidget(movie=movie_data_1.copy(), api_client=None, main_window=mock_main_window, tmdb_client=tmdb_client, parent=poster_label_container)

print(f"[TEST_SCENARIO_1] Movie data after MovieDetailsWidget init: {widget_1.movie}")

import time
print("[TEST_SCENARIO_1] Waiting for image loading thread...")
time.sleep(7) 

print(f"[TEST_SCENARIO_1] Poster label pixmap null after wait: {widget_1.poster.pixmap().isNull()}")
print(f"[TEST_SCENARIO_1] Movie data after wait: {widget_1.movie}")

# Check cache content
print("[TEST_SCENARIO_1] Checking cache content...")
expected_poster_url = "https://image.tmdb.org/t/p/w500/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg"
expected_cache_path = ImageCache.get_cache_path(expected_poster_url)
print(f"[TEST_SCENARIO_1] Expected cache path: {expected_cache_path}")

if os.path.exists(expected_cache_path):
    print(f"[TEST_SCENARIO_1] SUCCESS: Expected poster image found in cache at {expected_cache_path}.")
else:
    print(f"[TEST_SCENARIO_1] FAILURE: Expected poster image NOT found in cache at {expected_cache_path}.")
    # Listing directory content for debugging if file not found
    cache_base_dir = "/app/assets/cache/images/"
    if os.path.exists(cache_base_dir):
        for root, dirs, files in os.walk(cache_base_dir):
            print(f"[TEST_SCENARIO_1] Cache content - Root: {root}, Dirs: {dirs}, Files: {files}")

print("[TEST_SCENARIO_1] END")

