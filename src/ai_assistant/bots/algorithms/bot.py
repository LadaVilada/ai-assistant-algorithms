"""Bot implementation for algorithm-related queries."""
from typing import Dict, Any, List, AsyncIterable

import time

from ai_assistant.bots.base.base_bot import BaseBot
from ai_assistant.core.services.llm_service import LLMService
from ai_assistant.core.services.rag_service import RAGService
from ai_assistant.core.utils.logging import LoggingConfig


class AlgorithmsBot(BaseBot):
    """Bot implementation for algorithm-related queries."""

    def __init__(self, rag_service: RAGService, llm_service: LLMService):
        """
        Initialize the algorithms bot with required services.
        
        Args:
            rag_service: RAG service for query processing
            llm_service: LLM service for response generation
        """
        super().__init__(rag_service, llm_service)
        self.logger = LoggingConfig.get_logger(__name__)

    async def handle_message(self, update, message):
        """Process incoming messages."""
        if not message:
            return
            
        try:
            return await self.process_query(message)
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
            return {
                "error": True,
                "response": "Sorry, I encountered an error processing your message."
            }

    async def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process a query and return a response with sources.
        
        Args:
            query: The user's query string
            
        Returns:
            Dict containing:
                - query: Original query
                - response: Generated response
                - sources: List of source documents
                - processing_time_seconds: Time taken to process
                - retrieved_count: Number of sources retrieved
        """
        self.logger.info("Starting Algorithm Learning Assistant: process_query method")
        start_time = time.time()

        try:
            # Get retrieved documents first
            retrieved_docs = self.rag_service.retrieve(query, top_k=3)
            
            # Accumulate streaming response
            response = ""
            async for chunk in self.rag_service.query(query, self.llm_service):
                response += chunk

            # Calculate processing time
            processing_time = time.time() - start_time

            # Prepare result object with detailed source information
            result = {
                "query": query,
                "response": response,
                "sources": [
                    {
                        "title": doc.get("metadata", {}).get("source", "Unknown"),
                        "score": doc.get("score", 0),
                        "metadata": doc.get("metadata", {}),
                        "text": doc.get("text", "")
                    }
                    for doc in retrieved_docs
                ],
                "query_type": "algorithms",
                "processing_time_seconds": processing_time,
                "retrieved_count": len(retrieved_docs)
            }

            self.logger.info(f"Query processed in {processing_time:.2f}s with {len(retrieved_docs)} sources")
            return result

        except Exception as e:
            self.logger.error(f"Error processing query: {e}")
            return {
                "query": query,
                "response": "I encountered an error while processing your query. Please try again.",
                "sources": [],
                "processing_time_seconds": time.time() - start_time,
                "error": str(e),
                "retrieved_count": 0
            }

    async def stream_response(self, query: str) -> AsyncIterable[str]:
        """Stream a response using the RAG service.
        
        Args:
            query: The user's query
            
        Yields:
            String chunks of the streaming response
        """
        try:
            # Get retrieved documents first (to possibly guide the LLM)
            retrieved_docs = self.rag_service.retrieve(query, top_k=3)
            
            # Stream response from the LLM via RAG service
            async for chunk in self.rag_service.query(query, self.llm_service):
                yield chunk
        except Exception as e:
            self.logger.error(f"Error in streaming response: {str(e)}")
            raise

    def run_tests(self) -> List[Dict[str, str]]:
        """
        Run predefined tests for the algorithms bot.
        
        Returns:
            List of test results containing queries and responses
        """
        test_queries = [
            "What is a dataset?",
            "Explain binary search",
            "How does quicksort work?"
        ]

        results = []
        for query in test_queries:
            result = self.process_query(query)
            results.append({
                "query": query,
                "response": result['response']
            })

        return results