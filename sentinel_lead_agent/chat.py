"""Interactive CLI for Sentinel Lead Engine.

Collects an ICP profile through natural conversation, runs the lead search
pipeline, and prints a formatted plain-text report. No JSON is shown to the user.

Usage:
    python -m sentinel_lead_agent.chat
    # or, after pip install:
    sentinel-chat
"""
from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

from dotenv import load_dotenv
from openai import AsyncOpenAI

from sentinel_lead_agent.formatters.report_formatter import format_response
from sentinel_lead_agent.models.lead_model import LeadIntelligenceRequest
from sentinel_lead_agent.services.config import Settings
from sentinel_lead_agent.services.lead_intelligence_service import LeadIntelligenceService

load_dotenv()

# ─── System prompt for the ICP collection conversation ────────────────────────

_CHAT_SYSTEM = """\
You are Sentinel, an AI lead engine assistant that finds CMMC 2.0 compliance
software buyers for a B2B sales team.

Your job is to collect a search profile from the user through natural
conversation, confirm the parameters, then trigger the search.

TARGET BUYER ICP (always keep this in mind):
  • Small to mid-sized DoD prime contractors, subcontractors, defense suppliers,
    aerospace companies, manufacturers, engineering firms, and R&D shops.
  • Organizations that handle Controlled Unclassified Information (CUI) and must
    achieve or maintain CMMC 2.0 Level 2 or Level 3 compliance for their contracts.
  • Visible signals: SAM.gov registration, CAGE codes, DFARS 252.204-7012 clauses,
    ITAR/EAR-controlled products, federal prime or sub-contract work.
  • Default geography: Maryland, Virginia, Washington DC area — unless the user
    specifies otherwise.

NEVER target:
  • CMMC consultants, C3PAOs, RPOs, MSSPs, or companies that sell compliance
    services (these are competitors, not buyers).
  • Large enterprises (>1,000 employees) unless the user has a specific reason.
  • Universities, government agencies, nonprofits.

CONVERSATION FLOW:
  1. Welcome the user and ask about their geographic focus for this search.
  2. Ask about industry or company type (e.g. defense manufacturing, aerospace,
     IT services for DoD, engineering).
  3. Ask about company size if not obvious from context.
  4. Ask how many leads they want (default 5, max 20).
  5. Optionally ask if they want to exclude anything or include specific signals.
  6. Summarize the confirmed parameters clearly in plain text.
  7. Ask: "Ready to search? (yes/no)"
  8. When the user confirms, call the `start_lead_search` function immediately.

RULES:
  • Ask ONE or TWO questions per turn — never dump a long form.
  • Propose sensible defaults when the user is vague; label them as assumptions.
  • Keep replies short and direct.
  • Do not mention JSON, APIs, or technical internals.
  • Do not search or invent leads yourself — use the function call.
"""

# ─── Function schema for parameter extraction ─────────────────────────────────

_SEARCH_FUNCTION: dict[str, Any] = {
    "name": "start_lead_search",
    "description": (
        "Called exactly once when the user has confirmed all ICP parameters "
        "and wants to start the lead search. Extract every confirmed field."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Primary search query summarising the ICP.",
            },
            "location_text": {
                "type": "string",
                "description": "Free-form location (e.g. 'Maryland, Virginia, DC').",
            },
            "city": {"type": "string"},
            "state": {"type": "string"},
            "region": {"type": "string"},
            "zip_code": {"type": "string"},
            "radius_miles": {"type": "integer"},
            "employee_min": {"type": "integer"},
            "employee_max": {"type": "integer"},
            "include_company_types": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Company types to include (e.g. manufacturer, contractor).",
            },
            "exclude_company_types": {
                "type": "array",
                "items": {"type": "string"},
            },
            "search_terms": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Keyword terms to prioritise in search.",
            },
            "must_include_terms": {
                "type": "array",
                "items": {"type": "string"},
            },
            "exclude_terms": {
                "type": "array",
                "items": {"type": "string"},
            },
            "limit": {
                "type": "integer",
                "description": "Number of leads to return (1-20). Default 5.",
            },
        },
        "required": ["query", "limit"],
    },
}


