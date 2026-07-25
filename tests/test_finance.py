import pytest

from app.finance import (
    analyze_investment,
    break_even_monthly_rent,
    calculate_irr,
    monthly_mortgage_payment,
    recommendation_from_metrics,
)


BASE_ASSUMPTIONS = {
    "purchase_price": 285000,
    "monthly_rent": 2450,
    "down_payment_percent": 20,
    "interest_rate_percent": 6.75,
    "loan_term_years": 30,
    "annual_property_tax": 3600,
    "annual_insurance": 1700,
    "monthly_hoa_fee": 0,
    "maintenance_percent_of_rent": 8,
    "monthly_maintenance": 0,
    "vacancy_percent": 6,
    "property_management_percent": 8,
    "annual_appreciation_percent": 3,
    "annual_rent_growth_percent": 3,
    "annual_expense_growth_percent": 2.5,
    "closing_cost_percent": 3,
    "selling_cost_percent": 6,
}


def test_monthly_mortgage_payment():
    payment = monthly_mortgage_payment(228000, 6.75, 30)
    assert payment == pytest.approx(1478.87, abs=0.5)


def test_cash_flow_and_cap_rate():
    metrics = analyze_investment(BASE_ASSUMPTIONS)
    assert metrics["gross_annual_rent"] == 29400
    assert metrics["noi"] == pytest.approx(17632, abs=1)
    assert metrics["annual_cash_flow"] == pytest.approx(-114.42, abs=5)
    assert metrics["cap_rate"] == pytest.approx(0.0619, abs=0.001)
    assert metrics["ltv"] == pytest.approx(0.8)


def test_break_even_rent():
    break_even = break_even_monthly_rent(
        annual_debt_service=17746.44,
        annual_property_tax=3600,
        annual_insurance=1700,
        monthly_hoa_fee=0,
        maintenance_percent_of_rent=8,
        monthly_maintenance=0,
        vacancy_percent=6,
        property_management_percent=8,
    )
    assert break_even == pytest.approx(2462.23, abs=2)


def test_irr_calculation():
    irr = calculate_irr([-100000, 10000, 10000, 10000, 10000, 140000])
    assert irr == pytest.approx(0.1449, abs=0.002)


def test_equity_multiple_exit_cap_and_sales_costs():
    metrics = analyze_investment(BASE_ASSUMPTIONS)
    five_year = metrics["projections"]["5"]
    ten_year = metrics["projections"]["10"]

    assert metrics["equity_multiple_5_year"] == pytest.approx(1.551, abs=0.002)
    assert metrics["equity_multiple_10_year"] == pytest.approx(2.923, abs=0.002)
    assert metrics["exit_cap_rate_5_year"] == pytest.approx(0.0604, abs=0.001)
    assert five_year["sale"]["selling_costs"] == pytest.approx(19823.59, abs=1)
    assert five_year["holding_period_years"] == 5
    assert ten_year["holding_period_years"] == 10


def test_recommendation_reject_for_low_dscr():
    metrics = analyze_investment({**BASE_ASSUMPTIONS, "monthly_rent": 1500})
    recommendation = recommendation_from_metrics(metrics, "medium", 0)
    assert recommendation["status"] == "Reject"


def test_recommendation_buy_for_strong_deal():
    metrics = analyze_investment(
        {
            **BASE_ASSUMPTIONS,
            "purchase_price": 220000,
            "monthly_rent": 2700,
            "annual_property_tax": 2800,
            "annual_insurance": 1400,
        }
    )
    recommendation = recommendation_from_metrics(metrics, "low", 0)
    assert recommendation["status"] == "Buy"
