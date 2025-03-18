from typing import Dict, Any
from telegram import Update
from telegram.ext import ContextTypes
from ai_assistant.bots.telegram.base_telegram_bot import TelegramBot
from ai_assistant.bots.algorithms.bot import AlgorithmsBot

class TelegramAlgorithmsBot:
    """Telegram bot implementation for algorithm queries using composition pattern."""
    
    def __init__(self, token: str):
        """
        Initialize the Telegram bot with an algorithms bot.
        
        Args:
            token: Telegram bot token
        """
        # Create the underlying algorithms bot
        self.algorithms_bot = AlgorithmsBot()
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
                                                                                                                                                                                                                           