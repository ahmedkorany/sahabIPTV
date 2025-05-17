from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PyQt5.QtCore import Qt

class AccountEditDialog(QDialog):
    """Dialog for adding or editing an account (not for login)"""
    def __init__(self, parent=None, name="", server="", username="", password="", is_edit=False):
        super().__init__(parent)
        self.setWindowTitle("Edit Account" if is_edit else "Add Account")
        self.setMinimumWidth(400)
        self.is_edit = is_edit
        self.setup_ui(name, server, username, password)

    def setup_ui(self, name, server, username, password):
        layout = QVBoxLayout(self)

        # Account Name
        name_layout = QHBoxLayout()
        name_label = QLabel("Account Name:")
        self.name_input = QLineEdit(name)
        self.name_input.setPlaceholderText("e.g. My IPTV Account")
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)

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

        # Buttons
        buttons_layout = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.save_button)
        buttons_layout.addWidget(self.cancel_button)

        # Add all layouts to main layout
        layout.addLayout(name_layout)
        layout.addLayout(server_layout)
        layout.addLayout(username_layout)
        layout.addLayout(password_layout)
        layout.addLayout(buttons_layout)

    def get_account_data(self):
        return {
            'name': self.name_input.text(),
            'server': self.server_input.text(),
            'username': self.username_input.text(),
            'password': self.password_input.text()
        }
