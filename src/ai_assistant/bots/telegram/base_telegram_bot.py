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
from telegram.constants import ChatAction

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
        self._accumulated_text = ""
        self._current_message = None
        self._last_update_time = 0.0
        self._update_interval = 0.5  # Assuming a default update_interval

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
            result = await self.bot.process_query(text)
            
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
            "👋 Welcome! I'm your AI-powered algorithm assistant. "
            "Complex problems? No worries—I'll help you break them down into simple, "
            "logical steps. Whether it's data structures, coding challenges, or algorithm design, "
            "let's tackle them one piece at a time. Keep coding, keep learning, and let's build something great! 🚀"
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
        """Handle incoming messages with streaming support."""
        try:
            message = update.message
            if not message or not message.text:
                return

            # Get chat ID and user info
            chat_id = message.chat_id
            user_id = str(message.from_user.id)
            username = message.from_user.username or "Anonymous"

            # Log incoming message
            self.logger.info(f"Received message from {username} (ID: {user_id}): {message.text}")

            # Send typing indicator
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

            # Reset state for new message
            self._accumulated_text = ""
            self._current_message = None
            self._last_update_time = 0.0

            # Process the message and get streaming response
            try:
                # Get the async iterator from stream_response
                response_stream = await self.bot.stream_response(message.text)
                
                # Iterate over the chunks
                async for chunk in response_stream:
                    self._accumulated_text += chunk
                    
                    # Update message with rate limiting
                    await self._update_message(context, chat_id)

                # Final update to ensure all text is shown
                if self._current_message:
                    await self._current_message.edit_text(
                        text=self._accumulated_text,
                        parse_mode='HTML'
                    )

            except Exception as e:
                self.logger.error(f"Error during streaming response: {str(e)}")
                await self._handle_error(context, chat_id, str(e))
                return

            # Clear state
            self._current_message = None
            self._accumulated_text = ""

            # Log successful response
            self.logger.info(f"Successfully processed message for {username} (ID: {user_id})")

        except Exception as e:
            self.logger.error(f"Error handling message: {str(e)}")
            await self._handle_error(context, chat_id, str(e))

    async def _update_message(self, context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
        """Update the message with rate limiting and error handling."""
        import time
        current_time = time.time()
        
        # Check if enough time has passed since last update
        if current_time - self._last_update_time < self._update_interval:
            return

        try:
            if not self._current_message:
                # Create new message
                self._current_message = await context.bot.send_message(
                    chat_id=chat_id,
                    text=self._accumulated_text,
                    parse_mode='HTML',
                    disable_web_page_preview=True
                )
            else:
                # Update existing message
                await self._current_message.edit_text(
                    text=self._accumulated_text,
                    parse_mode='HTML',
                    disable_web_page_preview=True
                )
            
            self._last_update_time = current_time

        except Exception as e:
            self.logger.error(f"Error updating message: {str(e)}")
            # Handle different types of errors
            if "Message is too long" in str(e):
                # If message is too long, create a new one
                self._current_message = None
                self._accumulated_text = self._accumulated_text[:4000] + "..."
                await self._update_message(context, chat_id)
            elif "Message not modified" in str(e):
                # Ignore this error as it's not critical
                pass
            else:
                # For other errors, try to recover
                await self._handle_error(context, chat_id, str(e))

    async def _handle_error(self, context: ContextTypes.DEFAULT_TYPE, chat_id: int, error_msg: str = None) -> None:
        """Handle errors gracefully with detailed error messages."""
        error_message = (
            "Sorry, I encountered an error processing your message.\n"
            "Please try again or rephrase your question.\n"
            f"Error: {error_msg if error_msg else 'Unknown error'}"
        )
        
        try:
            if self._current_message:
                await self._current_message.edit_text(
                    text=error_message,
                    parse_mode='HTML'
                )
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=error_message,
                    parse_mode='HTML'
                )
        except Exception as e:
            self.logger.error(f"Error sending error message: {str(e)}")
            # Fallback to plain text if HTML parsing fails
            await context.bot.send_message(
                chat_id=chat_id,
                text=error_message
            )


