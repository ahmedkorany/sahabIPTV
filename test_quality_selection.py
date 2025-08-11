#!/usr/bin/env python3
"""
Simple test script to verify quality selection functionality
"""
import sys
import os
sys.path.insert(0, '/Users/ahmedkorany/Work/IPTV/sahabIPTV/src')

from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget
from PyQt5.QtCore import QObject

# Mock API client for testing
class MockAPIClient:
    def get_series_url(self, episode_id, container_extension):
        # Return a sample HLS URL for testing
        return "https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_ts/master.m3u8"

# Mock translations
mock_translations = {
    "Select Quality": "Select Quality",
    "Choose video quality for export:": "Choose video quality for export:",
    "Quality": "Quality",
    "Resolution": "Resolution", 
    "Bandwidth": "Bandwidth",
    "Auto (Best Available)": "Auto (Best Available)",
    "Export with Selected Quality": "Export with Selected Quality",
    "Cancel": "Cancel",
    "Detecting available qualities...": "Detecting available qualities...",
    "Server does not support multiple qualities": "Server does not support multiple qualities",
    "Quality detection failed": "Quality detection failed",
    "High": "High",
    "Medium": "Medium",
    "Low": "Low",
    "Unknown": "Unknown",
    "qualities found": "qualities found"
}

class MockTranslations:
    def get(self, key, default=None):
        return mock_translations.get(key, default or key)

def test_quality_dialog():
    """Test the quality selection dialog"""
    app = QApplication(sys.argv)
    
    # Import after QApplication is created
    from ui.widgets.quality_selection_dialog import QualitySelectionDialog
    
    # Mock episode data
    episode_data = {
        'id': '12345',
        'title': 'Test Episode',
        'container_extension': 'mp4'
    }
    
    # Create mock objects
    api_client = MockAPIClient()
    translations = MockTranslations()
    
    # Create main window for testing
    main_window = QMainWindow()
    main_window.setWindowTitle("Quality Selection Test")
    main_window.setGeometry(100, 100, 300, 200)
    
    # Create test button
    central_widget = QWidget()
    layout = QVBoxLayout(central_widget)
    
    test_button = QPushButton("Test Quality Selection")
    
    def show_quality_dialog():
        dialog = QualitySelectionDialog(episode_data, api_client, translations, main_window)
        result = dialog.exec()
        if result:
            quality = dialog.get_selected_quality()
            print(f"Selected quality: {quality}")
        else:
            print("Dialog cancelled")
    
    test_button.clicked.connect(show_quality_dialog)
    layout.addWidget(test_button)
    
    main_window.setCentralWidget(central_widget)
    main_window.show()
    
    return app.exec()

if __name__ == "__main__":
    test_quality_dialog()