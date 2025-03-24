"""Configuration module for Algorithm Learning Agent."""

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()

import os

class AgentConfig(BaseModel):
    """Configuration for the Algorithm Learning Agent."""
    
    # API Keys and external services
    openai_api_key: str = Field(default=os.getenv("OPENAI_API_KEY", ""))
    pinecone_api_key: str = Field(default=os.getenv("PINECONE_API_KEY", ""))
    pinecone_environment: str = Field(
        default=os.getenv("PINECONE_ENVIRONMENT", "")
    )
    
    # Model configuration
    model_name: str = Field(default=os.getenv("MODEL_NAME", "gpt-4"))
    embedding_model: str = Field(
        default=os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")
    )
    
    # Storage paths
    pdf_storage_path: Path = Field(
        default=Path(os.getenv("PDF_STORAGE_PATH", "./storage/data"))
    )
    
    # Vector database settings
    index_name: str = Field(
        default=os.getenv("INDEX_NAME", "algorithm-assistant")
    )
    vector_dimension: int = Field(default=1536)  # Default for OpenAI embeddings
    
    # Chunking settings
    chunk_size: int = Field(default=1000)
    chunk_overlap: int = Field(default=200)
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"


# Create singleton configuration instance
config = AgentConfig()