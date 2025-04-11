"""Bot implementation for algorithm-related queries."""
from typing import Dict, Any, List, Optional, AsyncGenerator

import time

from ai_assistant.bots.base.base_bot import BaseBot
from ai_assistant.core.services.llm_service import LLMService
from ai_assistant.core.services.rag_service import RAGService
from ai_assistant.core.utils.logging import LoggingConfig


class WellDoneBot(BaseBot):
    """Bot implementation for WellDone assisted queries."""

    def __init__(self, rag_service: RAGService, llm_service: LLMService):
        """
        Initialize the WellDone bot with required services.

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
        user = update.message.from_user
        name = user.first_name or user.username or "Моя хорошая"

        try:
            return await self.process_query(message, user_name=name)
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
            return {
                "error": True,
                "response": "Sorry, I encountered an error processing your message."
            }

    async def process_query(self, query: str, user_name: Optional[str] = None) -> Dict[str, Any]:
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
        self.logger.info("Starting WellDone Assistant: process_query method")
        start_time = time.time()

        try:
            # Get retrieved documents first
            retrieved_docs = self.rag_service.retrieve(query, top_k=3)

            # Accumulate streaming response
            response = ""
            async for chunk in self.rag_service.query(query, self.llm_service, user_name=user_name):
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
                "query_type": "welldone",
                "processing_time_seconds": processing_time,
                "retrieved_count": len(retrieved_docs)
            }

            self.logger.info(f"Query processed in {processing_time:.2f}s with {len(retrieved_docs)} sources")
            return result

        except Exception as e:
            self.logger.error(f"Error processing query: {e}")
            return {
                "query": query,
                "response": "Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте ещё раз.",
                "sources": [],
                "processing_time_seconds": time.time() - start_time,
                "error": str(e),
                "retrieved_count": 0
            }

    async def stream_response(self, query: str) -> AsyncGenerator[dict[str, Any | None] | Any, None]:
        """Stream a response using the RAG service.

        Args:
            query: The user's query

        Yields:
            String chunks of the streaming response
        """
        try:
            # Get retrieved documents first (to possibly guide the LLM)
            retrieved_docs = self.rag_service.retrieve(query, top_k=3)

            # Extract image_url from top document
            image_url = None
            if retrieved_docs:
                image_url = retrieved_docs[0].get("metadata", {}).get("image_url")


            # Stream response from the LLM via RAG service
            async for chunk in self.rag_service.query(query, self.llm_service):
                yield chunk

            # When done, yield a special marker
            yield {"__image_url__": image_url}
        except Exception as e:
            self.logger.error(f"Error in streaming response: {str(e)}")
            raise

    def run_tests(self) -> List[Dict[str, str]]:
        """
        Run predefined tests for the WellDone culinary assistant bot.

        Returns:
            List of test results containing queries and responses
        """
        test_queries = [
            "Как правильно замораживать брокколи?",
            "Рецепт базиликового масла",
            "Что можно приготовить на 3 дня вперёд с курицей?",
            "Как красиво выложить тарелку с овощами и белком?",
            "Что такое шоковая заморозка и зачем она нужна?"
        ]

        results = []
        for query in test_queries:
            result = self.process_query(query)
            results.append({
                "query": query,
                "response": result['response']
            })

        return results
