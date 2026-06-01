from pathlib import Path

from sentinel_lead_agent.models.lead_model import DiscoveredLead, ScoreBand, Scorecard, WebsiteAnalysis


class LeadScoringTool:
    def __init__(self, settings) -> None:
        self.settings = settings
        self.rules_path = Path(__file__).resolve().parents[1] / "prompts" / "scoring_rules.txt"

    def score_lead(self, lead: DiscoveredLead, analysis: WebsiteAnalysis | None) -> Scorecard:
        score = 4
        matched_signals: list[str] = []
        missed_signals: list[str] = []
        rationale: list[str] = []

        if analysis and analysis.government_signals:
            increment = min(3, len(analysis.government_signals))
            score += increment
            matched_signals.extend(analysis.government_signals)
            rationale.append("Government contracting signals increase urgency.")
        else:
            missed_signals.append("No clear government contracting evidence surfaced.")

        if analysis and analysis.compliance_signals:
            score += 2
            matched_signals.extend(analysis.compliance_signals)
            rationale.append("Compliance language suggests active pressure or readiness work.")
        else:
            missed_signals.append("No visible compliance language found.")

        target_regions = ["maryland", "virginia", "washington", "dc", "district of columbia"]
        if lead.location and any(region in lead.location.lower() for region in target_regions):
            score += 1
            rationale.append("Located in the primary target region.")
        else:
            missed_signals.append("Outside the core target region or location unknown.")

        if lead.employee_estimate and any(token in lead.employee_estimate.lower() for token in ["10", "25", "50", "100"]):
            score += 1
            rationale.append("Employee size appears close to the ideal SMB range.")

        if analysis and analysis.likely_pain_points:
            score += 1
            rationale.append("Website content suggests tangible compliance pain points.")

        if lead.employee_estimate and any(token in lead.employee_estimate.lower() for token in ["500", "1000", "enterprise"]):
            score -= 2
            missed_signals.append("Company may be too large for the target ICP.")

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
