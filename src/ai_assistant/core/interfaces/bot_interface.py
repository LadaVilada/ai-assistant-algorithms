from abc import ABC, abstractmethod

class BaseBotInterface(ABC):
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