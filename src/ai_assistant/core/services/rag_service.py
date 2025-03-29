"""Retrieval-Augmented Generation chain for algorithm learning."""
import logging
from typing import Any, Dict, List, Optional, Tuple, AsyncGenerator, Generator

from ai_assistant.core.services.embedding_service import EmbeddingService
from ai_assistant.core.services.document_service import DocumentService
from ai_assistant.core.infrastructure.vector_store import VectorStore
from ai_assistant.core.utils.logging import LoggingConfig


class RAGService:
    """Retrieval-Augmented Generation chain for algorithm learning."""

    def __init__(
        self,
        loader: Optional[DocumentService] = None,
        embedding_generator: Optional[EmbeddingService] = None,
        vector_store: Optional[VectorStore] = None
    ):
        """Initialize the RAG chain.

        Args:
            loader: Document loader instance
            embedding_generator: Embedding generator instance
            vector_store: Vector store instance
        """

        # Get a logger for this service
        self.logger = LoggingConfig.get_logger(__name__)

        # Log service initialization
        self.logger.info("RAG Service initialized")

        # Use dynamic imports to avoid circular dependencies
        if loader is None:
            self.loader = DocumentService()
        else:
            self.loader = loader

        if embedding_generator is None:
            self.embedding_generator = EmbeddingService()
        else:
            self.embedding_generator = embedding_generator

        if vector_store is None:
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
            self.logger.info(f"Starting document ingestion: {file_path}")

            # 1. Load and chunk the document
            chunks = self.loader.load_document(file_path)
            if not chunks:
                self.logger.warning(f"No chunks extracted from document: {file_path}")
                return False

            total_chunks = len(chunks)
            self.logger.info(f"Processing {total_chunks} chunks from {file_path}")

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
                    self.logger.info(f"Progress: {successful_chunks}/{total_chunks} chunks processed")

                except Exception as batch_error:
                    self.logger.error(f"Error processing batch {i//batch_size}: {batch_error}")
                    continue

            self.logger.info(f"Document ingestion complete: {file_path} - Processed {successful_chunks}/{total_chunks} chunks")
            return successful_chunks > 0

        except Exception as e:
            self.logger.error(f"Error ingesting document {file_path}: {e}")
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

        print(type(self.vector_store))
        index_stats = self.vector_store.index.describe_index_stats()
        print(index_stats)  # See what the response contains

        # Extract the number of stored vectors (documents)
        num_vectors = index_stats["total_vector_count"]
        print(f"Total vectors in Pinecone: {num_vectors}")


        # 2. Retrieve relevant document chunks
        retrieved_chunks = self.vector_store.retrieve_documents(
            query_vector=query_embedding,
            top_k=top_k,
            filters=filter_dict
        )

        return retrieved_chunks

    @staticmethod
    def format_retrieved_context(retrieved_docs: List[Dict[str, Any]]) -> str:
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
            text = doc.get("page_content", "").strip()

        # context_parts.append(
        #         f"[Document {i+1}] From: {source}, Page: {page}, "
        #         f"Section: {section}\n{doc['metadata']['text']}\n"
        #     )

        context_parts.append(
            f"[Документ {i+1}] Источник: {source}, Стр.: {page}, Раздел: {section}\n{text}"
        )
        return "\n\n".join(context_parts)

    async def query(
            self,
            query: str,
            llm_service=None,
            top_k: int = 3,
            user_name: Optional[str] = None
        ) -> AsyncGenerator[str, None]:
        """Process a query end-to-end.

        Args:
            query: User query
            llm_service: LLM service instance (optional)
            top_k: Number of documents to retrieve

        Yields:
            String chunks of the streaming response
            :param user_name:  Name of the user to personalize the response
        """
        # Dynamic import to avoid circular imports
        if llm_service is None:
            from llm_service import LLMService
            llm_service = LLMService()
        try:
            # 1. Retrieve relevant documents
            retrieved_docs = self.retrieve(query, top_k=top_k)

            # 2. Format documents into context
            context = self.format_retrieved_context(retrieved_docs)

            # 3. Generate system message
            # system_message = (
            #     "You are an algorithm learning assistant that provides accurate, "
            #     "educational explanations about algorithms and data structures. "
            #     "Base your response on the provided context when possible."
            # )

            # system_message = (
            #     "Ты — AI-ассистент школы WellDone, обучающий кулинарии по методологии Маши Шелушенко. "
            #     "Отвечай в её стиле: тепло, вдохновляюще, на 'ты', с примерами из повседневной жизни. "
            #     "Используй характерные фразы вроде: 'Очень советую попробовать вот так', 'Мой любимый способ', "
            #     "'Это волшебно работает!'. Основывай свои ответы на предоставленном контексте из курса."
            # )

            system_message = (
                "Ты — AI-ассистент школы WellDone, обученный на материалах Маши Шелушенко. "
                "Ты говоришь от её имени: тепло, душевно, по-дружески и на 'ты'. "
                "Ты вдохновляешь, ободряешь и объясняешь просто, но с вниманием к деталям. "
                "Отвечай, как будто ты Маша: делись личными рекомендациями, любимыми приёмами, бытовыми примерами. "
                "Обязательно используй фирменные фразы Маши, такие как: «Очень советую попробовать вот так», "
                "«Мой любимый способ», «Это волшебно работает!», «Привет, мои хорошие!\".\n\n"

                "Если тебе передано *имя пользователя* — обязательно обращайся к нему по имени, а не обобщённо. "
                "Не используй «мои хорошие», если знаешь имя.\n\n"

                "Ты не придумываешь информацию от себя — ты используешь только контекст, который получаешь из документов курса. "
                "Если информации недостаточно, мягко скажи, что пока не можешь подсказать.\n\n"

                "Твоя цель — сделать процесс готовки вкусным, лёгким и красивым. "
                "Помоги пользователю почувствовать уверенность, радость и вдохновение на кухне."
            )

            user_name = user_name or "Моя хорошая"

            user_prompt = (
                f"{user_name} спрашивает:\n\n"
                f"Context:\n{context}\n\n"
                f"Question: {query}\n\n"
    
                "Пожалуйста, начни ответ с тёплого вступления в стиле Маши — "
                "фразы вроде «Достаём!», «Ну что, поехали!» или «Начнём с самого вкусного...» "
                "задают нужное настроение. Обратись к пользователю по имени.\n\n"
    
                "Если в контексте есть конкретные рецепты маринадов — обязательно приведи их списком. "
                "Каждый пункт начинается с номера и жирного названия, затем — краткое описание.\n\n"
    
                "Формат:\n"
                "1. **Название.** Описание...\n"
                "2. **Название.** Описание...\n\n"
    
                "Используй Markdown для форматирования. "
                "Не добавляй отдельное приветствие — сразу переходи к содержательной части."
            )

            messages = [
                    {"role": "system", "content":  system_message},
                    {"role": "user","content": user_prompt}
                    # {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}
                ]

            # Get streaming response from LLM
            async for chunk in llm_service.get_streaming_response(messages):
                yield chunk

        except Exception as e:
            self.logger.error(f"Error in streaming RAG response: {str(e)}")
            raise
