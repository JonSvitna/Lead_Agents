from agents import Agent

from sentinel_lead_agent.models.lead_model import WebsiteAnalysisAgentOutput
from sentinel_lead_agent.services.prompt_service import build_agent_instructions


def build_analyzer_agent(scrape_tool, model: str) -> Agent:
	return Agent(
		name="Website Analyzer Agent",
		model=model,
		instructions=build_agent_instructions("analyzer_agent.txt"),
		tools=[scrape_tool],
		output_type=WebsiteAnalysisAgentOutput,
	)
