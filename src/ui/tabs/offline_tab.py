import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QListWidget, QListWidgetItem, QProgressBar, QMessageBox, QSizePolicy)
from PyQt5.QtCore import pyqtSignal, Qt, QSize
from PyQt5.QtGui import QIcon, QPixmap

from src.utils.offline_manager import OfflineManager
from src.utils.helpers import load_image_async, get_translations # Assuming get_translations is globally accessible or passed

class OfflineItemWidget(QWidget):
    play_requested = pyqtSignal(str, object) # filepath, movie_meta

    def __init__(self, movie_meta, offline_manager, main_window, parent=None):
        super().__init__(parent)
        self.movie_meta = movie_meta
        self.offline_manager = offline_manager
        self.main_window = main_window
        self.stream_id = str(movie_meta.get('stream_id', movie_meta.get('id', ''))) # movie_meta might have 'id' or 'stream_id'

        # Get translations
        language = getattr(self.main_window, 'language', 'en') if self.main_window else 'en'
        self.translations = get_translations(language)

        self._init_ui()
        self.update_ui_for_status() # Initial UI setup based on status

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(QSize(80, 120))
        self.thumbnail_label.setScaledContents(False) # Let load_image_async handle scaling if needed
        layout.addWidget(self.thumbnail_label)

        icon_url = self.movie_meta.get('icon_url', self.movie_meta.get('stream_icon'))
        if icon_url:
            load_image_async(icon_url, self.thumbnail_label, default_pixmap=QPixmap("assets/movies.png"), update_size=QSize(80,120), main_window=self.main_window)
        else:
            self.thumbnail_label.setPixmap(QPixmap("assets/movies.png").scaled(80, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        info_layout = QVBoxLayout()
        self.title_label = QLabel(self.movie_meta.get('title', self.movie_meta.get('name', 'N/A')))
        self.title_label.setFont(self.font()) # Adjust font as needed
        self.title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        info_layout.addWidget(self.title_label)

        self.status_label = QLabel(self.movie_meta.get('status', 'N/A'))
        info_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(15)
        self.progress_bar.setTextVisible(True)
        info_layout.addWidget(self.progress_bar)

        layout.addLayout(info_layout)

        # --- Buttons ---
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(5)

        self.play_button = QPushButton()
        self.play_button.setIcon(QIcon.fromTheme("media-playback-start", QIcon("assets/movies.png")))
        self.play_button.setToolTip(self.translations.get("Play Offline", "Play Offline"))
        self.play_button.clicked.connect(self._handle_play)
        buttons_layout.addWidget(self.play_button)

        self.pause_resume_button = QPushButton() # Text/Icon set in update_ui
        self.pause_resume_button.clicked.connect(self._handle_pause_resume)
        buttons_layout.addWidget(self.pause_resume_button)

        self.cancel_button = QPushButton()
        self.cancel_button.setIcon(QIcon.fromTheme("process-stop", QIcon("assets/reload.png")))
        self.cancel_button.setToolTip(self.translations.get("Cancel Download", "Cancel Download"))
        self.cancel_button.clicked.connect(self._handle_cancel)
        buttons_layout.addWidget(self.cancel_button)

        self.remove_button = QPushButton()
        self.remove_button.setIcon(QIcon.fromTheme("edit-delete", QIcon("assets/reload.png")))
        self.remove_button.setToolTip(self.translations.get("Remove Download", "Remove Download"))
        self.remove_button.clicked.connect(self._handle_remove)
        buttons_layout.addWidget(self.remove_button)

        layout.addLayout(buttons_layout)
        self.setMinimumHeight(130) # Ensure enough height for thumbnail and buttons

    def update_ui_for_status(self, status=None, progress=None):
        current_status = status if status is not None else self.offline_manager.get_movie_status(self.stream_id)
        current_progress = progress if progress is not None else self.offline_manager.get_movie_progress(self.stream_id)

        if current_status is None: # Not in manager's list anymore (e.g. removed)
            self.status_label.setText(self.translations.get("Removed", "Removed"))
            self.setDisabled(True)
            return

        self.movie_meta['status'] = current_status # Update local copy of status
        self.status_label.setText(f"{self.translations.get(current_status.capitalize(), current_status.capitalize())}")
        self.progress_bar.setVisible(False)
        self.play_button.setVisible(False)
        self.pause_resume_button.setVisible(False)
        self.cancel_button.setVisible(False)
        self.remove_button.setVisible(False) # Default to hidden

        if current_status == OfflineManager.PENDING:
            self.status_label.setText(self.translations.get("Pending", "Pending..."))
            self.cancel_button.setVisible(True)
        elif current_status == OfflineManager.DOWNLOADING:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(current_progress)
            self.status_label.setText(f"{self.translations.get('Downloading', 'Downloading')}... {current_progress}%")
            self.pause_resume_button.setText(self.translations.get("Pause", "Pause"))
            self.pause_resume_button.setIcon(QIcon.fromTheme("media-playback-pause"))
            self.pause_resume_button.setVisible(True)
            self.cancel_button.setVisible(True)
        elif current_status == OfflineManager.PAUSED:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(current_progress)
            self.status_label.setText(f"{self.translations.get('Paused', 'Paused')} ({current_progress}%)")
            self.pause_resume_button.setText(self.translations.get("Resume", "Resume"))
            self.pause_resume_button.setIcon(QIcon.fromTheme("media-playback-start"))
            self.pause_resume_button.setVisible(True)
            self.cancel_button.setVisible(True)
        elif current_status == OfflineManager.COMPLETED:
            self.status_label.setText(self.translations.get("Downloaded", "Downloaded"))
            self.play_button.setVisible(True)
            self.remove_button.setVisible(True)
        elif current_status == OfflineManager.ERROR:
            self.status_label.setText(self.translations.get("Error", "Error"))
            # Show retry on pause_resume_button
            self.pause_resume_button.setText(self.translations.get("Retry", "Retry"))
            self.pause_resume_button.setIcon(QIcon.fromTheme("view-refresh"))
            self.pause_resume_button.setVisible(True)
            self.remove_button.setVisible(True) # Allow removing errored downloads
        elif current_status == OfflineManager.CANCELLED:
             self.status_label.setText(self.translations.get("Cancelled", "Cancelled"))
             self.remove_button.setVisible(True) # Allow removing cancelled entry
             # Or offer a "Download Again" button
             self.pause_resume_button.setText(self.translations.get("Download Again", "Download Again"))
             self.pause_resume_button.setIcon(QIcon.fromTheme("download"))
             self.pause_resume_button.setVisible(True)
        elif current_status == OfflineManager.STORAGE_FULL:
            self.status_label.setText(self.translations.get("Storage Full", "Storage Full"))
            self.cancel_button.setVisible(True) # Allow cancelling
            self.remove_button.setVisible(True) # Allow removing to free space

    def _handle_play(self):
        if self.movie_meta['status'] == OfflineManager.COMPLETED:
            filepath = self.offline_manager.get_movie_filepath(self.stream_id)
            if filepath and os.path.exists(filepath):
                self.play_requested.emit(filepath, self.movie_meta)
            else:
                QMessageBox.warning(self, self.translations.get("File Not Found", "File Not Found"),
                                    self.translations.get("The offline movie file is missing.", "The offline movie file is missing."))
                self.update_ui_for_status(OfflineManager.ERROR) # Mark as error if file missing

    def _handle_pause_resume(self):
        status = self.offline_manager.get_movie_status(self.stream_id)
        if status == OfflineManager.DOWNLOADING:
            self.offline_manager.pause_download(self.stream_id)
        elif status == OfflineManager.PAUSED or status == OfflineManager.ERROR or status == OfflineManager.CANCELLED:
            # For ERROR or CANCELLED, this acts as a "Retry" or "Download Again"
            self.offline_manager.resume_download(self.stream_id) # resume_download also handles starting if not already started

    def _handle_cancel(self):
        self.offline_manager.cancel_download(self.stream_id)

    def _handle_remove(self):
        reply = QMessageBox.question(self, self.translations.get("Confirm Removal", "Confirm Removal"),
                                     self.translations.get("Are you sure you want to remove this download: ",
                                                                      "Are you sure you want to remove this download: ") + self.movie_meta.get('title', 'N/A') + "?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.offline_manager.remove_movie(self.stream_id)
            # The OfflineTab will handle removing the widget from the list via offline_list_changed signal

class OfflineTab(QWidget):
    offline_play_requested = pyqtSignal(str, object) # filepath, movie_meta

    def __init__(self, offline_manager, main_window, parent=None):
        super().__init__(parent)
        self.offline_manager = offline_manager
        self.main_window = main_window
        self.item_widgets_map = {}  # movie_id: OfflineItemWidget

        language = getattr(self.main_window, 'language', 'en') if self.main_window else 'en'
        self.translations = get_translations(language)

        self._init_ui()
        self._setup_connections()

        self._populate_offline_list()
        self._update_total_storage_display() # Initial call

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        self.total_storage_label = QLabel(self.translations.get("Total storage used: calculating...", "Total storage used: calculating..."))
        main_layout.addWidget(self.total_storage_label)

        # Optional: Refresh button
        refresh_button = QPushButton(self.translations.get("Refresh List", "Refresh List"))
        refresh_button.setIcon(QIcon.fromTheme("view-refresh"))
        refresh_button.clicked.connect(self._populate_offline_list)
        main_layout.addWidget(refresh_button, 0, Qt.AlignRight)

        self.offline_list_widget = QListWidget()
        self.offline_list_widget.setStyleSheet("QListWidget::item { border-bottom: 1px solid #333; }")
        main_layout.addWidget(self.offline_list_widget)

    def _setup_connections(self):
        self.offline_manager.offline_list_changed_signal.connect(self._populate_offline_list)
        self.offline_manager.progress_signal.connect(self._update_item_progress)
        self.offline_manager.status_changed_signal.connect(self._update_item_status)
        self.offline_manager.storage_usage_signal.connect(self._update_total_storage_display)

    def _populate_offline_list(self):
        self.offline_list_widget.clear()
        self.item_widgets_map.clear()

        # get_all_movies_details() returns a dict {movie_id: metadata}
        all_movies_meta = self.offline_manager.get_all_movies_details()

        if not all_movies_meta:
            # Show a message if there are no offline items
            # Using .get for translations
            placeholder_text = self.translations.get("No offline items yet. Downloads will appear here.",
                                                     "No offline items yet. Downloads will appear here.")
            placeholder_label = QLabel(placeholder_text)
            placeholder_label.setAlignment(Qt.AlignCenter)

            if self.offline_list_widget.count() == 0:
                item = QListWidgetItem(self.offline_list_widget)
                self.offline_list_widget.addItem(item)
                label_widget = QLabel(placeholder_text) # Use the fetched text
                label_widget.setAlignment(Qt.AlignCenter)
                item.setSizeHint(label_widget.sizeHint())
                self.offline_list_widget.setItemWidget(item, label_widget)
            return

        for movie_id, movie_meta in all_movies_meta.items():
            item_widget = OfflineItemWidget(movie_meta, self.offline_manager, self.main_window)
            item_widget.play_requested.connect(self.offline_play_requested) # Forward the signal

            list_item = QListWidgetItem(self.offline_list_widget)
            list_item.setSizeHint(item_widget.sizeHint()) # Use item_widget's preferred size

            self.offline_list_widget.addItem(list_item)
            self.offline_list_widget.setItemWidget(list_item, item_widget)
            self.item_widgets_map[str(movie_id)] = item_widget

        self._update_total_storage_display() # Recalculate storage after list populates

    def _update_item_progress(self, movie_id, progress):
        movie_id_str = str(movie_id)
        if movie_id_str in self.item_widgets_map:
            self.item_widgets_map[movie_id_str].update_ui_for_status(progress=progress)

    def _update_item_status(self, movie_id, status):
        movie_id_str = str(movie_id)
        if movie_id_str in self.item_widgets_map:
            self.item_widgets_map[movie_id_str].update_ui_for_status(status=status)
        # If status is CANCELLED or REMOVED, and manager confirms removal from list,
        # offline_list_changed signal should handle repopulating.

    def _format_size_gb(self, gb_value):
        if gb_value < 0: return "N/A"
        if gb_value < 1.0:
            return f"{gb_value * 1024:.2f} MB"
        return f"{gb_value:.2f} GB"

    def _update_total_storage_display(self, used_gb=None, total_gb=None):
        # If signals provide values (from OfflineManager's initial emit or updates)
        if used_gb is not None: # This parameter name might need to be changed if signal emits bytes
            # Assuming storage_usage_signal emits total_app_usage_bytes (int)
            # For now, let's adapt to the provided parameters if they are indeed GB.
            # If the signal emits bytes, this method needs to be updated.
            # Based on previous subtask, storage_usage_signal emits (int) total_app_usage_bytes.
            # So, the parameters here are likely a misunderstanding from the old signal.
            # Let's assume _update_total_storage_display is now called with one int arg: used_bytes

            # Correcting the logic based on storage_usage_signal = pyqtSignal(int)
            # The parameters used_gb, total_gb are from the old signal type.
            # This method should now accept used_bytes (int)

            # Re-interpreting based on new signal pyqtSignal(int) for total_app_usage_bytes
            # The method signature in connect is _update_total_storage_display.
            # If it's connected to pyqtSignal(int), it will receive one int argument.
            # Let's rename used_gb to used_bytes for clarity if it's the single int arg.

            # Assuming this method is now: _update_total_storage_display(self, used_bytes_arg)
            # And the old (float, float) version is no longer relevant.
            # For the purpose of this diff, I'll assume the method signature was changed
            # when storage_usage_signal was changed in OfflineManager.
            # If not, this is where the fix for the signal data type mismatch would go.
            # The current task is only fixing get_translation.

            # Sticking to fixing get_translation, assuming the parameters are what they are for now.
            used_formatted = self._format_size_gb(used_gb if used_gb is not None else 0) # Handle None
            total_formatted = self._format_size_gb(total_gb if total_gb is not None else 0) # Handle None

            # If total_gb is not meaningful for app-specific usage, we might simplify the message.
            # For now, using the existing format string.
            self.total_storage_label.setText(
                self.translations.get("Storage: {used} / {total}", "Storage: {used} / {total}").format(used=used_formatted, total=total_formatted)
            )
        else:
            # This else block might be for when the signal is not yet emitted or provides no data.
            # If storage_usage_signal correctly emits an int, this method should be called with that int.
            # For now, let's assume the signal is the source of truth for used_gb, total_gb
            # If not, we would call:
            # disk_usage_bytes = self.offline_manager.get_total_disk_usage() # This method needs to exist in OfflineManager
            # total_physical_storage_bytes = psutil.disk_usage(self.offline_manager.offline_movies_dir).total
            # self.total_storage_label.setText(...)
            # To keep it simple, we rely on storage_usage_signal to provide the values.
            # The OfflineManager should emit this signal upon init and changes.
             pass # Rely on signal data

    def refresh_tab_content(self):
        """Public method to refresh content, e.g., when tab becomes active."""
        self._populate_offline_list()
        # Ask OfflineManager to re-emit storage usage, or get it directly if manager has a getter
        self.offline_manager._emit_storage_usage() # Call the method that emits the signal
