from abc import ABC, abstractmethod
from typing import Dict, Any
from telegram import Update
from telegram.ext import ContextTypes
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from ai_assistant.bots.base.base_bot import BaseBot

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
        
        self.logger = logging.getLogger(self.__class__.__name__)
        self.last_results = {}

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
                f"[Sources found: {len(result.get('sources', []))}]"
            )
            await update.message.reply_text(response_text)

        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            await update.message.reply_text(
                "Sorry, an error occurred while processing your request. Please try again."
            )

    def format_sources(self, sources: list) -> str:
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
        """Run the Telegram bot with proper lifecycle management."""
        import asyncio
        
        async def main():
            await self.start()
            await self.application.run_polling(drop_pending_updates=True)
        
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            self.logger.info("Bot stopped by user")
        except Exception as e:
            self.logger.error(f"Error running bot: {e}")
            raise
        finally:
            # Ensure proper cleanup
            if self.application:
                asyncio.run(self.stop())
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        await update.message.reply_text(
            "Hi! I'm your algorithm assistant. "
            "Ask me a question, and I'll help you find the answer."
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        await update.message.reply_text(
            "I can help you with algorithm-related questions. "
            "Just ask your question, and I'll search through my knowledge base to find the answer.\n\n"
            "You can also use /sources to see the sources for my last answer."
        )

