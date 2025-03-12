import time
from ai_assistant.bots.base_bot import BaseBot

from ai_assistant.core import DocumentService, VectorStore


class AlgorithmsBot(BaseBot):

    def __init__(self):
        # Get a logger with potentially different log level
        # self.logger = LoggingConfig.get_logger(
        #     name=__name__,
        #     level=logging.DEBUG
        # )
        super().__init__()
        self.vector_store = VectorStore()
        self.loader = DocumentService()

    def process_query(self, query: str):
        """
        Specific implementation for algorithms bot
        Can include additional logic specific to algorithms
        """
        self.logger.info("Starting Algorithm Learning Assistant: process_query method")

        start_time = time.time()

        try:
            response, sources = self.rag_service.query(query, self.llm_service)

            # Calculate processing time
            processing_time = time.time() - start_time

            # Prepare result object with more detailed source information
            result = {
                "query": query,
                "response": response,
                "sources": [
                    {
                        "title": doc.get("metadata", {}).get("source", "Unknown"),
                        "score": doc.get("score", 0),
                        "metadata": doc.get("metadata", {}),  # Include full metadata
                        "text": doc.get("text", "")  # Include the text content
                    }
                    for doc in sources
                ],
                "query_type": "algorithms",
                "processing_time_seconds": processing_time,
                "retrieved_count": len(sources)
            }

            self.logger.info(f"Query processed in {processing_time:.2f}s with {len(sources)} sources")
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


    def run_tests(self):
        """
        Optional method for running bot-specific tests
        Can be used for local testing without Telegram
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