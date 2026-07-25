# NorthStar Knowledge Bank

This folder is NorthStar's local library of policy, HOA, lease, lender, and rental-law information. It is plain files — nothing here is a database, and you can open, edit, or delete anything with a text editor.

## The Skill versus this folder

These are two different things that are easy to confuse:

| | `property-policy-research` (the Skill) | `knowledge_bank/` (this folder) |
|---|---|---|
| What it is | Instructions an AI agent follows | A folder of files |
| Where it lives | `.claude/skills/property-policy-research/` | here |
| What it does | Researches rental rules on the live web and writes a note | Stores notes and hands them to the app |
| Who runs it | You, in Claude Code / Cowork / claude.ai | Nobody — the app just reads it |
| Needs internet | Yes | No |

**The Skill writes into this folder. The app only reads from it.** The app never goes online: it reads whatever files are sitting here at the moment you click Analyze.

## Three ways files get in here

1. **The research Skill.** Ask Claude *"Run policy diligence on 250 5th Ave, Brooklyn, NY 11215"* and it researches the rules, verifies them against official `.gov` sources, and writes a dated, cited note to `zips/11215/policy-notes.md`.
2. **The app's Knowledge Bank page.** Open `http://localhost:8000/knowledge-bank`, use the "Add a local policy note" form, pick where it applies, paste your text, and save.
3. **By hand.** Drop a `.md` or `.txt` file into the right folder yourself.

All three are equivalent — the app cannot tell them apart and does not care.

## Folder layout

Folders run from broad to specific. A property picks up every folder that matches it, so a Brooklyn condo reads `global/`, `states/NY/`, `zips/11215/`, `cities/brooklyn_ny/`, and its own property folder.

```text
knowledge_bank/
├── global/                      every property
├── states/NY/                   any property in New York
├── zips/11215/                  that ZIP
├── cities/brooklyn_ny/          that city
└── properties/250_5th_ave_11215/   one specific address
```

Folders are created on demand — only ones that hold a note exist.

Older notes in a flat `<state>-<zip>/` folder (for example `ny-11215/`) are still read, so nothing breaks if you have them.

## Analysis trail (`_analysis-log.md`)

Every time you analyze a property, NorthStar appends a record to `zips/<ZIP>/_analysis-log.md`: the address, the recommendation, which market and policy records matched, which notes were read, and which flags fired. That is the traceability record — months later you can open the folder for a ZIP and see exactly what produced a past recommendation.

**Files beginning with `_` are written by the app and are never read back into a report.** Do not name your own notes with a leading underscore. You can delete a log at any time; it is a record, not an input.

## What makes a note do more than display

Any note is shown in the report. A note gains extra power if it includes either of these optional sections.

**A high-attention flags table** — its rows appear in "Policy Restrictions and Sources", and every HIGH row becomes a risk that can change the recommendation:

```markdown
## 5. High-Attention Flags (summary for NorthStar report)

| Flag | Severity | Why |
|---|---|---|
| HOA rental cap may be full | HIGH | The unit may not be rentable this year |
```

**A machine-readable summary** — these values are checked against the investor's own assumptions, so a note can correct the financial model:

```markdown
## NorthStar Machine-Readable Summary

- rent_growth_cap_percent: 3
- short_term_rental_allowed: false
- security_deposit_cap_months: 1
```

If the analysis uses a rent-growth assumption above `rent_growth_cap_percent`, the report opens with a warning that the projections assume growth the local rules do not allow, and names the note it came from. Use `none` when a limit does not apply.

Notes are also scanned for lines containing "unverified", "confirm with", or "obtain", which become the report's **Diligence Checklist**. A note with a `**Researched:**` date older than 120 days is marked stale.

## Good things to keep here

Rent-increase limits, landlord registration and licensing rules, short-term rental permits and caps, HOA or condo rental restrictions, deed restrictions, inspection and occupancy rules, lender conditions, and lease restrictions.

Do not store passwords, API keys, bank information, or sensitive personal information here.
