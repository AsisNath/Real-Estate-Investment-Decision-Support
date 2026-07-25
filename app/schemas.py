from __future__ import annotations

from pydantic import BaseModel, Field


class AnalysisRequest(BaseModel):
    address: str = Field(..., min_length=3)
    city: str = Field(..., min_length=2)
    state: str = Field(..., min_length=2, max_length=2)
    zip_code: str = Field(..., min_length=5, max_length=10)
    purchase_price: float = Field(..., gt=0)
    monthly_rent: float = Field(..., ge=0)
    down_payment_percent: float = Field(20, ge=0, le=100)
    interest_rate_percent: float = Field(6.75, ge=0, le=25)
    loan_term_years: int = Field(30, ge=1, le=40)
    annual_property_tax: float = Field(3600, ge=0)
    annual_insurance: float = Field(1800, ge=0)
    monthly_hoa_fee: float = Field(0, ge=0)
    maintenance_percent_of_rent: float = Field(8, ge=0, le=50)
    monthly_maintenance: float = Field(0, ge=0)
    vacancy_percent: float = Field(6, ge=0, le=100)
    property_management_percent: float = Field(8, ge=0, le=100)
    annual_appreciation_percent: float = Field(3, ge=-20, le=30)
    annual_rent_growth_percent: float = Field(2.5, ge=-20, le=30)
    annual_expense_growth_percent: float = Field(2.5, ge=0, le=30)
    closing_cost_percent: float = Field(3, ge=0, le=15)
    selling_cost_percent: float = Field(6, ge=0, le=15)


class LocationCheckRequest(BaseModel):
    """Loose validation on purpose: the point is to report bad input, not reject it."""

    city: str = ""
    state: str = ""
    zip_code: str = ""


class NewNoteRequest(BaseModel):
    """A policy note the user is adding through the app."""

    scope: str = "custom"
    value: str = ""
    state: str = ""
    folder: str = ""
    filename: str = "policy-notes.md"
    content: str = Field(..., min_length=1)
    overwrite: bool = False


class HealthResponse(BaseModel):
    status: str
    app: str
