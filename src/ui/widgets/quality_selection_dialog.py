"""
Quality Selection Dialog for Export Features
"""
import threading
import time
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QProgressBar, QMessageBox,
    QHeaderView, QAbstractItemView
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, pyqtSlot
from PyQt5.QtGui import QFont
import requests
import m3u8

class QualityDetectionWorker(QThread):
    """Worker thread for detecting available video qualities"""
    qualitiesDetected = pyqtSignal(list)  # List of quality dictionaries
    detectionFailed = pyqtSignal(str)     # Error message
    
    def __init__(self, episode_url, timeout=10):
        super().__init__()
        self.episode_url = episode_url
        self.timeout = timeout
        
    def run(self):
        """Detect available qualities from the stream URL"""
        try:
            # 1. Fast check: Inspect extension of the URL path first
            from urllib.parse import urlparse
            parsed_url = urlparse(self.episode_url)
            path = parsed_url.path.lower()
            
            # Common direct video file extensions that are never HLS playlists
            direct_video_extensions = ('.mp4', '.mkv', '.avi', '.ts', '.mp3', '.m4a', '.flv', '.wmv', '.mov')
            if path.endswith(direct_video_extensions):
                print(f"[QualityDetectionWorker] URL ends with direct video extension: {path}. Skipping fetch.")
                self.qualitiesDetected.emit([])
                return
                
            # 2. Network check: Use stream=True to only fetch headers first
            response = requests.get(self.episode_url, timeout=self.timeout, stream=True)
            if response.status_code != 200:
                self.detectionFailed.emit(f"HTTP {response.status_code}")
                return
                
            # Check Content-Type header
            content_type = response.headers.get('Content-Type', '').lower()
            
            # If Content-Type is a standard video container, skip downloading
            if 'video/' in content_type and 'mpegurl' not in content_type and 'apple.mpegurl' not in content_type:
                print(f"[QualityDetectionWorker] Content-Type is a direct video format: {content_type}. Skipping fetch.")
                self.qualitiesDetected.emit([])
                return
                
            # 3. Read only a small chunk to check if it contains M3U8 headers
            # HLS master playlists are small text files. We only need the first few hundred bytes.
            content = ""
            for chunk in response.iter_content(chunk_size=4096, decode_unicode=True):
                if chunk:
                    content += chunk
                    # Stop reading if we got enough content to identify and parse the playlist
                    # Or if we've read enough and determined it is not a playlist
                    if len(content) > 65536 or '#EXT-X-STREAM-INF' in content or '#EXTM3U' not in content:
                        break
            
            # Check if it's an HLS playlist
            if '#EXTM3U' in content and '#EXT-X-STREAM-INF' in content:
                self._parse_hls_playlist(content)
            else:
                # Not an HLS playlist, assume single quality
                self.qualitiesDetected.emit([])
                
        except requests.RequestException as e:
            self.detectionFailed.emit(str(e))
        except Exception as e:
            self.detectionFailed.emit(f"Unexpected error: {str(e)}")
    
    def _parse_hls_playlist(self, playlist_content):
        """Parse HLS playlist to extract quality variants"""
        try:
            # Parse with m3u8 library
            playlist = m3u8.loads(playlist_content)
            
            if not playlist.playlists:
                self.qualitiesDetected.emit([])
                return
            
            qualities = []
            for variant in playlist.playlists:
                quality_info = {
                    'url': variant.uri,
                    'bandwidth': variant.stream_info.bandwidth if variant.stream_info.bandwidth else 0,
                    'resolution': variant.stream_info.resolution if variant.stream_info.resolution else None,
                    'codecs': variant.stream_info.codecs if variant.stream_info.codecs else None,
                }
                
                # Add quality label based on bandwidth or resolution
                quality_info['label'] = self._get_quality_label(quality_info)
                qualities.append(quality_info)
            
            # Sort by bandwidth (highest first)
            qualities.sort(key=lambda x: x['bandwidth'], reverse=True)
            self.qualitiesDetected.emit(qualities)
            
        except Exception as e:
            self.detectionFailed.emit(f"Playlist parsing error: {str(e)}")
    
    def _get_quality_label(self, quality_info):
        """Generate a quality label based on resolution or bandwidth"""
        if quality_info['resolution']:
            width, height = quality_info['resolution']
            if height >= 1080:
                return "High (1080p+)"
            elif height >= 720:
                return "Medium (720p)"
            elif height >= 480:
                return "Low (480p)"
            else:
                return f"Low ({height}p)"
        elif quality_info['bandwidth']:
            # Estimate quality based on bandwidth
            bandwidth_mbps = quality_info['bandwidth'] / 1000000
            if bandwidth_mbps >= 5:
                return "High"
            elif bandwidth_mbps >= 2:
                return "Medium"
            else:
                return "Low"
        else:
            return "Unknown"


