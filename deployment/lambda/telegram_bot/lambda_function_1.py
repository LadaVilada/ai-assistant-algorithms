import json
import os

from ai_assistant.core.utils.logging import LoggingConfig
from ai_assistant.bots.telegram.bot import TelegramAlgorithmsBot

logger = LoggingConfig.get_logger(__name__)

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

        bot = TelegramAlgorithmsBot(token)

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