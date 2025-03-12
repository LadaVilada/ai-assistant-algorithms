import boto3
import sys

def create_conversation_table(table_name='ConversationHistory'):
    """Create DynamoDB table for storing conversation history if it doesn't exist"""
    dynamodb = boto3.client('dynamodb')

    # Check if table already exists
    existing_tables = dynamodb.list_tables()['TableNames']
    if table_name in existing_tables:
        print(f"Table {table_name} already exists. Skipping creation.")
        return

    # Create the table
    print(f"Creating table {table_name}...")
    try:
        dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'session_id', 'KeyType': 'HASH'},
                {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'session_id', 'AttributeType': 'S'},
                {'AttributeName': 'timestamp', 'AttributeType': 'N'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )

        # Wait for the table to be created
        print("Waiting for table to be created...")
        waiter = dynamodb.get_waiter('table_exists')
        waiter.wait(TableName=table_name)

        # Enable TTL (optional)
        dynamodb.update_time_to_live(
            TableName=table_name,
            TimeToLiveSpecification={
                'Enabled': True,
                'AttributeName': 'ttl'
            }
        )

        print(f"Table {table_name} created successfully with TTL enabled.")

    except Exception as e:
        print(f"Error creating table: {e}")
        sys.exit(1)

if __name__ == "__main__":
    create_conversation_table()