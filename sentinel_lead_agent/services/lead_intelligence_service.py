import asyncio

from sentinel_lead_agent.models.lead_model import (
    DiscoveredLead,
    LeadIntelligenceRecord,
    LeadIntelligenceRequest,
    LeadIntelligenceResponse,
)
from sentinel_lead_agent.services.logging_service import get_logger
from sentinel_lead_agent.services.openai_service import OpenAIAgentRuntime
from sentinel_lead_agent.tools.scoring_tool import LeadScoringTool
from sentinel_lead_agent.tools.scraper_tool import WebsiteScraperTool
from sentinel_lead_agent.tools.search_tool import LeadSearchTool


class LeadIntelligenceService:
    def __init__(self, settings) -> None:
        self.settings = settings
        self.logger = get_logger(__name__)
        self.search_tool = LeadSearchTool(settings)
        self.scraper_tool = WebsiteScraperTool(settings)
        self.scoring_tool = LeadScoringTool(settings)
        self.runtime = OpenAIAgentRuntime(settings, self.search_tool, self.scraper_tool, self.scoring_tool)

    async def generate_intelligence(self, payload: LeadIntelligenceRequest) -> LeadIntelligenceResponse:
        discovery_output = await self.runtime.discover(payload)
        leads = discovery_output.leads[: payload.limit]

        if not leads:
            raise ValueError("No leads were discovered. Provide a broader query or seed companies/websites.")

        records = await asyncio.gather(*(self._build_record(lead) for lead in leads))
        self.logger.info(
            "lead_intelligence_completed",
            extra={"query": payload.query, "lead_count": len(records)},
        )
        return LeadIntelligenceResponse(query=payload.query, total_leads=len(records), leads=records)

    async def _build_record(self, lead: DiscoveredLead) -> LeadIntelligenceRecord:
        analysis = await self.runtime.analyze(lead)
        qualification_output = await self.runtime.qualify(lead, analysis)
        outreach_output = await self.runtime.generate_outreach(lead, analysis, qualification_output)
        return LeadIntelligenceRecord(
            lead=lead,
            website_analysis=analysis,
            qualification=qualification_output.qualification,
            outreach=outreach_output.outreach,
        )