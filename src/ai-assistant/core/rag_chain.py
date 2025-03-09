"""Retrieval-Augmented Generation chain for algorithm learning."""

import logging
from typing import Any, Dict, List, Optional, Tuple

from document_loader import DocumentLoader
from embeddings import EmbeddingManager
from vectore_store import VectorStore

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
    
    def ingest_document(self, file_path: str) -> bool:
        """Ingest a document into the RAG system.
        
        Args:
            file_path: Path to the document file
        """
        logger.info(f"Ingesting document: {file_path}")

        # 1. Load and chunk the document
        chunks = self.loader.load_document(file_path)

        if not chunks:
            logger.warning(f"No chunks extracted from document: {file_path}")
            return False

        # 2. Generate embeddings for chunks
        # TODO: move to -> embeddings = self.embedding_generator.generate_embeddings(chunks)
        doc_ids = [f"doc_{i}" for i in range(len(chunks))]
        for i, chunk in enumerate(chunks):
            chunk.metadata["doc_id"] = doc_ids[i]

        # Generate embeddings
        embeddings_dict = {}
        for chunk in chunks:
            doc_id = chunk.metadata["doc_id"]
            embedding = self.embedding_generator.create_embeddings(chunk.page_content)
            embeddings_dict[doc_id] = embedding


        # 3. Store chunks and embeddings in vector store
        self.vector_store.store_documents(chunks, embeddings_dict)

        logger.info(f"Document ingestion complete: {file_path}")
        return True

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