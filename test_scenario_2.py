import sys
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, '/app')

from PyQt5.QtWidgets import QApplication, QLabel
from PyQt5.QtGui import QPixmap
from src.ui.widgets.movie_details_widget import MovieDetailsWidget
from src.api.tmdb import TMDBClient
from src.utils.image_cache import ImageCache

os.environ['TMDB_READACCESS_TOKEN'] = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJjYjI5ZWU1NzcxMDIxZmNhNWE4NTE5YWRkMGE1NTQxMiIsInN1YiI6IjY2MjY1NTVjMzY2ODc1MDE3ZDNlNzM2YiIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.7L6FpWp0U5XQ89J1W8fBq_kYc8dJq0pkp0j77O_uYdM"

class MockLoadingIconController:
    def __init__(self, instance_name=""):
        self.instance_name = instance_name
        self.show_icon = self._create_mock_signal("show_icon")
        self.hide_icon = self._create_mock_signal("hide_icon")

    def _create_mock_signal(self, name):
        mock_signal_object = lambda: None 
        mock_signal_object.emit = lambda: print(f"[TEST_LOG_MOCK {self.instance_name}] MockLoadingIconController.{name}.emit() called")
        return mock_signal_object

class MockMainWindow:
    def __init__(self, instance_name=""):
        self.loading_icon_controller = MockLoadingIconController(instance_name)
        self.api_client = None

app = QApplication.instance() if QApplication.instance() else QApplication(sys.argv)

print("[TEST_SCENARIO_2] START")

movie_data = {
    'name': 'Fight Club',
    'tmdb_id': 550 
}
tmdb_poster_url = "https://image.tmdb.org/t/p/w500/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg"
expected_cache_path = ImageCache.get_cache_path(tmdb_poster_url)


# --- First Instantiation (to populate cache) ---
print("\n[TEST_SCENARIO_2] --- First Instantiation ---")
# Clear cache before the first run to ensure it's a download
if os.path.exists(expected_cache_path):
    os.remove(expected_cache_path)
    print(f"[TEST_SCENARIO_2] Cleared specific cache file: {expected_cache_path}")
# Ensure parent directories for the cache file exist for subsequent operations
ImageCache.ensure_cache_dir() # This creates /app/assets/cache/images
# We also need to ensure the specific subdirectories for TMDB urls are made if not existing
# However, get_cache_path and subsequent save in load_image_async should handle this.

tmdb_client = TMDBClient() 
mock_main_window_1 = MockMainWindow("Instance1")
poster_label_container_1 = QLabel() 

widget_1 = MovieDetailsWidget(movie=movie_data.copy(), api_client=None, main_window=mock_main_window_1, tmdb_client=tmdb_client, parent=poster_label_container_1)
print(f"[TEST_SCENARIO_2] Instance 1: Movie data after init: {widget_1.movie}")
import time
print("[TEST_SCENARIO_2] Instance 1: Waiting for image loading thread...")
time.sleep(7) 
print(f"[TEST_SCENARIO_2] Instance 1: Poster pixmap null after wait: {widget_1.poster.pixmap().isNull()}")
if os.path.exists(expected_cache_path):
    print(f"[TEST_SCENARIO_2] Instance 1: SUCCESS - Image found in cache at {expected_cache_path}")
else:
    print(f"[TEST_SCENARIO_2] Instance 1: FAILURE - Image NOT in cache at {expected_cache_path}")


# --- Second Instantiation (should hit cache) ---
print("\n[TEST_SCENARIO_2] --- Second Instantiation ---")
# Movie data for the second instance should reflect that stream_icon was updated by the first
# This simulates navigating away and back, where the application might re-fetch movie info
# or use an updated movie object. For this test, we use the updated movie object from widget_1.
movie_data_for_second_run = widget_1.movie.copy() 
# Alternatively, if the movie object isn't updated globally, we could provide the original movie_data
# and expect it to re-fetch from TMDB then hit the *download* cache if the URL is the same,
# or hit the *pixmap* cache if load_image_async itself has an in-memory pixmap cache (it doesn't explicitly).
# The key here is that the image_url given to load_image_async will be the TMDB one.

mock_main_window_2 = MockMainWindow("Instance2")
poster_label_container_2 = QLabel()

# IMPORTANT: For the cache test to be valid, the second call to load_image_async
# must use the *exact same image_url* that was used in the first call (which is now stored in widget_1.movie['stream_icon'])
print(f"[TEST_SCENARIO_2] Instance 2: Initial movie data: {movie_data_for_second_run}")

widget_2 = MovieDetailsWidget(movie=movie_data_for_second_run, api_client=None, main_window=mock_main_window_2, tmdb_client=tmdb_client, parent=poster_label_container_2)
print(f"[TEST_SCENARIO_2] Instance 2: Movie data after init: {widget_2.movie}")
# Less wait time needed if it's a cache hit, but worker thread still runs
print("[TEST_SCENARIO_2] Instance 2: Waiting for image loading thread (should be quick if cached)...")
time.sleep(1) # Shorter wait, cache hit should be fast
print(f"[TEST_SCENARIO_2] Instance 2: Poster pixmap null after wait: {widget_2.poster.pixmap().isNull()}")

print("[TEST_SCENARIO_2] END")

