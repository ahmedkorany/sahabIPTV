import unittest
from unittest.mock import MagicMock, patch

from PyQt5.QtWidgets import QApplication, QListWidgetItem

# Import the classes to be tested
from src.ui.tabs.offline_tab import OfflineTab, OfflineItemWidget
from src.utils.offline_manager import OfflineManager # For status constants

# Minimal application setup
app = None
def qapplication_instance():
    global app
    if app is None:
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
    return app

class TestOfflineTab(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = qapplication_instance()

    def setUp(self):
        self.mock_offline_manager = MagicMock(spec=OfflineManager)
        self.mock_main_window = MagicMock()
        self.mock_main_window.language = 'en' # For translations

        self.tab = OfflineTab(
            offline_manager=self.mock_offline_manager,
            main_window=self.mock_main_window
        )

    def test_initialization(self):
        self.assertIsNotNone(self.tab.offline_list_widget)
        self.assertIsNotNone(self.tab.total_storage_label)
        # Check if signals are connected
        self.mock_offline_manager.offline_list_changed_signal.connect.assert_called()
        self.mock_offline_manager.progress_signal.connect.assert_called()
        self.mock_offline_manager.status_changed_signal.connect.assert_called()
        self.mock_offline_manager.storage_usage_signal.connect.assert_called()
        # Check initial population calls
        self.mock_offline_manager.get_all_movies_details.assert_called_once()


    def test_populate_offline_list_empty(self):
        self.mock_offline_manager.get_all_movies_details.return_value = {}
        self.tab._populate_offline_list()
        # Should show a placeholder item or be empty
        # The current implementation adds a placeholder item with a QLabel
        self.assertEqual(self.tab.offline_list_widget.count(), 1)
        item = self.tab.offline_list_widget.item(0)
        widget = self.tab.offline_list_widget.itemWidget(item)
        self.assertIsNotNone(widget)
        self.assertIn("No offline items", widget.text())


    @patch('src.ui.tabs.offline_tab.OfflineItemWidget') # Patch OfflineItemWidget
    def test_populate_offline_list_with_items(self, MockOfflineItemWidget):
        mock_movie1_meta = {'stream_id': '1', 'title': 'Movie 1', 'status': OfflineManager.COMPLETED}
        mock_movie2_meta = {'stream_id': '2', 'title': 'Movie 2', 'status': OfflineManager.DOWNLOADING, 'progress': 50}
        self.mock_offline_manager.get_all_movies_details.return_value = {
            '1': mock_movie1_meta,
            '2': mock_movie2_meta
        }

        # Mock the instance returned by OfflineItemWidget constructor
        mock_item_widget_instance = MagicMock()
        MockOfflineItemWidget.return_value = mock_item_widget_instance

        self.tab._populate_offline_list()

        self.assertEqual(self.tab.offline_list_widget.count(), 2)
        # Check that OfflineItemWidget was instantiated correctly for each movie
        MockOfflineItemWidget.assert_any_call(mock_movie1_meta, self.mock_offline_manager, self.mock_main_window)
        MockOfflineItemWidget.assert_any_call(mock_movie2_meta, self.mock_offline_manager, self.mock_main_window)

        # Check that item_widgets_map is populated
        self.assertIn('1', self.tab.item_widgets_map)
        self.assertIn('2', self.tab.item_widgets_map)
        self.assertEqual(self.tab.item_widgets_map['1'], mock_item_widget_instance)

        # Check if setItemWidget was called (indirectly tests QListWidgetItem creation)
        # This requires ensuring that QListWidget.setItemWidget is called.
        # The actual item set is a QListWidgetItem, and widget is our custom one.
        # For more detailed check, we might need to inspect itemWidget(item) for each item.
        self.assertTrue(self.tab.offline_list_widget.itemWidget(self.tab.offline_list_widget.item(0)) is mock_item_widget_instance)


    def test_update_item_progress(self):
        movie_id = 'movie123'
        mock_item_widget = MagicMock(spec=OfflineItemWidget)
        self.tab.item_widgets_map[movie_id] = mock_item_widget

        self.tab._update_item_progress(movie_id, 75)
        mock_item_widget.update_ui_for_status.assert_called_once_with(progress=75)

    def test_update_item_status(self):
        movie_id = 'movie456'
        mock_item_widget = MagicMock(spec=OfflineItemWidget)
        self.tab.item_widgets_map[movie_id] = mock_item_widget

        self.tab._update_item_status(movie_id, OfflineManager.ERROR)
        mock_item_widget.update_ui_for_status.assert_called_once_with(status=OfflineManager.ERROR)

    def test_update_total_storage_display(self):
        self.tab._update_total_storage_display(used_gb=1.5, total_gb=100.0)
        self.assertIn("1.50 GB", self.tab.total_storage_label.text())
        self.assertIn("100.00 GB", self.tab.total_storage_label.text())

        self.tab._update_total_storage_display(used_gb=0.05, total_gb=100.0) # 50 MB
        self.assertIn("51.20 MB", self.tab.total_storage_label.text()) # 0.05 * 1024

    def test_offline_list_changed_signal_refreshes_list(self):
        # We can mock _populate_offline_list to check if it's called
        with patch.object(self.tab, '_populate_offline_list') as mock_populate:
            # Simulate the signal emission
            # This requires the signal to be a MagicMock or similar that we can "emit"
            # Or, if we are testing the connection setup in __init__,
            # we can directly call the slot that is connected.
            # For this test, let's assume the signal is connected and we trigger the slot.

            # To directly test the slot:
            self.tab._populate_offline_list() # Initial call
            mock_populate.reset_mock() # Reset after initial call

            # Simulate a scenario where the slot for offline_list_changed_signal is called
            # This is usually done by the actual signal emit if not mocking the signal itself.
            # If self.offline_manager.offline_list_changed_signal is a MagicMock:
            self.mock_offline_manager.offline_list_changed_signal.connect.call_args[0][0]() # Call the connected slot

            mock_populate.assert_called_once()


# --- Basic tests for OfflineItemWidget (can be expanded) ---
class TestOfflineItemWidget(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = qapplication_instance()

    def setUp(self):
        self.mock_offline_manager = MagicMock(spec=OfflineManager)
        self.mock_main_window = MagicMock()
        self.mock_main_window.language = 'en'

        self.movie_meta_completed = {
            'stream_id': '1', 'title': 'Completed Movie', 'name': 'Completed Movie',
            'status': OfflineManager.COMPLETED, 'icon_url': 'some_icon.png'
        }
        self.movie_meta_downloading = {
            'stream_id': '2', 'title': 'Downloading Movie', 'name': 'Downloading Movie',
            'status': OfflineManager.DOWNLOADING, 'progress': 40, 'icon_url': 'another_icon.png'
        }

        # Patch load_image_async as it's external and might involve network/file I/O
        self.patch_load_image = patch('src.ui.tabs.offline_tab.load_image_async')
        self.mock_load_image = self.patch_load_image.start()


    def tearDown(self):
        self.patch_load_image.stop()


    def test_ui_for_completed_status(self):
        widget = OfflineItemWidget(self.movie_meta_completed, self.mock_offline_manager, self.mock_main_window)
        widget.update_ui_for_status() # Call with no args to use internal status

        self.assertTrue(widget.play_button.isVisible())
        self.assertTrue(widget.remove_button.isVisible())
        self.assertFalse(widget.pause_resume_button.isVisible())
        self.assertFalse(widget.cancel_button.isVisible())
        self.assertFalse(widget.progress_bar.isVisible())
        self.assertEqual(widget.status_label.text().lower(), "completed")

    def test_ui_for_downloading_status(self):
        # Mock manager calls for status/progress as update_ui_for_status will query them
        self.mock_offline_manager.get_movie_status.return_value = OfflineManager.DOWNLOADING
        self.mock_offline_manager.get_movie_progress.return_value = 40

        widget = OfflineItemWidget(self.movie_meta_downloading, self.mock_offline_manager, self.mock_main_window)
        # update_ui_for_status is called in __init__, then we can call again if needed
        # widget.update_ui_for_status(status=OfflineManager.DOWNLOADING, progress=40)

        self.assertFalse(widget.play_button.isVisible())
        self.assertTrue(widget.pause_resume_button.isVisible())
        self.assertEqual(widget.pause_resume_button.text(), "Pause")
        self.assertTrue(widget.cancel_button.isVisible())
        self.assertFalse(widget.remove_button.isVisible())
        self.assertTrue(widget.progress_bar.isVisible())
        self.assertEqual(widget.progress_bar.value(), 40)
        self.assertIn("Downloading", widget.status_label.text()) # e.g. "Downloading... 40%"

    def test_play_button_emits_signal(self):
        # Need to mock get_movie_filepath and os.path.exists for _handle_play
        self.mock_offline_manager.get_movie_filepath.return_value = "/fake/path/movie.mp4"
        with patch('os.path.exists', return_value=True):
            widget = OfflineItemWidget(self.movie_meta_completed, self.mock_offline_manager, self.mock_main_window)

            mock_slot = MagicMock()
            widget.play_requested.connect(mock_slot)

            widget.play_button.click()
            mock_slot.assert_called_once_with("/fake/path/movie.mp4", self.movie_meta_completed)

    def test_pause_resume_button_calls_manager_pause(self):
        self.mock_offline_manager.get_movie_status.return_value = OfflineManager.DOWNLOADING
        widget = OfflineItemWidget(self.movie_meta_downloading, self.mock_offline_manager, self.mock_main_window)
        widget.pause_resume_button.click()
        self.mock_offline_manager.pause_download.assert_called_once_with(self.movie_meta_downloading['stream_id'])

    def test_pause_resume_button_calls_manager_resume(self):
        meta_paused = {**self.movie_meta_downloading, 'status': OfflineManager.PAUSED}
        self.mock_offline_manager.get_movie_status.return_value = OfflineManager.PAUSED
        widget = OfflineItemWidget(meta_paused, self.mock_offline_manager, self.mock_main_window)
        widget.pause_resume_button.click()
        self.mock_offline_manager.resume_download.assert_called_once_with(meta_paused['stream_id'])

    def test_cancel_button_calls_manager(self):
        self.mock_offline_manager.get_movie_status.return_value = OfflineManager.DOWNLOADING
        widget = OfflineItemWidget(self.movie_meta_downloading, self.mock_offline_manager, self.mock_main_window)
        widget.cancel_button.click()
        self.mock_offline_manager.cancel_download.assert_called_once_with(self.movie_meta_downloading['stream_id'])

    @patch('src.ui.tabs.offline_tab.QMessageBox.question')
    def test_remove_button_calls_manager_on_confirm(self, mock_msgbox):
        mock_msgbox.return_value = QMessageBox.Yes
        widget = OfflineItemWidget(self.movie_meta_completed, self.mock_offline_manager, self.mock_main_window)
        widget.remove_button.click()
        self.mock_offline_manager.remove_movie.assert_called_once_with(self.movie_meta_completed['stream_id'])

    @patch('src.ui.tabs.offline_tab.QMessageBox.question')
    def test_remove_button_does_not_call_manager_on_cancel(self, mock_msgbox):
        mock_msgbox.return_value = QMessageBox.No
        widget = OfflineItemWidget(self.movie_meta_completed, self.mock_offline_manager, self.mock_main_window)
        widget.remove_button.click()
        self.mock_offline_manager.remove_movie.assert_not_called()


if __name__ == '__main__':
    unittest.main()
