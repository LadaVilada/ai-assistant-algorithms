import logging
import os
from typing import List, Optional, Dict

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from openai import OpenAI

load_dotenv()

logger = logging.getLogger(__name__)

class EmbeddingManager:
    """
    Advanced embedding and vector store management
    Responsibility : Generate embeddings for prompts.
    Content : Functions to create prompt embeddings using a pre-trained model.
    """

    """Manager for generating and handling embeddings."""

    def __init__(
            self,
            api_key: Optional[str] = None,
            model_name: str = "text-embedding-ada-002"
    ):
        """Initialize the embedding manager.

        Args:
            api_key: OpenAI API key (defaults to environment variable)
            model_name: Name of the embedding model to use
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

        self.model_name = model_name

        if not self.api_key:
            raise ValueError(
                "OpenAI API key must be provided either as a parameter or "
                "through the OPENAI_API_KEY environment variable."
            )

        # Initialize OpenAI client
        self.client = OpenAI(api_key=self.api_key)

        # Initialize LangChain embedding model
        self.embedding_model = OpenAIEmbeddings(
            model=self.model_name,
            openai_api_key=self.api_key
        )

        logger.info(f"Initialized embedding manager with model: {self.model_name}")


    def create_embeddings(
            self,
            text: str
    ) -> List[float]:
        """
        Create OpenAI embeddings

        Args:
             text: Text to embed

        Returns:
            OpenAIEmbeddings instance
        """
        try:

            response = self.client.embeddings.create(
                input=[text],
                model=self.model_name
            )

            # Extract embeddings from response (new structure)
            embedding = response.data[0].embedding
            return embedding

        except Exception as e:
            logging.error(f"Error creating embeddings: {e}")
            raise

    def generate_embeddings(
            self,
            documents: List[Document]
    ) -> Dict[str, List[float]]:
        """Generate embeddings for multiple documents.

        Args:
            documents: List of documents to embed

        Returns:
            Dictionary mapping document IDs to embeddings
        """
        embeddings_dict = {}

        try:
            # Process in batches to avoid rate limits
            batch_size = 20  # Adjust based on your API limits

            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]

                # Extract texts and doc_ids
                texts = [doc.page_content for doc in batch]
                doc_ids = [
                    doc.metadata.get("doc_id", f"doc_{i+j}")
                    for j, doc in enumerate(batch)
                ]

                # Generate embeddings for batch
                response = self.client.embeddings.create(
                    input=texts,
                    model=self.model_name
                )

                # Map embeddings to doc_ids
                for j, doc_id in enumerate(doc_ids):
                    embeddings_dict[doc_id] = response.data[j].embedding


            logger.info(f"Generated embeddings for {len(documents)} documents")
            return embeddings_dict

        except Exception as e:
            logger.error(f"Error generating embeddings for documents: {e}")
            return embeddings_dict

    def generate_embedding(
            self,
            text: str
    ) -> List[float]:
        """Generate embedding for a single text string.
        This is an alias for create_embeddings for interface consistency.

        Args:
            text: Text to embed

        Returns:
            List of embedding values
        """
        return self.create_embeddings(text)

    @classmethod
    def create_embeddings_model(
            cls,
            model: str = "text-embedding-ada-002",
            api_key: Optional[str] = None
    ) -> OpenAIEmbeddings:
        """
        Create OpenAI embeddings model for LangChain integration

        Args:
            model (str): Embedding model name

        Returns:
            OpenAIEmbeddings instance
        """
        try:
            api_key = api_key or os.getenv("OPENAI_API_KEY")
            return OpenAIEmbeddings(
                model=model,
                openai_api_key=api_key
            )
        except Exception as e:
            logger.error(f"Error creating embeddings model: {e}")
            raise

    @staticmethod
    def get_dimension_for_model(model_name: str) -> int:
        """
        Get the embedding dimension for a given model.

        Args:
            model_name: Name of the embedding model

        Returns:
            Dimension of the embedding model
        """
        # Common embedding model dimensions
        dimensions = {
            "text-embedding-ada-002": 1536,
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072
        }

        return dimensions.get(model_name, 1536)  # Default to 1536 if unknown

    # @classmethod
    # def create_pinecone_store(
    #         cls,
    #         documents: List[Document],
    #         index_name: str,
    #         embeddings: Optional[OpenAIEmbeddings] = None
    # ) -> VectorStore:
    #     """
    #     Create Pinecone vector store
    #
    #     Args:
    #         documents (List[Document]): Documents to embed
    #         index_name (str): Pinecone index name
    #         embeddings (Optional[OpenAIEmbeddings]): Embedding model
    #
    #     Returns:
    #         Pinecone vector store
    #     """
    #     try:
    #
    #         pinecone_config = AgentConfig.get_pinecone_config()
    #         pinecone = Pinecone(
    #             api_key=pinecone_config["api_key"]
    #         )
    #
    #         # Check if index exists
    #         if index_name not in pinecone.list_indexes().names():
    #             print(f"\n--- Creating Pinecone index {index_name} ---")
    #             logging.info(f"Creating Pinecone index {index_name}")
    #
    #             try:
    #                 # Create a serverless index
    #                 pinecone.create_index(
    #                     name=index_name,
    #                     dimension=1536,
    #                     metric="cosine",  # Similarity metric
    #                     spec=ServerlessSpec(
    #                         cloud="aws",      # Cloud provider
    #                         region="us-east-1"  # Specific region
    #                     )
    #                 )
    #                 print(f"--- Created Pinecone index {index_name} ---")
    #             except Exception as e:
    #                 print(f"Error creating Pinecone index: {e}")
    #         else :
    #             print(f"--- Pinecone index {index_name} already exists ---")
    #
    #         print(f"--- Connecting to Pinecone index {index_name} ---")
    #
    #
    #         # Use provided embeddings or create new
    #         if embeddings is None:
    #             embeddings = cls.create_embeddings()
    #
    #         # Create Pinecone vector store safely
    #         vector_store = VectorStore.from_documents(
    #             documents,
    #             embeddings,
    #             index_name=index_name
    #         )
    #
    #         logging.info(f"Created Pinecone vector store in index {index_name}")
    #         return vector_store
    #     except Exception as e:
    #         logging.error(f"Error creating Pinecone vector store: {e}")
    #         raise

    # @classmethod
    # def create_retriever(
    #         cls,
    #         vector_store,
    #         search_kwargs: Optional[dict] = None
    # ):
    #     """
    #     Create a retriever from vector store
    #
    #     Args:
    #         vector_store: Vector store instance
    #         search_kwargs (Optional[dict]): Search configuration
    #
    #     Returns:
    #         Retriever object
    #     """
    #     default_kwargs = {"k": 5}
    #     search_kwargs = search_kwargs or default_kwargs
    #
    #     return vector_store.as_retriever(search_kwargs=search_kwargs)