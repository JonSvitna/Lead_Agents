import asyncio
import json

from sentinel_lead_agent.models.lead_model import DiscoveredLead, LeadSeedInput, SourceReference
from sentinel_lead_agent.services.logging_service import get_logger

try:
    import httpx
except ImportError:  # pragma: no cover - depends on runtime environment
    httpx = None

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

        if query:
            firecrawl_results = await self._try_firecrawl(query, limit)
            if firecrawl_results:
                return firecrawl_results

            tavily_results = await self._try_tavily(query, limit)
            if tavily_results:
                return tavily_results

            apollo_results = await self._try_apollo(query, limit)
            if apollo_results:
                return apollo_results

        return self._search_from_inputs(seed_companies, websites, limit)

    async def _try_firecrawl(self, query: str, limit: int) -> list[DiscoveredLead]:
        if not (self.settings.firecrawl_enabled and Firecrawl is not None):
            return []

        try:
            return await asyncio.to_thread(self._search_with_firecrawl, query, limit)
        except Exception as exc:  # pragma: no cover - provider/runtime dependent
            self.logger.warning(
                "lead_search_provider_failed",
                extra={"provider": "firecrawl", "error": str(exc)},
            )
            return []

    async def _try_tavily(self, query: str, limit: int) -> list[DiscoveredLead]:
        if not (self.settings.tavily_enabled and httpx is not None):
            return []

        try:
            return await asyncio.to_thread(self._search_with_tavily, query, limit)
        except Exception as exc:  # pragma: no cover - provider/runtime dependent
            self.logger.warning(
                "lead_search_provider_failed",
                extra={"provider": "tavily", "error": str(exc)},
            )
            return []

    async def _try_apollo(self, query: str, limit: int) -> list[DiscoveredLead]:
        if not (self.settings.apollo_enabled and httpx is not None):
            return []

        try:
            return await asyncio.to_thread(self._search_with_apollo, query, limit)
        except Exception as exc:  # pragma: no cover - provider/runtime dependent
            self.logger.warning(
                "lead_search_provider_failed",
                extra={"provider": "apollo", "error": str(exc)},
            )
            return []

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

    def _search_with_tavily(self, query: str, limit: int) -> list[DiscoveredLead]:
        headers = {"Content-Type": "application/json"}
        payload = {
            "api_key": self.settings.tavily_api_key,
            "query": query,
            "max_results": limit,
            "search_depth": "advanced",
        }

        with httpx.Client(timeout=self.settings.request_timeout_seconds) as client:
            response = client.post("https://api.tavily.com/search", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        results = data.get("results", [])
        leads: list[DiscoveredLead] = []
        for item in results[:limit]:
            url = item.get("url")
            title = item.get("title") or url
            content = item.get("content")
            leads.append(
                DiscoveredLead(
                    company_name=title,
                    website=url,
                    why_match=[content] if content else [f"Matched Tavily search for: {query}"],
                    confidence=0.6,
                    source_references=[SourceReference(title=title or url or "unknown", url=url, excerpt=content)] if url else [],
                )
            )

        self.logger.info(
            "lead_search_completed",
            extra={"provider": "tavily", "query": query, "limit": limit, "result_count": len(leads)},
        )
        return leads

    def _search_with_apollo(self, query: str, limit: int) -> list[DiscoveredLead]:
        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "X-Api-Key": self.settings.apollo_api_key,
        }
        payload = {
            "q_organization_name": query,
            "page": 1,
            "per_page": limit,
        }

        with httpx.Client(timeout=self.settings.request_timeout_seconds) as client:
            response = client.post(
                "https://api.apollo.io/api/v1/mixed_companies/search",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        organizations = data.get("organizations", [])
        leads: list[DiscoveredLead] = []
        for org in organizations[:limit]:
            name = org.get("name") or "Unknown Organization"
            website = org.get("website_url")
            industry = org.get("industry")
            location_parts = [org.get("city"), org.get("state"), org.get("country")]
            location = ", ".join(part for part in location_parts if part)
            employee_count = org.get("estimated_num_employees")
            employee_estimate = str(employee_count) if employee_count is not None else None

            summary = {
                "keywords": org.get("keywords", []),
                "short_description": org.get("short_description"),
                "founded_year": org.get("founded_year"),
            }
            excerpt = json.dumps(summary)

            leads.append(
                DiscoveredLead(
                    company_name=name,
                    website=website,
                    industry=industry,
                    employee_estimate=employee_estimate,
                    location=location or None,
                    why_match=[f"Matched Apollo organization search for: {query}"],
                    confidence=0.6,
                    source_references=[SourceReference(title=name, url=website, excerpt=excerpt)] if website else [],
                )
            )

        self.logger.info(
            "lead_search_completed",
            extra={"provider": "apollo", "query": query, "limit": limit, "result_count": len(leads)},
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
