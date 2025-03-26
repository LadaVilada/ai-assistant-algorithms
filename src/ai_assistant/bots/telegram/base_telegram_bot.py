import asyncio
import json
import os
import tempfile
from typing import Dict, Any

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from telegram.constants import ChatAction

from ai_assistant.bots.base.base_bot import BaseBot
from ai_assistant.core.utils.logging import LoggingConfig
from ai_assistant.core.services.speech_service import SpeechService

# Define conversation states
AWAITING_QUERY = 1

class TelegramBot:
    """Base class for Telegram bot implementations using composition pattern."""
    
    def __init__(self, token: str, underlying_bot: BaseBot):
        """
        Initialize Telegram bot with an underlying bot implementation.
        
        Args:
            token: Telegram bot token
            underlying_bot: The bot implementation that handles the core logic
        """
        self.token = token
        self.bot = underlying_bot
        self.application = None
        self.logger = LoggingConfig.get_logger(__name__)
        self.last_results = {}
        self._accumulated_text = ""
        self._current_message = None
        self._last_update_time = 0.0
        self._update_interval = 0.5  # Assuming a default update_interval
        self.speech_service = SpeechService()

        self._message_parts = []
        self._current_part_index = 0

    @staticmethod
    def format_sources(sources: list) -> str:
        """Format sources for display."""
        if not sources:
            return "No sources available."

        formatted_sources = []
        for i, source in enumerate(sources, 1):
            formatted_sources.append(f"{i}. {source}")

        return "Sources:\n" + "\n".join(formatted_sources)

    async def start(self):
        """Initialize and start the Telegram bot."""
        self.application = Application.builder().token(self.token).build()
        
        # Add handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.application.add_handler(MessageHandler(filters.VOICE, self.handle_voice_message))
        
        # Start the bot
        await self.application.initialize()
        await self.application.start()

        # Use the application's run_polling method which manages its own event loop
        await self.application.run_polling(drop_pending_updates=True)

    async def stop(self):
        """Stop the Telegram bot gracefully."""
        if self.application:
            await self.application.stop()
            await self.application.shutdown()

    def run(self):
        """
        Run the bot in a completely synchronous manner.
        This approach avoids all the asyncio event loop conflicts.
        """
        try:
            self.logger.info("Starting Telegram bot...")

            # Create a new application instance
            self.application = Application.builder().token(self.token).build()

            # Register handlers
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(CommandHandler("help", self.help_command))
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
            self.application.add_handler(MessageHandler(filters.VOICE, self.handle_voice_message))

            # Use the application's run_polling method which manages its own event loop
            self.application.run_polling(drop_pending_updates=True)

        except KeyboardInterrupt:
            self.logger.info("Bot stopped by user")
        except Exception as e:
            self.logger.error(f"Error running bot: {e}")
            raise

    @staticmethod
    async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        await update.message.reply_text(
            "👋 Welcome! I'm your AI-powered algorithm assistant. "
            "Complex problems? No worries—I'll help you break them down into simple, "
            "logical steps. Whether it's data structures, coding challenges, or algorithm design, "
            "let's tackle them one piece at a time. Keep coding, keep learning, and let's build something great! 🚀"
        )

    @staticmethod
    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        await update.message.reply_text(
            "I can help you with algorithm-related questions. "
            "Just ask your question, and I'll search through my knowledge base to find the answer.\n\n"
            "You can send your questions as text or voice messages.\n"
            "You can also use /sources to see the sources for my last answer."
        )

    async def handle_voice_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming voice messages."""
        try:
            message = update.message
            if not message or not message.voice:
                self.logger.warning("Received update without voice message")
                return

            # Get chat ID and user info
            chat_id = message.chat_id
            user_id = str(message.from_user.id)
            username = message.from_user.username or "Anonymous"

            # Log incoming voice message details
            self.logger.info(f"Received voice message from {username} (ID: {user_id})")
            self.logger.info(f"Voice message details: duration={message.voice.duration}, file_size={message.voice.file_size}")

            # Send typing indicator
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

            # Get the voice file
            voice_file = await context.bot.get_file(message.voice.file_id)
            self.logger.info(f"Retrieved voice file: {voice_file.file_path}")

            # Create a temporary file to store the voice message
            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_file:
                temp_path = temp_file.name
                self.logger.info(f"Created temporary file: {temp_path}")

                try:
                    # Download the voice file
                    await voice_file.download_to_drive(temp_path)
                    self.logger.info(f"Downloaded voice file to {temp_path}")

                    # Verify file exists and has content
                    if not os.path.exists(temp_path):
                        raise FileNotFoundError(f"Temporary file {temp_path} was not created")
                    
                    file_size = os.path.getsize(temp_path)
                    self.logger.info(f"Voice file size: {file_size} bytes")

                    if file_size == 0:
                        raise ValueError("Downloaded voice file is empty")

                    # Transcribe the voice message
                    self.logger.info("Starting voice transcription...")
                    transcribed_text = await self.speech_service.transcribe_audio(temp_path)
                    self.logger.info(f"Transcribed text: {transcribed_text}")

                    if not transcribed_text:
                        raise ValueError("No text was transcribed from the voice message")

                    # Process the transcribed text
                    await self.handle_message(update, context, transcribed_text)

                except Exception as e:
                    self.logger.error(f"Error processing voice message: {str(e)}")
                    await self._handle_error(context, chat_id, f"Error processing voice message: {str(e)}")
                finally:
                    # Clean up the temporary file
                    try:
                        os.unlink(temp_path)
                        self.logger.info(f"Cleaned up temporary file: {temp_path}")
                    except Exception as e:
                        self.logger.error(f"Error cleaning up temporary file: {str(e)}")

        except Exception as e:
            self.logger.error(f"Error handling voice message: {str(e)}")
            await self._handle_error(context, chat_id, str(e))

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str = None):
        """Handle incoming messages with streaming support."""
        try:
            message = update.message
            if not message:
                self.logger.warning("Received update without message")
                return

            # Use provided text or get from message
            message_text = text or message.text
            if not message_text:
                self.logger.warning("Received message without text")
                return

            # Get chat ID and user info
            chat_id = message.chat_id
            user_id = str(message.from_user.id)
            username = message.from_user.username or "Anonymous"

            # Log incoming message
            self.logger.info(f"Received message from {username} (ID: {user_id}): {message_text}")

            # Send typing indicator
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

            # Reset state for new message
            self._accumulated_text = ""
            self._current_message = None
            self._last_update_time = 0.0

            # Process the message and get streaming response
            try:
                # Stream response directly without awaiting
                async for chunk in self.bot.stream_response(message_text):
                    if chunk:  # Only process non-empty chunks
                        self._accumulated_text += chunk
                        
                        # Update message with rate limiting
                        await self._update_message(context, chat_id)

                # Final update to ensure all text is shown
                if self._current_message and self._accumulated_text:
                    await self._current_message.edit_text(
                        text=self._accumulated_text,
                        parse_mode='HTML'
                    )

                    # Final update if needed
                    await self._update_message(context, chat_id)

                    # Finalize messages with correct part numbering
                    await self._finalize_messages(context, chat_id)

            except Exception as e:
                self.logger.error(f"Error during streaming response: {str(e)}")
                await self._handle_error(context, chat_id, str(e))
                return

            # Clear state
            self._current_message = None
            self._accumulated_text = ""

            # Log successful response
            self.logger.info(f"Successfully processed message for {username} (ID: {user_id})")

        except Exception as e:
            self.logger.error(f"Error handling message: {str(e)}")
            await self._handle_error(context, chat_id, str(e))


    async def _update_message(self, context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
        """Update the message with rate limiting and error handling."""
        import time
        current_time = time.time()

        # Check if enough time has passed since last update
        if current_time - self._last_update_time < self._update_interval:
            return

        # Don't update if text is empty
        if not self._accumulated_text:
            self.logger.warning("Attempted to update message with empty text")
            return

        # Constants for Telegram limits
        MAX_MESSAGE_LENGTH = 4000  # Using 4000 to be safe (actual limit is 4096)

        try:
            if not self._current_message:
                # Check if text is going to be too long for a single message
                if len(self._accumulated_text) > MAX_MESSAGE_LENGTH:
                    # Initialize message parts tracking if not already done
                    if not hasattr(self, '_message_parts'):
                        self._message_parts = []
                        self._current_part_index = 0

                    # Send the first part
                    first_part = self._accumulated_text[:MAX_MESSAGE_LENGTH]
                    self._current_message = await context.bot.send_message(
                        chat_id=chat_id,
                        text=first_part,
                        parse_mode='HTML',
                        disable_web_page_preview=True
                    )

                    # Store this part
                    self._message_parts.append({
                        'message': self._current_message,
                        'text': first_part
                    })

                    # Set up for next part
                    self._accumulated_text = self._accumulated_text[MAX_MESSAGE_LENGTH:]
                    self._current_part_index += 1
                    self._current_message = None

                    # Continue with the next part immediately
                    await self._update_message(context, chat_id)
                else:
                    # If it fits in one message, just send it normally
                    self._current_message = await context.bot.send_message(
                        chat_id=chat_id,
                        text=self._accumulated_text,
                        parse_mode='HTML',
                        disable_web_page_preview=True
                    )
            else:
                # Check if the updated text will be too long
                if len(self._accumulated_text) > MAX_MESSAGE_LENGTH:
                    # If we haven't started tracking parts yet
                    if not hasattr(self, '_message_parts'):
                        self._message_parts = []
                        self._current_part_index = 0

                        # Add current message as first part
                        self._message_parts.append({
                            'message': self._current_message,
                            'text': self._accumulated_text[:MAX_MESSAGE_LENGTH]
                        })

                        # Update the current message with the first part
                        await self._current_message.edit_text(
                            text=self._accumulated_text[:MAX_MESSAGE_LENGTH],
                            parse_mode='HTML',
                            disable_web_page_preview=True
                        )

                        # Set up for next part
                        self._accumulated_text = self._accumulated_text[MAX_MESSAGE_LENGTH:]
                        self._current_part_index += 1
                        self._current_message = None

                        # Continue with the next part immediately
                        await self._update_message(context, chat_id)
                    else:
                        # We're already tracking parts, so update the current part
                        # If we have a current message, update it
                        if self._current_message:
                            # Update with as much text as will fit
                            update_text = self._accumulated_text[:MAX_MESSAGE_LENGTH]

                            await self._current_message.edit_text(
                                text=update_text,
                                parse_mode='HTML',
                                disable_web_page_preview=True
                            )

                            # Update part info
                            if self._current_part_index < len(self._message_parts):
                                self._message_parts[self._current_part_index]['text'] = update_text
                            else:
                                self._message_parts.append({
                                    'message': self._current_message,
                                    'text': update_text
                                })

                            # If there's still more text, set up for next part
                            if len(self._accumulated_text) > MAX_MESSAGE_LENGTH:
                                self._accumulated_text = self._accumulated_text[MAX_MESSAGE_LENGTH:]
                                self._current_part_index += 1
                                self._current_message = None

                                # Continue with the next part immediately
                                await self._update_message(context, chat_id)
                else:
                    # Text fits in current message, just update it
                    await self._current_message.edit_text(
                        text=self._accumulated_text,
                        parse_mode='HTML',
                        disable_web_page_preview=True
                    )

            self._last_update_time = current_time

        except Exception as e:
            self.logger.error(f"Error updating message: {str(e)}")
            # Handle different types of errors
            if "Message is too long" in str(e):
                # If message is too long, split it
                if not hasattr(self, '_message_parts'):
                    self._message_parts = []
                    self._current_part_index = 0

                # If we have a current message, add it to parts
                if self._current_message and self._current_part_index == len(self._message_parts):
                    self._message_parts.append({
                        'message': self._current_message,
                        'text': self._accumulated_text[:MAX_MESSAGE_LENGTH]
                    })

                # Move to the next part
                self._accumulated_text = self._accumulated_text[MAX_MESSAGE_LENGTH:]
                self._current_part_index += 1
                self._current_message = None

                # Continue with the next part
                await self._update_message(context, chat_id)
            elif "Message not modified" in str(e):
                # Ignore this error as it's not critical
                pass
            else:
                # For other errors, try to recover
                await self._handle_error(context, chat_id, str(e))

async def _finalize_messages(self) -> None:
    """Finalize messages after streaming is complete by updating part numbers."""
    try:
        # If we don't have message parts, nothing to do
        if not hasattr(self, '_message_parts') or not self._message_parts:
            return

        # If we have a current message that's not in parts yet, add it
        if self._current_message and self._accumulated_text:
            self._message_parts.append({
                'message': self._current_message,
                'text': self._accumulated_text
            })

        # Update all parts with correct part numbers
        total_parts = len(self._message_parts)

        for i, part_info in enumerate(self._message_parts):
            try:
                message = part_info['message']
                text = part_info['text']

                # Add part numbers
                if total_parts > 1:
                    part_text = f"Part {i+1}/{total_parts}\n\n{text}"
                else:
                    part_text = text

                # Update the message
                await message.edit_text(
                    text=part_text,
                    parse_mode='HTML',
                    disable_web_page_preview=True
                )
            except Exception as e:
                self.logger.error(f"Error updating part {i+1}: {str(e)}")
                # Continue with other parts even if one fails

        # Clear the parts tracking
        self._message_parts = []
        self._current_part_index = 0

    except Exception as e:
        self.logger.error(f"Error finalizing messages: {str(e)}")

    # async def _update_message(self, context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    #     """Update the message with rate limiting and error handling."""
    #     import time
    #     current_time = time.time()
    #
    #     # Check if enough time has passed since last update
    #     if current_time - self._last_update_time < self._update_interval:
    #         return
    #
    #     # Don't update if text is empty
    #     if not self._accumulated_text:
    #         self.logger.warning("Attempted to update message with empty text")
    #         return
    #
    #     try:
    #         if not self._current_message:
    #             # Create new message
    #             self._current_message = await context.bot.send_message(
    #                 chat_id=chat_id,
    #                 text=self._accumulated_text,
    #                 parse_mode='HTML',
    #                 disable_web_page_preview=True
    #             )
    #         else:
    #             # Update existing message
    #             await self._current_message.edit_text(
    #                 text=self._accumulated_text,
    #                 parse_mode='HTML',
    #                 disable_web_page_preview=True
    #             )
    #
    #         self._last_update_time = current_time
    #
    #     except Exception as e:
    #         self.logger.error(f"Error updating message: {str(e)}")
    #         # Handle different types of errors
    #         if "Message is too long" in str(e):
    #             # If message is too long, create a new one
    #             self._current_message = None
    #             self._accumulated_text = self._accumulated_text[:4000] + "..."
    #             await self._update_message(context, chat_id)
    #         elif "Message not modified" in str(e):
    #             # Ignore this error as it's not critical
    #             pass
    #         else:
    #             # For other errors, try to recover
    #             await self._handle_error(context, chat_id, str(e))

    async def _handle_error(self, context: ContextTypes.DEFAULT_TYPE, chat_id: int, error_msg: str = None) -> None:
        """Handle errors gracefully with detailed error messages."""
        error_message = (
            "Sorry, I encountered an error processing your message.\n"
            "Please try again or rephrase your question.\n"
            f"Error: {error_msg if error_msg else 'Unknown error'}"
        )
        
        try:
            if self._current_message:
                await self._current_message.edit_text(
                    text=error_message,
                    parse_mode='HTML'
                )
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=error_message,
                    parse_mode='HTML'
                )
        except Exception as e:
            self.logger.error(f"Error sending error message: {str(e)}")
            # Fallback to plain text if HTML parsing fails
            await context.bot.send_message(
                chat_id=chat_id,
                text=error_message
            )


