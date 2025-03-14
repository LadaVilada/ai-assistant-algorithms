#!/usr/bin/env python3
import argparse
import os

import boto3
import requests
from dotenv import load_dotenv


def setup_api_gateway():
    # Load environment variables
    load_dotenv()

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Set up API Gateway for Lambda function')
    parser.add_argument('--function-name', default="telegram-lambda-minimal",
                        help='Lambda function name (default: telegram-lambda-minimal)')
    parser.add_argument('--api-name', default="telegram-webhook-api",
                        help='API Gateway name (default: telegram-webhook-api)')
    parser.add_argument('--region', default="us-east-1",
                        help='AWS region (default: us-east-1)')
    parser.add_argument('--stage-name', default="prod",
                        help='API Gateway stage name (default: prod)')

    args = parser.parse_args()

    # Configuration
    function_name = args.function_name
    api_name = args.api_name
    region = args.region
    stage_name = args.stage_name
    telegram_token = os.environ.get('TELEGRAM_BOT_TOKEN')

    if not telegram_token:
        print("Warning: TELEGRAM_BOT_TOKEN not found in environment variables or .env file")
        telegram_token = input("Enter your Telegram bot token: ")

    # Initialize AWS clients
    lambda_client = boto3.client('lambda', region_name=region)
    apigatewayv2_client = boto3.client('apigatewayv2', region_name=region)
    sts_client = boto3.client('sts')

    print(f"\n{'-'*60}")
    print(f"Setting up API Gateway for Lambda function: {function_name}")
    print(f"{'-'*60}\n")

    # Get Lambda function ARN
    try:
        lambda_arn = lambda_client.get_function(FunctionName=function_name)['Configuration']['FunctionArn']
        print(f"✅ Found Lambda function: {function_name}")
    except Exception as e:
        print(f"❌ Error: Lambda function '{function_name}' not found. Make sure it's deployed first.")
        print(f"Error details: {str(e)}")
        return

    # Check if API already exists
    try:
        apis = apigatewayv2_client.get_apis()
        existing_api = next((api for api in apis.get('Items', []) if api['Name'] == api_name), None)

        if existing_api:
            api_id = existing_api['ApiId']
            print(f"ℹ️ API '{api_name}' already exists with ID: {api_id}")
            should_recreate = input("Do you want to delete and recreate it? (y/N): ").lower() == 'y'

            if should_recreate:
                print(f"🗑️ Deleting existing API...")
                apigatewayv2_client.delete_api(ApiId=api_id)
                print(f"✅ Existing API deleted.")
                api_id = None
            else:
                print(f"ℹ️ Using existing API.")
        else:
            api_id = None

    except Exception as e:
        print(f"❌ Error checking existing APIs: {str(e)}")
        api_id = None

    # Create HTTP API if needed
    if not api_id:
        try:
            print("🔄 Creating API Gateway HTTP API...")
            api_response = apigatewayv2_client.create_api(
                Name=api_name,
                ProtocolType='HTTP',
                Target=lambda_arn
            )
            api_id = api_response['ApiId']
            print(f"✅ API created with ID: {api_id}")
        except Exception as e:
            print(f"❌ Error creating API: {str(e)}")
            return

    # Get or create stage
    try:
        stages = apigatewayv2_client.get_stages(ApiId=api_id)
        existing_stage = next((stage for stage in stages.get('Items', []) if stage['StageName'] == stage_name), None)

        if not existing_stage:
            print(f"🔄 Creating API stage: {stage_name}...")
            apigatewayv2_client.create_stage(
                ApiId=api_id,
                StageName=stage_name,
                AutoDeploy=True
            )
            print(f"✅ Stage created: {stage_name}")
    except Exception as e:
        print(f"❌ Error with stage creation: {str(e)}")

    # Create /webhook route and integration
    try:
        # Get routes to check if webhook route exists
        routes = apigatewayv2_client.get_routes(ApiId=api_id)
        webhook_route = next((route for route in routes.get('Items', [])
                              if route['RouteKey'] == 'POST /webhook'), None)

        if not webhook_route:
            print("🔄 Creating Lambda integration...")
            integration_response = apigatewayv2_client.create_integration(
                ApiId=api_id,
                IntegrationType='AWS_PROXY',
                IntegrationMethod='POST',
                PayloadFormatVersion='2.0',
                IntegrationUri=lambda_arn
            )

            print("🔄 Creating webhook route...")
            route_response = apigatewayv2_client.create_route(
                ApiId=api_id,
                RouteKey='POST /webhook',
                Target=f'integrations/{integration_response["IntegrationId"]}'
            )
            print("✅ Webhook route created")
        else:
            print("ℹ️ Webhook route already exists")
    except Exception as e:
        print(f"❌ Error setting up route or integration: {str(e)}")

    # Add Lambda permission for API Gateway
    try:
        print("🔄 Adding Lambda permission...")
        # Get the AWS account ID
        account_id = sts_client.get_caller_identity().get('Account')

        # Create a unique statement ID to avoid duplicates
        statement_id = f'apigateway-invoke-{api_id}-{stage_name}'

        try:
            # Check if permission already exists by trying to remove it first
            lambda_client.remove_permission(
                FunctionName=function_name,
                StatementId=statement_id
            )
            print("ℹ️ Removed existing permission")
        except Exception:
            # Permission doesn't exist, which is fine
            pass

        lambda_client.add_permission(
            FunctionName=function_name,
            StatementId=statement_id,
            Action='lambda:InvokeFunction',
            Principal='apigateway.amazonaws.com',
            SourceArn=f'arn:aws:execute-api:{region}:{account_id}:{api_id}/*/*/webhook'
        )
        print("✅ Lambda permission added")
    except Exception as e:
        print(f"❌ Error adding Lambda permission: {str(e)}")

    # Get the API endpoint
    endpoint = f"https://{api_id}.execute-api.{region}.amazonaws.com/{stage_name}/webhook"
    print(f"\n🔗 Webhook URL: {endpoint}")

    # Save the URL to a file for later use
    with open('webhook_url.txt', 'w') as f:
        f.write(endpoint)

    # Set Telegram webhook if token is provided
    if telegram_token:
        try:
            print("\n🔄 Setting Telegram webhook...")
            webhook_url = f"https://api.telegram.org/bot{telegram_token}/setWebhook?url={endpoint}"
            response = requests.get(webhook_url)
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    print("✅ Telegram webhook set successfully!")
                else:
                    print(f"❌ Telegram API error: {result.get('description')}")
            else:
                print(f"❌ HTTP Error: {response.status_code}")
        except Exception as e:
            print(f"❌ Error setting Telegram webhook: {str(e)}")

    print(f"\n{'-'*60}")
    print("✅ API Gateway setup complete! Your Telegram bot should now be accessible.")
    print(f"{'-'*60}")
    print("\nTo test your bot, send a message to it in Telegram.")
    print("To check webhook status: " +
          f"https://api.telegram.org/bot{telegram_token[:3]}...{telegram_token[-3:]}/getWebhookInfo")

if __name__ == '__main__':
    setup_api_gateway()