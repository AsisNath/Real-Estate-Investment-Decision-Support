"""Endpoint-level tests.

These call the route functions directly rather than through TestClient, which
would add an httpx dependency the app does not otherwise need.
"""

import pytest
from fastapi import HTTPException

import app.main as main_module

import app.knowledge_bank as knowledge_bank
from app.main import (
    add_knowledge_bank_note,
    analyze_property,
    knowledge_bank_inventory,
    knowledge_bank_note,
    location_check,
)
from app.schemas import AnalysisRequest, LocationCheckRequest, NewNoteRequest


@pytest.fixture(autouse=True)
def no_analysis_trail(monkeypatch):
    """Keep these tests from writing trail files into the real knowledge bank.

    The trail itself is covered by tests/test_analysis_trail.py.
    """
    monkeypatch.setattr(main_module, "record_analysis", lambda report: None)


def test_location_check_endpoint_flags_state_mismatch():
    result = location_check(LocationCheckRequest(city="Saint Charles", state="IN", zip_code="63301"))

    assert result["status"] == "warning"
    assert "belongs to MO" in result["warnings"][0]


def test_location_check_endpoint_accepts_matching_address():
    result = location_check(LocationCheckRequest(city="Saint Charles", state="MO", zip_code="63301"))

    assert result["status"] == "ok"
    assert result["warnings"] == []


def test_location_check_endpoint_tolerates_empty_input():
    # The form calls this while the user is still typing, so blanks must not 500.
    result = location_check(LocationCheckRequest())

    assert result["status"] == "warning"


def test_analyze_includes_location_check_and_risk():
    payload = AnalysisRequest(
        address="219 Charlestowne Place Dr",
        city="Saint Charles",
        state="IN",
        zip_code="63301",
        purchase_price=260000,
        monthly_rent=2600,
    )

    report = analyze_property(payload)

    assert report["location_check"]["status"] == "warning"
    assert report["risks"][0]["title"] == "Address Fields Do Not Match"
    assert report["risks"][0]["level"] == "high"


def test_inventory_lists_the_bundled_notes():
    inventory = knowledge_bank_inventory()

    paths = [note["relative_path"] for note in inventory["notes"]]
    assert "zips/78704/policy-notes.md" in paths
    assert "zips/90026/policy-notes.md" in paths
    assert "zips/11215/policy-notes.md" in paths
    assert inventory["high_flag_total"] >= 6


def test_note_endpoint_renders_html():
    note = knowledge_bank_note("zips/11215/policy-notes.md")

    assert "Brooklyn" in note["place"]
    assert "<table>" in note["html"]


def test_note_endpoint_rejects_traversal():
    with pytest.raises(HTTPException) as error:
        knowledge_bank_note("../../secrets.md")

    assert error.value.status_code == 400


def test_note_endpoint_404_for_missing_file():
    with pytest.raises(HTTPException) as error:
        knowledge_bank_note("zips/00000/nope.md")

    assert error.value.status_code == 404


def test_add_note_endpoint_writes_into_the_bank(tmp_path, monkeypatch):
    monkeypatch.setattr(knowledge_bank, "KNOWLEDGE_BANK_DIR", tmp_path)

    result = add_knowledge_bank_note(
        NewNoteRequest(
            scope="zip",
            value="46202",
            filename="hoa-cap.md",
            content="# HOA cap\n\n- Rentals capped at 10% of units.\n",
        )
    )

    assert result["relative_path"] == "zips/46202/hoa-cap.md"
    assert (tmp_path / "zips" / "46202" / "hoa-cap.md").exists()


def test_add_note_endpoint_reports_bad_scope_values(tmp_path, monkeypatch):
    monkeypatch.setattr(knowledge_bank, "KNOWLEDGE_BANK_DIR", tmp_path)

    with pytest.raises(HTTPException) as error:
        add_knowledge_bank_note(NewNoteRequest(scope="zip", value="abc", content="x"))

    assert error.value.status_code == 400


def test_add_note_endpoint_conflicts_on_existing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(knowledge_bank, "KNOWLEDGE_BANK_DIR", tmp_path)
    payload = NewNoteRequest(scope="global", filename="note.md", content="first")
    add_knowledge_bank_note(payload)

    with pytest.raises(HTTPException) as error:
        add_knowledge_bank_note(payload)

    assert error.value.status_code == 409


