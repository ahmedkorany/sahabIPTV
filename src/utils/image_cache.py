import os
import hashlib

CACHE_DIR = 'assets/cache/'

def ensure_cache_dir():
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

def get_cache_path(image_url_or_id):
    h = hashlib.md5(str(image_url_or_id).encode('utf-8')).hexdigest()
    return f"{CACHE_DIR}{h}.jpg"  # Use .jpg for Qt compatibility
