from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QMessageBox, QHeaderView, QTableWidgetItem, QTableWidget, QProgressBar)

class DownloadsTab(QWidget):
    """Downloads tracking tab widget"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.downloads = []  # List of download items
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the UI components"""
        layout = QVBoxLayout(self)
        
        # Downloads list
        self.downloads_table = QTableWidget()
        self.downloads_table.setColumnCount(5)
        self.downloads_table.setHorizontalHeaderLabels(["Name", "Progress", "Status", "Actions", ""])
        self.downloads_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.downloads_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.downloads_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.downloads_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.downloads_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        
        layout.addWidget(self.downloads_table)
    
    def add_download(self, download_item):
        """Add a new download to the tracking list"""
        self.downloads.append(download_item)
        self.update_downloads_table()
    
    def update_progress(self, download_item, progress, downloaded_size=0, total_size=0):
        """Update the progress of a specific download"""
        for item in self.downloads:
            if item == download_item:
                item.update_progress(progress, downloaded_size, total_size)
                break
        self.update_downloads_table()

    def update_downloads_table(self):
        """Update the downloads table with current downloads"""
        self.downloads_table.setRowCount(len(self.downloads))
        
        for row, download in enumerate(self.downloads):
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
            
            # Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            
            if download.status == 'active':
                pause_button = QPushButton("Pause")
                pause_button.clicked.connect(lambda _, idx=row: self.pause_download(idx))
                actions_layout.addWidget(pause_button)
            elif download.status == 'paused':
                resume_button = QPushButton("Resume")
                resume_button.clicked.connect(lambda _, idx=row: self.resume_download(idx))
                actions_layout.addWidget(resume_button)
            
            self.downloads_table.setCellWidget(row, 3, actions_widget)
            
            # Delete button
            delete_widget = QWidget()
            delete_layout = QHBoxLayout(delete_widget)
            delete_layout.setContentsMargins(0, 0, 0, 0)
            
            delete_button = QPushButton("Delete")
            delete_button.clicked.connect(lambda _, idx=row: self.delete_download(idx))
            delete_layout.addWidget(delete_button)
            
            self.downloads_table.setCellWidget(row, 4, delete_widget)
    
    def pause_download(self, index):
        """Pause a download"""
        if 0 <= index < len(self.downloads):
            self.downloads[index].status = 'paused'
            self.update_downloads_table()
    
    def resume_download(self, index):
        """Resume a download"""
        if 0 <= index < len(self.downloads):
            self.downloads[index].status = 'active'
            self.update_downloads_table()
    
    def delete_download(self, index):
        """Delete a download"""
        if 0 <= index < len(self.downloads):
            # Ask for confirmation
            reply = QMessageBox.question(
                self, "Delete Download", 
                f"Are you sure you want to delete '{self.downloads[index].name}'?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                del self.downloads[index]
                self.update_downloads_table()
