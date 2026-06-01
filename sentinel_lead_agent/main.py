import uvicorn
from fastapi import FastAPI
from dotenv import load_dotenv

from sentinel_lead_agent.api.routes import router
from sentinel_lead_agent.services.config import Settings
from sentinel_lead_agent.services.lead_intelligence_service import LeadIntelligenceService
from sentinel_lead_agent.services.logging_service import configure_logging, get_logger


load_dotenv()


def create_app() -> FastAPI:
    settings = Settings.from_env()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="Sentinel Lead Intelligence Engine",
        version="0.1.0",
        description="AI-powered lead discovery, website analysis, qualification, and outreach generation.",
    )
    app.state.settings = settings
    app.state.lead_service = LeadIntelligenceService(settings)
    app.include_router(router)

    logger = get_logger(__name__)
    logger.info(
        "application_started",
        extra={
            "service": "sentinel_lead_agent",
            "firecrawl_enabled": settings.firecrawl_enabled,
            "playwright_enabled": settings.playwright_enabled,
            "model": settings.openai_model,
        },
    )
    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(app, host=app.state.settings.host, port=app.state.settings.port)