# ─── Chat engine ──────────────────────────────────────────────────────────────

class SentinelChat:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        self.messages: list[dict[str, Any]] = [
            {"role": "system", "content": _CHAT_SYSTEM}
        ]
        self.lead_service = LeadIntelligenceService(settings)

    async def _send(self, user_input: str) -> tuple[str | None, dict[str, Any] | None]:
        """Send a user message and return (reply_text, function_call_args or None)."""
        self.messages.append({"role": "user", "content": user_input})

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            tools=[{"type": "function", "function": _SEARCH_FUNCTION}],
            tool_choice="auto",
        )

        choice = response.choices[0]
        msg = choice.message

        # Check for a tool call
        if msg.tool_calls:
            tool_call = msg.tool_calls[0]
            args = json.loads(tool_call.function.arguments)
            # Append the assistant message so history is coherent
            self.messages.append(msg.model_dump(exclude_unset=True))
            return None, args

        reply = msg.content or ""
        self.messages.append({"role": "assistant", "content": reply})
        return reply, None

    async def _run_search(self, params: dict[str, Any]) -> str:
        payload = LeadIntelligenceRequest(
            query=params.get("query"),
            limit=min(int(params.get("limit", 5)), 20),
            location_text=params.get("location_text"),
            city=params.get("city"),
            state=params.get("state"),
            region=params.get("region"),
            zip_code=params.get("zip_code"),
            radius_miles=params.get("radius_miles"),
            employee_min=params.get("employee_min"),
            employee_max=params.get("employee_max"),
            include_company_types=params.get("include_company_types") or [],
            exclude_company_types=params.get("exclude_company_types") or [],
            search_terms=params.get("search_terms") or [],
            must_include_terms=params.get("must_include_terms") or [],
            exclude_terms=params.get("exclude_terms") or [],
        )
        response = await self.lead_service.generate_intelligence(payload)
        return format_response(response)

    async def run(self) -> None:
        _banner()

        # Kick off the conversation
        reply, _ = await self._send(
            "Hello, I'd like to find CMMC 2.0 compliance software buyers."
        )
        if reply:
            _print_agent(reply)

        while True:
            try:
                user_input = _prompt()
            except (KeyboardInterrupt, EOFError):
                print("\n\nSession ended.")
                break

            if not user_input.strip():
                continue

            if user_input.strip().lower() in {"exit", "quit", "q"}:
                print("\nSession ended.")
                break

            reply, search_params = await self._send(user_input)

            if search_params is not None:
                _print_agent(
                    "Parameters confirmed. Running lead search now — this may take a minute..."
                )
                try:
                    report = await self._run_search(search_params)
                    print()
                    print(report)
                except ValueError as exc:
                    _print_agent(f"Search returned no results: {exc}")
                    _print_agent(
                        "Try broadening the geography, removing size filters, "
                        "or adding more keyword hints. Want to adjust the search?"
                    )
                    # Let the user continue the conversation to refine
                    continue
                except RuntimeError as exc:
                    _print_agent(f"Search failed: {exc}")
                break

            if reply:
                _print_agent(reply)


# ─── UI helpers ───────────────────────────────────────────────────────────────

def _banner() -> None:
    print()
    print("═" * 62)
    print("  SENTINEL LEAD ENGINE  —  CMMC 2.0 Buyer Discovery")
    print("═" * 62)
    print("  Type your answers in plain English. Type 'exit' to quit.")
    print("═" * 62)
    print()


def _print_agent(text: str) -> None:
    print(f"\n  Sentinel: {text}\n")


def _prompt() -> str:
    try:
        return input("  You: ").strip()
    except EOFError:
        return "exit"


# ─── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    settings = Settings.from_env()
    if not settings.openai_api_key:
        print("Error: OPENAI_API_KEY is not set. Add it to your .env file.")
        sys.exit(1)
    asyncio.run(SentinelChat(settings).run())


if __name__ == "__main__":
    main()
