import json
import logging
import os
import sys
from typing import Dict, Any

# Add the Lambda task root to Python path
sys.path.insert(0, os.environ['LAMBDA_TASK_ROOT'])
sys.path.append('/var/task')

from src.ai_assistant.core import LoggingConfig
from src.ai_assistant.core.utils.dependency_injector import DependencyInjector
from src.ai_assistant.bots.algorithms.bot import AlgorithmsBot
from src.ai_assistant.bots.telegram.base_telegram_bot import TelegramBot

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = LoggingConfig.get_logger(__name__)

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
        
        logger.info("Successfully initialized all services")
        return {
            'rag': rag_service,
            'llm': llm_service
        }
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise

def create_bot(token: str) -> TelegramBot:
    """Create and configure the Telegram bot with its dependencies."""
    try:
        # Initialize services
        services = initialize_services()
        
        # Create algorithms bot
        algorithms_bot = AlgorithmsBot(services['rag'], services['llm'])
        logger.info("Created AlgorithmsBot")
        
        # Create Telegram bot with algorithms bot
        telegram_bot = TelegramBot(token, algorithms_bot)
        logger.info("Created TelegramBot")
        
        return telegram_bot
    except Exception as e:
        logger.error(f"Failed to create bot: {e}")
        raise

def lambda_handler(event, context):
    """
    Lambda handler for Telegram bot using composition pattern
    """
    try:
        # Log incoming request (sanitized)
        logger.info(f"Received event type: {event.get('httpMethod', 'UNKNOWN')}")

        # Get Telegram token
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")

        # Create bot using the new composition pattern
        bot = create_bot(token)
        
        # Process the event
        response = bot.handle_lambda_event(event, context)

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps(response)
        }

    except ValueError as ve:
        logger.error(f"Configuration error: {ve}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Configuration error',
                'details': str(ve)
            })
        }
    except Exception as e:
        logger.error(f"Error in Telegram bot Lambda: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error',
                'details': str(e)
            })
        }