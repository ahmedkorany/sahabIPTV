"""
Custom dialog widgets for the application
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QLineEdit, QPushButton, QProgressBar, QMessageBox,
                            QCheckBox, QFileDialog)
from PyQt5.QtCore import Qt, pyqtSignal

class LoginDialog(QDialog):
    """Dialog for entering IPTV server credentials"""
    
    def __init__(self, parent=None, server="", username="", password="", remember=True):
        super().__init__(parent)
        self.setWindowTitle("Connect to IPTV Server")
        self.setMinimumWidth(400)
        
        self.setup_ui(server, username, password, remember)
    
    def setup_ui(self, server, username, password, remember):
        """Set up the UI components"""
        layout = QVBoxLayout(self)
        
        # Server URL
        server_layout = QHBoxLayout()
        server_label = QLabel("Server URL:")
        self.server_input = QLineEdit(server)
        self.server_input.setPlaceholderText("http://example.com")
        server_layout.addWidget(server_label)
        server_layout.addWidget(self.server_input)
        
        # Username
        username_layout = QHBoxLayout()
        username_label = QLabel("Username:")
        self.username_input = QLineEdit(username)
        username_layout.addWidget(username_label)
        username_layout.addWidget(self.username_input)
        
        # Password
        password_layout = QHBoxLayout()
        password_label = QLabel("Password:")
        self.password_input = QLineEdit(password)
        self.password_input.setEchoMode(QLineEdit.Password)
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_input)
        
        # Remember checkbox
        self.remember_checkbox = QCheckBox("Remember credentials")
        self.remember_checkbox.setChecked(remember)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.connect_button)
        buttons_layout.addWidget(self.cancel_button)
        
        # Add all layouts to main layout
        layout.addLayout(server_layout)
        layout.addLayout(username_layout)
        layout.addLayout(password_layout)
        layout.addWidget(self.remember_checkbox)
        layout.addLayout(buttons_layout)
    
    def get_credentials(self):
        """Get the entered credentials"""
        return {
            'server': self.server_input.text(),
            'username': self.username_input.text(),
            'password': self.password_input.text(),
            'remember': self.remember_checkbox.isChecked()
        }


class ProgressDialog(QDialog):
    """Dialog for showing progress of operations like downloads"""
    cancelled = pyqtSignal()
    
    def __init__(self, parent=None, title="Progress", text="Please wait..."):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.CustomizeWindowHint)
        
        self.setup_ui(text)
    
    def setup_ui(self, text):
        """Set up the UI components"""
        layout = QVBoxLayout(self)
        
        self.text_label = QLabel(text)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel)
        
        layout.addWidget(self.text_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.cancel_button, alignment=Qt.AlignRight)
    
    def set_progress(self, value):
        """Set the progress bar value"""
        self.progress_bar.setValue(value)
    
    def set_text(self, text):
        """Set the dialog text"""
        self.text_label.setText(text)
    
    def cancel(self):
        """Emit the cancelled signal"""
        self.cancelled.emit()
