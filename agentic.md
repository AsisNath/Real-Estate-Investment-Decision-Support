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
- `tests/` - 90 tests in 6 files
- `Run_NorthStar.bat` / `Clean_NorthStar.bat` - one-click launch and one-click cleanup
- `AGENTS.md` - the spec this file must satisfy; `Project_Prompt.md` - the original build brief (both were `.md.txt` until the user renamed them)

Flow: form -> `POST /api/analyze` -> Pydantic -> address check -> finance -> market/policy lookup -> knowledge-bank read -> report assembly -> analysis trail written -> browser render.

## Key Decisions

- **No paid APIs or scraping at analysis time.** The app is offline and deterministic; live research happens outside it through the agent Skill. This is a proposal commitment, not an accident - do not "improve" it by adding runtime web calls without discussing it.
- **Financial math is plain Python, never LLM-generated**, and is unit-tested so every number is auditable.
- **Missing data is stated, never guessed.** ZIP-level misses fall back to state, then national, and say so. Checks that cannot be performed are reported as `unverified` rather than passing silently.
- **The recommendation is rule-based and transparent**, with its reasons listed.
- **Provenance is a structural guarantee, not a label.** `knowledge_bank/researched/` is writable only by the Skill and `knowledge_bank/user/` only by people, enforced in code rather than by convention - see the next section. Legacy flat `<state>-<zip>/` folders are still read so notes from the standalone Lab 5 Skill keep working.

## How the knowledge bank works

Two roots, same taxonomy (`global/states/zips/cities/properties`): `knowledge_bank/researched/` is written only by the Skill; `knowledge_bank/user/` is written by the in-app form or by hand. `build_folder` in `app/knowledge_bank.py` always prepends `user/` (there is no "researched" scope choice in the form anymore - removed when this split landed), and `create_note` separately refuses any folder starting with `researched/` even if a caller tries to set `payload.folder` directly, so the trust boundary holds regardless of entry point. `describe_source` tags every note/document with `researched`, `user`, or `legacy` (old flat `<state>-<zip>/` folders, still read for compatibility). `data_loader.load_knowledge_bank_context` searches both roots at every specificity tier (broadest to most specific), interleaved per tier so a more specific folder always outranks a broader one regardless of which root it's in.

`property-policy-research` (the Skill, in `.claude/skills/`) **writes** notes; the app only **reads** them. Notes also arrive from the in-app form (`POST /api/knowledge-bank/notes`) or by hand - the app cannot tell the difference beyond the root tag. The Skill cannot run inside the app itself: it needs an LLM agent loop with live web search, a different runtime than this deterministic FastAPI process, and calling out to one at request time would break the proposal's offline MVP commitment. What the app does instead: `build_research_request` in `analysis.py` builds a ready-to-paste command from the address already on the form (`"Run policy diligence on {address}, {city}, {state} {zip}."`) and returns it as `report["research_request"]` with a `status` of `missing` (no note at all), `stale` (note exists but older than 120 days), or `current` (skip the panel). The frontend renders it with a copy-to-clipboard button in `researchRequestPanel` (`static/app.js`) only for `missing`/`stale`.

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
- **Folder casing under `knowledge_bank/user/` is not a bug.** The loader searches lowercase `user/zips/`, the user's folder is `user/Zips/`, and it resolves fine because this project is Windows-only. Verified end to end, not assumed. Leave it alone.
- **`rmdir /s /q` on Windows can partially delete on a locked file, not abort cleanly.** Reproduced directly: with one file inside `.venv` locked, `rmdir /s /q ".venv"` removed `pyvenv.cfg` and `Lib` but left the locked file and its parent folder - producing a `.venv` with `Scripts\python.exe` present but `pyvenv.cfg` missing. This exact shape broke a real user's install, because `Run_NorthStar.bat` only checked for `python.exe`. Fixed in two places: `Run_NorthStar.bat` now also requires `pyvenv.cfg` and rebuilds if either is missing (self-heals regardless of *why* `.venv` got corrupted), and `Clean_NorthStar.bat` checks whether its own `rmdir` fully succeeded and warns instead of leaving a silent partial state. Any future script that deletes a multi-file directory on Windows must assume partial failure is possible and verify afterward - never assume `rmdir`/`Remove-Item` is atomic.
- **Do not let a cleanup/maintenance script recurse into `.venv`.** `Clean_NorthStar.bat` originally did a broad `Get-ChildItem -Recurse` for `__pycache__` from the project root, which also swept through every installed package inside `.venv\Lib\site-packages`. Harmless by itself, but unnecessary surface area for exactly the kind of interaction above. Rewritten to touch only an explicit allowlist (`app\__pycache__`, `tests\__pycache__`, `.pytest_cache`) - never a recursive scan of the whole tree.

