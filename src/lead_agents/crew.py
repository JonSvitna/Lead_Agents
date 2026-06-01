from __future__ import annotations

import asyncio
from typing import List

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task
from crewai.tools import BaseTool
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from sentinel_lead_agent.models.lead_model import LeadIntelligenceRequest
from sentinel_lead_agent.services.config import Settings
from sentinel_lead_agent.services.lead_intelligence_service import LeadIntelligenceService


load_dotenv()


class LeadIntelligenceToolInput(BaseModel):
    query: str = Field(description="Lead search query.")
    limit: int = Field(default=5, ge=1, le=20, description="Maximum number of leads to return.")


class LeadIntelligenceTool(BaseTool):
    name: str = "run_lead_intelligence"
    description: str = "Run the Sentinel lead intelligence pipeline and return structured JSON output."
    args_schema: type[BaseModel] = LeadIntelligenceToolInput

    def _run(self, query: str, limit: int = 5) -> str:
        settings = Settings.from_env()
        service = LeadIntelligenceService(settings)
        payload = LeadIntelligenceRequest(query=query, limit=limit)
        response = asyncio.run(service.generate_intelligence(payload))
        return response.model_dump_json(indent=2)


@CrewBase
class LeadAgentsCrew:
    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def lead_intelligence_operator(self) -> Agent:
        return Agent(
            config=self.agents_config["lead_intelligence_operator"],  # type: ignore[index]
            tools=[LeadIntelligenceTool()],
            verbose=True,
            allow_delegation=False,
        )

    @task
    def run_lead_intelligence(self) -> Task:
        return Task(
            config=self.tasks_config["run_lead_intelligence"],  # type: ignore[index]
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )


def kickoff(inputs: dict | None = None):
    payload = inputs or {"query": "Maryland defense subcontractor MSP", "limit": 5}
    return LeadAgentsCrew().crew().kickoff(inputs=payload)
