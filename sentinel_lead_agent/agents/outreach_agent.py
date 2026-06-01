from agents import Agent

from sentinel_lead_agent.models.lead_model import OutreachAgentOutput
from sentinel_lead_agent.services.prompt_service import build_agent_instructions


def build_outreach_agent(model: str) -> Agent:
	return Agent(
		name="Outreach Generation Agent",
		model=model,
		instructions=build_agent_instructions("outreach_agent.txt"),
		output_type=OutreachAgentOutput,
	)
