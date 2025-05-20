import os
import hashlib

class ImageCache:
    CACHE_DIR = 'assets/cache/images/'

    @staticmethod
    def ensure_cache_dir():
        if not os.path.exists(ImageCache.CACHE_DIR):
            os.makedirs(ImageCache.CACHE_DIR)

    @staticmethod
    def get_cache_path(image_url_or_id):
        h = hashlib.md5(str(image_url_or_id).encode('utf-8')).hexdigest()
        return f"{ImageCache.CACHE_DIR}{h}.jpg"  # Use .jpg for Qt compatibility