class QualitySelectionDialog(QDialog):
    """Dialog for selecting video quality for export"""
    
    def __init__(self, episode_data, api_client, translations, parent=None):
        super().__init__(parent)
        self.episode_data = episode_data
        self.api_client = api_client
        self.translations = translations
        self.selected_quality = None
        self.qualities = []
        
        self.setWindowTitle(self.translations.get("Select Quality", "Select Quality"))
        self.setMinimumSize(500, 350)
        self.setModal(True)
        
        self._setup_ui()
        self._detect_qualities()
    
    def _setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)
        
        # Header
        header_label = QLabel(self.translations.get("Choose video quality for export:", "Choose video quality for export:"))
        header_label.setFont(QFont('Arial', 12, QFont.Bold))
        layout.addWidget(header_label)
        
        # Progress bar for detection
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel(self.translations.get("Detecting available qualities...", "Detecting available qualities..."))
        layout.addWidget(self.status_label)
        
        # Quality table
        self.quality_table = QTableWidget()
        self.quality_table.setColumnCount(3)
        self.quality_table.setHorizontalHeaderLabels([
            self.translations.get("Quality", "Quality"),
            self.translations.get("Resolution", "Resolution"),
            self.translations.get("Bandwidth", "Bandwidth")
        ])
        
        # Configure table
        self.quality_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.quality_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.quality_table.horizontalHeader().setStretchLastSection(True)
        self.quality_table.setAlternatingRowColors(True)
        self.quality_table.setVisible(False)  # Hide until qualities are loaded
        
        layout.addWidget(self.quality_table)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.export_button = QPushButton(self.translations.get("Export with Selected Quality", "Export with Selected Quality"))
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self.accept)
        
        cancel_button = QPushButton(self.translations.get("Cancel", "Cancel"))
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(self.export_button)
        
        layout.addLayout(button_layout)
        
        # Connect table selection
        self.quality_table.itemSelectionChanged.connect(self._on_quality_selected)
    
    def _detect_qualities(self):
        """Start quality detection in background thread"""
        episode_id = self.episode_data.get('id') or self.episode_data.get('stream_id')
        container_extension = self.episode_data.get('container_extension', 'mp4')
        
        # Support both movie and episode/series URLs
        stream_type = self.episode_data.get('stream_type', 'episode')
        if stream_type == 'movie':
            episode_url = self.api_client.get_movie_url(episode_id, container_extension)
        else:
            episode_url = self.api_client.get_series_url(episode_id, container_extension)
        
        if not episode_url:
            self._on_detection_failed("Could not get episode URL")
            return
        
        # Start worker thread
        self.worker = QualityDetectionWorker(episode_url)
        self.worker.qualitiesDetected.connect(self._on_qualities_detected)
        self.worker.detectionFailed.connect(self._on_detection_failed)
        self.worker.start()
    
    @pyqtSlot(list)
    def _on_qualities_detected(self, qualities):
        """Handle detected qualities"""
        self.qualities = qualities
        self.progress_bar.setVisible(False)
        
        if not qualities:
            # No quality variants found - server likely doesn't support multiple qualities
            self.status_label.setText(self.translations.get("Server does not support multiple qualities", "Server does not support multiple qualities"))
            
            # Add a single "Auto" option
            self.quality_table.setRowCount(1)
            self.quality_table.setItem(0, 0, QTableWidgetItem(self.translations.get("Auto (Best Available)", "Auto (Best Available)")))
            self.quality_table.setItem(0, 1, QTableWidgetItem("-"))
            self.quality_table.setItem(0, 2, QTableWidgetItem("-"))
            
            # Select the auto option by default
            self.quality_table.selectRow(0)
            self.selected_quality = None  # None means use default URL
        else:
            # Show detected qualities
            self.status_label.setText(f"{len(qualities)} {self.translations.get('qualities found', 'qualities found')}")
            self._populate_quality_table()
        
        self.quality_table.setVisible(True)
        self.export_button.setEnabled(True)
    
    @pyqtSlot(str)
    def _on_detection_failed(self, error_message):
        """Handle detection failure"""
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"{self.translations.get('Quality detection failed', 'Quality detection failed')}: {error_message}")
        
        # Still provide option to export with default quality
        self.quality_table.setRowCount(1)
        self.quality_table.setItem(0, 0, QTableWidgetItem(self.translations.get("Auto (Best Available)", "Auto (Best Available)")))
        self.quality_table.setItem(0, 1, QTableWidgetItem("-"))
        self.quality_table.setItem(0, 2, QTableWidgetItem("-"))
        
        self.quality_table.selectRow(0)
        self.quality_table.setVisible(True)
        self.export_button.setEnabled(True)
        self.selected_quality = None
    
    def _populate_quality_table(self):
        """Populate the quality table with detected qualities"""
        self.quality_table.setRowCount(len(self.qualities) + 1)  # +1 for Auto option
        
        # Add "Auto" option first
        self.quality_table.setItem(0, 0, QTableWidgetItem(self.translations.get("Auto (Best Available)", "Auto (Best Available)")))
        self.quality_table.setItem(0, 1, QTableWidgetItem("-"))
        self.quality_table.setItem(0, 2, QTableWidgetItem("-"))
        
        # Add detected qualities
        for i, quality in enumerate(self.qualities, 1):
            self.quality_table.setItem(i, 0, QTableWidgetItem(quality['label']))
            
            # Resolution
            if quality['resolution']:
                resolution_text = f"{quality['resolution'][0]}x{quality['resolution'][1]}"
            else:
                resolution_text = self.translations.get("Unknown", "Unknown")
            self.quality_table.setItem(i, 1, QTableWidgetItem(resolution_text))
            
            # Bandwidth
            if quality['bandwidth']:
                bandwidth_text = f"{quality['bandwidth'] / 1000000:.1f} Mbps"
            else:
                bandwidth_text = self.translations.get("Unknown", "Unknown")
            self.quality_table.setItem(i, 2, QTableWidgetItem(bandwidth_text))
        
        # Select Auto by default
        self.quality_table.selectRow(0)
        self.selected_quality = None
    
    def _on_quality_selected(self):
        """Handle quality selection change"""
        selected_rows = self.quality_table.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            if row == 0:
                # Auto selected
                self.selected_quality = None
            else:
                # Specific quality selected
                self.selected_quality = self.qualities[row - 1]
    
    def get_selected_quality(self):
        """Get the selected quality information"""
        return self.selected_quality
    
    def get_export_url(self):
        """Get the URL to use for export based on selection"""
        episode_id = self.episode_data.get('id') or self.episode_data.get('stream_id')
        container_extension = self.episode_data.get('container_extension', 'mp4')
        stream_type = self.episode_data.get('stream_type', 'episode')
        
        if self.selected_quality is None:
            # Use default API URL
            if stream_type == 'movie':
                return self.api_client.get_movie_url(episode_id, container_extension)
            else:
                return self.api_client.get_series_url(episode_id, container_extension)
        else:
            # Use specific quality URL (need to resolve relative URLs)
            if stream_type == 'movie':
                base_url = self.api_client.get_movie_url(episode_id, container_extension)
            else:
                base_url = self.api_client.get_series_url(episode_id, container_extension)
                
            if self.selected_quality['url'].startswith('http'):
                return self.selected_quality['url']
            else:
                # Resolve relative URL
                from urllib.parse import urljoin
                return urljoin(base_url, self.selected_quality['url'])