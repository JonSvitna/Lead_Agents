import json
import os

from agents import Runner, function_tool

from sentinel_lead_agent.agents.analyzer_agent import build_analyzer_agent
from sentinel_lead_agent.agents.discovery_agent import build_discovery_agent
from sentinel_lead_agent.agents.outreach_agent import build_outreach_agent
from sentinel_lead_agent.agents.qualification_agent import build_qualification_agent
from sentinel_lead_agent.models.lead_model import (
	DiscoveredLead,
	DiscoveryAgentOutput,
	LeadIntelligenceRequest,
	OutreachAgentOutput,
	QualificationAgentOutput,
	WebsiteAnalysis,
	WebsiteAnalysisAgentOutput,
)
from sentinel_lead_agent.services.logging_service import get_logger


class OpenAIAgentRuntime:
	def __init__(self, settings, search_tool, scraper_tool, scoring_tool) -> None:
		self.settings = settings
		if settings.openai_api_key:
			os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)
		self.search_tool = search_tool
		self.scraper_tool = scraper_tool
		self.scoring_tool = scoring_tool
		self.logger = get_logger(__name__)

		self.discovery_agent = build_discovery_agent(self._build_search_businesses_tool(), settings.openai_model)
		self.analyzer_agent = build_analyzer_agent(self._build_scrape_website_tool(), settings.openai_model)
		self.qualification_agent = build_qualification_agent(self._build_score_lead_tool(), settings.openai_model)
		self.outreach_agent = build_outreach_agent(settings.openai_model)

	def _ensure_runtime_configured(self) -> None:
		if not self.settings.openai_api_key:
			raise RuntimeError("OPENAI_API_KEY is required to run the lead intelligence agents.")

	def _build_search_businesses_tool(self):
		search_service = self.search_tool

		@function_tool
		async def search_businesses(
			query: str,
			limit: int = 5,
			search_terms: list[str] | None = None,
			location_text: str | None = None,
			zip_code: str | None = None,
			city: str | None = None,
			state: str | None = None,
			region: str | None = None,
			radius_miles: int | None = None,
		) -> str:
			"""Search for candidate business leads and return structured JSON results."""
			leads = await search_service.search_businesses(
				query=query,
				limit=limit,
				search_terms=search_terms,
				location_text=location_text,
				zip_code=zip_code,
				city=city,
				state=state,
				region=region,
				radius_miles=radius_miles,
			)
			return json.dumps([lead.model_dump(mode="json") for lead in leads], indent=2)

		return search_businesses

	def _build_scrape_website_tool(self):
		scraper_service = self.scraper_tool

		@function_tool
		async def scrape_website(url: str) -> str:
			"""Scrape a company website and return structured page content for analysis."""
			payload = await scraper_service.scrape_website(url)
			return payload.model_dump_json(indent=2)

		return scrape_website

	def _build_score_lead_tool(self):
		scoring_service = self.scoring_tool

		@function_tool
		async def score_lead(lead_json: str, analysis_json: str | None = None) -> str:
			"""Generate a deterministic lead scorecard from a discovered lead and optional website analysis."""
			lead = DiscoveredLead.model_validate_json(lead_json)
			analysis = WebsiteAnalysis.model_validate_json(analysis_json) if analysis_json else None
			scorecard = scoring_service.score_lead(lead, analysis)
			return scorecard.model_dump_json(indent=2)

		return score_lead

	async def discover(self, payload: LeadIntelligenceRequest) -> DiscoveryAgentOutput:
		self._ensure_runtime_configured()

		if not payload.query and not payload.seed_companies and not payload.websites:
			raise ValueError("Provide at least one of: query, seed_companies, or websites.")

		# Deterministic discovery avoids LLM-only misses and always executes provider search first.
		leads = await self.search_tool.search_businesses(
			query=payload.query,
			limit=payload.limit,
			search_terms=payload.search_terms,
			location_text=payload.location_text,
			zip_code=payload.zip_code,
			city=payload.city,
			state=payload.state,
			region=payload.region,
			radius_miles=payload.radius_miles,
			seed_companies=payload.seed_companies,
			websites=payload.websites,
		)
		return DiscoveryAgentOutput(leads=leads)

	async def analyze(self, lead: DiscoveredLead) -> WebsiteAnalysis | None:
		self._ensure_runtime_configured()
		if not lead.website:
			return None

		request_text = (
			"Analyze this company website for government contracting signals, compliance indicators, "
			f"service offerings, and likely cybersecurity pain points: {lead.website}."
		)
		result = await Runner.run(self.analyzer_agent, request_text)
		output = result.final_output
		if isinstance(output, WebsiteAnalysisAgentOutput):
			return output.analysis
		return WebsiteAnalysisAgentOutput.model_validate(output).analysis

	async def qualify(
		self,
		lead: DiscoveredLead,
		analysis: WebsiteAnalysis | None,
	) -> QualificationAgentOutput:
		self._ensure_runtime_configured()
		request_text = (
			"Qualify this lead using the deterministic score tool and the supplied context. "
			"Return a practical decision with score, risks, best contact title, and outreach angle.\n\n"
			f"Lead: {lead.model_dump_json(indent=2)}\n\n"
			f"Website analysis: {analysis.model_dump_json(indent=2) if analysis else 'null'}"
		)
		result = await Runner.run(self.qualification_agent, request_text)
		output = result.final_output
		if isinstance(output, QualificationAgentOutput):
			return output
		return QualificationAgentOutput.model_validate(output)

	async def generate_outreach(
		self,
		lead: DiscoveredLead,
		analysis: WebsiteAnalysis | None,
		qualification: QualificationAgentOutput,
	) -> OutreachAgentOutput:
		self._ensure_runtime_configured()
		request_text = (
			"Generate practical first-touch outreach for this lead. Keep it concise, relevant, and grounded in the qualification context.\n\n"
			f"Lead: {lead.model_dump_json(indent=2)}\n\n"
			f"Website analysis: {analysis.model_dump_json(indent=2) if analysis else 'null'}\n\n"
			f"Qualification: {qualification.model_dump_json(indent=2)}"
		)
		result = await Runner.run(self.outreach_agent, request_text)
		output = result.final_output
		if isinstance(output, OutreachAgentOutput):
			return output
		return OutreachAgentOutput.model_validate(output)
