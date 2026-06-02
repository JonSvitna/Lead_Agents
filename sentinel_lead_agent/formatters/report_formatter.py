from sentinel_lead_agent.models.lead_model import LeadIntelligenceRecord, LeadIntelligenceResponse


_DIVIDER = "─" * 62
_HEADER = "═" * 62


def format_response(response: LeadIntelligenceResponse) -> str:
    lines: list[str] = []
    lines.append(_HEADER)
    lines.append("  SENTINEL · CMMC 2.0 BUYER LEAD REPORT")
    lines.append(_HEADER)
    if response.query:
        lines.append(f"  Search  : {response.query}")
    lines.append(f"  Leads   : {response.total_leads} found")
    lines.append(f"  Run at  : {response.generated_at.strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("")

    for i, record in enumerate(response.leads, 1):
        lines.extend(_format_record(i, record))

    lines.append(_HEADER)
    lines.append(f"  End of report — {response.total_leads} lead(s) returned.")
    lines.append(_HEADER)
    return "\n".join(lines)


def _priority_badge(priority: str) -> str:
    badges = {"priority": "★ PRIORITY", "high": "▲ HIGH", "medium": "● MEDIUM", "low": "▽ LOW"}
    return badges.get(priority.lower(), priority.upper())


def _format_record(index: int, record: LeadIntelligenceRecord) -> list[str]:
    lead = record.lead
    qual = record.qualification
    analysis = record.website_analysis
    outreach = record.outreach

    lines: list[str] = []
    lines.append(_DIVIDER)
    lines.append(f"  LEAD {index} — {lead.company_name}")
    badge = _priority_badge(qual.priority.value)
    lines.append(f"  {badge}  |  Score {qual.lead_score}/10  |  Confidence {int(qual.confidence * 100)}%")
    lines.append("")

    # Company basics
    if lead.website:
        lines.append(f"  Website    : {lead.website}")
    if lead.location:
        lines.append(f"  Location   : {lead.location}")
    if lead.industry:
        lines.append(f"  Industry   : {lead.industry}")
    if lead.employee_estimate:
        lines.append(f"  Employees  : {lead.employee_estimate}")
    lines.append("")

    # Why this lead
    if lead.why_match:
        lines.append("  WHY THIS LEAD")
        for reason in lead.why_match:
            lines.append(f"    • {reason}")
        lines.append("")

    # Government / compliance signals from website analysis
    if analysis and analysis.government_signals:
        lines.append("  GOVERNMENT & COMPLIANCE SIGNALS")
        for sig in analysis.government_signals:
            lines.append(f"    • {sig}")
        lines.append("")

    if analysis and analysis.compliance_signals:
        lines.append("  COMPLIANCE INDICATORS")
        for sig in analysis.compliance_signals:
            lines.append(f"    • {sig}")
        lines.append("")

    # Qualification
    lines.append(f"  FIT SUMMARY")
    lines.append(f"    {qual.fit_summary}")
    lines.append("")

    if qual.strengths:
        lines.append("  STRENGTHS")
        for s in qual.strengths:
            lines.append(f"    + {s}")
        lines.append("")

    if qual.risks:
        lines.append("  RISKS")
        for r in qual.risks:
            lines.append(f"    ! {r}")
        lines.append("")

    if qual.likely_pain_points:
        lines.append("  PAIN POINTS")
        for p in qual.likely_pain_points:
            lines.append(f"    • {p}")
        lines.append("")

    lines.append(f"  Best Contact  : {qual.best_contact_title}")
    lines.append(f"  Outreach Angle: {qual.recommended_outreach_angle}")
    lines.append("")

    # Outreach content
    lines.append("  ── OUTREACH ─────────────────────────────────────────")
    lines.append(f"  Email Subject : {outreach.email_subject}")
    lines.append("")
    lines.append("  Email Body:")
    for body_line in outreach.email_body.splitlines():
        lines.append(f"    {body_line}")
    lines.append("")
    lines.append("  LinkedIn Message:")
    for msg_line in outreach.linkedin_message.splitlines():
        lines.append(f"    {msg_line}")
    lines.append("")

    return lines
