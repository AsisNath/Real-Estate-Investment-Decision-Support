# NorthStar Property Investment Consulting - AI Project Memory

Working notes for future AI sessions. The user-facing documentation is [README.md](README.md); this file records *why* things are the way they are, and the traps.

## Project Goal

A local web app that acts as a first-pass real estate investment consultant. The user enters a U.S. property address and investment assumptions; the app returns financial, market, policy, risk, opportunity, and recommendation output (Buy / Investigate Further / Reject).

Design Studio project for BUKD-X500, Kelley School of Business. Team 5: Ashish Nath, Justin Kretschman. Published at https://github.com/AsisNath/Real-Estate-Investment-Decision-Support (commit 1 is the untouched original code, so later commits show exactly what changed).

## Current Architecture

FastAPI backend, vanilla HTML/CSS/JS frontend, no build step.

- `app/main.py` - routes and the JSON API
- `app/schemas.py` - Pydantic validation
- `app/finance.py` - deterministic financial model
- `app/data_loader.py` - JSON loading, jurisdiction layering, address checks, knowledge-bank discovery
- `app/knowledge_bank.py` - note parsing, rendering, scanning, writing, analysis trail
- `app/analysis.py` - report assembly, risks, assumption conflicts
- `data/` - market, policy, sample properties, `zip_directory.json`
- `knowledge_bank/` - local policy library (see its README)
- `templates/` + `static/` - analysis page and Knowledge Bank page
- `tests/` - 80 tests in 6 files

Flow: form -> `POST /api/analyze` -> Pydantic -> address check -> finance -> market/policy lookup -> knowledge-bank read -> report assembly -> analysis trail written -> browser render.

## Key Decisions

- **No paid APIs or scraping at analysis time.** The app is offline and deterministic; live research happens outside it through the agent Skill. This is a proposal commitment, not an accident - do not "improve" it by adding runtime web calls without discussing it.
- **Financial math is plain Python, never LLM-generated**, and is unit-tested so every number is auditable.
- **Missing data is stated, never guessed.** ZIP-level misses fall back to state, then national, and say so. Checks that cannot be performed are reported as `unverified` rather than passing silently.
- **The recommendation is rule-based and transparent**, with its reasons listed.
- **Two conventions are supported for knowledge-bank ZIP folders.** `zips/<ZIP>/` is canonical; flat `<state>-<zip>/` is still read so notes from the standalone Lab 5 Skill keep working.

## How the knowledge bank works

`property-policy-research` (the Skill, in `.claude/skills/`) **writes** notes; the app only **reads** them. Notes also arrive from the in-app form (`POST /api/knowledge-bank/notes`) or by hand - the app cannot tell the difference.

`parse_policy_note` in `app/knowledge_bank.py` pulls structure out of a note: heading, `**Researched:**` date and staleness (over 120 days), the `| Flag | Severity | Why |` table, a `## NorthStar Machine-Readable Summary` key/value block, diligence lines (containing "unverified", "confirm with", "obtain"), and counts of official versus secondary citations. Notes lacking any of that still display; they just contribute less.

Downstream:
- Flags join the policy restriction flags, tagged with the researched jurisdiction. Any HIGH flag becomes a risk naming its source file and raises the policy risk level, which can flip the recommendation.
- `build_assumption_conflicts` in `analysis.py` compares declared limits (`rent_growth_cap_percent`, `short_term_rental_allowed`) against the entered assumptions and raises a high-severity conflict above the recommendation.
- Diligence lines become the report's checklist.

Writes are guarded by `safe_note_path`: `..`, drive letters, and absolute paths are refused rather than reinterpreted, and the resolved path must stay inside `knowledge_bank/`. Existing files are never overwritten without an explicit flag (409 otherwise).

**Analysis trail.** Each analysis appends to `knowledge_bank/zips/<ZIP>/_analysis-log.md`: address, recommendation, which records matched, which notes were read, flags applied, conflicts. Capped at 40 entries, git-ignored, and `record_analysis` never raises so a failed write cannot break an analysis.

## Traps

- **A stale server is the single most common source of "your fix didn't work."** A running uvicorn process keeps the code *and* the JSON it loaded at startup. `Run_NorthStar.bat` now clears port 8000 before starting, and `index.html` loads static assets with a `?v=<mtime>` cache-buster. Check `Get-NetTCPConnection -LocalPort 8000` and the process start time before debugging anything else.
- **Files prefixed `_` must never be parsed as notes.** Both `data_loader.load_knowledge_bank_context` and `knowledge_bank.scan_knowledge_bank` filter them. Without that filter the analysis trail is read back as policy and the report feeds on its own past output.
- **`tests/test_api.py` patches out `record_analysis`.** Otherwise running the suite writes trail files into the real `knowledge_bank/`.
- `markdown` is an optional dependency; `render_markdown` falls back to escaped preformatted text if it is missing, so the app must never assume it is installed.
- City matching normalizes "Saint" to "St." - do not compare city names raw.

