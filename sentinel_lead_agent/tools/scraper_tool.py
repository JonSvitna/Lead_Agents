import asyncio

from sentinel_lead_agent.models.lead_model import ScrapedWebsiteContent
from sentinel_lead_agent.services.logging_service import get_logger

try:
    from firecrawl import Firecrawl
except ImportError:  # pragma: no cover - depends on runtime environment
    Firecrawl = None

try:
    from playwright.async_api import async_playwright
except ImportError:  # pragma: no cover - depends on runtime environment
    async_playwright = None


class WebsiteScraperTool:
    def __init__(self, settings) -> None:
        self.settings = settings
        self.logger = get_logger(__name__)

    async def scrape_website(self, url: str) -> ScrapedWebsiteContent:
        if self.settings.firecrawl_enabled and Firecrawl is not None:
            return await asyncio.to_thread(self._scrape_with_firecrawl, url)

        if self.settings.playwright_enabled and async_playwright is not None:
            return await self._scrape_with_playwright(url)

        raise RuntimeError(
            "Website analysis requires either FIRECRAWL_API_KEY or ENABLE_PLAYWRIGHT=true with Playwright browsers installed."
        )

    def _scrape_with_firecrawl(self, url: str) -> ScrapedWebsiteContent:
        client = Firecrawl(api_key=self.settings.firecrawl_api_key)
        result = client.scrape(url, formats=["markdown", "html", "links"])
        data = getattr(result, "data", None)
        if data is None and isinstance(result, dict):
            data = result.get("data", result)

        metadata = getattr(data, "metadata", None) or data.get("metadata", {}) if isinstance(data, dict) else {}
        markdown = getattr(data, "markdown", None) if not isinstance(data, dict) else data.get("markdown")
        html = getattr(data, "html", None) if not isinstance(data, dict) else data.get("html")

        payload = ScrapedWebsiteContent(
            url=url,
            source="firecrawl",
            title=metadata.get("title"),
            description=metadata.get("description"),
            markdown=markdown,
            html=html,
        )
        self.logger.info("website_scraped", extra={"url": url, "source": payload.source})
        return payload

    async def _scrape_with_playwright(self, url: str) -> ScrapedWebsiteContent:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(url, wait_until="networkidle", timeout=self.settings.browser_timeout_ms)
                title = await page.title()
                description = None
                description_tag = await page.query_selector("meta[name='description']")
                if description_tag is not None:
                    description = await description_tag.get_attribute("content")
                body = await page.locator("body").inner_text()
                payload = ScrapedWebsiteContent(
                    url=url,
                    source="playwright",
                    title=title,
                    description=description,
                    body_text=body[: self.settings.max_page_characters],
                )
                self.logger.info("website_scraped", extra={"url": url, "source": payload.source})
                return payload
            finally:
                await browser.close()
