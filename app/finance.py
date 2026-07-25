from __future__ import annotations

from typing import Any


def percent(value: float) -> float:
    return value / 100.0


def monthly_mortgage_payment(
    loan_amount: float,
    annual_interest_rate_percent: float,
    loan_term_years: int,
) -> float:
    """Standard fixed-rate amortizing mortgage payment."""
    if loan_amount <= 0:
        return 0.0

    months = loan_term_years * 12
    if months <= 0:
        raise ValueError("loan_term_years must be positive")

    monthly_rate = percent(annual_interest_rate_percent) / 12
    if monthly_rate == 0:
        return loan_amount / months

    factor = (1 + monthly_rate) ** months
    return loan_amount * (monthly_rate * factor) / (factor - 1)


def remaining_loan_balance(
    original_loan_amount: float,
    annual_interest_rate_percent: float,
    loan_term_years: int,
    months_elapsed: int,
) -> float:
    if original_loan_amount <= 0:
        return 0.0

    total_months = loan_term_years * 12
    if months_elapsed >= total_months:
        return 0.0

    monthly_rate = percent(annual_interest_rate_percent) / 12
    if monthly_rate == 0:
        return original_loan_amount * (1 - months_elapsed / total_months)

    factor_total = (1 + monthly_rate) ** total_months
    factor_elapsed = (1 + monthly_rate) ** months_elapsed
    return original_loan_amount * (factor_total - factor_elapsed) / (factor_total - 1)


def calculate_irr(cash_flows: list[float]) -> float | None:
    """Annual IRR for evenly spaced yearly cash flows."""
    has_positive = any(value > 0 for value in cash_flows)
    has_negative = any(value < 0 for value in cash_flows)
    if not has_positive or not has_negative:
        return None

    def npv(rate: float) -> float:
        return sum(value / ((1 + rate) ** index) for index, value in enumerate(cash_flows))

    low = -0.99
    high = 1.0
    low_value = npv(low)
    high_value = npv(high)

    while low_value * high_value > 0 and high < 10:
        high *= 2
        high_value = npv(high)

    if low_value * high_value > 0:
        return None

    for _ in range(120):
        midpoint = (low + high) / 2
        midpoint_value = npv(midpoint)
        if abs(midpoint_value) < 0.000001:
            return midpoint
        if low_value * midpoint_value < 0:
            high = midpoint
            high_value = midpoint_value
        else:
            low = midpoint
            low_value = midpoint_value

    return (low + high) / 2


def annual_operating_expenses(
    gross_annual_rent: float,
    annual_property_tax: float,
    annual_insurance: float,
    monthly_hoa_fee: float,
    maintenance_percent_of_rent: float,
    monthly_maintenance: float,
    vacancy_percent: float,
    property_management_percent: float,
) -> dict[str, float]:
    maintenance = (
        monthly_maintenance * 12
        if monthly_maintenance > 0
        else gross_annual_rent * percent(maintenance_percent_of_rent)
    )
    vacancy = gross_annual_rent * percent(vacancy_percent)
    management = gross_annual_rent * percent(property_management_percent)
    hoa = monthly_hoa_fee * 12
    total = annual_property_tax + annual_insurance + hoa + maintenance + vacancy + management

    return {
        "property_tax": annual_property_tax,
        "insurance": annual_insurance,
        "hoa": hoa,
        "maintenance": maintenance,
        "vacancy": vacancy,
        "management": management,
        "total": total,
    }


def break_even_monthly_rent(
    annual_debt_service: float,
    annual_property_tax: float,
    annual_insurance: float,
    monthly_hoa_fee: float,
    maintenance_percent_of_rent: float,
    monthly_maintenance: float,
    vacancy_percent: float,
    property_management_percent: float,
) -> float:
    fixed_expenses = annual_property_tax + annual_insurance + (monthly_hoa_fee * 12)
    variable_rate = percent(vacancy_percent) + percent(property_management_percent)

    if monthly_maintenance > 0:
        fixed_expenses += monthly_maintenance * 12
    else:
        variable_rate += percent(maintenance_percent_of_rent)

    rent_capture_rate = max(0.01, 1 - variable_rate)
    return (annual_debt_service + fixed_expenses) / (12 * rent_capture_rate)


def projected_annual_cash_flows(
    assumptions: dict[str, float | int | str],
    monthly_payment: float,
    years: int,
) -> list[float]:
    return [
        year["annual_cash_flow"]
        for year in projected_annual_operations(assumptions, monthly_payment, years)
    ]


