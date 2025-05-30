from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton
from src.utils.helpers import apply_dark_theme, get_translations

class AccountEditDialog(QDialog):
    """Dialog for adding or editing an account (not for login)"""
    def __init__(self, parent=None, name="", server="", username="", password="", is_edit=False):
        super().__init__(parent)
        # Get translations from parent or default to empty dict
        self.translations = getattr(parent, 'translations', {}) if parent else {}
        self.setWindowTitle(self.translations.get("Edit Account", "Edit Account") if is_edit else self.translations.get("Add Account", "Add Account"))
        self.setMinimumWidth(400)
        self.is_edit = is_edit
        self.setup_ui(name, server, username, password)

    def setup_ui(self, name, server, username, password):
        layout = QVBoxLayout(self)

        # Account Name
        name_layout = QHBoxLayout()
        name_label = QLabel(self.translations.get("Account Name", "Account Name:"))
        self.name_input = QLineEdit(name)
        self.name_input.setPlaceholderText(self.translations.get("e.g. My IPTV Account", "e.g. My IPTV Account"))
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)

        # Server URL
        server_layout = QHBoxLayout()
        server_label = QLabel(self.translations.get("Server URL", "Server URL:"))
        self.server_input = QLineEdit(server)
        self.server_input.setPlaceholderText(self.translations.get("http://example.com", "http://example.com"))
        server_layout.addWidget(server_label)
        server_layout.addWidget(self.server_input)

        # Username
        username_layout = QHBoxLayout()
        username_label = QLabel(self.translations.get("Username", "Username:"))
        self.username_input = QLineEdit(username)
        username_layout.addWidget(username_label)
        username_layout.addWidget(self.username_input)

        # Password
        password_layout = QHBoxLayout()
        password_label = QLabel(self.translations.get("Password", "Password:"))
        self.password_input = QLineEdit(password)
        self.password_input.setEchoMode(QLineEdit.Password)
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_input)

        # Buttons
        buttons_layout = QHBoxLayout()
        self.save_button = QPushButton(self.translations.get("Save", "Save"))
        self.save_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton(self.translations.get("Cancel", "Cancel"))
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
