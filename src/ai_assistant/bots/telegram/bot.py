import debugpy
# Allow remote connections
debugpy.listen(("0.0.0.0", 5678))

from typing import Dict, Any

from ai_assistant.bots.algorithms.bot import AlgorithmsBot
from ai_assistant.bots.telegram.base_telegram_bot import TelegramBot
from ai_assistant.core.utils.dependency_injector import DependencyInjector


def initialize_services() -> Dict[str, Any]:
    """
    Initialize core services using dependency injection.

    Returns:
        Dict[str, Any]: Dictionary containing initialized services:
            - 'rag': RAGService instance
            - 'llm': LLMService instance
    """
    try:
        # Get or create services
        embedding_service = DependencyInjector.get_service('embedding')
        vector_store = DependencyInjector.get_service('vector_store')
        document_loader = DependencyInjector.get_service('document')
        llm_service = DependencyInjector.get_service('llm')

        # Create RAG service with dependencies
        rag_service = DependencyInjector.get_service('rag',
                                                     loader=document_loader,
                                                     embedding_generator=embedding_service,
                                                     vector_store=vector_store
                                                     )

        # logger.info("Successfully initialized all services")
        return {
            'rag': rag_service,
            'llm': llm_service
        }
    except Exception as e:
        # logger.error(f"Failed to initialize services: {e}")
        raise

class TelegramAlgorithmsBot:
    """Telegram bot implementation for algorithm queries using composition pattern."""
    
    def __init__(self, token: str):
        """
        Initialize the Telegram bot with an algorithms bot.
        
        Args:
            token: Telegram bot token
        """

        # Initialize services
        services = initialize_services()

        # Create the underlying algorithms bot
        self.algorithms_bot = AlgorithmsBot(services['rag'], services['llm'])

        # Create the Telegram bot wrapper
        self.telegram_bot = TelegramBot(token, self.algorithms_bot)

    def run(self):
        """Run the Telegram bot."""
        self.telegram_bot.run()

    def handle_lambda_event(self, event, context):
        """Handle Lambda events."""
        return self.telegram_bot.handle_lambda_event(event, context)

    def process_query(self, query: str) -> Dict[str, Any]:
        """
            Process a Telegram message query

            Delegates to AlgorithmsBot for processing
        """
        return self.algorithms_bot.process_query(query)