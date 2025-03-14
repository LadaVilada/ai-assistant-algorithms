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
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ROLE_ARN="arn:aws:iam::$AWS_ACCOUNT_ID:role/$ROLE_NAME"
ECR_REPOSITORY="${FUNCTION_NAME}-ecr"
ECR_IMAGE_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPOSITORY}:latest"

# Ensure AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}AWS CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    echo -e "${YELLOW}Loading environment variables from .env file...${NC}"
    export $(grep -v '^#' .env | xargs)
else
    echo -e "${RED}ERROR: .env file not found!${NC}"
    exit 1
fi

# Validate TELEGRAM_BOT_TOKEN
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo -e "${RED}ERROR: TELEGRAM_BOT_TOKEN is empty! Make sure .env is loaded.${NC}"
    exit 1
else
    echo -e "${GREEN}Using TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}${NC}"
fi

# Check if function exists
FUNCTION_EXISTS=$(aws lambda list-functions --query "Functions[?FunctionName=='$FUNCTION_NAME'].FunctionName" --output text)

if [ -z "$FUNCTION_EXISTS" ]; then
    # Function doesn't exist, create it
    echo -e "${YELLOW}Creating new Lambda function with container image...${NC}"

    aws lambda create-function \
        --function-name "$FUNCTION_NAME" \
        --package-type Image \
        --code ImageUri="$ECR_IMAGE_URI" \
        --role "$ROLE_ARN" \
        --timeout 60 \
        --memory-size 512 \
        --environment "Variables={
            TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN},
            ENVIRONMENT=production,
            LOG_LEVEL=INFO
        }"
else
    # Function exists, update it
    echo -e "${YELLOW}Updating existing Lambda function with container image...${NC}"

    aws lambda update-function-code \
        --function-name "$FUNCTION_NAME" \
        --image-uri "$ECR_IMAGE_URI"

    aws lambda update-function-configuration \
        --function-name "$FUNCTION_NAME" \
        --timeout 60 \
        --memory-size 512 \
        --environment "Variables={
            TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN},
            ENVIRONMENT=production,
            LOG_LEVEL=INFO
        }"
fi

echo -e "${GREEN}Lambda function $FUNCTION_NAME created/updated successfully!${NC}"