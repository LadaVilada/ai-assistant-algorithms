import os
import sys


# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

from ai_assistant.bots.telegram.bot import TelegramAlgorithmsBot

def main():
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    bot = TelegramAlgorithmsBot(token)
    bot.run()

if __name__ == '__main__':
    main()