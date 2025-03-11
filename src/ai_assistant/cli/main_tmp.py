# import argparse
# import logging
# import sys
# from typing import Optional
#
# # Import core services and bots
# from ai_assistant.core.services.rag_service import RAGService
# from ai_assistant.core.services.llm_service import LLMService
# from ai_assistant.algorithms.bot import AlgorithmsBot
# from ai_assistant.telegram.algorithms_bot import TelegramAlgorithmsBot
#
# class CLIApplication:
#     """
#     Command-line interface for interacting with AI assistants
#     Provides multiple modes of interaction
#     """
#     def __init__(self):
#         # Configure logging
#         logging.basicConfig(
#             level=logging.INFO,
#             format='%(asctime)s - %(levelname)s - %(message)s'
#         )
#         self.logger = logging.getLogger(__name__)
#
#         # Initialize core services
#         self.rag_service = RAGService()
#         self.llm_service = LLMService()
#
#     def interactive_mode(self, bot_type: str = 'algorithms'):
#         """
#         Start an interactive CLI session with the specified bot
#         """
#         if bot_type == 'algorithms':
#             bot = AlgorithmsBot(self.rag_service, self.llm_service)
#         else:
#             self.logger.error(f"Unsupported bot type: {bot_type}")
#             return
#
#         print(f"🤖 Interactive {bot_type.capitalize()} Bot CLI")
#         print("Type 'exit' or 'quit' to end the session")
#
#         while True:
#             try:
#                 query = input("You: ").strip()
#
#                 # Exit conditions
#                 if query.lower() in ['exit', 'quit', 'q']:
#                     print("Goodbye!")
#                     break
#
#                 # Process query
#                 result = bot.process_query(query)
#
#                 # Print response
#                 print("\n🤖 Bot Response:")
#                 print(result['response'])
#
#                 # Optional: Show sources
#                 if result.get('sources'):
#                     print("\n📚 Sources:")
#                     for i, source in enumerate(result['sources'], 1):
#                         print(f"{i}. {source.get('metadata', {}).get('source', 'Unknown Source')}")
#
#                 print("\n" + "-"*50 + "\n")
#
#             except KeyboardInterrupt:
#                 print("\nSession interrupted. Exiting...")
#                 break
#             except Exception as e:
#                 self.logger.error(f"Error in interactive mode: {e}")
#
#     def run_tests(self, bot_type: str = 'algorithms'):
#         """
#         Run predefined tests for a specific bot
#         """
#         if bot_type == 'algorithms':
#             bot = AlgorithmsBot(self.rag_service, self.llm_service)
#             test_results = bot.run_tests()
#
#             print(f"🧪 Test Results for {bot_type.capitalize()} Bot:")
#             for result in test_results:
#                 print("\n" + "="*50)
#                 print(f"Query: {result['query']}")
#                 print(f"Response: {result['response']}")
#                 print("="*50)
#         else:
#             self.logger.error(f"No tests available for bot type: {bot_type}")
#
#     def start_telegram_bot(self, token: Optional[str] = None):
#         """
#         Start the Telegram bot
#         """
#         if not token:
#             token = input("Enter Telegram Bot Token: ").strip()
#
#         try:
#             bot = TelegramAlgorithmsBot(token)
#             print("🚀 Starting Telegram Bot...")
#             bot.run()
#         except Exception as e:
#             self.logger.error(f"Failed to start Telegram bot: {e}")
#
# def main():
#     """
#     Main CLI entry point with argument parsing
#     """
#     parser = argparse.ArgumentParser(
#         description="AI Assistant CLI - Interact with different bot types"
#     )
#
#     # Add CLI mode arguments
#     parser.add_argument(
#         'mode',
#         choices=['interactive', 'test', 'telegram'],
#         help='Mode of operation'
#     )
#
#     # Optional bot type argument
#     parser.add_argument(
#         '--bot',
#         choices=['algorithms'],
#         default='algorithms',
#         help='Specify the bot type (default: algorithms)'
#     )
#
#     # Optional Telegram token argument
#     parser.add_argument(
#         '--token',
#         help='Telegram Bot Token (for telegram mode)',
#         default=None
#     )
#
#     # Parse arguments
#     args = parser.parse_args()
#
#     # Create CLI application
#     cli_app = CLIApplication()
#
#     # Run the appropriate mode
#     if args.mode == 'interactive':
#         cli_app.interactive_mode(args.bot)
#     elif args.mode == 'test':
#         cli_app.run_tests(args.bot)
#     elif args.mode == 'telegram':
#         cli_app.start_telegram_bot(args.token)
#
# if __name__ == '__main__':
#     main()