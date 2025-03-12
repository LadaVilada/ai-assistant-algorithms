#!/bin/bash
set -e

# Variables - customize these
# ./deploy.sh telegram-bot
#LAMBDA_FUNCTION_NAME="ai-assistant"
AWS_REGION="us-east-1"
FUNCTION_NAME=$1
# Configuration
AWS_ACCOUNT_ID="122505305911"
LAMBDA_ROLE_ARN="arn:aws:iam::$AWS_ACCOUNT_ID/role/telegram-ai-assistant-lambda-role"
FUNCTION_NAME="telegram-ai-assistant"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

if [ -z "$FUNCTION_NAME" ]; then
    echo "Please specify a function name. Available functions:"
    ls -1 deployment/lambda/
    exit 1
fi

FUNCTION_DIR="deployment/lambda/$FUNCTION_NAME"
ZIP_FILE="${FUNCTION_NAME}.zip"

# Customize test payload based on bot type
if [ "$FUNCTION_NAME" = "telegram-bot" ]; then
    TEST_PAYLOAD='{"bot_type":"telegram","body":{"message":{"text":"Hello","chat":{"id":12345}}}}'
elif [ "$FUNCTION_NAME" = "algorithms-bot" ]; then
    TEST_PAYLOAD='{"bot_type":"algorithms","query":"What is a dataset?"}'
fi
#TEST_PAYLOAD='{"body": {"question": "What is AWS Lambda?", "model": "gpt-3.5-turbo"}}'  # Example test payload

echo -e "${YELLOW}Starting deployment workflow...${NC}"

# Step 1: Check if DynamoDB table needs to be created
echo -e "${YELLOW}Do you want to create/update the DynamoDB table? (y/n)${NC}"
read create_table

if [ "$create_table" = "y" ]; then
    echo -e "${YELLOW}Creating DynamoDB table...${NC}"
    python scripts/table/create_table.py
    echo -e "${GREEN}Table setup complete.${NC}"
fi

# Step 2: Build the Lambda package
echo -e "${YELLOW}Cleaning up previous build...${NC}"
rm -rf package $ZIP_FILE

echo -e "${YELLOW}Installing dependencies...${NC}"
mkdir -p package
pip install --target ./package -r $FUNCTION_DIR/requirements.txt

echo -e "${YELLOW}Creating deployment package...${NC}"
cd package
zip -r ../$ZIP_FILE .
cd ..

echo -e "${YELLOW}Adding lambda_function.py to the archive...${NC}"
cp $FUNCTION_DIR/lambda_function_1.py .
zip -g $ZIP_FILE lambda_function_1.py
rm lambda_function_1.py  # Clean up the copied file after zipping

echo -e "${GREEN}Lambda package created: lambda.zip${NC}"

# Step 3: Upload to AWS
echo -e "${YELLOW}Do you want to upload the Lambda package to AWS? (y/n)${NC}"
read upload_lambda

if [ "$upload_lambda" = "y" ]; then
    echo -e "${YELLOW}Uploading Lambda package to AWS...${NC}"

    # Check if AWS CLI is installed
    if ! command -v aws &> /dev/null; then
        echo -e "${RED}AWS CLI not found. Please install it to continue.${NC}"
        exit 1
    fi

    # Upload the Lambda package
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://$ZIP_FILE \
        --region $AWS_REGION

    echo -e "${GREEN}Lambda function updated successfully!${NC}"

    # Step 4: Test the Lambda function
    echo -e "${YELLOW}Do you want to test the Lambda function? (y/n)${NC}"
    read test_lambda

    if [ "$test_lambda" = "y" ]; then
        echo -e "${YELLOW}Testing Lambda function...${NC}"
        echo -e "${YELLOW}Using test payload: ${TEST_PAYLOAD}${NC}"

        TEST_RESULT=$(aws lambda invoke \
                    --function-name $FUNCTION_NAME \
                    --payload "$TEST_PAYLOAD" \
                    --region $AWS_REGION \
                    --cli-binary-format raw-in-base64-out \
                    /tmp/lambda-test-output.json > /tmp/lambda-test-stats.txt)

        STATUS_CODE=$(cat /tmp/lambda-test-stats.txt | grep StatusCode | cut -d":" -f2 | tr -d ' ,')

        if [ "$STATUS_CODE" = "200" ]; then
            echo -e "${GREEN}Lambda test successful!${NC}"
            echo -e "${YELLOW}Response:${NC}"
            cat /tmp/lambda-test-output.json | jq .
        else
            echo -e "${RED}Lambda test failed with status code: $STATUS_CODE${NC}"
            echo -e "${YELLOW}Error details:${NC}"
            cat /tmp/lambda-test-output.json
        fi
    fi
fi

echo -e "${GREEN}Deployment workflow completed!${NC}"