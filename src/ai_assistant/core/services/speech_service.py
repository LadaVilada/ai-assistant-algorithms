"""Service for handling speech-to-text conversion using OpenAI's speech-to-text models."""
import logging
import os
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

    async def transcribe_audio(self, audio_file_path: str, model: str = "whisper-1") -> str:
        """Transcribe audio file to text using OpenAI's models.
        
        Args:
            audio_file_path: Path to the audio file
            model: Model to use for transcription (whisper-1)
            
        Returns:
            Transcribed text
        """
        try:
            # Verify file exists
            if not os.path.exists(audio_file_path):
                raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

            # Verify file size
            file_size = os.path.getsize(audio_file_path)
            if file_size == 0:
                raise ValueError(f"Audio file is empty: {audio_file_path}")

            self.logger.info(f"Transcribing audio file: {audio_file_path} (size: {file_size} bytes)")

            # Open and transcribe the audio file
            with open(audio_file_path, "rb") as audio_file:
                response = await self.client.audio.transcriptions.create(
                    model=model,
                    file=audio_file,
                    language="en"  # Specify language for better accuracy
                )
                
                if not response.text:
                    raise ValueError("No text was transcribed from the audio")
                
                self.logger.info(f"Successfully transcribed audio: {response.text[:100]}...")
                return response.text

        except Exception as e:
            self.logger.error(f"Error transcribing audio: {str(e)}")
            raise 