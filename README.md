# NorthStar Property Investment Consulting

NorthStar is a local real estate investment decision-support tool. It lets a user enter a mainland U.S. property address and investment assumptions, then returns a structured investor report with financial metrics, local sample market context, policy/rental restriction warnings, risks, opportunities, and a final recommendation: **Buy**, **Investigate Further**, or **Reject**.

This local MVP does not use paid APIs or live real estate data. The sample market and policy data are stored in local JSON files so the demo is reliable. Live policy research is handled outside the app runtime by the reusable `property-policy-research` agent Skill (see below), so the demo stays fully reliable offline.

> Design Studio Project | BUKD-X500: Agentic AI Systems | Kelley School of Business
> Team 5: Ashish Nath, Justin Kretschman
> Full proposal: [Week9_DSP_NorthStar_Property_Investment_Consulting_Proposal.docx](Week9_DSP_NorthStar_Property_Investment_Consulting_Proposal.docx)

## Architecture

- `app/main.py`: FastAPI app, page routes, health endpoint, sample property endpoint, location-check endpoint, knowledge-bank endpoints, analysis endpoint.
- `app/knowledge_bank.py`: scanning, parsing, rendering, and writing knowledge-bank notes.
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
- `tests/test_data_loader.py`: unit tests for policy layering, location checks, and knowledge-bank discovery.
- `tests/test_api.py`: endpoint tests for the location check and analysis routes.
- `.claude/skills/property-policy-research/`: reusable agent Skill that researches live rental policy for an address and writes source-cited notes into `knowledge_bank/`.
- `agentic.md`: AI project memory for future work sessions.

## Data Flow

1. The browser form collects property and investment assumptions.
2. The frontend sends a JSON request to `POST /api/analyze`.
3. FastAPI validates the request with Pydantic, then `check_location_consistency` verifies that the city, state, and ZIP describe the same place using `data/zip_directory.json`. A mismatch produces a warning banner at the top of the report, a high risk entry, and counts against a confident recommendation. The same check also runs live on the form through `POST /api/location-check`, so a mismatch appears under the property fields before the user clicks Analyze.
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
knowledge_bank/global                    every property
knowledge_bank/states/STATE              any property in that state
knowledge_bank/zips/ZIP                  that ZIP
knowledge_bank/cities/city_state         that city
knowledge_bank/properties/address_zip    one specific address
```

Folders run broad to specific and are created on demand, so only folders holding a note exist. Older flat `state-zip` folders (for example `tx-78704`) are still read, so notes written by the standalone Lab 5 Skill keep working.

Example:

```text
knowledge_bank/properties/725_n_delaware_st_46202/hoa_restrictions.md
```

## The Skill Versus the Knowledge Bank

Two different things, easy to confuse:

- **`property-policy-research`** (in `.claude/skills/`) is a **Skill** — instructions an AI agent follows. It researches rental rules on the live web and **writes** notes. You run it in Claude Code, Cowork, or claude.ai.
- **`knowledge_bank/`** is a **folder of files**. The app **reads** it and never writes policy into it.

Files get in three ways — through the Skill, through the app's Knowledge Bank page, or by dropping a file in by hand. The app cannot tell them apart. See [knowledge_bank/README.md](knowledge_bank/README.md) for the full explanation.

## Traceability: the analysis trail

Every analysis appends a record to `knowledge_bank/zips/<ZIP>/_analysis-log.md` capturing the address, the recommendation, which market and policy records matched, which notes were read, and which flags fired. Open the folder for a ZIP months later and you can see exactly what produced a past recommendation.

Files beginning with `_` are written by the app and are never read back into a report, so the trail can never feed the analysis its own output. Trails are git-ignored — they are your run history, not project source.

## Knowledge Bank Page

`http://localhost:8000/knowledge-bank` is a browsable library of every policy note the project holds. It is built by scanning the folder at request time, so anything added — by the research Skill, by the in-app form, or by dropping a file in — appears immediately.

Each note shows where it applies, when it was researched, how many high-attention flags it carries, how many citations are official versus secondary, and how many diligence follow-ups it raises. Notes older than 120 days are marked stale. Clicking through renders the full note as HTML, so the official `.gov` source links are clickable instead of buried in a text dump.

The same page has an **Add a local policy note** form. Pick where the note applies (ZIP, state, city, a single property, everywhere, or a custom folder), paste the text, and save — the file is written into `knowledge_bank/` and picked up by the next analysis. See [knowledge_bank/README.md](knowledge_bank/README.md) for the optional sections that let a note raise risk flags or correct the financial model.

## Notes That Correct the Financial Model

A note may declare machine-readable limits:

```markdown
## NorthStar Machine-Readable Summary

- rent_growth_cap_percent: 0
- short_term_rental_allowed: false
```

NorthStar checks those against the assumptions entered. Analyzing the Brooklyn sample with 3% rent growth opens the report with a red panel: the Rent Guidelines Board froze stabilized leases at 0%, so the IRR and equity multiple below assume growth the law does not permit. This is the knowledge bank reaching into the deterministic model rather than sitting beside it as commentary.

Notes also feed a **Diligence Checklist** in the report, built from their "unverified / confirm with / obtain" lines, each labeled with the note it came from.

## Bundled Researched Policy Notes

Three notes produced by the research Skill ship with the project and are read automatically when the matching property is analyzed:

| Note | Market | Why it is interesting |
|---|---|---|
| `knowledge_bank/zips/78704/policy-notes.md` | Austin, TX | STR legal with a license; no rent control statewide |
| `knowledge_bank/zips/90026/policy-notes.md` | Los Angeles, CA | STR effectively banned for investors; two overlapping rent-control regimes |
| `knowledge_bank/zips/11215/policy-notes.md` | Brooklyn, NY | STR blocked by Local Law 18; rent freeze adopted for stabilized units |

Each note ends with a `| Flag | Severity | Why |` table. NorthStar parses that table and feeds the findings into the report: the flags appear in **Policy Restrictions and Sources** tagged with the researched jurisdiction, every HIGH flag becomes a risk entry naming its source file, and a HIGH flag raises the overall policy risk, which can change the recommendation. Los Angeles and Brooklyn have no built-in sample policy record at all, so those reports are driven entirely by the researched notes — which is the knowledge bank doing exactly the job the proposal describes.

Use the "Load sample" menu to try them: the Los Angeles and Brooklyn samples both surface researched policy findings.

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
