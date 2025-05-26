import sys
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, '/app')

from PyQt5.QtWidgets import QApplication, QLabel
from PyQt5.QtGui import QPixmap
from src.ui.widgets.movie_details_widget import MovieDetailsWidget
# TMDBClient might not be strictly needed if it's not even constructed or called
# but importing for consistency in test structure
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

app = QApplication.instance() if QApplication.instance() else QApplication(sys.argv)

print("[TEST_SCENARIO_4] START")

# --- Test Scenario 4 ---
print("\n[TEST_SCENARIO_4] --- Movie with no stream_icon and no tmdb_id ---")

movie_data_4_a = {
    'name': 'Movie With Nothing'
    # stream_icon is missing
    # tmdb_id is missing
}
print(f"[TEST_SCENARIO_4] Initial movie_data_4_a: {movie_data_4_a}")

# tmdb_client can be None here as it shouldn't be used if tmdb_id is missing
tmdb_client_for_test = TMDBClient() # Or None, but MovieDetailsWidget expects a client object or None
mock_main_window_4a = MockMainWindow("Instance4a")
poster_label_container_4a = QLabel() 

widget_4a = MovieDetailsWidget(movie=movie_data_4_a.copy(), api_client=None, main_window=mock_main_window_4a, tmdb_client=tmdb_client_for_test, parent=poster_label_container_4a)
print(f"[TEST_SCENARIO_4] Movie data after MovieDetailsWidget init (4a): {widget_4a.movie}")
print(f"[TEST_SCENARIO_4] Poster label pixmap null after init (4a): {widget_4a.poster.pixmap().isNull()}")
if 'stream_icon' not in widget_4a.movie or widget_4a.movie['stream_icon'] is None:
    print("[TEST_SCENARIO_4] SUCCESS (4a): movie.stream_icon is not set.")
else:
    print(f"[TEST_SCENARIO_4] FAILURE (4a): movie.stream_icon was unexpectedly set to: {widget_4a.movie.get('stream_icon')}")

print("\n[TEST_SCENARIO_4] --- Movie with no stream_icon and tmdb_id is None ---")
movie_data_4_b = {
    'name': 'Movie With tmdb_id as None',
    'tmdb_id': None # Explicitly None
}
print(f"[TEST_SCENARIO_4] Initial movie_data_4_b: {movie_data_4_b}")

mock_main_window_4b = MockMainWindow("Instance4b")
poster_label_container_4b = QLabel() 

widget_4b = MovieDetailsWidget(movie=movie_data_4_b.copy(), api_client=None, main_window=mock_main_window_4b, tmdb_client=tmdb_client_for_test, parent=poster_label_container_4b)
print(f"[TEST_SCENARIO_4] Movie data after MovieDetailsWidget init (4b): {widget_4b.movie}")
print(f"[TEST_SCENARIO_4] Poster label pixmap null after init (4b): {widget_4b.poster.pixmap().isNull()}")
if 'stream_icon' not in widget_4b.movie or widget_4b.movie['stream_icon'] is None:
    print("[TEST_SCENARIO_4] SUCCESS (4b): movie.stream_icon is not set.")
else:
    print(f"[TEST_SCENARIO_4] FAILURE (4b): movie.stream_icon was unexpectedly set to: {widget_4b.movie.get('stream_icon')}")

print("[TEST_SCENARIO_4] END")

