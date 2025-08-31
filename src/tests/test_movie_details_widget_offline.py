import unittest
from unittest.mock import MagicMock, patch

# Ensure QApplication instance exists for widget testing, if not already handled by test runner
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QObject # For mocking main_window if it's a QObject

# Import the widget to be tested and its dependencies that need mocking
from src.ui.widgets.movie_details_widget import MovieDetailsWidget
from src.utils.offline_manager import OfflineManager # For status constants

# Minimal application setup if not run via a Qt-aware test runner
app = None
def qapplication_instance():
    global app
    if app is None:
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
    return app


class TestMovieDetailsWidgetOffline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = qapplication_instance()

    def setUp(self):
        # Mock OfflineManager
        self.mock_offline_manager = MagicMock(spec=OfflineManager)

        # Mock main_window and attach the offline_manager to it
        # If main_window is a QObject, mock it as such, otherwise a simple MagicMock
        self.mock_main_window = MagicMock(spec=QObject) # Or MagicMock() if no QObject features needed
        self.mock_main_window.offline_manager = self.mock_offline_manager
        self.mock_main_window.language = 'en' # For translations
        # Mock favorites_manager if MovieDetailsWidget interacts with it directly or via main_window
        self.mock_main_window.favorites_manager = MagicMock()


        # Mock api_client
        self.mock_api_client = MagicMock()

        # Mock tmdb_client
        self.mock_tmdb_client = MagicMock()

        # Sample movie data
        self.sample_movie_data = {
            'stream_id': '12345',
            'name': 'Test Offline Movie',
            'stream_icon': 'http://example.com/icon.png',
            'container_extension': 'mp4',
            'tmdb_id': 'tmdb123'
            # Add other fields MovieDetailsWidget might expect
        }

        # Create MovieDetailsWidget instance
        # Ensure all required arguments for MovieDetailsWidget constructor are provided
        self.widget = MovieDetailsWidget(
            movie=self.sample_movie_data,
            api_client=self.mock_api_client,
            main_window=self.mock_main_window, # Pass the mock main_window
            tmdb_client=self.mock_tmdb_client
        )
        # Ensure stream_id is set on the widget for _update_download_ui
        self.widget.stream_id = self.sample_movie_data['stream_id']


    def tearDown(self):
        # Clean up widget if necessary, though Qt might handle it with WA_DeleteOnClose
        # self.widget.deleteLater() # If not parented and need explicit cleanup
        pass

    def test_ui_status_not_downloaded(self):
        self.mock_offline_manager.get_movie_status.return_value = None # Not in manager's list
        self.widget._update_download_ui() # Call the UI update method

        self.assertEqual(self.widget.download_action_button.text(), "Download")
        self.assertFalse(self.widget.download_progress_bar.isVisible())
        self.assertFalse(self.widget.cancel_download_button.isVisible())
        self.assertFalse(self.widget.delete_download_button.isVisible())

    def test_ui_status_downloading(self):
        self.mock_offline_manager.get_movie_status.return_value = OfflineManager.DOWNLOADING
        self.mock_offline_manager.get_movie_progress.return_value = 50
        self.widget._update_download_ui()

        self.assertEqual(self.widget.download_action_button.text(), "Pause")
        self.assertTrue(self.widget.download_progress_bar.isVisible())
        self.assertEqual(self.widget.download_progress_bar.value(), 50)
        self.assertTrue(self.widget.cancel_download_button.isVisible())
        self.assertFalse(self.widget.delete_download_button.isVisible())
        self.assertEqual(self.widget.download_status_label.text(), "50%")


    def test_ui_status_paused(self):
        self.mock_offline_manager.get_movie_status.return_value = OfflineManager.PAUSED
        self.mock_offline_manager.get_movie_progress.return_value = 60
        self.widget._update_download_ui()

        self.assertEqual(self.widget.download_action_button.text(), "Resume")
        self.assertTrue(self.widget.download_progress_bar.isVisible())
        self.assertEqual(self.widget.download_progress_bar.value(), 60)
        self.assertTrue(self.widget.cancel_download_button.isVisible())
        self.assertFalse(self.widget.delete_download_button.isVisible())
        self.assertIn("Paused", self.widget.download_status_label.text())


    def test_ui_status_completed(self):
        self.mock_offline_manager.get_movie_status.return_value = OfflineManager.COMPLETED
        self.widget._update_download_ui()

        self.assertEqual(self.widget.download_action_button.text(), "Downloaded")
        self.assertFalse(self.widget.download_action_button.isEnabled()) # Or "Play Offline" and enabled
        self.assertFalse(self.widget.download_progress_bar.isVisible())
        self.assertFalse(self.widget.cancel_download_button.isVisible())
        self.assertTrue(self.widget.delete_download_button.isVisible())
        self.assertEqual(self.widget.download_status_label.text(), "Completed")

    def test_ui_status_error(self):
        self.mock_offline_manager.get_movie_status.return_value = OfflineManager.ERROR
        self.widget._update_download_ui()

        self.assertEqual(self.widget.download_action_button.text(), "Retry")
        self.assertFalse(self.widget.download_progress_bar.isVisible())
        self.assertFalse(self.widget.cancel_download_button.isVisible()) # Or True if cancel makes sense for error
        self.assertTrue(self.widget.delete_download_button.isVisible()) # Allow deleting errored
        self.assertEqual(self.widget.download_status_label.text(), "Error")

    def test_click_download_button_when_not_downloaded(self):
        self.mock_offline_manager.get_movie_status.return_value = None # Not downloaded
        # Mock the api_client's get_movie_url to return successfully
        self.mock_api_client.get_movie_url.return_value = (True, {'url': 'http://example.com/stream.mp4'})

        self.widget._handle_download_action() # Simulate click logic

        self.mock_api_client.get_movie_url.assert_called_once_with(
            self.sample_movie_data['stream_id'],
            self.sample_movie_data['container_extension']
        )
        self.mock_offline_manager.add_movie.assert_called_once()
        # Check arguments passed to add_movie
        args, _ = self.mock_offline_manager.add_movie.call_args
        self.assertEqual(args[0], self.sample_movie_data['stream_id']) # movie_id
        self.assertEqual(args[1], 'http://example.com/stream.mp4')    # url
        self.assertEqual(args[2], self.sample_movie_data['name'])      # title


    def test_click_pause_button_when_downloading(self):
        self.mock_offline_manager.get_movie_status.return_value = OfflineManager.DOWNLOADING
        self.widget._handle_download_action() # Simulate click logic for "Pause"

        self.mock_offline_manager.pause_download.assert_called_once_with(self.sample_movie_data['stream_id'])

    def test_click_resume_button_when_paused(self):
        self.mock_offline_manager.get_movie_status.return_value = OfflineManager.PAUSED
        self.widget._handle_download_action() # Simulate click logic for "Resume"

        self.mock_offline_manager.resume_download.assert_called_once_with(self.sample_movie_data['stream_id'])

    def test_click_cancel_button(self):
        # Assuming cancel button is visible, e.g., when DOWNLOADING
        self.mock_offline_manager.get_movie_status.return_value = OfflineManager.DOWNLOADING
        self.widget._update_download_ui() # To make cancel button potentially visible

        self.widget.cancel_download_button.click() # Simulate direct click on cancel button

        self.mock_offline_manager.cancel_download.assert_called_once_with(self.sample_movie_data['stream_id'])

    def test_click_delete_button_when_completed(self):
        self.mock_offline_manager.get_movie_status.return_value = OfflineManager.COMPLETED
        self.widget._update_download_ui() # To make delete button visible

        self.widget.delete_download_button.click() # Simulate direct click

        self.mock_offline_manager.remove_movie.assert_called_once_with(self.sample_movie_data['stream_id'])


if __name__ == '__main__':
    unittest.main()
