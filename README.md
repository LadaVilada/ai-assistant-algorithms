# AI Assistant with DynamoDB Conversation History

This project implements an AI assistant with retrieval-augmented generation (RAG) capabilities and conversation history storage in DynamoDB.

## Installation

```bash
cd path_to_your_project    # Change to your project directory
source venv/bin/activate   # Activate the virtual environment
poetry --version           # Verify Poetry is available
poetry install --no-root   # Install dependencies
```

## Configuration

Set the following environment variables:

```bash
# OpenAI API
export OPENAI_API_KEY=your-api-key

# Pinecone Vector Database
export PINECONE_API_KEY=your-pinecone-api-key
export PINECONE_ENVIRONMENT=your-pinecone-environment

# AWS DynamoDB (for conversation history)
export AWS_ACCESS_KEY_ID=your-aws-access-key
export AWS_SECRET_ACCESS_KEY=your-aws-secret-key
export AWS_REGION=us-east-1  # or your preferred region
export DYNAMODB_TABLE_NAME=conversation-history
```

## Setting Up DynamoDB

Create the DynamoDB table for conversation history:

```bash
# Create the DynamoDB table
poetry run python -m ai_assistant.scripts.dynamodb.create_table
```

## Running the Assistant

```bash
# Run the interactive assistant
poetry run python main.py

# Ingest documents for RAG
poetry run python main.py --ingest data/algorithms/

# Run tests
poetry run pytest
```

## Architecture

### Components

1. **RAG Service**: Core retrieval-augmented generation service
2. **Conversation Service**: Manages conversation history
3. **DynamoDB Client**: Interface for storing/retrieving conversations
4. **Vector Store**: Pinecone vector database for document embeddings
5. **Telegram Bot**: User interface via Telegram

### Conversation Storage Schema

The DynamoDB table has the following structure:

- **Partition Key**: `conversation_id` (String)
- **Sort Key**: `timestamp` (Number)
- **Attributes**:
  - `role` (String): "user", "assistant", or "system"
  - `content` (String): Message content
  - `message_id` (String): Unique message identifier
  - `metadata` (Map): Optional metadata about the message

## Features

- Retrieval-augmented generation with Pinecone vector database
- Persistent conversation history in DynamoDB
- Context-aware responses using previous conversation
- Support for multiple platforms via modular architecture
- Telegram bot integration with streaming responses
- Voice message processing

## License

MIT