def test_rent_growth_above_the_noted_cap_is_flagged():
    # The Brooklyn note records a 0% cap for stabilized leases.
    payload = AnalysisRequest(
        address="250 5th Ave",
        city="Brooklyn",
        state="NY",
        zip_code="11215",
        purchase_price=1350000,
        monthly_rent=5200,
        annual_rent_growth_percent=3,
    )

    report = analyze_property(payload)

    titles = [conflict["title"] for conflict in report["assumption_conflicts"]]
    assert "Rent Growth Exceeds the Local Legal Cap" in titles
    assert report["risks"][0]["title"] == "Rent Growth Exceeds the Local Legal Cap"


def test_rent_growth_within_the_noted_cap_is_not_flagged():
    payload = AnalysisRequest(
        address="250 5th Ave",
        city="Brooklyn",
        state="NY",
        zip_code="11215",
        purchase_price=1350000,
        monthly_rent=5200,
        annual_rent_growth_percent=0,
    )

    report = analyze_property(payload)

    titles = [conflict["title"] for conflict in report["assumption_conflicts"]]
    assert "Rent Growth Exceeds the Local Legal Cap" not in titles


def test_uncapped_market_has_no_rent_growth_conflict():
    # The Austin note records no rent-control cap.
    payload = AnalysisRequest(
        address="1200 S Congress Ave",
        city="Austin",
        state="TX",
        zip_code="78704",
        purchase_price=725000,
        monthly_rent=3900,
        annual_rent_growth_percent=5,
    )

    report = analyze_property(payload)

    assert report["assumption_conflicts"] == []


def test_research_request_prompt_uses_the_entered_address():
    payload = AnalysisRequest(
        address="219 Charlestowne Place Dr",
        city="Saint Charles",
        state="mo",
        zip_code="63301",
        purchase_price=260000,
        monthly_rent=2600,
    )

    report = analyze_property(payload)

    assert report["research_request"]["prompt"] == (
        "Run policy diligence on 219 Charlestowne Place Dr, Saint Charles, MO 63301."
    )


def test_research_request_is_missing_when_no_notes_exist(tmp_path, monkeypatch):
    import app.data_loader as data_loader

    monkeypatch.setattr(data_loader, "KNOWLEDGE_BANK_DIR", tmp_path)
    payload = AnalysisRequest(
        address="1 Empty Folder Rd",
        city="Nowhere",
        state="WY",
        zip_code="82001",
        purchase_price=260000,
        monthly_rent=2600,
    )

    report = analyze_property(payload)

    assert report["research_request"]["status"] == "missing"


def test_research_request_is_stale_when_a_matching_note_is_old(tmp_path, monkeypatch):
    import app.data_loader as data_loader

    monkeypatch.setattr(data_loader, "KNOWLEDGE_BANK_DIR", tmp_path)
    note_dir = tmp_path / "zips" / "82001"
    note_dir.mkdir(parents=True)
    (note_dir / "policy-notes.md").write_text(
        "# Policy Notes - Somewhere, WY 82001\n\n**Researched:** 2020-01-01\n\nOld note.\n",
        encoding="utf-8",
    )
    payload = AnalysisRequest(
        address="1 Old Note Rd",
        city="Somewhere",
        state="WY",
        zip_code="82001",
        purchase_price=260000,
        monthly_rent=2600,
    )

    report = analyze_property(payload)

    assert report["research_request"]["status"] == "stale"


def test_research_request_is_current_for_a_fresh_bundled_note():
    payload = AnalysisRequest(
        address="1200 S Congress Ave",
        city="Austin",
        state="TX",
        zip_code="78704",
        purchase_price=725000,
        monthly_rent=3900,
    )

    report = analyze_property(payload)

    assert report["research_request"]["status"] == "current"


def test_diligence_checklist_reaches_the_report():
    payload = AnalysisRequest(
        address="1400 Echo Park Ave",
        city="Los Angeles",
        state="CA",
        zip_code="90026",
        purchase_price=985000,
        monthly_rent=4200,
    )

    report = analyze_property(payload)

    assert report["diligence_items"]
    assert all(entry["source_document"] for entry in report["diligence_items"])


def test_analyze_clean_address_has_no_location_risk():
    payload = AnalysisRequest(
        address="725 N Delaware St",
        city="Indianapolis",
        state="IN",
        zip_code="46202",
        purchase_price=260000,
        monthly_rent=2600,
    )

    report = analyze_property(payload)

    assert report["location_check"]["status"] == "ok"
    assert all(risk["title"] != "Address Fields Do Not Match" for risk in report["risks"])
