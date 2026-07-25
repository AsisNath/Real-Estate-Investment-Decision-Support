# NorthStar Property Investment Consulting - AI Project Memory

## Project Goal
Build a local web app that acts as a first-pass real estate investment consultant. The user enters a mainland U.S. property address and investment assumptions, and the app returns a financial, market, policy, risk, opportunity, and recommendation report.

## Current Architecture
The app uses a FastAPI backend with a vanilla HTML/CSS/JavaScript frontend.

- Frontend: `templates/index.html`, `static/app.js`, `static/styles.css`
- Backend API: `app/main.py`
- Input validation: `app/schemas.py`
- Deterministic financial model: `app/finance.py`
- Report assembly and rule-based risk/opportunity analysis: `app/analysis.py`
- Local data loading and fallback logic: `app/data_loader.py`
- Sample data: `data/market_data.json`, `data/policy_data.json`, `data/sample_properties.json`
- Tests: `tests/test_finance.py`

Data flow: browser form -> `POST /api/analyze` -> Pydantic validation -> financial calculations -> local market/policy lookup -> report assembly -> browser report rendering.

## Key Decisions
- No paid APIs or scraping in the MVP.
- Financial calculations are deterministic Python functions, not LLM-generated math.
- Local JSON data is used for reliable demos.
- Missing ZIP-level data falls back to state or national sample records and creates visible missing-data flags.
- Final recommendation uses transparent rules: Buy, Investigate Further, or Reject.
- Policy review now displays source links and high-attention restriction flags from `data/policy_data.json`.
- The app reads local `.md` and `.txt` notes from `knowledge_bank` as a manual fallback for HOA, local law, lease, lender, and rental-policy documents.

## Data Assumptions
Market and policy data are sample records, not live verified data. They are structured to mimic public-data fields and can be replaced later with API or document-based sources. HOA, condo, deed, and address-specific rental restrictions are treated as missing unless uploaded or manually verified in a future version.

The current app does not perform live web research at request time. Instead, policy records contain official/public read-more links, and the knowledge bank lets the user add local policy documents manually. A future version can replace this with live retrieval and document upload.

## Financial Model Notes
The model calculates loan amount, amortized monthly mortgage payment, operating expenses, NOI, monthly and annual cash flow, going-in cap rate, cash-on-cash return, break-even rent, DSCR, projected sale value, loan payoff, net sale proceeds, LTV, sales costs, 5-year and 10-year IRR, equity multiple, final-year NOI, and exit cap rate.

Base operating expenses include property tax, insurance, HOA, maintenance, vacancy, and property management. Maintenance can be modeled as a percentage of rent or as a fixed monthly amount.

## Current Status
Initial MVP files have been created. The app structure, backend modules, sample data, frontend dashboard, README, tests, and one-click batch runner are in place. Dependencies were installed in the workspace virtual environment, the finance test suite passes, and the app has been verified at `http://127.0.0.1:8000`.

The completed app files were copied into:

`C:\Users\natha\Documents\Kelley\MUKD_X500_AI\NorthStar Property Investment Consulting`

Recent UI update: removed school-demo wording from the user-facing app and color-coded input sections. Required property fields use blue styling, purchase/financing assumptions use green styling, and expense/growth assumptions use amber styling.

Recent policy update: added official/public source links, high-attention policy flags, and a `knowledge_bank` folder reader. The policy report now tells users where to place manual HOA/local-law files until upload is added.

Recent finance update: added investor-facing LTV, equity multiple, growth/inflation assumptions, sales-cost detail, holding-period outputs, final-year NOI, and exit cap-rate metrics to the API and report UI.

Recent proposal update: created `NorthStar_Property_Investment_Consulting_Proposal_2_Page_Revised.docx`, a tighter two-page proposal that incorporates the working website, one-click runner, deterministic finance model, expanded investor metrics, policy source links, and knowledge-bank fallback.

