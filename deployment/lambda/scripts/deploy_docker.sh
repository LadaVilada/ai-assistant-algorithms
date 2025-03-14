#!/bin/bash
set -e

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

cd "$(dirname "$0")/../../.." || exit 1
echo -e "${YELLOW}Changed directory to project root: $(pwd)${NC}"

# Load environment variables from .env file
if [ -f .env ]; then
    echo -e "${YELLOW}Loading environment variables from .env file...${NC}"
    export "$(grep -v '^#' .env | xargs)"
else
    echo -e "${RED}ERROR: .env file not found!${NC}"
    exit 1
fi

echo -e "${YELLOW}Copying .env to /var/task...${NC}"
cp .env deployment/lambda/telegram_bot/.env

# Verify if the copy was successful
if [ -f deployment/lambda/telegram_bot/.env ]; then
    echo -e "${GREEN}.env copied successfully!${NC}"
else
    echo -e "${RED}ERROR: Failed to copy .env!${NC}"
    exit 1
fi

# Get AWS Account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)

# Ensure AWS_ACCOUNT_ID is not empty
if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo -e "${RED}ERROR: AWS_ACCOUNT_ID is empty! Check AWS credentials.${NC}"
    exit 1
fi

# Configuration
FUNCTION_NAME="telegram-ai-assistant"
REGION="us-east-1"
ECR_REPOSITORY="${FUNCTION_NAME}-ecr"
ROLE_ARN="arn:aws:iam::$AWS_ACCOUNT_ID:role/$ROLE_NAME"
ECR_IMAGE_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPOSITORY}:latest"
AWS_ACCOUNT=$(aws sts get-caller-identity --query "Account" --output text)

if [ ! -f deployment/lambda/telegram_bot/lambda_function.py ]; then
    echo -e "${RED}ERROR: lambda_function.py not found in deployment/lambda/telegram_bot/${NC}"
    exit 1
else
    echo -e "${GREEN}lambda_function.py found! Copying to the root.${NC}"
fi

echo -e "${YELLOW}Copying lambda_function.py to the root...${NC}"
cp deployment/lambda/telegram_bot/lambda_function.py lambda_function.py

# Create Dockerfile
echo -e "${YELLOW}Creating Dockerfile...${NC}"
cat > Dockerfile << 'EOF'
FROM public.ecr.aws/lambda/python:3.9

# Define Lambda Task Root
ENV LAMBDA_TASK_ROOT=/var/task

# Set Python path to include Lambda task root and src/
ENV PYTHONPATH="/var/task:/var/task/src"

# Make sure lambda_function.py is at the root level
COPY deployment/lambda/telegram_bot/lambda_function.py ${LAMBDA_TASK_ROOT}/lambda_function.py
# Copy .env file for runtime environment variables
COPY .env ${LAMBDA_TASK_ROOT}/.env

# Copy your project files
COPY . ${LAMBDA_TASK_ROOT}/

# Ensure directories are recognized as Python packages
RUN touch ${LAMBDA_TASK_ROOT}/deployment/__init__.py \
    && touch ${LAMBDA_TASK_ROOT}/deployment/lambda/__init__.py \
    && touch ${LAMBDA_TASK_ROOT}/deployment/lambda/telegram_bot/__init__.py \
    && touch ${LAMBDA_TASK_ROOT}/src/__init__.py \
    && touch ${LAMBDA_TASK_ROOT}/src/ai_assistant/__init__.py

# Install dependencies
COPY deployment/lambda/requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --target ${LAMBDA_TASK_ROOT} -r ${LAMBDA_TASK_ROOT}/requirements.txt

# Set the handler
CMD [ "lambda_function.lambda_handler" ]
#CMD [ "deployment.lambda.telegram_bot.lambda_function.lambda_handler" ]
EOF

echo -e "${YELLOW}Checking or Creating ECR repository...${NC}"
aws ecr describe-repositories --repository-names ${ECR_REPOSITORY} >/dev/null 2>&1

if [ $? -ne 0 ]; then
    echo -e "${YELLOW}Repository not found. Creating it now...${NC}"
    aws ecr create-repository --repository-name ${ECR_REPOSITORY}
else
    echo -e "${GREEN}Repository already exists!${NC}"
fi

#RUN echo "Checking lambda_function.py location inside container:" && ls -la ${LAMBDA_TASK_ROOT}/lambda_function.py

# Log in to ECR
echo -e "${YELLOW}Logging in to ECR...${NC}"
aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com


# After creating lambda_function.py
echo "Checking if lambda_function.py was created:"
ls -la lambda_function.py
cat lambda_function.py | head -5


# Before building, verify lambda_function.py exists
echo -e "${YELLOW}Verifying lambda_function.py exists...${NC}"
if [ ! -f lambda_function.py ]; then
    echo -e "${RED}ERROR: lambda_function.py not found in the current directory!${NC}"
    exit 1
else
    echo -e "${GREEN}lambda_function.py found!${NC}"
fi

# Build the Docker image
echo -e "${YELLOW}Building Docker image...${NC}"
docker buildx build --platform=linux/amd64 --load --cache-from ${ECR_REPOSITORY}:latest -t ${ECR_REPOSITORY} .

# Tag the image
echo -e "${YELLOW}Tagging Docker image...${NC}"
docker tag ${ECR_REPOSITORY}:latest ${AWS_ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPOSITORY}:latest

# Push the image to ECR
echo -e "${YELLOW}Pushing Docker image to ECR...${NC}"
docker push ${AWS_ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPOSITORY}:latest
#docker push ${ECR_REPOSITORY}:latest

# Update the Lambda function to use the new container image
echo -e "${YELLOW}Updating Lambda function...${NC}"
aws lambda update-function-code \
        --function-name "${FUNCTION_NAME}" \
        --image-uri "${ECR_IMAGE_URI}"

# Update function configuration
echo -e "${YELLOW}Updating Lambda configuration...${NC}"
aws lambda update-function-configuration \
              --function-name "${FUNCTION_NAME}" \
              --timeout 60 \
              --memory-size 512 \
              --environment "Variables={
                  TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN},
                  ENVIRONMENT=production,
                  LOG_LEVEL=INFO
              }"

echo -e "${GREEN}Lambda function ${FUNCTION_NAME} updated successfully with container image!${NC}"

# Clean up
rm -f Dockerfile