def projected_annual_operations(
    assumptions: dict[str, float | int | str],
    monthly_payment: float,
    years: int,
) -> list[dict[str, Any]]:
    rent_growth = percent(float(assumptions["annual_rent_growth_percent"]))
    expense_growth = percent(float(assumptions["annual_expense_growth_percent"]))
    annual_debt_service = monthly_payment * 12
    operations: list[dict[str, Any]] = []

    for year in range(1, years + 1):
        growth_factor = (1 + rent_growth) ** (year - 1)
        expense_factor = (1 + expense_growth) ** (year - 1)
        gross_rent = float(assumptions["monthly_rent"]) * 12 * growth_factor

        expenses = annual_operating_expenses(
            gross_rent,
            float(assumptions["annual_property_tax"]) * expense_factor,
            float(assumptions["annual_insurance"]) * expense_factor,
            float(assumptions["monthly_hoa_fee"]) * expense_factor,
            float(assumptions["maintenance_percent_of_rent"]),
            float(assumptions["monthly_maintenance"]) * expense_factor,
            float(assumptions["vacancy_percent"]),
            float(assumptions["property_management_percent"]),
        )
        noi = gross_rent - expenses["total"]
        operations.append(
            {
                "year": year,
                "gross_annual_rent": gross_rent,
                "operating_expenses": expenses,
                "noi": noi,
                "annual_cash_flow": noi - annual_debt_service,
            }
        )

    return operations


def sale_analysis(
    purchase_price: float,
    loan_amount: float,
    annual_interest_rate_percent: float,
    loan_term_years: int,
    annual_appreciation_percent: float,
    selling_cost_percent: float,
    years: int,
) -> dict[str, float]:
    future_sale_value = purchase_price * ((1 + percent(annual_appreciation_percent)) ** years)
    selling_costs = future_sale_value * percent(selling_cost_percent)
    loan_balance = remaining_loan_balance(
        loan_amount,
        annual_interest_rate_percent,
        loan_term_years,
        years * 12,
    )
    net_sale_proceeds = future_sale_value - selling_costs - loan_balance

    return {
        "future_sale_value": future_sale_value,
        "selling_costs": selling_costs,
        "loan_balance": loan_balance,
        "net_sale_proceeds": net_sale_proceeds,
    }


def recommendation_from_metrics(
    metrics: dict[str, Any],
    policy_risk_level: str = "medium",
    missing_data_count: int = 0,
) -> dict[str, Any]:
    policy_risk = policy_risk_level.lower()
    monthly_rent = metrics["monthly_rent"]
    break_even_rent = metrics["break_even_monthly_rent"]
    annual_cash_flow = metrics["annual_cash_flow"]
    dscr = metrics["dscr"]
    irr_5 = metrics["irr_5_year"]

    reasons: list[str] = []
    status = "Investigate Further"

    if annual_cash_flow <= -3600:
        reasons.append("Annual cash flow is meaningfully negative.")
    if dscr < 1.0:
        reasons.append("DSCR is below 1.0, so NOI does not cover debt service.")
    if break_even_rent > monthly_rent * 1.25:
        reasons.append("Break-even rent is more than 25% above the expected rent.")
    if policy_risk == "high":
        reasons.append("Policy or rental restriction risk is high.")

    if reasons:
        status = "Reject"
    elif (
        annual_cash_flow > 0
        and dscr >= 1.2
        and irr_5 is not None
        and irr_5 >= 0.08
        and policy_risk in {"low", "medium"}
        and missing_data_count <= 2
    ):
        status = "Buy"
        reasons.extend(
            [
                "Projected cash flow is positive.",
                "DSCR is at or above the 1.20 comfort threshold.",
                "Five-year IRR meets the investment target.",
            ]
        )
    else:
        reasons.extend(
            [
                "The deal has mixed signals or needs stronger verification before purchase.",
                "Review rent assumptions, local restrictions, and expense sensitivity before deciding.",
            ]
        )

    return {"status": status, "reasons": reasons}


