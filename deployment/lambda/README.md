# AI Assistant Lambda Deployment

## Prerequisites
- AWS CLI configured
- Python 3.9+
- Poetry or pip
- AWS Account with Lambda permissions

## Deployment Steps

### 1. Create IAM Role
```bash
chmod +x scripts/create_lambda_role.sh
./scripts/create_lambda_role.sh
```

### 2. Create Lambda Function
```bash
chmod +x scripts/create_lambda_function.sh
./scripts/create_lambda_function.sh
```

### 3. Update Lambda Function (after code changes)
```bash
chmod +x scripts/update_lambda_function.sh
./scripts/update_lambda_function.sh
```

### 4. Set Telegram Webhook
```bash
# Set environment variables first
export TELEGRAM_BOT_TOKEN=your_bot_token
export LAMBDA_WEBHOOK_URL=your_lambda_webhook_url

python scripts/set_telegram_webhook.py
```

## Environment Variables
- `TELEGRAM_BOT_TOKEN`: Telegram bot token
- `LAMBDA_WEBHOOK_URL`: AWS Lambda function webhook URL
- `ENVIRONMENT`: Deployment environment (production/development)
- `LOG_LEVEL`: Logging level (INFO/DEBUG/WARNING/ERROR)

## Troubleshooting
- Ensure AWS CLI is configured with correct credentials
- Check CloudWatch logs for Lambda function errors
- Verify IAM role permissions