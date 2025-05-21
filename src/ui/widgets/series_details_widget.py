"""
Series Details Widget for the application
"""
import os
import time
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton, 
    QListWidget, QMessageBox, QFileDialog, QListWidgetItem
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QFont

# Assuming DownloadItem is accessible or will be moved/imported appropriately
# from src.utils.download import DownloadItem, BatchDownloadThread
# For now, let's define a placeholder or assume it's passed if needed by methods here

class DownloadItem:
    def __init__(self, name, save_path, download_thread=None):
        self.name = name
        self.save_path = save_path
        self.progress = 0
        self.status = 'active'  # active, paused, completed, error
        self.download_thread = download_thread
        self.error_message = None
        self.time_created = time.time()
        self.time_completed = None
        self.total_size = 0
        self.downloaded_size = 0
        self.speed = 0  # bytes per second
        self.estimated_time = 0  # seconds remaining

class SeriesDetailsWidget(QWidget):
    back_clicked = pyqtSignal()
    play_episode_requested = pyqtSignal(object)  # episode data
    toggle_favorite_series_requested = pyqtSignal(object) # series data
    # Signals for download/export actions, will need to be connected in SeriesTab
    download_episode_requested = pyqtSignal(object) # episode data
    download_season_requested = pyqtSignal(str) # season number
    export_season_requested = pyqtSignal(str) # season number

    def __init__(self, series_data, api_client, main_window, parent=None):
        super().__init__(parent)
        self.series_data = series_data
        self.api_client = api_client
        self.main_window = main_window # For accessing player, favorites status etc.
        self.current_episodes = []
        self.current_season = None
        self.series_info = {} # To store detailed series info including episodes

        self._setup_ui()
        self._load_initial_data()

    def _setup_ui(self):
        layout = QHBoxLayout(self)

        # --- Left: Poster, Back button, Favorite button --- 
        left_layout = QVBoxLayout()
        
        self.back_btn = QPushButton("← Back")
        self.back_btn.setFixedWidth(80)
        self.back_btn.clicked.connect(self.back_clicked.emit)
        left_layout.addWidget(self.back_btn, alignment=Qt.AlignLeft)

        self.poster_label = QLabel()
        self.poster_label.setAlignment(Qt.AlignTop)
        left_layout.addWidget(self.poster_label)

        self.favorite_series_btn = QPushButton()
        self.favorite_series_btn.setFixedWidth(180) # Match poster width
        self.favorite_series_btn.clicked.connect(self._on_toggle_favorite_series)
        left_layout.addWidget(self.favorite_series_btn)
        
        # Placeholder for Download Season and Export Season buttons
        self.download_season_btn = QPushButton("Available Offline")
        self.download_season_btn.setVisible(False)
        self.download_season_btn.clicked.connect(self._on_download_season)
        left_layout.addWidget(self.download_season_btn)

        self.export_season_btn = QPushButton("Export Season URLs")
        self.export_season_btn.setVisible(False)
        self.export_season_btn.clicked.connect(self._on_export_season)
        left_layout.addWidget(self.export_season_btn)

        left_layout.addStretch() # Pushes buttons to the top
        layout.addLayout(left_layout)

        # --- Right: Metadata, seasons, episodes --- 
        right_layout = QVBoxLayout()
        self.title_label = QLabel()
        self.title_label.setFont(QFont('Arial', 16, QFont.Bold))
        right_layout.addWidget(self.title_label)

        self.meta_label = QLabel()
        right_layout.addWidget(self.meta_label)

        self.desc_text = QTextEdit()
        self.desc_text.setReadOnly(True)
        self.desc_text.setMaximumHeight(100) # Increased height
        right_layout.addWidget(self.desc_text)

        self.seasons_list = QListWidget()
        self.episodes_list = QListWidget()
        self.seasons_list.itemClicked.connect(self._on_season_clicked)
        self.episodes_list.itemDoubleClicked.connect(self._on_episode_double_clicked)
        self.episodes_list.currentItemChanged.connect(self._update_play_and_download_buttons_state)

        right_layout.addWidget(QLabel("Seasons"))
        right_layout.addWidget(self.seasons_list)
        right_layout.addWidget(QLabel("Episodes"))
        right_layout.addWidget(self.episodes_list)

        # Action buttons for episodes
        episode_actions_layout = QHBoxLayout()
        self.play_episode_btn = QPushButton("Play")
        self.play_episode_btn.setEnabled(False)
        self.play_episode_btn.setVisible(False)
        self.play_episode_btn.clicked.connect(self._on_play_selected_episode)
        episode_actions_layout.addWidget(self.play_episode_btn)

        self.download_episode_btn = QPushButton("Download Episode")
        self.download_episode_btn.setEnabled(False)
        self.download_episode_btn.setVisible(False)
        self.download_episode_btn.clicked.connect(self._on_download_episode)
        episode_actions_layout.addWidget(self.download_episode_btn)
        right_layout.addLayout(episode_actions_layout)

        self.trailer_btn = QPushButton("WATCH TRAILER")
        self.trailer_btn.setVisible(False) # Initially hidden
        self.trailer_btn.clicked.connect(self._on_play_trailer)
        right_layout.addWidget(self.trailer_btn)

        layout.addLayout(right_layout)
        self.setLayout(layout)

    def _load_initial_data(self):
        series_id = self.series_data.get('series_id')
        self.title_label.setText(self.series_data.get('name', ''))
        self.meta_label.setText(f"Year: {self.series_data.get('year', '--')} | Genre: {self.series_data.get('genre', '--')}")
        self.desc_text.setPlainText(self.series_data.get('plot', ''))

        # Load poster
        pix = QPixmap()
        series_cover_url = self.series_data.get('cover')
        if series_cover_url:
            image_data = self.api_client.get_image_data(series_cover_url)
            if image_data:
                pix.loadFromData(image_data)
        if not pix or pix.isNull():
            pix = QPixmap('assets/series.png') # Assuming assets path is correct relative to main app
        if not pix.isNull():
            self.poster_label.setPixmap(pix.scaled(180, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        
        self._update_favorite_series_button_text()

        # Fetch detailed series info for trailer, seasons, and potentially more accurate metadata
        if series_id:
            try:
                success, series_info_full = self.api_client.get_series_info(series_id)
                if success and series_info_full:
                    self.series_info = series_info_full # Store for season/episode loading
                    info_dict = series_info_full.get('info', {})
                    
                    # Update metadata from detailed info if available
                    self.meta_label.setText(f"Year: {info_dict.get('releaseDate', self.series_data.get('year', '--'))} | Genre: {info_dict.get('genre', self.series_data.get('genre', '--'))}")
                    self.desc_text.setPlainText(info_dict.get('plot', self.series_data.get('plot', '')))
                    
                    # Update poster if a better one is in detailed info
                    if 'cover' in info_dict and info_dict['cover']:
                        detailed_cover_data = self.api_client.get_image_data(info_dict['cover'])
                        if detailed_cover_data:
                            detailed_pix = QPixmap()
                            detailed_pix.loadFromData(detailed_cover_data)
                            if not detailed_pix.isNull():
                                self.poster_label.setPixmap(detailed_pix.scaled(180, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation))

                    trailer_url = info_dict.get('youtube_trailer') or info_dict.get('trailer_url') # Prioritize youtube_trailer
                    if trailer_url:
                        self.trailer_url = trailer_url # Store for the button
                        self.trailer_btn.setVisible(True)
                    else:
                        self.trailer_btn.setVisible(False)

                    # Load seasons using the fetched series_info
                    self._load_seasons_from_info()
                else:
                    QMessageBox.warning(self, "Error", f"Failed to load detailed series information: {series_info_full}")
                    self._load_seasons_from_info() # Attempt to load seasons even if full info fails, if series_info has episodes

            except Exception as e:
                print(f"Error fetching detailed series metadata: {e}")
                QMessageBox.warning(self, "Error", f"Error fetching detailed series metadata: {str(e)}")
                self._load_seasons_from_info() # Fallback
        else:
             QMessageBox.warning(self, "Error", "Series ID is missing, cannot load details.")

    def _load_seasons_from_info(self):
        self.seasons_list.clear()
        self.episodes_list.clear()
        if 'episodes' in self.series_info:
            # Sort season numbers numerically if they are strings
            try:
                sorted_season_numbers = sorted(self.series_info['episodes'].keys(), key=int)
            except ValueError:
                 # Handle cases where season numbers might not be purely numeric (e.g., 'Special')
                sorted_season_numbers = sorted(self.series_info['episodes'].keys())

            for season_number in sorted_season_numbers:
                self.seasons_list.addItem(f"Season {season_number}")
        else:
            # Optionally, display a message if no seasons/episodes are found
            # self.seasons_list.addItem("No seasons available")
            pass 

    def _on_season_clicked(self, item):
        season_text = item.text()
        season_number_str = season_text.replace("Season ", "")
        
        if hasattr(self, 'series_info') and 'episodes' in self.series_info and season_number_str in self.series_info['episodes']:
            self.export_season_btn.setVisible(True)
            self.download_season_btn.setVisible(True)
            episodes_data = self.series_info['episodes'][season_number_str]
            self.episodes_list.clear()
            self.current_episodes = episodes_data
            self.current_season = season_number_str
            
            # Sort episodes by episode_num before adding
            try:
                sorted_episodes = sorted(episodes_data, key=lambda x: int(x.get('episode_num', 0)))
            except ValueError:
                sorted_episodes = episodes_data # Fallback if episode_num is not int

            for episode in sorted_episodes:
                episode_title = episode.get('title', 'Unnamed Episode')
                list_item = QListWidgetItem(f"E{episode.get('episode_num', '?')} - {episode_title}")
                list_item.setData(Qt.UserRole, episode) # Store full episode dict
                self.episodes_list.addItem(list_item)
        self._update_play_and_download_buttons_state() # Update button states after loading episodes

    def _update_play_and_download_buttons_state(self):
        selected_episode_item = self.episodes_list.currentItem()
        is_episode_selected = selected_episode_item is not None
        self.play_episode_btn.setEnabled(is_episode_selected)
        self.download_episode_btn.setEnabled(is_episode_selected)
        self.play_episode_btn.setVisible(is_episode_selected)
        self.download_episode_btn.setVisible(is_episode_selected)

    def _on_episode_double_clicked(self, item):
        self._play_episode_from_item(item)

    def _on_play_selected_episode(self):
        item = self.episodes_list.currentItem()
        if item:
            self._play_episode_from_item(item)

    def _play_episode_from_item(self, item):
        episode_data = item.data(Qt.UserRole)
        if episode_data:
            self.play_episode_requested.emit(episode_data)
        else:
            QMessageBox.warning(self, "Error", "Episode data not found.")

    def _on_toggle_favorite_series(self):
        self.toggle_favorite_series_requested.emit(self.series_data)
        # The button text/icon update should be handled by the main window
        # or by re-checking favorite status after the signal is processed.
        # For immediate feedback, we can call _update_favorite_series_button_text here,
        # but it's better if the source of truth (main_window) drives this.
        # self._update_favorite_series_button_text() # Re-query status

    def _update_favorite_series_button_text(self):
        # This method now relies on main_window to check favorite status
        if not self.main_window or not hasattr(self.main_window, 'is_favorite'):
            self.favorite_series_btn.setText("Favorite N/A")
            return

        favorite_item_check = {
            'series_id': self.series_data.get('series_id'),
            'stream_type': 'series'
        }

        if self.main_window.is_favorite(favorite_item_check):
            self.favorite_series_btn.setText("★") # Or use an icon
            self.favorite_series_btn.setStyleSheet("QPushButton { color: gold; background: transparent; font-size: 16px; }")
            self.favorite_series_btn.setToolTip("Remove from favorites")
        else:
            self.favorite_series_btn.setText("☆") # Or use an icon
            self.favorite_series_btn.setStyleSheet("QPushButton { color: white; background: transparent; font-size: 16px; }")
            self.favorite_series_btn.setToolTip("Add to favorites")

    def _on_play_trailer(self):
        if hasattr(self, 'trailer_url') and self.trailer_url:
            if self.main_window and hasattr(self.main_window, 'player_window'):
                # The player_window.play method expects a dictionary for the second argument
                # For trailers, it's simpler, but good to maintain consistency if possible
                trailer_info = {'name': f"{self.series_data.get('name', 'Series')} Trailer", 'stream_type': 'trailer'}
                self.main_window.player_window.play(self.trailer_url, trailer_info)
                self.main_window.player_window.show()
            else:
                QMessageBox.warning(self, "Error", "Player window not available.")
        else:
            QMessageBox.information(self, "Trailer", "No trailer URL available for this series.")

    def _on_download_episode(self):
        item = self.episodes_list.currentItem()
        if not item:
            QMessageBox.warning(self, "Error", "No episode selected for download.")
            return
        episode_data = item.data(Qt.UserRole)
        if episode_data:
            self.download_episode_requested.emit(episode_data)
        else:
            QMessageBox.warning(self, "Error", "Episode data not found for download.")

    def _on_download_season(self):
        if not self.seasons_list.currentItem():
            QMessageBox.warning(self, "Error", "No season selected to download.")
            return
        season_text = self.seasons_list.currentItem().text()
        season_number = season_text.replace("Season ", "")
        self.download_season_requested.emit(season_number)

    def _on_export_season(self):
        if not self.seasons_list.currentItem():
            QMessageBox.warning(self, "Error", "No season selected to export.")
            return
        season_text = self.seasons_list.currentItem().text()
        season_number = season_text.replace("Season ", "")
        self.export_season_requested.emit(season_number)

    # Public method to be called by SeriesTab after favorite status changes
    def refresh_favorite_button(self):
        self._update_favorite_series_button_text()

    # Placeholder for current_detailed_series if SeriesTab needs it
    # This widget itself is the detail view, so series_data is its primary data
    def get_current_detailed_series(self):
        return self.series_data

    # Placeholder for series_info if SeriesTab needs it
    def get_series_info(self):
        return self.series_info

    # Placeholder for current_episodes if SeriesTab needs it
    def get_current_episodes(self):
        return self.current_episodes

    # Placeholder for current_season if SeriesTab needs it
    def get_current_season(self):
        return self.current_season