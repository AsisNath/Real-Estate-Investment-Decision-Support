"""Tests for researched policy notes written by the property-policy-research Skill."""

import app.data_loader as data_loader
from app.analysis import build_report
from app.data_loader import (
    load_knowledge_bank_context,
    load_market_context,
    load_policy_context,
    parse_policy_note,
)
from app.schemas import AnalysisRequest


NOTE = """# Policy Notes - Austin, TX 78704 (Travis County)

**Property context:** Residential rental property
**Researched:** July 19, 2026
**Method:** Web search + verification against official (.gov) sources

## 1. Short-Term Rental (STR) Rules

- Something cited. - as of 2026-07-19 official

## 5. High-Attention Flags (summary for NorthStar report)

| Flag | Severity | Why |
|---|---|---|
| STR license enforcement live | HIGH | Unlicensed STR income is not modelable |
| HOA CC&Rs unknown for parcel | MEDIUM | A recorded restriction can void the strategy |
| No rent control | INFO (positive) | Rent growth capped by market only |
"""


def test_parses_heading_place_and_research_date():
    parsed = parse_policy_note(NOTE)

    assert parsed["place"] == "Austin, TX 78704 (Travis County)"
    assert parsed["researched"] == "July 19, 2026"


def test_parses_flag_table_and_maps_severity():
    flags = parse_policy_note(NOTE)["flags"]

    assert [flag["level"] for flag in flags] == ["high", "medium", "low"]
    assert flags[0]["title"] == "STR license enforcement live"
    assert flags[0]["detail"] == "Unlicensed STR income is not modelable"


def test_note_without_flag_table_yields_no_flags():
    parsed = parse_policy_note("# Local notes\n\nJust a plain note with no table.\n")

    assert parsed["flags"] == []
    assert parsed["place"] == "Local notes"


def test_bundled_austin_note_is_discovered_and_parsed():
    context = load_knowledge_bank_context("1200 S Congress Ave", "Austin", "TX", "78704")

    paths = [doc["relative_path"] for doc in context["documents"]]
    assert "zips/78704/policy-notes.md" in paths

    titles = [flag["title"] for flag in context["researched_flags"]]
    assert any("STR license" in title for title in titles)
    assert all(flag["source_document"] for flag in context["researched_flags"])


def test_bundled_notes_exist_for_all_three_lab_markets():
    for city, state, zip_code in (
        ("Austin", "TX", "78704"),
        ("Los Angeles", "CA", "90026"),
        ("Brooklyn", "NY", "11215"),
    ):
        context = load_knowledge_bank_context("1 Main St", city, state, zip_code)
        assert context["researched_flags"], f"no researched flags for {city}"


def _report_for(address, city, state, zip_code, price, rent):
    request = AnalysisRequest(
        address=address, city=city, state=state, zip_code=zip_code,
        purchase_price=price, monthly_rent=rent,
    )
    return build_report(
        request,
        load_market_context(zip_code, state),
        load_policy_context(zip_code, state, city),
        load_knowledge_bank_context(address, city, state, zip_code),
    )


def test_researched_flags_reach_the_policy_section_and_risks():
    report = _report_for("1400 Echo Park Ave", "Los Angeles", "CA", "90026", 985000, 4200)

    policy_titles = [flag["title"] for flag in report["policy"]["restriction_flags"]]
    assert any("STR effectively unavailable" in title for title in policy_titles)

    risk_titles = [risk["title"] for risk in report["risks"]]
    assert any("RSO likely applies" in title for title in risk_titles)


def test_researched_notes_replace_the_add_notes_placeholder():
    report = _report_for("1400 Echo Park Ave", "Los Angeles", "CA", "90026", 985000, 4200)

    titles = [flag["title"] for flag in report["policy"]["restriction_flags"]]
    assert "Local law not resolved" not in titles
    assert any("researched knowledge-bank notes" in flag for flag in report["missing_data_flags"])


def test_placeholder_remains_when_no_notes_exist(tmp_path, monkeypatch):
    monkeypatch.setattr(data_loader, "KNOWLEDGE_BANK_DIR", tmp_path)
    report = _report_for("1 Main St", "Nowhere", "ZZ", "99999", 200000, 1500)

    titles = [flag["title"] for flag in report["policy"]["restriction_flags"]]
    assert "Local law not resolved" in titles


def test_high_researched_flag_raises_policy_risk():
    report = _report_for("250 5th Ave", "Brooklyn", "NY", "11215", 1350000, 5200)

    assert report["policy"]["risk_level"] == "high"
    assert report["overall_risk"] == "high"


def test_property_without_notes_has_no_researched_flags(tmp_path, monkeypatch):
    monkeypatch.setattr(data_loader, "KNOWLEDGE_BANK_DIR", tmp_path)
    context = load_knowledge_bank_context("1 Main St", "Nowhere", "IN", "46202")

    assert context["researched_flags"] == []
