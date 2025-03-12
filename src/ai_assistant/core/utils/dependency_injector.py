from ai_assistant.core import RAGService, LLMService, EmbeddingService


class DependencyInjector:
    @staticmethod
    def get_service(service_type, **kwargs):
        services = {
            'rag': RAGService,
            'llm': LLMService,
            'embedding': EmbeddingService
        }
        return services.get(service_type)(**kwargs)