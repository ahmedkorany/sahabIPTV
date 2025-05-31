#!/usr/bin/env python3
import os
import time
import pickle
import hashlib
from typing import Any, Optional

from src.constants import CacheConstants, ErrorMessages


class CacheManager:
    """Manages caching operations for the application"""
    
    def __init__(self, cache_directory: str):
        self.cache_directory = cache_directory
        self._ensure_cache_directory()
    
    def _ensure_cache_directory(self):
        """Ensure cache directory exists"""
        if not os.path.exists(self.cache_directory):
            os.makedirs(self.cache_directory)
    
    def _get_cache_path(self, key: str) -> str:
        """Get cache file path for a given key"""
        key_hash = hashlib.md5(key.encode('utf-8')).hexdigest()
        return os.path.join(self.cache_directory, f"cache_{key_hash}.pkl")
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value by key
        
        Args:
            key: Cache key
            
        Returns:
            Cached value if exists and not expired, None otherwise
        """
        cache_path = self._get_cache_path(key)
        
        if not os.path.exists(cache_path):
            return None
        
        try:
            with open(cache_path, 'rb') as f:
                data = pickle.load(f)
            
            if self._is_cache_expired(data['timestamp']):
                self._remove_cache_file(cache_path)
                return None
            
            return data['value']
            
        except Exception as e:
            print(ErrorMessages.CACHE_LOAD_ERROR.format(e))
            self._remove_cache_file(cache_path)
            return None
    
    def set(self, key: str, value: Any) -> bool:
        """Set cached value by key
        
        Args:
            key: Cache key
            value: Value to cache
            
        Returns:
            True if successfully cached, False otherwise
        """
        cache_path = self._get_cache_path(key)
        
        try:
            cache_data = {
                'timestamp': time.time(),
                'value': value
            }
            
            with open(cache_path, 'wb') as f:
                pickle.dump(cache_data, f)
            
            return True
            
        except Exception as e:
            print(ErrorMessages.CACHE_SAVE_ERROR.format(e))
            return False
    
    def delete(self, key: str) -> bool:
        """Delete cached value by key
        
        Args:
            key: Cache key
            
        Returns:
            True if successfully deleted, False otherwise
        """
        cache_path = self._get_cache_path(key)
        return self._remove_cache_file(cache_path)
    
    def clear(self) -> bool:
        """Clear all cached values
        
        Returns:
            True if successfully cleared, False otherwise
        """
        try:
            for filename in os.listdir(self.cache_directory):
                if filename.startswith('cache_') and filename.endswith('.pkl'):
                    file_path = os.path.join(self.cache_directory, filename)
                    os.remove(file_path)
            return True
            
        except Exception as e:
            print(f"Error clearing cache: {e}")
            return False
    
    def cleanup_expired(self) -> int:
        """Remove expired cache entries
        
        Returns:
            Number of entries removed
        """
        removed_count = 0
        
        try:
            for filename in os.listdir(self.cache_directory):
                if filename.startswith('cache_') and filename.endswith('.pkl'):
                    file_path = os.path.join(self.cache_directory, filename)
                    
                    try:
                        with open(file_path, 'rb') as f:
                            data = pickle.load(f)
                        
                        if self._is_cache_expired(data['timestamp']):
                            os.remove(file_path)
                            removed_count += 1
                            
                    except Exception:
                        # Remove corrupted cache files
                        os.remove(file_path)
                        removed_count += 1
                        
        except Exception as e:
            print(f"Error during cache cleanup: {e}")
        
        return removed_count
    
    def get_cache_info(self) -> dict:
        """Get cache statistics
        
        Returns:
            Dictionary with cache statistics
        """
        total_files = 0
        total_size = 0
        expired_files = 0
        
        try:
            for filename in os.listdir(self.cache_directory):
                if filename.startswith('cache_') and filename.endswith('.pkl'):
                    file_path = os.path.join(self.cache_directory, filename)
                    total_files += 1
                    
                    try:
                        total_size += os.path.getsize(file_path)
                        
                        with open(file_path, 'rb') as f:
                            data = pickle.load(f)
                        
                        if self._is_cache_expired(data['timestamp']):
                            expired_files += 1
                            
                    except Exception:
                        expired_files += 1
                        
        except Exception as e:
            print(f"Error getting cache info: {e}")
        
        return {
            'total_files': total_files,
            'total_size_bytes': total_size,
            'expired_files': expired_files,
            'cache_directory': self.cache_directory
        }
    
    def _is_cache_expired(self, timestamp: float) -> bool:
        """Check if cache entry is expired
        
        Args:
            timestamp: Cache entry timestamp
            
        Returns:
            True if expired, False otherwise
        """
        return time.time() - timestamp > CacheConstants.EXPIRATION_SECONDS
    
    def _remove_cache_file(self, cache_path: str) -> bool:
        """Remove cache file safely
        
        Args:
            cache_path: Path to cache file
            
        Returns:
            True if successfully removed, False otherwise
        """
        try:
            if os.path.exists(cache_path):
                os.remove(cache_path)
            return True
        except Exception as e:
            print(f"Error removing cache file {cache_path}: {e}")
            return False


class XtreamCacheManager(CacheManager):
    """Specialized cache manager for Xtream API data"""
    
    def get_live_categories_key(self, server_url: str, username: str) -> str:
        """Get cache key for live categories"""
        return f'live_categories_{server_url}_{username}'
    
    def get_vod_categories_key(self, server_url: str, username: str) -> str:
        """Get cache key for VOD categories"""
        return f'vod_categories_{server_url}_{username}'
    
    def get_series_categories_key(self, server_url: str, username: str) -> str:
        """Get cache key for series categories"""
        return f'series_categories_{server_url}_{username}'
    
    def get_live_streams_key(self, server_url: str, username: str, category_id: str) -> str:
        """Get cache key for live streams"""
        return f'live_streams_{server_url}_{username}_{category_id}'
    
    def get_vod_streams_key(self, server_url: str, username: str, category_id: str) -> str:
        """Get cache key for VOD streams"""
        return f'vod_streams_{server_url}_{username}_{category_id}'
    
    def get_series_key(self, server_url: str, username: str, category_id: str) -> str:
        """Get cache key for series"""
        return f'series_{server_url}_{username}_{category_id}'
    
    def update_stream_in_category(self, cache_key: str, stream_id: str, updated_data: dict) -> bool:
        """Update a specific stream within a cached category list
        
        Args:
            cache_key: Cache key for the category
            stream_id: ID of the stream to update
            updated_data: New data for the stream
            
        Returns:
            True if successfully updated, False otherwise
        """
        cached_streams = self.get(cache_key)
        
        if not isinstance(cached_streams, list):
            return False
        
        for i, stream in enumerate(cached_streams):
            if isinstance(stream, dict) and stream.get('stream_id') == stream_id:
                # Update the stream data
                cached_streams[i].update(updated_data)
                return self.set(cache_key, cached_streams)
        
        return False
    
    def update_series_in_category(self, cache_key: str, series_id: str, updated_data: dict) -> bool:
        """Update a specific series within a cached category list
        
        Args:
            cache_key: Cache key for the category
            series_id: ID of the series to update
            updated_data: New data for the series
            
        Returns:
            True if successfully updated, False otherwise
        """
        cached_series = self.get(cache_key)
        
        if not isinstance(cached_series, list):
            return False
        
        for i, series in enumerate(cached_series):
            if isinstance(series, dict) and series.get('series_id') == series_id:
                # Update the series data
                cached_series[i].update(updated_data)
                return self.set(cache_key, cached_series)
        
        return False
    
    def clear_all(self) -> bool:
        """Clear all cached values (alias for clear method)
        
        Returns:
            True if successfully cleared, False otherwise
        """
        return self.clear()