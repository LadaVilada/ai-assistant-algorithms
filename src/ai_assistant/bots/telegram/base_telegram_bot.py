import asyncio
import json
from typing import Dict, Any

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from ai_assistant.bots.base.base_bot import BaseBot
from ai_assistant.core.utils.logging import LoggingConfig

# Define conversation states
AWAITING_QUERY = 1

class TelegramBot:
    """Base class for Telegram bot implementations using composition pattern."""
    
    def __init__(self, token: str, underlying_bot: BaseBot):
        """
        Initialize Telegram bot with an underlying bot implementation.
        
        Args:
            token: Telegram bot token
            underlying_bot: The bot implementation that handles the core logic
        """
        self.token = token
        self.bot = underlying_bot
        self.application = None
        self.logger = LoggingConfig.get_logger(__name__)
        self.last_results = {}

    async def handle_lambda_event(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """
        Handle AWS Lambda events for Telegram webhook.
        The method follows this flow:
        Parse Lambda event → Extract Telegram message → 
        Process with bot → Format response → Return to API Gateway
        
        Args:
            event: AWS Lambda event containing Telegram update
            context: AWS Lambda context
            
        Returns:
            Dict containing response for API Gateway
        """
        try:
            # Log the received event (sanitized)
            self.logger.info(f"Received event type: {event.get('httpMethod', 'UNKNOWN')}")
            
            # Parse the Telegram update from the event
            if 'body' not in event:
                raise ValueError("No body in event")
                
            body = event['body']
            if isinstance(body, str):
                body = json.loads(body)
                
            # Extract message from update
            if 'message' not in body:
                raise ValueError("No message in Telegram update")
                
            message = body['message']
            chat_id = message.get('chat', {}).get('id')
            text = message.get('text', '')
            
            if not chat_id or not text:
                raise ValueError("Missing chat_id or text in message")
                
            # Process the message using the underlying bot
            result = self.bot.process_query(text)
            
            # Format response for Telegram
            response_text = (
                f"{result['response']}\n\n"
            )
            
            # Send response back to Telegram
            telegram_response = {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': response_text,
                'parse_mode': 'Markdown'
            }
            
            # Store result for potential sources request
            self.last_results[chat_id] = result
            
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps(telegram_response)
            }
            
        except ValueError as ve:
            self.logger.error(f"Validation error: {ve}")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': str(ve)})
            }
        except Exception as e:
            self.logger.error(f"Error processing Telegram update: {e}")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Internal server error'})
            }

    @staticmethod
    def format_sources(sources: list) -> str:
        """Format sources for display."""
        if not sources:
            return "No sources available."

        formatted_sources = []
        for i, source in enumerate(sources, 1):
            formatted_sources.append(f"{i}. {source}")

        return "Sources:\n" + "\n".join(formatted_sources)

    async def start(self):
        """Initialize and start the Telegram bot."""
        self.application = Application.builder().token(self.token).build()
        
        # Add handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Initialize the application
        await self.application.initialize()
        await self.application.start()

    async def stop(self):
        """Stop the Telegram bot gracefully."""
        if self.application:
            await self.application.stop()
            await self.application.shutdown()

    def run(self):
        """
        Run the bot in a completely synchronous manner.
        This approach avoids all the asyncio event loop conflicts.
        """
        try:
            self.logger.info("Starting Telegram bot...")

            # Create a new application instance
            self.application = Application.builder().token(self.token).build()

            # Register handlers
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(CommandHandler("help", self.help_command))
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

            # Use the application's run_polling method which manages its own event loop
            self.application.run_polling(drop_pending_updates=True)

        except KeyboardInterrupt:
            self.logger.info("Bot stopped by user")
        except Exception as e:
            self.logger.error(f"Error running bot: {e}")
            raise

    @staticmethod
    async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        await update.message.reply_text(
            "Hi! I'm your algorithm assistant. "
            "Ask me a question, and I'll help you find the answer."
        )

    @staticmethod
    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        await update.message.reply_text(
            "I can help you with algorithm-related questions. "
            "Just ask your question, and I'll search through my knowledge base to find the answer.\n\n"
            "You can also use /sources to see the sources for my last answer."
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming Telegram messages."""
        user_id = update.effective_user.id
        query = update.message.text

        # Handle 'sources' request
        if query.lower() == 'sources' or query.lower() == '/sources':
            if user_id in self.last_results:
                sources_text = self.format_sources(self.last_results[user_id].get('sources', []))
                await update.message.reply_text(sources_text)
            else:
                await update.message.reply_text("I don't have a previous answer to show sources for.")
            return

        # Process regular query
        await update.message.reply_text("🔍 Searching for an answer...")

        try:
            # Use the underlying bot to process the query
            result = self.bot.process_query(query)
            self.logger.info(f"Processed message: {query}")
            self.logger.info(f"RAG Query Result: {result}")

            # Store result for potential sources request
            self.last_results[user_id] = result

            # Format and send response
            response_text = (
                f"{result['response']}\n\n"
            )
            await update.message.reply_text(response_text)

        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            await update.message.reply_text(
                "Sorry, an error occurred while processing your request. Please try again."
            )


