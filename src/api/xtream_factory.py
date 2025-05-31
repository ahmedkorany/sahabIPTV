"""Factory for creating XtreamClient instances with proper dependencies"""
import os
from typing import Optional

from .xtream import XtreamClient
from src.services.cache_manager import XtreamCacheManager
from src.services.service_container import ServiceLocator


class XtreamClientFactory:
    """Factory for creating XtreamClient instances with proper dependencies"""
    
    @staticmethod
    def create_client(cache_manager: Optional[XtreamCacheManager] = None) -> XtreamClient:
        """Create a new XtreamClient instance with dependencies
        
        Args:
            cache_manager: Optional cache manager. If None, will try to get from service container
            
        Returns:
            Configured XtreamClient instance
        """
        if cache_manager is None:
            try:
                service_locator = ServiceLocator.get_instance()
                cache_manager = service_locator.get('xtream_cache_manager')
            except Exception:
                # If service container is not available, create a default cache manager
                cache_dir = os.path.expanduser('~/.sahab_iptv/cache')
                cache_manager = XtreamCacheManager(cache_dir)
        
        return XtreamClient(cache_manager=cache_manager)
    
    @staticmethod
    def create_client_without_cache() -> XtreamClient:
        """Create a new XtreamClient instance without caching
        
        Returns:
            XtreamClient instance without cache manager
        """
        return XtreamClient(cache_manager=None)