from __future__ import annotations

import argparse
import asyncio
from typing import Any

from crewai import Agent, Crew, Process, Task
from crewai.tools import BaseTool
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from sentinel_lead_agent.models.lead_model import LeadIntelligenceRequest
from sentinel_lead_agent.services.config import Settings
from sentinel_lead_agent.services.lead_intelligence_service import LeadIntelligenceService


load_dotenv()


class LeadIntelligenceToolInput(BaseModel):
    query: str = Field(description="Lead search query.")
    limit: int = Field(default=5, ge=1, le=20, description="Maximum number of leads.")


class LeadIntelligenceTool(BaseTool):
    name: str = "run_lead_intelligence"
    description: str = (
        "Run the Sentinel lead-intelligence pipeline and return structured JSON including discovery, analysis, qualification, and outreach."
    )
    args_schema: type[BaseModel] = LeadIntelligenceToolInput

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
    tool = LeadIntelligenceTool()

    orchestrator = Agent(
        role="Lead Intelligence Operator",
        goal="Generate high-signal lead intelligence outputs with practical qualification and outreach recommendations.",
        backstory=(
            "You are a focused operations analyst. You call the lead intelligence tool and return grounded, JSON-first outputs "
            "without inventing company details."
        ),
        tools=[tool],
        allow_delegation=False,
        verbose=True,
    )

    task = Task(
        description=(
            "Run lead intelligence for query '{query}' with limit {limit}. "
            "Use the tool and return the final structured JSON exactly as produced by the pipeline."
        ),
        expected_output="Structured JSON response from the lead-intelligence pipeline.",
        agent=orchestrator,
    )

    return Crew(
        agents=[orchestrator],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    )


def kickoff(query: str, limit: int = 5) -> Any:
    crew = build_crew()
    return crew.kickoff(inputs={"query": query, "limit": limit})


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Lead_Agents through a CrewAI entrypoint.")
    parser.add_argument("--query", required=True, help="Lead search query")
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of leads (1-20)")
    args = parser.parse_args()

    result = kickoff(query=args.query, limit=args.limit)
    print(result)


if __name__ == "__main__":
    main()
