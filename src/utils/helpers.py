"""
Helper functions for the application
"""
import os
import json
from PyQt5.QtGui import QPalette, QColor, QPixmap
from PyQt5.QtCore import Qt, QMetaObject, Q_ARG, QObject
import threading
import requests # Added import
from .image_cache import ImageCache
import unicodedata

def load_json_file(file_path, default=None):
    """Load JSON data from a file"""
    if default is None:
        default = {}
    
    if not os.path.exists(file_path):
        return default
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default

def save_json_file(file_path, data):
    """Save JSON data to a file"""
    try:
        directory = os.path.dirname(file_path)
        if not os.path.exists(directory):
            os.makedirs(directory)
            
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def format_duration(seconds):
    """Format seconds to HH:MM:SS"""
    if seconds is None:
        return "00:00:00"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"

def apply_dark_theme(app):
    """Apply dark theme to the application"""
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.WindowText, Qt.white)
    dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
    dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
    dark_palette.setColor(QPalette.ToolTipText, Qt.white)
    dark_palette.setColor(QPalette.Text, Qt.white)
    dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ButtonText, Qt.white)
    dark_palette.setColor(QPalette.BrightText, Qt.red)
    dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.HighlightedText, Qt.black)
    
    app.setPalette(dark_palette)
    
    # Set stylesheet for better appearance
    app.setStyleSheet("""
        QToolTip { 
            color: #ffffff; 
            background-color: #2a82da; 
            border: 1px solid white; 
        }
        
        QTabWidget::pane {
            border: 1px solid #444;
            top: -1px;
        }
        
        QTabBar::tab {
            background: #3A3A3A;
            border: 1px solid #444;
            padding: 5px 10px;
            margin-right: 2px;
        }
        
        QTabBar::tab:selected {
            background: #636363;
        }
        
        QTabBar::tab:hover {
            background: #505050;
        }
        
        QPushButton {
            background-color: #3A3A3A;
            border: 1px solid #555;
            border-radius: 4px;
            padding: 5px 10px;
        }
        
        QPushButton:hover {
            background-color: #505050;
        }
        
        QPushButton:pressed {
            background-color: #2a82da;
        }
        
        QLineEdit, QComboBox {
            background-color: #2D2D2D;
            border: 1px solid #555;
            border-radius: 4px;
            padding: 3px 5px;
        }
        
        QProgressBar {
            border: 1px solid #555;
            border-radius: 4px;
            text-align: center;
        }
        
        QProgressBar::chunk {
            background-color: #2a82da;
        }
        
        QSlider::groove:horizontal {
            height: 8px;
            background: #2D2D2D;
            margin: 2px 0;
        }
        
        QSlider::handle:horizontal {
            background: #2a82da;
            border: 1px solid #2a82da;
            width: 18px;
            margin: -2px 0;
            border-radius: 9px;
        }
        
        QSlider::sub-page:horizontal {
            background: #2a82da;
        }
    """)
def get_translations(language):
    """Get translations for the specified language"""
    translations = {
        "en": {
            "Live TV": "Live TV",
            "Movies": "Movies",
            "Series": "Series",
            "Favorites": "Favorites",
            "Play": "Play",
            "Pause": "Pause",
            "Stop": "Stop",
            "Record": "Record",
            "Stop Recording": "Stop Recording",
            "Add to Favorites": "Add to Favorites",
            "Remove from Favorites": "Remove from Favorites",
            "Connect": "Connect",
            "Server URL": "Server URL",
            "Username": "Username",
            "Password": "Password",
            "Remember": "Remember",
            "Search channels...": "Search channels...",
            "Search movies...": "Search movies...",
            "Search series...": "Search series...",
            "Search favorites...": "Search favorites...",
            "Settings": "Settings",
            "Language": "Language",
            "Dark Mode": "Dark Mode",
            "Volume": "Volume",
            "Mute": "Mute",
            "Fullscreen": "Fullscreen",
            "Exit Fullscreen": "Exit Fullscreen",
            "Speed": "Speed"
        },
        "ar": {
            "Live TV": "البث المباشر",
            "Movies": "الأفلام",
            "Series": "المسلسلات",
            "Favorites": "المفضلة",
            "Play": "تشغيل",
            "Pause": "إيقاف مؤقت",
            "Stop": "إيقاف",
            "Record": "تسجيل",
            "Stop Recording": "إيقاف التسجيل",
            "Add to Favorites": "إضافة إلى المفضلة",
            "Remove from Favorites": "إزالة من المفضلة",
            "Connect": "اتصال",
            "Server URL": "عنوان الخادم",
            "Username": "اسم المستخدم",
            "Password": "كلمة المرور",
            "Remember": "تذكر",
            "Search channels...": "البحث في القنوات...",
            "Search movies...": "البحث في الأفلام...",
            "Search series...": "البحث في المسلسلات...",
            "Search favorites...": "البحث في المفضلة...",
            "Settings": "الإعدادات",
            "Language": "اللغة",
            "Dark Mode": "الوضع الداكن",
            "Volume": "الصوت",
            "Mute": "كتم",
            "Fullscreen": "ملء الشاشة",
            "Exit Fullscreen": "الخروج من ملء الشاشة",
            "Speed": "السرعة"
        }
    }
    
    return translations.get(language, translations["en"])

def get_api_client_from_label(label, main_window):
    # Try to get api_client from main_window, fallback to traversing parents
    if main_window and hasattr(main_window, 'api_client'):
        return main_window.api_client
    # Fallback: traverse up the parent chain
    parent = label.parent()
    for _ in range(5):
        if parent is None:
            break
        if hasattr(parent, 'api_client'):
            return parent.api_client
        parent = parent.parent() if hasattr(parent, 'parent') else None
    return None

