"""
Downloads tab for the application
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                            QTableWidgetItem, QPushButton, QProgressBar,
                            QHeaderView, QLabel, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal

class DownloadsTab(QWidget):
    """Downloads tracking tab widget"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.downloads = []  # List of download items
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the UI components"""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Downloads"))
        
        clear_completed_button = QPushButton("Clear Completed")
        clear_completed_button.clicked.connect(self.clear_completed_downloads)
        header_layout.addWidget(clear_completed_button)
        
        # Downloads table
        self.downloads_table = QTableWidget()
        self.downloads_table.setColumnCount(6)
        self.downloads_table.setHorizontalHeaderLabels(["Name", "Progress", "Status", "Speed", "ETA", "Actions"])
        self.downloads_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.downloads_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.downloads_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.downloads_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.downloads_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.downloads_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        
        # Add components to layout
        layout.addLayout(header_layout)
        layout.addWidget(self.downloads_table)
    
    def add_download(self, download_item):
        """Add a new download to the tracking list"""
        self.downloads.append(download_item)
        self.update_downloads_table()
    
    def update_download_item(self, download_item):
        """Update a specific download item in the table"""
        for i, download in enumerate(self.downloads):
            if download is download_item:
                self.update_table_row(i)
                break
    
    def update_downloads_table(self):
        """Update the downloads table with current downloads"""
        self.downloads_table.setRowCount(len(self.downloads))
        
        for row in range(len(self.downloads)):
            self.update_table_row(row)
    
    def update_table_row(self, row):
        """Update a specific row in the table"""
        if row < 0 or row >= len(self.downloads):
            return
        
        download = self.downloads[row]
        
        # Name
        name_item = QTableWidgetItem(download.name)
        self.downloads_table.setItem(row, 0, name_item)
        
        # Progress
        progress_bar = QProgressBar()
        progress_bar.setValue(download.progress)
        progress_bar.setTextVisible(True)
        self.downloads_table.setCellWidget(row, 1, progress_bar)
        
        # Status
        status_item = QTableWidgetItem(download.status)
        self.downloads_table.setItem(row, 2, status_item)
        
        # Speed
        speed_item = QTableWidgetItem(download.get_formatted_speed())
        self.downloads_table.setItem(row, 3, speed_item)
        
        # ETA
        eta_item = QTableWidgetItem(download.get_formatted_time())
        self.downloads_table.setItem(row, 4, eta_item)
        
        # Actions
        actions_widget = QWidget()
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        
        # Different buttons based on status
        if download.status == 'active':
            pause_button = QPushButton("Pause")
            pause_button.clicked.connect(lambda _, idx=row: self.pause_download(idx))
            actions_layout.addWidget(pause_button)
            
            cancel_button = QPushButton("Cancel")
            cancel_button.clicked.connect(lambda _, idx=row: self.cancel_download(idx))
            actions_layout.addWidget(cancel_button)
            
        elif download.status == 'paused':
            resume_button = QPushButton("Resume")
            resume_button.clicked.connect(lambda _, idx=row: self.resume_download(idx))
            actions_layout.addWidget(resume_button)
            
            cancel_button = QPushButton("Cancel")
            cancel_button.clicked.connect(lambda _, idx=row: self.cancel_download(idx))
            actions_layout.addWidget(cancel_button)
            
        elif download.status in ['completed', 'error', 'cancelled']:
            delete_button = QPushButton("Remove")
            delete_button.clicked.connect(lambda _, idx=row: self.remove_download(idx))
            actions_layout.addWidget(delete_button)
        
        self.downloads_table.setCellWidget(row, 5, actions_widget)
    
    def pause_download(self, index):
        """Pause a download"""
        if 0 <= index < len(self.downloads):
            self.downloads[index].pause()
            self.update_table_row(index)
    
    def resume_download(self, index):
        """Resume a download"""
        if 0 <= index < len(self.downloads):
            self.downloads[index].resume()
            self.update_table_row(index)
    
    def cancel_download(self, index):
        """Cancel a download"""
        if 0 <= index < len(self.downloads):
            reply = QMessageBox.question(
                self, "Cancel Download", 
                f"Are you sure you want to cancel '{self.downloads[index].name}'?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.downloads[index].cancel()
                self.update_table_row(index)
    
    def remove_download(self, index):
        """Remove a download from the list"""
        if 0 <= index < len(self.downloads):
            reply = QMessageBox.question(
                self, "Remove Download", 
                f"Are you sure you want to remove '{self.downloads[index].name}' from the list?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                del self.downloads[index]
                self.update_downloads_table()
    
    def clear_completed_downloads(self):
        """Clear all completed downloads from the list"""
        if not self.downloads:
            return
        
        reply = QMessageBox.question(
            self, "Clear Completed Downloads", 
            "Are you sure you want to clear all completed downloads?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.downloads = [d for d in self.downloads if d.status not in ['completed', 'error', 'cancelled']]
            self.update_downloads_table()
