from __future__ import annotations

from typing import Any

from app.finance import analyze_investment, recommendation_from_metrics
from app.schemas import AnalysisRequest


def _risk_level_score(level: str) -> int:
    return {"low": 1, "medium": 2, "high": 3}.get(level.lower(), 2)


def _risk_label(score: int) -> str:
    if score >= 3:
        return "high"
    if score == 2:
        return "medium"
    return "low"


def build_risks(
    metrics: dict[str, Any],
    market_context: dict[str, Any],
    policy_context: dict[str, Any],
    missing_flags: list[str],
) -> list[dict[str, str]]:
    risks: list[dict[str, str]] = []

    if metrics["annual_cash_flow"] < 0:
        risks.append(
            {
                "level": "high" if metrics["annual_cash_flow"] < -3600 else "medium",
                "title": "Negative Cash Flow",
                "detail": "The base case produces negative annual cash flow after debt service.",
            }
        )
    if metrics["dscr"] < 1.2:
        risks.append(
            {
                "level": "high" if metrics["dscr"] < 1.0 else "medium",
                "title": "Debt Coverage Pressure",
                "detail": "NOI is close to or below the annual debt service threshold.",
            }
        )
    if metrics["break_even_monthly_rent"] > metrics["monthly_rent"] * 1.15:
        risks.append(
            {
                "level": "medium",
                "title": "Break-Even Rent Gap",
                "detail": "The break-even rent is materially above the expected rent assumption.",
            }
        )
    if _risk_level_score(policy_context.get("risk_level", "medium")) >= 3:
        risks.append(
            {
                "level": "high",
                "title": "Policy Restriction Risk",
                "detail": policy_context.get("rental_restriction_summary", "Local rules need careful review."),
            }
        )
    if missing_flags:
        risks.append(
            {
                "level": "medium",
                "title": "Missing Data",
                "detail": "Some market or policy data is generic and should be verified before purchase.",
            }
        )
    if market_context.get("insurance_risk_note"):
        risks.append(
            {
                "level": market_context.get("insurance_risk_level", "medium"),
                "title": "Insurance and Local Hazard Risk",
                "detail": market_context["insurance_risk_note"],
            }
        )

    return risks


def build_opportunities(metrics: dict[str, Any], market_context: dict[str, Any]) -> list[dict[str, str]]:
    opportunities: list[dict[str, str]] = []

    if metrics["annual_cash_flow"] > 0:
        opportunities.append(
            {
                "title": "Positive Base Cash Flow",
                "detail": "The property produces positive projected annual cash flow in the base case.",
            }
        )
    if metrics["dscr"] >= 1.2:
        opportunities.append(
            {
                "title": "Healthy Debt Coverage",
                "detail": "DSCR is at or above the 1.20 investment threshold.",
            }
        )
    if metrics["irr_5_year"] is not None and metrics["irr_5_year"] >= 0.08:
        opportunities.append(
            {
                "title": "Attractive Five-Year IRR",
                "detail": "The five-year projected IRR meets the target threshold.",
            }
        )
    if market_context.get("rent_trend"):
        opportunities.append(
            {
                "title": "Market Rent Signal",
                "detail": market_context["rent_trend"],
            }
        )
    if market_context.get("demand_driver"):
        opportunities.append(
            {
                "title": "Demand Driver",
                "detail": market_context["demand_driver"],
            }
        )

    return opportunities


def build_assumption_conflicts(
    assumptions: dict[str, Any],
    declared_facts: dict[str, Any],
) -> list[dict[str, str]]:
    """Compare the user's assumptions against limits declared in policy notes.

    A note can state machine-readable facts such as `rent_growth_cap_percent: 0`.
    When an assumption exceeds a legal ceiling, the projection is not achievable
    and the investor needs to know before reading the IRR.
    """
    conflicts: list[dict[str, str]] = []

    cap_entry = declared_facts.get("rent_growth_cap_percent")
    if cap_entry and isinstance(cap_entry.get("value"), (int, float)):
        cap = float(cap_entry["value"])
        entered = float(assumptions.get("annual_rent_growth_percent", 0))
        if entered > cap:
            conflicts.append(
                {
                    "level": "high",
                    "title": "Rent Growth Exceeds the Local Legal Cap",
                    "detail": (
                        f"The assumptions use {entered:g}% annual rent growth, but the policy note "
                        f"for this location records a cap of {cap:g}%. Every projection, IRR, and "
                        f"equity multiple above assumes growth the local rules do not allow. "
                        f"Source: {cap_entry['source_document']}."
                    ),
                }
            )

    str_entry = declared_facts.get("short_term_rental_allowed")
    if str_entry and str_entry.get("value") is False:
        conflicts.append(
            {
                "level": "medium",
                "title": "Short-Term Rental Income Is Not Available Here",
                "detail": (
                    "The policy note records that short-term rental use is not available to an "
                    "investor at this location, so the rent assumption must be supported by "
                    f"long-term lease comps. Source: {str_entry['source_document']}."
                ),
            }
        )

    return conflicts


