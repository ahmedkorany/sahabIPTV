"""
Main application window
"""
from PyQt5.QtWidgets import (QMainWindow, QTabWidget, QMessageBox, 
                            QAction, QMenu, QStatusBar, QLabel,
                            QProgressDialog)
from PyQt5.QtCore import Qt, QSettings, pyqtSignal, QObject, QThread
from PyQt5.QtSvg import QSvgWidget
from src.api.xtream import XtreamClient
from src.ui.tabs.live_tab import LiveTab
from src.ui.tabs.movies_tab import MoviesTab
from src.ui.tabs.series_tab import SeriesTab
from src.ui.tabs.search_tab import SearchTab
from src.ui.tabs.offline_tab import OfflineTab
from src.utils.offline_manager import OfflineManager
import src.config as app_config
from src.ui.widgets.notifications import NotificationPopup # Added

from src.utils.helpers import get_translations
from src.utils.favorites_manager import FavoritesManager
from src.config import DEFAULT_LANGUAGE, WINDOW_SIZE
from src.ui.widgets.home_screen import HomeScreenWidget
from src.ui.player import PlayerWindow

class CachePopulationThread(QThread):
    progress_updated = pyqtSignal(int, int, str, bool)  # current_step, total_steps, message, is_error
    population_finished = pyqtSignal(bool, str) # success, message

    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api_client = api_client

    def run(self):
        try:
            success, message = self.api_client.populate_full_cache(self.progress_callback)
            self.population_finished.emit(success, message)
        except Exception as e:
            self.population_finished.emit(False, f"Error during cache population: {str(e)}")

    def progress_callback(self, current_step, total_steps, message, is_error):
        self.progress_updated.emit(current_step, total_steps, message, is_error)

class LoadingIconController(QObject):
    show_icon = pyqtSignal()
    hide_icon = pyqtSignal()

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.show_icon.connect(self._show)
        self.hide_icon.connect(self._hide)

    def _show(self):
        if hasattr(self.main_window, 'statusBar') and hasattr(self.main_window, 'loading_icon_label'):
            if not self.main_window.loading_icon_label.isVisible():
                self.main_window.statusBar.addPermanentWidget(self.main_window.loading_icon_label)
                self.main_window.loading_icon_label.setVisible(True)
            self.main_window.statusBar.showMessage("Loading images...")

    def _hide(self):
        if hasattr(self.main_window, 'statusBar') and hasattr(self.main_window, 'loading_icon_label'):
            self.main_window.statusBar.clearMessage()
            self.main_window.statusBar.removeWidget(self.main_window.loading_icon_label)
            self.main_window.loading_icon_label.setVisible(False)

