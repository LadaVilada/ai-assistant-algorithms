#!/bin/bash
set -e

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Lambda role configuration
ROLE_NAME="telegram-ai-assistant-lambda-role"
REGION="us-east-1"

# Ensure AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}AWS CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if role already exists
if aws iam get-role --role-name "$ROLE_NAME" &> /dev/null; then
    echo -e "${YELLOW}Role $ROLE_NAME already exists. Updating policies...${NC}"
else
    echo -e "${YELLOW}Creating IAM role: $ROLE_NAME${NC}"
    # Create IAM role
    aws iam create-role \
        --role-name "$ROLE_NAME" \
        --assume-role-policy-document file://deployment/lambda/config/trust_policy.json
fi

# Attach necessary policies
echo -e "${YELLOW}Attaching Lambda execution policies...${NC}"

# Basic Lambda execution policy
aws iam attach-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# DynamoDB access
aws iam attach-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess

# Secrets Manager access
aws iam attach-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/SecretsManagerReadWrite

# Optional: Add more specific policies as needed

echo -e "${GREEN}Lambda IAM role $ROLE_NAME created and configured successfully!${NC}"

# Get and display the role ARN
ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" --query 'Role.Arn' --output text)
echo -e "${GREEN}Role ARN: $ROLE_ARN${NC}"