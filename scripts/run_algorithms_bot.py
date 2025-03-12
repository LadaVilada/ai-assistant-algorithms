import os
import sys
import logging

from ai_assistant.algorithms.bot import AlgorithmsBot
from ai_assistant.core.utils.logging import LoggingConfig

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

def main():

    # Setup logging for the CLI application
    # This sets up logging for the entire application
    LoggingConfig.setup_logging(
        log_level=logging.INFO,  # or logging.DEBUG during development
        app_name='algorithms_bot_cli'
    )

    # Get a logger for this module
    logger = LoggingConfig.get_logger(__name__)

    try:
        # Log the start of the application
        logger.info("Starting Algorithms Bot CLI")

        # Create bot instance
        bot = AlgorithmsBot()

        # Run tests or interactive mode
        test_results = bot.run_tests()

        # Log test results
        for result in test_results:
            logger.info(f"Test Query: {result['query']}")
            logger.info(f"Test Response: {result['response']}")

    except Exception as e:
        # Log any critical errors
        logger.exception("Critical error in Algorithms Bot CLI")


if __name__ == '__main__':
    main()