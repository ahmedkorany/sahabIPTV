from PyQt5.QtCore import QObject, pyqtSignal, QThread, QTimer
import os
import requests
import json
from pathlib import Path
from urllib.parse import urlparse

class DownloadWorker(QThread):
    progress_updated = pyqtSignal(str, int)
    download_finished = pyqtSignal(str, str)
    error_occurred = pyqtSignal(str, str)

    def __init__(self, url, dest_path):
        super().__init__()
        self.url = url
        self.dest_path = dest_path
        self._is_paused = False
        self._is_canceled = False

    def run(self):
        try:
            with requests.get(self.url, stream=True, timeout=10) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                downloaded = 0
                
                with open(self.dest_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if self._is_canceled:
                            os.remove(self.dest_path)
                            return
                        if not self._is_paused:
                            f.write(chunk)
                            downloaded += len(chunk)
                            progress = int((downloaded / total_size) * 100) if total_size > 0 else 0
                            self.progress_updated.emit(self.url, progress)
                
                if not self._is_canceled:
                    self.download_finished.emit(self.url, self.dest_path)
        except Exception as e:
            self.error_occurred.emit(self.url, str(e))

    def pause(self):
        self._is_paused = True

    def resume(self):
        self._is_paused = False

    def cancel(self):
        self._is_canceled = True


class DownloadService(QObject):
    _instance = None
    download_progress = pyqtSignal(str, int)
    download_complete = pyqtSignal(str, str)
    download_error = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.active_downloads = {}
        self.download_queue = []
        self.storage_path = os.path.join(str(Path.home()), 'sahab_downloads')
        os.makedirs(self.storage_path, exist_ok=True)
        self._load_state()

        # Auto-save every 30 seconds
        self.autosave_timer = QTimer()
        self.autosave_timer.timeout.connect(self._save_state)
        self.autosave_timer.start(30000)

    def _load_state(self):
        state_file = os.path.join(self.storage_path, '.download_state.json')
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    self.download_queue = state.get('queue', [])
            except json.JSONDecodeError:
                pass

    def _save_state(self):
        state_file = os.path.join(self.storage_path, '.download_state.json')
        state = {
            'queue': self.download_queue
        }
        with open(state_file, 'w') as f:
            json.dump(state, f)

    def queue_download(self, url):
        if url in self.active_downloads or url in self.download_queue:
            return

        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)
        dest_path = os.path.join(self.storage_path, filename)

        if os.path.exists(dest_path):
            dest_path = self._get_unique_filename(dest_path)

        self.download_queue.append({'url': url, 'path': dest_path})
        self._process_queue()

    def _get_unique_filename(self, path):
        base, ext = os.path.splitext(path)
        counter = 1
        while os.path.exists(path):
            path = f"{base} ({counter}){ext}"
            counter += 1
        return path

    def _process_queue(self):
        if not self.download_queue:
            return

        next_download = self.download_queue.pop(0)
        worker = DownloadWorker(next_download['url'], next_download['path'])
        worker.progress_updated.connect(self._handle_progress)
        worker.download_finished.connect(self._handle_completion)
        worker.error_occurred.connect(self._handle_error)
        self.active_downloads[next_download['url']] = worker
        worker.start()

    def _handle_progress(self, url, progress):
        self.download_progress.emit(url, progress)

    def _handle_completion(self, url, path):
        del self.active_downloads[url]
        self.download_complete.emit(url, path)
        self._process_queue()

    def _handle_error(self, url, error):
        del self.active_downloads[url]
        self.download_error.emit(url, error)
        self._process_queue()

    def pause_download(self, url):
        if url in self.active_downloads:
            self.active_downloads[url].pause()

    def resume_download(self, url):
        if url in self.active_downloads:
            self.active_downloads[url].resume()

    def cancel_download(self, url):
        if url in self.active_downloads:
            self.active_downloads[url].cancel()
            del self.active_downloads[url]
        elif url in self.download_queue:
            self.download_queue.remove(url)

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance