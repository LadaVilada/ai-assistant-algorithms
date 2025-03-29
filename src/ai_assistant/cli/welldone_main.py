import argparse
import logging
from pathlib import Path
from typing import Optional

import sys
from dotenv import load_dotenv

from ai_assistant.bots.telegram.base_telegram_bot import TelegramBot
from ai_assistant.bots.welldone.bot import WellDoneBot
from ai_assistant.core import RAGService, DependencyInjector
from ai_assistant.core.utils.document_tracker import DocumentTracker
from ai_assistant.core.utils.logging import LoggingConfig


# Import core services and bots

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("🔍 Logging is working!")

def ingest_documents(rag_service, directory_path):
    """
    Ingest documents from the specified path.

    Args:
        rag_service (RAGService): RAG service for document ingestion
        directory_path (str): Path to documents to be ingested
    """
    global file_path
    logger = LoggingConfig.get_logger(__name__)
    logger.info("🔍 Logging is working!" + directory_path)

    path = Path(directory_path)

    if not path.exists():
        logger.error(f"Directory not found: {directory_path}")
        return

    # Initialize document tracker
    tracker = DocumentTracker()

    # Count successful and failed ingestion's
    success_count = 0
    skipped_count = 0
    failed_count = 0

    # List of supported file extensions
    supported_extensions = [".pdf", ".txt", ".md"]

    try:
        logger.info(f"Starting document ingestion from {path}")
        # Implement document ingestion logic here
        # Find all files with supported extensions
        for ext in supported_extensions:
            for file_path in path.glob(f"**/*{ext}"):  # Use ** for recursive search
                try:
                    # Check if document already ingested and unchanged
                    if tracker.is_document_ingested(str(file_path)):
                        logger.info(f"Skipping already ingested document: {file_path}")
                        skipped_count += 1
                        continue

                    logger.info(f"Ingesting {file_path}...")
                    success = rag_service.ingest_document(str(file_path))

                    if success:
                        # Mark as successfully ingested
                        tracker.mark_document_ingested(str(file_path))
                        logger.info(f"Successfully ingested: {file_path}")
                        success_count += 1
                    else:
                        logger.warning(f"Failed to ingest: {file_path}")
                        failed_count += 1

                except Exception as e:
                    logger.error(f"Error ingesting {file_path}: {e}")
                    failed_count += 1

    except Exception as e:
        logger.error(f"Error during document ingestion: {e}", exc_info=True)
        logger.error(f"❌ Failed to ingest file: {file_path}")
        logger.exception(e)
        raise

    # Log ingestion summary
    logger.info(f"Ingestion complete. Success: {success_count}, Skipped: {skipped_count}, Failed: {failed_count}")
    print(f"Ingestion complete. Success: {success_count}, Skipped: {skipped_count}, Failed: {failed_count}")