Latest proposal update: created `NorthStar_Property_Investment_Consulting_Proposal_AI_Future_Revised.docx`, which adds a clearer "Where AI Helps" section, maps AI contribution by platform/tool, and lists future extensions including hosting the website online, secure document upload, live public-data retrieval, AI document Q&A, scenario comparison, and multi-property comparison.

Knowledge-bank reorganization and traceability (2026-07-25): the folder held two competing layouts for the same scope - the app's `zips/78704/` hierarchy and the Skill's flat `tx-78704/` - plus eleven placeholder README.md files the loader always skipped (16 files, 3 of which were real). Consolidated onto the single broad-to-specific hierarchy: the three notes moved to `zips/78704`, `zips/90026`, `zips/11215`, placeholders deleted, empty folders removed. The loader still accepts flat `<state>-<zip>` folders so older Skill output keeps working. The project's copy of SKILL.md now writes to `zips/<zip>/`; the Lab 5 submitted copy is unchanged.

Added an analysis trail for traceability: every analysis appends to `knowledge_bank/zips/<ZIP>/_analysis-log.md` recording address, recommendation, which market and policy records matched, which notes were read, the address check, flags applied, and assumption conflicts. Files prefixed `_` are app-written and excluded from note parsing in both `data_loader` and `scan_knowledge_bank` - without that, the trail would feed the report its own past output (a bug the tests caught). Trails are surfaced in a separate "Analysis trail" section on the Knowledge Bank page via `GET /api/knowledge-bank/trace`, capped at 40 entries, git-ignored, and `record_analysis` never raises so a failed write cannot break an analysis. `tests/test_api.py` patches out `record_analysis` so API tests do not write into the real folder.

Knowledge bank as a first-class feature (2026-07-25): added `app/knowledge_bank.py` (scan, parse, render, write) and a `/knowledge-bank` page. The page is built by scanning the folder at request time, so it is fully dynamic - anything the Skill writes, the user adds through the form, or drops in by hand shows up immediately. Per note it reports scope, research date and staleness (over 120 days), flag counts by severity, official-vs-secondary citation counts, and diligence count, and renders the full note as HTML so official source links are clickable (`markdown` is an optional dependency with a preformatted-text fallback).

Users can add notes from inside the app: `POST /api/knowledge-bank/notes` with a scope (zip/state/city/property/global/custom) that builds the folder path. Writes are guarded by `safe_note_path`, which refuses `..`, drive letters, and absolute paths rather than silently reinterpreting them, and confirms the resolved path stays inside `knowledge_bank/`. Existing files are never overwritten without an explicit flag (409 otherwise).

Notes can now correct the financial model. A note may declare a `## NorthStar Machine-Readable Summary` section with `rent_growth_cap_percent` and `short_term_rental_allowed`; `build_assumption_conflicts` in `analysis.py` compares those to the entered assumptions and raises a high-severity conflict (shown above the recommendation, counted against it) when rent growth exceeds the local legal cap. The three bundled notes carry blocks summarizing facts they already cite: Austin uncapped, LA 4% (RSO formula), Brooklyn 0% (RGB freeze). Notes also feed a Diligence Checklist built from their unverified/confirm/obtain lines.

Lab 5 knowledge-bank integration (2026-07-25): brought the three researched policy notes from `M8\Lab5\knowledge_bank` into this project (`tx-78704`, `ca-90026`, `ny-11215`) and made them drive the report instead of only displaying as text. `parse_policy_note` in `data_loader.py` extracts the heading, the "Researched:" date, and the `| Flag | Severity | Why |` table that the Skill always writes; severities map HIGH/MEDIUM/LOW/INFO to the app's high/medium/low. `load_knowledge_bank_context` returns these as `researched_flags`, and `build_report` merges them into the policy restriction flags (tagged with the researched jurisdiction), promotes every HIGH flag to a risk naming its source file, and raises the policy risk level to high, which can flip the recommendation. When researched notes exist, the national-fallback placeholder flag ("Local law not resolved - add notes to the knowledge bank") is dropped and the missing-data message explains that findings come from the notes. Added ZIPs 90026 and 11215 to `zip_directory.json` and Los Angeles/Brooklyn sample properties. The Lab 5 Skill files were byte-identical to the project copy, so nothing was overwritten. `SUBMISSION-NOTES` and the LA HTML brief were left in Lab5 as coursework artifacts.