## Data Assumptions

Market and policy records in `data/` are sample data shaped like public-data fields, not verified facts. Address-specific HOA, condo, and deed restrictions are treated as unknown unless a knowledge-bank note supplies them. `zip_directory.json` holds a small place directory plus a mainland ZIP-prefix-to-state table; unassigned prefixes deliberately produce no warning (fail open) rather than a false alarm. Notes in `knowledge_bank/` may be researched (Skill-generated, source-cited), user-provided, or a mix. The app *does* distinguish provenance - `describe_source` tags every note `researched`, `user`, or `legacy` from its root folder, and both the report and the Knowledge Bank page display that tag. Within a researched note, the note's own per-fact ✅ official / ⚠ secondary markers remain the finer-grained trust signal.

## Financial Model Notes

Loan amount, amortized payment, operating expenses, NOI, monthly and annual cash flow, going-in cap rate, cash-on-cash return, break-even rent, DSCR, projected sale value, loan payoff, net sale proceeds, LTV, sales costs, 5- and 10-year IRR, equity multiple, final-year NOI, exit cap rate. Operating expenses cover property tax, insurance, HOA, maintenance, vacancy, and management; maintenance is either a percentage of rent or a fixed monthly amount.

## Current Status

Complete and working. All 90 tests pass. The app has been verified in a browser end to end: analysis, the address-mismatch warnings, the Knowledge Bank page, adding a note through the form and watching it change that property's report, and the analysis trail.

Bundled researched notes cover Austin (78704), Los Angeles (90026), and Brooklyn (11215), all in `knowledge_bank/researched/`. Los Angeles and Brooklyn have no built-in policy record, so those reports are driven entirely by the notes.

The user's own Saint Charles, MO 63301 research (real property they're evaluating) is written locally at `knowledge_bank/researched/zips/63301/policy-notes.md` but deliberately kept out of git - the repo is public, and that note is tied to a real address and a recorded HOA document at `knowledge_bank/user/Zips/63301/HOA_852771.pdf`. Both files are untracked and stay local-only unless the user asks to publish them.

The user's folder naming is deliberate and verified working. `user/Zips/` reads correctly despite the loader searching `user/zips/`, because this is a Windows-only project (both launchers are `.bat`) and NTFS is case-insensitive - confirmed empirically by dropping a note in `user/Zips/63301/` and watching the loader return it tagged `source=user`. Do not "fix" this casing.

One structural note that is *not* about casing: `record_analysis` writes trails to `knowledge_bank/zips/<ZIP>/_analysis-log.md` - a top-level `zips/` outside both roots. The user has since organized their own files under `user/Zips/`, so the next analysis will create a separate top-level `knowledge_bank/zips/` rather than appending under `user/`. The empty `user/Zips/{11215,46202,78704,90026}` folders are leftovers from trails that `Clean_NorthStar.bat` removed. If the trail location should move under `user/`, that is a one-line change in `record_analysis` plus its tests - ask before changing it.

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

