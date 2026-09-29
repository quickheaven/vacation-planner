import os
import requests
import json

# Set these in your environment before running:
#   set -x CLIENT_ID "your-client-id"
#   set -x CLIENT_SECRET "your-client-secret"
#   set -x TOKEN_URL "your-token-url"
#   set -x GATEWAY_URL "your-gateway-url"
#   python gwtest.py


CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]
TOKEN_URL = os.environ["TOKEN_URL"]

def fetch_access_token(client_id, client_secret, token_url):
  response = requests.post(
    token_url,
    data="grant_type=client_credentials&client_id={client_id}&client_secret={client_secret}".format(client_id=client_id, client_secret=client_secret),
    headers={'Content-Type': 'application/x-www-form-urlencoded'}
  )

  return response.json()['access_token']

def list_tools(gateway_url, access_token):
  headers = {
      "Content-Type": "application/json",
      "Authorization": f"Bearer {access_token}",
      "MCP-Protocol-Version": "2025-11-25" # Fix 'Unsupported protocol version: 2025-03-26'
  }

  payload = {
      "jsonrpc": "2.0",
      "id": "list-tools-request",
      "method": "tools/list"
  }

  response = requests.post(gateway_url, headers=headers, json=payload)
  return response.json()

def call_tool(gateway_url, access_token, tool_name, arguments):
  headers = {
      "Content-Type": "application/json",
      "Authorization": f"Bearer {access_token}",
      "MCP-Protocol-Version": "2025-11-25"
  }

  payload = {
      "jsonrpc": "2.0",
      "id": "call-tool-request",
      "method": "tools/call",
      "params": {
          "name": tool_name,     # Tool identifier
          "arguments": arguments # Input parameters for the tool
      }
  }

  response_tool = requests.post(gateway_url, headers=headers, json=payload)
  print("Travel Package Details:", response_tool.json())
  return response_tool.json()

# Example usage
gateway_url = os.environ["GATEWAY_URL"]
access_token = fetch_access_token(CLIENT_ID, CLIENT_SECRET, TOKEN_URL)
tools = list_tools(gateway_url, access_token)
print(json.dumps(tools, indent=2))

# Call the travel packages tool
tool_response = call_tool(gateway_url, access_token, "traveltool___get_travel_packages", {"city": "Mumbai"})
print(tool_response)