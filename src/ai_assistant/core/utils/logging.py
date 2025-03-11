import os
import time
import logging
from typing import Optional, Union

class LoggingConfig:
    """
    Centralized logging configuration for the AI Assistant application.

    Supports multiple logging scenarios:
    - Console logging
    - File logging
    - Configurable log levels
    - Log rotation
    """

    @staticmethod
    def setup_logging(
            log_level: int = logging.INFO,
            log_dir: Optional[str] = None,
            app_name: str = "ai_assistant"
    ) -> None:
        """
        Set up comprehensive logging configuration.

        Args:
            log_level (int): Logging level (default: logging.INFO)
            log_dir (str, optional): Directory to store log files
            app_name (str): Name of the application for log file naming
        """
        # Determine log directory
        if log_dir is None:
            log_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..", "..", "..", "logs"
            )

        # Ensure log directory exists
        os.makedirs(log_dir, exist_ok=True)

        # Generate timestamp for log file
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        log_file_path = os.path.join(log_dir, f"{app_name}_{timestamp}.log")

        # Create formatters
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Configure root logger
        logging.basicConfig(
            level=log_level,
            handlers=[]  # We'll add handlers manually
        )

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(log_level)

        # File handler
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(log_level)

        # Get the root logger and add handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()  # Remove any existing handlers
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)

        # Reduce log levels for noisy libraries
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("openai").setLevel(logging.WARNING)
        logging.getLogger("pinecone").setLevel(logging.WARNING)
        logging.getLogger("telegram").setLevel(logging.WARNING)

        # Log initialization
        logger = logging.getLogger(__name__)
        logger.info(f"Logging initialized")
        logger.info(f"Log file created at: {log_file_path}")

    @staticmethod
    def get_logger(
            name: Optional[str] = None,
            level: Optional[Union[int, str]] = None
    ) -> logging.Logger:
        """
        Get a logger with optional custom configuration.

        Args:
            name (str, optional): Name of the logger (defaults to root logger)
            level (int or str, optional): Logging level

        Returns:
            logging.Logger: Configured logger instance
        """
        # Use the provided name or get the root logger
        logger = logging.getLogger(name)

        # Set custom log level if provided
        if level is not None:
            # Convert string levels to integers if needed
            if isinstance(level, str):
                level = getattr(logging, level.upper())
            logger.setLevel(level)

        return logger

# Usage examples
def main():
    # Basic logging setup
    LoggingConfig.setup_logging()

    # Get a logger for a specific module
    logger = LoggingConfig.get_logger(__name__)

    # Example logging
    logger.info("Application started")
    logger.warning("This is a warning message")

    try:
        # Simulated error
        1 / 0
    except Exception as e:
        logger.error("An error occurred", exc_info=True)

if __name__ == "__main__":
    main()