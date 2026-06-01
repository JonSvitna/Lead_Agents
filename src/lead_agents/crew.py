from __future__ import annotations

import asyncio
import json
from typing import Any

from crewai import Agent, Crew, Process, Task
from crewai.tools import BaseTool
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from sentinel_lead_agent.models.lead_model import LeadIntelligenceRequest
from sentinel_lead_agent.services.config import Settings
from sentinel_lead_agent.services.lead_intelligence_service import LeadIntelligenceService
from sentinel_lead_agent.services.openai_service import OpenAIAgentRuntime
from sentinel_lead_agent.tools.scoring_tool import LeadScoringTool
from sentinel_lead_agent.tools.scraper_tool import WebsiteScraperTool
from sentinel_lead_agent.tools.search_tool import LeadSearchTool


load_dotenv()


class StageInput(BaseModel):
    query: str = Field(description="Lead search query.")
    limit: int = Field(default=5, ge=1, le=20, description="Maximum number of leads.")


def _build_runtime() -> OpenAIAgentRuntime:
    settings = Settings.from_env()
    search_tool = LeadSearchTool(settings)
    scraper_tool = WebsiteScraperTool(settings)
    scoring_tool = LeadScoringTool(settings)
    return OpenAIAgentRuntime(settings, search_tool, scraper_tool, scoring_tool)


class DiscoveryTool(BaseTool):
    name: str = "run_discovery_stage"
    description: str = "Run lead discovery and return structured discovery JSON with candidate leads."
    args_schema: type[BaseModel] = StageInput

    def _run(self, query: str, limit: int = 5) -> str:
        runtime = _build_runtime()
        payload = LeadIntelligenceRequest(query=query, limit=limit)
        output = asyncio.run(runtime.discover(payload))
        return output.model_dump_json(indent=2)


class AnalyzerTool(BaseTool):
    name: str = "run_analyzer_stage"
    description: str = "Run website analysis for discovered leads and return structured analysis JSON."
    args_schema: type[BaseModel] = StageInput

    def _run(self, query: str, limit: int = 5) -> str:
        runtime = _build_runtime()
        payload = LeadIntelligenceRequest(query=query, limit=limit)
        discovery = asyncio.run(runtime.discover(payload))

        analyses: list[dict[str, Any]] = []
        for lead in discovery.leads[:limit]:
            analysis = asyncio.run(runtime.analyze(lead))
            analyses.append(
                {
                    "lead": lead.model_dump(mode="json"),
                    "analysis": analysis.model_dump(mode="json") if analysis else None,
                }
            )

        return json.dumps({"query": query, "limit": limit, "analyses": analyses}, indent=2)


class QualificationTool(BaseTool):
    name: str = "run_qualification_stage"
    description: str = "Run lead qualification on discovered and analyzed leads and return structured qualification JSON."
    args_schema: type[BaseModel] = StageInput

    def _run(self, query: str, limit: int = 5) -> str:
        runtime = _build_runtime()
        payload = LeadIntelligenceRequest(query=query, limit=limit)
        discovery = asyncio.run(runtime.discover(payload))

        qualifications: list[dict[str, Any]] = []
        for lead in discovery.leads[:limit]:
            analysis = asyncio.run(runtime.analyze(lead))
            qualification = asyncio.run(runtime.qualify(lead, analysis))
            qualifications.append(
                {
                    "lead": lead.model_dump(mode="json"),
                    "analysis": analysis.model_dump(mode="json") if analysis else None,
                    "qualification": qualification.model_dump(mode="json"),
                }
            )

        return json.dumps({"query": query, "limit": limit, "qualifications": qualifications}, indent=2)


class OutreachTool(BaseTool):
    name: str = "run_outreach_stage"
    description: str = "Run the complete outreach stage and return final lead intelligence JSON."
    args_schema: type[BaseModel] = StageInput

    def _run(self, query: str, limit: int = 5) -> str:
        settings = Settings.from_env()
        service = LeadIntelligenceService(settings)
        payload = LeadIntelligenceRequest(query=query, limit=limit)

        try:
            response = asyncio.run(service.generate_intelligence(payload))
        except RuntimeError as exc:
            return f"Lead intelligence execution failed: {exc}"

        return response.model_dump_json(indent=2)


def build_crew() -> Crew:
    discovery_agent = Agent(
        role="Lead Discovery Agent",
        goal="Find grounded lead candidates for the search query.",
        backstory="You identify candidate companies from trusted search results and avoid fabricated data.",
        tools=[DiscoveryTool()],
        allow_delegation=False,
        verbose=True,
    )

    analyzer_agent = Agent(
        role="Website Analyzer Agent",
        goal="Analyze discovered lead websites for compliance and government-contracting signals.",
        backstory="You extract practical website signals that support qualification decisions.",
        tools=[AnalyzerTool()],
        allow_delegation=False,
        verbose=True,
    )

    qualification_agent = Agent(
        role="Qualification Agent",
        goal="Score and prioritize leads based on evidence from discovery and analysis.",
        backstory="You turn lead evidence into actionable qualification output.",
        tools=[QualificationTool()],
        allow_delegation=False,
        verbose=True,
    )

    outreach_agent = Agent(
        role="Outreach Generation Agent",
        goal="Generate outreach content from qualified lead context.",
        backstory="You produce concise outreach grounded in the qualification and website context.",
        tools=[OutreachTool()],
        allow_delegation=False,
        verbose=True,
    )

    discovery_task = Task(
        description=(
            "Run discovery for query '{query}' with limit {limit}. "
            "Use run_discovery_stage and return the structured discovery JSON."
        ),
        expected_output="Structured JSON with discovered leads.",
        agent=discovery_agent,
    )

    analyzer_task = Task(
        description=(
            "Run analyzer stage for query '{query}' with limit {limit}. "
            "Use run_analyzer_stage and return structured analysis JSON for discovered leads."
        ),
        expected_output="Structured JSON with lead analyses.",
        agent=analyzer_agent,
        context=[discovery_task],
    )

    qualification_task = Task(
        description=(
            "Run qualification stage for query '{query}' with limit {limit}. "
            "Use run_qualification_stage and return structured qualification JSON."
        ),
        expected_output="Structured JSON with lead qualification output.",
        agent=qualification_agent,
        context=[discovery_task, analyzer_task],
    )

    outreach_task = Task(
        description=(
            "Run final outreach stage for query '{query}' with limit {limit}. "
            "Use run_outreach_stage and return the final structured pipeline JSON exactly as produced."
        ),
        expected_output="Final structured JSON response from the lead-intelligence pipeline.",
        agent=outreach_agent,
        context=[discovery_task, analyzer_task, qualification_task],
    )

    return Crew(
        agents=[discovery_agent, analyzer_agent, qualification_agent, outreach_agent],
        tasks=[discovery_task, analyzer_task, qualification_task, outreach_task],
        process=Process.sequential,
        verbose=True,
    )


def kickoff(inputs: dict | None = None) -> Any:
    payload = inputs or {"query": "Maryland defense subcontractor MSP", "limit": 5}
    return build_crew().kickoff(inputs=payload)
