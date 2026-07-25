# NorthStar Property Investment Consulting

NorthStar is a local real estate investment decision-support tool. It lets a user enter a mainland U.S. property address and investment assumptions, then returns a structured investor report with financial metrics, local sample market context, policy/rental restriction warnings, risks, opportunities, and a final recommendation.

This local MVP does not use paid APIs or live real estate data. The sample market and policy data are stored in local JSON files so the demo is reliable.

## Architecture

- `app/main.py`: FastAPI app, page route, health endpoint, sample property endpoint, analysis endpoint.
- `app/schemas.py`: Pydantic request validation.
- `app/finance.py`: deterministic financial model, return metrics, projection metrics, and recommendation rules.
- `app/data_loader.py`: local JSON data loading and fallback logic.
- `app/analysis.py`: combines finance, market data, policy data, risks, opportunities, and final report.
- `data/`: sample market, policy, and property records.
- `knowledge_bank/`: local folder for HOA rules, city policy notes, rental law notes, lease restrictions, or other manual due-diligence files.
- `templates/index.html`: dashboard page.
- `static/app.js`: form handling and report rendering.
- `static/styles.css`: business dashboard styling.
- `tests/test_finance.py`: unit tests for financial calculations and recommendation logic.
- `agentic.md`: AI project memory for future work sessions.

## Data Flow

1. The browser form collects property and investment assumptions.
2. The frontend sends a JSON request to `POST /api/analyze`.
3. FastAPI validates the request with Pydantic.
4. `finance.py` calculates loan, LTV, operating expenses, NOI, cash flow, break-even rent, DSCR, going-in cap rate, cash-on-cash return, 5-year and 10-year IRR, equity multiple, exit cap rate, sales costs, and projected sale proceeds.
5. `data_loader.py` loads market and policy data by ZIP code, then falls back to state or national sample data if needed.
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
```

Example:

```text
knowledge_bank/properties/725_n_delaware_st_46202/hoa_restrictions.md
```

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

The batch file will create `.venv` if needed, install requirements, run the quick tests, open the browser, and start the local server at `http://127.0.0.1:8000`.

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

## Responsible Use

NorthStar is a decision-support tool, not legal, tax, financial, or investment advice. All public data and policy summaries must be verified before a real purchase decision.
