#!/bin/bash
set -e

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
FUNCTION_NAME="telegram-ai-assistant"
ROLE_NAME="telegram-ai-assistant-lambda-role"
REGION="us-east-1"
RUNTIME="python3.9"
HANDLER="lambda_function.lambda_handler"
MEMORY_SIZE=512  # Increased for better performance with RAG
TIMEOUT=60       # Increased for RAG processing

# Ensure AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}AWS CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Get AWS Account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ROLE_ARN="arn:aws:iam::$AWS_ACCOUNT_ID:role/$ROLE_NAME"

# Create deployment package
echo -e "${YELLOW}Creating deployment package...${NC}"
mkdir -p package
pip install -r deployment/lambda/scripts/requirements.txt --target ./package

# Zip deployment package
cd package
zip -r ../lambda.zip .
cd ..

# Add lambda function to package
cp ./deployment/lambda/telegram_bot/lambda_function.py .
zip -g lambda.zip lambda_function.py

# Create or update Lambda function
echo -e "${YELLOW}Creating/Updating Lambda function...${NC}"
aws lambda create-function \
    --function-name "$FUNCTION_NAME" \
    --runtime "$RUNTIME" \
    --role "$ROLE_ARN" \
    --handler "$HANDLER" \
    --zip-file fileb://lambda.zip \
    --timeout 30 \
    --memory-size 256 \
    --environment "Variables={
        ENVIRONMENT=production,
        LOG_LEVEL=INFO
    }"

# Configure function settings
echo -e "${YELLOW}Configuring Lambda function...${NC}"
aws lambda update-function-configuration \
    --function-name "$FUNCTION_NAME" \
    --timeout 30 \
    --memory-size 256

echo -e "${GREEN}Lambda function $FUNCTION_NAME created successfully!${NC}"

# Clean up
rm -rf package lambda.zip lambda_function.py