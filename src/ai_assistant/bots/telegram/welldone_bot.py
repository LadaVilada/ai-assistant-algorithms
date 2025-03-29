from typing import Dict, Any, Optional

from ai_assistant.bots.telegram.base_telegram_bot import TelegramBot
from ai_assistant.bots.welldone.bot import WellDoneBot
from ai_assistant.core import DependencyInjector


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
        speech_service = DependencyInjector.get_service('speech')

        # Create RAG service with dependencies
        rag_service = DependencyInjector.get_service('rag',
                                                     loader=document_loader,
                                                     embedding_generator=embedding_service,
                                                     vector_store=vector_store
                                                     )

        # logger.info("Successfully initialized all services")
        return {
            'rag': rag_service,
            'llm': llm_service,
            'speech': speech_service
        }
    except Exception as e:
        # logger.error(f"Failed to initialize services: {e}")
        raise


class TelegramWellDoneBot:


    def __init__(self, token: str):

        """
      Initialize the Telegram bot with an algorithms bot.

      Args:
          token: Telegram bot token
      """

        # Initialize services
        services = initialize_services()

        # Create the underlying algorithms bot
        self.welldone_bot = WellDoneBot(services['rag'], services['llm'])

        # Create the Telegram bot wrapper
        self.telegram_bot = TelegramBot(token, self.welldone_bot)


    def run(self):
        self.telegram_bot.run()

    def process_query(self, query: str, user_name: Optional[str] = None) -> Dict[str, Any]:
        return self.welldone_bot.process_query(query, user_name)

