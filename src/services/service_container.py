"""Service container for dependency injection"""
from typing import Dict, Any, Type, TypeVar, Optional

T = TypeVar('T')


class ServiceContainer:
    """Container for managing service instances and dependencies"""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._singletons: Dict[str, Any] = {}
        self._factories: Dict[str, callable] = {}
    
    def register_singleton(self, service_type: Type[T], instance: T) -> None:
        """Register a singleton service instance
        
        Args:
            service_type: Type of the service
            instance: Service instance
        """
        service_name = self._get_service_name(service_type)
        self._singletons[service_name] = instance
    
    def register_factory(self, service_type: Type[T], factory: callable) -> None:
        """Register a factory function for creating service instances
        
        Args:
            service_type: Type of the service
            factory: Factory function that creates the service
        """
        service_name = self._get_service_name(service_type)
        self._factories[service_name] = factory
    
    def register_transient(self, service_type: Type[T], implementation: Type[T]) -> None:
        """Register a transient service (new instance each time)
        
        Args:
            service_type: Type of the service interface
            implementation: Implementation type
        """
        service_name = self._get_service_name(service_type)
        self._factories[service_name] = lambda: implementation()
    
    def get(self, service_type: Type[T]) -> Optional[T]:
        """Get service instance
        
        Args:
            service_type: Type of the service to retrieve
            
        Returns:
            Service instance or None if not found
        """
        service_name = self._get_service_name(service_type)
        
        # Check singletons first
        if service_name in self._singletons:
            return self._singletons[service_name]
        
        # Check factories
        if service_name in self._factories:
            return self._factories[service_name]()
        
        # Check if already instantiated
        if service_name in self._services:
            return self._services[service_name]
        
        return None
    
    def get_or_create(self, service_type: Type[T], *args, **kwargs) -> T:
        """Get existing service or create new instance
        
        Args:
            service_type: Type of the service
            *args: Arguments for service constructor
            **kwargs: Keyword arguments for service constructor
            
        Returns:
            Service instance
        """
        service = self.get(service_type)
        if service is None:
            service = service_type(*args, **kwargs)
            self.register_singleton(service_type, service)
        return service
    
    def has(self, service_type: Type[T]) -> bool:
        """Check if service is registered
        
        Args:
            service_type: Type of the service
            
        Returns:
            True if service is registered, False otherwise
        """
        service_name = self._get_service_name(service_type)
        return (service_name in self._singletons or 
                service_name in self._factories or 
                service_name in self._services)
    
    def remove(self, service_type: Type[T]) -> bool:
        """Remove service from container
        
        Args:
            service_type: Type of the service to remove
            
        Returns:
            True if service was removed, False if not found
        """
        service_name = self._get_service_name(service_type)
        removed = False
        
        if service_name in self._singletons:
            del self._singletons[service_name]
            removed = True
        
        if service_name in self._factories:
            del self._factories[service_name]
            removed = True
        
        if service_name in self._services:
            del self._services[service_name]
            removed = True
        
        return removed
    
    def clear(self) -> None:
        """Clear all registered services"""
        self._services.clear()
        self._singletons.clear()
        self._factories.clear()
    
    def get_registered_services(self) -> Dict[str, str]:
        """Get list of all registered services
        
        Returns:
            Dictionary mapping service names to their types
        """
        services = {}
        
        for service_name in self._singletons.keys():
            services[service_name] = 'singleton'
        
        for service_name in self._factories.keys():
            services[service_name] = 'factory'
        
        for service_name in self._services.keys():
            services[service_name] = 'instance'
        
        return services
    
    def _get_service_name(self, service_type: Type[T]) -> str:
        """Get service name from type
        
        Args:
            service_type: Service type
            
        Returns:
            Service name string
        """
        return f"{service_type.__module__}.{service_type.__name__}"


class ServiceLocator:
    """Global service locator for accessing the service container"""
    
    _container: Optional[ServiceContainer] = None
    
    @classmethod
    def set_container(cls, container: ServiceContainer) -> None:
        """Set the global service container
        
        Args:
            container: Service container instance
        """
        cls._container = container
    
    @classmethod
    def get_container(cls) -> ServiceContainer:
        """Get the global service container
        
        Returns:
            Service container instance
        """
        if cls._container is None:
            cls._container = ServiceContainer()
        return cls._container
    
    @classmethod
    def get_service(cls, service_type: Type[T]) -> Optional[T]:
        """Get service from global container
        
        Args:
            service_type: Type of service to retrieve
            
        Returns:
            Service instance or None if not found
        """
        return cls.get_container().get(service_type)
    
    @classmethod
    def register_singleton(cls, service_type: Type[T], instance: T) -> None:
        """Register singleton in global container
        
        Args:
            service_type: Type of the service
            instance: Service instance
        """
        cls.get_container().register_singleton(service_type, instance)
    
    @classmethod
    def register_factory(cls, service_type: Type[T], factory: callable) -> None:
        """Register factory in global container
        
        Args:
            service_type: Type of the service
            factory: Factory function
        """
        cls.get_container().register_factory(service_type, factory)


def configure_services() -> ServiceContainer:
    """Configure and return the application service container
    
    Returns:
        Configured service container
    """
    from src.services.image_service import ImageService, ImageLoadingController
    from src.services.cache_manager import CacheManager, XtreamCacheManager
    from src.services.media_service import MediaService, RecordingService
    from src.utils.favorites_manager import FavoritesManager
    from src.config import CACHE_DIR
    import os
    
    container = ServiceContainer()
    
    # Register cache managers
    cache_dir = os.path.join(CACHE_DIR, 'data')
    cache_manager = CacheManager(cache_dir)
    xtream_cache_manager = XtreamCacheManager(cache_dir)
    
    container.register_singleton(CacheManager, cache_manager)
    container.register_singleton(XtreamCacheManager, xtream_cache_manager)
    
    # Register services with factories
    container.register_factory(
        ImageService, 
        lambda: ImageService()
    )
    
    container.register_factory(
        MediaService,
        lambda: MediaService()
    )
    
    container.register_factory(
        RecordingService,
        lambda: RecordingService()
    )
    
    container.register_factory(
        ImageLoadingController,
        lambda: ImageLoadingController()
    )
    
    return container