class CLIApplication:
    """
    Command-line interface for interacting with AI assistants
    Uses dependency injection for service management
    """
    def __init__(self):
        self.logger = LoggingConfig.get_logger(__name__)
        self._initialize_services()

    def _initialize_services(self):
        """Initialize core services using dependency injection."""
        # Get or create services
        self.embedding_service = DependencyInjector.get_service('embedding')
        self.vector_store = DependencyInjector.get_service('vector_store')
        self.document_loader = DependencyInjector.get_service('document')
        self.llm_service = DependencyInjector.get_service('llm')

        # Create RAG service with dependencies
        self.rag_service = DependencyInjector.get_service('rag',
                                                          loader=self.document_loader,
                                                          embedding_generator=self.embedding_service,
                                                          vector_store=self.vector_store
                                                          )

    def interactive_mode(self, bot_type: str = 'welldone'):
        """
        Start an interactive CLI session with the specified bot
        """
        try:
            # Get services from dependency injector
            services = DependencyInjector.get_all_services()

            # Initialize the appropriate bot
            if bot_type == 'welldone':
                bot = WellDoneBot(services['rag'], services['llm'])
            else:
                self.logger.error(f"Unsupported bot type: {bot_type}")
                return

            # Enhanced welcome screen
            print("\n" + "=" * 50)
            print(f"🤖 Interactive {bot_type.capitalize()} Bot CLI")
            print("Commands:")
            print("  - Type your question to get an answer")
            print("  - 'sources' to view sources of last answer")
            print("  - 'exit', 'quit', or 'q' to end the session")
            print("=" * 50 + "\n")

            # Track the last result for source display
            last_result = None

            while True:
                try:
                    # Get user query
                    query = input("You: ").strip()

                    # Exit conditions
                    if query.lower() in ['exit', 'quit', 'q']:
                        self.logger.info("User ended interactive session")
                        print("Goodbye!")
                        break

                    # Sources command
                    if query.lower() == 'sources':
                        if last_result and last_result.get('sources'):
                            print("\n📚 Sources for the Last Answer:")
                            for i, source in enumerate(last_result['sources'], 1):
                                try:
                                    # Extract source details
                                    file_path = source.get('metadata', {}).get('source', 'Unknown Source')
                                    file_name = file_path.split('/')[-1] if isinstance(file_path, str) else 'Unknown'

                                    # Additional source details
                                    page = source.get('metadata', {}).get('page', 'N/A')
                                    score = source.get('score', 0)

                                    # Text preview
                                    text = source.get('text', '')
                                    preview = (text[:150] + "...") if len(text) > 150 else text
                                    preview = " ".join(preview.split())  # Clean whitespace

                                    # Print source information
                                    print(f"{i}. 📄 {file_name}")
                                    print(f"   📖 Page: {page}")
                                    print(f"   🌟 Relevance: {score:.4f}")
                                    print(f"   💬 Preview: \"{preview}\"")
                                    print()
                                except Exception as source_error:
                                    self.logger.warning(f"Error processing source {i}: {source_error}")
                            continue
                        else:
                            print("No previous sources to display.")
                            continue

                    # Skip empty queries
                    if not query:
                        continue

                    # Log the incoming query
                    self.logger.info(f"Processing query: {query}")
                    print("\n⏳ Processing your query...\n")

                    # Process query
                    result = bot.process_query(query)
                    last_result = result  # Store the result for potential source display

                    # Print response
                    print("\n🤖 Bot Response:")
                    print(result['response'])

                    # Processing information
                    if 'processing_time_seconds' in result:
                        print(f"\n[Processed in {result['processing_time_seconds']:.2f}s]")

                    print("\n[Type 'sources' to see the sources used for this answer]")
                    print("-" * 50 + "\n")

                except KeyboardInterrupt:
                    self.logger.info("Interactive session interrupted by user")
                    print("\nSession interrupted. Exiting...")
                    break
                except Exception as e:
                    self.logger.error(f"Error in interactive mode: {e}", exc_info=True)
                    self.logger.error(f"Error in interactive mode: {e}")

        except Exception as init_error:
            self.logger.error(f"Failed to initialize {bot_type} bot: {init_error}",
                              exc_info=True)
            print(f"❌ Failed to start interactive mode: {init_error}")

    def run_tests(self, bot_type: str = 'welldone'):
        """
        Run predefined tests for a specific bot
        """
        if bot_type == 'welldone':
            # Get services from dependency injector
            services = DependencyInjector.get_all_services()
            bot = WellDoneBot(services['rag'], services['llm'])
            test_results = bot.run_tests()

            print(f"🧪 Test Results for {bot_type.capitalize()} Bot:")
            for result in test_results:
                print("\n" + "="*50)
                print(f"Query: {result['query']}")
                print(f"Response: {result['response']}")
                print("="*50)
        else:
            self.logger.error(f"No tests available for bot type: {bot_type}")

    def start_telegram_bot(self, token: Optional[str] = None):
        """
        Start the Telegram bot using dependency injection
        """
        if not token:
            token = input("Enter Telegram Bot Token: ").strip()

        try:
            # Get services from dependency injector
            services = DependencyInjector.get_all_services()

            # Create algorithms bot
            welldone_bot = WellDoneBot(services['rag'], services['llm'])

            # Create Telegram bot with algorithms bot
            telegram_bot = TelegramBot(token, welldone_bot)

            print("🚀 Starting Telegram Bot...")
            telegram_bot.run()
        except Exception as e:
            self.logger.error(f"Failed to start Telegram bot: {e}")
            raise

def main():
    # Load environment variables
    load_dotenv()

    """
    Main CLI entry point with argument parsing
    """
    parser = argparse.ArgumentParser(
        description="AI Assistant CLI - Interact with different bot types"
    )

    # Ingestion and index management arguments
    parser.add_argument(
        '--ingest',
        help='Path to directory containing documents to ingest'
    )

    parser.add_argument(
        "--clean-index",
        action="store_true",
        help="Clean the vector store completely")

    # Logging configuration
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level'
    )

    # Bot mode and type arguments
    parser.add_argument(
        'mode',
        choices=['interactive', 'test', 'telegram'],
        help='Mode of operation'
    )

    # Optional bot type argument
    parser.add_argument(
        '--bot',
        choices=['welldone', 'algorithms'],
        default='welldone',
        help='Specify the bot type (default: welldone)'
    )

    # Optional Telegram bot token argument
    parser.add_argument(
        '--token',
        help='Telegram Bot Token (for telegram mode)',
        default=None
    )

    # Parse arguments
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info("Parsed arguments: %s", args)

    # Set up logging
    log_level = getattr(logging, args.log_level)
    LoggingConfig.setup_logging(
        log_level=log_level,
        app_name="ai_assistant_cli"
    )

    # Get logger for main function
    logger = LoggingConfig.get_logger(__name__)
    logger.info("Starting AI Assistant CLI")

    try:
        # Create CLI application
        cli_app = CLIApplication()

        # Handle index cleaning
        if args.clean_index:
            logger.info("Cleaning vector store index")
            cli_app.vector_store.clear_index()
            sys.exit(0)

        # Handle document ingestion
        if args.ingest:
            logger.info(f"Ingesting documents from {args.ingest}")
            ingest_documents(cli_app.rag_service, args.ingest)


        # Run the appropriate mode
        if args.mode == 'interactive':
            cli_app.interactive_mode(args.bot)
        elif args.mode == 'test':
            cli_app.run_tests(args.bot)
        elif args.mode == 'telegram':
            cli_app.start_telegram_bot(args.token)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()