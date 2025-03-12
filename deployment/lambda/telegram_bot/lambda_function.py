import json
import os
import logging
import requests
from typing import Dict, Any

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class TelegramBot:
    def __init__(self, token):
        self.token = token
        self.api_base = f"https://api.telegram.org/bot{token}"

    def send_message(self, chat_id, text):
        """Send a message to a Telegram chat"""
        url = f"{self.api_base}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }

        try:
            response = requests.post(url, json=payload)
            return response.json()
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return None

    def process_message(self, message: Dict[str, Any]):
        """Process an incoming message"""
        chat_id = message.get('chat', {}).get('id')
        if not chat_id:
            logger.error("No chat ID found in message")
            return

        # Extract message text if present
        text = message.get('text', '')
        if not text:
            self.send_message(chat_id, "I can only process text messages.")
            return

        logger.info(f"Processing message: {text}")

        # Simple echo response for now
        response_text = f"Echo: {text}\n\nI'm a temporary version of the bot while debugging."
        self.send_message(chat_id, response_text)

    def handle_update(self, update: Dict[str, Any]):
        """Handle a Telegram update"""
        # Process message if present
        if 'message' in update:
            self.process_message(update['message'])
            return True

        return False

def lambda_handler(event, context):
    """AWS Lambda handler for Telegram webhook"""
    try:
        logger.info(f"Received event: {json.dumps(event)}")

        # Get token from environment variable
        token = os.environ.get('TELEGRAM_BOT_TOKEN')
        if not token:
            logger.error("No Telegram bot token provided")
            return {
                'statusCode': 200,  # Return 200 to Telegram
                'body': json.dumps({'error': 'Configuration error'})
            }

        # Initialize bot
        bot = TelegramBot(token)

        # Parse request body from API Gateway
        if 'body' in event:
            try:
                body = json.loads(event['body'])
                logger.info(f"Update received: {json.dumps(body)}")

                # Process the update
                bot.handle_update(body)

            except json.JSONDecodeError as e:
                logger.error(f"Error parsing request body: {e}")

        # Return success response
        return {
            'statusCode': 200,
            'body': json.dumps({'ok': True})
        }

    except Exception as e:
        logger.error(f"Error in Lambda handler: {e}", exc_info=True)
        # Still return 200 to prevent Telegram from retrying
        return {
            'statusCode': 200,
            'body': json.dumps({'ok': False, 'error': str(e)})
        }