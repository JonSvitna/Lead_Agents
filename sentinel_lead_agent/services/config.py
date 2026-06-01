import os

from pydantic import BaseModel, Field


class Settings(BaseModel):
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    firecrawl_api_key: str | None = None
    tavily_api_key: str | None = None
    apollo_api_key: str | None = None
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    enable_playwright: bool = False
    request_timeout_seconds: int = 45
    browser_timeout_ms: int = 30000
    max_page_characters: int = 12000

    @property
    def firecrawl_enabled(self) -> bool:
        return bool(self.firecrawl_api_key)

    @property
    def tavily_enabled(self) -> bool:
        return bool(self.tavily_api_key)

    @property
    def apollo_enabled(self) -> bool:
        return bool(self.apollo_api_key)

    @property
    def playwright_enabled(self) -> bool:
        return self.enable_playwright

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            firecrawl_api_key=os.getenv("FIRECRAWL_API_KEY"),
            tavily_api_key=os.getenv("TAVILY_API_KEY"),
            apollo_api_key=os.getenv("APOLLO_API_KEY"),
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8000")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            enable_playwright=os.getenv("ENABLE_PLAYWRIGHT", "false").lower() == "true",
            request_timeout_seconds=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "45")),
            browser_timeout_ms=int(os.getenv("BROWSER_TIMEOUT_MS", "30000")),
            max_page_characters=int(os.getenv("MAX_PAGE_CHARACTERS", "12000")),
        )