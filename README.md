# NorthStar Property Investment Consulting

NorthStar is a local real estate investment decision-support tool. It lets a user enter a mainland U.S. property address and investment assumptions, then returns a structured investor report with financial metrics, local sample market context, policy/rental restriction warnings, risks, opportunities, and a final recommendation: **Buy**, **Investigate Further**, or **Reject**.

This local MVP does not use paid APIs or live real estate data. The sample market and policy data are stored in local JSON files so the demo is reliable. Live policy research is handled outside the app runtime by the reusable `property-policy-research` agent Skill (see below), so the demo stays fully reliable offline.

> Design Studio Project | BUKD-X500: Agentic AI Systems | Kelley School of Business
> Team 5: Ashish Nath, Justin Kretschman
> Full proposal: [Week9_DSP_NorthStar_Property_Investment_Consulting_Proposal.docx](Week9_DSP_NorthStar_Property_Investment_Consulting_Proposal.docx)

## Architecture

- `app/main.py`: FastAPI app, page route, health endpoint, sample property endpoint, analysis endpoint.
- `app/schemas.py`: Pydantic request validation.
- `app/finance.py`: deterministic financial model, return metrics, projection metrics, and recommendation rules.
- `app/data_loader.py`: local JSON data loading and fallback logic.
- `app/analysis.py`: combines finance, market data, policy data, risks, opportunities, and final report.
- `data/`: sample market, policy, and property records, plus `zip_directory.json` for city/state/ZIP consistency checks.
- `knowledge_bank/`: local folder for HOA rules, city policy notes, rental law notes, lease restrictions, or other manual due-diligence files.
- `templates/index.html`: dashboard page.
- `static/app.js`: form handling and report rendering.
- `static/styles.css`: business dashboard styling.
- `tests/test_finance.py`: unit tests for financial calculations and recommendation logic.
- `tests/test_data_loader.py`: unit tests for knowledge-bank folder discovery.
- `.claude/skills/property-policy-research/`: reusable agent Skill that researches live rental policy for an address and writes source-cited notes into `knowledge_bank/`.
- `agentic.md`: AI project memory for future work sessions.

## Data Flow

1. The browser form collects property and investment assumptions.
2. The frontend sends a JSON request to `POST /api/analyze`.
3. FastAPI validates the request with Pydantic, then `check_location_consistency` verifies that the city, state, and ZIP describe the same place using `data/zip_directory.json`. A mismatch produces a warning banner at the top of the report, a high risk entry, and counts against a confident recommendation.
4. `finance.py` calculates loan, LTV, operating expenses, NOI, cash flow, break-even rent, DSCR, going-in cap rate, cash-on-cash return, 5-year and 10-year IRR, equity multiple, exit cap rate, sales costs, and projected sale proceeds.
5. `data_loader.py` loads market data by ZIP code with state/national fallback, and builds a layered policy context: city/county (ZIP-level), state, and national records are merged so the report covers every jurisdiction level that matches, and each restriction flag and source link is tagged with its jurisdiction (city/county, state, HOA/private). City-specific example links inside a state record are only shown when the analyzed city matches, so a Saint Charles property never displays St. Louis rules.
6. `data_loader.py` also checks `knowledge_bank` for local `.md` or `.txt` policy files matching the state, ZIP, city, or specific property.
7. `analysis.py` combines the results into a structured report.
8. The frontend renders summary cards, projections, risks, opportunities, policy source links, knowledge-bank notes, missing-data flags, and a final recommendation.

## Knowledge Bank

Until document upload is added, put manual policy and restriction files in `knowledge_bank`.

Useful files include:

- HOA declarations or rental caps
- Condo rules
- Deed restrictions
- City rental registration notes
- Short-term rental permit notes
- Local landlord-tenant law notes
- Lender or lease restrictions

NorthStar reads `.md` and `.txt` files from:

```text
knowledge_bank/global
knowledge_bank/states/STATE
knowledge_bank/zips/ZIP
knowledge_bank/cities/city_state
knowledge_bank/properties/address_zip
knowledge_bank/state-zip          (written by the policy research Skill, e.g. tx-78704)
knowledge_bank/state-city_slug    (written by the policy research Skill, e.g. tx-austin)
```

Example:

```text
knowledge_bank/properties/725_n_delaware_st_46202/hoa_restrictions.md
```

## Policy Research Skill (agent)

The project includes a reusable agent Skill, `property-policy-research` (in `.claude/skills/`), that automates first-pass policy diligence. Given an address, it web-searches short-term rental permit rules, state landlord-tenant law, rent control status, and HOA rental restrictions, verifies findings against official `.gov` sources, and writes dated, source-cited notes to `knowledge_bank/<state>-<zip>/policy-notes.md`. Every fact carries a source link, an "as of" date, and an official-vs-secondary tag.

The Skill runs outside the app runtime (in Claude Code, Cowork, or claude.ai with web search enabled), so the app itself stays offline and deterministic. On the next analysis of that address, the app surfaces the generated notes in the report's knowledge-bank section. See `.claude/skills/property-policy-research/README.md` for installation and usage on other platforms.

## Investor Metrics Included

The report includes:

- Debt Service Coverage Ratio (DSCR)
- Net Operating Income (NOI)
- Cash-on-Cash (CoC) Return
- Equity Multiple for 5-year and 10-year holding periods
- Growth and inflation assumptions
- Sales costs and closing costs
- Holding-period projections
- Going-in capitalization rate and exit capitalization rate
- Loan-to-Value (LTV) ratio

## Setup

From the project folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## One-Click Run

Double-click `Run_NorthStar.bat`.

The batch file will create `.venv` if needed, install requirements, run the quick tests, stop any old NorthStar server still holding port 8000, open the browser, and start the local server at `http://127.0.0.1:8000`.

Stopping the old server matters: a running Python process keeps the code and JSON data it loaded at startup, so a stale server keeps serving old results no matter what changed on disk. To stop one by hand:

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

## Run

```powershell
uvicorn app.main:app --reload
```

Open:

```text
http://localhost:8000
```

## Test

```powershell
pytest
```

## Demo Suggestions

Use the "Load sample" menu to quickly populate a scenario:

- Indianapolis sample: stronger deal that should produce a Buy recommendation.
- St. Louis sample: older-home diligence case.
- Austin sample: high-price caution case with policy risk.

You can also type any address, city, state, and ZIP. If the ZIP is not in the local sample data, NorthStar will use fallback data and clearly flag the missing local information.

## Future Extensions

- Host the full website on a server or cloud platform for online access.
- Secure document upload for HOA declarations, leases, local ordinances, lender terms, and inspection reports, with AI-assisted document Q&A.
- Live public-data retrieval for market rents, property taxes, insurance assumptions, and zoning through paid APIs.
- Scenario comparison for best/base/worst cases, multiple financing structures, and sensitivity analysis.
- Multi-property comparison so investors can rank several candidate properties side by side.

## Responsible Use

NorthStar is a decision-support tool, not licensed legal, tax, financial, or investment advice. All public data and policy summaries must be verified before a real purchase decision. Policy notes generated by the research Skill separate officially verified facts from secondary sources — anything tagged secondary should be confirmed with the issuing authority.
