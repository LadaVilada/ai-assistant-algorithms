import logging
from abc import ABC, abstractmethod
from typing import Dict, Any

# from src.ai_assistant.core.utils.dependency_injector import DependencyInjector


class BaseBot(ABC):
    def __init__(self, rag_service=None, llm_service=None):
        """
        Initialize bot with optional service injection

        Args:
            rag_service: RAG service for query processing
            llm_service: LLM service for response generation
        """

        # Lazy service loading
        self.rag_service = (
                rag_service or
                self._create_rag_service()
        )

        self.llm_service = (
                llm_service or
                self._create_llm_service()
        )

        # Logging setup
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info(f"Initializing {self.__class__.__name__}")

    def _create_rag_service(self):
        """Create default RAG service"""
        from ai_assistant.core.services.rag_service import RAGService
        return RAGService()
        # return DependencyInjector.get('rag_service')

    def _create_llm_service(self):
        """Create default LLM service"""
        from ai_assistant.core.services.llm_service import LLMService
        return LLMService()

    @abstractmethod
    def handle_message(self, update, message):
        """
        Process incoming messages
        Must be implemented by specific bot types
        """
        pass

    @abstractmethod
    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process a user query and return a response
        Must be implemented by specific bot types
        """
        pass

    def run(self):
        """
        Default run method
        Can be overridden by specific implementations
        Raises NotImplementedError by default
        """
        raise NotImplementedError("Specific bot must implement run method")

    def handle_lambda_event(self, event, context):
        """
        Handle AWS Lambda event with default error handling

        Args:
            event (dict): Lambda event
            context (object): Lambda context

        Returns:
            dict: Processing result
        """
        try:
            # Extract message from event
            message = self._extract_message(event)

            # Process message
            result = self.handle_message(event, message)

            return {
                'statusCode': 200,
                'body': result
            }
        except Exception as e:
            self.logger.error(f"Error in Lambda event handling: {e}", exc_info=True)
            return {
                'statusCode': 500,
                'body': {
                    'error': str(e)
                }
            }

    def _extract_message(self, event):
        """
        Extract message from different event formats

        Args:
            event (dict): Input event

        Returns:
            str: Extracted message
        """
        # Handle different event formats
        if isinstance(event, str):
            return event

        # API Gateway or other JSON-based events
        body = event.get('body', event)
        if isinstance(body, str):
            import json
            body = json.loads(body)

        # Try multiple message extraction methods
        message_keys = ['message', 'text', 'query', 'question']
        for key in message_keys:
            if key in body:
                return body[key]

        raise ValueError("Unable to extract message from event")

    def get_response(self, query: str) -> Dict[str, Any]:
        """
        Generic method to get bot response with error handling.

        Args:
            query (str): User's input query

        Returns:
            dict: Processing result or error response
        """
        try:
            # Validate input
            if not query or not isinstance(query, str):
                return {
                    'response': "Invalid query input.",
                    'error': True
                }

            # Process query
            result = self.process_query(query)

            # Ensure consistent response structure
            if not isinstance(result, dict):
                return {
                    'response': str(result),
                    'error': False
                }

            return result

        except Exception as e:
            # Comprehensive error logging
            self.logger.error(f"Error processing query: {e}", exc_info=True)

            return {
                'response': "Sorry, I couldn't process your query.",
                'error': True,
                'details': str(e)
            }