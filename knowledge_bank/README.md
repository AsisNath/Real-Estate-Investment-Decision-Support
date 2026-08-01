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

## Two roots: `researched/` vs. `user/`

The folder is split into two roots that hold the identical taxonomy below, so you can always tell a verified fact from something typed in:

- **`knowledge_bank/researched/`** — written *only* by the property-policy-research Skill, after live web search and verification against official sources. The app's own write path (the "Add a note" form) refuses to write here, so a note's presence in this folder is a real trust signal.
- **`knowledge_bank/user/`** — written by you: the in-app form, or a file you drop in by hand.

A property reads *both* roots at every specificity tier (broadest to most specific), so a ZIP folder in `researched/` and one in `user/` for the same ZIP are both picked up. Every note the app surfaces is tagged with which root it came from.

## Three ways files get in here

1. **The research Skill.** Ask Claude *"Run policy diligence on 250 5th Ave, Brooklyn, NY 11215"* and it researches the rules, verifies them against official `.gov` sources, and writes a dated, cited note to `researched/zips/11215/policy-notes.md`.
2. **The app's Knowledge Bank page.** Open `http://localhost:8000/knowledge-bank`, use the "Add a local policy note" form, pick where it applies, paste your text, and save — this always lands under `user/`.
3. **By hand.** Drop a `.md` or `.txt` file into the right `user/` folder yourself.

All three are read the same way by the app.

## Folder layout

Within each root, folders run from broad to specific. A property picks up every matching folder in *both* roots, so a Brooklyn condo reads `{researched,user}/global/`, `{researched,user}/states/NY/`, `{researched,user}/zips/11215/`, `{researched,user}/cities/brooklyn_ny/`, and its own property folder in each.

```text
knowledge_bank/
├── researched/                              written only by the Skill
│   └── zips/11215/policy-notes.md
└── user/                                    written by you
    ├── global/                              every property
    ├── states/NY/                           any property in New York
    ├── zips/11215/                          that ZIP
    ├── cities/brooklyn_ny/                  that city
    └── properties/250_5th_ave_11215/        one specific address
```

Folders are created on demand — only ones that hold a note exist.

Older notes in a flat `<state>-<zip>/` folder (for example `ny-11215/`, from before this split existed) are still read, tagged as a legacy source, so nothing breaks if you have them.

## Analysis trail — lives in `logs/`, not here

Every time you analyze a property, NorthStar appends a record to **`logs/zips/<ZIP>/_analysis-log.md`** at the project root: the address, the recommendation, which market and policy records matched, which notes were read, and which flags fired. Months later you can open the folder for a ZIP and see exactly what produced a past recommendation.

It is deliberately **not** in this folder. The knowledge bank holds policy knowledge the app *reads*, and has exactly two roots. A trail records what the app *did* — a different kind of thing, and putting it here would add a confusing third root. A test enforces the separation, failing if an analysis writes anything into the knowledge bank.

**Files beginning with `_` are never read back into a report.** Do not name your own notes with a leading underscore. You can delete a log at any time; it is a record, not an input.

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
