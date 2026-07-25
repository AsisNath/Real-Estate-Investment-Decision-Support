"""Endpoint-level tests.

These call the route functions directly rather than through TestClient, which
would add an httpx dependency the app does not otherwise need.
"""

from app.main import analyze_property, location_check
from app.schemas import AnalysisRequest, LocationCheckRequest


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
