import asyncio

from sentinel_lead_agent.models.lead_model import DiscoveredLead, LeadSeedInput, SourceReference
from sentinel_lead_agent.services.logging_service import get_logger

try:
    from firecrawl import Firecrawl
except ImportError:  # pragma: no cover - depends on runtime environment
    Firecrawl = None


class LeadSearchTool:
    def __init__(self, settings) -> None:
        self.settings = settings
        self.logger = get_logger(__name__)

    async def search_businesses(
        self,
        query: str | None,
        limit: int,
        seed_companies: list[LeadSeedInput] | None = None,
        websites: list[str] | None = None,
    ) -> list[DiscoveredLead]:
        seed_companies = seed_companies or []
        websites = websites or []

        if query and self.settings.firecrawl_enabled and Firecrawl is not None:
            return await asyncio.to_thread(self._search_with_firecrawl, query, limit)

        return self._search_from_inputs(seed_companies, websites, limit)

    def _search_with_firecrawl(self, query: str, limit: int) -> list[DiscoveredLead]:
        client = Firecrawl(api_key=self.settings.firecrawl_api_key)
        result = client.search(
            query=query,
            limit=limit,
            scrape_options={"formats": ["markdown"]},
        )
        web_results = getattr(result, "web", None)
        if web_results is None and isinstance(result, dict):
            web_results = result.get("web", [])
        web_results = web_results or []

        leads: list[DiscoveredLead] = []
        for item in web_results[:limit]:
            url = getattr(item, "url", None) or item.get("url")
            title = getattr(item, "title", None) or item.get("title") or url
            description = getattr(item, "description", None) or item.get("description")
            confidence = 0.65 if description else 0.55
            leads.append(
                DiscoveredLead(
                    company_name=title,
                    website=url,
                    why_match=[description] if description else [f"Matched Firecrawl search for: {query}"],
                    confidence=confidence,
                    source_references=[
                        SourceReference(
                            title=title,
                            url=url,
                            excerpt=description,
                        )
                    ]
                    if url
                    else [],
                )
            )

        self.logger.info(
            "lead_search_completed",
            extra={"query": query, "limit": limit, "result_count": len(leads)},
        )
        return leads

    def _search_from_inputs(
        self,
        seed_companies: list[LeadSeedInput],
        websites: list[str],
        limit: int,
    ) -> list[DiscoveredLead]:
        leads = [
            DiscoveredLead(
                company_name=seed.company_name,
                website=seed.website,
                industry=seed.industry,
                employee_estimate=seed.employee_estimate,
                location=seed.location,
                why_match=seed.notes or ["Provided directly in request payload."],
                confidence=0.45,
                source_references=[
                    SourceReference(title=seed.company_name, url=seed.website, excerpt="Seed input")
                ]
                if seed.website
                else [],
            )
            for seed in seed_companies
        ]

        for website in websites:
            leads.append(
                DiscoveredLead(
                    company_name=website,
                    website=website,
                    why_match=["Website provided directly for enrichment."],
                    confidence=0.35,
                    source_references=[SourceReference(title=website, url=website, excerpt="Direct website input")],
                )
            )

        unique_leads: list[DiscoveredLead] = []
        seen = set()
        for lead in leads:
            key = lead.website or lead.company_name.lower()
            if key in seen:
                continue
            seen.add(key)
            unique_leads.append(lead)

        self.logger.info(
            "lead_search_fallback_used",
            extra={"seed_count": len(seed_companies), "website_count": len(websites), "result_count": len(unique_leads[:limit])},
        )
        return unique_leads[:limit]