Inline form validation (2026-07-25): the location check also runs while the user fills the form. `POST /api/location-check` (schema `LocationCheckRequest`, deliberately loose so blanks and malformed input report rather than 500) is called on change/blur of the city, state, and ZIP fields, on sample load, and at page load. The result renders in `#locationNotice` inside the property fieldset - red for a mismatch, amber for unverified, hidden when the address is consistent. The check waits until all three fields are filled so it does not nag mid-typing, and a failed request never blocks the form.

Location consistency check (2026-07-25): added `data/zip_directory.json` (a small ZIP-to-place directory for the sample markets plus a full mainland ZIP-prefix-to-state table) and `check_location_consistency` in `data_loader.py`. If the city, state, and ZIP do not describe the same place, the report shows a red banner at the top, adds a high "Address Fields Do Not Match" risk, and counts the mismatch against a confident recommendation. Checks that cannot be made (unlisted ZIP or prefix) are reported as `unverified` rather than passing silently, so the tool never implies it confirmed something it did not. The prefix table is deliberately fail-open: unassigned prefixes produce no warning.

Wrong-city policy fix (2026-07-25): searching ZIP 63301 (Saint Charles, MO) fell back to the Missouri state record, which carried a "St. Louis STR permits example" link, so the report appeared to show St. Louis rules for a Saint Charles property. City-specific example links in state fallback records now carry an `applies_to_city` tag and are filtered out unless the analyzed city matches. Matching normalizes "Saint" to "St." so "Saint Louis", "St. Louis", and "st louis" are treated as the same city. `load_policy_context` takes a `city` argument (passed from the request in `main.py`), and the state-fallback missing-data message now names the actual city, e.g. "No city or county policy record was found for Saint Charles, MO. The rules below are MO state-level only."

Jurisdiction layering update (2026-07-25): the Policy Restrictions and Sources section now covers every matching jurisdiction level instead of a single record. `load_policy_context` merges the ZIP-level (city/county) record with the state record (deduplicating repeated links by URL+category and skipping state "local rules unresolved" flags marked `fallback_only` when the ZIP record already resolved them). Every restriction flag and source link in `data/policy_data.json` carries a `jurisdiction` label (e.g. "City of Austin", "State of Texas", "HOA / private documents"). The report groups source links under jurisdiction headings, shows the jurisdiction on each flag, and lists "Jurisdictions reviewed" in the Policy Review panel.

Week 9 proposal update (2026-07-25): aligned the project with `Week9_DSP_NorthStar_Property_Investment_Consulting_Proposal.docx`. The `property-policy-research` agent Skill is now bundled in the repo at `.claude/skills/property-policy-research/` (it researches STR permits, landlord-tenant law, rent control, and HOA restrictions via live web search and writes dated, source-cited notes into `knowledge_bank/<state>-<zip>/`). `data_loader.py` now also searches the Skill's output folders (`knowledge_bank/state-zip` and `knowledge_bank/state-city_slug`) so generated notes appear in the report, with new tests in `tests/test_data_loader.py`. README and knowledge_bank docs were updated to document the Skill workflow. The project was published to GitHub: https://github.com/AsisNath/Real-Estate-Investment-Decision-Support

## Known Issues
FastAPI and pytest may need to be installed in any new local Python environment with `pip install -r requirements.txt`. The current data is sample data, so all market and policy findings should be verified before use.

## Next Steps
- Open `http://localhost:8000` and test the sample properties.
- For future work, create a dedicated virtual environment inside the class project folder or reuse an existing environment with the installed requirements.
- Add document upload for HOA/rental restriction files in a later iteration.
- Add live web retrieval or an LLM policy-research step in a later iteration if internet/API access is available.

## Run Instructions
Double-click `Run_NorthStar.bat`, or run manually:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open `http://localhost:8000`.
