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
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPOSITORY="${FUNCTION_NAME}"
ECR_IMAGE_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPOSITORY}:latest"

# Ensure we're in the project root
cd "$(dirname "$0")/../../.."
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
mkdir -p deployment/lambda/telegram_bot
cp .env deployment/lambda/telegram_bot/.env

# Verify if the copy was successful
if [ -f deployment/lambda/telegram_bot/.env ]; then
    echo -e "${GREEN}.env copied successfully!${NC}"
else
    echo -e "${RED}ERROR: Failed to copy .env!${NC}"
    exit 1
fi

if [ ! -f deployment/lambda/telegram_bot/lambda_function.py ]; then
    echo -e "${RED}ERROR: lambda_function.py not found in deployment/lambda/telegram_bot/${NC}"
    exit 1
else
    echo -e "${GREEN}lambda_function.py found! Copying to the root.${NC}"
fi

echo -e "${YELLOW}Copying lambda_function.py to the root...${NC}"
cp deployment/lambda/telegram_bot/lambda_function.py lambda_function.py


echo -e "${YELLOW}Starting Docker deployment process...${NC}"

# Step 2: Create a minimal Dockerfile
echo -e "${YELLOW}Creating Dockerfile...${NC}"
cat > Dockerfile << 'EOF'
FROM public.ecr.aws/lambda/python:3.9

# Define Lambda Task Root
ENV LAMBDA_TASK_ROOT=/var/task

# Set working directory
WORKDIR ${LAMBDA_TASK_ROOT}

# Set Python path to include Lambda task root and src/
ENV PYTHONPATH="/var/task:/var/task/src"

# Make sure lambda_function.py is at the root level
COPY deployment/lambda/telegram_bot/lambda_function.py ${LAMBDA_TASK_ROOT}/lambda_function.py
COPY .env* /var/task/.env

# Copy your project files
COPY . ${LAMBDA_TASK_ROOT}/

# Ensure directories are recognized as Python packages
RUN touch ${LAMBDA_TASK_ROOT}/deployment/__init__.py \
    && touch ${LAMBDA_TASK_ROOT}/deployment/lambda/__init__.py \
    && touch ${LAMBDA_TASK_ROOT}/deployment/lambda/telegram_bot/__init__.py \
    && touch ${LAMBDA_TASK_ROOT}/src/__init__.py \
    && touch ${LAMBDA_TASK_ROOT}/src/ai_assistant/__init__.py

# Install dependencies
COPY requirements.txt ${LAMBDA_TASK_ROOT}/requirements.txt
RUN pip wheel --wheel-dir=/tmp/wheels -r ${LAMBDA_TASK_ROOT}/requirements.txt
RUN pip install --no-cache-dir --target ${LAMBDA_TASK_ROOT} --find-links=/tmp/wheels -r ${LAMBDA_TASK_ROOT}/requirements.txt

# Debugging: Verify installation inside the image
RUN python3 -c "import langchain_community; print('Langchain installed successfully!')"

# Set the handler
CMD [ "lambda_function.lambda_handler" ]
EOF

# Step 3: Build and tag the Docker image
echo -e "${YELLOW}Building Docker image...${NC}"
docker buildx build --platform=linux/amd64 --load -t ${FUNCTION_NAME}:latest .

# Additional verification
docker images | grep "${FUNCTION_NAME}"

# Step 4: Login to ECR
echo -e "${YELLOW}Logging in to ECR...${NC}"
aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com

# Step 5: Create ECR repository if it doesn't exist
echo -e "${YELLOW}Ensuring ECR repository exists...${NC}"
aws ecr describe-repositories --repository-names ${ECR_REPOSITORY} >/dev/null 2>&1 || \
    aws ecr create-repository --repository-name ${ECR_REPOSITORY}

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

# Step 6: Tag and push the image
echo -e "${YELLOW}Tagging and pushing image...${NC}"
docker tag ${ECR_REPOSITORY}:latest ${AWS_ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPOSITORY}:latest
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPOSITORY}:latest

# Step 7: Update Lambda function
echo -e "${YELLOW}Updating Lambda function...${NC}"
aws lambda update-function-code \
    --function-name ${FUNCTION_NAME} \
    --image-uri "${ECR_IMAGE_URI}"

# Update function configuration with token and environment variables
echo -e "${YELLOW}Updating Lambda configuration...${NC}"
aws lambda update-function-configuration \
              --function-name "${FUNCTION_NAME}" \
              --timeout 60 \
              --memory-size 512 \
              --environment "Variables={
                  TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN},
                  ENVIRONMENT=production,
                  LOG_LEVEL=INFO
              }" \
              --region ${REGION}

echo -e "${GREEN}Lambda function ${FUNCTION_NAME} updated successfully with container image!${NC}"

# Step 8: Clean up
echo -e "${YELLOW}Cleaning up...${NC}"
rm -f Dockerfile

echo -e "${GREEN}Deployment completed successfully!${NC}"