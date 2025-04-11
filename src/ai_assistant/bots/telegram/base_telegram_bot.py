import os
import tempfile
import re

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from ai_assistant.bots.base.base_bot import BaseBot
from ai_assistant.core.services.speech_service import SpeechService
from ai_assistant.core.utils.logging import LoggingConfig

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
        self._has_formatting_error = False  # Track if we encountered formatting errors
        self.token = token
        self.bot = underlying_bot
        self.application = None
        self.last_results = {}
        self._accumulated_text = ""
        self._raw_accumulated_text = ""
        self._current_message = None
        self._last_update_time = 0.0
        self._update_interval = 0.5  # Assuming a default update_interval
        self.speech_service = SpeechService()

        # Logging configuration
        self.logger = LoggingConfig.get_logger(__name__)
        self.logger.info("Base Telegram bot initialized")

        # Initialize message parts for splitting long messages
        self._message_parts = []
        self._current_part_index = 0

        # Track last sent text to avoid redundant edits
        self._last_sent_text = ""

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
            # Run polling (blocks until stopped)
            self.application.run_polling(drop_pending_updates=True)

        except KeyboardInterrupt:
            self.logger.info("Bot stopped by user")
        except Exception as e:
            self.logger.error(f"Error running bot: {e}")
            raise

    @staticmethod
    async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""

        user = update.message.from_user
        name = user.first_name or user.username or "Дорогая"

        context.user_data["name"] = name

        await update.message.reply_text(
            f"👋 *Привет, и добро пожаловать на новый поток Гастрономии!*\n\n"
            f"*{name}*, я очень рада, что ты здесь 🧡\n\n"
            "Спрашивай всё, что касается заготовок, вкусных решений и кулинарной красоты. "
            "Про чеснок в масле, *волшебные маринады* или тарелку как в ресторане — подскажу с радостью.\n\n"
            "_Ну что, достаём контейнеры и наводим красоту?_ ✨",
            parse_mode='Markdown'
        )



    @staticmethod
    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""

        await update.message.reply_text(
            "🧑‍🍳 Я помогу тебе с вопросами по заготовкам, рецептам, красивой сервировке и заморозке. "
            "Просто задай свой вопрос — текстом или голосом.\n\n"
            "Примеры:\n"
            "• Как правильно замораживать брокколи?\n"
            "• Что приготовить на 3 дня из курицы?\n"
            "• Рецепт базиликового масла\n"
            "• Как красиво выложить овощи на тарелке?\n\n"
            "Я рядом, чтобы подсказывать тебе так, как подсказываю своим девчонкам на курсе WellDone. \n\n"
            "Будет вкусно, красиво и легко, обещаю 💛 \n\n"
            "_Если хочешь увидеть, откуда взят ответ — напиши /sources._",
            parse_mode='Markdown'
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

                    # Process the transcribed file as a regular message
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
        """Handle incoming messages with streaming support and Markdown formatting."""
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

            # Indicate bot is typing
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

            # Reset state for new message
            self._accumulated_text = ""
            self._raw_accumulated_text = ""
            self._current_message = None
            self._last_update_time = 0.0
            self._has_formatting_error = False
            self._last_sent_text = ""
            image_url = None

            # Stream the response from the underlying bot and send it incrementally
            try:
                async for chunk in self.bot.stream_response(message_text):
                    if isinstance(chunk, dict) and "__image_url__" in chunk:
                        # Extract the image URL from the special marker
                        image_url = chunk["__image_url__"]
                        self.logger.warning(f"Image URL found in chunk! {image_url}")
                        continue  # skip processing this as text
                    if chunk:  # Only process non-empty chunks
                        self._raw_accumulated_text += chunk
                        self.logger.warning(f"Processing non empty chunk, errors update! {self._has_formatting_error}")

                        # Apply Markdown formatting if no formatting errors have occurred
                        if not self._has_formatting_error:
                            try:
                                self.logger.warning(f"Formatting error encountered, using _format_for_markdown")
                                self._accumulated_text = self._format_for_markdown(self._raw_accumulated_text)
                            except Exception as e:
                                # On formatting error, switch to escaping text (no rich formatting)
                                self.logger.error(f"Markdown formatting error: {e}")
                                self._has_formatting_error = True
                                self._accumulated_text = self.escape_markdown(self._raw_accumulated_text)
                        else:
                            # If a formatting error was encountered, use escaped raw text for updates
                            self.logger.error(f"Formatting error encountered, using raw text")
                            self._accumulated_text = self.escape_markdown(self._raw_accumulated_text)

                        # Update the message in Telegram (with rate limiting)
                        await self._update_message(context, chat_id)

                # After streaming is done, ensure the final state of the message is sent
                if self._current_message:
                    try:
                        final_text = (self._format_for_markdown(self._raw_accumulated_text)
                                      if not self._has_formatting_error
                                      else self.escape_markdown(self._raw_accumulated_text))
                        # Avoid sending an identical final update
                        if final_text != self._last_sent_text:
                            await self._current_message.edit_text(
                                text=final_text,
                                parse_mode='MarkdownV2',
                                disable_web_page_preview=True
                            )
                            self._last_sent_text = final_text
                    except Exception as e:
                        error_msg = str(e)
                        self.logger.error(f"Error in final message update: {error_msg}")
                        # Fallback: try sending raw text without Markdown formatting
                        try:
                            await self._current_message.edit_text(
                                text=self._raw_accumulated_text,
                                disable_web_page_preview=True
                            )
                        except Exception as e2:
                            self.logger.error(f"Failed to send final message without formatting: {e2}")

                # Finalize multi-part messages by adding part numbers if needed
                await self._finalize_messages()

                def generate_pre_signed_url(s3_uri: str, expiration: int = 3600) -> str:
                    import boto3
                    from botocore.exceptions import ClientError
                    from urllib.parse import quote

                    s3 = boto3.client("s3")

                    try:
                        bucket, key = s3_uri.replace("s3://", "").split("/", 1)
                        return s3.generate_presigned_url(
                            "get_object",
                            Params={"Bucket": bucket, "Key": key},
                            ExpiresIn=expiration
                        )
                    except ClientError as e:
                        self.logger.error(f"Error generating presigned URL for {s3_uri}: {e}")
                        return ""


                # Send image only if it was present in the original document
                if image_url:
                    try:
                        if image_url.startswith("s3://"):
                            image_url = generate_pre_signed_url(image_url)
                            await context.bot.send_photo(chat_id=chat_id,
                                                         photo=image_url,
                                                         caption="Фото блюда из документа")
                    except Exception as e:
                        self.logger.warning(f"❌ Could not send image: {e}")

            except Exception as e:
                self.logger.error(f"Error during streaming response: {str(e)}")
                await self._handle_error(context, chat_id, str(e))
                return

            # Clear state
            self._current_message = None
            self._accumulated_text = ""
            self._raw_accumulated_text = ""

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
        # Rate limit updates to avoid flooding
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
                # If no message sent yet, send a new message (or first part of a long message)
                if len(self._accumulated_text) > MAX_MESSAGE_LENGTH:
                    # Start splitting into multiple messages if not already doing so
                    if not self._message_parts:
                        self._message_parts = []
                        self._current_part_index = 0

                    # Send the first part of the message
                    first_part = self._accumulated_text[:MAX_MESSAGE_LENGTH]
                    self.logger.info(f"📤 Sending message:\n{self._accumulated_text[:300]}")
                    self._current_message = await context.bot.send_message(
                        chat_id=chat_id,
                        text=first_part,
                        parse_mode='MarkdownV2',
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
                    # If it fits in one message/part, just send it normally
                    self._current_message = await context.bot.send_message(
                        chat_id=chat_id,
                        text=self._accumulated_text,
                        parse_mode='MarkdownV2',
                        disable_web_page_preview=True
                    )
            else:
                # A message (or part) already exists, update it
                if len(self._accumulated_text) > MAX_MESSAGE_LENGTH:
                    # If the current message now exceeds the limit, split into parts
                    if not self._message_parts:
                        self._message_parts = []
                        self._current_part_index = 0

                        # Add current message as first part
                        self._message_parts.append({
                            'message': self._current_message,
                            'text': self._accumulated_text[:MAX_MESSAGE_LENGTH]
                        })

                        # Edit the current message to contain only the first part
                        part_text = self._accumulated_text[:MAX_MESSAGE_LENGTH]
                        if part_text != self._message_parts[0]['text']:
                            await self._current_message.edit_text(
                                text=part_text,
                                parse_mode='MarkdownV2',
                                disable_web_page_preview=True
                            )
                            # Update stored text for part 0
                            self._message_parts[0]['text'] = part_text

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

                            # Only edit if there's a change
                            current_part = self._message_parts[self._current_part_index] if self._current_part_index < len(self._message_parts) else None
                            if current_part is None or update_text != current_part.get('text', ''):
                                await self._current_message.edit_text(
                                    text=update_text,
                                    parse_mode='MarkdownV2',
                                    disable_web_page_preview=True
                                )

                            # Update or append this part's text
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
                    # Text fits in the current message part
                    if not self._message_parts:
                        # Single message scenario
                        if self._accumulated_text != self._last_sent_text:
                            # Text fits in current message, just update it
                            await self._current_message.edit_text(
                                text=self._accumulated_text,
                                parse_mode='MarkdownV2',
                                disable_web_page_preview=True
                            )
                            self._last_sent_text = self._accumulated_text
                    else:
                        # We have parts but the latest text fits in the current part (no new part needed)
                        if self._accumulated_text != self._message_parts[self._current_part_index]['text']:
                            await self._current_message.edit_text(
                                text=self._accumulated_text,
                                parse_mode='MarkdownV2',
                                disable_web_page_preview=True
                            )
                            # Update stored text for this part
                            self._message_parts[self._current_part_index]['text'] = self._accumulated_text

            self._last_update_time = current_time

        except Exception as e:
            self.logger.error(f"Error updating message: {e}")
            error_str = str(e)
            if "Message is too long" in error_str:
                # If message still too long, continue splitting
                if not self._message_parts:
                    self._message_parts = []
                    self._current_part_index = 0
                if self._current_message and self._current_part_index == len(self._message_parts):
                    # Add current message as a part if not already listed
                    self._message_parts.append({
                        'message': self._current_message,
                        'text': self._accumulated_text[:MAX_MESSAGE_LENGTH]
                    })
                # Move to next part
                self._accumulated_text = self._accumulated_text[MAX_MESSAGE_LENGTH:]
                self._current_part_index += 1
                self._current_message = None
                await self._update_message(context, chat_id)
            elif "Message is not modified" in error_str or "message is not modified" in error_str.lower():
                # Gracefully ignore "not modified" errors
                self.logger.info(f"Ignoring 'Message not modified' error during update.")
            else:
                # For other errors, use the generic error handler
                await self._handle_error(context, chat_id, error_str)


        async def _handle_error(self, context: ContextTypes.DEFAULT_TYPE, chat_id: int, error_msg: str = None) -> None:
            """Handle errors gracefully by sending an error message to the user."""
            # Skip trivial "not modified" errors
            if error_msg and ("message is not modified" in error_msg.lower()):
                self.logger.info(f"Ignoring message not modified error: {error_msg}")
                return

            # Generic user-facing error message
            error_message = (
                "Sorry, I encountered an error processing your message.\n"
                "Please try again or rephrase your question."
            )
            # Include technical details for non-Telegram errors
            if error_msg and not any(word in error_msg.lower() for word in ["telegram", "message", "bot", "chat"]):
                error_message += f"\n\nError: {error_msg}"

            try:
                if self._current_message:
                    await self._current_message.edit_text(text=error_message, parse_mode='MarkdownV2')
                else:
                    await context.bot.send_message(chat_id=chat_id, text=error_message, parse_mode='MarkdownV2')
            except Exception as e:
                self.logger.error(f"Error sending error message: {e}")
                # Fallback to plain text if Markdown formatting fails for the error message
                await context.bot.send_message(chat_id=chat_id, text=error_message)

    async def format_and_send_code_blocks(self, context, chat_id, text):
        """Extract code blocks from text and send them separately with proper formatting"""
        # More flexible pattern to catch different code block variations
        code_pattern = r'```(?:(?P<lang>\w+)?)?\s*\n([\s\S]+?)\n\s*```'

        matches = re.finditer(code_pattern, text)
        code_blocks = [(m.group('lang') or '', m.group(2)) for m in matches]

        if not code_blocks:
            return

        # For each code block found
        for i, (lang, code) in enumerate(code_blocks):
            try:
                # First try using standard Markdown which is more reliable than MarkdownV2
                header = f"Code block {i+1}/{len(code_blocks)}"
                if lang:
                    header += f" ({lang})"

                formatted_message = f"{header}:\n\n```\n{code}\n```"

                await context.bot.send_message(
                    chat_id=chat_id,
                    text=formatted_message,
                    parse_mode='MarkdownV2'  # Use standard Markdown
                )
            except Exception as e:
                self.logger.error(f"Error sending formatted code block: {str(e)}")
                # Fallback to plain text with no parsing
                try:
                    lang_info = f" ({lang})" if lang else ""
                    plain_message = f"Code block {i+1}/{len(code_blocks)}{lang_info}:\n\n{code}"
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=plain_message
                    )
                except Exception as e2:
                    self.logger.error(f"Error sending plain code block: {str(e2)}")

    @staticmethod
    def _escape_html(text):
        """
        Escape HTML special characters comprehensively.
        This is extracted to a separate method for clarity and reuse.
        """
        replacements = [
            ('&', '&amp;'),  # Must be first to avoid double-escaping
            ('<', '&lt;'),
            ('>', '&gt;'),
            ('=', '&equals;'),
            ('"', '&quot;'),
            ("'", '&#39;')
        ]

        for old, new in replacements:
            text = text.replace(old, new)

        return text


    @staticmethod
    def escape_markdown(text: str) -> str:
        """Escape all special characters in text for MarkdownV2."""
        # First, escape backslashes
        text = text.replace("\\", "\\\\")
        # Escape all other MarkdownV2 special characters
        escape_chars = r'_*\[\]()~`>#+-=|{}.!'
        return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

    @staticmethod
    def detect_code_language(code: str) -> str:
        """Very basic heuristic to detect code language."""
        if any(keyword in code for keyword in ["public static void", "System.out.println", "class", "int"]):
            return "java"
        elif any(keyword in code for keyword in ["def", "print", "self", "import"]):
            return "python"
        return ""

    @staticmethod
    def _format_for_markdown(text: str) -> str:
        """
        Format the text for Telegram MarkdownV2:
        - Preserve code blocks and inline code with proper Markdown syntax.
        - Escape other special characters.
        """
        # Pattern to match triple backtick code blocks (with optional language specifier)
        code_pattern = r'```(?:(?P<lang>\w+)?\s*\n)?([\s\S]+?)\n\s*```'
        code_blocks = []
        result = ""
        last_end = 0

        for match in re.finditer(code_pattern, text):
            code_blocks.append(match.group(2))
            start, end = match.span()
            result += text[last_end:start] + f"PHCODEBLOCK{len(code_blocks)-1}"
            last_end = end
        result += text[last_end:]

        indent_blocks = []
        indent_positions = []
        lines = result.splitlines(keepends=True)
        i = 0
        while i < len(lines):
            if lines[i].startswith("    ") or lines[i].startswith("\t"):
                start_line = i
                code_lines = []
                while i < len(lines) and (lines[i].startswith("    ") or lines[i].startswith("\t")):
                    if lines[i].startswith("\t"):
                        code_line = lines[i][1:]
                    else:
                        code_line = lines[i][4:] if lines[i].startswith("    ") else lines[i]
                    code_lines.append(code_line)
                    i += 1
                block_text = "".join(code_lines)
                indent_blocks.append(block_text)
                char_start = sum(len(l) for l in lines[:start_line])
                char_end = char_start + sum(len(l) for l in lines[start_line:i])
                indent_positions.append((char_start, char_end))
            else:
                i += 1

        if indent_positions:
            new_result = ""
            last_idx = 0
            for j, (start, end) in enumerate(indent_positions):
                new_result += result[last_idx:start] + f"PHCODEBLOCK{len(code_blocks) + j}"
                last_idx = end
            new_result += result[last_idx:]
            result = new_result
            code_blocks.extend(indent_blocks)

        inline_blocks = []
        inline_positions = []
        for match in re.finditer(r'`([^`]+)`', result):
            inline_blocks.append(match.group(1))
            inline_positions.append(match.span())
        if inline_positions:
            new_result = ""
            last_idx = 0
            for k, (start, end) in enumerate(inline_positions):
                new_result += result[last_idx:start] + f"PHINLINE{k}"
                last_idx = end
            new_result += result[last_idx:]
            result = new_result

        result = TelegramBot.escape_markdown(result)

        for k in range(len(inline_blocks) - 1, -1, -1):
            content = inline_blocks[k].replace("\\", "\\\\")
            result = result.replace(f"PHINLINE{k}", f"`{content}`")

        for j in range(len(code_blocks) - 1, -1, -1):
            code_text = code_blocks[j].replace("\\", "\\\\").replace("`", "\\`")
            lang = TelegramBot.detect_code_language(code_text)
            lang_header = f"{lang}" if lang else ""
            result = result.replace(f"PHCODEBLOCK{j}", f"```{lang_header}\n{code_text}\n```")

        return result

    async def _finalize_messages(self) -> None:
        """Add part numbers to split messages after streaming is complete."""
        try:
            # If we don't have message parts, nothing to do
            if not self._message_parts or len(self._message_parts) == 0:
                return

            total_parts = len(self._message_parts)
            if total_parts <= 1:
                # Only one part, no need to add part number
                return

            for i, part_info in enumerate(self._message_parts):
                try:
                    message = part_info['message']
                    text = part_info['text']
                    part_text = f"Part {i+1}/{total_parts}\n\n{text}"
                    await message.edit_text(
                        text=part_text,
                        parse_mode='MarkdownV2',
                        disable_web_page_preview=True
                    )
                except Exception as e:
                    self.logger.error(f"Error updating part {i+1}: {e}")
                    # Continue to next part even if one fails
            # Clear parts tracking for next message
            self._message_parts = []
            self._current_part_index = 0

        except Exception as e:
            self.logger.error(f"Error finalizing messages: {e}")

    async def _handle_error(self, context, chat_id, param):
        pass

