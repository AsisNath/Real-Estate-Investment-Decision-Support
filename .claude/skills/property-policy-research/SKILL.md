---
name: property-policy-research
description: >
  Research current local rental regulations for a specific U.S. property address —
  short-term rental (STR) permit rules, state landlord-tenant law, rent control
  status, and HOA rental restrictions — using live web search, then save structured,
  source-cited findings into the knowledge_bank folder. Use this skill whenever the
  user provides a property address (or city/state/ZIP) and asks for policy research,
  a policy brief, rental rule lookup, HOA restriction check, STR legality check, or
  wants the knowledge_bank populated for a property under evaluation. Also trigger
  on phrases like "can I Airbnb this property," "what are the rental rules in
  [city]," or "run policy diligence on [address]."
---

# Property Policy Research

Research the regulatory environment for a residential rental property and produce
a structured, investor-readable policy note. The output feeds the NorthStar
Property Investment Consulting app's `knowledge_bank/` layer and its report's
high-attention risk flags. The audience is an individual investor doing first-pass
due diligence: they need to know what is *confirmed*, what is *unverified*, and
what could *kill the deal* — not a wall of legal prose.

## Tool requirement (non-negotiable)

**Use web search for every regulatory fact. Never answer from memory.** Rental
regulations vary by city, county, and even subdivision, and they change frequently
(Austin, for example, switched from one-year to two-year STR licenses in October
2025 and began platform delisting enforcement on July 1, 2026). A fact recalled
from training data may be years stale. If web search is unavailable, stop and say
so — do not produce a policy note from memory.

## Workflow

### Step 1: Parse the address

Extract: street, city, county (search for it if not given), state, ZIP. If the
user names an HOA or subdivision, record it. If only a city/state is given,
proceed at city/state level and say so in the output.

### Step 2: Search each policy topic separately

Run distinct web searches per topic — a single combined search buries the
specifics. Minimum set (see `references/policy-topics.md` for query patterns):

1. **STR rules:** "[city] [state] short-term rental ordinance permit requirements [year]"
2. **Landlord–tenant law:** "[state] landlord tenant law security deposit return deadline notice"
3. **Rent control:** "[state] rent control law" AND "[city] rent stabilization ordinance"
4. **HOA restrictions:** "[state] HOA authority restrict rentals leasing" plus
   "[HOA name] rental restrictions" if an HOA is named

### Step 3: Verify against official sources

This is the most important step. Search results are dominated by property-management
blogs and STR-industry marketing pages, which are frequently stale or wrong.

- For every load-bearing fact (fee amounts, deadlines, license terms, statute
  citations), open or fetch the **official source**: city .gov page, state statute
  site, or state law library. Prefer it over any aggregator.
- **When an official source and a third-party guide disagree, the official source
  wins** — and note the discrepancy in the output so the reader knows stale info
  is circulating.
- Tag every fact: ✅ official (source is .gov/statute) or ⚠ secondary (blog,
  aggregator, industry site — "confirm with authority" note required).
- **If an official site blocks automated access** (403/bot-wall — common on city
  housing pages), do not silently fall back to a blog as if it were verified.
  Keep the fact, tag it ⚠ secondary, state in the Method line that the official
  page was unreachable, and add a "confirm with [agency] directly" note. If the
  fact is load-bearing (a rent cap, a ban), also raise it to at least MEDIUM in
  the High-Attention Flags table.

### Step 4: Classify and flag

Sort findings into the five fixed sections of the Output Format. Anything that
could materially change the investment decision gets a HIGH flag: STR bans or
active enforcement regimes, rent caps, HOA rental restrictions, pending ordinance
changes with near-term effective dates.

### Step 5: Save the file

