from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseBotInterface(ABC):
    """
    Abstract base class defining the contract for all bot implementations
    """
    @abstractmethod
    def initialize(self):
        """Initialize bot configuration"""
        pass

    @abstractmethod
    def handle_message(self, message):
        """Process incoming messages"""
        pass

    @abstractmethod
    def run(self):
        """Start the bot"""
        pass

    @abstractmethod
    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process a user query and return a response

        Args:
            query (str): User's input query

        Returns:
            dict: Response containing at least 'response' and optionally 'sources'
        """
        pass

    @abstractmethod
    def handle_lambda_event(self, event, context):
        """
        Handle Lambda event for specific bot type

        Args:
            event (dict): Lambda event
            context (object): Lambda context

        Returns:
            dict: Processing result
        """
        raise NotImplementedError("Subclasses must implement this method")