## Data Assumptions

Market and policy records in `data/` are sample data shaped like public-data fields, not verified facts. Address-specific HOA, condo, and deed restrictions are treated as unknown unless a knowledge-bank note supplies them. `zip_directory.json` holds a small place directory plus a mainland ZIP-prefix-to-state table; unassigned prefixes deliberately produce no warning (fail open) rather than a false alarm. Notes in `knowledge_bank/` may be researched (Skill-generated, source-cited), user-provided, or a mix; the app does not distinguish provenance, so a note's own citations are the only trust signal.

## Financial Model Notes

Loan amount, amortized payment, operating expenses, NOI, monthly and annual cash flow, going-in cap rate, cash-on-cash return, break-even rent, DSCR, projected sale value, loan payoff, net sale proceeds, LTV, sales costs, 5- and 10-year IRR, equity multiple, final-year NOI, exit cap rate. Operating expenses cover property tax, insurance, HOA, maintenance, vacancy, and management; maintenance is either a percentage of rent or a fixed monthly amount.

## Current Status

Complete and working. All 80 tests pass. The app has been verified in a browser end to end: analysis, the address-mismatch warnings, the Knowledge Bank page, adding a note through the form and watching it change that property's report, and the analysis trail.

Bundled researched notes cover Austin (78704), Los Angeles (90026), and Brooklyn (11215). Los Angeles and Brooklyn have no built-in policy record, so those reports are driven entirely by the notes.

## Known Issues

- Sample market and policy data in `data/` is illustrative, not verified public data - it must not be relied on for a real purchase decision.
- No authentication or multi-user support; the app assumes a single local user, matching the MVP scope in the proposal.
- The research Skill must be run manually in a separate agent session; the app cannot trigger live research itself by design (see Key Decisions).
- `markdown` (the optional rendering dependency) must be installed via `requirements.txt` for notes to render as HTML; without it, notes still display, just as preformatted text.

## Next Steps

- Proposal future extensions not yet built: hosted deployment, real document upload (PDF/scanned HOA docs) with AI-assisted Q&A, live paid-API market/tax data, scenario comparison, multi-property comparison.
- Consider letting the Knowledge Bank page edit or delete an existing note, not just add new ones.
- Consider expanding `zip_directory.json` beyond the five sample-market ZIPs plus the three researched ZIPs, if more demo markets are added.

## Change Log

Newest first. Each entry is one commit on `main`.

1. **Knowledge-bank reorganization and traceability** - the folder had two competing layouts for the same scope (`zips/78704/` and flat `tx-78704/`) plus eleven placeholder READMEs the loader always skipped; consolidated to one hierarchy, added the per-ZIP analysis trail, and updated the project's `SKILL.md` to write into `zips/<zip>/` (the Lab 5 submitted copy is unchanged).
2. **Knowledge bank as a first-class feature** - added `app/knowledge_bank.py`, the `/knowledge-bank` page, in-app note creation, HTML rendering of notes, staleness and citation counts, the machine-readable limits that correct the financial model, and the diligence checklist.
3. **Lab 5 integration** - brought the three researched notes into the project and made their flag tables drive the report instead of displaying as text.
4. **Static asset cache-busting** - `?v=<mtime>` so a cached `app.js` cannot make fixed code look broken.
5. **Inline address validation** - the location check also runs on the form via `POST /api/location-check`.
6. **Launcher clears port 8000** - stops a stale NorthStar server before starting, warns instead of killing anything that is not one.
7. **Location consistency check** - `zip_directory.json` plus `check_location_consistency`; mismatches warn on the form, above the recommendation, and as a high risk.
8. **Wrong-city policy fix** - a Saint Charles ZIP falling back to Missouri state data was showing a St. Louis example link; city-specific links now carry `applies_to_city` and are filtered unless the city matches.
9. **Jurisdiction layering** - policy output merges city/county, state, and national records instead of picking one, with every flag and link tagged by jurisdiction.
10. **Week 9 proposal alignment** - bundled the Skill into the repo and wired its output folders into the loader.

## Run instructions

Double-click `Run_NorthStar.bat`, or:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open `http://localhost:8000`. Run tests with `pytest`.
