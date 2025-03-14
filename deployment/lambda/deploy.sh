#!/bin/bash
set -e

# At the beginning of the script
# Change to the script's directory first:
#The script can determine its own location and change to that directory:
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color


# Create project structure
echo -e "${YELLOW}Creating project structure...${NC}"
mkdir -p telegram-lambda

# Move to project directory
cd telegram-lambda

# Create .env file
echo -e "${YELLOW}Creating .env file...${NC}"
cat > .env << EOF
TELEGRAM_BOT_TOKEN=7868012719:AAGOUM03lL8MMEjMZrEqpqyhQQ5oyri3M-g
EOF

# Create basic Lambda function
echo -e "${YELLOW}Creating Lambda function code...${NC}"
cat > lambda_function.py << EOF
import json
import os
import logging
import requests

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """Simple Lambda handler for Telegram webhook"""

    # Log the received event
    logger.info(f"Received event: {json.dumps(event)}")

    # Get Telegram token from environment variable
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("No Telegram bot token provided")
        return {
            'statusCode': 200,  # Return 200 to Telegram regardless
            'body': json.dumps({'error': 'Configuration error'})
        }

    # Parse the incoming update from Telegram (via API Gateway)
    if 'body' in event:
        try:
            body = json.loads(event['body'])
            logger.info(f"Parsed Telegram update: {json.dumps(body)}")

            # Extract chat ID and message if present
            if 'message' in body:
                chat_id = body['message'].get('chat', {}).get('id')
                text = body['message'].get('text', '')

                if chat_id and text:
                    # Send echo response
                    response_text = f"Echo: {text}"
                    send_telegram_message(token, chat_id, response_text)

        except json.JSONDecodeError as e:
            logger.error(f"Error parsing request body: {e}")

    # Always return success to Telegram
    return {
        'statusCode': 200,
        'body': json.dumps({'ok': True})
    }

def send_telegram_message(token, chat_id, text):
    """Send a message to a Telegram chat"""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }

    try:
        response = requests.post(url, json=payload)
        logger.info(f"Message sent. Response: {response.text}")
        return response.json()
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return None
EOF

# After creating lambda_function.py
echo "Checking if lambda_function.py was created:"
ls -la lambda_function.py
cat lambda_function.py | head -5


# Create requirements.txt
echo -e "${YELLOW}Creating requirements.txt...${NC}"
cat > requirements.txt << EOF
requests==2.28.1
EOF

# Create Dockerfile
echo -e "${YELLOW}Creating Dockerfile...${NC}"
cat > Dockerfile << 'EOF'
FROM public.ecr.aws/lambda/python:3.9

# Define the AWS Lambda Task Root
ENV LAMBDA_TASK_ROOT=/var/task

# Copy function code
COPY lambda_function.py ${LAMBDA_TASK_ROOT}/
COPY requirements.txt ${LAMBDA_TASK_ROOT}/

# Install the dependencies
RUN pip install --target ${LAMBDA_TASK_ROOT} -r ${LAMBDA_TASK_ROOT}/requirements.txt

# Set the CMD to your handler
CMD [ "lambda_function.lambda_handler" ]
EOF

# Load environment variables from .env file
if [ -f .env ]; then
    echo -e "${YELLOW}Loading environment variables from .env file...${NC}"
    export $(grep -v '^#' .env | xargs)
else
    echo -e "${RED}ERROR: .env file not found!${NC}"
    exit 1
fi

# Configuration
FUNCTION_NAME="telegram-lambda-minimal"
ROLE_NAME="telegram-ai-assistant-lambda-role"
REGION="us-east-1"
ECR_REPOSITORY="${FUNCTION_NAME}-ecr"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ROLE_ARN="arn:aws:iam::$AWS_ACCOUNT_ID:role/$ROLE_NAME"
ECR_IMAGE_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPOSITORY}:latest"

# Get AWS account ID
echo -e "${YELLOW}Getting AWS account ID...${NC}"
AWS_ACCOUNT=$(aws sts get-caller-identity --query "Account" --output text)

# Create or ensure the ECR repository exists
echo -e "${YELLOW}Checking or Creating ECR repository...${NC}"
aws ecr describe-repositories --repository-names ${ECR_REPOSITORY} >/dev/null 2>&1 || \
    aws ecr create-repository --repository-name ${ECR_REPOSITORY}

# Log in to ECR
echo -e "${YELLOW}Logging in to ECR...${NC}"
aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com

# Build the Docker image
echo -e "${YELLOW}Building Docker image...${NC}"
docker buildx build --platform=linux/amd64 --load -t ${ECR_REPOSITORY}:latest .

# Tag the image for ECR
echo -e "${YELLOW}Tagging Docker image...${NC}"
docker tag ${ECR_REPOSITORY}:latest ${AWS_ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPOSITORY}:latest

# Push the image to ECR
echo -e "${YELLOW}Pushing Docker image to ECR...${NC}"
docker push ${AWS_ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPOSITORY}:latest

# Ensure AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}AWS CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if function exists
FUNCTION_EXISTS=$(aws lambda list-functions --query "Functions[?FunctionName=='$FUNCTION_NAME'].FunctionName" --output text)