def load_image_async(image_url, label, default_pixmap, update_size=(100, 140), main_window=None, loading_counter=None, on_failure=None):
    ImageCache.ensure_cache_dir()
    cache_path = ImageCache.get_cache_path(image_url)
    def set_pixmap(pixmap):
        try:
            if not hasattr(label, 'setPixmap'):
                return

            label.setPixmap(pixmap.scaled(*update_size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except RuntimeError:
            return
    def worker():
            # print(f"[DEBUG] Start loading image: {image_url}")
            if main_window and hasattr(main_window, 'loading_icon_controller'):
                main_window.loading_icon_controller.show_icon.emit()
            
            final_pix = QPixmap() 
            download_successful = False

            try:
                if not image_url:
                    print(f"[load_image_async] Invalid image_url (None or empty). Using default.")
                    # final_pix remains empty, will lead to default_pixmap and on_failure
                else:
                    # cache_path is from outer scope
                    temp_pix_worker = QPixmap() 
                    if os.path.exists(cache_path):
                        if temp_pix_worker.load(cache_path) and not temp_pix_worker.isNull():
                            final_pix = temp_pix_worker
                        else:
                            print(f"[load_image_async] Failed to load image from cache or cache invalid: {cache_path}")
                            # final_pix remains empty
                    
                    if final_pix.isNull(): # If not loaded from cache or cache was bad
                        image_data = None
                        if image_url.startswith('http://') or image_url.startswith('https://'):
                            #print(f"[load_image_async] Downloading image via requests: {image_url}")
                            
                            try:
                                response = requests.get(image_url, timeout=10) 
                                response.raise_for_status() 
                                image_data = response.content
                                download_successful = True
                                
                            except requests.HTTPError as e:
                                print(f"[load_image_async] HTTP Error downloading image: {e}")
                                image_data = None
                                        
                            except requests.RequestException as e:
                                print(f"[load_image_async] Request error: {e}")
                                image_data = None
                                    
                            except Exception as e:
                                print(f"[load_image_async] Unexpected error downloading with requests: {e}")
                                image_data = None 
                        else:
                            print(f"[load_image_async] Downloading image via api_client: {image_url}")
                            api_client = get_api_client_from_label(label, main_window)
                            try:
                                if api_client:
                                    image_data = api_client.get_image_data(image_url)
                                    if image_data:
                                        download_successful = True
                                else:
                                    print("[load_image_async] Could not find api_client for image download!")
                                    image_data = None 
                            except Exception as e: 
                                print(f"[load_image_async] Error downloading image via api_client: {e}")
                                image_data = None 
                        
                        if image_data:
                            if temp_pix_worker.loadFromData(image_data) and not temp_pix_worker.isNull():
                                final_pix = temp_pix_worker
                                try:
                                    saved = final_pix.save(cache_path) # Use cache_path from outer scope
                                    # print(f"[load_image_async] Image downloaded and cached: {cache_path}, save result: {saved}")
                                except Exception as e:
                                    print(f"[load_image_async] Error saving image to cache: {e}")
                            else:
                                print(f"[load_image_async] Failed to load image from data for: {image_url}")
                                # final_pix remains empty
                                download_successful = False
                        # else: image_data is None, final_pix remains empty
            
            except AttributeError as e: 
                print(f"[load_image_async] AttributeError in worker, likely due to invalid image_url '{image_url}': {e}")
                # final_pix remains empty
            except Exception as e: 
                print(f"[load_image_async] Unexpected error in image loading worker for '{image_url}': {e}")
                # final_pix remains empty

            pix_to_set = final_pix 
            if pix_to_set.isNull(): 
                pix_to_set = default_pixmap 
                if on_failure:
                    is_network_error = not download_successful and (image_url.startswith('http://') or image_url.startswith('https://'))
                    if hasattr(on_failure, '__self__') and isinstance(on_failure.__self__, QObject) and hasattr(on_failure, '__name__'):
                        QMetaObject.invokeMethod(on_failure.__self__, on_failure.__name__, Qt.QueuedConnection, Q_ARG(bool, is_network_error))
                    elif callable(on_failure):
                        # Handle lambda functions and other callables
                        try:
                            on_failure()
                        except Exception as e:
                            print(f"[load_image_async] Error calling on_failure callback: {e}")
                    else:
                        print(f"[load_image_async] on_failure callback '{on_failure}' is not a recognized QObject method or slot.")
            
            try:
                if hasattr(label, 'setPixmap'): 
                    scaled_pixmap = pix_to_set.scaled(*update_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)


                    QMetaObject.invokeMethod(label, "setPixmap", Qt.QueuedConnection, Q_ARG(QPixmap, scaled_pixmap))
                else:
                    print(f"[load_image_async] Label {label} does not have setPixmap method.")
            except RuntimeError: 
                pass 

            if loading_counter is not None:
                loading_counter['count'] -= 1
                if loading_counter['count'] <= 0 and main_window and hasattr(main_window, 'loading_icon_controller'):
                    main_window.loading_icon_controller.hide_icon.emit()
            else: 
                if main_window and hasattr(main_window, 'loading_icon_controller'):
                    main_window.loading_icon_controller.hide_icon.emit()
            #print(f"[DEBUG] Finished loading image: {image_url}")
    # Set cached or placeholder immediately
    if os.path.exists(cache_path):
        pix = QPixmap()
        pix.load(cache_path)
        set_pixmap(pix)
    else:
        set_pixmap(default_pixmap)
        if loading_counter is not None:
            loading_counter['count'] += 1
        threading.Thread(target=worker, daemon=True).start()