1. **Documentation audit across every markdown file** - rewrote `README.md` against the actual source (the test count had drifted to 80 vs. the real 90; no top-level file except the app modules was documented; the analysis-trail location was missing from the folder diagram) and added a project tree, table of contents, and per-file test table. Then audited the rest: fixed the same stale count here, removed a direct contradiction in Data Assumptions (it claimed the app cannot distinguish note provenance, while How the knowledge bank works correctly described `describe_source` doing exactly that), corrected the HOA PDF path after the user moved it, and fixed four places where the bundled Skill's `README.md` still documented the pre-split `knowledge_bank/zips/<zip>/` output path while its own `SKILL.md` correctly said `researched/zips/<zip>/`. Also recorded the user's `.md.txt` -> `.md` renames of `AGENTS.md` and `Project_Prompt.md` in git.
2. **Fixed a real incident: Clean_NorthStar.bat's .venv removal could corrupt .venv, breaking Run_NorthStar.bat** - a user reported "after cleaning, I can't Run_NorthStar" after choosing to also remove `.venv`. Root cause, confirmed by reproduction: `rmdir /s /q` on Windows can partially delete when a file is locked (removed `pyvenv.cfg` and `Lib`, left `Scripts\python.exe`), and `Run_NorthStar.bat` only checked for `python.exe`, so it used the broken environment instead of rebuilding it. Fixed both sides: `Run_NorthStar.bat` now also requires `pyvenv.cfg` and self-heals regardless of cause; `Clean_NorthStar.bat` verifies its own removal succeeded and warns instead of leaving a silent partial state, and its cache cleanup no longer recurses into `.venv` at all (explicit allowlist only). See Traps.
3. **Added Clean_NorthStar.bat for clearing generated files** - see the entry above for the fix that followed; original version removed Python cache and analysis trail logs after confirmation, with `.venv` removal as a separate optional step.
4. **Split the knowledge bank into researched/ vs. user/ roots** - the user asked for a real trust boundary between AI-verified and human-typed notes. `researched/` is written only by the Skill (SKILL.md updated to match); `user/` is written by the in-app form (the old "researched"-style scope choice was removed from the form entirely) or by hand. `create_note` refuses to write into `researched/` even via a direct `folder` override. The three bundled sample notes moved to `researched/zips/{78704,90026,11215}/`. Also actually ran the Skill (via the Skill tool, with my own web search - no new API key needed) for the user's real address, cross-referencing a recorded HOA Master Indenture PDF they had on file; wrote the result to `researched/zips/63301/` but kept it and the PDF out of git since the repo is public.
5. **README/agentic.md realignment + the research-request panel** - rewrote README.md and agentic.md end to end (they had drifted from the code and from each other by accretion), added a Mermaid flow diagram of the whole project, and closed a real gap the user found: since the app already has the address, `build_research_request` now hands the user a ready-to-paste Skill command instead of making them retype it, shown only when a note is missing or stale.
6. **Knowledge-bank reorganization and traceability** - the folder had two competing layouts for the same scope (`zips/78704/` and flat `tx-78704/`) plus eleven placeholder READMEs the loader always skipped; consolidated to one hierarchy, added the per-ZIP analysis trail, and updated the project's `SKILL.md` to write into `zips/<zip>/` (the Lab 5 submitted copy is unchanged).
7. **Knowledge bank as a first-class feature** - added `app/knowledge_bank.py`, the `/knowledge-bank` page, in-app note creation, HTML rendering of notes, staleness and citation counts, the machine-readable limits that correct the financial model, and the diligence checklist.
8. **Lab 5 integration** - brought the three researched notes into the project and made their flag tables drive the report instead of displaying as text.
9. **Static asset cache-busting** - `?v=<mtime>` so a cached `app.js` cannot make fixed code look broken.
10. **Inline address validation** - the location check also runs on the form via `POST /api/location-check`.
11. **Launcher clears port 8000** - stops a stale NorthStar server before starting, warns instead of killing anything that is not one.
12. **Location consistency check** - `zip_directory.json` plus `check_location_consistency`; mismatches warn on the form, above the recommendation, and as a high risk.
13. **Wrong-city policy fix** - a Saint Charles ZIP falling back to Missouri state data was showing a St. Louis example link; city-specific links now carry `applies_to_city` and are filtered unless the city matches.
14. **Jurisdiction layering** - policy output merges city/county, state, and national records instead of picking one, with every flag and link tagged by jurisdiction.
15. **Week 9 proposal alignment** - bundled the Skill into the repo and wired its output folders into the loader.

## Run instructions

Double-click `Run_NorthStar.bat`, or:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open `http://localhost:8000`. Run tests with `pytest`.
