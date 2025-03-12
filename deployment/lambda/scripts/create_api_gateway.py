#!/usr/bin/env python3
import boto3
import json
import os

# Configuration
function_name = "telegram-ai-assistant"
api_name = "telegram-bot-api"
region = "us-east-1"
stage_name = "prod"

# Initialize AWS clients
lambda_client = boto3.client('lambda', region_name=region)
apigateway_client = boto3.client('apigatewayv2', region_name=region)

# Get Lambda function ARN
lambda_arn = lambda_client.get_function(FunctionName=function_name)['Configuration']['FunctionArn']

# Create HTTP API
print("Creating API Gateway HTTP API...")
api_response = apigateway_client.create_api(
    Name=api_name,
    ProtocolType='HTTP',
    Target=lambda_arn
)

api_id = api_response['ApiId']
print(f"API created with ID: {api_id}")

# Create stage
print("Creating API stage...")
apigateway_client.create_stage(
    ApiId=api_id,
    StageName=stage_name,
    AutoDeploy=True
)

# Create route and integration
print("Creating route and integration...")
integration_response = apigateway_client.create_integration(
    ApiId=api_id,
    IntegrationType='AWS_PROXY',
    IntegrationMethod='POST',
    PayloadFormatVersion='2.0',
    IntegrationUri=lambda_arn
)

route_response = apigateway_client.create_route(
    ApiId=api_id,
    RouteKey='POST /webhook',
    Target=f'integrations/{integration_response["IntegrationId"]}'
)

# Add Lambda permission for API Gateway
print("Adding Lambda permission...")
# Get the AWS account ID
account_id = boto3.client('sts').get_caller_identity().get('Account')
lambda_client.add_permission(
    FunctionName=function_name,
    StatementId=f'apigateway-invoke-{api_id}',
    Action='lambda:InvokeFunction',
    Principal='apigateway.amazonaws.com',
    SourceArn=f'arn:aws:execute-api:{region}:{account_id}:{api_id}/*/*/webhook'
)

# Get the API endpoint
endpoint = f"https://{api_id}.execute-api.{region}.amazonaws.com/{stage_name}/webhook"
print(f"Webhook URL: {endpoint}")

# Save the URL to a file for later use
with open('webhook_url.txt', 'w') as f:
    f.write(endpoint)

print("API Gateway setup complete. Use this URL for your Telegram webhook.")