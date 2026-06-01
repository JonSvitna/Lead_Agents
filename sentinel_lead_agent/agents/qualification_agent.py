from agents import Agent

from sentinel_lead_agent.models.lead_model import QualificationAgentOutput
from sentinel_lead_agent.services.prompt_service import build_agent_instructions


def build_qualification_agent(score_tool, model: str) -> Agent:
	return Agent(
		name="Qualification Agent",
		model=model,
		instructions=build_agent_instructions("qualification_agent.txt", include_scoring_rules=True),
		tools=[score_tool],
		output_type=QualificationAgentOutput,
	)
