import logging
from abc import ABC, abstractmethod
from ai_assistant.core.services.rag_service import RAGService
from ai_assistant.core.services.llm_service import LLMService

class BaseBot(ABC):
    def __init__(self, rag_service: RAGService, llm_service: LLMService):
        self.rag_service = rag_service
        self.llm_service = llm_service
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def process_query(self, query: str):
        """Process a query using RAG and LLM services"""
        pass

    def get_response(self, query: str):
        """Generic method to get bot response"""
        try:
            return self.process_query(query)
        except Exception as e:
            self.logger.error(f"Error processing query: {e}")
            return "Sorry, I couldn't process your query."