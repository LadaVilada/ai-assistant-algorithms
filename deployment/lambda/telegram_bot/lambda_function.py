import json
import os
import logging

import sys

# Add the Lambda task root to Python path
sys.path.insert(0, os.environ['LAMBDA_TASK_ROOT'])
# Add the Lambda task root to Python path
sys.path.append('/var/task')

# from src.ai_assistant.bots.telegram.bot import TelegramAlgorithmsBot
from src.ai_assistant.core import LoggingConfig

# Setup basic logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = LoggingConfig.get_logger(__name__)

# Then try to set up more specific logging if the module is available
try:
    from src.ai_assistant.core import LoggingConfig
    logger = LoggingConfig.get_logger(__name__)
except ImportError:
    logger.info("Using basic logging configuration")

def lambda_handler(event, context):
    """
    Lambda handler specifically for Telegram bot
    """
    try:
        # Log incoming request (sanitized)
        logger.info(f"Received event type: {event.get('httpMethod', 'UNKNOWN')}")

        # Initialize Telegram bot
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")

        # Create bot using deferred import to avoid circular dependencies
        try:
            from src.ai_assistant.bots.telegram.bot import TelegramAlgorithmsBot
            bot = TelegramAlgorithmsBot(token)
            logger.info("Successfully created TelegramAlgorithmsBot")
        except ImportError as e:
            logger.error(f"Failed to import TelegramAlgorithmsBot: {e}")
            raise

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