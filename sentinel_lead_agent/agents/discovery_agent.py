from agents import Agent

from sentinel_lead_agent.models.lead_model import DiscoveryAgentOutput
from sentinel_lead_agent.services.prompt_service import build_agent_instructions


def build_discovery_agent(search_tool, model: str) -> Agent:
	return Agent(
		name="Discovery Agent",
		model=model,
		instructions=build_agent_instructions("discovery_agent.txt"),
		tools=[search_tool],
		output_type=DiscoveryAgentOutput,
	)
