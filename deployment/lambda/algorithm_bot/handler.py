import json
import os
import uuid
from typing import Optional

import boto3
import sys
from openai import OpenAI
from pydantic import BaseModel, ValidationError

from ai_assistant.bots.algorithms.bot import AlgorithmsBot
from ai_assistant.bots.telegram.bot import TelegramAlgorithmsBot

# Ensure AWS Lambda finds dependencies
sys.path.insert(0, os.path.join(os.getcwd()))

# Load API key securely
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("Missing OpenAI API key!")

# Initialize OpenAI client with API key (without additional parameters)
client = OpenAI(api_key=api_key)

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb', region_name="us-east-1")
conversation_table = dynamodb.Table('ConversationHistory')


# Define input validation using Pydantic
class QueryModel(BaseModel):
    question: str
    model: str = "gpt-4o-mini"  # Default to more efficient model
    session_id: Optional[str] = None
    user_id: Optional[str] = None

def get_conversation_history(session_id, limit=5):
    """Retrieve conversation history from DynamoDB"""
    try:
        response = conversation_table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('session_id').eq(session_id),
            ScanIndexForward=True,  # Sort by timestamp ascending
            Limit=limit
        )
        return response.get('Items', [])
    except Exception as e:
        print(f"Error retrieving conversation history: {e}")
        return []


import time
import boto3


def store_conversation(session_id, user_id, user_message, assistant_response):
    """Store conversation in DynamoDB"""
    try:
        timestamp = int(time.time())
        expiry_time = timestamp + (30 * 24 * 60 * 60)  # 30 days from now

        item = {
            'session_id': session_id,
            'timestamp': timestamp,
            'user_id': user_id,
            'user_message': user_message,
            'assistant_response': assistant_response,
            'ttl': expiry_time
        }

        print(f"[LOG] Writing to DynamoDB: {item}")  # Debugging line

        conversation_table.put_item(Item=item)  # Insert into DynamoDB

        return True
    except Exception as e:
        print(f"[ERROR] Failed to store conversation: {e}")
        return False

def lambda_handler(event, context):
    try:
        # Parse request body
        body = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
        query_data = QueryModel(**body)  # Validates input with Pydantic

        # Get or generate session_id
        session_id = body.get('session_id', str(uuid.uuid4()))
        user_id = body.get('user_id', uuid.uuid4())
        # 'anonymous'

        # Get conversation history
        history = get_conversation_history(session_id)

        # Prepare messages including history
        messages = [{"role": "system", "content": "You are a helpful assistant."}]

        # Add conversation history to messages
        for entry in history:
            messages.append({"role": "user", "content": entry["user_message"]})
            messages.append({"role": "assistant", "content": entry["assistant_response"]})

        # Add current question
        messages.append({"role": "user", "content": query_data.question})

    except (KeyError, TypeError, json.JSONDecodeError, ValidationError) as e:
        return {
            "statusCode": 400,
            "body": json.dumps({
                "error": "Invalid or missing 'question' field",
                "details": str(e)
            })
        }

    # Call OpenAI API with latest client format
    try:
        # Using the messages array that includes conversation history
        response = client.chat.completions.create(
            model=query_data.model,
            messages=messages
        )

        # Access response properties using the new structure
        answer = response.choices[0].message.content

        # Store the conversation - ADD THIS LINE
        store_conversation(session_id, user_id, query_data.question, answer)

        # Include some metadata in response
        return {
            "statusCode": 200,
            "body": json.dumps({
                "answer": answer,
                "model": query_data.model,
                "session_id": session_id,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            })
        }

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
