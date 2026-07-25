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


def build_report(
    request: AnalysisRequest,
    market_context: dict[str, Any],
    policy_context: dict[str, Any],
    knowledge_bank_context: dict[str, Any],
    location_check: dict[str, Any] | None = None,
) -> dict[str, Any]:
    assumptions = request.dict()
    metrics = analyze_investment(assumptions)
    location_check = location_check or {"status": "unverified", "warnings": [], "unverified": []}
    location_mismatch = location_check.get("status") == "warning"

    missing_flags = []
    missing_flags.extend(market_context.get("missing_data_flags", []))
    missing_flags.extend(policy_context.get("missing_data_flags", []))

    recommendation = recommendation_from_metrics(
        metrics,
        policy_context.get("risk_level", "medium"),
        # A location mismatch means the market and policy sections may describe
        # the wrong place, so it counts against a confident recommendation.
        len(missing_flags) + (1 if location_mismatch else 0),
    )

    risks = build_risks(metrics, market_context, policy_context, missing_flags)
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
