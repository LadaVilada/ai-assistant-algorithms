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
pip install -r deployment/lambda/requirements.txt --target ./package

# Create necessary directory structure in the package
echo -e "${YELLOW}Setting up directory structure...${NC}"
mkdir -p package/src/ai_assistant/bots/base_bot
mkdir -p package/src/ai_assistant/bots/telegram
mkdir -p package/src/ai_assistant/bots/base  # Correct path for base_bot.py
mkdir -p package/ai_assistant/algorithms/bot
mkdir -p package/ai_assistant/core/utils
mkdir -p package/telegram
mkdir -p package/telegram/ext

# Copy your source files
echo -e "${YELLOW}Copying source files...${NC}"

# First ensure all __init__.py files exist
mkdir -p package/src
mkdir -p package/src/ai_assistant
mkdir -p package/src/ai_assistant/bots
mkdir -p package/ai_assistant
mkdir -p package/ai_assistant/algorithms
mkdir -p package/ai_assistant/core

touch package/src/__init__.py
touch package/src/ai_assistant/__init__.py
touch package/src/ai_assistant/bots/__init__.py
touch package/src/ai_assistant/bots/base/__init__.py  # Updated path
touch package/src/ai_assistant/bots/base_bot/__init__.py
touch package/src/ai_assistant/bots/telegram/__init__.py
touch package/ai_assistant/__init__.py
touch package/ai_assistant/algorithms/__init__.py
touch package/ai_assistant/algorithms/bot/__init__.py
touch package/ai_assistant/core/__init__.py
touch package/ai_assistant/core/utils/__init__.py

# Copy base bot files - CORRECTED PATH
if [ -f src/ai_assistant/bots/base/base_bot.py ]; then
    cp src/ai_assistant/bots/base/base_bot.py package/src/ai_assistant/bots/base/
fi

# Copy telegram bot files
if [ -d src/ai_assistant/bots/telegram ]; then
    cp -r src/ai_assistant/bots/telegram/*.py package/src/ai_assistant/bots/telegram/
fi

# Copy algorithms bot files
if [ -d ai_assistant/algorithms/bot ]; then
    cp -r ai_assistant/algorithms/bot/*.py package/ai_assistant/algorithms/bot/
fi

# Copy core utils
if [ -d ai_assistant/core/utils ]; then
    cp -r ai_assistant/core/utils/*.py package/ai_assistant/core/utils/
fi

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
rm -rf package lambda.zip lambda_function.py