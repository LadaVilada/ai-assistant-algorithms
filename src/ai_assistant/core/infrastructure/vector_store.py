"""Pinecone vector database for storing and retrieving document embeddings."""

import logging
import os
from typing import List, Dict, Any, Optional

# Load environment variables from .env file
from dotenv import load_dotenv
from langchain_core.documents import Document
from pinecone import Pinecone, ServerlessSpec

load_dotenv()

logger = logging.getLogger(__name__)


class VectorStore:
    """Pinecone vector database for storing and retrieving document embeddings."""
    
    def __init__(
        self, 
        api_key: str = None,
        environment: str = None,
        # index_name: str = "algorithm-assistant",
        index_name: str = "welldone-assistant",
        dimension: int = 1536  # Default for OpenAI embeddings
    ):
        """Initialize the Pinecone vector store.
        
        Args:
            api_key: Pinecone API key (defaults to PINECONE_API_KEY env var)
            environment: Pinecone environment (defaults to PINECONE_ENVIRONMENT env var)
            index_name: Name of the Pinecone index
            dimension: Dimension of embedding vectors
        """
        # Get API credentials from parameters or environment variables
        self.api_key = api_key or os.getenv("PINECONE_API_KEY")
        self.environment = environment or os.getenv("PINECONE_ENVIRONMENT")
        self.index_name = index_name
        self.dimension = dimension
        
        if not self.api_key or not self.environment:
            raise ValueError(
                "Pinecone API key and environment must be provided either "
                "as parameters or through environment variables."
            )
        
        # Initialize Pinecone connection
        self._connect_to_pinecone()
    
    def _connect_to_pinecone(self):
        """Connect to Pinecone and ensure index exists."""
        try:

            # Initialize Pinecone
            pinecone = Pinecone(
                api_key=self.api_key
            )

            try:
                # Connect to the index
                self.index = pinecone.Index(self.index_name)
                logger.info(f"Successfully connected to Pinecone index: {self.index_name}")
            except Exception as error: # IndexNotFoundError
                logger.info(f"Index not found: {self.index_name}")
                try:
                    # Check if index exists, create if not
                    if self.index_name not in pinecone.list_indexes():
                        pinecone.create_index(
                            name=self.index_name,
                            dimension=self.dimension,
                            metric="cosine",
                            spec=ServerlessSpec(
                                    cloud="aws",      # Cloud provider
                                    region="us-east-1"  # Specific region
                                )
                        )

                        logger.info(f"Created new Pinecone index: {self.index_name}")
                except Exception as error: # IndexAlreadyExistsError
                    # Connect to the index
                    self.index = pinecone.Index(self.index_name)
                    logger.info(f"Successfully connected to Pinecone index: {self.index_name}")

        except Exception as e:
            logger.error(f"Failed to connect to Pinecone: {e}")
            raise
    
    def store_documents(
        self, 
        documents: List[Document], 
        embeddings: Dict[str, List[float]]
    ) -> None:
        """Store documents with their embeddings in Pinecone.
        
        Args:
            documents: List of documents to store
            embeddings: Dictionary mapping document IDs to embeddings
        """
        try:
            vectors_to_upsert = []
            
            for i, doc in enumerate(documents):
                # Generate a deterministic ID if not present
                doc_id = str(doc.metadata.get("doc_id", f"doc_{i}"))
                
                if doc_id not in embeddings:
                    logger.warning(f"No embedding found for document {doc_id}")
                    continue
                
                # Prepare vector with metadata
                vectors_to_upsert.append((
                    doc_id,
                    embeddings[doc_id],
                    {
                        "text": doc.page_content,
                        **doc.metadata
                    }
                ))
            
            # Upsert vectors in batches
            batch_size = 100
            total_vectors = len(vectors_to_upsert)
            
            for i in range(0, total_vectors, batch_size):
                batch = vectors_to_upsert[i:i + batch_size]
                self.index.upsert(vectors=batch)
                
            logger.info(f"Successfully stored {total_vectors} vectors in Pinecone")
            
        except Exception as e:
            logger.error(f"Error storing documents in Pinecone: {e}")
            raise
    
    def similarity_search(
        self, 
        query_vector: List[float], 
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        namespace: str = ""
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors in Pinecone.
        
        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            filters: Metadata filters to apply
            namespace: Optional Pinecone namespace
            
        Returns:
            List of documents with similarity scores
        """
        try:
            # Query Pinecone
            results = self.index.query(
                vector=query_vector,
                top_k=top_k,
                include_metadata=True,
                filter=filters,
                namespace=namespace
            )
            
            # Format results
            formatted_results = [
                {
                    "id": match["id"],
                    "score": match["score"],
                    "text": match["metadata"].get("text", ""),
                    "metadata": match["metadata"]
                }
                for match in results["matches"]
            ]
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching Pinecone: {e}")
            return []

    def retrieve_documents(
            self,
            query_vector: List[float],
            top_k: int = 5,
            filters: Optional[Dict[str, Any]] = None,
            namespace: str = ""
    ) -> List[Dict[str, Any]]:
        """Retrieve documents based on query vector similarity.
        This method is an alias for similarity_search to maintain
        interface consistency across the codebase.

        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            filters: Metadata filters to apply
            namespace: Optional Pinecone namespace

        Returns:
            List of documents with similarity scores
        """
        return self.similarity_search(
            query_vector=query_vector,
            top_k=top_k,
            filters=filters,
            namespace=namespace
        )
    
    def delete_documents(self, ids: List[str], namespace: str = "") -> None:
        """Delete documents from Pinecone.
        
        Args:
            ids: List of document IDs to delete
            namespace: Optional Pinecone namespace
        """
        try:
            self.index.delete(ids=ids, namespace=namespace)
            logger.info(f"Deleted {len(ids)} documents from Pinecone")
        except Exception as e:
            logger.error(f"Error deleting documents from Pinecone: {e}")
            raise
    
    def clear_index(self) -> None:
        """Clear all vectors from the index."""
        try:
            self.index.delete(delete_all=True)
            logger.info(f"Cleared all vectors from Pinecone index: {self.index_name}")
        except Exception as e:
            logger.error(f"Error clearing Pinecone index: {e}")
            raise
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the Pinecone index.
        
        Returns:
            Dictionary with index statistics
        """
        try:
            stats = self.index.describe_index_stats()
            return stats
        except Exception as e:
            logger.error(f"Error getting Pinecone index stats: {e}")
            return {}
    
    def close(self) -> None:
        """Close connection to Pinecone."""
        # Pinecone client doesn't require explicit closing,
        # but this method is provided for API completeness
        logger.info("Pinecone connection closed")

    @classmethod
    def from_documents(cls, documents, embeddings, index_name):
        pass