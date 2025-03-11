# Import your existing RAG components
import logging

from ai_assistant.core import LLMService
from ai_assistant.core import RAGService
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from ai_assistant.algorithms.bot import AlgorithmsBot
from ai_assistant.core.utils.logging import LoggingConfig


class TelegramAlgorithmsBot:
    def __init__(self, token: str):

        # Setup logging for the Telegram bot
        LoggingConfig.setup_logging(
            log_level=logging.INFO,
            app_name='telegram_algorithms_bot'
        )

        # Get a logger specific to this class
        self.logger = LoggingConfig.get_logger(__name__)

        self.token = token
        # Initialize your RAG components
        rag_service = RAGService()
        llm_service = LLMService()
        self.algorithms_bot = AlgorithmsBot(rag_service, llm_service)
        self.application = None
        # Store the last result for each user
        self.last_results = {}

    async def start_command(self, update, context):
        """Handle /start command"""
        await (update.message
               .reply_text("Hi! I'm your algorithm assistant. "
                           "Ask me a question, and I'll help you find the answer."))

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send help message when /help command is issued."""
        await update.message.reply_text(
            "You can ask me questions about algorithms and data structures. "
            "To get information about sources, use the /sources command after receiving an answer."
        )

    async def handle_message(self, update, context):
        """Process user messages and respond using RAG."""
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

        # Debug: Print the RAG chain query method signature
        self.logger.info(f"RAG Chain query method signature: {query}")

        # Handle incoming messages
        try:
            # Call your existing RAG pipeline
            result = self.algorithms_bot.process_query(query)

            self.logger.info(f"Processed message: {query}")
            # Debug: Log the actual result structure
            self.logger.info(f"RAG Query Result: {result}")

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

    def setup_handlers(self):
        """Set up Telegram bot handlers"""
        self.application = Application.builder().token(self.token).build()

        self.application.add_handler(CommandHandler('start', self.start_command))
        self.application.add_handler(CommandHandler('help', self.help_command))
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )

    def format_sources(self, sources):
        """Format sources for Telegram message."""
        if not self:
            return "No available sources."

        result = "📚 Sources:\n\n"
        for i, source in enumerate(sources):
            doc_path = source.get("title", "Unknown")
            doc_name = doc_path.split("/")[-1] if "/" in doc_path else doc_path
            page = source.get("metadata", {}).get("page", "N/A")
            score = source.get("score", 0)

            result += f"{i + 1}. {doc_name} (Page: {page}, Relevance: {score:.2f})\n"

        return result

    def run(self):
        """Run the Telegram bot"""
        self.setup_handlers()
        self.application.run_polling(drop_pending_updates=True)