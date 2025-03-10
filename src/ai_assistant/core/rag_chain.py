"""Retrieval-Augmented Generation chain for algorithm learning."""
import hashlib
import logging
from typing import Any, Dict, List, Optional, Tuple

from .document_loader import DocumentLoader
from .embeddings import EmbeddingManager
from .vectore_store import VectorStore

logger = logging.getLogger(__name__)


class RAGChain:
    """Retrieval-Augmented Generation chain for algorithm learning."""

    def __init__(
        self,
        loader: Optional[DocumentLoader] = None,
        embedding_generator: Optional[EmbeddingManager] = None,
        vector_store: Optional[VectorStore] = None
    ):
        """Initialize the RAG chain.

        Args:
            loader: Document loader instance
            embedding_generator: Embedding generator instance
            vector_store: Vector store instance
        """
        # Use dynamic imports to avoid circular dependencies
        if loader is None:
            from document_loader import DocumentLoader
            self.loader = DocumentLoader()
        else:
            self.loader = loader

        if embedding_generator is None:
            from embeddings import EmbeddingManager
            self.embedding_generator = EmbeddingManager()
        else:
            self.embedding_generator = embedding_generator

        if vector_store is None:
            from vectore_store import VectorStore
            self.vector_store = VectorStore()
        else:
            self.vector_store = vector_store

    def generate_doc_id(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
            Generate a deterministic and unique document ID based on content and metadata.

            Args:
                content: The text content to hash
                metadata: Optional metadata to include in the ID generation

            Returns:
                A unique document ID
            """
        import hashlib
        import base64
        import time

        # Start with a simple hash of the content
        # Truncate very long content for performance
        if len(content) > 10000:
            # Use first and last parts of content for uniqueness while maintaining performance
            hash_content = content[:5000] + content[-5000:]
        else:
            hash_content = content

        # Initialize hasher
        hasher = hashlib.sha256()

        # Add content
        hasher.update(hash_content.encode('utf-8'))

        # Add key metadata if available
        if metadata:
            # Include source document in hash if available
            if 'source' in metadata:
                hasher.update(str(metadata['source']).encode('utf-8'))

            # Include position/page information if available
            if 'page' in metadata:
                hasher.update(str(metadata['page']).encode('utf-8'))

            # Include chunk number if available
            if 'chunk' in metadata:
                hasher.update(str(metadata['chunk']).encode('utf-8'))

        # Get the hash digest
        content_hash = hasher.digest()

        # Convert to base64 and make URL-safe
        # This gives us a shorter ID than hexdigest
        b64_hash = base64.urlsafe_b64encode(content_hash).decode('utf-8')

        # Take just the first part for brevity
        short_hash = b64_hash[:16].replace('=', '')

        # Option 2: Include timestamp for guaranteed uniqueness
        timestamp = int(time.time())
        return f"doc_{short_hash}_{timestamp}"

    def ingest_document(self, file_path: str) -> bool:
        """Ingest a document into the RAG system with batch processing."""
        try:
            logger.info(f"Starting document ingestion: {file_path}")

            # 1. Load and chunk the document
            chunks = self.loader.load_document(file_path)
            if not chunks:
                logger.warning(f"No chunks extracted from document: {file_path}")
                return False

            total_chunks = len(chunks)
            logger.info(f"Processing {total_chunks} chunks from {file_path}")

            # 2. Process in batches
            batch_size = 10  # Process 10 chunks at a time
            successful_chunks = 0

            for i in range(0, total_chunks, batch_size):
                # Get current batch
                batch_chunks = chunks[i:i+batch_size]
                batch_doc_ids = []
                batch_embeddings = {}

                # Generate IDs for this batch
                for chunk in batch_chunks:
                    doc_id = self.generate_doc_id(chunk.page_content)
                    chunk.metadata["doc_id"] = doc_id
                    batch_doc_ids.append(doc_id)

                # Generate embeddings for the batch
                batch_texts = [chunk.page_content for chunk in batch_chunks]

                try:
                    # Create embeddings in a single API call
                    response = self.embedding_generator.client.embeddings.create(
                        input=batch_texts,
                        model=self.embedding_generator.model_name
                    )

                    # Map embeddings to doc_ids
                    for j, doc_id in enumerate(batch_doc_ids):
                        batch_embeddings[doc_id] = response.data[j].embedding

                    # Store batch in vector store
                    self.vector_store.store_documents(batch_chunks, batch_embeddings)

                    successful_chunks += len(batch_chunks)
                    logger.info(f"Progress: {successful_chunks}/{total_chunks} chunks processed")

                except Exception as batch_error:
                    logger.error(f"Error processing batch {i//batch_size}: {batch_error}")
                    continue

            logger.info(f"Document ingestion complete: {file_path} - Processed {successful_chunks}/{total_chunks} chunks")
            return successful_chunks > 0

        except Exception as e:
            logger.error(f"Error ingesting document {file_path}: {e}")
            return False

    def retrieve(self, query: str, top_k: int = 3,
                 filter_dict: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Retrieve relevant documents for a given query.

        Args:
            query: User query
            top_k: Number of documents to retrieve
            filter_dict: Optional filter dictionary

        Returns:
            List of relevant document chunks
        """
        # 1. Generate embeddings for the query
        query_embedding = self.embedding_generator.create_embeddings(query)

        # # TODO: Implement retrieval logic with filtering
        # # 2. Perform similarity search in vector store
        # results = self.vector_store.similarity_search(
        #     query_vector=query_embedding,
        #     top_k=top_k,
        #     filter_dict=filter_dict
        # )

        print(type(self.vector_store))
        index_stats = self.vector_store.index.describe_index_stats()
        print(index_stats)  # ✅ See what the response contains

        # Extract the number of stored vectors (documents)
        num_vectors = index_stats["total_vector_count"]
        print(f"Total vectors in Pinecone: {num_vectors}")


        # 2. Retrieve relevant document chunks
        # TODO: move to -> retrieved_chunks = self.vector_store.retrieve_documents(query_embedding, top_k)
        retrieved_chunks = self.vector_store.retrieve_documents(
            query_vector=query_embedding,
            top_k=top_k,
            filters=filter_dict
        )

        return retrieved_chunks

    def format_retrieved_context(self, retrieved_docs: List[Dict[str, Any]]) -> str:
        """Format retrieved documents into a context string for LLM.

        Args:
            retrieved_docs: List of retrieved documents

        Returns:
            Formatted context string
        """
        context_parts = []
        for i, doc in enumerate(retrieved_docs):
            metadata = doc["metadata"]
            source = metadata.get("source", "Unknown")
            page = metadata.get("page", "Unknown")
            section = metadata.get("section", "Unknown")

            context_parts.append(
                f"[Document {i+1}] From: {source}, Page: {page}, "
                f"Section: {section}\n{doc['metadata']['text']}\n"
            )

        return "\n\n".join(context_parts)

    def query(
            self,
            query: str,
            llm_service=None,
            top_k: int = 3
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Process a query end-to-end.

        Args:
            query: User query
            llm_service: LLM service instance (optional)
            top_k: Number of documents to retrieve

        Returns:
            Tuple of (response, retrieved_documents)
        """
        # Dynamic import to avoid circular imports
        if llm_service is None:
            from llm_service import LLMService
            llm_service = LLMService()

        # 1. Retrieve relevant documents
        retrieved_docs = self.retrieve(query, top_k=top_k)

        # 2. Format documents into context
        context = self.format_retrieved_context(retrieved_docs)

        # 3. Generate system message
        system_message = (
            "You are an algorithm learning assistant that provides accurate, "
            "educational explanations about algorithms and data structures. "
            "Base your response on the provided context when possible."
        )

        # 4. Generate completion
        prompt = f"{query}\n\nContext from reference materials:\n{context}"
        response = llm_service.generate_completion(
            prompt=prompt,
            system_message=system_message
        )

        return response, retrieved_docs