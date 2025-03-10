"""Service for interacting with large language models."""

import logging
from typing import Optional

from openai import OpenAI

from .config import config

logger = logging.getLogger(__name__)


class LLMService:
    """Service for interacting with large language models."""
    
    def __init__(self, model_name: str = None):
        """Initialize the LLM service.
        
        Args:
            model_name: Name of the LLM to use
        """
        self.model_name = model_name or config.model_name
        self.api_key = config.openai_api_key
        self.client = OpenAI(api_key=self.api_key)
        logger.info(f"Using OpenAI model: {self.model_name}")
    
    def generate_completion(
        self, 
        prompt: str,
        system_message: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1000
    ) -> str:
        """Generate a completion from the LLM.
        
        Args:
            prompt: User prompt
            system_message: Optional system message
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text
        """
        try:
            messages = []
            
            # Add system message if provided
            if system_message:
                messages.append({"role": "system", "content": system_message})
                
            # Add user prompt
            messages.append({"role": "user", "content": prompt})
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating completion: {e}")
            # Return a graceful error message
            return (
                "I'm sorry, I encountered an error while generating a response. "
                "Please try again later."
            )