from __future__ import annotations

import argparse
import asyncio

from dotenv import load_dotenv

from sentinel_lead_agent.models.lead_model import LeadIntelligenceRequest
from sentinel_lead_agent.services.config import Settings
from sentinel_lead_agent.services.lead_intelligence_service import LeadIntelligenceService


load_dotenv()


async def run_local_test(query: str, limit: int) -> str:
    settings = Settings.from_env()
    service = LeadIntelligenceService(settings)
    payload = LeadIntelligenceRequest(query=query, limit=limit)
    response = await service.generate_intelligence(payload)
    return response.model_dump_json(indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the lead intelligence pipeline locally without FastAPI or CrewAI AMP deployment.")
    parser.add_argument("--query", required=True, help="Lead search query")
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of leads to return")
    args = parser.parse_args()

    output = asyncio.run(run_local_test(query=args.query, limit=args.limit))
    print(output)


if __name__ == "__main__":
    main()