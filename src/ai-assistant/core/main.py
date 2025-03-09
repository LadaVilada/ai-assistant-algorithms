"""Main entry point for the Algorithm Learning Agent."""

import argparse
import logging
import os
from pathlib import Path

import sys
import time
from dotenv import load_dotenv

from document_loader import DocumentLoader
from embeddings import EmbeddingManager
from llm_service import LLMService
from rag_chain import RAGChain
from vectore_store import VectorStore


def setup_logging(log_level=logging.INFO):
    """Set up logging configuration.

   Args:
       log_level: Logging level (default: INFO)
   """
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)

    # Generate timestamp for log file
    timestamp = time.strftime("%Y%m%d-%H%M%S")

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f'logs/app_{timestamp}.log')
        ]
    )

    # Set lower log level for some noisy libraries
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("pinecone").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info("Logging initialized")


def ingest_documents(rag_chain, directory_path):
    """Ingest all PDF documents in the specified directory.
    
    Args:
        rag_chain: RAG chain instance
        directory_path: Path to directory containing PDFs
    """

    logger = logging.getLogger(__name__)
    path = Path(directory_path)

    if not path.exists():
        logging.error(f"Directory not found: {directory_path}")
        return

    # Count successful and failed ingestions
    success_count = 0
    failed_count = 0

    # List of supported file extensions
    supported_extensions = [".pdf", ".txt", ".md"]

    # Find all files with supported extensions
    for ext in supported_extensions:
        for file_path in path.glob(f"*{ext}"):
            try:
                logger.info(f"Ingesting {file_path}...")

                success = rag_chain.ingest_document(str(file_path))

                if success:
                    logger.info(f"Successfully ingested: {file_path}")
                    success_count += 1
                else:
                    logger.warning(f"Failed to ingest: {file_path}")
                    failed_count += 1

            except Exception as e:
                logger.error(f"Error ingesting {file_path}: {e}")
                failed_count += 1

    # Log ingestion summary
    logger.info(f"Ingestion complete. Success: {success_count}, Failed: {failed_count}")
    print(f"Ingestion complete. Success: {success_count}, Failed: {failed_count}")



def process_query(rag_chain, llm_service, query, top_k=3):
    """Process a user query.
    
    Args:
        rag_chain: RAG chain instance
        llm_service: LLM service instance
        query: User query
        top_k: Number of documents to retrieve
        
    Returns:
        Response to the query
    """

    logger = logging.getLogger(__name__)
    start_time = time.time()

    try:
        # Process the query using the RAG chain
        response, retrieved_docs = rag_chain.query(query, llm_service, top_k)

        # Calculate processing time
        processing_time = time.time() - start_time
        # Prepare result object
        result = {
            "query": query,
            "response": response,
            "sources": [
                {
                    "title": doc.get("metadata", {}).get("source", "Unknown"),
                    "score": doc.get("score", 0),
                }
                for doc in retrieved_docs
            ],
            "processing_time_seconds": processing_time,
            "retrieved_count": len(retrieved_docs)
        }

        logger.info(f"Query processed in {processing_time:.2f}s with {len(retrieved_docs)} sources")
        return result

    except Exception as e:
        logger.error(f"Error processing query: {e}")
        return {
            "query": query,
            "response": "I encountered an error while processing your query. Please try again.",
            "sources": [],
            "processing_time_seconds": time.time() - start_time,
            "error": str(e)
        }



def interactive_mode(rag_chain, llm_service):
    """Run the agent in interactive mode.
    
    Args:
        rag_chain: RAG chain instance
        llm_service: LLM service instance
    """
    logger = logging.getLogger(__name__)

    print("\n" + "="*50)
    print("Algorithm Learning Assistant")
    print("Enter 'exit' or 'quit' to end the session")
    print("\n" + "="*50)
    
    while True:
        try:
            # Get user query
            query = input("\nQuestion: ")
            query = query.strip()

            # Check for exit commands
            if query.lower() in ('exit', 'quit'):
                print("\nExiting. Goodbye!")
                break

            print("\nProcessing...\n")

            # Process query
            result = process_query(rag_chain, llm_service, query)

            # Print response
            print(f"Answer: {result['response']}")

            # Print processing info
            print(f"\n[Retrieved {result['retrieved_count']} documents in {result['processing_time_seconds']:.2f}s]")
            print("[Type 'sources' to see the sources used for this answer]")

        except KeyboardInterrupt:
            print("\nInterrupted by user. Exiting.")
            break
        except Exception as e:
            logger.error(f"Error in interactive mode: {e}")
            print(f"\nAn error occurred: {e}")


def main():
    """Main entry point."""
    # Set up logging
    setup_logging()
    
    # Load environment variables
    load_dotenv()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Algorithm Learning Assistant"
    )
    parser.add_argument(
        '--ingest',
        help='Path to directory containing PDFs to ingest'
    )

    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level'
    )

    args = parser.parse_args()

    # Set up logging
    log_level = getattr(logging, args.log_level)
    setup_logging(log_level)

    logger = logging.getLogger(__name__)
    logger.info("Starting Algorithm Learning Assistant")

    try:
        # Initialize components
        logger.info("Initializing components...")

        embedding_generator = EmbeddingManager()
        vector_store = VectorStore()
        loader = DocumentLoader()
        llm_service = LLMService()

        # Initialize RAG chain
        rag_chain = RAGChain(
            loader=loader,
            embedding_generator=embedding_generator,
            vector_store=vector_store
        )

        # Ingest documents if specified
        if args.ingest:
            ingest_documents(rag_chain, args.ingest)

        # Run in interactive mode
        interactive_mode(rag_chain, llm_service)

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()