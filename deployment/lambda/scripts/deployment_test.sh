#!/bin/bash
set -e

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
FUNCTION_NAME="telegram-ai-assistant"
REGION="us-east-1"

# Ensure AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}AWS CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Create deployment package
echo -e "${YELLOW}Creating deployment package...${NC}"
mkdir -p package

# Install required packages
pip install requests -t ./package

# Install development dependencies
pip install -r requirements-dev.txt

# Zip deployment package
cd package
zip -r ../lambda.zip .
cd ..

# Add lambda function to package
cp ./deployment/lambda/telegram_bot/lambda_function.py .
zip -g lambda.zip lambda_function.py

# Update Lambda function code
echo -e "${YELLOW}Updating Lambda function code...${NC}"
aws lambda update-function-code \
    --function-name "$FUNCTION_NAME" \
    --zip-file fileb://lambda.zip

# Update function configuration with bot token
echo -e "${YELLOW}Updating Lambda configuration...${NC}"
aws lambda update-function-configuration \
    --function-name "$FUNCTION_NAME" \
    --timeout 60 \
    --memory-size 512 \
    --environment "Variables={TELEGRAM_BOT_TOKEN=7868012719:AAGOUM03lL8MMEjMZrEqpqyhQQ5oyri3M-g}"

echo -e "${GREEN}Lambda function $FUNCTION_NAME updated successfully!${NC}"

# Clean up
rm -rf package lambda.zip

# Start local development server
./scripts/dev.sh local

# In another terminal, start ngrok
ngrok http 8080

# Update your Telegram webhook to the ngrok URL

# Run tests before deployment
./scripts/dev.sh test

# Deploy only code changes (much faster)
./scripts/dev.sh quick-deploy