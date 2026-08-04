"""Redfin ZIP-level sale data: lookup, layering, and the price-vs-market check.

None of these tests touch the network or require `data/redfin_markets.json` to
exist. The generated file is optional by design, so the fixtures below stand in
for it and the "no file at all" case is tested explicitly.
"""

import pytest

from app import data_loader
from app.analysis import build_opportunities, build_risks, price_vs_market


SAMPLE_RECORD = {
    "period_end": "2026-06-30",
    "city": "Indianapolis",
    "state_code": "IN",
    "metro": "Indianapolis, IN",
    "median_sale_price": 250000.0,
    "median_sale_price_yoy": 0.04,
    "median_list_price": 259000.0,
    "median_ppsf": 165.0,
    "homes_sold": 42.0,
    "inventory": 88.0,
    "months_of_supply": 2.1,
    "median_days_on_market": 23.0,
    "avg_sale_to_list": 0.98,
}


@pytest.fixture
def redfin_file(monkeypatch):
    """Stand in for a generated data/redfin_markets.json covering 46202."""

    real_load_json = data_loader.load_json

    def fake_load_json(filename):
        if filename == "redfin_markets.json":
            return {"zip_markets": {"46202": SAMPLE_RECORD}}
        return real_load_json(filename)

    monkeypatch.setattr(data_loader, "load_json", fake_load_json)


@pytest.fixture
def no_redfin_file(monkeypatch):
    """Stand in for the refresh script never having been run."""

    real_load_json = data_loader.load_json

    def fake_load_json(filename):
        if filename == "redfin_markets.json":
            raise FileNotFoundError(filename)
        return real_load_json(filename)

    monkeypatch.setattr(data_loader, "load_json", fake_load_json)


def test_missing_file_is_not_an_error(no_redfin_file):
    assert data_loader.redfin_market("46202") is None


def test_missing_file_still_returns_market_context(no_redfin_file):
    context = data_loader.load_market_context("46202", "IN")
    assert context["match_level"] == "zip"
    assert "redfin" not in context


def test_uncovered_zip_returns_none(redfin_file):
    assert data_loader.redfin_market("99999") is None


def test_covered_zip_returns_the_record(redfin_file):
    record = data_loader.redfin_market("46202")
    assert record["median_sale_price"] == 250000.0
    assert record["metro"] == "Indianapolis, IN"


def test_market_context_layers_redfin_over_the_sample(redfin_file):
    context = data_loader.load_market_context("46202", "IN")
    assert context["redfin"]["median_sale_price"] == 250000.0
    # Redfin has no rent data, so the sample rent estimate must survive intact.
    assert context["median_rent_estimate"] == 1850


def test_redfin_never_overwrites_the_rent_estimate(redfin_file):
    """The one number Redfin must not touch, checked on a state fallback too."""
    context = data_loader.load_market_context("46202", "IN")
    sample = data_loader.load_json("market_data.json")["zip_markets"]["46202"]
    assert context["median_rent_estimate"] == sample["median_rent_estimate"]


def test_price_vs_market_returns_none_without_redfin():
    assert price_vs_market({"purchase_price": 300000}, {}) is None


def test_price_vs_market_computes_the_premium():
    context = {"redfin": {"median_sale_price": 250000.0}}
    assert price_vs_market({"purchase_price": 300000}, context) == pytest.approx(0.20)
    assert price_vs_market({"purchase_price": 200000}, context) == pytest.approx(-0.20)


def _metrics(purchase_price):
    return {
        "purchase_price": purchase_price,
        "annual_cash_flow": 1000,
        "dscr": 1.5,
        "break_even_monthly_rent": 1000,
        "monthly_rent": 2000,
        "irr_5_year": 0.10,
    }


def test_overpaying_raises_a_risk():
    context = {"redfin": {"median_sale_price": 250000.0}}
    risks = build_risks(_metrics(325000), context, {"risk_level": "low"}, [])
    flagged = [risk for risk in risks if risk["title"] == "Above-Market Purchase Price"]
    assert len(flagged) == 1
    assert flagged[0]["level"] == "high"
    assert "30%" in flagged[0]["detail"]


def test_a_modest_premium_is_only_a_medium_risk():
    context = {"redfin": {"median_sale_price": 250000.0}}
    risks = build_risks(_metrics(300000), context, {"risk_level": "low"}, [])
    flagged = [risk for risk in risks if risk["title"] == "Above-Market Purchase Price"]
    assert flagged[0]["level"] == "medium"


def test_paying_the_median_raises_nothing():
    context = {"redfin": {"median_sale_price": 250000.0}}
    risks = build_risks(_metrics(255000), context, {"risk_level": "low"}, [])
    assert not [r for r in risks if r["title"] == "Above-Market Purchase Price"]


def test_a_discount_is_an_opportunity_with_a_caveat():
    context = {"redfin": {"median_sale_price": 250000.0}}
    found = build_opportunities(_metrics(200000), context)
    flagged = [item for item in found if item["title"] == "Below-Market Purchase Price"]
    assert len(flagged) == 1
    assert "deferred maintenance" in flagged[0]["detail"]


def test_no_price_signal_without_redfin_coverage():
    risks = build_risks(_metrics(900000), {}, {"risk_level": "low"}, [])
    found = build_opportunities(_metrics(10000), {})
    assert not [r for r in risks if r["title"] == "Above-Market Purchase Price"]
    assert not [o for o in found if o["title"] == "Below-Market Purchase Price"]
