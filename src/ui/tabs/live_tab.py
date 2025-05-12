"""
Live TV tab for the application
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
                            QListWidget, QPushButton, QLineEdit, QMessageBox,
                            QFileDialog, QLabel)
from PyQt5.QtCore import Qt, pyqtSignal
from src.ui.player import MediaPlayer
from src.utils.recorder import RecordingThread
from src.ui.widgets.dialogs import ProgressDialog

class LiveTab(QWidget):
    """Live TV tab widget"""
    add_to_favorites = pyqtSignal(dict)
    
    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.live_channels = []
        self.current_channel = None
        self.recording_thread = None
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the UI components"""
        layout = QVBoxLayout(self)
        
        # Search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search channels...")
        self.search_input.textChanged.connect(self.search_channels)
        search_layout.addWidget(self.search_input)
        
        # Main content area with splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Categories and channels lists
        lists_widget = QWidget()
        lists_layout = QVBoxLayout(lists_widget)
        lists_layout.setContentsMargins(0, 0, 0, 0)
        
        self.categories_list = QListWidget()
        self.categories_list.setMinimumWidth(200)
        self.categories_list.itemClicked.connect(self.category_clicked)
        
        self.channels_list = QListWidget()
        self.channels_list.setMinimumWidth(300)
        self.channels_list.itemDoubleClicked.connect(self.channel_double_clicked)
        
        lists_layout.addWidget(QLabel("Categories"))
        lists_layout.addWidget(self.categories_list)
        lists_layout.addWidget(QLabel("Channels"))
        lists_layout.addWidget(self.channels_list)
        
        # Player and controls
        player_widget = QWidget()
        player_layout = QVBoxLayout(player_widget)
        player_layout.setContentsMargins(0, 0, 0, 0)
        
        self.player = MediaPlayer()
        
        # Additional controls
        controls_layout = QHBoxLayout()
        
        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self.play_channel)
        
        self.record_button = QPushButton("Record")
        self.record_button.clicked.connect(self.record_channel)
        
        self.stop_record_button = QPushButton("Stop Recording")
        self.stop_record_button.clicked.connect(self.stop_recording)
        self.stop_record_button.setEnabled(False)
        
        self.add_favorite_button = QPushButton("Add to Favorites")
        self.add_favorite_button.clicked.connect(self.add_to_favorites_clicked)
        
        controls_layout.addWidget(self.play_button)
        controls_layout.addWidget(self.record_button)
        controls_layout.addWidget(self.stop_record_button)
        controls_layout.addWidget(self.add_favorite_button)
        
        player_layout.addWidget(self.player)
        player_layout.addLayout(controls_layout)
        
        # Add widgets to splitter
        splitter.addWidget(lists_widget)
        splitter.addWidget(player_widget)
        splitter.setSizes([400, 800])
        
        # Add all components to main layout
        layout.addLayout(search_layout)
        layout.addWidget(splitter)
    
    def load_categories(self):
        """Load live TV categories from the API"""
        self.categories_list.clear()
        
        success, data = self.api_client.get_live_categories()
        if success:
            for category in data:
                self.categories_list.addItem(category['category_name'])
        else:
            QMessageBox.warning(self, "Error", f"Failed to load categories: {data}")
    
    def category_clicked(self, item):
        """Handle category selection"""
        category_name = item.text()
        
        # Find category ID
        success, categories = self.api_client.get_live_categories()
        if not success:
            QMessageBox.warning(self, "Error", f"Failed to load categories: {categories}")
            return
        
        category_id = None
        for category in categories:
            if category['category_name'] == category_name:
                category_id = category['category_id']
                break
        
        if category_id:
            self.load_channels(category_id)
    
    def load_channels(self, category_id):
        """Load channels for the selected category"""
        self.channels_list.clear()
        
        success, data = self.api_client.get_live_streams(category_id)
        if success:
            self.live_channels = data
            for channel in data:
                self.channels_list.addItem(channel['name'])
        else:
            QMessageBox.warning(self, "Error", f"Failed to load channels: {data}")
    
    def search_channels(self, text):
        """Search channels based on input text"""
        if not self.live_channels:
            return
        
        text = text.lower()
        self.channels_list.clear()
        
        for channel in self.live_channels:
            if text in channel['name'].lower():
                self.channels_list.addItem(channel['name'])
    
    def channel_double_clicked(self, item):
        """Handle channel double-click"""
        self.play_channel()
    
    def play_channel(self):
        """Play the selected channel"""
        if not self.channels_list.currentItem():
            QMessageBox.warning(self, "Error", "No channel selected")
            return
        
        channel_name = self.channels_list.currentItem().text()
        channel = None
        for ch in self.live_channels:
            if ch['name'] == channel_name:
                channel = ch
                break
        
        if not channel:
            return
        
        stream_id = channel['stream_id']
        stream_url = self.api_client.get_live_stream_url(stream_id)
        
        if self.player.play(stream_url):
            self.current_channel = {
                'name': channel['name'],
                'stream_url': stream_url,
                'stream_id': stream_id,
                'stream_type': 'live'
            }
    
    def record_channel(self):
        """Record the current channel"""
        if not self.current_channel:
            QMessageBox.warning(self, "Error", "No channel is playing")
            return
        
        # Ask for save location
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Recording", f"{self.current_channel['name']}.mp4", "MP4 Files (*.mp4)"
        )
        
        if not save_path:
            return
        
        # Start recording thread
        self.recording_thread = RecordingThread(
            self.current_channel['stream_url'], 
            save_path, 
            self.api_client.headers
        )
        self.recording_thread.recording_started.connect(self.recording_started)
        self.recording_thread.recording_error.connect(self.recording_error)
        self.recording_thread.recording_stopped.connect(self.recording_stopped)
        
        self.recording_thread.start()
        
        # Update UI
        self.record_button.setEnabled(False)
        self.stop_record_button.setEnabled(True)
    
    def stop_recording(self):
        """Stop the current recording"""
        if self.recording_thread and self.recording_thread.isRunning():
            self.recording_thread.stop_recording()
    
    def recording_started(self):
        """Handle recording started event"""
        QMessageBox.information(self, "Recording", "Recording started successfully")
    
    def recording_error(self, error_message):
        """Handle recording error"""
        QMessageBox.critical(self, "Recording Error", error_message)
        self.record_button.setEnabled(True)
        self.stop_record_button.setEnabled(False)
    
    def recording_stopped(self):
        """Handle recording stopped event"""
        QMessageBox.information(self, "Recording", "Recording stopped successfully")
        self.record_button.setEnabled(True)
        self.stop_record_button.setEnabled(False)
    
    def add_to_favorites_clicked(self):
        """Add current channel to favorites"""
        if not self.current_channel:
            QMessageBox.warning(self, "Error", "No channel is playing")
            return
        
        self.add_to_favorites.emit(self.current_channel)
