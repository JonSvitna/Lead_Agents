from __future__ import annotations

import asyncio
import json
from typing import Any

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
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


@CrewBase
class LeadAgentsCrew:
    """AI-powered Lead Intelligence crew."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def lead_discovery_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["lead_discovery_agent"],
            tools=[DiscoveryTool()],
            allow_delegation=False,
            verbose=True,
        )

    @agent
    def website_analyzer_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["website_analyzer_agent"],
            tools=[AnalyzerTool()],
            allow_delegation=False,
            verbose=True,
        )

    @agent
    def qualification_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["qualification_agent"],
            tools=[QualificationTool()],
            allow_delegation=False,
            verbose=True,
        )

    @agent
    def outreach_generation_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["outreach_generation_agent"],
            tools=[OutreachTool()],
            allow_delegation=False,
            verbose=True,
        )

    @task
    def run_discovery_stage(self) -> Task:
        return Task(config=self.tasks_config["run_discovery_stage"])

    @task
    def run_analyzer_stage(self) -> Task:
        return Task(config=self.tasks_config["run_analyzer_stage"])

    @task
    def run_qualification_stage(self) -> Task:
        return Task(config=self.tasks_config["run_qualification_stage"])

    @task
    def run_outreach_stage(self) -> Task:
        return Task(config=self.tasks_config["run_outreach_stage"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )


def kickoff(inputs: dict | None = None) -> Any:
    payload = inputs or {"query": "Maryland defense subcontractor MSP", "limit": 5}
    return LeadAgentsCrew().crew().kickoff(inputs=payload)
