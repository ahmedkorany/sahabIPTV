#!/usr/bin/env python3
"""
Favorites Manager Utility

Centralized favorites management for the IPTV application.
Handles adding, removing, checking, saving, and loading favorites.
"""

import os
from typing import List, Dict, Any, Optional
from PyQt5.QtCore import QObject, pyqtSignal
from src.utils.helpers import load_json_file, save_json_file
from src.config import FAVORITES_FILE


class FavoritesManager(QObject):
    """Centralized favorites management class"""
    
    # Signals
    favorites_changed = pyqtSignal()  # Emitted when favorites list changes
    item_added = pyqtSignal(dict)     # Emitted when an item is added
    item_removed = pyqtSignal(dict)   # Emitted when an item is removed
    
    def __init__(self, current_account: str = ""):
        super().__init__()
        self.current_account = current_account
        self.favorites_by_account: Dict[str, List[Dict[str, Any]]] = {}
        self.favorites: List[Dict[str, Any]] = []
        self.load_favorites()
    
    def set_current_account(self, account_name: str) -> None:
        """Set the current account and load its favorites"""
        if self.current_account != account_name:
            # Save current account's favorites before switching
            if self.current_account:
                self.save_favorites()
            
            self.current_account = account_name
            self.load_favorites()
    
    def load_favorites(self) -> None:
        """Load favorites from file for the current account"""
        try:
            data = load_json_file(FAVORITES_FILE)
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
            print(f"Failed to load favorites: {e}. Favorites will be reset.")
            self.favorites_by_account = {}
            self.favorites = []
        
        self.favorites_changed.emit()
    
    def save_favorites(self) -> None:
        """Save favorites to file, keyed by account"""
        if not self.current_account:
            return
        
        self.favorites_by_account[self.current_account] = self.favorites
        try:
            save_json_file(FAVORITES_FILE, self.favorites_by_account)
        except Exception as e:
            print(f"Failed to save favorites: {e}")
    
    def add_to_favorites(self, item: Dict[str, Any]) -> bool:
        """Add an item to favorites for the current account
        
        Args:
            item: Dictionary containing item data with required keys:
                  - stream_type: 'movie', 'series', or 'live'
                  - stream_id or series_id: unique identifier
                  - name: display name
        
        Returns:
            bool: True if item was added, False if already exists
        """
        if self.is_favorite(item):
            return False
        
        # Ensure required fields are present
        if not self._validate_item(item):
            print(f"Warning: Invalid item data for favorites: {item}")
            return False
        
        self.favorites.append(item)
        self.save_favorites()
        self.item_added.emit(item)
        self.favorites_changed.emit()
        return True
    
    def remove_from_favorites(self, item: Dict[str, Any]) -> bool:
        """Remove an item from favorites for the current account
        
        Args:
            item: Dictionary containing item data to remove
        
        Returns:
            bool: True if item was removed, False if not found
        """
        found_index = self._find_item_index(item)
        
        if found_index != -1:
            removed_item = self.favorites.pop(found_index)
            self.save_favorites()
            self.item_removed.emit(removed_item)
            self.favorites_changed.emit()
            return True
        
        return False
    
    def toggle_favorite(self, item: Dict[str, Any]) -> bool:
        """Toggle an item's favorite status
        
        Args:
            item: Dictionary containing item data
        
        Returns:
            bool: True if item is now a favorite, False if removed
        """
        if self.is_favorite(item):
            self.remove_from_favorites(item)
            return False
        else:
            self.add_to_favorites(item)
            return True
    
    def is_favorite(self, item: Dict[str, Any]) -> bool:
        """Check if an item is in favorites for the current account
        
        Args:
            item: Dictionary containing item data to check
        
        Returns:
            bool: True if item is in favorites, False otherwise
        """
        return self._find_item_index(item) != -1
    
    def get_favorites(self) -> List[Dict[str, Any]]:
        """Get the current list of favorites
        
        Returns:
            List of favorite items for the current account
        """
        return self.favorites.copy()
    
    def get_favorites_by_type(self, stream_type: str) -> List[Dict[str, Any]]:
        """Get favorites filtered by stream type
        
        Args:
            stream_type: 'movie', 'series', or 'live'
        
        Returns:
            List of favorite items of the specified type
        """
        return [item for item in self.favorites if item.get('stream_type') == stream_type]
    
    def clear_favorites(self) -> None:
        """Clear all favorites for the current account"""
        self.favorites.clear()
        self.save_favorites()
        self.favorites_changed.emit()
    
    def get_favorites_count(self) -> int:
        """Get the total number of favorites
        
        Returns:
            Number of items in favorites
        """
        return len(self.favorites)
    
    def _find_item_index(self, item: Dict[str, Any]) -> int:
        """Find the index of an item in favorites list
        
        Args:
            item: Dictionary containing item data to find
        
        Returns:
            int: Index of item if found, -1 otherwise
        """
        item_type = item.get('stream_type')
        item_id = self._get_item_id(item)
        
        if item_id is None:
            return -1
        
        for i, fav_item in enumerate(self.favorites):
            fav_type = fav_item.get('stream_type')
            fav_id = self._get_item_id(fav_item)
            
            if fav_type == item_type and fav_id == item_id and fav_id is not None:
                return i
        
        return -1
    
    def _get_item_id(self, item: Dict[str, Any]) -> Optional[Any]:
        """Extract the unique identifier from an item
        
        Args:
            item: Dictionary containing item data
        
        Returns:
            The unique identifier or None if not found
        """
        item_type = item.get('stream_type')
        
        if item_type == 'series':
            return item.get('series_id')
        elif item_type in ['movie', 'live']:
            return item.get('stream_id')
        else:
            # Fallback: try to find any ID
            return (item.get('stream_id') or 
                   item.get('series_id') or 
                   item.get('id'))
    
    def _validate_item(self, item: Dict[str, Any]) -> bool:
        """Validate that an item has required fields for favorites
        
        Args:
            item: Dictionary containing item data
        
        Returns:
            bool: True if item is valid, False otherwise
        """
        if not isinstance(item, dict):
            return False
        
        # Check for required fields
        if 'stream_type' not in item:
            return False
        
        if 'name' not in item:
            return False
        
        # Check for appropriate ID field
        item_id = self._get_item_id(item)
        if item_id is None:
            return False
        
        return True