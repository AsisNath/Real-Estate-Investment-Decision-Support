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
