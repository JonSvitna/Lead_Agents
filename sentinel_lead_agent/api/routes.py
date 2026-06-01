from fastapi import APIRouter, HTTPException, Request

from sentinel_lead_agent.models.lead_model import LeadIntelligenceRequest, LeadIntelligenceResponse

router = APIRouter(prefix="/api/v1", tags=["lead-intelligence"])


@router.get("/health")
async def health(request: Request) -> dict[str, object]:
    settings = request.app.state.settings
    return {
        "status": "ok",
        "firecrawl_enabled": settings.firecrawl_enabled,
        "tavily_enabled": settings.tavily_enabled,
        "apollo_enabled": settings.apollo_enabled,
        "playwright_enabled": settings.playwright_enabled,
        "model": settings.openai_model,
    }


@router.post("/lead-intelligence", response_model=LeadIntelligenceResponse)
async def generate_lead_intelligence(
    payload: LeadIntelligenceRequest,
    request: Request,
) -> LeadIntelligenceResponse:
    service = request.app.state.lead_service

    try:
        return await service.generate_intelligence(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
