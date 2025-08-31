import os
import json
import time
import threading
import requests
import psutil
from PyQt5.QtCore import QObject, pyqtSignal

class OfflineManager(QObject):
    progress_signal = pyqtSignal(str, int)  # movie_id, progress
    completion_signal = pyqtSignal(str)  # movie_id
    error_signal = pyqtSignal(str, str)  # movie_id, error_message
    status_changed_signal = pyqtSignal(str, str)  # movie_id, status
    offline_list_changed_signal = pyqtSignal()
    # Changed to emit total bytes used by app's offline files
    storage_usage_signal = pyqtSignal(int)  # total_app_usage_bytes

    PENDING = "pending"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"
    STORAGE_FULL = "storage_full"

    STORAGE_BUFFER_BYTES = 10 * 1024 * 1024  # 10MB buffer for storage checks

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.offline_movies_dir = self.config.OFFLINE_MOVIES_DIR
        self.metadata_file = self.config.OFFLINE_METADATA_FILE
        self.download_chunk_size = self.config.DOWNLOAD_CHUNK_SIZE
        self.offline_movies = {}  # movie_id: {metadata}
        self.download_threads = {}  # movie_id: thread
        self.download_stop_events = {} # movie_id: threading.Event() to signal stop

        os.makedirs(self.offline_movies_dir, exist_ok=True)
        self._load_metadata()
        self.update_total_storage_usage() # Corrected call

    def _load_metadata(self):
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, 'r') as f:
                    self.offline_movies = json.load(f)
                # Reset status of incomplete downloads to PENDING or PAUSED
                for movie_id, data in self.offline_movies.items():
                    if data['status'] == self.DOWNLOADING:
                        self._update_status(movie_id, self.PAUSED, emit_signal=False) # Or PENDING if you prefer to restart
            except json.JSONDecodeError:
                self.offline_movies = {}
        else:
            self.offline_movies = {}
        self.offline_list_changed_signal.emit()

    def _save_metadata(self):
        with open(self.metadata_file, 'w') as f:
            json.dump(self.offline_movies, f, indent=4)
        self.offline_list_changed_signal.emit()
        self.update_total_storage_usage() # Update usage after metadata changes

    def _update_status(self, movie_id, status, emit_signal=True):
        if movie_id in self.offline_movies:
            self.offline_movies[movie_id]['status'] = status
            if emit_signal:
                self.status_changed_signal.emit(movie_id, status)
            # _save_metadata will call update_total_storage_usage, so no need to call it directly here
            # if status change implies a potential change in storage (e.g. COMPLETED, CANCELLED involving file ops)
            self._save_metadata()

    # Removed faulty _emit_storage_usage method.
    # System-wide disk usage (free/total) is checked directly where needed (start_download, _download_worker).
    # storage_usage_signal now reports app-specific usage.

    def update_total_storage_usage(self):
        """Calculates and emits the total storage used by offline downloads."""
        usage_bytes = self.get_total_offline_storage_usage()
        self.storage_usage_signal.emit(usage_bytes)

    def get_movie_filepath(self, movie_id):
        if movie_id in self.offline_movies:
            # Use the filename stored in metadata if available
            filename = self.offline_movies[movie_id].get('filename')
            if filename:
                return os.path.join(self.offline_movies_dir, filename)
        # Fallback or if filename is not stored (older versions)
        return os.path.join(self.offline_movies_dir, f"{movie_id}.mp4")


    def add_movie(self, movie_id, url, title, icon_url, metadata=None):
        if movie_id in self.offline_movies and self.offline_movies[movie_id]['status'] not in [self.ERROR, self.CANCELLED, self.STORAGE_FULL]:
            print(f"Movie {movie_id} already in download list or downloaded.")
            return

        # Extract filename from URL or generate one
        try:
            original_filename = os.path.basename(url.split('?')[0]) # Basic extraction
            _, ext = os.path.splitext(original_filename)
            if not ext: # if no extension, default to .mp4
                ext = ".mp4"
            safe_filename = f"{movie_id}{ext}"
        except Exception:
            safe_filename = f"{movie_id}.mp4"


        self.offline_movies[movie_id] = {
            'url': url,
            'title': title,
            'icon_url': icon_url,
            'status': self.PENDING,
            'progress': 0,
            'filepath': os.path.join(self.offline_movies_dir, safe_filename), # Store full path
            'filename': safe_filename, # Store just the filename
            'added_date': time.time(),
            'size_bytes': 0, # Will be updated once download starts
            **(metadata or {})
        }
        self._update_status(movie_id, self.PENDING)
        self.start_download(movie_id)

    def start_download(self, movie_id):
        if movie_id not in self.offline_movies:
            self.error_signal.emit(movie_id, "Movie not found in download list.")
            return

        if self.offline_movies[movie_id]['status'] == self.DOWNLOADING:
            print(f"Download for {movie_id} is already in progress.")
            return

        if self.offline_movies[movie_id]['status'] == self.COMPLETED:
            print(f"Movie {movie_id} is already downloaded.")
            return

        # Check storage before starting
        try:
            # Try to get total size from headers first
            # Increased timeout for HEAD request
            response = requests.head(self.offline_movies[movie_id]['url'], timeout=20, allow_redirects=True)
            response.raise_for_status() # Check for HTTP errors on HEAD request
            total_size = int(response.headers.get('content-length', 0))

            if total_size > 0: # Only store if valid
                self.offline_movies[movie_id]['size_bytes'] = total_size

            free_space = psutil.disk_usage(self.offline_movies_dir).free

            # Use the class-level STORAGE_BUFFER_BYTES for consistency
            disk_info = psutil.disk_usage(self.offline_movies_dir) # Get named tuple
            free_space = disk_info.free
            if total_size > 0 and free_space < (total_size + self.STORAGE_BUFFER_BYTES):
                print(f"Storage check failed for {movie_id}: Required {total_size + self.STORAGE_BUFFER_BYTES}, Available {free_space}")
                self._update_status(movie_id, self.STORAGE_FULL)
                self.error_signal.emit(movie_id, "Not enough storage space to start download.")
                # self.update_total_storage_usage() # _update_status calls _save_metadata which calls this
                return
            elif total_size == 0: # Content-Length was 0 or not provided
                 print(f"Warning: Content-Length is 0 or not provided for {movie_id}. Proceeding without pre-download storage check for file size.")
                 # We might still hit storage full during download if the file is actually large.

        except (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
            print(f"Network connection issue during pre-download for {movie_id}: {e}")
            self._update_status(movie_id, self.PAUSED) # Pause, user can retry
            self.error_signal.emit(movie_id, "Network connection issue. Download paused.")
            return
        except requests.exceptions.HTTPError as e:
            print(f"HTTP error during pre-download for {movie_id}: {e}")
            self._update_status(movie_id, self.ERROR)
            self.error_signal.emit(movie_id, f"Download failed: Server error {e.response.status_code}")
            return
        except requests.exceptions.RequestException as e:
            print(f"Could not fetch content length for {movie_id} due to a network request error: {e}")
            self._update_status(movie_id, self.ERROR) # Error, as we couldn't get essential info
            self.error_signal.emit(movie_id, "Download failed: Network request error before starting.")
            return

        self._update_status(movie_id, self.DOWNLOADING)
        self.download_stop_events[movie_id] = threading.Event()
        thread = threading.Thread(target=self._download_worker, args=(movie_id,))
        self.download_threads[movie_id] = thread
        thread.daemon = True
        thread.start()

    def pause_download(self, movie_id):
        if movie_id in self.download_threads and self.download_threads[movie_id].is_alive():
            if movie_id in self.download_stop_events:
                self.download_stop_events[movie_id].set() # Signal the thread to stop
            self._update_status(movie_id, self.PAUSED)
        elif movie_id in self.offline_movies and self.offline_movies[movie_id]['status'] == self.PENDING:
             self._update_status(movie_id, self.PAUSED)

    def resume_download(self, movie_id):
        if movie_id not in self.offline_movies:
            self.error_signal.emit(movie_id, "Movie not in list.")
            return

        if self.offline_movies[movie_id]['status'] == self.PAUSED:
            # Reset stop event for the new thread
            if movie_id in self.download_stop_events:
                self.download_stop_events[movie_id].clear()
            self.start_download(movie_id) # This will handle status updates and thread creation
        elif self.offline_movies[movie_id]['status'] == self.ERROR:
             # Allow retrying from error state
            if movie_id in self.download_stop_events:
                self.download_stop_events[movie_id].clear()
            self.start_download(movie_id)


    def cancel_download(self, movie_id):
        if movie_id in self.download_threads and self.download_threads[movie_id].is_alive():
            if movie_id in self.download_stop_events:
                self.download_stop_events[movie_id].set()
                # Wait for the thread to finish to ensure cleanup
                # self.download_threads[movie_id].join(timeout=5) # Optional: add timeout

        self._update_status(movie_id, self.CANCELLED)
        filepath = self.get_movie_filepath(movie_id) # Use the stored filepath

        # Attempt to clean up the partial file
        # Ensure we have the correct filepath from metadata
        if movie_id in self.offline_movies and 'filepath' in self.offline_movies[movie_id]:
            filepath_to_delete = self.offline_movies[movie_id]['filepath']
            if os.path.exists(filepath_to_delete):
                try:
                    os.remove(filepath_to_delete)
                    print(f"Partially downloaded file {filepath_to_delete} removed.")
                except OSError as e:
                    print(f"Error removing file {filepath_to_delete}: {e}")
                    self.error_signal.emit(movie_id, f"Error removing file: {e}")

        # Reset progress and potentially other fields
        if movie_id in self.offline_movies:
            self.offline_movies[movie_id]['progress'] = 0
            # self.offline_movies[movie_id]['size_bytes'] = 0 # Or keep it if you want to show potential size
        self._save_metadata()


    def remove_movie(self, movie_id):
        self.cancel_download(movie_id) # Ensure download is stopped and file is initially handled

        if movie_id in self.offline_movies:
            filepath_to_delete = self.offline_movies[movie_id].get('filepath')
            if filepath_to_delete and os.path.exists(filepath_to_delete):
                try:
                    os.remove(filepath_to_delete)
                    print(f"Completed file {filepath_to_delete} removed.")
                except OSError as e:
                    print(f"Error removing file {filepath_to_delete}: {e}")
                    self.error_signal.emit(movie_id, f"Error removing file: {e}")

            del self.offline_movies[movie_id]
            self._save_metadata()
            if movie_id in self.download_threads:
                del self.download_threads[movie_id]
            if movie_id in self.download_stop_events:
                del self.download_stop_events[movie_id]
        else:
            self.error_signal.emit(movie_id, "Movie not found in offline list.")


    def _download_worker(self, movie_id):
        movie_data = self.offline_movies[movie_id]
        url = movie_data['url']
        filepath = movie_data['filepath'] # Use the stored filepath

        try:
            headers = {}
            current_size = 0
            if os.path.exists(filepath):
                current_size = os.path.getsize(filepath)
                headers['Range'] = f'bytes={current_size}-'

            # Update status to DOWNLOADING if it was PENDING or PAUSED
            self._update_status(movie_id, self.DOWNLOADING)

            response = requests.get(url, headers=headers, stream=True, timeout=30) # Increased timeout
            response.raise_for_status() # Will raise HTTPError for bad responses (4XX or 5XX)

            # Get total size for progress calculation
            total_size_str = response.headers.get('content-length')
            if current_size > 0 and response.status_code == 206: # Partial content
                # Content-Range header should be present for 206, e.g., "bytes 1000-5000/10000"
                content_range = response.headers.get('content-range')
                if content_range and '/' in content_range:
                    total_size = int(content_range.split('/')[-1])
                else: # Fallback if Content-Range is missing or malformed
                    total_size = current_size + int(total_size_str) if total_size_str else 0
            elif total_size_str:
                total_size = int(total_size_str)
                if current_size > 0 and current_size < total_size : # Resuming but server didn't send 206
                    print(f"Resuming download for {movie_id} from {current_size} but server sent {response.status_code}")
                    # Server might not support range requests correctly or file changed
                    # Decide if you want to restart or error out
                    # For now, we continue, but this might lead to corrupted files if not handled well
                elif current_size == 0 : # Fresh download
                     pass # total_size is correctly set
                else: # current_size >= total_size
                    if current_size == total_size and total_size > 0 : # Already downloaded
                         self._update_status(movie_id, self.COMPLETED)
                         self.completion_signal.emit(movie_id)
                         self.offline_movies[movie_id]['progress'] = 100
                         self.offline_movies[movie_id]['size_bytes'] = total_size
                         self._save_metadata()
                         return # Already complete
                    else: # File on disk is larger or mismatch, restart download
                        print(f"File size mismatch for {movie_id}. Restarting download.")
                        current_size = 0
                        os.remove(filepath) # Remove corrupted/mismatched file
                        # Make a new request without Range header
                        response = requests.get(url, stream=True, timeout=30)
                        response.raise_for_status()
                        total_size = int(response.headers.get('content-length', 0))


            else: # No content-length header
                total_size = 0 # Cannot calculate progress accurately

            if total_size > 0 :
                 self.offline_movies[movie_id]['size_bytes'] = total_size # Store actual total size


            mode = 'ab' if current_size > 0 else 'wb'
            downloaded_this_session = 0

            with open(filepath, mode) as f:
                for chunk in response.iter_content(chunk_size=self.download_chunk_size):
                    if self.download_stop_events[movie_id].is_set():
                        # Status will be PAUSED or CANCELLED by the calling method
                        print(f"Download stopped for {movie_id}")
                        # self._save_metadata() # Save current progress before exiting
                        return

                    if chunk:
                        f.write(chunk)
                        downloaded_this_session += len(chunk)
                        current_file_size = current_size + downloaded_this_session

                        # Update current actual size in metadata for get_total_offline_storage_usage
                        self.offline_movies[movie_id]['current_actual_size_bytes'] = current_file_size


                        # Refined In-Download Storage Check
                        disk_info_loop = psutil.disk_usage(os.path.dirname(filepath))
                        free_space_in_loop = disk_info_loop.free
                        required_for_chunk = len(chunk)
                        if free_space_in_loop < required_for_chunk + self.STORAGE_BUFFER_BYTES:
                            print(f"Stopping download for {movie_id} due to insufficient storage during download.")
                            self._update_status(movie_id, self.STORAGE_FULL)
                            self.error_signal.emit(movie_id, "Not enough storage space. Download paused.")
                            self.download_stop_events[movie_id].set() # Signal thread to stop
                            return # Exit worker

                        if total_size > 0:
                            progress = int((current_file_size / total_size) * 100)
                            self.offline_movies[movie_id]['progress'] = progress
                            self.progress_signal.emit(movie_id, progress)
                        else:
                            # If no total_size, emit bytes downloaded or a fixed progress
                            self.progress_signal.emit(movie_id, -1) # Indicate unknown progress

            # After loop, check if download was stopped or completed
            if self.download_stop_events[movie_id].is_set():
                 # This means it was paused or cancelled, status already set
                pass
            elif total_size == 0 or (current_size + downloaded_this_session) >= total_size : # If total_size was unknown, assume completion
                final_size = os.path.getsize(filepath)
                if total_size > 0 and final_size < total_size:
                    # This case might happen if stream ended prematurely
                    self._update_status(movie_id, self.ERROR, "Download incomplete, stream ended early.")
                    self.error_signal.emit(movie_id, "Download incomplete, stream ended prematurely.")
                else:
                    self._update_status(movie_id, self.COMPLETED)
                    self.completion_signal.emit(movie_id)
                    self.offline_movies[movie_id]['progress'] = 100
                    if total_size == 0: # If total size was unknown, set it now
                        self.offline_movies[movie_id]['size_bytes'] = final_size
            else: # Not stopped, and not completed by size check (e.g. total_size known and current_file_size < total_size)
                 self._update_status(movie_id, self.ERROR) # Assume error if loop finishes but conditions not met
                 self.error_signal.emit(movie_id, "Download incomplete. Please retry.")

        except (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
            print(f"Network connection issue for {movie_id}: {e}")
            self._update_status(movie_id, self.PAUSED) # Set to PAUSED for network issues
            self.error_signal.emit(movie_id, "Network connection issue. Download paused.")
        except requests.exceptions.HTTPError as e:
            print(f"HTTP error for {movie_id}: {e}")
            self._update_status(movie_id, self.ERROR)
            self.error_signal.emit(movie_id, f"Download failed: Server error {e.response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Generic network request error for {movie_id}: {e}")
            self._update_status(movie_id, self.ERROR)
            self.error_signal.emit(movie_id, "Download failed: Network request error.")
        except IOError as e:
            # Check for "No space left on device"
            if e.errno == 28: # errno.ENOSPC
                print(f"IOError (No space left) for {movie_id}: {e}")
                self._update_status(movie_id, self.STORAGE_FULL)
                self.error_signal.emit(movie_id, "No space left on device. Download paused.")
            else:
                print(f"File system error for {movie_id}: {e}")
                self._update_status(movie_id, self.ERROR)
                self.error_signal.emit(movie_id, "File system error during download.")
        except Exception as e: # Catch-all for any other unexpected errors
            print(f"An unexpected error occurred for {movie_id}: {e}")
            self._update_status(movie_id, self.ERROR)
            self.error_signal.emit(movie_id, f"An unexpected error occurred: {str(e)[:100]}.") # Keep message brief
        finally:
            # Ensure thread entry is cleaned up if thread is exiting.
            # This part might be complex if multiple threads can manage the same movie_id over time.
            # For simplicity, let's assume one worker thread per movie_id at a time.
            if movie_id in self.download_threads:
                # Check if thread is still the one we manage, relevant for quick start/stop/resume
                if threading.current_thread() == self.download_threads.get(movie_id):
                    pass #
            # _save_metadata calls update_total_storage_usage
            self._save_metadata() # Ensure metadata is saved at the end of a download attempt


    def get_offline_movies_list(self):
        return list(self.offline_movies.values())

    def get_movie_status(self, movie_id):
        return self.offline_movies.get(movie_id, {}).get('status')

    def get_movie_progress(self, movie_id):
        return self.offline_movies.get(movie_id, {}).get('progress', 0)

    def get_total_offline_storage_usage(self):
        """Calculates total storage used by successfully downloaded or partially downloaded files."""
        total_usage_bytes = 0
        for movie_id, meta in self.offline_movies.items():
            filepath = meta.get('filepath')
            if filepath and os.path.exists(filepath):
                if meta['status'] == self.COMPLETED:
                    total_usage_bytes += os.path.getsize(filepath)
                elif meta['status'] in [self.DOWNLOADING, self.PAUSED, self.ERROR, self.STORAGE_FULL]:
                    # For incomplete downloads, use actual current file size
                    total_usage_bytes += os.path.getsize(filepath)
            # If file doesn't exist but metadata is there (e.g. pending, or error before file creation),
            # it contributes 0 to current usage.
        return total_usage_bytes

    def retry_download(self, movie_id):
        if movie_id in self.offline_movies:
            status = self.offline_movies[movie_id]['status']
            if status == self.ERROR or status == self.STORAGE_FULL or status == self.CANCELLED:
                # Reset progress for a clean retry, or rely on resume logic in start_download
                # self.offline_movies[movie_id]['progress'] = 0
                if movie_id in self.download_stop_events:
                    self.download_stop_events[movie_id].clear()
                self.start_download(movie_id)
            else:
                print(f"Cannot retry download for {movie_id}, status is {status}")
        else:
            self.error_signal.emit(movie_id, "Movie not found, cannot retry.")

    def get_all_movies_details(self):
        """Returns a deep copy of all movie details."""
        return json.loads(json.dumps(self.offline_movies)) # Simple way to deepcopy

    def get_movie_meta(self, movie_id):
        """Returns the metadata for a given movie_id."""
        return self.offline_movies.get(str(movie_id))

    def is_movie_downloaded(self, movie_id):
        """Checks if a movie is fully downloaded."""
        movie_data = self.offline_movies.get(movie_id)
        if movie_data and movie_data['status'] == self.COMPLETED:
            # Additionally, verify the file exists
            filepath = movie_data.get('filepath')
            if filepath and os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                # Optionally, compare file size with metadata size if available and reliable
                # if movie_data.get('size_bytes', 0) > 0 and os.path.getsize(filepath) == movie_data['size_bytes']:
                # return True
                return True
        return False

    def cleanup_threads(self):
        """
        Cleans up any completed or dead threads.
        Should be called periodically or on application shutdown.
        """
        threads_to_remove = []
        for movie_id, thread in self.download_threads.items():
            if not thread.is_alive():
                threads_to_remove.append(movie_id)

        for movie_id in threads_to_remove:
            # print(f"Cleaning up thread for movie ID: {movie_id}")
            del self.download_threads[movie_id]
            # stop_event is usually removed when download ends or is cancelled/removed
            # if movie_id in self.download_stop_events:
            # del self.download_stop_events[movie_id]

    def stop_all_downloads(self, cancel=False):
        """
        Stops all ongoing downloads. If 'cancel' is True, also sets their status to CANCELLED.
        """
        for movie_id in list(self.download_threads.keys()): # Iterate over a copy of keys
            if self.download_threads[movie_id].is_alive():
                if movie_id in self.download_stop_events:
                    self.download_stop_events[movie_id].set()

                status_after_stop = self.CANCELLED if cancel else self.PAUSED
                self._update_status(movie_id, status_after_stop, emit_signal=True)

                if cancel: # If cancelling, also trigger the file removal logic if any
                    filepath_to_delete = self.offline_movies[movie_id].get('filepath')
                    if filepath_to_delete and os.path.exists(filepath_to_delete) and status_after_stop == self.CANCELLED:
                         # Only remove if it was truly cancelled, not just paused due to app closing
                        try:
                            os.remove(filepath_to_delete)
                            print(f"Partially downloaded file {filepath_to_delete} removed during stop_all (cancel=True).")
                        except OSError as e:
                            print(f"Error removing file {filepath_to_delete} during stop_all: {e}")


        # Wait for threads to finish (optional, with timeout)
        for thread in self.download_threads.values():
            thread.join(timeout=1.0) # Give threads a moment to stop
        self.cleanup_threads()
        self._save_metadata() # Ensure all status changes are saved
