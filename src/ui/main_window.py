"""
Main application window
"""
import os
from PyQt5.QtWidgets import (QMainWindow, QTabWidget, QMessageBox, 
                            QAction, QMenu, QMenuBar, QToolBar, QStatusBar, QLabel,
                            QProgressDialog) # Added QProgressDialog
from PyQt5.QtCore import Qt, QSettings, QSize, pyqtSignal, QObject, QThread # Added QThread
from PyQt5.QtGui import QIcon
from PyQt5.QtSvg import QSvgWidget
from src.api.xtream import XtreamClient
from src.ui.tabs.live_tab import LiveTab
from src.ui.tabs.movies_tab import MoviesTab
from src.ui.tabs.series_tab import SeriesTab
from src.ui.tabs.search_tab import SearchTab # Added SearchTab
from src.utils.helpers import load_json_file, save_json_file, get_translations
from src.config import FAVORITES_FILE, SETTINGS_FILE, DEFAULT_LANGUAGE, WINDOW_SIZE, ICON_SIZE
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
    
    def __init__(self):
        super().__init__()
        self.api_client = XtreamClient()
        self.favorites = []
        self.settings = QSettings()
        self.language = self.settings.value("language", DEFAULT_LANGUAGE)
        self.translations = get_translations(self.language)
        self.accounts = self.settings.value("accounts", {}, type=dict)
        self.current_account = self.settings.value("current_account", "", type=str)
        self.player_window = PlayerWindow()  # Persistent player window
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
        self.setWindowTitle("Sahab Xtream IPTV")
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
        self.live_tab = LiveTab(self.api_client, parent=self)
        self.movies_tab = MoviesTab(self.api_client, parent=self)
        self.series_tab = SeriesTab(self.api_client, main_window=self)
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
        self.tabs.addTab(self.search_tab, self.translations.get("Search", "Search")) # Added Search tab

        self.live_tab.main_window = self
        self.movies_tab.main_window = self
        self.series_tab.main_window = self
        self.search_tab.main_window = self # Set main_window for search_tab
        self.setCentralWidget(self.tabs)

        # Connect tab change to handler
        self.tabs.currentChanged.connect(self.on_tab_changed)

        # Create menu bar
        self.create_menu_bar()

        # Create status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")
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
        self.progress_dialog.setWindowTitle("Caching Data")
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
        dialog.setWindowTitle("Account Management")
        dialog.setMinimumWidth(500)
        layout = QVBoxLayout(dialog)
        screen = AccountManagementScreen(self, self.accounts, self.current_account)
        layout.addWidget(screen)
        dialog.setLayout(layout)
        dialog.exec_()

    def show_account_switch_dialog(self):
        self.show_account_management_screen()

    def show_login_dialog(self, account_switch=False, prefill=None):
        # Get saved credentials or prefill
        if prefill:
            server = prefill.get('server', '')
            username = prefill.get('username', '')
            password = prefill.get('password', '')
            remember = True
            account_name = prefill.get('account_name', self.current_account or "")
        else:
            server = self.settings.value("server", "")
            username = self.settings.value("username", "")
            password = self.settings.value("password", "")
            remember = self.settings.value("remember_credentials", True, type=bool)
            account_name = self.current_account or ""
        from src.ui.widgets.dialogs import LoginDialog
        from PyQt5.QtWidgets import QLineEdit, QLabel, QVBoxLayout
        dialog = LoginDialog(self, server, username, password, remember)
        # Add account name field to the dialog
        name_label = QLabel("Account Name:")
        name_edit = QLineEdit(account_name)
        dialog.layout().insertWidget(0, name_edit)
        dialog.layout().insertWidget(0, name_label)
        if dialog.exec_():
            credentials = dialog.get_credentials()
            name = name_edit.text().strip() or f"Account {len(self.accounts)+1}"
            # Save account
            acc = {
                'server': credentials['server'],
                'username': credentials['username'],
                'password': credentials['password'],
                'account_name': name
            }
            # Remove old name if renaming
            if self.current_account and self.current_account in self.accounts and self.current_account != name:
                self.accounts.pop(self.current_account)
            self.accounts[name] = acc
            self.current_account = name
            self.settings.setValue("accounts", self.accounts)
            self.settings.setValue("current_account", name)
            # Save credentials if remember is checked
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
            # Connect to server
            self.connect_to_server(credentials['server'], credentials['username'], credentials['password'])
            self.update_account_label()  # Update app title after login
        elif account_switch:
            self.show_account_switch_dialog()

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
        self.statusBar.showMessage("Connecting to server...")
        # Recreate all tabs and UI to avoid using deleted widgets
        # self.setup_ui()  # This will recreate tabs, home_screen, etc. - Let's see if this is still needed or if selective updates are better
        # self.load_favorites()  # Ensure favorites are loaded for the new tab instance
        self.api_client.set_credentials(server, username, password)
        success, data = self.api_client.authenticate()
        expiry_str = ""
        if success:
            self.statusBar.showMessage("Connected successfully. Populating cache...")
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
            self.statusBar.showMessage("Connection failed")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Connection Error", f"Failed to connect: {data}")
            self.show_login_dialog(account_switch=True)

    def load_favorites(self):
        """Load favorites from file with error handling"""
        try:
            data = load_json_file(FAVORITES_FILE, default={})
            if isinstance(data, dict):
                self.favorites_by_account = data
                self.favorites = data.get(self.current_account, [])
            elif isinstance(data, list):
                # Legacy: if file is a list, treat as favorites for current account
                self.favorites_by_account = {self.current_account: data}
                self.favorites = data
            else:
                self.favorites_by_account = {}
                self.favorites = []
        except Exception as e:
            QMessageBox.warning(self, "Favorites Error", f"Failed to load favorites: {e}\nFavorites will be reset.")
            self.favorites_by_account = {}
            self.favorites = []
        print(f"[DEBUG] Loaded favorites for account '{self.current_account}': {self.favorites}")
        if hasattr(self, 'favorites_tab'):
            self.favorites_tab.set_favorites(self.favorites)

    def save_favorites(self):
        """Save favorites to file, keyed by account"""
        if not hasattr(self, 'favorites_by_account'):
            self.favorites_by_account = {}
        self.favorites_by_account[self.current_account] = self.favorites
        save_json_file(FAVORITES_FILE, self.favorites_by_account)

    def add_to_favorites(self, item):
        """Add an item to favorites for the current account"""
        if not hasattr(self, 'favorites'):
            self.favorites = []
        # Use is_favorite for robust duplicate check
        if self.is_favorite(item):
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(self, "Favorites", "Already in favorites.")
            return
        self.favorites.append(item)
        if hasattr(self, 'favorites_tab'):
            self.favorites_tab.set_favorites(self.favorites)
        self.save_favorites()
        item_name = item.get('name', 'Item')
        self.statusBar.showMessage(f"'{item_name}' added to favorites.", 3000)
        self.favorites_changed.emit()

    def remove_from_favorites(self, item_to_remove):
        """Remove an item from favorites for the current account.
        The item is identified by its content (e.g., stream_type and ID).
        """
        if not hasattr(self, 'favorites') or not self.favorites:
            return

        found_index = -1
        item_type_to_remove = item_to_remove.get('stream_type')
        id_to_remove = None

        # Determine the ID from item_to_remove based on its stream_type
        if item_type_to_remove == 'movie':
            id_to_remove = item_to_remove.get('movie_id') or item_to_remove.get('id') # Common keys for movie ID
        elif item_type_to_remove == 'series':
            id_to_remove = item_to_remove.get('series_id')
        elif item_type_to_remove == 'live':
            id_to_remove = item_to_remove.get('stream_id')
        # Add other types if necessary, or a general 'id' fallback
        # else:
            # id_to_remove = item_to_remove.get('id') # General fallback

        if id_to_remove is None and item_type_to_remove is not None:
            # This case might happen if the ID key is unexpected for a known type
            print(f"Warning: Could not determine a unique ID for removal for item type '{item_type_to_remove}': {item_to_remove}")
            return
        elif id_to_remove is None and item_type_to_remove is None:
             # This case if item_to_remove is not structured as expected (e.g. not a dict or missing keys)
             # This was the original problem path if 'index' (now item_to_remove) was an int.
             # However, the TypeError implies item_to_remove is a dict here.
             # For safety, if it's not a dict or doesn't have expected keys, we can't proceed.
            if isinstance(item_to_remove, int):
                 # Handle the original integer index case if it's still possible from other call sites
                if 0 <= item_to_remove < len(self.favorites):
                    found_index = item_to_remove
                else:
                    print(f"Warning: Index {item_to_remove} out of bounds for favorites list.")
                    return # Index out of bounds
            else:
                print(f"Warning: item_to_remove is not an integer index and key identifiers (stream_type, id) are missing: {item_to_remove}")
                return

        if found_index == -1: # If not already found via integer index path
            for i, fav_item in enumerate(self.favorites):
                fav_item_type = fav_item.get('stream_type')
                fav_item_id = None

                if fav_item_type == 'movie':
                    fav_item_id = fav_item.get('movie_id') or fav_item.get('id')
                elif fav_item_type == 'series':
                    fav_item_id = fav_item.get('series_id')
                elif fav_item_type == 'live':
                    fav_item_id = fav_item.get('stream_id')
                # else:
                    # fav_item_id = fav_item.get('id') # General fallback

                if fav_item_type == item_type_to_remove and fav_item_id == id_to_remove and fav_item_id is not None:
                    found_index = i
                    break
        
        if found_index != -1:
            removed = self.favorites.pop(found_index)
            if hasattr(self, 'favorites_tab'):
                self.favorites_tab.set_favorites(self.favorites)
            self.save_favorites()
            item_name = removed.get('name', 'Item')
            self.statusBar.showMessage(f"'{item_name}' removed from favorites.", 3000)
            self.favorites_changed.emit()
        else:
            item_name_to_remove = item_to_remove.get('name', 'Unknown item') if isinstance(item_to_remove, dict) else 'Item at invalid index'
            # print(f"Warning: Item '{item_name_to_remove}' (ID: {id_to_remove}, Type: {item_type_to_remove}) not found in favorites for removal.")
            self.statusBar.showMessage(f"Could not remove '{item_name_to_remove}'. Item not found in favorites.", 3000)

    def is_favorite(self, item_to_check):
        """Check if an item is in favorites for the current account, considering item type."""
        if not hasattr(self, 'favorites') or not self.favorites:
            return False

        item_id_to_check = None
        # stream_type should ideally be present in item_to_check.
        # It can be 'movie', 'series', or 'live'.
        item_type_to_check = item_to_check.get('stream_type')

        # Determine the primary ID for item_to_check
        if item_to_check.get('series_id') is not None:
            item_id_to_check = item_to_check.get('series_id')
            # If series_id is present, the type must be 'series'.
            # If item_type_to_check is different, it's a data inconsistency. Prioritize series_id.
            if item_type_to_check != 'series':
                # print(f"[WARN] is_favorite: Item has series_id {item_id_to_check} but stream_type is '{item_type_to_check}'. Assuming 'series'.")
                item_type_to_check = 'series'
        elif item_to_check.get('stream_id') is not None:
            item_id_to_check = item_to_check.get('stream_id')
            # If only stream_id is present, item_type_to_check should be 'movie' or 'live'.
            # If item_type_to_check is None here, it's problematic for typed comparison.
            # add_to_favorites should ensure stream_type is set.
            if item_type_to_check is None:
                # print(f"[WARN] is_favorite: Item with stream_id {item_id_to_check} has no stream_type. Type comparison might be unreliable.")
                pass # Keep item_type_to_check as None for now.
        else:
            # No usable ID found in item_to_check
            return False

        if item_id_to_check is None: # Should be caught above, but as a safeguard.
            return False

        for favorite_item in self.favorites:
            fav_item_id = None
            # Favorites are expected to have 'stream_type' stored by add_to_favorites.
            fav_item_type = favorite_item.get('stream_type')

            if fav_item_type == 'series':
                fav_item_id = favorite_item.get('series_id')
            elif fav_item_type == 'movie' or fav_item_type == 'live': # Assuming 'live' is also a possible type
                fav_item_id = favorite_item.get('stream_id')
            else:
                # This favorite_item might be from an older version or has an unknown/missing type.
                # If both the item_to_check and the favorite_item lack a specific type,
                # fall back to the original generic ID comparison.
                if not item_type_to_check and not fav_item_type:
                    # Original untyped comparison logic
                    generic_id_to_check = item_to_check.get('stream_id') or item_to_check.get('series_id')
                    generic_fav_id = favorite_item.get('stream_id') or favorite_item.get('series_id')
                    if generic_fav_id is not None and generic_fav_id == generic_id_to_check:
                        return True
                continue # Skip if types are inconsistent or fav_item_type is unknown for typed comparison

            # Now compare with type
            if fav_item_id is not None and fav_item_id == item_id_to_check and fav_item_type == item_type_to_check:
                return True
        
        return False
    def switch_account(self, name):
        """Switch to a different account and reload all tab data without deleting/recreating widgets"""
        self.current_account = name
        self.settings.setValue("current_account", name)
        self.load_favorites()
        if hasattr(self, 'favorites_tab'):
            self.favorites_tab.set_favorites(self.favorites)
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
        self.tabs.setTabText(4, self.translations.get("Search", "Search")) # Added Search tab title
        
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
        from src.ui.widgets.dialogs import LoginDialog
        dialog = LoginDialog(self, acc.get('server', ''), acc.get('username', ''), acc.get('password', ''), True)
        if dialog.exec_():
            credentials = dialog.get_credentials()
            # Optionally allow renaming
            from PyQt5.QtWidgets import QInputDialog
            new_name, ok = QInputDialog.getText(self, "Edit Account Name", "Edit account name:", text=name)
            if not ok or not new_name.strip():
                new_name = name
            # Update account
            self.accounts.pop(name)
            self.accounts[new_name] = {
                'server': credentials['server'],
                'username': credentials['username'],
                'password': credentials['password']
            }
            self.current_account = new_name
            self.settings.setValue("accounts", self.accounts)
            self.settings.setValue("current_account", new_name)
            self.api_client.set_credentials(credentials['server'], credentials['username'], credentials['password'])
            self.connect_to_server(credentials['server'], credentials['username'], credentials['password'])
            self.update_account_label()

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
                self.setWindowTitle("Sahab Xtream IPTV")

    def _account_data_key(self, suffix):
        # Use a unique key for each account's data
        return f"{self.current_account}_{suffix}" if self.current_account else suffix

    def _load_account_data(self):
        # Load downloads for the current account (favorites are already loaded by load_favorites)
        # TODO: Implement per-account downloads loading if needed
        pass

    def show_home_screen(self):
        """Return to the home screen from any tab"""
        self.setCentralWidget(self.home_screen)

    def show_status_message(self, message, timeout=5000):
        if hasattr(self, 'statusBar') and self.statusBar:
            self.statusBar.showMessage(message, timeout)
