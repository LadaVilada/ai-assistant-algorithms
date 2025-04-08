"""Retrieval-Augmented Generation chain for algorithm learning."""
from typing import Any, Dict, List, Optional, AsyncGenerator

from ai_assistant.core.infrastructure.vector_store import VectorStore
from ai_assistant.core.services.conversation_service import ConversationService
from ai_assistant.core.services.document_service import DocumentService
from ai_assistant.core.services.embedding_service import EmbeddingService
from ai_assistant.core.utils.logging import LoggingConfig


def extract_keywords_simple(text: str, top_n=5):
    import re

    words = re.findall(r"\b[а-яА-Я]{4,}\b", text.lower())
    freq = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1
    sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [w for w, _ in sorted_words[:top_n]]

class RAGService:
    """Retrieval-Augmented Generation chain for algorithm learning."""

    def __init__(
        self,
        loader: Optional[DocumentService] = None,
        embedding_generator: Optional[EmbeddingService] = None,
        vector_store: Optional[VectorStore] = None,
        conversation_service: Optional[ConversationService] = None
    ):
        """Initialize the RAG chain.

        Args:
            loader: Document loader instance
            embedding_generator: Embedding generator instance
            vector_store: Vector store instance
            conversation_service: Conversation history service instance
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
            
        if conversation_service is None:
            self.conversation_service = ConversationService()
        else:
            self.conversation_service = conversation_service


    def attach_image_url(self, chunk_metadata: dict) -> Optional[str]:
        """
        Extracts and returns image_url from chunk metadata if available.
        Returns an empty string if no image_url is present to avoid None values.
        """
        url = chunk_metadata.get("image_url")
        if not url:
            self.logger.debug("No image_url found in chunk metadata.")
            # Return empty string instead of None to avoid Pinecone error
            return ""
        return url

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
        """Ingest a document into the RAG system with batch processing,
        now adapted to handle image metadata."""
        try:
            self.logger.info(f"Starting document ingestion: {file_path}")

            # 1. Load and chunk the document. The loader now returns chunks that may include image metadata.
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
                # Get current batch of chunks
                batch_chunks = chunks[i:i + batch_size]
                batch_doc_ids = []
                batch_embeddings = {}

                # Generate document IDs for each chunk and log image metadata if available
                for chunk in batch_chunks:
                    # Pass chunk.metadata to incorporate additional info (like page and image data) into the ID
                    doc_id = self.generate_doc_id(chunk.page_content, chunk.metadata)
                    chunk.metadata["doc_id"] = doc_id
                    batch_doc_ids.append(doc_id)

                    # Log if image metadata is present
                    if "image_url" in chunk.metadata and chunk.metadata["image_url"]:
                        self.logger.info(f"Chunk {doc_id} contains an image: {chunk.metadata['image_url']}")

                # Prepare the texts for embedding generation
                batch_texts = []
                for chunk in batch_chunks:
                    text = chunk.page_content
                    image_url = self.attach_image_url(chunk.metadata)
                    try:
                        enriched_metadata = self.embedding_generator.enrich_recipe(text, image_url=image_url)  # LLM возвращает dict
                        chunk.metadata.update(enriched_metadata)  # добавляем метаданные в chunk
                    except Exception as enrich_error:
                        self.logger.warning(f"LLM enrichment failed for chunk {chunk.metadata.get('doc_id', 'unknown')}: {enrich_error}")

                    batch_texts.append(text)

                try:
                    # Generate embeddings for the batch in a single API call
                    response = self.embedding_generator.client.embeddings.create(
                        input=batch_texts,
                        model=self.embedding_generator.embedding_model
                    )

                    # Map embeddings to their corresponding document IDs
                    for j, doc_id in enumerate(batch_doc_ids):
                        batch_embeddings[doc_id] = response.data[j].embedding

                    # Store the batch in the vector store (metadata, including image_url, is preserved)
                    self.vector_store.store_documents(batch_chunks, batch_embeddings)

                    successful_chunks += len(batch_chunks)
                    self.logger.info(f"Progress: {successful_chunks}/{total_chunks} chunks processed")

                except Exception as batch_error:
                    self.logger.error(f"Error processing batch {i // batch_size}: {batch_error}")
                    continue

            self.logger.info(f"Document ingestion complete: {file_path}")
            return True

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

        embedding_query = self.build_embedding_query(query)

        query_embedding = self.embedding_generator.create_embeddings(embedding_query)
        keywords = extract_keywords_simple(query)
        # query_embedding = self.embedding_generator.create_embeddings(query)

        print(type(self.vector_store))
        index_stats = self.vector_store.index.describe_index_stats()
        print(index_stats)  # See what the response contains

        # Extract the number of stored vectors (documents)
        num_vectors = index_stats["total_vector_count"]
        print(f"Total vectors in Pinecone: {num_vectors}")


        # 2. Retrieve relevant document chunks
        filters = {"keywords": {"$in": keywords}} if keywords else None


        retrieved_chunks = self.vector_store.retrieve_documents(
            query_vector=query_embedding,
            top_k=top_k,
            filters=filters
            # filters=filter_dict
        )

        self.logger.debug(f"Retrieved {len(retrieved_chunks)} chunks for query.")
        self.logger.debug(f"Query: {query}, Embedding: {query_embedding}, Filters: {filters}")

        return retrieved_chunks

    @staticmethod
    def build_embedding_query(query: str) -> str:
        q = query.lower().strip()

        # Если слишком короткий и нет слова "рецепт"
        if "рецепт" not in q and len(q.split()) <= 5:
            return (
                f"Найди рецепт под названием: {query}. "
                f"Если в документах есть ингредиенты и шаги приготовления, сформируй полноценный рецепт."
            )

        # Разговорные / общие вопросы
        if any(word in q for word in ["расскажи", "покажи", "какие", "есть ли", "что можно", "хочу рецепт"]):
            return (
                f"Найди рецепты, в которых используются: {query}. "
                f"Сформируй список с ингредиентами, пошаговым приготовлением и советами от шефа WellDone."
            )

        # По умолчанию
        return (
            f"Найди кулинарный рецепт: {query}. "
            f"Он должен содержать ингредиенты, пошаговое приготовление и советы от шефа WellDone."
        )

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
            text = doc.get("text", "")
            # text = doc.get("page_content", "").strip()

        # context_parts.append(
        #         f"[Document {i+1}] From: {source}, Page: {page}, "
        #         f"Section: {section}\n{doc['metadata']['text']}\n"
        #     )
            context_parts.append(
                f"[Документ {i+1}] Источник: {source}, Стр.: {page}, Раздел: {section}\n{text}"
            )

        if not context_parts:
            # Optionally return a default message if no documents were found.
            return "No context available."

        return "\n\n".join(context_parts)

    async def query(
            self,
            query: str,
            llm_service=None,
            top_k: int = 3,
            user_name: Optional[str] = None,
            conversation_id: Optional[str] = None,
            user_id: Optional[str] = None,
            include_history: bool = True,
            history_limit: int = 5
        ) -> AsyncGenerator[str, None]:
        """Process a query end-to-end.

        Args:
            query: User query
            llm_service: LLM service instance (optional)
            top_k: Number of documents to retrieve
            user_name: Name of the user to personalize the response
            conversation_id: Conversation identifier for history tracking
            user_id: User identifier, required if creating a new conversation
            include_history: Whether to include conversation history in the response
            history_limit: Maximum number of previous messages to include

        Yields:
            String chunks of the streaming response
        """
        # Dynamic import to avoid circular imports
        if llm_service is None:
            from llm_service import LLMService
            llm_service = LLMService()
        try:
            # Create or retrieve conversation
            if not conversation_id and user_id:
                # Initialize new conversation with system prompt
                system_prompt = RAGService.get_system_message()
                conversation_id = self.conversation_service.create_conversation(
                    user_id=user_id,
                    system_prompt=system_prompt,
                    metadata={"user_name": user_name}
                )
                self.logger.info(f"Created new conversation {conversation_id} for user {user_id}")
            
            # Record user message in conversation history
            if conversation_id:
                self.conversation_service.add_user_message(
                    conversation_id=conversation_id,
                    content=query
                )
            
            # 1. Retrieve relevant documents
            retrieved_docs = self.retrieve(query, top_k=top_k)

            # 2. Format documents into context
            context = self.format_retrieved_context(retrieved_docs)

            # 3. Get conversation history if requested
            conversation_context = ""
            if include_history and conversation_id:
                # Get recent conversation history
                history = self.conversation_service.get_formatted_history(
                    conversation_id=conversation_id,
                    limit=history_limit
                )
                
                # Format conversation history as context
                if history:
                    conversation_messages = []
                    for msg in history:
                        role_prefix = "User: " if msg["role"] == "user" else "Assistant: "
                        conversation_messages.append(f"{role_prefix}{msg['content']}")
                    
                    conversation_context = "Recent conversation:\n" + "\n".join(conversation_messages)
            
            # 4. Prepare prompts with both document and conversation context
            prompts = self.format_rag_prompt(
                query=query, 
                context=context,
                conversation_context=conversation_context if conversation_context else None,
                user_name=user_name
            )

            messages = [
                {"role": "system", "content": prompts["system_message"]},
                {"role": "user", "content": prompts["user_message"]}
            ]

            # Capture assistant response to store in history
            full_response = ""

            # Get streaming response from LLM
            async for chunk in llm_service.get_streaming_response(messages):
                # Accumulate full response
                full_response += chunk
                yield chunk
            
            # Record assistant response in conversation history
            if conversation_id:
                self.conversation_service.add_assistant_message(
                    conversation_id=conversation_id,
                    content=full_response
                )

        except Exception as e:
            self.logger.error(f"Error in streaming RAG response: {str(e)}")
            raise

    @staticmethod
    def format_rag_prompt(
        query: str, 
        context: str, 
        user_name: str = "Пользователь", 
        conversation_context: Optional[str] = None
    ) -> dict:
            """
            Формирует system и user prompt для RAG-бота WellDone
            Возвращает словарь с system_message и user_message
            
            Args:
                query: User query
                context: Document context from retrieval
                user_name: Name of the user
                conversation_context: Optional conversation history context
            """

            system_message = RAGService.get_system_message()

            user_prompt_template = (
                "Найди и опиши рецепт по запросу: \"{query}\"\n\n"
                "Если в документах найдены:\n"
                "- ингредиенты — выдели их\n"
                "- шаги приготовления — оформи по пунктам\n"
                "- советы, ссылки, заготовки — тоже включи, если есть\n"
            )
            
            # Include conversation history if available
            conversation_section = ""
            if conversation_context:
                conversation_section = f"Предыдущая часть разговора:\n{conversation_context}\n\n"

            formatted_user_prompt = (
                f"{user_name} спрашивает:\n\n"
                f"{conversation_section}"
                f"Context:\n{context}\n\n"
                f"{user_prompt_template.format(query=query)}"
            )

            return {
                "system_message": system_message,
                "user_message": formatted_user_prompt
            }

    @staticmethod
    def get_system_message():
        system_message = (
            "Ты — заботливый кулинарный ассистент школы WellDone.\n"
            "Твоя задача — помогать готовить вкусно, просто и уверенно,\n"
            "используя рецепты из материалов Маши Шелушенко.\n\n"
            "Отвечай как Маша:\n"
            "— на 'ты'\n"
            "— дружелюбно и с верой в успех\n"
            "— чётко: выделяй ингредиенты и шаги\n"
            "— добавляй совет или лайфхак, если он есть в документе\n"
            "— если есть фото — скажи, что его сейчас покажешь\n"
            "— учитывай предыдущую часть разговора, если она есть\n"
            "Если в документах нет советов, можешь добавить универсальный кулинарный совет или напоминание — "
            "в духе Маши Шелушенко. Говори на 'ты', поддерживай и вдохновляй."
            "Иногда заверши ответ короткой тёплой фразой или смайликом (например: «Удачи на кухне!» или «Я верю в тебя!»). "
            "Но не всегда — делай это по настроению.\n"
        )
        return system_message
