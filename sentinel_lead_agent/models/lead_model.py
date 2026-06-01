from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class SourceReference(BaseModel):
    title: str = Field(description="Human-readable title for the source.")
    url: str = Field(description="Source URL.")
    excerpt: str | None = Field(default=None, description="Relevant summary or excerpt.")


class LeadSeedInput(BaseModel):
    company_name: str = Field(description="Known company name to enrich.")
    website: str | None = Field(default=None, description="Known company website.")
    industry: str | None = Field(default=None, description="Known industry.")
    location: str | None = Field(default=None, description="Known location.")
    employee_estimate: str | None = Field(default=None, description="Known employee estimate.")
    notes: list[str] = Field(default_factory=list, description="User-provided discovery hints.")


class DiscoveredLead(BaseModel):
    company_name: str
    website: str | None = None
    industry: str | None = None
    employee_estimate: str | None = None
    location: str | None = None
    why_match: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    source_references: list[SourceReference] = Field(default_factory=list)


class ScrapedWebsiteContent(BaseModel):
    url: str
    source: str
    title: str | None = None
    description: str | None = None
    markdown: str | None = None
    html: str | None = None
    body_text: str | None = None
    screenshot_url: str | None = None


class WebsiteAnalysis(BaseModel):
    company_summary: str
    government_signals: list[str] = Field(default_factory=list)
    compliance_signals: list[str] = Field(default_factory=list)
    service_offerings: list[str] = Field(default_factory=list)
    likely_pain_points: list[str] = Field(default_factory=list)
    recommended_contact_titles: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    analyzed_url: str | None = None


class ScoreBand(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    priority = "priority"


class Scorecard(BaseModel):
    score: int = Field(ge=1, le=10)
    matched_signals: list[str] = Field(default_factory=list)
    missed_signals: list[str] = Field(default_factory=list)
    rationale: list[str] = Field(default_factory=list)


class QualificationResult(BaseModel):
    lead_score: int = Field(ge=1, le=10)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    priority: ScoreBand
    fit_summary: str
    strengths: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    likely_pain_points: list[str] = Field(default_factory=list)
    best_contact_title: str
    recommended_outreach_angle: str
    deterministic_scorecard: Scorecard


class OutreachContent(BaseModel):
    email_subject: str
    email_body: str
    linkedin_message: str
    follow_up_message: str


class LeadIntelligenceRecord(BaseModel):
    lead: DiscoveredLead
    website_analysis: WebsiteAnalysis | None = None
    qualification: QualificationResult
    outreach: OutreachContent


class DiscoveryAgentOutput(BaseModel):
    leads: list[DiscoveredLead] = Field(default_factory=list)


class WebsiteAnalysisAgentOutput(BaseModel):
    analysis: WebsiteAnalysis


class QualificationAgentOutput(BaseModel):
    qualification: QualificationResult


class OutreachAgentOutput(BaseModel):
    outreach: OutreachContent


class LeadIntelligenceRequest(BaseModel):
    query: str | None = Field(default=None, description="Search query for new leads.")
    limit: int = Field(default=5, ge=1, le=20)
    search_terms: list[str] = Field(
        default_factory=list,
        description="Optional explicit keywords to prioritize during discovery.",
    )
    location_text: str | None = Field(
        default=None,
        description="Optional free-form location filter (for example: 'near Baltimore, MD').",
    )
    zip_code: str | None = Field(default=None, description="Optional US ZIP code filter.")
    city: str | None = Field(default=None, description="Optional city filter.")
    state: str | None = Field(default=None, description="Optional state or region code filter.")
    region: str | None = Field(default=None, description="Optional broader region filter.")
    radius_miles: int | None = Field(default=None, ge=1, le=250, description="Optional distance radius in miles.")
    must_include_terms: list[str] = Field(
        default_factory=list,
        description="Optional terms that must appear in candidate evidence.",
    )
    exclude_terms: list[str] = Field(
        default_factory=list,
        description="Optional terms that cause candidates to be excluded.",
    )
    include_company_types: list[str] = Field(
        default_factory=list,
        description="Optional company type hints to include (for example MSP, manufacturer).",
    )
    exclude_company_types: list[str] = Field(
        default_factory=list,
        description="Optional company type hints to exclude (for example university, agency).",
    )
    employee_min: int | None = Field(default=None, ge=1, description="Optional minimum employee estimate.")
    employee_max: int | None = Field(default=None, ge=1, description="Optional maximum employee estimate.")
    websites: list[str] = Field(default_factory=list, description="Websites to analyze directly.")
    seed_companies: list[LeadSeedInput] = Field(
        default_factory=list,
        description="Known companies to enrich when external search is unavailable or when the user wants targeted analysis.",
    )

    def has_structured_search_intent(self) -> bool:
        return any(
            [
                bool(self.search_terms),
                self.location_text is not None,
                self.zip_code is not None,
                self.city is not None,
                self.state is not None,
                self.region is not None,
                self.radius_miles is not None,
                bool(self.must_include_terms),
                bool(self.exclude_terms),
                bool(self.include_company_types),
                bool(self.exclude_company_types),
                self.employee_min is not None,
                self.employee_max is not None,
            ]
        )


class LeadIntelligenceResponse(BaseModel):
    query: str | None
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_leads: int
    leads: list[LeadIntelligenceRecord]
