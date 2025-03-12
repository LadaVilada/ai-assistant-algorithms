"""Main entry point for the Algorithm Learning Agent."""

import argparse
import logging
# import logging
import os
from pathlib import Path

import sys
import time
from dotenv import load_dotenv

from src.ai_assistant.core import DocumentService
from src.ai_assistant.core import EmbeddingService
from src.ai_assistant.core import LLMService
from src.ai_assistant.core import RAGService
from src.ai_assistant.core import VectorStore
from src.ai_assistant.core.utils.document_tracker import DocumentTracker
from src.ai_assistant.core.utils.logging import LoggingConfig


def ingest_documents(rag_chain, directory_path):
    """Ingest all PDF documents in the specified directory,
       skipping previously ingested ones.
    
    Args:
        rag_chain: RAG chain instance
        directory_path: Path to directory containing PDFs
    """


    logger = logging.getLogger(__name__)
    path = Path(directory_path)

    if not path.exists():
        logger.error(f"Directory not found: {directory_path}")
        return

    # Initialize document tracker
    tracker = DocumentTracker()

    # Count successful and failed ingestion's
    success_count = 0
    skipped_count = 0
    failed_count = 0

    # List of supported file extensions
    supported_extensions = [".pdf", ".txt", ".md"]

    # Find all files with supported extensions
    for ext in supported_extensions:
        for file_path in path.glob(f"**/*{ext}"):  # Use ** for recursive search
            try:
                # Check if document already ingested and unchanged
                if tracker.is_document_ingested(str(file_path)):
                    logger.info(f"Skipping already ingested document: {file_path}")
                    skipped_count += 1
                    continue

                logger.info(f"Ingesting {file_path}...")
                success = rag_chain.ingest_document(str(file_path))

                if success:
                    # Mark as successfully ingested
                    tracker.mark_document_ingested(str(file_path))
                    logger.info(f"Successfully ingested: {file_path}")
                    success_count += 1
                else:
                    logger.warning(f"Failed to ingest: {file_path}")
                    failed_count += 1

            except Exception as e:
                logger.error(f"Error ingesting {file_path}: {e}")
                failed_count += 1

    # Log ingestion summary
    logger.info(f"Ingestion complete. Success: {success_count}, Skipped: {skipped_count}, Failed: {failed_count}")
    print(f"Ingestion complete. Success: {success_count}, Skipped: {skipped_count}, Failed: {failed_count}")


def process_query(rag_chain, llm_service, query, top_k=3):
    """Process a user query.
    
    Args:
        rag_chain: RAG chain instance
        llm_service: LLM service instance
        query: User query
        top_k: Number of documents to retrieve
        
    Returns:
        Dictionary with response and source information
    """

    logger = logging.getLogger(__name__)
    start_time = time.time()

    try:
        # Process the query using the RAG chain
        response, retrieved_docs = rag_chain.query(query, llm_service, top_k)

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
            "error": str(e),
            "retrieved_count": 0
        }


def interactive_mode(rag_chain, llm_service):
    """Run the agent in interactive mode.
    
    Args:
        rag_chain: RAG chain instance
        llm_service: LLM service instance
    """
    logger = logging.getLogger(__name__)

    print("\n" + "=" * 50)
    print("Algorithm Learning Assistant")
    print("Enter 'exit' or 'quit' to end the session")
    print("\n" + "=" * 50)

    # Keep track of the last result for displaying sources
    last_result = None

    while True:
        try:
            # Get user query
            query = input("\nQuestion: ")
            query = query.strip()

            # Check for exit commands
            if query.lower() in ('exit', 'quit'):
                print("\nExiting. Goodbye!")
                break

            # Check for sources command
            if query.lower() == 'sources' and last_result:
                print("\nSources for the last answer:")
                if last_result['sources']:
                    for i, source in enumerate(last_result['sources']):
                        file_path = source.get("title", "Unknown")
                        # Extract just the filename from the path
                        file_name = os.path.basename(file_path) if isinstance(file_path, str) else "Unknown"

                        page = source.get("metadata", {}).get("page", "N/A")
                        score = source.get("score", 0)

                        # Extract and format text preview
                        text = source.get("text", "")
                        preview = text[:100] + "..." if len(text) > 100 else text

                        # Clean up the preview (remove excess whitespace)
                        preview = " ".join(preview.split())

                        # Print source information with text preview
                        print(f"{i+1}. {file_name} (Page: {page}, Relevance: {score:.4f})")
                        print(f"   Preview: \"{preview}\"")
                        print()  # Empty line for better readability
                else:
                    print("No sources were retrieved for the last answer.")
                continue
            elif query.lower() == 'sources' and not last_result:
                print("\nNo previous query to show sources for.")
                continue

            # Skip empty queries
            if not query:
                continue

            print("\nProcessing...\n")

            # Process query
            result = process_query(rag_chain, llm_service, query)
            last_result = result  # Store the result for potential source display

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

    # Load environment variables
    load_dotenv()

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Algorithm Learning Assistant"
    )
    parser.add_argument(
        '--ingest',
        help='Path to directory containing documents to ingest'
    )

    parser.add_argument(
        "--clean-index", action="store_true",
        help="Clean the vector store completely")


    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level'
    )

    args = parser.parse_args()
    # Set up logging
    log_level = getattr(logging, args.log_level)

    LoggingConfig.setup_logging(
        log_level=log_level,
        # log_level=logging.INFO,
        app_name="ai_assistant_cli"
    )

    logger = logging.getLogger(__name__)
    logger.info("Starting Algorithm Learning Assistant")

    try:
        # Initialize components
        logger.info("Initializing components...")

        embedding_generator = EmbeddingService()
        vector_store = VectorStore()
        loader = DocumentService()
        llm_service = LLMService()

        # Initialize RAG chain
        rag_chain = RAGService(
            loader=loader,
            embedding_generator=embedding_generator,
            vector_store=vector_store
        )

        # Handle index cleaning if requested
        if args.clean_index:
            vector_store.clear_index()
            sys.exit(0)

        # Ingest documents if specified
        if args.ingest:
            ingest_documents(rag_chain, args.ingest)

        # ingest_documents(rag_chain, os.getenv("STORAGE_PATH", ""))

        # Run in interactive mode
        interactive_mode(rag_chain, llm_service)

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
