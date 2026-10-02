import json
import boto3
import uuid

def lambda_handler(event, context):

    # Create a client connection with Bedrock AgentCore
    client = boto3.client('bedrock-agentcore', region_name='us-east-1')

    # Get user input from event, match to the expected Agent payload structure
    user_input = event.get('prompt', 'Tokyo')
    payload = json.dumps({'topic': user_input})

    # Generate unique session ID (must be 33+ characters long) using UUID without hypens
    session_id = f"lambda_session_{str(uuid.uuid4()).replace('-', '')}"

    print(f"Invoking AgentCore with payload: {payload} & session_id: {session_id}")

    # Invoke the AgentCore runtime with the vacation planner agent
    response = client.invoke_agent_runtime(
        # agentRuntimeArn='arn:aws:bedrock-agentcore:us-east-1:601958100101:runtime/vacation_planner_agent-56Ni6B7ZLQ',
        agentRuntimeArn='arn:aws:bedrock-agentcore:us-east-1:601958100101:runtime/vacation_planner_agent_gateway_tools-7cYLuOEBA8',
        runtimeSessionId=session_id, # Must be 33+ characters
        payload=payload,
        qualifier="DEFAULT" # Optional
    )

    # Read and parse the response from AgentCore
    response_body = response['response'].read()
    print(f"Response body: {response_body}")

    response_data = json.loads(response_body)

    # Return successful Lambda response with CORS headers
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
        },
        'body': json.dumps({
            'result': response_data,
            'session_id': session_id
        })
    }    