def analyze_investment(assumptions: dict[str, float | int | str]) -> dict[str, Any]:
    purchase_price = float(assumptions["purchase_price"])
    down_payment = purchase_price * percent(float(assumptions["down_payment_percent"]))
    loan_amount = max(0.0, purchase_price - down_payment)
    ltv = loan_amount / purchase_price if purchase_price else 0.0
    closing_costs = purchase_price * percent(float(assumptions["closing_cost_percent"]))
    initial_cash_invested = down_payment + closing_costs

    monthly_payment = monthly_mortgage_payment(
        loan_amount,
        float(assumptions["interest_rate_percent"]),
        int(assumptions["loan_term_years"]),
    )
    annual_debt_service = monthly_payment * 12
    gross_annual_rent = float(assumptions["monthly_rent"]) * 12

    operating_expense_detail = annual_operating_expenses(
        gross_annual_rent,
        float(assumptions["annual_property_tax"]),
        float(assumptions["annual_insurance"]),
        float(assumptions["monthly_hoa_fee"]),
        float(assumptions["maintenance_percent_of_rent"]),
        float(assumptions["monthly_maintenance"]),
        float(assumptions["vacancy_percent"]),
        float(assumptions["property_management_percent"]),
    )

    noi = gross_annual_rent - operating_expense_detail["total"]
    annual_cash_flow = noi - annual_debt_service
    monthly_cash_flow = annual_cash_flow / 12
    cap_rate = noi / purchase_price if purchase_price else 0.0
    cash_on_cash_return = annual_cash_flow / initial_cash_invested if initial_cash_invested else 0.0
    dscr = noi / annual_debt_service if annual_debt_service else 99.0
    break_even = break_even_monthly_rent(
        annual_debt_service,
        float(assumptions["annual_property_tax"]),
        float(assumptions["annual_insurance"]),
        float(assumptions["monthly_hoa_fee"]),
        float(assumptions["maintenance_percent_of_rent"]),
        float(assumptions["monthly_maintenance"]),
        float(assumptions["vacancy_percent"]),
        float(assumptions["property_management_percent"]),
    )

    projections: dict[str, dict[str, Any]] = {}
    irr_results: dict[int, float | None] = {}

    for years in (5, 10):
        annual_operations = projected_annual_operations(assumptions, monthly_payment, years)
        annual_cash_flows = [year["annual_cash_flow"] for year in annual_operations]
        sale = sale_analysis(
            purchase_price,
            loan_amount,
            float(assumptions["interest_rate_percent"]),
            int(assumptions["loan_term_years"]),
            float(assumptions["annual_appreciation_percent"]),
            float(assumptions["selling_cost_percent"]),
            years,
        )
        irr_cash_flows = [-initial_cash_invested] + annual_cash_flows[:]
        irr_cash_flows[-1] += sale["net_sale_proceeds"]
        irr = calculate_irr(irr_cash_flows)
        total_cash_flow = sum(annual_cash_flows)
        total_distributions = total_cash_flow + sale["net_sale_proceeds"]
        equity_multiple = (
            total_distributions / initial_cash_invested if initial_cash_invested else None
        )
        final_year_noi = annual_operations[-1]["noi"]
        exit_cap_rate = (
            final_year_noi / sale["future_sale_value"] if sale["future_sale_value"] else None
        )
        irr_results[years] = irr
        projections[str(years)] = {
            "holding_period_years": years,
            "annual_operations": annual_operations,
            "annual_cash_flows": annual_cash_flows,
            "sale": sale,
            "irr": irr,
            "total_cash_flow": total_cash_flow,
            "total_distributions": total_distributions,
            "equity_multiple": equity_multiple,
            "final_year_noi": final_year_noi,
            "exit_cap_rate": exit_cap_rate,
        }

    return {
        "purchase_price": purchase_price,
        "monthly_rent": float(assumptions["monthly_rent"]),
        "down_payment": down_payment,
        "loan_amount": loan_amount,
        "ltv": ltv,
        "closing_costs": closing_costs,
        "initial_cash_invested": initial_cash_invested,
        "monthly_mortgage_payment": monthly_payment,
        "annual_debt_service": annual_debt_service,
        "gross_annual_rent": gross_annual_rent,
        "operating_expenses": operating_expense_detail,
        "noi": noi,
        "monthly_cash_flow": monthly_cash_flow,
        "annual_cash_flow": annual_cash_flow,
        "cap_rate": cap_rate,
        "cash_on_cash_return": cash_on_cash_return,
        "break_even_monthly_rent": break_even,
        "dscr": dscr,
        "irr_5_year": irr_results[5],
        "irr_10_year": irr_results[10],
        "equity_multiple_5_year": projections["5"]["equity_multiple"],
        "equity_multiple_10_year": projections["10"]["equity_multiple"],
        "exit_cap_rate_5_year": projections["5"]["exit_cap_rate"],
        "exit_cap_rate_10_year": projections["10"]["exit_cap_rate"],
        "growth_assumptions": {
            "annual_appreciation": percent(float(assumptions["annual_appreciation_percent"])),
            "annual_rent_growth": percent(float(assumptions["annual_rent_growth_percent"])),
            "annual_expense_inflation": percent(float(assumptions["annual_expense_growth_percent"])),
        },
        "sale_assumptions": {
            "selling_cost_percent": percent(float(assumptions["selling_cost_percent"])),
            "closing_cost_percent": percent(float(assumptions["closing_cost_percent"])),
        },
        "holding_periods": [5, 10],
        "projections": projections,
    }
