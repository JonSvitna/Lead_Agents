# Lead_Agents

Lead_Agents is a Python backend for AI-assisted lead discovery, website analysis, qualification, and outreach generation.

The project is built around a clean FastAPI service and a modular OpenAI Agents SDK workflow designed for compliance-focused B2B lead intelligence.

## What It Does

The platform can:

- Discover business leads from a search query or seeded company inputs
- Analyze company websites for government contracting and compliance signals
- Score companies against a practical qualification model
- Generate structured outreach content
- Return structured JSON for downstream workflows

## Architecture

The backend is organized under `sentinel_lead_agent/` with these main areas:

- `agents/` specialist agents for discovery, analysis, qualification, and outreach
- `tools/` reusable tool adapters for search, scraping, and scoring
- `prompts/` prompt files aligned with each agent's job
- `services/` orchestration, config, logging, prompt loading, and OpenAI runtime wiring
- `api/` FastAPI routes
- `models/` Pydantic request and response models

The implementation uses:

- Python
- FastAPI
- OpenAI Agents SDK
- Pydantic
- Async orchestration
- Firecrawl for search and scraping when configured
- Tavily as a lead-search fallback when Firecrawl is unavailable or out of credits
- Apollo organization search as an additional lead-search fallback
- Playwright fallback for website analysis
- Environment-variable based configuration
- Structured JSON logging
- CrewAI entrypoint with four visible stages: Discovery, Analyzer, Qualification, and Outreach

CrewAI canonical package layout for deployment:

- `src/lead_agents/main.py`
- `src/lead_agents/crew.py`
- `src/lead_agents/config/agents.yaml`
- `src/lead_agents/config/tasks.yaml`

## Key Endpoint

The main API endpoint is:

- `POST /api/v1/lead-intelligence`

It accepts a structured request with a search query and optional direct websites or seed companies, then returns discovered leads, website analysis, qualification output, and outreach content.

Health endpoint:

- `GET /api/v1/health`

## Installation

Install dependencies:

```bash
pip install -r sentinel_lead_agent/requirements.txt
```

If you plan to use Playwright fallback, install browser binaries as well:

```bash
playwright install
```

## Configuration

Copy the sample environment file and fill in your keys:

```bash
copy .env.example .env
```

Required for agent execution:

- `OPENAI_API_KEY`

Optional but recommended:

- `FIRECRAWL_API_KEY` for search and scrape support
- `TAVILY_API_KEY` for lead-search fallback support
- `APOLLO_API_KEY` for organization-search fallback support
- `ENABLE_PLAYWRIGHT=true` if you want Playwright website analysis fallback

Lead-search provider order:

- Firecrawl
- Tavily
- Apollo
- Seed companies or direct website inputs from request payload

## Running The API

From the repository root:

```bash
uvicorn sentinel_lead_agent.main:app --reload
```

Default local URL:

```text
http://127.0.0.1:8000
```

Swagger docs:

```text
http://127.0.0.1:8000/docs
```

## Local Testing Without CrewAI AMP

If you just want to validate the lead intelligence pipeline in your current environment,
you do not need the CrewAI deployment path or `uv.lock`.

Run the pipeline directly:

```bash
python -m sentinel_lead_agent.local_test --query "Maryland defense subcontractor MSP" --limit 3
```

This exercises the same discovery, analysis, qualification, and outreach service used by the API.

## Example Request

```json
{
	"query": "Maryland defense subcontractor MSP",
	"limit": 3,
	"websites": [],
	"seed_companies": []
}
```

## Example Response Shape

```json
{
	"query": "Maryland defense subcontractor MSP",
	"generated_at": "2026-06-01T00:00:00Z",
	"total_leads": 1,
	"leads": [
		{
			"lead": {
				"company_name": "Example Company",
				"website": "https://example.com",
				"industry": "Managed IT Services",
				"employee_estimate": "25-50",
				"location": "Maryland",
				"why_match": [
					"Matched search results with government-services language"
				],
				"confidence": 0.72,
				"source_references": [
					{
						"title": "Example Company",
						"url": "https://example.com",
						"excerpt": "Provides IT services to public-sector customers"
					}
				]
			},
			"website_analysis": {
				"company_summary": "Regional IT services provider with public-sector delivery focus.",
				"government_signals": [
					"Mentions public-sector and government clients"
				],
				"compliance_signals": [
					"References cybersecurity and risk management"
				],
				"service_offerings": [
					"Managed IT",
					"Cybersecurity support"
				],
				"likely_pain_points": [
					"Need to document security controls for regulated customers"
				],
				"recommended_contact_titles": [
					"CEO",
					"Director of Operations",
					"VP of Technology"
				],
				"confidence": 0.76,
				"analyzed_url": "https://example.com"
			},
			"qualification": {
				"lead_score": 8,
				"confidence": 0.78,
				"priority": "high",
				"fit_summary": "Strong fit due to public-sector signals and likely compliance pressure.",
				"strengths": [
					"Government-adjacent delivery",
					"Cybersecurity services footprint"
				],
				"risks": [
					"Employee count is inferred from limited evidence"
				],
				"likely_pain_points": [
					"CMMC or NIST readiness",
					"Security documentation gaps"
				],
				"best_contact_title": "CEO",
				"recommended_outreach_angle": "Offer practical help preparing for federal cybersecurity expectations.",
				"deterministic_scorecard": {
					"score": 8,
					"matched_signals": [
						"Government-adjacent services",
						"Compliance language"
					],
					"missed_signals": [],
					"rationale": [
						"Government contracting signals increase urgency."
					]
				}
			},
			"outreach": {
				"email_subject": "Quick question about compliance readiness",
				"email_body": "...",
				"linkedin_message": "...",
				"follow_up_message": "..."
			}
		}
	]
}
```

## Notes

- The service is intentionally bounded and avoids autonomous looping frameworks.
- If `FIRECRAWL_API_KEY` is not configured, lead discovery can still run from direct `seed_companies` or `websites` input.
- If neither Firecrawl nor Playwright is available, website analysis will fail with a clear runtime error.
- Python execution may need to be validated locally if Python is not available in the current terminal environment.
