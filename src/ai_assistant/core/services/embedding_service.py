import logging
import os
from typing import List, Optional, Dict

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from openai import OpenAI

# from package.pydantic import SecretStr
from pydantic import SecretStr

load_dotenv()

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Advanced embedding and vector store management.
    This class is a wrapper around OpenAI’s embedding API, built to generate embeddings for:
    single queries, documents (text chunks) and eventually store them in Pinecone (your vector DB)

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
            api_key=SecretStr(self.api_key)
        )

        logger.info(f"Initialized embedding manager with model: {self.model_name}")

    def create_embeddings(
            self,
            text: str
    ) -> List[float]:
        """
        Create OpenAI embeddings for a single text string.

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

    def create_embeddings_batch(
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
                    doc.metadata.get("doc_id", f"doc_{i + j}")
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