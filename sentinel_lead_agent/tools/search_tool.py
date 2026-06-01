import asyncio
import json
import re
from dataclasses import dataclass

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


@dataclass
class SearchIntent:
    query: str
    search_terms: list[str]
    location_text: str | None
    zip_code: str | None
    city: str | None
    state: str | None
    region: str | None
    radius_miles: int | None


class LeadSearchTool:
    def __init__(self, settings) -> None:
        self.settings = settings
        self.logger = get_logger(__name__)

    async def search_businesses(
        self,
        query: str | None,
        limit: int,
        search_terms: list[str] | None = None,
        location_text: str | None = None,
        zip_code: str | None = None,
        city: str | None = None,
        state: str | None = None,
        region: str | None = None,
        radius_miles: int | None = None,
        seed_companies: list[LeadSeedInput] | None = None,
        websites: list[str] | None = None,
    ) -> list[DiscoveredLead]:
        seed_companies = seed_companies or []
        websites = websites or []

        intent = self._build_search_intent(
            query=query,
            search_terms=search_terms,
            location_text=location_text,
            zip_code=zip_code,
            city=city,
            state=state,
            region=region,
            radius_miles=radius_miles,
        )

        self.logger.info(
            "lead_search_intent_parsed",
            extra={
                "query": intent.query,
                "search_terms": intent.search_terms,
                "location_text": intent.location_text,
                "zip_code": intent.zip_code,
                "city": intent.city,
                "state": intent.state,
                "region": intent.region,
                "radius_miles": intent.radius_miles,
            },
        )

        if intent.query:
            firecrawl_results = await self._try_firecrawl(intent, limit)
            if firecrawl_results:
                return firecrawl_results

            tavily_results = await self._try_tavily(intent, limit)
            if tavily_results:
                return tavily_results

            apollo_results = await self._try_apollo(intent, limit)
            if apollo_results:
                return apollo_results

        return self._search_from_inputs(seed_companies, websites, limit)

    async def _try_firecrawl(self, intent: SearchIntent, limit: int) -> list[DiscoveredLead]:
        if not (self.settings.firecrawl_enabled and Firecrawl is not None):
            return []

        try:
            return await asyncio.to_thread(self._search_with_firecrawl, intent, limit)
        except Exception as exc:  # pragma: no cover - provider/runtime dependent
            self.logger.warning(
                "lead_search_provider_failed",
                extra={"provider": "firecrawl", "error": str(exc)},
            )
            return []

    async def _try_tavily(self, intent: SearchIntent, limit: int) -> list[DiscoveredLead]:
        if not (self.settings.tavily_enabled and httpx is not None):
            return []

        try:
            return await asyncio.to_thread(self._search_with_tavily, intent, limit)
        except Exception as exc:  # pragma: no cover - provider/runtime dependent
            self.logger.warning(
                "lead_search_provider_failed",
                extra={"provider": "tavily", "error": str(exc)},
            )
            return []

    async def _try_apollo(self, intent: SearchIntent, limit: int) -> list[DiscoveredLead]:
        if not (self.settings.apollo_enabled and httpx is not None):
            return []

        try:
            return await asyncio.to_thread(self._search_with_apollo, intent, limit)
        except Exception as exc:  # pragma: no cover - provider/runtime dependent
            self.logger.warning(
                "lead_search_provider_failed",
                extra={"provider": "apollo", "error": str(exc)},
            )
            return []

    def _search_with_firecrawl(self, intent: SearchIntent, limit: int) -> list[DiscoveredLead]:
        provider_query = self._build_provider_query(intent)
        client = Firecrawl(api_key=self.settings.firecrawl_api_key)
        result = client.search(
            query=provider_query,
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
                    why_match=[description] if description else [f"Matched Firecrawl search for: {provider_query}"],
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
            extra={"provider": "firecrawl", "query": provider_query, "limit": limit, "result_count": len(leads)},
        )
        return self._rank_and_trim(leads, intent, limit)

    def _search_with_tavily(self, intent: SearchIntent, limit: int) -> list[DiscoveredLead]:
        provider_query = self._build_provider_query(intent)
        headers = {"Content-Type": "application/json"}
        payload = {
            "api_key": self.settings.tavily_api_key,
            "query": provider_query,
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
                    why_match=[content] if content else [f"Matched Tavily search for: {provider_query}"],
                    confidence=0.6,
                    source_references=[SourceReference(title=title or url or "unknown", url=url, excerpt=content)] if url else [],
                )
            )

        self.logger.info(
            "lead_search_completed",
            extra={"provider": "tavily", "query": provider_query, "limit": limit, "result_count": len(leads)},
        )
        return self._rank_and_trim(leads, intent, limit)

    def _search_with_apollo(self, intent: SearchIntent, limit: int) -> list[DiscoveredLead]:
        provider_query = self._build_provider_query(intent)
        apollo_org_query = self._build_apollo_query(intent)
        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "X-Api-Key": self.settings.apollo_api_key,
        }
        payload = {
            "q_organization_name": apollo_org_query,
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
                    why_match=[f"Matched Apollo organization search for: {apollo_org_query}"],
                    confidence=0.6,
                    source_references=[SourceReference(title=name, url=website, excerpt=excerpt)] if website else [],
                )
            )

        self.logger.info(
            "lead_search_completed",
            extra={"provider": "apollo", "query": provider_query, "limit": limit, "result_count": len(leads)},
        )
        return self._rank_and_trim(leads, intent, limit)

    def _build_search_intent(
        self,
        query: str | None,
        search_terms: list[str] | None,
        location_text: str | None,
        zip_code: str | None,
        city: str | None,
        state: str | None,
        region: str | None,
        radius_miles: int | None,
    ) -> SearchIntent:
        normalized_query = (query or "").strip()
        normalized_terms = [term.strip() for term in (search_terms or []) if term and term.strip()]

        extracted_zip = zip_code or self._extract_zip_code(normalized_query)
        extracted_radius = radius_miles or self._extract_radius_miles(normalized_query)
        extracted_location = location_text or self._extract_location_text(normalized_query)

        effective_location = extracted_location or self._compose_location_text(extracted_zip, city, state, region)

        if not normalized_terms:
            normalized_terms = self._extract_search_terms(normalized_query)

        effective_query = normalized_query or " ".join(normalized_terms)
        if not effective_query and effective_location:
            effective_query = effective_location

        return SearchIntent(
            query=effective_query,
            search_terms=normalized_terms,
            location_text=effective_location,
            zip_code=extracted_zip,
            city=city,
            state=state,
            region=region,
            radius_miles=extracted_radius,
        )

    def _build_provider_query(self, intent: SearchIntent) -> str:
        parts: list[str] = []
        if intent.search_terms:
            parts.append(" ".join(intent.search_terms))
        elif intent.query:
            parts.append(intent.query)

        if intent.location_text:
            parts.append(f"near {intent.location_text}")
        elif intent.zip_code:
            parts.append(f"near {intent.zip_code}")

        if intent.radius_miles:
            parts.append(f"within {intent.radius_miles} miles")

        return " ".join(part.strip() for part in parts if part).strip()

    def _build_apollo_query(self, intent: SearchIntent) -> str:
        terms = intent.search_terms[:4] if intent.search_terms else []
        location_hint = intent.city or intent.state or intent.region or intent.zip_code
        query_parts = terms or ([intent.query] if intent.query else [])
        if location_hint:
            query_parts.append(location_hint)
        return " ".join(query_parts).strip() or intent.query

    def _extract_zip_code(self, query: str) -> str | None:
        match = re.search(r"\b(\d{5})(?:-\d{4})?\b", query)
        return match.group(1) if match else None

    def _extract_radius_miles(self, query: str) -> int | None:
        match = re.search(r"\bwithin\s+(\d{1,3})\s*miles?\b", query, flags=re.IGNORECASE)
        if not match:
            return None
        try:
            return int(match.group(1))
        except ValueError:
            return None

    def _extract_location_text(self, query: str) -> str | None:
        match = re.search(
            r"\b(?:near|in|around)\s+([A-Za-z0-9\s,.-]+?)(?:\s+within\s+\d{1,3}\s*miles?)?$",
            query,
            flags=re.IGNORECASE,
        )
        if not match:
            return None
        location = match.group(1).strip(" ,.-")
        return location or None

    def _extract_search_terms(self, query: str) -> list[str]:
        if not query:
            return []

        cleaned = re.sub(r"\bwithin\s+\d{1,3}\s*miles?\b", "", query, flags=re.IGNORECASE)
        cleaned = re.sub(r"\b(?:near|in|around)\s+[A-Za-z0-9\s,.-]+$", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\b\d{5}(?:-\d{4})?\b", "", cleaned)
        terms = [part for part in re.split(r"[^A-Za-z0-9+#]+", cleaned) if part]
        return terms[:8]

    def _compose_location_text(
        self,
        zip_code: str | None,
        city: str | None,
        state: str | None,
        region: str | None,
    ) -> str | None:
        parts = [city, state, region, zip_code]
        location = ", ".join(part.strip() for part in parts if part and part.strip())
        return location or None

    def _rank_and_trim(self, leads: list[DiscoveredLead], intent: SearchIntent, limit: int) -> list[DiscoveredLead]:
        if not leads:
            return []

        lowered_terms = [term.lower() for term in intent.search_terms]
        location_tokens = [
            token.lower()
            for token in [intent.location_text, intent.zip_code, intent.city, intent.state, intent.region]
            if token
        ]

        def score(lead: DiscoveredLead) -> float:
            text_parts = [lead.company_name, lead.location or "", lead.industry or ""]
            text_parts.extend(lead.why_match)
            full_text = " ".join(part for part in text_parts if part).lower()

            term_hits = sum(1 for term in lowered_terms if term in full_text)
            location_hits = sum(1 for token in location_tokens if token in full_text)
            return lead.confidence + (0.08 * term_hits) + (0.12 * location_hits)

        ranked = sorted(leads, key=score, reverse=True)
        return ranked[:limit]

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
