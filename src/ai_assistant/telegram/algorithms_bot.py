import logging
import os

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Import your existing RAG components
from ai_assistant.core import LLMService
from ai_assistant.core import RAGChain

from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize your RAG components
rag_chain = RAGChain()
llm_service = LLMService()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send greeting message when /start command is issued."""
    await update.message.reply_text(
        "👋 Hi! I'm your algorithm assistant. Ask me a question, and I'll help you find the answer."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send help message when /help command is issued."""
    await update.message.reply_text(
        "You can ask me questions about algorithms and data structures. "
        "To get information about sources, use the /sources command after receiving an answer."
    )

# Store the last result for each user
last_results = {}

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process user messages and respond using RAG."""
    user_id = update.effective_user.id
    message_text = update.message.text

    # Handle 'sources' request
    if message_text.lower() == 'sources' or message_text.lower() == '/sources':
        if user_id in last_results:
            sources_text = format_sources(last_results[user_id].get('sources', []))
            await update.message.reply_text(sources_text)
        else:
            await update.message.reply_text("I don't have a previous answer to show sources for.")
        return

    # Process regular query
    await update.message.reply_text("🔍 Searching for an answer...")

    try:

        # Debug: Print the RAG chain query method signature
        logger.info(f"RAG Chain query method signature: {rag_chain.query}")

        # Call your existing RAG pipeline
        result = rag_chain.query(message_text, llm_service, 3)
        logger.info(f"Processed message: {message_text}")
        # Debug: Log the actual result structure
        logger.info(f"RAG Query Result: {result}")


        # Store result for sources request
        # last_results[user_id] = result
        # logger.info(f"Stored result for user: {user_id}")

        # Ensure the result has the expected structure
        if isinstance(result, dict):
            # Store result for sources request
            last_results[user_id] = result

            # Send the response
            await update.message.reply_text(
                f"{result.get('response', 'No response generated')}\n\n"
                f"[Found {result.get('retrieved_count', 0)} sources. Type 'sources' to see details]"
            )
        elif isinstance(result, tuple):
            # If result is a tuple, handle it accordingly
            response, sources = result
            last_results[user_id] = {
                'response': response,
                'sources': sources,
                'retrieved_count': len(sources)
            }

            # Send the response
            await update.message.reply_text(
                f"{result['response']}\n\n"
                f"[Found {result['retrieved_count']} sources. Type 'sources' to see details]"
            )
        else:
            # Unexpected result type
            logger.error(f"Unexpected result type: {type(result)}")
            await update.message.reply_text(
                "Sorry, I couldn't process the query properly. Please try again."
            )

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        await update.message.reply_text(
            "Sorry, an error occurred while processing your request. Please try again."
        )

def format_sources(sources):
    """Format sources for Telegram message."""
    if not sources:
        return "No available sources."

    result = "📚 Sources:\n\n"
    for i, source in enumerate(sources):
        doc_path = source.get("title", "Unknown")
        doc_name = doc_path.split("/")[-1] if "/" in doc_path else doc_path
        page = source.get("metadata", {}).get("page", "N/A")
        score = source.get("score", 0)

        result += f"{i+1}. {doc_name} (Page: {page}, Relevance: {score:.2f})\n"

    return result

def main() -> None:
    """Start the bot."""
    # Load environment variables
    load_dotenv()

    # Create the Application instance
    application = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()