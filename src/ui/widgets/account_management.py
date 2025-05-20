from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem, QLineEdit, QMessageBox
from PyQt5.QtCore import Qt

class AccountManagementScreen(QWidget):
    def __init__(self, main_window, accounts, current_account):
        super().__init__()
        self.main_window = main_window
        self.accounts = accounts
        self.current_account = current_account
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        title = QLabel("Account Management")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        layout.addWidget(title, alignment=Qt.AlignCenter)

        # Back button
        back_btn = QPushButton("← Back")
        back_btn.setFixedWidth(80)
        back_btn.clicked.connect(self.go_back)
        layout.addWidget(back_btn, alignment=Qt.AlignLeft)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(lambda _: self.switch_account())
        self.refresh_list()
        layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add Account")
        self.edit_btn = QPushButton("Edit Account")
        self.delete_btn = QPushButton("Delete Account")
        self.switch_btn = QPushButton("Switch Account")
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.switch_btn)
        layout.addLayout(btn_layout)

        self.add_btn.clicked.connect(self.add_account)
        self.edit_btn.clicked.connect(self.edit_account)
        self.delete_btn.clicked.connect(self.delete_account)
        self.switch_btn.clicked.connect(self.switch_account)

    def refresh_list(self):
        self.list_widget.clear()
        for name in self.accounts:
            item = QListWidgetItem(name)
            # Remove custom background/text color for selected item, use system default
            self.list_widget.addItem(item)

    def add_account(self):
        self.main_window.show_login_dialog(account_switch=True)
        self.accounts = self.main_window.accounts
        self.current_account = self.main_window.current_account
        self.refresh_list()

    def edit_account(self):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.warning(self, "Edit Account", "Select an account to edit.")
            return
        name = item.text()
        self.main_window.edit_account(name, self.accounts[name])
        self.accounts = self.main_window.accounts
        self.current_account = self.main_window.current_account
        self.refresh_list()

    def delete_account(self):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.warning(self, "Delete Account", "Select an account to delete.")
            return
        name = item.text()
        if name == self.current_account:
            QMessageBox.warning(self, "Delete Account", "Cannot delete the currently active account.")
            return
        reply = QMessageBox.question(self, "Delete Account", f"Delete account '{name}'?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.accounts.pop(name)
            self.main_window.accounts = self.accounts
            self.main_window.settings.setValue("accounts", self.accounts)
            self.refresh_list()

    def switch_account(self):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.warning(self, "Switch Account", "Select an account to switch to.")
            return
        name = item.text()
        if name == self.current_account:
            QMessageBox.information(self, "Switch Account", "Already using this account.")
            return
        acc = self.accounts[name]
        self.main_window.api_client.set_credentials(acc['server'], acc['username'], acc['password'])
        success, _ = self.main_window.api_client.authenticate()
        if success:
            self.main_window.current_account = name
            self.main_window.settings.setValue("current_account", name)
            self.main_window.connect_to_server(acc['server'], acc['username'], acc['password'])
            self.main_window.update_account_label()
            # Dismiss the dialog after successful switch
            parent_dialog = self.parent()
            while parent_dialog and not hasattr(parent_dialog, 'accept'):
                parent_dialog = parent_dialog.parent()
            if parent_dialog and hasattr(parent_dialog, 'accept'):
                parent_dialog.accept()
        else:
            QMessageBox.warning(self, "Switch Account", "Authentication failed. Please check credentials.")
        self.accounts = self.main_window.accounts
        self.current_account = self.main_window.current_account
        self.refresh_list()

    def go_back(self):
        if hasattr(self.main_window, 'show_home_screen'):
            self.main_window.show_home_screen()
