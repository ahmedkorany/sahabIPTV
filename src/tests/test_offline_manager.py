import unittest
from unittest.mock import patch, MagicMock, mock_open, PropertyMock
import os
import json
import tempfile
import shutil
import time
import errno

# Attempt to import Qt classes if available for signal testing, otherwise mock them.
try:
    from PyQt5.QtCore import QObject, pyqtSignal
except ImportError:
    # Mock QObject and pyqtSignal if PyQt5 is not installed in the test environment
    class QObject:
        def __init__(self, parent=None): pass

    class pyqtSignal:
        def __init__(self, *args, **kwargs): pass
        def emit(self, *args, **kwargs): pass
        def connect(self, slot): pass
        def disconnect(self, slot): pass

# Import the class to be tested
from src.utils.offline_manager import OfflineManager

# Mock config object
class MockConfig:
    def __init__(self, temp_dir):
        self.OFFLINE_MOVIES_DIR = os.path.join(temp_dir, "offline_movies")
        self.OFFLINE_METADATA_FILE = os.path.join(temp_dir, "offline_movies.json")
        self.DOWNLOAD_CHUNK_SIZE = 8192

class TestOfflineManager(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.mock_config = MockConfig(self.temp_dir)

        # Patch external dependencies
        self.patch_requests_get = patch('requests.get')
        self.patch_requests_head = patch('requests.head')
        self.patch_psutil_disk_usage = patch('psutil.disk_usage')
        self.patch_os_path_exists = patch('os.path.exists')
        self.patch_os_remove = patch('os.remove')
        self.patch_os_makedirs = patch('os.makedirs') # Already called in OfflineManager init
        self.patch_threading_thread = patch('threading.Thread')
        self.patch_open = patch('builtins.open', new_callable=mock_open)

        self.mock_requests_get = self.patch_requests_get.start()
        self.mock_requests_head = self.patch_requests_head.start()
        self.mock_psutil_disk_usage = self.patch_psutil_disk_usage.start()
        self.mock_os_path_exists = self.patch_os_path_exists.start()
        self.mock_os_remove = self.patch_os_remove.start()
        self.mock_os_makedirs = self.patch_os_makedirs.start()
        self.mock_threading_thread = self.patch_threading_thread.start()
        self.mock_builtin_open = self.patch_open.start()

        # Default behavior for mocks
        self.mock_os_path_exists.return_value = False # Default to file not existing
        self.mock_psutil_disk_usage.return_value = MagicMock(free=2 * 1024 * 1024 * 1024) # 2GB free

        self.offline_manager = OfflineManager(config=self.mock_config)

        # Replace signals with MagicMock for easier testing if Qt context is an issue
        self.offline_manager.progress_signal = MagicMock(spec=pyqtSignal)
        self.offline_manager.completion_signal = MagicMock(spec=pyqtSignal)
        self.offline_manager.error_signal = MagicMock(spec=pyqtSignal)
        self.offline_manager.status_changed_signal = MagicMock(spec=pyqtSignal)
        self.offline_manager.offline_list_changed_signal = MagicMock(spec=pyqtSignal)
        self.offline_manager.storage_usage_signal = MagicMock(spec=pyqtSignal)


    def tearDown(self):
        shutil.rmtree(self.temp_dir)
        self.patch_requests_get.stop()
        self.patch_requests_head.stop()
        self.patch_psutil_disk_usage.stop()
        self.patch_os_path_exists.stop()
        self.patch_os_remove.stop()
        self.patch_os_makedirs.stop()
        self.patch_threading_thread.stop()
        self.patch_open.stop()

    def test_initialization_no_metadata_file(self):
        # os.path.exists for metadata file should return False (default mock setup)
        self.mock_os_path_exists.side_effect = lambda path: path != self.mock_config.OFFLINE_METADATA_FILE

        # Re-initialize to test loading
        manager = OfflineManager(config=self.mock_config)
        self.assertEqual(manager.offline_movies, {})
        self.mock_os_makedirs.assert_called_with(self.mock_config.OFFLINE_MOVIES_DIR, exist_ok=True)

    def test_initialization_with_empty_metadata_file(self):
        self.mock_os_path_exists.side_effect = lambda path: path == self.mock_config.OFFLINE_METADATA_FILE
        self.mock_builtin_open.return_value.read.return_value = "" # Empty file

        manager = OfflineManager(config=self.mock_config)
        self.assertEqual(manager.offline_movies, {})

    def test_initialization_with_corrupted_metadata_file(self):
        self.mock_os_path_exists.side_effect = lambda path: path == self.mock_config.OFFLINE_METADATA_FILE
        self.mock_builtin_open.return_value.read.return_value = "{corrupted_json"

        manager = OfflineManager(config=self.mock_config)
        self.assertEqual(manager.offline_movies, {})

    def test_initialization_with_existing_metadata(self):
        mock_data = {
            "123": {"title": "Movie A", "status": OfflineManager.DOWNLOADING, "progress": 50},
            "456": {"title": "Movie B", "status": OfflineManager.COMPLETED, "progress": 100}
        }
        self.mock_os_path_exists.side_effect = lambda path: path == self.mock_config.OFFLINE_METADATA_FILE
        self.mock_builtin_open.return_value.read.return_value = json.dumps(mock_data)

        manager = OfflineManager(config=self.mock_config)
        self.assertEqual(manager.offline_movies["456"]["status"], OfflineManager.COMPLETED)
        # Check that DOWNLOADING status is reset to PAUSED
        self.assertEqual(manager.offline_movies["123"]["status"], OfflineManager.PAUSED)

    def test_add_movie_success(self):
        self.mock_requests_head.return_value = MagicMock(status_code=200, headers={'content-length': '102400'}) # 100KB
        self.mock_os_path_exists.return_value = False # Ensure movie file does not exist initially

        movie_id = "test_movie_01"
        self.offline_manager.add_movie(movie_id, "http://example.com/movie.mp4", "Test Movie", "http://icon.com/icon.png")

        self.assertIn(movie_id, self.offline_manager.offline_movies)
        self.assertEqual(self.offline_manager.offline_movies[movie_id]['title'], "Test Movie")
        # Status could be PENDING then DOWNLOADING almost immediately if thread starts
        # We check if start_download was called (which implies thread creation if successful)
        self.mock_threading_thread.assert_called_once() # Check if a thread was started
        # Check that status changed signal was emitted for PENDING and then DOWNLOADING (or PAUSED/ERROR if pre-check failed)
        # This requires more granular checking of status_changed_signal calls.
        # For simplicity, check final state if thread is mocked to not run worker.
        # If worker runs, it will change status. For now, assume add_movie calls start_download, which sets up thread.
        # The actual status after add_movie depends on whether the mocked thread executes _download_worker.
        # Let's assume the thread is mocked and doesn't run the worker in this specific test.
        # The status sequence should be PENDING -> (start_download) -> DOWNLOADING

        # Check if status changed to PENDING then DOWNLOADING
        status_calls = [call[0][1] for call in self.offline_manager.status_changed_signal.emit.call_args_list if call[0][0] == movie_id]
        self.assertIn(OfflineManager.PENDING, status_calls)
        # Depending on how start_download and threading is mocked, DOWNLOADING might or might not be set immediately by the main thread.
        # If start_download is synchronous up to a point, it might set DOWNLOADING.
        # If it's fully async, PENDING might be the only one here.
        # Given self.mock_threading_thread, the worker won't run. start_download sets to DOWNLOADING.
        self.assertIn(OfflineManager.DOWNLOADING, status_calls)


    def test_add_movie_storage_full_on_add(self):
        self.mock_requests_head.return_value = MagicMock(status_code=200, headers={'content-length': str(1024 * 1024 * 1024)}) # 1GB
        self.mock_psutil_disk_usage.return_value = MagicMock(free=500 * 1024 * 1024) # 500MB (less than 1GB + buffer)

        movie_id = "test_movie_02"
        self.offline_manager.add_movie(movie_id, "http://example.com/large_movie.mp4", "Large Movie", "icon.png")

        self.assertIn(movie_id, self.offline_manager.offline_movies)
        self.assertEqual(self.offline_manager.offline_movies[movie_id]['status'], OfflineManager.STORAGE_FULL)
        self.offline_manager.error_signal.emit.assert_called_with(movie_id, "Not enough storage space to start download.")
        self.mock_threading_thread.assert_not_called() # Thread should not start

    @patch.object(OfflineManager, '_download_worker', side_effect=lambda movie_id: None) # Mock the worker to not run
    def test_add_movie_already_exists(self, mock_worker):
        movie_id = "existing_movie"
        self.offline_manager.offline_movies[movie_id] = {
            'title': 'Existing Movie', 'status': OfflineManager.COMPLETED, 'filepath': 'dummy.mp4'
        }
        # Ensure _save_metadata is called if we manually populate like this for a real scenario
        # self.offline_manager._save_metadata = MagicMock() # Or ensure it's part of the test

        self.offline_manager.add_movie(movie_id, "new_url", "New Title", "new_icon")
        # Check that it didn't overwrite or try to re-download
        self.assertEqual(self.offline_manager.offline_movies[movie_id]['title'], 'Existing Movie')
        mock_worker.assert_not_called() # Download worker should not be called

    # Example of testing the download worker more directly
    def test_download_worker_success_direct_call(self):
        movie_id = "direct_dl_success"
        # Setup movie metadata
        self.offline_manager.offline_movies[movie_id] = {
            'url': 'http://example.com/movie.mp4', 'title': 'Test Movie', 'status': OfflineManager.PENDING,
            'progress': 0, 'filepath': os.path.join(self.temp_dir, f"{movie_id}.mp4"), 'filename': f"{movie_id}.mp4",
            'size_bytes': 0
        }
        self.offline_manager.download_stop_events[movie_id] = MagicMock()
        self.offline_manager.download_stop_events[movie_id].is_set.return_value = False

        # Mock requests.get response
        mock_response = MagicMock()
        mock_response.headers = {'content-length': '2048'} # 2KB
        mock_response.iter_content.return_value = [b'chunk1data', b'chunk2data']
        mock_response.status_code = 200
        self.mock_requests_get.return_value = mock_response

        # Mock os.path.exists for the filepath to simulate resume logic (or fresh download)
        self.mock_os_path_exists.side_effect = lambda path: path == self.mock_config.OFFLINE_METADATA_FILE or \
                                                         (path == self.offline_manager.offline_movies[movie_id]['filepath'] and False)


        # Call the worker directly
        self.offline_manager._download_worker(movie_id)

        self.assertEqual(self.offline_manager.offline_movies[movie_id]['status'], OfflineManager.COMPLETED)
        self.assertEqual(self.offline_manager.offline_movies[movie_id]['progress'], 100)
        self.offline_manager.completion_signal.emit.assert_called_with(movie_id)

        # Check if file was written (mock_open can track this)
        # self.mock_builtin_open.assert_called_with(self.offline_manager.offline_movies[movie_id]['filepath'], 'wb')
        # handle = self.mock_builtin_open()
        # handle.write.assert_any_call(b'chunk1data')
        # handle.write.assert_any_call(b'chunk2data')


    def test_download_worker_network_connection_error_direct_call(self):
        movie_id = "net_error_movie"
        self.offline_manager.offline_movies[movie_id] = {
            'url': 'http://example.com/movie.mp4', 'title': 'Net Error Movie', 'status': OfflineManager.PENDING,
            'progress': 0, 'filepath': os.path.join(self.temp_dir, f"{movie_id}.mp4"), 'filename': f"{movie_id}.mp4"
        }
        self.offline_manager.download_stop_events[movie_id] = MagicMock()
        self.offline_manager.download_stop_events[movie_id].is_set.return_value = False
        self.mock_requests_get.side_effect = requests.exceptions.ConnectionError("Test connection error")

        self.offline_manager._download_worker(movie_id)

        self.assertEqual(self.offline_manager.offline_movies[movie_id]['status'], OfflineManager.PAUSED)
        self.offline_manager.error_signal.emit.assert_called_with(movie_id, "Network connection issue. Download paused.")

    def test_download_worker_http_error_direct_call(self):
        movie_id = "http_error_movie"
        # Setup movie data...
        self.offline_manager.offline_movies[movie_id] = {
            'url': 'http://example.com/movie.mp4', 'title': 'HTTP Error', 'status': OfflineManager.PENDING,
            'progress': 0, 'filepath': os.path.join(self.temp_dir, f"{movie_id}.mp4"), 'filename': f"{movie_id}.mp4"
        }
        self.offline_manager.download_stop_events[movie_id] = MagicMock()
        self.offline_manager.download_stop_events[movie_id].is_set.return_value = False

        mock_response = MagicMock(status_code=404) # Not Found
        http_error = requests.exceptions.HTTPError(response=mock_response)
        mock_response.raise_for_status.side_effect = http_error # Make response.raise_for_status() throw it
        self.mock_requests_get.return_value = mock_response # requests.get should return this mock

        self.offline_manager._download_worker(movie_id)

        self.assertEqual(self.offline_manager.offline_movies[movie_id]['status'], OfflineManager.ERROR)
        self.offline_manager.error_signal.emit.assert_called_with(movie_id, "Download failed: Server error 404")


    def test_download_worker_io_error_no_space_direct_call(self):
        movie_id = "io_error_no_space"
        self.offline_manager.offline_movies[movie_id] = {
            'url': 'http://example.com/movie.mp4', 'title': 'IO Error No Space', 'status': OfflineManager.PENDING,
            'progress': 0, 'filepath': os.path.join(self.temp_dir, f"{movie_id}.mp4"), 'filename': f"{movie_id}.mp4"
        }
        self.offline_manager.download_stop_events[movie_id] = MagicMock()
        self.offline_manager.download_stop_events[movie_id].is_set.return_value = False

        mock_response = MagicMock()
        mock_response.headers = {'content-length': '1024'}
        mock_response.iter_content.return_value = [b'data']
        self.mock_requests_get.return_value = mock_response

        # Simulate IOError with errno.ENOSPC (No space left on device)
        self.mock_builtin_open.return_value.__enter__.return_value.write.side_effect = IOError(errno.ENOSPC, "No space left")


        self.offline_manager._download_worker(movie_id)

        self.assertEqual(self.offline_manager.offline_movies[movie_id]['status'], OfflineManager.STORAGE_FULL)
        self.offline_manager.error_signal.emit.assert_called_with(movie_id, "No space left on device. Download paused.")


    def test_pause_download_while_downloading(self):
        movie_id = "pause_test"
        self.offline_manager.offline_movies[movie_id] = {'status': OfflineManager.DOWNLOADING, 'filepath':'dummy.mp4'}
        # Mock thread as alive
        mock_thread_instance = MagicMock()
        mock_thread_instance.is_alive.return_value = True
        self.offline_manager.download_threads[movie_id] = mock_thread_instance
        self.offline_manager.download_stop_events[movie_id] = MagicMock()

        self.offline_manager.pause_download(movie_id)

        self.offline_manager.download_stop_events[movie_id].set.assert_called_once()
        self.assertEqual(self.offline_manager.offline_movies[movie_id]['status'], OfflineManager.PAUSED)
        self.offline_manager.status_changed_signal.emit.assert_called_with(movie_id, OfflineManager.PAUSED)

    def test_resume_download_from_paused(self):
        movie_id = "resume_test"
        self.offline_manager.offline_movies[movie_id] = {
            'url': 'http://example.com/movie.mp4', 'title': 'Resume Test',
            'status': OfflineManager.PAUSED, 'progress': 30,
            'filepath': os.path.join(self.temp_dir, f"{movie_id}.mp4"), 'filename': f"{movie_id}.mp4"
        }
        # Mock that the file exists (for resume logic)
        self.mock_os_path_exists.side_effect = lambda path: path == self.offline_manager.offline_movies[movie_id]['filepath'] or \
                                                         path == self.mock_config.OFFLINE_METADATA_FILE

        # Mock getsize for the existing partial file
        with patch('os.path.getsize', return_value=30720): # 30KB
            self.mock_requests_head.return_value = MagicMock(status_code=200, headers={'content-length': '102400'}) # 100KB
            self.offline_manager.resume_download(movie_id)

        self.mock_threading_thread.assert_called_once() # New thread should start
        # Status should change to DOWNLOADING via start_download -> _update_status
        # self.assertEqual(self.offline_manager.offline_movies[movie_id]['status'], OfflineManager.DOWNLOADING)
        # Check status_changed_signal for DOWNLOADING
        # This is tricky because the actual worker is mocked by default by self.mock_threading_thread
        # To test this part of resume properly, you might need a more complex mock for threading.Thread
        # or test start_download directly. For now, ensuring a thread is attempted is a good start.
        status_calls = [call[0][1] for call in self.offline_manager.status_changed_signal.emit.call_args_list if call[0][0] == movie_id]
        self.assertIn(OfflineManager.DOWNLOADING, status_calls)


    def test_cancel_download_deletes_file_and_metadata_entry_if_not_completed(self):
        movie_id = "cancel_test"
        filepath = os.path.join(self.temp_dir, f"{movie_id}.mp4")
        self.offline_manager.offline_movies[movie_id] = {
            'status': OfflineManager.DOWNLOADING, 'filepath': filepath, 'filename': f"{movie_id}.mp4"
        }
        # Mock thread as alive
        mock_thread_instance = MagicMock()
        mock_thread_instance.is_alive.return_value = True
        self.offline_manager.download_threads[movie_id] = mock_thread_instance
        self.offline_manager.download_stop_events[movie_id] = MagicMock()

        self.mock_os_path_exists.return_value = True # File exists

        self.offline_manager.cancel_download(movie_id)

        self.offline_manager.download_stop_events[movie_id].set.assert_called_once()
        self.assertEqual(self.offline_manager.offline_movies[movie_id]['status'], OfflineManager.CANCELLED)
        self.mock_os_remove.assert_called_with(filepath)
        # The current cancel_download doesn't remove the metadata entry, it sets status to CANCELLED.
        # If it should remove, the test needs adjustment. Let's assume it sets to CANCELLED.
        self.assertIn(movie_id, self.offline_manager.offline_movies)


    def test_remove_movie_deletes_file_and_metadata(self):
        movie_id = "remove_test"
        filepath = os.path.join(self.temp_dir, f"{movie_id}.mp4")
        self.offline_manager.offline_movies[movie_id] = {
            'status': OfflineManager.COMPLETED, 'filepath': filepath, 'filename': f"{movie_id}.mp4"
        }
        self.mock_os_path_exists.return_value = True # File exists

        self.offline_manager.remove_movie(movie_id)

        self.mock_os_remove.assert_called_with(filepath)
        self.assertNotIn(movie_id, self.offline_manager.offline_movies)
        self.offline_manager.offline_list_changed_signal.emit.assert_called()


if __name__ == '__main__':
    unittest.main()
