import logging
import os
import json
from typing import List, Optional, Dict, TypedDict

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from openai import OpenAI

# from package.pydantic import SecretStr
from pydantic import SecretStr

load_dotenv()

logger = logging.getLogger(__name__)

class RecipeMetadata(TypedDict):
    title: str
    recipe_type: str
    duration_total: Optional[str]
    is_make_ahead: bool
    difficulty: str
    keywords: List[str]
    image_url: Optional[str]


DEFAULT_METADATA: RecipeMetadata = {
    "title": "Untitled Recipe",
    "recipe_type": "другое",
    "duration_total": "не указано",
    "is_make_ahead": False,
    "difficulty": "unknown",
    "keywords": [],
    "image_url": ""  # Use empty string instead of None to prevent Pinecone errors
}

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
            embedding_model: str = "text-embedding-ada-002",
            chat_model: str = "gpt-4o-mini"
    ):
        """Initialize the embedding manager.

        Args:
            api_key: OpenAI API key (defaults to environment variable)
            embedding_model: Name of the embedding model to use
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

        self.embedding_model = embedding_model
        self.chat_model = chat_model

        if not self.api_key:
            raise ValueError(
                "OpenAI API key must be provided either as a parameter or "
                "through the OPENAI_API_KEY environment variable."
            )

        # Initialize OpenAI client
        self.client = OpenAI()

        logger.info(f"Initialized embedding manager with model: {self.embedding_model}")

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
                model=self.embedding_model
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
                    model=self.embedding_model
                )

                # Map embeddings to doc_ids
                for j, doc_id in enumerate(doc_ids):
                    embeddings_dict[doc_id] = response.data[j].embedding

            logger.info(f"Generated embeddings for {len(documents)} documents")
            return embeddings_dict

        except Exception as e:
            logger.error(f"Error generating embeddings for documents: {e}")
            return embeddings_dict


    def enrich_recipe(self, recipe_text, image_url: Optional[str] = None) -> RecipeMetadata:
        prompt = f"""
            Ты — помощник кулинара. Проанализируй рецепт и верни метаданные в формате JSON.
            Если текст не содержит рецепта, но даёт советы по посуде, оборудованию, технике — тоже верни метаданные. 
            Укажи `recipe_type: "инструмент"` и опиши ключевые слова.
            
            Текст рецепта:
            
            \"\"\"{recipe_text}\"\"\"
            
            Верни ответ в JSON-формате со следующими полями:
            - title
            - recipe_type (заготовка, соус, заморозка, основа, выпечка, десерт, горячее, салат, напиток, разное и т.д.)
            - duration_total (если указано, в свободной форме, например: "40–45 минут")
            - is_make_ahead (true/false)
            - difficulty (easy / medium / hard)
            - keywords (важные ингредиенты — список слов)
            """

        response = self.client.chat.completions.create(
            model=self.chat_model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )

        reply = response.choices[0].message.content
        clean_json = self.extract_json_block(reply)

        try:
            metadata_dict = json.loads(clean_json)

            def safe_get(value, default):
                return value if value is not None else default

            # Process image_url to ensure it's not None (Pinecone rejects null values)
            processed_image_url = "" if image_url is None else image_url
            
            # Fallbacks for missing fields
            return {
                "title": safe_get(metadata_dict.get("title"), DEFAULT_METADATA["title"]),
                "recipe_type": safe_get(metadata_dict.get("recipe_type"), DEFAULT_METADATA["recipe_type"]),
                "duration_total": safe_get(metadata_dict.get("duration_total"), DEFAULT_METADATA["duration_total"]),
                "is_make_ahead": safe_get(metadata_dict.get("is_make_ahead"), DEFAULT_METADATA["is_make_ahead"]),
                "difficulty": safe_get(metadata_dict.get("difficulty"), DEFAULT_METADATA["difficulty"]),
                "keywords": safe_get(metadata_dict.get("keywords"), DEFAULT_METADATA["keywords"]),
                "image_url": processed_image_url  # Use empty string instead of None
            }
        except json.JSONDecodeError:
            logger.warning("Ошибка разбора JSON. Ответ от модели:")
            logger.warning(f"Сырые данные от LLM:\n{reply}")
            return DEFAULT_METADATA

    @staticmethod
    def extract_json_block(text: str) -> str:
        """
        Удаляет обёртку ```json ... ``` или возвращает текст как есть.
        """
        import re
        match = re.search(r"```json(.*?)```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return text.strip()

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