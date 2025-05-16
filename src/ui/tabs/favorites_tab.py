"""
Favorites tab for the application
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
                            QListWidget, QPushButton, QLineEdit, QMessageBox,
                            QLabel)
from PyQt5.QtCore import Qt, pyqtSignal
from src.ui.player import MediaPlayer

class FavoritesTab(QWidget):
    """Favorites tab widget"""
    remove_from_favorites = pyqtSignal(int)
    
    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.favorites = []
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the UI components"""
        layout = QVBoxLayout(self)
        
        # Search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search favorites...")
        self.search_input.textChanged.connect(self.search_favorites)
        search_layout.addWidget(self.search_input)
        
        # Main content area with splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Favorites list
        list_widget = QWidget()
        list_layout = QVBoxLayout(list_widget)
        list_layout.setContentsMargins(0, 0, 0, 0)
        
        self.favorites_list = QListWidget()
        self.favorites_list.setMinimumWidth(300)
        self.favorites_list.itemDoubleClicked.connect(self.favorite_double_clicked)
        
        list_layout.addWidget(QLabel("Favorites"))
        list_layout.addWidget(self.favorites_list)
        
        # Player and controls
        player_widget = QWidget()
        player_layout = QVBoxLayout(player_widget)
        player_layout.setContentsMargins(0, 0, 0, 0)
        
        self.player = MediaPlayer()
        
        # Additional controls
        controls_layout = QHBoxLayout()
        
        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self.play_favorite)
        
        self.remove_button = QPushButton("Remove from Favorites")
        self.remove_button.clicked.connect(self.remove_favorite)
        
        controls_layout.addWidget(self.play_button)
        controls_layout.addWidget(self.remove_button)
        
        player_layout.addWidget(self.player)
        player_layout.addLayout(controls_layout)
        
        # Add widgets to splitter
        splitter.addWidget(list_widget)
        splitter.addWidget(player_widget)
        splitter.setSizes([300, 900])
        
        # Add all components to main layout
        layout.addLayout(search_layout)
        layout.addWidget(splitter)
    
    def set_favorites(self, favorites):
        """Set the favorites list"""
        self.favorites = favorites
        self.update_favorites_list()
    
    def update_favorites_list(self):
        """Update the favorites list widget"""
        self.favorites_list.clear()
        for favorite in self.favorites:
            self.favorites_list.addItem(favorite['name'])
    
    def search_favorites(self, text):
        """Search favorites based on input text"""
        text = text.lower()
        self.favorites_list.clear()
        
        for favorite in self.favorites:
            if text in favorite['name'].lower():
                self.favorites_list.addItem(favorite['name'])
    
    def favorite_double_clicked(self, item):
        """Handle favorite double-click"""
        self.play_favorite()
    
    def play_favorite(self):
        """Play the selected favorite"""
        if not self.favorites_list.currentItem():
            QMessageBox.warning(self, "Error", "No favorite selected")
            return
        
        index = self.favorites_list.currentRow()
        if index < 0 or index >= len(self.favorites):
            return
        
        favorite = self.favorites[index]
        
        stream_url = favorite.get('stream_url')
        stream_id = favorite.get('stream_id')
        container_extension = favorite.get('container_extension')
        if not stream_url:
            stream_url = self.api_client.get_movie_url(stream_id, container_extension)
        # Play the stream
        self.player.play(stream_url, favorite)
    
    def remove_favorite(self):
        """Remove the selected favorite"""
        if not self.favorites_list.currentItem():
            QMessageBox.warning(self, "Error", "No favorite selected")
            return
        
        index = self.favorites_list.currentRow()
        if index < 0 or index >= len(self.favorites):
            return
        
        # Ask for confirmation
        reply = QMessageBox.question(
            self, "Remove Favorite", 
            f"Are you sure you want to remove '{self.favorites[index]['name']}' from favorites?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.remove_from_favorites.emit(index)
