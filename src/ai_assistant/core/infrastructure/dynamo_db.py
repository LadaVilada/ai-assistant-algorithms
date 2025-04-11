"""DynamoDB client for conversation history storage."""

import os
import logging
import time
import uuid
import json
from typing import Dict, List, Optional, Any

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

class DynamoDBClient:
    """DynamoDB client for conversation history storage."""
    
    def __init__(
        self,
        table_name: str = None,
        aws_region: str = None,
        aws_access_key_id: str = None,
        aws_secret_access_key: str = None,
    ):
        """Initialize the DynamoDB client.
        
        Args:
            table_name: DynamoDB table name (defaults to DYNAMODB_TABLE_NAME env var)
            aws_region: AWS region (defaults to AWS_REGION env var)
            aws_access_key_id: AWS access key ID (defaults to AWS_ACCESS_KEY_ID env var)
            aws_secret_access_key: AWS secret access key (defaults to AWS_SECRET_ACCESS_KEY env var)
        """
        # Get credentials from parameters or environment variables
        self.table_name = table_name or os.getenv("DYNAMODB_TABLE_NAME", "conversation-history")
        aws_region = aws_region or os.getenv("AWS_REGION", "us-east-1")
        aws_access_key_id = aws_access_key_id or os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_access_key = aws_secret_access_key or os.getenv("AWS_SECRET_ACCESS_KEY")
        
        # Initialize DynamoDB client
        if aws_access_key_id and aws_secret_access_key:
            self.dynamodb = boto3.resource(
                'dynamodb',
                region_name=aws_region,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key
            )
        else:
            self.dynamodb = boto3.resource('dynamodb', region_name=aws_region)
        
        # Get or create table
        self.table = self._get_or_create_table()
        
    def _get_or_create_table(self):
        """Get the DynamoDB table, creating it if it doesn't exist."""
        try:
            # Check if table exists
            table = self.dynamodb.Table(self.table_name)
            table.table_status  # This will raise if table doesn't exist
            logger.info(f"Connected to DynamoDB table: {self.table_name}")
            return table
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                logger.info(f"Table {self.table_name} does not exist, creating...")
                # Create the table
                table = self.dynamodb.create_table(
                    TableName=self.table_name,
                    KeySchema=[
                        {
                            'AttributeName': 'conversation_id',
                            'KeyType': 'HASH'  # Partition key
                        },
                        {
                            'AttributeName': 'timestamp',
                            'KeyType': 'RANGE'  # Sort key
                        }
                    ],
                    AttributeDefinitions=[
                        {
                            'AttributeName': 'conversation_id',
                            'AttributeType': 'S'
                        },
                        {
                            'AttributeName': 'timestamp',
                            'AttributeType': 'N'
                        }
                    ],
                    BillingMode='PAY_PER_REQUEST'
                )
                
                # Wait for table to be created
                table.meta.client.get_waiter('table_exists').wait(TableName=self.table_name)
                logger.info(f"Created DynamoDB table: {self.table_name}")
                return table
            else:
                logger.error(f"Error connecting to DynamoDB: {e}")
                raise
    
    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Add a message to the conversation history.
        
        Args:
            conversation_id: Unique identifier for the conversation
            role: Message role (user, assistant, system)
            content: Message content
            metadata: Additional metadata for the message
            
        Returns:
            The created message item
        """
        timestamp = int(time.time() * 1000)  # Current time in milliseconds
        
        # Create message item
        item = {
            'conversation_id': conversation_id,
            'timestamp': timestamp,
            'role': role,
            'content': content,
            'message_id': str(uuid.uuid4()),
        }
        
        # Add metadata if provided
        if metadata:
            item['metadata'] = metadata
        
        try:
            # Add message to DynamoDB
            self.table.put_item(Item=item)
            logger.info(f"Added message to conversation {conversation_id}")
            return item
        except Exception as e:
            logger.error(f"Error adding message to DynamoDB: {e}")
            raise
    
    def get_conversation_history(
        self,
        conversation_id: str,
        limit: int = 20,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get the conversation history for a specific conversation.
        
        Args:
            conversation_id: Unique identifier for the conversation
            limit: Maximum number of messages to retrieve
            start_time: Optional start time for filtering messages (milliseconds)
            end_time: Optional end time for filtering messages (milliseconds)
            
        Returns:
            List of message items in chronological order
        """
        try:
            # Base query for the conversation ID
            key_condition = Key('conversation_id').eq(conversation_id)
            
            # Add time range filter if provided
            if start_time and end_time:
                key_condition = key_condition & Key('timestamp').between(start_time, end_time)
            elif start_time:
                key_condition = key_condition & Key('timestamp').gte(start_time)
            elif end_time:
                key_condition = key_condition & Key('timestamp').lte(end_time)
            
            # Query DynamoDB
            response = self.table.query(
                KeyConditionExpression=key_condition,
                Limit=limit,
                ScanIndexForward=True  # true = ascending order by timestamp
            )
            
            logger.info(f"Retrieved {len(response['Items'])} messages for conversation {conversation_id}")
            return response['Items']
        except Exception as e:
            logger.error(f"Error retrieving conversation history from DynamoDB: {e}")
            return []
    
    def get_formatted_history(
        self,
        conversation_id: str,
        limit: int = 20
    ) -> List[Dict[str, str]]:
        """Get conversation history formatted for LLM context.
        
        Args:
            conversation_id: Unique identifier for the conversation
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of message dictionaries in the format expected by OpenAI API
        """
        messages = self.get_conversation_history(conversation_id, limit=limit)
        
        # Format for LLM context
        formatted_messages = []
        for message in messages:
            formatted_messages.append({
                'role': message['role'],
                'content': message['content']
            })
        
        return formatted_messages
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete all messages for a conversation.
        
        Args:
            conversation_id: Unique identifier for the conversation
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # First, get all messages for the conversation
            messages = self.get_conversation_history(conversation_id, limit=1000)
            
            # Batch delete items
            with self.table.batch_writer() as batch:
                for message in messages:
                    batch.delete_item(
                        Key={
                            'conversation_id': message['conversation_id'],
                            'timestamp': message['timestamp']
                        }
                    )
            
            logger.info(f"Deleted conversation {conversation_id} with {len(messages)} messages")
            return True
        except Exception as e:
            logger.error(f"Error deleting conversation from DynamoDB: {e}")
            return False
    
    def create_conversation(
        self,
        user_id: str,
        system_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new conversation with optional system message.
        
        Args:
            user_id: User identifier
            system_message: Optional system message to start the conversation
            metadata: Additional metadata for the conversation
            
        Returns:
            The new conversation ID
        """
        conversation_id = str(uuid.uuid4())
        
        # Add system message if provided
        if system_message:
            self.add_message(
                conversation_id=conversation_id,
                role='system',
                content=system_message,
                metadata={
                    'user_id': user_id,
                    **(metadata or {})
                }
            )
        
        logger.info(f"Created new conversation {conversation_id} for user {user_id}")
        return conversation_id