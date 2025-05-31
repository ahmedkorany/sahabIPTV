"""Image service for centralized image loading and caching"""
import os
import threading
from typing import Callable, Optional, Tuple
from PyQt5.QtCore import QObject, pyqtSignal, QMetaObject, Qt, Q_ARG
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QLabel

from src.utils.image_cache import ImageCache
from src.constants import UIConstants, FileConstants


class ImageLoadingController(QObject):
    """Controls loading indicator for image operations"""
    show_loading = pyqtSignal()
    hide_loading = pyqtSignal()
    
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        self.loading_count = 0
        self._setup_connections()
    
    def _setup_connections(self):
        """Setup signal connections"""
        if self.main_window and hasattr(self.main_window, 'loading_icon_controller'):
            self.show_loading.connect(self.main_window.loading_icon_controller.show_icon)
            self.hide_loading.connect(self.main_window.loading_icon_controller.hide_icon)
    
    def increment_loading(self):
        """Increment loading counter and show indicator"""
        self.loading_count += 1
        if self.loading_count == 1:
            self.show_loading.emit()
    
    def decrement_loading(self):
        """Decrement loading counter and hide indicator when done"""
        self.loading_count = max(0, self.loading_count - 1)
        if self.loading_count == 0:
            self.hide_loading.emit()


class ImageService:
    """Service for handling image loading and caching operations"""
    
    def __init__(self, api_client=None, loading_controller: Optional[ImageLoadingController] = None):
        self.api_client = api_client
        self.loading_controller = loading_controller
        self._ensure_cache_directory()
    
    def _ensure_cache_directory(self):
        """Ensure image cache directory exists"""
        ImageCache.ensure_cache_dir()
    
    def load_image_async(
        self,
        image_url: str,
        label: QLabel,
        default_pixmap: QPixmap,
        size: Tuple[int, int] = UIConstants.IMAGE_SIZE,
        callback: Optional[Callable] = None
    ):
        """Load image asynchronously with caching
        
        Args:
            image_url: URL of the image to load
            label: QLabel to display the image
            default_pixmap: Default image to show while loading
            size: Target size for the image
            callback: Optional callback when loading completes
        """
        cache_path = ImageCache.get_cache_path(image_url)
        
        # Set cached image immediately if available
        if os.path.exists(cache_path):
            self._set_cached_image(label, cache_path, size)
        else:
            self._set_placeholder_image(label, default_pixmap, size)
            self._load_image_from_network(image_url, label, default_pixmap, size, callback)
    
    def _set_cached_image(self, label: QLabel, cache_path: str, size: Tuple[int, int]):
        """Set cached image on label"""
        pixmap = QPixmap()
        if pixmap.load(cache_path):
            self._apply_pixmap_to_label(label, pixmap, size)
    
    def _set_placeholder_image(self, label: QLabel, default_pixmap: QPixmap, size: Tuple[int, int]):
        """Set placeholder image on label"""
        self._apply_pixmap_to_label(label, default_pixmap, size)
    
    def _apply_pixmap_to_label(self, label: QLabel, pixmap: QPixmap, size: Tuple[int, int]):
        """Apply scaled pixmap to label"""
        scaled_pixmap = pixmap.scaled(
            *size, 
            Qt.KeepAspectRatio, 
            Qt.SmoothTransformation
        )
        label.setPixmap(scaled_pixmap)
    
    def _load_image_from_network(
        self, 
        image_url: str, 
        label: QLabel, 
        default_pixmap: QPixmap, 
        size: Tuple[int, int],
        callback: Optional[Callable] = None
    ):
        """Load image from network in background thread"""
        if self.loading_controller:
            self.loading_controller.increment_loading()
        
        def worker():
            try:
                pixmap = self._download_and_cache_image(image_url)
                if pixmap.isNull():
                    pixmap = default_pixmap
                
                # Update UI on main thread
                QMetaObject.invokeMethod(
                    label, 
                    "setPixmap", 
                    Qt.QueuedConnection,
                    Q_ARG(QPixmap, pixmap.scaled(*size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                )
                
                if callback:
                    callback(pixmap)
                    
            except Exception as e:
                print(f"Error loading image {image_url}: {e}")
            finally:
                if self.loading_controller:
                    self.loading_controller.decrement_loading()
        
        threading.Thread(target=worker, daemon=True).start()
    
    def _download_and_cache_image(self, image_url: str) -> QPixmap:
        """Download image and save to cache"""
        cache_path = ImageCache.get_cache_path(image_url)
        pixmap = QPixmap()
        
        try:
            if self.api_client:
                image_data = self.api_client.get_image_data(image_url)
                if image_data and pixmap.loadFromData(image_data):
                    pixmap.save(cache_path)
                    return pixmap
        except Exception as e:
            print(f"Error downloading image {image_url}: {e}")
        
        return pixmap
    
    def clear_cache(self):
        """Clear image cache"""
        cache_dir = ImageCache.CACHE_DIR
        if os.path.exists(cache_dir):
            for filename in os.listdir(cache_dir):
                if filename.endswith(FileConstants.IMAGE_CACHE_EXTENSION):
                    try:
                        os.remove(os.path.join(cache_dir, filename))
                    except Exception as e:
                        print(f"Error removing cached image {filename}: {e}")
    
    def get_cache_size(self) -> int:
        """Get total size of image cache in bytes"""
        cache_dir = ImageCache.CACHE_DIR
        total_size = 0
        
        if os.path.exists(cache_dir):
            for filename in os.listdir(cache_dir):
                if filename.endswith(FileConstants.IMAGE_CACHE_EXTENSION):
                    try:
                        file_path = os.path.join(cache_dir, filename)
                        total_size += os.path.getsize(file_path)
                    except Exception:
                        continue
        
        return total_size