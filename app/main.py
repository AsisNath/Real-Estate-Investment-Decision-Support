from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.analysis import build_report
from app.data_loader import (
    check_location_consistency,
    load_knowledge_bank_context,
    load_market_context,
    load_policy_context,
    load_sample_properties,
)
from app.schemas import AnalysisRequest, HealthResponse


BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(
    title="NorthStar Property Investment Consulting",
    description="Local real estate investment decision-support tool.",
    version="0.1.0",
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/health", response_model=HealthResponse)
def health():
    return {"status": "ok", "app": "NorthStar Property Investment Consulting"}


@app.get("/api/sample-properties")
def sample_properties():
    return {"properties": load_sample_properties()}


@app.post("/api/analyze")
def analyze_property(payload: AnalysisRequest):
    market_context = load_market_context(payload.zip_code, payload.state)
    policy_context = load_policy_context(payload.zip_code, payload.state, payload.city)
    knowledge_bank_context = load_knowledge_bank_context(
        payload.address,
        payload.city,
        payload.state,
        payload.zip_code,
    )
    location_check = check_location_consistency(
        payload.city,
        payload.state,
        payload.zip_code,
    )
    return build_report(
        payload,
        market_context,
        policy_context,
        knowledge_bank_context,
        location_check,
    )
