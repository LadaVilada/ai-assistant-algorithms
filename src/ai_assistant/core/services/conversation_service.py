"""Conversation history service for managing user-assistant interactions."""

import logging
from typing import List, Dict, Optional, Any

from ai_assistant.core.infrastructure.dynamo_db import DynamoDBClient
from ai_assistant.core.utils.logging import LoggingConfig

class ConversationService:
    """Service for managing conversation history."""
    
    def __init__(self, db_client: Optional[DynamoDBClient] = None):
        """Initialize the conversation service.
        
        Args:
            db_client: DynamoDB client (creates one if not provided)
        """
        # Get a logger for this service
        self.logger = LoggingConfig.get_logger(__name__)
        self.logger.info("Conversation Service initializing")
        
        # Initialize DynamoDB client if not provided
        if db_client is None:
            self.db_client = DynamoDBClient()
        else:
            self.db_client = db_client
            
        self.logger.info("Conversation Service initialized")
    
    def create_conversation(
        self,
        user_id: str,
        system_prompt: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new conversation.
        
        Args:
            user_id: Identifier for the user
            system_prompt: Optional system prompt to start the conversation
            metadata: Additional metadata to store with the conversation
            
        Returns:
            The new conversation ID
        """
        try:
            conversation_id = self.db_client.create_conversation(
                user_id=user_id,
                system_message=system_prompt,
                metadata=metadata
            )
            
            self.logger.info(f"Created conversation {conversation_id} for user {user_id}")
            return conversation_id
        except Exception as e:
            self.logger.error(f"Error creating conversation: {e}")
            raise
    
    def add_user_message(
        self,
        conversation_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Add a user message to a conversation.
        
        Args:
            conversation_id: Conversation identifier
            content: Message content
            metadata: Additional metadata for the message
            
        Returns:
            The created message item
        """
        try:
            self.logger.info(f"Calling add_message for {conversation_id}")

            message = self.db_client.add_message(
                conversation_id=conversation_id,
                role="user",
                content=content,
                metadata=metadata
            )
            
            self.logger.info(f"Added user message to conversation {conversation_id}")
            return message
        except Exception as e:
            self.logger.error(f"Error adding user message: {e}")
            raise
    
    def add_assistant_message(
        self,
        conversation_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Add an assistant message to a conversation.
        
        Args:
            conversation_id: Conversation identifier
            content: Message content
            metadata: Additional metadata for the message
            
        Returns:
            The created message item
        """
        try:
            message = self.db_client.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=content,
                metadata=metadata
            )
            
            self.logger.info(f"Added assistant message to conversation {conversation_id}")
            return message
        except Exception as e:
            self.logger.error(f"Error adding assistant message: {e}")
            raise
    
    def get_conversation_history(
        self,
        conversation_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get the conversation history.
        
        Args:
            conversation_id: Conversation identifier
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of message items
        """
        try:
            history = self.db_client.get_conversation_history(
                conversation_id=conversation_id,
                limit=limit
            )
            
            self.logger.info(f"Retrieved {len(history)} messages for conversation {conversation_id}")
            return history
        except Exception as e:
            self.logger.error(f"Error retrieving conversation history: {e}")
            return []
    
    def get_formatted_history(
        self,
        conversation_id: str,
        limit: int = 20
    ) -> List[Dict[str, str]]:
        """Get conversation history formatted for LLM input.
        
        Args:
            conversation_id: Conversation identifier
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of messages formatted for LLM
        """
        try:
            formatted_history = self.db_client.get_formatted_history(
                conversation_id=conversation_id,
                limit=limit
            )
            
            self.logger.info(f"Retrieved formatted history for conversation {conversation_id}")
            return formatted_history
        except Exception as e:
            self.logger.error(f"Error retrieving formatted conversation history: {e}")
            return []
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation.
        
        Args:
            conversation_id: Conversation identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            success = self.db_client.delete_conversation(conversation_id=conversation_id)
            
            if success:
                self.logger.info(f"Deleted conversation {conversation_id}")
            else:
                self.logger.warning(f"Failed to delete conversation {conversation_id}")
                
            return success
        except Exception as e:
            self.logger.error(f"Error deleting conversation: {e}")
            return False