Write to: `knowledge_bank/researched/zips/<zip>/policy-notes.md` (e.g.
`knowledge_bank/researched/zips/78704/policy-notes.md`). Create the folder if
needed. If only a city/state was given, use
`knowledge_bank/researched/cities/<city-slug>_<state>/` (e.g.
`knowledge_bank/researched/cities/austin_tx/`). Always record the state and
county in the note's heading, since the folder name carries only the ZIP.

**Always write under `researched/`, never under `user/`.** NorthStar treats
`knowledge_bank/researched/` as the folder only this Skill writes to — that is
what makes a note there trustworthy as AI-verified rather than a note anyone
could have typed. `knowledge_bank/user/` is reserved for notes added by a
person (through the app's form or by hand); this Skill must never write there.

Within `researched/`, folders run broad to specific: `global/`, `states/<ST>/`,
`zips/<ZIP>/`, `cities/<city_state>/`, `properties/<address_zip>/`. NorthStar
still reads older flat `<state>-<zip>/` folders from before this structure
existed, so any pre-existing notes keep working, but always write new notes
under `researched/` going forward.

Never write a file whose name starts with an underscore: NorthStar reserves that
prefix for its own analysis trail files.

### Step 5b: Include a machine-readable summary when the facts allow it

If the research produced a clear numeric or yes/no answer for any of these,
add a `## NorthStar Machine-Readable Summary` section as the last section of
the note, so NorthStar's report can check an investor's own assumptions
against it automatically:

```markdown
## NorthStar Machine-Readable Summary

- rent_growth_cap_percent: 3
- short_term_rental_allowed: false
- security_deposit_cap_months: 1
```

Use `none` for a key with no applicable limit. Never guess a number — omit the
key entirely if the research did not produce a specific, cited figure.

### Step 6: Re-read and audit

Read the saved file back and check every bullet: does it have (a) a source link,
(b) an "as of" date, (c) an official/secondary tag? Fix any that fail. A bullet
without all three is incomplete.

## Constraints

- **Never state a specific number** (fee, deposit cap, notice period, penalty)
  **without a source link.** If only secondary sources exist, keep the number but
  mark it "⚠ secondary source; confirm with [authority]."
- **Never present property-specific HOA facts you did not find.** State HOA *law*
  is researchable; whether *this parcel* has CC&R rental restrictions usually is
  not. Say explicitly: "Unverified for this specific property — obtain recorded
  dedicatory instruments from [county] records."
- **Every fact carries an "as of [date]" tag** (the date you checked it).
- **Absence of regulation is a finding.** "Texas bans rent control statewide" is
  investor-relevant and must appear, marked INFO/positive — don't silently omit
  quiet topics.
- **This is decision support, not legal advice.** Never write "you can legally X."
  Write what the rule says, cite it, and flag what needs professional confirmation.
- Keep bullets to 1–3 lines. The investor reads this next to a financial dashboard,
  not in a law office.

## Output Format

```markdown
# Policy Notes — [City], [ST] [ZIP] ([County])

**Property context:** [one line]
**Researched:** [date]
**Method:** Web search + verification against official (.gov) sources

## 1. Short-Term Rental (STR) Rules [— ⚠ HIGH ATTENTION if applicable]
- [Fact.] — [Source name](url) — as of YYYY-MM-DD ✅ official / ⚠ secondary

## 2. Landlord–Tenant Law (State of [State])
## 3. Rent Control
## 4. HOA / Deed Restrictions [— ⚠ VERIFY PER-PROPERTY]
## 5. High-Attention Flags (summary for NorthStar report)
| Flag | Severity (HIGH/LOW/INFO) | Why |
```

## Example of a good bullet

> - **License term:** Two years (changed from one year in October 2025). *Note:
>   several third-party guides still describe licensing as "annual" — the official
>   city page supersedes them.* — [City of Austin](https://www.austintexas.gov/development-services/short-term-rentals)
>   — as of 2026-07-19 ✅ official

Good because: specific fact, notes the recent change AND the stale-info trap,
official source, dated, tagged. A bare "licenses are annual" copied from a blog
would have been wrong.
