from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool
import os
from crewai import LLM

#1 Memory - imports
import boto3
import uuid
from datetime import datetime

#1AgentCore GW imports 
from crewai.tools import tool
import requests

# ---------- #1 Agentcore imports  --------------------
from bedrock_agentcore.runtime import BedrockAgentCoreApp
app = BedrockAgentCoreApp()

#Initialize SerperDev Tool
serper_dev_tool=SerperDevTool(api_key=os.environ.get("SERPER_API_KEY"))
llm=LLM(model="bedrock/us.amazon.nova-pro-v1:0")

# If you want to run a snippet of code before or after the crew starts,
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators


#2 Memory client initialization
memory_client = boto3.client('bedrock-agentcore', region_name='us-east-1')

#2 AgentCore Gateway Code
CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]
TOKEN_URL = os.environ["TOKEN_URL"]
GATEWAY_URL = os.environ["GATEWAY_URL"]

def fetch_access_token(client_id, client_secret, token_url):
    response = requests.post(
        token_url,
        data="grant_type=client_credentials&client_id={client_id}&client_secret={client_secret}".format(client_id=client_id, client_secret=client_secret),
        headers={'Content-Type': 'application/x-www-form-urlencoded'}
    )
    return response.json()['access_token']

def call_tool(gateway_url, access_token, tool_name, arguments):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    payload = {
        "jsonrpc": "2.0",
        "id": "call-tool-request",
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    response_tool = requests.post(gateway_url, headers=headers, json=payload)
    return response_tool.json()

#3 AgentCore GW - wrap your existing functions as a CrewAI tool - https://docs.crewai.com/en/concepts/tools#utilizing-the-tool-decorator
@tool("Get Travel Packages")
def get_travel_packages(city: str) -> str:
    """Fetches available travel packages for a given city from the AgentCore Gateway."""
    access_token = fetch_access_token(CLIENT_ID, CLIENT_SECRET, TOKEN_URL)
    result = call_tool(GATEWAY_URL, access_token, "traveltool___get_travel_packages", {"city": city})
    return str(result)

@CrewBase
class VacationPlanner():
    """VacationPlanner crew"""

    # Learn more about YAML configuration files here:
    # Agents: https://docs.crewai.com/concepts/agents#yaml-configuration-recommended
    # Tasks: https://docs.crewai.com/concepts/tasks#yaml-configuration-recommended
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    # If you would like to add tools to your agents, you can learn more about it here:
    # https://docs.crewai.com/concepts/agents#agent-tools
    @agent
    def vacation_researcher(self) -> Agent:
        return Agent(
            config=self.agents_config['vacation_researcher'],
            verbose=True,
            tools=[serper_dev_tool, get_travel_packages],
            llm=llm
        )

    @agent
    def itinerary_planner(self) -> Agent:
        return Agent(
            config=self.agents_config['itinerary_planner'],
            verbose=True,
            llm=llm
        )

    # To learn more about structured task outputs,
    # task dependencies, and task callbacks, check out the documentation:
    # https://docs.crewai.com/concepts/tasks#overview-of-a-task
    @task
    def research_task(self) -> Task:
        return Task(
            config=self.tasks_config['research_task'],
        )

    @task
    def reporting_task(self) -> Task:
        return Task(
            config=self.tasks_config['reporting_task'],
            output_file='report.md'
        )

    @crew
    def crew(self) -> Crew:
        """Creates the VacationPlanner crew"""
        # To learn how to add knowledge sources to your crew, check out the documentation:
        # https://docs.crewai.com/concepts/knowledge#what-is-knowledge

        return Crew(
            agents=self.agents, # Automatically created by the @agent decorator
            tasks=self.tasks, # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
            # process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
        )

    #3 --------@agentcore.entrypoint decorator- Python decorator within the Bedrock AgentCore SDK--------------------
    #  Function to be executed by the runtime on an event (prompt) & Creates WebServer Endpoints
    @app.entrypoint
    def agent_invocation(payload, context):
        """Handler for agent invocation"""
        print(f'Payload: {payload}')
        try: 
            # Extract user input from payload
            user_input = payload.get("topic", "Tokyo, Japan")
            print(f"Processing vacation destination: {user_input}")

            #3 Memory - Retrieve past memory
            session_id = getattr(context, "sessionId", "default_session")
            
            previous_events = memory_client.list_events(
                memoryId='vacation_planner_demo-MgKDiz44Nx',
                actorId='user',
                sessionId=session_id,
                maxResults=3
            )            
            
            # Crew Execution - Creates an instance of the VacationPlanner class and run crew method
            research_crew_instance = VacationPlanner()
            crew = research_crew_instance.crew()

            # Send input to Agent with previous memory
            events = previous_events.get('events', [])
            formatted_conversations = []
            for event in events:
                formatted_event = {}
                for key, value in event.items():
                    if isinstance(value, datetime):
                        formatted_event[key] = value.isoformat()
                    else:
                        formatted_event[key] = value
                formatted_conversations.append(formatted_event)

            #4 Memory - Starts the sequential agent workflow with memory
            result = crew.kickoff(inputs={'topic': user_input, 'previous_conversations': formatted_conversations})

            #5 Memory storage - Save current interaction
            memory_client.create_event(
                memoryId='vacation_planner_demo-MgKDiz44Nx',
                actorId='user',
                sessionId=session_id,
                eventTimestamp=datetime.utcnow(),
                payload=[
                    {
                        "conversational": {
                            "content": {"text": user_input},
                            "role": "USER"
                        }
                    },
                    {
                        "conversational": {
                            "content": {"text": result.raw},
                            "role": "ASSISTANT"
                        }
                    }
                ],
                clientToken=str(uuid.uuid4())
            )

            print("Context:\n-------\n", context)
            print("Result Raw:\n*******\n", result.raw)
            
            # Safely access json_dict if it exists
            if hasattr(result, 'json_dict'):
                print("Result JSON:\n*******\n", result.json_dict)
            
            return {"result": result.raw}
            
        except Exception as e:
            print(f'Exception occurred: {e}')
            return {"error": f"An error occurred: {str(e)}"}

    # Local test function
    def test_local():
        """Test the crew locally without AgentCore"""
        try:
            crew_instance = VacationPlanner()
            crew = crew_instance.crew()
            result = crew.kickoff(inputs={'topic': 'Plan a vacation to Germany'})
            print("Result:", result.raw)
            return result
        except Exception as e:
            print(f"Error: {e}")
            return None

if __name__ == "__main__":
    app.run(port=8080)