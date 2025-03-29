from typing import Dict, Any, Optional
from ai_assistant.core import RAGService, LLMService, EmbeddingService, DocumentService, VectorStore, SpeechService
from ai_assistant.core.utils.logging import LoggingConfig

class DependencyInjector:
    """Dependency injection container for managing services."""
    
    _services: Dict[str, Any] = {}
    _logger = LoggingConfig.get_logger(__name__)

    @classmethod
    def get_service(cls, service_type: str, **kwargs) -> Any:
        """
        Get a service instance, creating it if it doesn't exist.
        
        Args:
            service_type: Type of service to get
            **kwargs: Additional arguments for service creation
            
        Returns:
            Service instance
        """
        if service_type not in cls._services:
            cls._services[service_type] = cls._create_service(service_type, **kwargs)
        return cls._services[service_type]

    @classmethod
    def _create_service(cls, service_type: str, **kwargs) -> Any:
        """Create a new service instance."""
        services = {
            'rag': RAGService,
            'llm': LLMService,
            'embedding': EmbeddingService,
            'document': DocumentService,
            'vector_store': VectorStore,
            'speech': SpeechService
        }
        
        service_class = services.get(service_type)
        if not service_class:
            raise ValueError(f"Unknown service type: {service_type}")
            
        cls._logger.info(f"Creating new {service_type} service")
        return service_class(**kwargs)

    @classmethod
    def get_all_services(cls) -> Dict[str, Any]:
        """Get all registered services."""
        return cls._services.copy()

    @classmethod
    def clear_services(cls):
        """Clear all registered services."""
        cls._services.clear()
        cls._logger.info("Cleared all services")

    @classmethod
    def register_service(cls, service_type: str, service: Any):
        """Register a service instance."""
        cls._services[service_type] = service
        cls._logger.info(f"Registered {service_type} service")