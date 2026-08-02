from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
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
from app.knowledge_bank import (
    build_folder,
    create_note,
    read_note,
    read_trace,
    record_analysis,
    scan_knowledge_bank,
)
from app.policy_brief import build_brief
from app.policy_research import (
    availability as research_availability,
    request_research,
    status as research_status,
)
from app.schemas import (
    AnalysisRequest,
    HealthResponse,
    LocationCheckRequest,
    NewNoteRequest,
)


# Web assets live beside the code they serve, so this is the app package
# directory - not the project root that data_loader and knowledge_bank use.
APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
TEMPLATES_DIR = APP_DIR / "templates"

app = FastAPI(
    title="NorthStar Property Investment Consulting",
    description="Local real estate investment decision-support tool.",
    version="0.1.0",
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


def asset_version() -> str:
    """Newest timestamp among the static files, used to bust the browser cache.

    Without this, a browser can keep an old app.js after the server restarts,
    which makes fixed code look broken.
    """
    stamps = [
        int(path.stat().st_mtime)
        for path in STATIC_DIR.glob("*")
        if path.is_file()
    ]
    return str(max(stamps)) if stamps else "0"


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "asset_version": asset_version()},
    )


@app.get("/knowledge-bank", response_class=HTMLResponse)
def knowledge_bank_page(request: Request):
    return templates.TemplateResponse(
        "knowledge_bank.html",
        {"request": request, "asset_version": asset_version()},
    )


@app.get("/api/knowledge-bank")
def knowledge_bank_inventory():
    """Every note in the folder, including ones the user added by hand."""
    return scan_knowledge_bank()


@app.get("/api/knowledge-bank/note")
def knowledge_bank_note(path: str):
    try:
        return read_note(path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="That note was not found.")
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.get("/knowledge-bank/brief", response_class=HTMLResponse)
def knowledge_bank_brief(path: str, download: bool = False):
    """Render a note as a client-ready Policy Brief.

    This is the Lab 5 "polished deliverable" turned into a generator: it opens in
    a tab, prints to PDF cleanly, and is regenerated from the note every time, so
    a brief can never drift from the research behind it.
    """
    try:
        brief = build_brief(path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="That note was not found.")
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    headers = (
        {"Content-Disposition": f'attachment; filename="{brief["filename"]}"'}
        if download
        else {}
    )
    return HTMLResponse(content=brief["html"], headers=headers)


@app.get("/api/knowledge-bank/trace")
def knowledge_bank_trace(path: str):
    """Read an analysis trail file so the user can inspect past runs."""
    try:
        return read_trace(path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="That trace file was not found.")
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.post("/api/knowledge-bank/notes", status_code=201)
def add_knowledge_bank_note(payload: NewNoteRequest):
    """Save a policy note the user wrote or pasted into the app."""
    try:
        folder = payload.folder.strip() or build_folder(
            payload.scope, payload.value, payload.state
        )
        return create_note(folder, payload.filename, payload.content, payload.overwrite)
    except FileExistsError as error:
        raise HTTPException(status_code=409, detail=str(error))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except OSError as error:
        raise HTTPException(status_code=400, detail=f"Could not write the note: {error}")


@app.get("/api/health", response_model=HealthResponse)
def health():
    return {"status": "ok", "app": "NorthStar Property Investment Consulting"}


@app.get("/api/sample-properties")
def sample_properties():
    return {"properties": load_sample_properties()}


@app.post("/api/location-check")
def location_check(payload: LocationCheckRequest):
    """Check city/state/ZIP agreement while the user is still filling the form."""
    return check_location_consistency(payload.city, payload.state, payload.zip_code)


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
    report = build_report(
        payload,
        market_context,
        policy_context,
        knowledge_bank_context,
        location_check,
    )

    # If this location has no researched policy note, start one now. This returns
    # immediately - the research itself runs in a background thread and the page
    # polls /api/research/status - and it is a no-op when a note already exists,
    # when a pass is already running, or when no API key is configured.
    if report["research_request"]["status"] in {"missing", "stale"}:
        report["research_request"]["auto"] = request_research(
            payload.address,
            payload.city,
            payload.state,
            payload.zip_code,
        )
    else:
        report["research_request"]["auto"] = research_status(payload.zip_code)

    # Leave an audit trail beside that ZIP's notes so the sources behind this
    # recommendation can be traced later.
    report["analysis_log"] = record_analysis(report)
    return report


@app.get("/api/research/status")
def research_status_endpoint(zip_code: str):
    """Poll target while a background research pass runs."""
    return research_status(zip_code)


@app.post("/api/research/retry")
def research_retry(payload: AnalysisRequest):
    """Run research again after a failure, or refresh a note on demand.

    Automatic research refuses to repeat a failed call on its own, because a bad
    key would otherwise be retried - and billed - on every analysis. This is the
    explicit "try that again" the user asks for.
    """
    ready = research_availability()
    if not ready["available"]:
        raise HTTPException(status_code=400, detail=ready["reason"])
    return request_research(
        payload.address,
        payload.city,
        payload.state,
        payload.zip_code,
        force=True,
    )
