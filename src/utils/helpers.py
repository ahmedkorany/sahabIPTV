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
            "Speed": "Speed",
            # Additional UI strings
            "Home": "Home",
            "Search": "Search",
            "Categories": "Categories",
            "Channels": "Channels",
            "ALL": "ALL",
            "Default": "Default",
            "Date": "Date",
            "Rating": "Rating",
            "Name": "Name",
            "Desc": "Desc",
            "Asc": "Asc",
            "Previous": "Previous",
            "Next": "Next",
            "All": "All",
            "Live": "Live",
            "Save": "Save",
            "Cancel": "Cancel",
            "Edit Account": "Edit Account",
            "Add Account": "Add Account",
            "Delete Account": "Delete Account",
            "Switch Account": "Switch Account",
            "No items to display.": "No items to display.",
            "No channels to display.": "No channels to display.",
            "No movies to display.": "No movies to display.",
            "Account Management": "Account Management",
            "Error": "Error",
            "Warning": "Warning",
            "Information": "Information",
            "Success": "Success",
            "Episodes": "Episodes",
            "Cast": "Cast",
            "Export Season URLs": "Export Season URLs",
            "WATCH TRAILER": "WATCH TRAILER",
            "PLAY": "PLAY",
            "No cast information available": "No cast information available",
            "No rating": "No rating",
            "Ready": "Ready",
            "File": "File",
            "Exit": "Exit",
            "Help": "Help",
            "About": "About",
            "English": "English",
            "Arabic": "Arabic",
            "Fast Backward": "Fast Backward",
            "Fast Forward": "Fast Forward",
            "Player": "Player",
            "Recording": "Recording",
            "Trailer": "Trailer",
            "Download": "Download",
            "Export": "Export",
            "Season": "Season",
            "Episode": "Episode",
            "Progress": "Progress",
            "Please wait...": "Please wait...",
            "My IPTV Account": "My IPTV Account",
            "Remember credentials": "Remember credentials",
            "Connection Error": "Connection Error",
            "Playback Error": "Playback Error",
            "Recording Error": "Recording Error",
            "Input Error": "Input Error",
            "Navigation Error": "Navigation Error",
            "Edit Current Account": "Edit Current Account",
            "Add New Account": "Add New Account",
            "Caching Data": "Caching Data",
            "Populating cache...": "Populating cache...",
            "Connection failed": "Connection failed",
            "Already in favorites": "Already in favorites",
            "Download Started": "Download Started",
            "Export Successful": "Export Successful",
            "Export Error": "Export Error",
            "Export Failed": "Export Failed",
            "Export Complete": "Export Complete",
            "Save Episode": "Save Episode",
            "Save Recording": "Save Recording",
            "Video Files": "Video Files",
            "Text Files": "Text Files",
            "M3U Playlist": "M3U Playlist",
            "All Files": "All Files",
            "Sahab Xtream IPTV": "Sahab Xtream IPTV",
            "Connecting to server...": "Connecting to server...",
            "Connected successfully. Populating cache...": "Connected successfully. Populating cache...",
            "Loading...": "Loading...",
            "Loading cast...": "Loading cast...",
            "Loading images...": "Loading images...",
            "Order by": "Order by:",
            "Speed": "Speed:",
            "Page": "Page",
            "of": "of",
            "Account Name": "Account Name:",
            "Director": "Director:",
            "← Back": "← Back",
            "▶ PLAY": "▶ PLAY",
            "🎬 TRAILER": "🎬 TRAILER",
            "Search Live, Movies, and Series...": "Search Live, Movies, and Series...",
            "Search series...": "Search series...",
            "Search movies...": "Search movies...",
            "e.g. My IPTV Account": "e.g. My IPTV Account",
            "http://example.com": "http://example.com",
            "Add/Edit Account": "Add/Edit Account",
            "Account Management": "Account Management",
            "← Back": "← Back",
            "Delete Account": "Delete Account",
            "Switch Account": "Switch Account",
            "🎬 TRAILER": "🎬 TRAILER",
            "Director: ": "Director: ",
            "This category doesn't contain any Series": "This category doesn't contain any Series",
            "Episodes": "Episodes",
            "Play": "Play",
            "Desc": "Desc",
            "Loading cast...": "Loading cast...",
            "No cast information available": "No cast information available",
            "Reload Data": "Reload Data",
            "Switch Account": "Switch Account",
            "No items to display.": "No items to display.",
            "No channels to display.": "No channels to display.",
            "No movies to display.": "No movies to display.",
            "This category doesn't contain any Series": "This category doesn't contain any Series",
            "Press ESC to return to normal view": "Press ESC to return to normal view",
            "Play Episode": "Play Episode",
            "Trailer playback not implemented.": "Trailer playback not implemented.",
            "Unable to get movie stream URL.": "Unable to get movie stream URL.",
            "Player window not available.": "Player window not available.",
            "Invalid series data provided.": "Invalid series data provided.",
            "Could not retrieve stream URL for the episode.": "Could not retrieve stream URL for the episode.",
            "Player window or episode data not available.": "Player window or episode data not available.",
            "Favorite functionality not available.": "Favorite functionality not available.",
            "Series data is incomplete for favorites.": "Series data is incomplete for favorites.",
            "Episode or series data not found for download.": "Episode or series data not found for download.",
            "Could not retrieve download URL for the episode.": "Could not retrieve download URL for the episode.",
            "Series data not available for season export.": "Series data not available for season export.",
            "No episodes found for Season": "No episodes found for Season",
            "to export.": "to export.",
            "Could not load favorites from favorites manager.": "Could not load favorites from favorites manager.",
            "No episode selected": "No episode selected",
            "No season selected": "No season selected",
            "Failed to get season information": "Failed to get season information",
            "Season URLs exported to": "Season URLs exported to:",
            "Failed to export season URLs": "Failed to export season URLs:",
            "Select an account to edit.": "Select an account to edit.",
            "Select an account to delete.": "Select an account to delete.",
            "Cannot delete the currently active account.": "Cannot delete the currently active account.",
            "Delete account": "Delete account",
            "Select an account to switch to.": "Select an account to switch to.",
            "Already using this account.": "Already using this account.",
            "Authentication failed. Please check credentials.": "Authentication failed. Please check credentials.",
            "Failed to load categories": "Failed to load categories:",
            "Failed to load movies": "Failed to load movies:",
            "Failed to load series": "Failed to load series:",
            "Favorites manager not available.": "Favorites manager not available.",
            "No movie selected": "No movie selected",
            "No movie is playing": "No movie is playing",
            "Failed to load channels": "Failed to load channels:",
            "No channel selected": "No channel selected",
            "Could not open the stream. The channel may be temporarily unavailable.": "Could not open the stream. The channel may be temporarily unavailable.",
            "Channel data is missing stream ID": "Channel data is missing stream ID",
            "Could not play the channel from search.": "Could not play the channel from search.",
            "No channel is playing": "No channel is playing",
            "Recording started successfully": "Recording started successfully",
            "Recording stopped successfully": "Recording stopped successfully",
            "Failed to load detailed series information": "Failed to load detailed series information:",
            "Error fetching detailed series metadata": "Error fetching detailed series metadata:",
            "Series ID is missing, cannot load details.": "Series ID is missing, cannot load details.",
            "Episode data not found.": "Episode data not found.",
            "No trailer URL available for this series.": "No trailer URL available for this series.",
            "No season selected to export.": "No season selected to export.",
            "Series tab is not available.": "Series tab is not available.",
            "Movies tab is not available.": "Movies tab is not available.",
            "Live TV tab is not available.": "Live TV tab is not available.",
            "Account name cannot be empty.": "Account name cannot be empty.",
            "An account with the name": "An account with the name",
            "already exists.": "already exists.",
            "Failed to connect": "Failed to connect:",
            "Categories": "Categories",
            "All": "All",
            "Default": "Default",
            "Date": "Date",
            "Rating": "Rating",
            "Name": "Name",
            "Channels": "Channels",
            "Previous": "Previous",
            "Next": "Next",
            "Page 1 of 1": "Page 1 of 1",
            "Back": "Back",
            "PLAY": "PLAY",
            "Add to favorites": "Add to favorites",
            "Remove from favorites": "Remove from favorites",
            "Cast": "Cast",
            "Export Season URLs": "Export Season URLs",
            "User": "User:",
            "Subscription expires": "Subscription expires:",
            "Password": "Password:",
            "Remember credentials": "Remember credentials",
            "Save": "Save",
            "Cancel": "Cancel",
            "Account Name": "Account Name:",
            "Server URL": "Server URL:",
            "Add Account": "Add Account",
            "Edit Account": "Edit Account",
            "e.g. My IPTV Account": "e.g. My IPTV Account",
            "http://example.com": "http://example.com",
            "Add/Edit Account": "Add/Edit Account",
            "Account Management": "Account Management",
            "← Back": "← Back",
            "Delete Account": "Delete Account",
            "Switch Account": "Switch Account",
            "🎬 TRAILER": "🎬 TRAILER",
            "Director: ": "Director: ",
            "This category doesn't contain any Series": "This category doesn't contain any Series",
            "Episodes": "Episodes",
            "Play": "Play",
            "Desc": "Desc",
            "Loading cast...": "Loading cast...",
            "No cast information available": "No cast information available"
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
            "Speed": "السرعة",
            # Additional UI strings in Arabic
            "Home": "الرئيسية",
            "Search": "البحث",
            "Categories": "الفئات",
            "Channels": "القنوات",
            "ALL": "الكل",
            "Default": "افتراضي",
            "Date": "التاريخ",
            "Rating": "التقييم",
            "Name": "الاسم",
            "Desc": "تنازلي",
            "Asc": "تصاعدي",
            "Previous": "السابق",
            "Next": "التالي",
            "All": "الكل",
            "Live": "مباشر",
            "Save": "حفظ",
            "Cancel": "إلغاء",
            "Edit Account": "تعديل الحساب",
            "Add Account": "إضافة حساب",
            "Delete Account": "حذف الحساب",
            "Switch Account": "تبديل الحساب",
            "No items to display.": "لا توجد عناصر للعرض.",
            "No channels to display.": "لا توجد قنوات للعرض.",
            "No movies to display.": "لا توجد أفلام للعرض.",
            "Account Management": "إدارة الحسابات",
            "Error": "خطأ",
            "Warning": "تحذير",
            "Information": "معلومات",
            "Success": "نجح",
            "Episodes": "الحلقات",
            "Cast": "طاقم التمثيل",
            "Export Season URLs": "تصدير روابط الموسم",
            "WATCH TRAILER": "مشاهدة الإعلان",
            "PLAY": "تشغيل",
            "No cast information available": "لا توجد معلومات عن طاقم التمثيل",
            "No rating": "لا يوجد تقييم",
            "Ready": "جاهز",
            "File": "ملف",
            "Exit": "خروج",
            "Help": "مساعدة",
            "About": "حول",
            "English": "الإنجليزية",
            "Arabic": "العربية",
            "Fast Backward": "ترجيع سريع",
            "Fast Forward": "تقديم سريع",
            "Player": "المشغل",
            "Recording": "التسجيل",
            "Trailer": "الإعلان",
            "Download": "تحميل",
            "Export": "تصدير",
            "Season": "الموسم",
            "Episode": "الحلقة",
            "Progress": "التقدم",
            "Please wait...": "يرجى الانتظار...",
            "My IPTV Account": "حساب IPTV الخاص بي",
            "Remember credentials": "تذكر بيانات الاعتماد",
            "Connection Error": "خطأ في الاتصال",
            "Playback Error": "خطأ في التشغيل",
            "Recording Error": "خطأ في التسجيل",
            "Input Error": "خطأ في الإدخال",
            "Navigation Error": "خطأ في التنقل",
            "Edit Current Account": "تعديل الحساب الحالي",
            "Add New Account": "إضافة حساب جديد",
            "Caching Data": "تخزين البيانات مؤقتاً",
            "Populating cache...": "ملء التخزين المؤقت...",
            "Connection failed": "فشل الاتصال",
            "Already in favorites": "موجود بالفعل في المفضلة",
            "Download Started": "بدأ التحميل",
            "Export Successful": "تم التصدير بنجاح",
            "Export Error": "خطأ في التصدير",
            "Export Failed": "فشل التصدير",
            "Export Complete": "اكتمل التصدير",
            "Save Episode": "حفظ الحلقة",
            "Save Recording": "حفظ التسجيل",
            "Video Files": "ملفات الفيديو",
            "Text Files": "الملفات النصية",
            "M3U Playlist": "قائمة تشغيل M3U",
            "All Files": "جميع الملفات",
            "Sahab Xtream IPTV": "سحاب إكستريم IPTV",
            "Connecting to server...": "الاتصال بالخادم...",
            "Connected successfully. Populating cache...": "تم الاتصال بنجاح. جاري تحديث التخزين المؤقت...",
            "Loading...": "جاري التحميل...",
            "Loading cast...": "جاري تحميل طاقم التمثيل...",
            "Loading images...": "جاري تحميل الصور...",
            "Order by": "ترتيب حسب:",
            "Speed": "السرعة:",
            "Page": "صفحة",
            "of": "من",
            "Account Name": "اسم الحساب:",
            "Director": "المخرج:",
            "← Back": "← رجوع",
            "▶ PLAY": "▶ تشغيل",
            "🎬 TRAILER": "🎬 إعلان",
            "Search Live, Movies, and Series...": "البحث في البث المباشر والأفلام والمسلسلات...",
            "Search series...": "البحث في المسلسلات...",
            "Search movies...": "البحث في الأفلام...",
            "e.g. My IPTV Account": "مثال: حساب IPTV الخاص بي",
            "http://example.com": "http://example.com",
            "Add/Edit Account": "إضافة/تعديل حساب",
            "Reload Data": "إعادة تحميل البيانات",
            "Switch Account": "تبديل الحساب",
            "No items to display.": "لا توجد عناصر للعرض.",
            "No channels to display.": "لا توجد قنوات للعرض.",
            "No movies to display.": "لا توجد أفلام للعرض.",
            "This category doesn't contain any Series": "هذه الفئة لا تحتوي على أي مسلسلات",
            "Press ESC to return to normal view": "اضغط ESC للعودة إلى العرض العادي",
            "Play Episode": "تشغيل الحلقة",
            "Trailer playback not implemented.": "تشغيل الإعلان غير مطبق.",
            "Unable to get movie stream URL.": "غير قادر على الحصول على رابط تدفق الفيلم.",
            "Player window not available.": "نافذة المشغل غير متاحة.",
            "Invalid series data provided.": "بيانات المسلسل المقدمة غير صحيحة.",
            "Could not retrieve stream URL for the episode.": "لا يمكن استرداد رابط التدفق للحلقة.",
            "Player window or episode data not available.": "نافذة المشغل أو بيانات الحلقة غير متاحة.",
            "Favorite functionality not available.": "وظيفة المفضلة غير متاحة.",
            "Series data is incomplete for favorites.": "بيانات المسلسل غير مكتملة للمفضلة.",
            "Episode or series data not found for download.": "بيانات الحلقة أو المسلسل غير موجودة للتحميل.",
            "Could not retrieve download URL for the episode.": "لا يمكن استرداد رابط التحميل للحلقة.",
            "Series data not available for season export.": "بيانات المسلسل غير متاحة لتصدير الموسم.",
            "No episodes found for Season": "لم يتم العثور على حلقات للموسم",
            "to export.": "للتصدير.",
            "Could not load favorites from favorites manager.": "لا يمكن تحميل المفضلة من مدير المفضلة.",
            "No episode selected": "لم يتم تحديد حلقة",
            "No season selected": "لم يتم تحديد موسم",
            "Failed to get season information": "فشل في الحصول على معلومات الموسم",
            "Season URLs exported to": "تم تصدير روابط الموسم إلى:",
            "Failed to export season URLs": "فشل في تصدير روابط الموسم:",
            "Select an account to edit.": "حدد حساباً للتعديل.",
            "Select an account to delete.": "حدد حساباً للحذف.",
            "Cannot delete the currently active account.": "لا يمكن حذف الحساب النشط حالياً.",
            "Delete account": "حذف الحساب",
            "Select an account to switch to.": "حدد حساباً للتبديل إليه.",
            "Already using this account.": "تستخدم هذا الحساب بالفعل.",
            "Authentication failed. Please check credentials.": "فشل في المصادقة. يرجى التحقق من بيانات الاعتماد.",
            "Failed to load categories": "فشل في تحميل الفئات:",
            "Failed to load movies": "فشل في تحميل الأفلام:",
            "Failed to load series": "فشل في تحميل المسلسلات:",
            "Favorites manager not available.": "مدير المفضلة غير متاح.",
            "No movie selected": "لم يتم تحديد فيلم",
            "No movie is playing": "لا يوجد فيلم قيد التشغيل",
            "Failed to load channels": "فشل في تحميل القنوات:",
            "No channel selected": "لم يتم تحديد قناة",
            "Could not open the stream. The channel may be temporarily unavailable.": "لا يمكن فتح التدفق. قد تكون القناة غير متاحة مؤقتاً.",
            "Channel data is missing stream ID": "بيانات القناة تفتقر إلى معرف التدفق",
            "Could not play the channel from search.": "لا يمكن تشغيل القناة من البحث.",
            "No channel is playing": "لا توجد قناة قيد التشغيل",
            "Recording started successfully": "بدأ التسجيل بنجاح",
            "Recording stopped successfully": "توقف التسجيل بنجاح",
            "Failed to load detailed series information": "فشل في تحميل معلومات المسلسل التفصيلية:",
            "Error fetching detailed series metadata": "خطأ في جلب البيانات الوصفية التفصيلية للمسلسل:",
            "Series ID is missing, cannot load details.": "معرف المسلسل مفقود، لا يمكن تحميل التفاصيل.",
            "Episode data not found.": "بيانات الحلقة غير موجودة.",
            "No trailer URL available for this series.": "لا يوجد رابط إعلان متاح لهذا المسلسل.",
            "No season selected to export.": "لم يتم تحديد موسم للتصدير.",
            "Series tab is not available.": "تبويب المسلسلات غير متاح.",
            "Movies tab is not available.": "تبويب الأفلام غير متاح.",
            "Live TV tab is not available.": "تبويب البث المباشر غير متاح.",
            "Account name cannot be empty.": "اسم الحساب لا يمكن أن يكون فارغاً.",
            "An account with the name": "حساب بالاسم",
            "already exists.": "موجود بالفعل.",
            "Failed to connect": "فشل في الاتصال:",
            "Categories": "الفئات",
            "All": "الكل",
            "Default": "افتراضي",
            "Date": "التاريخ",
            "Rating": "التقييم",
            "Name": "الاسم",
            "Channels": "القنوات",
            "Previous": "السابق",
            "Next": "التالي",
            "Page 1 of 1": "صفحة 1 من 1",
            "Back": "رجوع",
            "PLAY": "تشغيل",
            "Add to favorites": "إضافة للمفضلة",
            "Remove from favorites": "إزالة من المفضلة",
            "Cast": "طاقم التمثيل",
            "Export Season URLs": "تصدير روابط الموسم",
            "User": "المستخدم",
            "Subscription expires": "إنتهاء الاشتراك",
            "Password": "كلمة المرور:",
            "Remember credentials": "تذكر بيانات الاعتماد",
            "Save": "حفظ",
            "Cancel": "إلغاء",
            "Account Name": "اسم الحساب:",
            "Server URL": "رابط الخادم:",
            "Add Account": "إضافة حساب",
            "Edit Account": "تعديل الحساب",
            "e.g. My IPTV Account": "مثال: حساب IPTV الخاص بي",
            "http://example.com": "http://example.com",
            "Add/Edit Account": "إضافة/تعديل الحساب",
            "Account Management": "إدارة الحسابات",
            "← Back": "← رجوع",
            "Delete Account": "حذف الحساب",
            "Switch Account": "تبديل الحساب",
            "🎬 TRAILER": "🎬 المقطع الدعائي",
            "Director: ": "المخرج: ",
            "This category doesn't contain any Series": "هذه الفئة لا تحتوي على أي مسلسلات",
            "Episodes": "الحلقات",
            "Play": "تشغيل",
            "Desc": "تنازلي",
            "Loading cast...": "جاري تحميل طاقم التمثيل...",
            "No cast information available": "لا توجد معلومات عن طاقم التمثيل"
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
    # Set placeholder immediately
    set_pixmap(default_pixmap)
    if loading_counter is not None:
        loading_counter['count'] += 1
    threading.Thread(target=worker, daemon=True).start()
