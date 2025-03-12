import os
import sys
import requests

def set_telegram_webhook():
    """
    Set Telegram webhook for the AI Assistant Lambda function
    """
    # Telegram Bot Token
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        print("Error: TELEGRAM_BOT_TOKEN environment variable not set")
        sys.exit(1)

    # AWS API Gateway webhook URL
    webhook_url = os.getenv('LAMBDA_WEBHOOK_URL')
    if not webhook_url:
        print("Error: LAMBDA_WEBHOOK_URL environment variable not set")
        sys.exit(1)

    # Telegram Bot API endpoint
    url = f'https://api.telegram.org/bot{bot_token}/setWebhook'

    # Webhook parameters
    params = {
        'url': webhook_url,
        'allowed_updates': ['message']  # Only receive message updates
    }

    try:
        # Send webhook setup request
        response = requests.get(url, params=params)

        # Check response
        if response.status_code == 200 and response.json().get('ok'):
            print("Telegram webhook set successfully!")
            print(f"Webhook URL: {webhook_url}")
        else:
            print("Failed to set Telegram webhook")
            print(response.text)
            sys.exit(1)

    except requests.RequestException as e:
        print(f"❌ Error setting Telegram webhook: {e}")
        sys.exit(1)

if __name__ == '__main__':
    set_telegram_webhook()