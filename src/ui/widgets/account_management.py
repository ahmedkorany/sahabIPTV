from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem, QLineEdit, QMessageBox
from PyQt5.QtCore import Qt
from .account_edit_dialog import AccountEditDialog

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
        current_row = 0
        for idx, name in enumerate(self.accounts):
            item = QListWidgetItem(name)
            self.list_widget.addItem(item)
            if name == self.current_account:
                current_row = idx
        # Set the current account as selected
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(current_row)

    def add_account(self):
        dialog = AccountEditDialog(self, is_edit=False)
        while True:
            if dialog.exec_() == dialog.Accepted:
                data = dialog.get_account_data()
                name = data['name'].strip()
                if not name:
                    QMessageBox.warning(self, "Add Account", "Account name cannot be empty.")
                    continue
                if name in self.accounts:
                    QMessageBox.warning(self, "Add Account", "Account already exists.")
                    continue
                # Validate credentials before saving
                from src.api.xtream import XtreamClient
                client = XtreamClient()
                client.set_credentials(data['server'], data['username'], data['password'])
                success, error = client.authenticate()
                if not success:
                    QMessageBox.critical(self, "Add Account", f"Failed to connect: {error}")
                    # Reopen dialog with previous data for editing
                    dialog = AccountEditDialog(self, name=data['name'], server=data['server'], username=data['username'], password=data['password'], is_edit=False)
                    continue
                self.accounts[name] = {
                    'server': data['server'],
                    'username': data['username'],
                    'password': data['password']
                }
                self.main_window.accounts = self.accounts
                self.main_window.settings.setValue("accounts", self.accounts)
                self.refresh_list()
                break
            else:
                break

    def edit_account(self):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.warning(self, "Edit Account", "Select an account to edit.")
            return
        name = item.text()
        acc = self.accounts[name]
        dialog = AccountEditDialog(self, name=name, server=acc['server'], username=acc['username'], password=acc['password'], is_edit=True)
        if dialog.exec_() == dialog.Accepted:
            data = dialog.get_account_data()
            new_name = data['name'].strip()
            if not new_name:
                QMessageBox.warning(self, "Edit Account", "Account name cannot be empty.")
                return
            if new_name != name and new_name in self.accounts:
                QMessageBox.warning(self, "Edit Account", "Another account with this name already exists.")
                return
            self.accounts.pop(name)
            self.accounts[new_name] = {
                'server': data['server'],
                'username': data['username'],
                'password': data['password']
            }
            self.main_window.accounts = self.accounts
            self.main_window.settings.setValue("accounts", self.accounts)
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
        # Validate credentials before switching
        from src.api.xtream import XtreamClient
        client = XtreamClient()
        client.set_credentials(acc['server'], acc['username'], acc['password'])
        success, error = client.authenticate()
        if success:
            self.main_window.current_account = name
            self.main_window.settings.setValue("current_account", name)
            self.main_window.api_client.set_credentials(acc['server'], acc['username'], acc['password'])
            self.main_window.connect_to_server(acc['server'], acc['username'], acc['password'])
            self.main_window.update_account_label()
            QMessageBox.information(self, "Switch Account", f"Switched to account '{name}'.")
            self.accounts = self.main_window.accounts
            self.current_account = self.main_window.current_account
            self.refresh_list()
        else:
            QMessageBox.warning(self, "Switch Account", f"Authentication failed: {error}\nPlease check credentials.")
        # Do not switch if authentication fails

    def go_back(self):
        if hasattr(self.main_window, 'show_home_screen'):
            self.main_window.show_home_screen()
