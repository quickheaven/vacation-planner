import json
import boto3

def lambda_handler(event, context):
    city = event['city']
    client = boto3.client('dynamodb')
    response = client.get_item(
        TableName='travel_packages',
        Key={'city': {'S': city}}
    )
    print(response)
    return {'statusCode': 200, 'body': json.dumps(response['Item'])}