def build_research_request(
    request: AnalysisRequest,
    knowledge_bank_context: dict[str, Any],
) -> dict[str, Any]:
    """Give the user a ready-to-paste command for the property-policy-research Skill.

    The app already has the address; the only reason a user would have to retype
    it is if we made them. The Skill itself cannot run inside this deterministic,
    offline FastAPI process (it needs an LLM agent loop with live web search), so
    the best the app can do is remove the busywork of composing the request.
    """
    prompt = (
        f"Run policy diligence on {request.address}, {request.city}, "
        f"{request.state.upper()} {request.zip_code}."
    )
    documents = knowledge_bank_context.get("documents", [])
    if not documents:
        status = "missing"
    elif any(document.get("is_stale") for document in documents):
        status = "stale"
    else:
        status = "current"

    return {"prompt": prompt, "status": status}


def build_report(
    request: AnalysisRequest,
    market_context: dict[str, Any],
    policy_context: dict[str, Any],
    knowledge_bank_context: dict[str, Any],
    location_check: dict[str, Any] | None = None,
) -> dict[str, Any]:
    assumptions = request.model_dump()
    metrics = analyze_investment(assumptions)
    location_check = location_check or {"status": "unverified", "warnings": [], "unverified": []}
    location_mismatch = location_check.get("status") == "warning"

    # Findings researched by the property-policy-research Skill sit alongside the
    # built-in sample records and can raise the policy risk on their own.
    researched_flags = knowledge_bank_context.get("researched_flags", [])
    if researched_flags:
        policy_context = dict(policy_context)
        # Placeholder flags that only say "add notes to the knowledge bank" are
        # obsolete once researched notes are actually driving the report.
        kept = [
            flag
            for flag in policy_context.get("restriction_flags", [])
            if not flag.get("needs_knowledge_bank")
        ]
        existing_titles = {flag["title"] for flag in kept}
        policy_context["restriction_flags"] = kept + [
            flag for flag in researched_flags if flag["title"] not in existing_titles
        ]
        if policy_context.get("match_level") == "national":
            policy_context["missing_data_flags"] = [
                "No built-in policy record exists for this ZIP or state. The policy findings "
                "below come from researched knowledge-bank notes instead. Check the source "
                "links and the research date inside each note before relying on them."
            ]

    policy_risk_level = policy_context.get("risk_level", "medium")
    if any(flag["level"] == "high" for flag in researched_flags):
        policy_risk_level = "high"
        policy_context["risk_level"] = "high"

    missing_flags = []
    missing_flags.extend(market_context.get("missing_data_flags", []))
    missing_flags.extend(policy_context.get("missing_data_flags", []))

    assumption_conflicts = build_assumption_conflicts(
        assumptions,
        knowledge_bank_context.get("declared_facts", {}),
    )

    recommendation = recommendation_from_metrics(
        metrics,
        policy_risk_level,
        # A location mismatch, or an assumption the local rules do not allow,
        # means the numbers above may not describe reality.
        len(missing_flags)
        + (1 if location_mismatch else 0)
        + sum(1 for conflict in assumption_conflicts if conflict["level"] == "high"),
    )

    risks = build_risks(metrics, market_context, policy_context, missing_flags)
    risks = assumption_conflicts + risks
    for flag in researched_flags:
        if flag["level"] == "high":
            risks.append(
                {
                    "level": "high",
                    "title": flag["title"],
                    "detail": f"{flag['detail']} (Researched policy note: {flag['source_document']})",
                }
            )
    if location_mismatch:
        risks.insert(
            0,
            {
                "level": "high",
                "title": "Address Fields Do Not Match",
                "detail": " ".join(location_check.get("warnings", [])),
            },
        )
    opportunities = build_opportunities(metrics, market_context)
    overall_risk = _risk_label(
        max(
            [_risk_level_score(item["level"]) for item in risks]
            + [_risk_level_score(policy_context.get("risk_level", "medium"))]
        )
    )

    return {
        "property": {
            "address": request.address,
            "city": request.city,
            "state": request.state.upper(),
            "zip_code": request.zip_code,
        },
        "assumptions": assumptions,
        "market": market_context,
        "policy": policy_context,
        "knowledge_bank": knowledge_bank_context,
        "research_request": build_research_request(request, knowledge_bank_context),
        "assumption_conflicts": assumption_conflicts,
        "diligence_items": knowledge_bank_context.get("diligence_items", []),
        "location_check": location_check,
        "financials": metrics,
        "risks": risks,
        "opportunities": opportunities,
        "missing_data_flags": missing_flags,
        "overall_risk": overall_risk,
        "recommendation": recommendation,
        "disclaimer": (
            "NorthStar is a decision-support tool, not legal, tax, "
            "financial, or investment advice. Verify all data before making a real purchase."
        ),
    }
