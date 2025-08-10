from PyQt5.QtWidgets import QWidget, QVBoxLayout, QListView, QPushButton, QLabel
from PyQt5.QtCore import Qt, QAbstractListModel, QModelIndex
from src.services.download_service import DownloadService

class DownloadListModel(QAbstractListModel):
    def __init__(self, downloads):
        super().__init__()
        self.downloads = downloads

    def rowCount(self, parent=QModelIndex()):
        return len(self.downloads)

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            url, progress = self.downloads[index.row()]
            return f"{url} - {progress}%"

class OfflineContentTab(QWidget):
    def __init__(self):
        super().__init__()
        self.download_service = DownloadService.instance()
        self.download_service.download_progress.connect(self._update_download_list)
        self.download_service.download_complete.connect(self._update_download_list)
        self.download_service.download_error.connect(self._update_download_list)

        self.layout = QVBoxLayout(self)
        self.download_list_view = QListView()
        self.download_list_model = DownloadListModel([])
        self.download_list_view.setModel(self.download_list_model)

        self.layout.addWidget(QLabel("Offline Content"))
        self.layout.addWidget(self.download_list_view)

        self.pause_button = QPushButton("Pause All")
        self.pause_button.clicked.connect(self._pause_all)
        self.layout.addWidget(self.pause_button)

        self.resume_button = QPushButton("Resume All")
        self.resume_button.clicked.connect(self._resume_all)
        self.layout.addWidget(self.resume_button)

        self.delete_button = QPushButton("Delete All")
        self.delete_button.clicked.connect(self._delete_all)
        self.layout.addWidget(self.delete_button)

    def _update_download_list(self, url, progress=None):
        downloads = [(url, progress) for url, progress in self.download_service.active_downloads.items()]
        self.download_list_model.downloads = downloads
        self.download_list_model.layoutChanged.emit()

    def _pause_all(self):
        for url in self.download_service.active_downloads.keys():
            self.download_service.pause_download(url)

    def _resume_all(self):
        for url in self.download_service.active_downloads.keys():
            self.download_service.resume_download(url)

    def _delete_all(self):
        for url in list(self.download_service.active_downloads.keys()):
            self.download_service.cancel_download(url)
        self._update_download_list(None)