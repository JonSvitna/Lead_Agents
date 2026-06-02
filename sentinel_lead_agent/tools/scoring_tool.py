from pathlib import Path

from sentinel_lead_agent.models.lead_model import DiscoveredLead, ScoreBand, Scorecard, WebsiteAnalysis

_COMPETITOR_TOKENS = [
    "c3pao", "rpo", "cmmc consultant", "cmmc consulting", "cmmc services",
    "cmmc partner", "cmmc accelerator", "cmmc readiness", "gap assessment",
    "readiness provider", "compliance-as-a-service", "managed compliance",
    "virtual ciso", "vciso", "mssp", "we help you achieve cmmc",
    "your cmmc partner", "cmmc audit",
]

_HARD_REJECT_TYPES = ["university", "government agency", "nonprofit", "c3pao", "rpo"]

_TARGET_REGIONS = ["maryland", "virginia", "washington", "dc", "district of columbia"]

_POSITIVE_INDUSTRIES = [
    "aerospace", "defense", "manufacturing", "engineering", "r&d", "research",
    "systems integrat", "federal contractor", "dod", "it integrat",
]


class LeadScoringTool:
    def __init__(self, settings) -> None:
        self.settings = settings
        self.rules_path = Path(__file__).resolve().parents[1] / "prompts" / "scoring_rules.txt"

    def score_lead(self, lead: DiscoveredLead, analysis: WebsiteAnalysis | None) -> Scorecard:
        score = 4  # neutral baseline
        matched_signals: list[str] = []
        missed_signals: list[str] = []
        rationale: list[str] = []

        # Build a single text blob for pattern matching
        evidence_parts = [
            lead.company_name,
            lead.website or "",
            lead.industry or "",
            lead.location or "",
            *(lead.why_match or []),
        ]
        if analysis:
            evidence_parts.extend(analysis.government_signals or [])
            evidence_parts.extend(analysis.compliance_signals or [])
            evidence_parts.extend(analysis.service_offerings or [])
            evidence_parts.extend(analysis.likely_pain_points or [])
        evidence = " ".join(evidence_parts).lower()

        # Hard-reject: competitor or provider profile
        if any(token in evidence for token in _COMPETITOR_TOKENS):
            return Scorecard(
                score=1,
                matched_signals=[],
                missed_signals=["Competitor or compliance-services provider — hard reject."],
                rationale=["Company appears to sell CMMC services, not buy them."],
            )

        # Hard-reject: non-business entity
        if any(token in evidence for token in _HARD_REJECT_TYPES):
            return Scorecard(
                score=1,
                matched_signals=[],
                missed_signals=["Non-buyer entity — university, agency, or nonprofit."],
                rationale=["Entity type is out of scope for CMMC software buyers."],
            )

        # Government contracting signals
        gov_keywords = ["sam.gov", "cage code", "uei", "gsa schedule", "idiq", "sbir", "sttr",
                        "prime contractor", "subcontractor", "federal award", "dod contract",
                        "department of defense", "army", "navy", "air force", "darpa", "dhs"]
        gov_hits = [kw for kw in gov_keywords if kw in evidence]
        if analysis and analysis.government_signals:
            increment = min(3, len(analysis.government_signals))
            score += increment
            matched_signals.extend(analysis.government_signals[:3])
            rationale.append("Government contracting signals indicate live DoD exposure.")
        elif gov_hits:
            score += 2
            matched_signals.extend(gov_hits[:3])
            rationale.append("Government contracting keywords found in discovery evidence.")
        else:
            missed_signals.append("No government contracting evidence found.")

        # DFARS / CMMC clause signals
        dfars_keywords = ["dfars 252.204-7012", "dfars 252.204-7021", "dfars", "252.204-7012"]
        if any(kw in evidence for kw in dfars_keywords):
            score += 2
            matched_signals.append("DFARS clause language detected.")
            rationale.append("DFARS clause language indicates direct CUI obligation.")

        # ITAR / EAR
        if any(kw in evidence for kw in ["itar", "ear ", "export controlled", "export-controlled"]):
            score += 2
            matched_signals.append("ITAR/EAR exposure detected.")
            rationale.append("Export-controlled work typically requires CMMC Level 2+.")

        # Explicit CMMC language
        cmmc_keywords = ["cmmc 2.0", "cmmc level 2", "cmmc level 3", "cmmc certification",
                         "cmmc in progress", "cmmc compliant", "cmmc assessment"]
        if any(kw in evidence for kw in cmmc_keywords):
            score += 2
            matched_signals.append("Explicit CMMC certification language found.")
            rationale.append("Company is actively referencing CMMC — strong buyer signal.")

        # NIST / compliance signals
        if analysis and analysis.compliance_signals:
            score += 2
            matched_signals.extend(analysis.compliance_signals[:2])
            rationale.append("Compliance indicators suggest active pressure or readiness effort.")
        elif any(kw in evidence for kw in ["nist 800-171", "ssp", "poa&m", "cui", "poam"]):
            score += 1
            matched_signals.append("NIST/CUI compliance language in evidence.")
            rationale.append("Compliance language signals buyer-side pressure.")
        else:
            missed_signals.append("No NIST 800-171 or CMMC compliance language found.")

        # Positive industry
        if lead.industry and any(token in lead.industry.lower() for token in _POSITIVE_INDUSTRIES):
            score += 1
            matched_signals.append(f"Industry: {lead.industry}")
            rationale.append("Industry sector aligns with typical CMMC buyer profile.")

        # Target region
        if lead.location and any(region in lead.location.lower() for region in _TARGET_REGIONS):
            score += 1
            rationale.append("Located in primary target region (MD/VA/DC).")
        else:
            missed_signals.append("Outside core target region or location unknown.")

        # Pain points visible
        if analysis and analysis.likely_pain_points:
            score += 1
            rationale.append("Website content surfaces tangible compliance pain points.")

        # Negative: large enterprise
        large_tokens = ["1,000 employees", "5,000 employees", "10,000", "enterprise", "fortune 500"]
        if any(token in evidence for token in large_tokens):
            score -= 2
            missed_signals.append("Company may be too large for the target SMB ICP.")

        # Negative: no defense signal at all
        defense_tokens = ["defense", "dod", "federal", "government", "military", "contractor"]
        if not any(token in evidence for token in defense_tokens):
            score -= 2
            missed_signals.append("No defense or federal delivery signal found in evidence.")

        final_score = max(1, min(10, score))
        return Scorecard(
            score=final_score,
            matched_signals=matched_signals,
            missed_signals=missed_signals,
            rationale=rationale,
        )

    def score_band(self, score: int) -> ScoreBand:
        if score >= 9:
            return ScoreBand.priority
        if score >= 7:
            return ScoreBand.high
        if score >= 4:
            return ScoreBand.medium
        return ScoreBand.low
