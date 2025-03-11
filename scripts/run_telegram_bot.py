import os
import sys

from ai_assistant.telegram.algorithms_bot import TelegramAlgorithmsBot

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

def main():
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    bot = TelegramAlgorithmsBot(token)
    bot.run()

if __name__ == '__main__':
    main()