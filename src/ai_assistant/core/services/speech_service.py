"""Service for handling speech-to-text conversion using OpenAI's speech-to-text models."""
import logging
from typing import Optional
from openai import OpenAI
from ai_assistant.core.utils.logging import LoggingConfig

class SpeechService:
    """Service for handling speech-to-text conversion."""

    def __init__(self, client: Optional[OpenAI] = None):
        """Initialize the speech service.
        
        Args:
            client: Optional OpenAI client instance
        """
        self.logger = LoggingConfig.get_logger(__name__)
        self.client = client or OpenAI()
        self.logger.info("Speech Service initialized")

    async def transcribe_audio(self, audio_file_path: str, model: str = "gpt-4o-transcribe") -> str:
        """Transcribe audio file to text using OpenAI's models.
        
        Args:
            audio_file_path: Path to the audio file
            model: Model to use for transcription (gpt-4o-transcribe or gpt-4o-mini-transcribe)
            
        Returns:
            Transcribed text
        """
        try:
            with open(audio_file_path, "rb") as audio_file:
                response = await self.client.audio.transcriptions.create(
                    model=model,
                    file=audio_file
                )
                return response.text
        except Exception as e:
            self.logger.error(f"Error transcribing audio: {str(e)}")
            raise 