class MainWindow(QMainWindow):
    """Main application window"""
    favorites_changed = pyqtSignal()
    play_offline_media_requested = pyqtSignal(str, object) # Added: filepath, movie_meta
    
    def __init__(self):
        super().__init__()
        self.api_client = XtreamClient()
        self.settings = QSettings()
        self.language = self.settings.value("language", DEFAULT_LANGUAGE)
        self.translations = get_translations(self.language)
        self.accounts = self.settings.value("accounts", {}, type=dict)
        self.current_account = self.settings.value("current_account", "", type=str)
        self._active_notifications = [] # Added

        # Initialize OfflineManager
        # It needs config for paths. Assuming app_config (imported src.config) is suitable.
        self.offline_manager = OfflineManager(config=app_config, parent=self)
        if hasattr(self, 'offline_manager') and self.offline_manager: # Connect signals
            self.offline_manager.completion_signal.connect(self._notify_download_complete)
            self.offline_manager.error_signal.connect(self._notify_download_error)

        # Initialize favorites manager
        self.favorites_manager = FavoritesManager(self.current_account)
        self.favorites_manager.favorites_changed.connect(self.favorites_changed.emit)
        
        self.player_window = PlayerWindow(favorites_manager=self.favorites_manager)  # Persistent player window
        self.player_window.add_to_favorites.connect(self.add_to_favorites)  # Connect player window favorites signal
        self.expiry_str = ""
        self.cache_thread = None
        self.progress_dialog = None

        self.setup_ui()  # Only call setup_ui here
        auto_login_success = False
        if self.current_account and self.current_account in self.accounts:
            acc = self.accounts[self.current_account]
            server, username, password = acc.get('server', ''), acc.get('username', ''), acc.get('password', '')
            if server and username and password:
                self.api_client.set_credentials(server, username, password)
                success, _ = self.api_client.authenticate()
                if success:
                    self.connect_to_server(server, username, password)
                    auto_login_success = True
        if not auto_login_success:
            self.show_account_switch_dialog()

    def setup_ui(self):
        """Set up the UI components"""
        self.setWindowTitle(self.translations.get("Sahab Xtream IPTV", "Sahab Xtream IPTV"))
        self.resize(*WINDOW_SIZE)

        # --- HOME SCREEN ---
        self.home_screen = HomeScreenWidget(
            parent=self,
            on_tile_clicked=self.handle_home_tile_clicked,
            user_info={'username': self.current_account or ''},
            expiry_date=self.expiry_str
        )
        self.home_screen.reload_requested.connect(self.handle_reload_requested)

        # --- Prepare tabs ---
        self.tabs = QTabWidget()
        self.tabs.addTab(self.home_screen, self.translations.get("Home", "Home"))
        self.live_tab = LiveTab(self.api_client, self.favorites_manager, parent=self)
        # Pass offline_manager and main_window to MoviesTab
        self.movies_tab = MoviesTab(self.api_client, self.favorites_manager, offline_manager=self.offline_manager, main_window=self, parent=self)
        self.series_tab = SeriesTab(self.api_client, self.favorites_manager, main_window=self)
        self.search_tab = SearchTab(self.api_client, main_window=self) # Added SearchTab instance


        self.live_tab.add_to_favorites.connect(self.add_to_favorites)
        self.movies_tab.add_to_favorites.connect(self.add_to_favorites)
        self.series_tab.add_to_favorites.connect(self.add_to_favorites)
        # Connect SearchTab signals for item clicks
        self.search_tab.movie_selected.connect(self.show_movie_details_from_search)
        self.search_tab.series_selected.connect(self.show_series_details_from_search)
        self.search_tab.channel_selected.connect(self.play_channel_from_search)

        self.tabs.addTab(self.live_tab, self.translations.get("Live TV", "Live TV"))
        self.tabs.addTab(self.movies_tab, self.translations.get("Movies", "Movies"))
        self.tabs.addTab(self.series_tab, self.translations.get("Series", "Series"))
        self.tabs.addTab(self.search_tab, self.translations.get("Search", "Search"))

        # Offline Tab
        self.offline_tab = OfflineTab(self.offline_manager, self)
        self.tabs.addTab(self.offline_tab, self.translations.get_translation("Offline", "Offline"))
        self.offline_tab.offline_play_requested.connect(self._handle_offline_play_request)


        self.live_tab.set_main_window(self)
        # self.movies_tab.main_window is already set in its constructor if main_window param is used
        self.series_tab.main_window = self # Passed to SeriesDetailsWidget
        self.search_tab.main_window = self
        # self.offline_tab.main_window is self, already set

        
        # Connect favorites changed signal to update favorites tab

        self.setCentralWidget(self.tabs)

        # Connect tab change to handler
        self.tabs.currentChanged.connect(self.on_tab_changed)

        # Create menu bar
        self.create_menu_bar()
        
        # Apply language settings including RTL layout
        self.apply_language()

        # Create status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage(self.translations.get("Ready", "Ready"))
        self.account_label = QLabel()
        self.expiry_label = QLabel()
        self.statusBar.addPermanentWidget(self.account_label)
        self.statusBar.addPermanentWidget(self.expiry_label)
        self.update_account_label()
        # Add loading icon label and loading counter for image loading
        self.loading_icon_label = QSvgWidget('assets/infinite-spinner.svg')
        self.loading_icon_label.setFixedSize(24, 24)  # Adjust size as needed for status bar
        self.loading_icon_label.setVisible(False)
        self.statusBar.addPermanentWidget(self.loading_icon_label, 1)
        self.loading_counter = {'count': 0}
        self.loading_icon_controller = LoadingIconController(self)

    def show_series_details_from_search(self, series_data):
        """Switches to Series tab and shows details for a series from search results."""
        if hasattr(self, 'series_tab') and self.series_tab:
            self.tabs.setCurrentWidget(self.series_tab)
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(0, lambda: self.series_tab.show_series_details_by_data(series_data))
        else:
            QMessageBox.warning(self, "Navigation Error", "Series tab is not available.")

    def show_movie_details_from_search(self, movie_data):
        """Switches to Movies tab and shows details for a movie from search results."""
        if hasattr(self, 'movies_tab') and self.movies_tab:
            self.tabs.setCurrentWidget(self.movies_tab)
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(0, lambda: self.movies_tab.show_movie_details_by_data(movie_data))
        else:
            QMessageBox.warning(self, "Navigation Error", "Movies tab is not available.")

    def play_channel_from_search(self, channel_data):
        """Switches to Live TV tab and plays the selected channel."""
        if hasattr(self, 'live_tab') and self.live_tab:
            # Optional: switch to live tab
            # self.tabs.setCurrentWidget(self.live_tab)
            self.live_tab.play_channel_by_data(channel_data)
        else:
            QMessageBox.warning(self, "Navigation Error", "Live TV tab is not available.")


    def on_tab_changed(self, index):
        current_widget = self.tabs.widget(index)
        if current_widget == self.home_screen:
            self.home_screen.update_expiry_date(self.expiry_str)
        elif current_widget == self.series_tab and hasattr(self.series_tab, 'tab_selected'):
            self.series_tab.tab_selected()
        elif current_widget == self.search_tab and hasattr(self.search_tab, 'refresh_search'):
            # self.search_tab.refresh_search() # Optionally refresh search or clear
            pass # Search tab handles its state internally mostly

    def handle_home_tile_clicked(self, key):
        # Switch to the appropriate tab when a tile is clicked
        # Home: 0, Live: 1, Movies: 2, Series: 3, Search: 4 (new)
        tab_map = {'live': 1, 'movies': 2, 'series': 3, 'search': 4}
        if key in tab_map:
            self.tabs.setCurrentIndex(tab_map[key])
            if key == 'search' and hasattr(self, 'search_tab'):
                self.search_tab.search_input.setFocus() # Focus search input
        elif key == 'settings': # Assuming 'settings' key for account management
            self.show_account_management_screen()

    def create_menu_bar(self):
        """Create the menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        connect_action = QAction("Connect / Re-login", self)
        connect_action.triggered.connect(self.show_account_switch_dialog)
        file_menu.addAction(connect_action)
        
        edit_account_action = QAction("Edit Current Account", self)
        edit_account_action.triggered.connect(self.edit_current_account)
        file_menu.addAction(edit_account_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Settings menu
        settings_menu = menubar.addMenu("Settings")
        
        language_menu = QMenu("Language", self)
        
        english_action = QAction("English", self)
        english_action.setCheckable(True)
        english_action.setChecked(self.language == "en")
        english_action.triggered.connect(lambda: self.change_language("en"))
        
        arabic_action = QAction("العربية", self)
        arabic_action.setCheckable(True)
        arabic_action.setChecked(self.language == "ar")
        arabic_action.triggered.connect(lambda: self.change_language("ar"))
        
        language_menu.addAction(english_action)
        language_menu.addAction(arabic_action)
        
        settings_menu.addMenu(language_menu)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

        # Add Home action to menu bar for returning to home screen
        home_action = QAction("Home", self)
        home_action.setShortcut("Ctrl+H")
        home_action.triggered.connect(self.show_home_screen)
        menubar.addAction(home_action)
    
    def start_full_cache_population(self, force_reload=False):
        if not self.api_client or not self.api_client.server_url:
            self.show_status_message("API client not configured. Cannot populate cache.")
            return

        if self.cache_thread and self.cache_thread.isRunning():
            self.show_status_message("Cache population is already in progress.")
            return

        if force_reload:
            self.api_client.invalidate_cache()
            print("[CACHE] Full cache invalidated due to forced reload.")

        self.progress_dialog = QProgressDialog("Populating cache...", "Cancel", 0, 100, self)
        self.progress_dialog.setWindowTitle(self.translations.get("Caching Data", "Caching Data"))
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setAutoClose(False) # We will close it manually
        self.progress_dialog.setAutoReset(False) # We will reset it manually
        self.progress_dialog.setValue(0)
        self.progress_dialog.show()

        self.cache_thread = CachePopulationThread(self.api_client)
        self.cache_thread.progress_updated.connect(self.update_progress_dialog)
        self.cache_thread.population_finished.connect(self.on_cache_population_finished)
        self.cache_thread.start()

    def update_progress_dialog(self, current_step, total_steps, message, is_error):
        dlg = self.progress_dialog
        if not dlg:
            return
        if total_steps > 0:
            dlg.setMaximum(total_steps)
            dlg.setValue(current_step)
        else:
            dlg.setMaximum(0)
            dlg.setValue(0)
        dlg.setLabelText(message)
        if dlg.wasCanceled():
            if self.cache_thread and self.cache_thread.isRunning():
                self.cache_thread.requestInterruption()
                print("[CACHE POPULATE] Cache population canceled by user.")
                # self.on_cache_population_finished(False, "Cache population canceled.")
    
    def on_cache_population_finished(self, success, message):
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        # Always reload favorites from file after cache population to ensure they persist
        self.load_favorites()
        if success:
            self.show_status_message("Full cache population completed successfully.")
            self.reload_tab_categories()
            self.home_screen.update_expiry_date(self.expiry_str)
        else:
            self.show_status_message(f"Cache population failed: {message}")
        self.cache_thread = None # Allow re-creation

    def reload_tab_categories(self):
        """Reloads categories in all relevant tabs."""
        if hasattr(self, 'live_tab') and self.live_tab:
            self.live_tab.load_categories()
        if hasattr(self, 'movies_tab') and self.movies_tab:
            self.movies_tab.load_categories()
        if hasattr(self, 'series_tab') and self.series_tab:
            self.series_tab.load_categories()
        print("[UI] Tab categories reloaded after cache population.")

    def handle_reload_requested(self):
        """Handles the reload request from the home screen."""
        if self.api_client and self.api_client.server_url:
            self.start_full_cache_population(force_reload=True)
            self.show_status_message("Cache cleared and data refresh initiated.")
        else:
            self.show_status_message("API client not available or not configured. Cannot reload data.")

    def show_account_management_screen(self):
        from src.ui.widgets.account_management import AccountManagementScreen
        from PyQt5.QtWidgets import QDialog, QVBoxLayout
        dialog = QDialog(self)
        dialog.setWindowTitle(self.translations.get("Account Management", "Account Management"))
        dialog.setMinimumWidth(500)
        layout = QVBoxLayout(dialog)
        screen = AccountManagementScreen(self, self.accounts, self.current_account)
        layout.addWidget(screen)
        dialog.setLayout(layout)
        dialog.exec_()

    def show_account_switch_dialog(self):
        self.show_account_management_screen()

    def show_login_dialog(self, account_switch=False, prefill=None, is_add_mode=False):
        # Get saved credentials or prefill
        if prefill:
            server = prefill.get('server', '')
            username = prefill.get('username', '')
            password = prefill.get('password', '')
            remember = True # In edit mode, 'remember' is implicitly true for existing data
            account_name = prefill.get('account_name', self.current_account or "")
        else: # This is typically for add mode or initial login
            server = self.settings.value("server", "")
            username = self.settings.value("username", "")
            password = self.settings.value("password", "")
            remember = self.settings.value("remember_credentials", True, type=bool)
            account_name = "" # Start with empty name for add mode

        from src.ui.widgets.dialogs import LoginDialog
        # Pass account_name and is_add_mode to LoginDialog constructor
        dialog = LoginDialog(self, account_name, server, username, password, remember, is_add_mode)

        if is_add_mode:
            dialog.setWindowTitle(self.translations.get("Add New Account", "Add New Account"))
            # Button text is already handled by LoginDialog's new __init__ and setup_ui
        else:
            dialog.setWindowTitle(f"Edit Account: {account_name}")
            # Button text is already handled by LoginDialog's new __init__ and setup_ui

        if dialog.exec_():
            credentials = dialog.get_credentials()
            new_account_name = credentials.get('account_name', '').strip()

            if not new_account_name:
                QMessageBox.warning(self, "Input Error", "Account name cannot be empty.")
                return # Or re-show dialog

            # Check for duplicate account name (only if it's a new name or add mode)
            if (is_add_mode and new_account_name in self.accounts) or \
               (not is_add_mode and new_account_name != account_name and new_account_name in self.accounts):
                QMessageBox.warning(self, "Input Error", f"An account with the name '{new_account_name}' already exists.")
                return # Or re-show dialog

            acc = {
                'server': credentials['server'],
                'username': credentials['username'],
                'password': credentials['password'],
                'account_name': new_account_name # Use the new name from dialog
            }

            # If editing and name changed, remove old entry
            if not is_add_mode and account_name and account_name != new_account_name and account_name in self.accounts:
                del self.accounts[account_name]
            
            self.accounts[new_account_name] = acc
            self.settings.setValue("accounts", self.accounts)

            if not is_add_mode: # Editing an existing account
                # Only switch and connect if account_switch is True
                if account_switch:
                    self.current_account = new_account_name
                    self.settings.setValue("current_account", new_account_name)
                    
                    if credentials['remember']:
                        self.settings.setValue("server", credentials['server'])
                        self.settings.setValue("username", credentials['username'])
                        self.settings.setValue("password", credentials['password'])
                        self.settings.setValue("remember_credentials", True)
                    else:
                        self.settings.remove("server")
                        self.settings.remove("username")
                        self.settings.remove("password")
                        self.settings.setValue("remember_credentials", False)
                    
                    self.connect_to_server(credentials['server'], credentials['username'], credentials['password'])
                    self.update_account_label()
                else:
                    # If not switching, just show a success message. 
                    # The current account remains unchanged.
                    self.show_status_message(f"Account '{new_account_name}' updated successfully.")
                    # We might need to update the account label if the *current* account's name changed,
                    # but not switch to the *edited* account if it wasn't the current one.
                    # If the edited account *was* the current one and its name changed, 
                    # current_account might be stale. Let's update it if the name changed.
                    if self.current_account == account_name and account_name != new_account_name:
                        # The current account was renamed, update self.current_account to the new name
                        # but don't trigger a full connect/switch if account_switch is False.
                        self.current_account = new_account_name
                        self.settings.setValue("current_account", self.current_account)
                    self.update_account_label() # Refresh label, might show old or new name based on current_account
            else:
                # In add mode, we just save and return to account management. No auto-switch.
                self.show_status_message(f"Account '{new_account_name}' added successfully.")
                # The account management screen should refresh itself or be re-shown

            # Refresh account management if it's open or re-trigger it
            # This part might need adjustment based on how AccountManagementScreen is structured
            # For now, assume it will be re-shown or refreshed by the caller

        else: # Dialog was cancelled
            # Only close the app if it's an initial login (account_switch=True)
            # AND it's NOT the "Add Account" dialog being cancelled (is_add_mode=False).
            # If is_add_mode is True, cancelling should just return to account management.
            if account_switch and not is_add_mode:
                self.close() # Close app if initial login is cancelled

    def clear_grids(self):
        # Clear Live grid
        if hasattr(self, 'live_tab') and hasattr(self.live_tab, 'channel_grid_layout'):
            layout = self.live_tab.channel_grid_layout
            if layout is not None and hasattr(layout, 'count'):
                try:
                    for i in reversed(range(layout.count())):
                        item = layout.itemAt(i)
                        if item is not None:
                            widget = item.widget()
                            if widget:
                                widget.setParent(None)
                except RuntimeError:
                    pass  # Layout was deleted
        # Clear Movies grid
        if hasattr(self, 'movies_tab') and hasattr(self.movies_tab, 'movie_grid_layout'):
            layout = self.movies_tab.movie_grid_layout
            if layout is not None and hasattr(layout, 'count'):
                try:
                    for i in reversed(range(layout.count())):
                        item = layout.itemAt(i)
                        if item is not None:
                            widget = item.widget()
                            if widget:
                                widget.setParent(None)
                except RuntimeError:
                    pass
        # Clear Series grid
        if hasattr(self, 'series_tab') and hasattr(self.series_tab, 'series_grid_layout'):
            layout = self.series_tab.series_grid_layout
            if layout is not None and hasattr(layout, 'count'):
                try:
                    for i in reversed(range(layout.count())):
                        item = layout.itemAt(i)
                        if item is not None:
                            widget = item.widget()
                            if widget:
                                widget.setParent(None)
                except RuntimeError:
                    pass

    def connect_to_server(self, server, username, password):
        self.statusBar.showMessage(self.translations.get("Connecting to server...", "Connecting to server..."))
        # Recreate all tabs and UI to avoid using deleted widgets
        # self.setup_ui()  # This will recreate tabs, home_screen, etc. - Let's see if this is still needed or if selective updates are better
        # self.load_favorites()  # Ensure favorites are loaded for the new tab instance
        self.api_client.set_credentials(server, username, password)
        success, data = self.api_client.authenticate()
        expiry_str = ""
        if success:
            self.statusBar.showMessage(self.translations.get("Connected successfully. Populating cache...", "Connected successfully. Populating cache..."))
            self.start_full_cache_population() # This will also reload tab categories upon completion
            
            # Get expiry date from user_info if available
            from PyQt5.QtCore import QTimer

            def update_expiry():
                if data and 'user_info' in data and 'exp_date' in data['user_info']:
                    import datetime
                    exp_ts = int(data['user_info']['exp_date'])
                    expiry = datetime.datetime.fromtimestamp(exp_ts)
                    self.expiry_str = expiry.strftime('%Y-%m-%d')
                    if hasattr(self, 'home_screen') and self.home_screen:
                        try:
                            self.home_screen.update_expiry_date(self.expiry_str)
                        except RuntimeError:
                            print("Warning: Attempted to update expiry date on a deleted HomeScreen instance.")
                    if hasattr(self, 'expiry_label') and self.expiry_label:
                        self.expiry_label.setText(f"Expiry: {self.expiry_str}")
                else:
                    if hasattr(self, 'expiry_label') and self.expiry_label:
                        self.expiry_label.setText("")

            QTimer.singleShot(100, update_expiry)
            self.update_account_label()
            self._load_account_data()
        else:
            self.statusBar.showMessage(self.translations.get("Connection failed", "Connection failed"))
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Connection Error", f"Failed to connect: {data}")
            self.show_login_dialog(account_switch=True)

    def load_favorites(self):
        """Load favorites from file for the current account"""
        self.favorites_manager.load_favorites()

    def save_favorites(self):
        """Save favorites to file, keyed by account"""
        self.favorites_manager.save_favorites()

    def add_to_favorites(self, item):
        """Add an item to favorites for the current account"""
        if self.favorites_manager.add_to_favorites(item):
            item_name = item.get('name', 'Item')
            self.statusBar.showMessage(f"'{item_name}' added to favorites.", 3000)
        else:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(self, "Favorites", "Already in favorites.")

    def remove_from_favorites(self, item_to_remove):
        """Remove an item from favorites for the current account.
        
        Args:
            item_to_remove: Can be an integer (index) or a dictionary (item data)
        """
        removed_item = None
        
        if isinstance(item_to_remove, int):
            # Remove by index
            favorites_list = self.favorites_manager.get_favorites()
            if 0 <= item_to_remove < len(favorites_list):
                removed_item = favorites_list[item_to_remove]
                self.favorites_manager.remove_from_favorites(removed_item)
        else:
            # Remove by matching item data
            if self.favorites_manager.remove_from_favorites(item_to_remove):
                removed_item = item_to_remove
        
        if removed_item:
            item_name = removed_item.get('name', 'Item')
            self.statusBar.showMessage(f"'{item_name}' removed from favorites.", 3000)
            self.favorites_changed.emit()
        else:
            item_name_to_remove = item_to_remove.get('name', 'Unknown item') if isinstance(item_to_remove, dict) else 'Item at invalid index'
            self.statusBar.showMessage(f"Could not remove '{item_name_to_remove}'. Item not found in favorites.", 3000)

    def is_favorite(self, item_to_check):
        """Check if an item is in favorites for the current account"""
        return self.favorites_manager.is_favorite(item_to_check)
    def switch_account(self, name):
        """Switch to a different account and reload all tab data without deleting/recreating widgets"""
        self.current_account = name
        self.settings.setValue("current_account", name)
        self.favorites_manager.set_current_account(name)
        # Reload categories/data in all tabs to reflect new account
        if hasattr(self, 'live_tab') and self.live_tab:
            self.live_tab.load_categories()
        if hasattr(self, 'movies_tab') and self.movies_tab:
            self.movies_tab.load_categories()
        if hasattr(self, 'series_tab') and self.series_tab:
            self.series_tab.load_categories()
        # Optionally, reload downloads or other per-account data here
        # Do NOT recreate or delete any widgets/tabs/main window

    def load_settings(self):
        """Load application settings"""
        self.language = self.settings.value("language", DEFAULT_LANGUAGE)
        self.translations = get_translations(self.language)
        
        # Apply language
        self.apply_language()
    
    def save_settings(self):
        """Save application settings"""
        self.settings.setValue("language", self.language)
    
    def change_language(self, language):
        """Change the application language"""
        if language != self.language:
            self.language = language
            self.translations = get_translations(language)
            self.apply_language()
            self.save_settings()
    
    def apply_language(self):
        """Apply language to UI elements"""
        # Set tab titles
        self.tabs.setTabText(0, self.translations.get("Home", "Home"))
        self.tabs.setTabText(1, self.translations.get("Live TV", "Live TV"))
        self.tabs.setTabText(2, self.translations.get("Movies", "Movies"))
        self.tabs.setTabText(3, self.translations.get("Series", "Series"))
        self.tabs.setTabText(4, self.translations.get("Search", "Search"))
        if self.tabs.count() > 5: # Check if Offline tab was added
            self.tabs.setTabText(5, self.translations.get_translation("Offline", "Offline"))
        
        # Update home screen translations
        if hasattr(self, 'home_screen') and self.home_screen:
            self.home_screen.update_translations(self.translations)
        
        # Set layout direction
        if self.language == "ar":
            self.setLayoutDirection(Qt.RightToLeft)
        else:
            self.setLayoutDirection(Qt.LeftToRight)
    
    def show_about_dialog(self):
        """Show the about dialog"""
        QMessageBox.about(
            self, "About Sahab IPTV",
            "Sahab IPTV Player\n\n"
            "A modern IPTV player for Xtream Codes API\n\n"
            "Features:\n"
            "- Live TV streaming\n"
            "- Movies and Series playback\n"
            "- Recording capability\n"
            "- Favorites management\n\n"
            "Version 2.0.0"
        )
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Save settings and favorites
        self.save_settings()
        self.save_favorites()
        event.accept()

    def edit_account(self, name, acc):
        # Ensure the account data being prefilled has the 'account_name' key
        # which show_login_dialog expects in prefill.
        # The 'acc' dictionary from self.accounts should already have this.
        if 'account_name' not in acc:
            acc['account_name'] = name # Ensure it's there for prefill

        # Call the centralized show_login_dialog for editing
        self.show_login_dialog(prefill=acc, is_add_mode=False, account_switch=False)
        # After show_login_dialog completes, the account management screen (if open)
        # or the main UI should reflect changes. If AccountManagementScreen is a dialog,
        # it might need to be closed and reopened or have a refresh mechanism.
        # For now, we assume show_login_dialog handles all necessary updates if successful.

    def edit_current_account(self):
        if self.current_account and self.current_account in self.accounts:
            self.edit_account(self.current_account, self.accounts[self.current_account])

    def update_account_label(self):
        if hasattr(self, 'account_label'):
            if self.current_account:
                user_info={'username': self.current_account or ''},
                self.home_screen.update_user_info(self.current_account)
                self.setWindowTitle(f"Sahab Xtream IPTV - {self.current_account}")
            else:
                self.account_label.setText("")
                self.setWindowTitle(self.translations.get("Sahab Xtream IPTV", "Sahab Xtream IPTV"))

    def _account_data_key(self, suffix):
        # Use a unique key for each account's data
        return f"{self.current_account}_{suffix}" if self.current_account else suffix

    def _load_account_data(self):
        # Load downloads for the current account (favorites are already loaded by load_favorites)
        # TODO: Implement per-account downloads loading if needed
        pass

    def show_home_screen(self):
        """Return to the home screen from any tab"""
        self.setCentralWidget(self.home_screen) # This might be problematic if tabs are the central widget.
        # A better approach for home might be to switch to the Home tab:
        # self.tabs.setCurrentIndex(0)


    def show_status_message(self, message, timeout=5000):
        if hasattr(self, 'statusBar') and self.statusBar:
            self.statusBar.showMessage(message, timeout)

    def _handle_offline_play_request(self, filepath, movie_meta):
        """Handles the request to play an offline file."""
        # Ensure os is imported if not already at the top of the file
        import os
        if not os.path.exists(filepath):
            QMessageBox.warning(self,
                                self.translations.get_translation("Playback Error", "Playback Error"),
                                self.translations.get_translation("Offline file not found: {}", "Offline file not found: {}").format(filepath))
            if hasattr(self, 'offline_manager') and movie_meta.get('stream_id'):
                # Use the existing error signal for consistency if appropriate,
                # or update status directly if the manager handles missing files that way.
                self.offline_manager.error_signal.emit(str(movie_meta.get('stream_id')), "Offline file missing")
            return

        self.player_window.play_media(
            media_source=filepath, # Corrected from url to media_source
            media_type='movie',
            metadata=movie_meta,
            is_offline=True
        )
        self.player_window.show()
        self.player_window.activateWindow()

    def show_app_notification(self, title, message, type='info', duration_ms=7000, action_callback=None):
        # Calculate position for the new notification
        # New notifications appear above older ones
        occupied_height = 0
        for notification in self._active_notifications:
            occupied_height += notification.height() + 5 # 5px spacing

        popup = NotificationPopup(title, message, type=type, parent=self, timeout=duration_ms, action_callback=action_callback)
        popup.destroyed.connect(self._remove_notification)

        # Position new notification based on how many are already active
        # This simple stacking places new ones above from bottom-right.
        # More sophisticated stacking might involve shifting existing ones.
        # For now, use a simple index for vertical offset.
        position_index = len(self._active_notifications)
        popup.show_popup(position_index=position_index)

        self._active_notifications.append(popup)

    def _remove_notification(self, obj):
        # obj is the QObject that was destroyed
        if obj in self._active_notifications:
            self._active_notifications.remove(obj)
        # Re-position remaining notifications if needed (optional, can be complex)
        # For simplicity, we don't reposition here; new ones will fill gaps or stack.

    def _notify_download_complete(self, movie_id):
        if not hasattr(self, 'offline_manager'): return
        meta = self.offline_manager.get_movie_meta(movie_id)
        if meta:
            movie_name = meta.get('title', meta.get('name', 'A movie')) # Use title or name

            def action():
                if hasattr(self, 'tabs') and hasattr(self, 'offline_tab'):
                    self.tabs.setCurrentWidget(self.offline_tab)
                    # Future: maybe select the item in offline_tab's list

            self.show_app_notification(
                self.translations.get_translation("Download Complete", "Download Complete"),
                self.translations.get_translation("'{movie_name}' is ready to watch offline.", "'{movie_name}' is ready to watch offline.").format(movie_name=movie_name),
                type='success',
                action_callback=action
            )

    def _notify_download_error(self, movie_id, error_msg):
        if not hasattr(self, 'offline_manager'): return

        # Filter out less critical error messages for notifications
        # For example, "paused" states due to network might not need an aggressive popup.
        # This depends on the exact error messages OfflineManager emits.
        # For now, let's check if the error_msg indicates a pause rather than a hard error.
        if "paused" in error_msg.lower(): # Simple check
            print(f"Download for {movie_id} paused, error: {error_msg}. Notification suppressed.")
            # Optionally show a less intrusive status bar message for pauses
            # self.show_status_message(f"Download for {movie_id} paused: {error_msg}", timeout=3000)
            return

        meta = self.offline_manager.get_movie_meta(movie_id)
        movie_name = "A download"
        if meta:
            movie_name = meta.get('title', meta.get('name', 'A download'))

        self.show_app_notification(
            self.translations.get_translation("Download Failed", "Download Failed"),
            self.translations.get_translation("Could not download '{movie_name}': {error_msg}", "Could not download '{movie_name}': {error_msg}").format(movie_name=movie_name, error_msg=error_msg),
            type='error'
        )