if [ -z "$FUNCTION_EXISTS" ]; then
    # Function doesn't exist, create it
    echo -e "${YELLOW}Creating new Lambda function with container image...${NC}"

    # Create new Lambda function
        echo -e "${YELLOW}Creating new Lambda function...${NC}"
        aws lambda create-function \
            --function-name ${FUNCTION_NAME} \
            --package-type Image \
            --code ImageUri="$ECR_IMAGE_URI" \
            --role "$ROLE_ARN" \
            --timeout 30 \
            --memory-size 256 \
            --environment "Variables={TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}}"
else
      # Update existing Lambda function
      echo -e "${YELLOW}Updating existing Lambda function...${NC}"
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

## Check if Lambda function exists
#echo -e "${YELLOW}Checking if Lambda function exists...${NC}"
#aws lambda get-function --function-name ${FUNCTION_NAME} > /dev/null 2>&1
#FUNCTION_EXISTS=$?
#
#echo "Function exists status code: $FUNCTION_EXISTS"
#
#if [ $FUNCTION_EXISTS -eq 0 ]; then
#    # Update existing Lambda function
#    echo -e "${YELLOW}Updating existing Lambda function...${NC}"
#    aws lambda update-function-code \
#        --function-name ${FUNCTION_NAME} \
#        --image-uri ${AWS_ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPOSITORY}:latest
#else
#    # Create new Lambda function
#    echo -e "${YELLOW}Creating new Lambda function...${NC}"
#    aws lambda create-function \
#        --function-name ${FUNCTION_NAME} \
#        --package-type Image \
#        --code ImageUri="$ECR_IMAGE_URI" \
#        --role "$ROLE_ARN" \
#        --timeout 30 \
#        --memory-size 256 \
#        --environment "Variables={TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}}"
#fi

## Update Lambda configuration
#echo -e "${YELLOW}Updating Lambda configuration...${NC}"
#aws lambda update-function-configuration \
#    --function-name ${FUNCTION_NAME} \
#    --timeout 30 \
#    --memory-size 256 \
#    --environment "Variables={TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}}"

# Note: API Gateway setup now done separately through setup_apigateway.py
echo -e "${GREEN}Lambda function deployed successfully!${NC}"
echo -e "${YELLOW}To set up API Gateway, run: python3 setup_apigateway.py${NC}"

echo -e "${GREEN}Deployment complete! Your Telegram bot is now connected to AWS Lambda via API Gateway.${NC}"
echo -e "${GREEN}Test your bot by sending a message to it on Telegram.${NC}"

## Set up API Gateway if needed
#echo -e "${YELLOW}Setting up API Gateway...${NC}"
#API_ID=$(aws apigateway get-rest-apis --query "items[?name=='TelegramWebhook'].id" --output text)
#
#if [ -z "$API_ID" ]; then
#    echo -e "${YELLOW}Creating new API Gateway...${NC}"
#    # Create API
#    API_ID=$(aws apigateway create-rest-api \
#        --name "TelegramWebhook" \
#        --description "API for Telegram bot webhook" \
#        --endpoint-configuration "types=REGIONAL" \
#        --query "id" --output text)
#
#    # Get root resource ID
#    ROOT_ID=$(aws apigateway get-resources \
#        --rest-api-id $API_ID \
#        --query "items[?path=='/'].id" --output text)
#
#    # Create resource
#    RESOURCE_ID=$(aws apigateway create-resource \
#        --rest-api-id $API_ID \
#        --parent-id $ROOT_ID \
#        --path-part "webhook" \
#        --query "id" --output text)
#
#    # Create POST method
#    aws apigateway put-method \
#        --rest-api-id $API_ID \
#        --resource-id $RESOURCE_ID \
#        --http-method POST \
#        --authorization-type NONE
#
#    # Set Lambda integration
#    aws apigateway put-integration \
#        --rest-api-id $API_ID \
#        --resource-id $RESOURCE_ID \
#        --http-method POST \
#        --type AWS_PROXY \
#        --integration-http-method POST \
#        --uri arn:aws:apigateway:${REGION}:lambda:path/2015-03-31/functions/arn:aws:lambda:${REGION}:${AWS_ACCOUNT}:function:${FUNCTION_NAME}/invocations
#
#    # Create deployment
#    aws apigateway create-deployment \
#        --rest-api-id $API_ID \
#        --stage-name prod
#
#    # Add Lambda permission
#    aws lambda add-permission \
#        --function-name ${FUNCTION_NAME} \
#        --statement-id apigateway-prod \
#        --action lambda:InvokeFunction \
#        --principal apigateway.amazonaws.com \
#        --source-arn "arn:aws:execute-api:${REGION}:${AWS_ACCOUNT}:${API_ID}/prod/POST/webhook"
#else
#    echo -e "${GREEN}API Gateway already exists with ID: ${API_ID}${NC}"
#fi

## Get the API Gateway URL
#WEBHOOK_URL="https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod/webhook"
#echo -e "${GREEN}Telegram webhook URL: ${WEBHOOK_URL}${NC}"
#
## Set Telegram webhook
#echo -e "${YELLOW}Setting Telegram webhook...${NC}"
#curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook?url=${WEBHOOK_URL}"
#
#echo -e "${GREEN}Deployment complete! Your Telegram bot is now connected to AWS Lambda via API Gateway.${NC}"
#echo -e "${GREEN}Test your bot by sending a message to it on Telegram.${NC}"