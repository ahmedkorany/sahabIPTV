import sys
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, '/app')

from PyQt5.QtWidgets import QApplication, QLabel
from PyQt5.QtGui import QPixmap
from src.ui.widgets.movie_details_widget import MovieDetailsWidget
from src.api.tmdb import TMDBClient

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

# Store original TMDBClient.get_movie_details
original_get_movie_details = TMDBClient.get_movie_details

def mock_get_movie_details_no_poster(self, tmdb_id):
    print(f"[TEST_LOG_MOCK TMDBClient] mock_get_movie_details_no_poster called for tmdb_id: {tmdb_id}")
    # Simulate a valid response but with no poster_path
    # Using TMDB ID 551 (Hooligans) as an example, but forcing no poster.
    if tmdb_id == 551: # Arbitrary ID for this test
        return {
            'adult': False, 'backdrop_path': '/xRyINp9KfMLVjRiO5nCsoRDdvvF.jpg', 
            'id': tmdb_id, 'original_title': 'Movie With No Poster', 
            'poster_path': None, # Key for this test
            'overview': 'This movie exists but has no poster in this mock.',
            'release_date': '2000-01-01'
        }
    # Fallback to original method if a different ID is somehow used
    return original_get_movie_details(self, tmdb_id)

app = QApplication.instance() if QApplication.instance() else QApplication(sys.argv)

print("[TEST_SCENARIO_3] START")

# --- Test Scenario 3 ---
print("\n[TEST_SCENARIO_3] --- Movie with tmdb_id but TMDB returns no poster_path ---")

movie_data_3 = {
    'name': 'Movie With No Poster',
    'tmdb_id': 551 # ID we will mock to have no poster
}
print(f"[TEST_SCENARIO_3] Initial movie_data_3: {movie_data_3}")

# Apply the mock
TMDBClient.get_movie_details = mock_get_movie_details_no_poster
print("[TEST_SCENARIO_3] TMDBClient.get_movie_details has been mocked.")

tmdb_client_mocked = TMDBClient()
mock_main_window_3 = MockMainWindow("Instance3")
poster_label_container_3 = QLabel() 

widget_3 = MovieDetailsWidget(movie=movie_data_3.copy(), api_client=None, main_window=mock_main_window_3, tmdb_client=tmdb_client_mocked, parent=poster_label_container_3)
print(f"[TEST_SCENARIO_3] Movie data after MovieDetailsWidget init: {widget_3.movie}")

import time
print("[TEST_SCENARIO_3] Waiting briefly (no download expected)...")
time.sleep(1) # Shorter wait as no download should occur

print(f"[TEST_SCENARIO_3] Poster label pixmap null after wait: {widget_3.poster.pixmap().isNull()}")
# If the default placeholder is set, the pixmap won't be null if the placeholder file exists and is valid.
# We check if stream_icon was updated. It should NOT be.
print(f"[TEST_SCENARIO_3] Movie data after wait: {widget_3.movie}")
if 'stream_icon' not in widget_3.movie or widget_3.movie['stream_icon'] is None:
    print("[TEST_SCENARIO_3] SUCCESS: movie.stream_icon was not set with a TMDB URL.")
else:
    print(f"[TEST_SCENARIO_3] FAILURE: movie.stream_icon was unexpectedly set to: {widget_3.movie.get('stream_icon')}")

# Restore original method
TMDBClient.get_movie_details = original_get_movie_details
print("[TEST_SCENARIO_3] TMDBClient.get_movie_details has been restored.")

print("[TEST_SCENARIO_3] END")

