# Property Policy Research Skill

A reusable agent Skill that researches the **rental regulatory environment for any
U.S. property address** — using live web search, never memory — and saves
structured, source-cited findings into a `knowledge_bank/` folder.

## Goal / Objective

Small real-estate investors evaluate deals by stitching together rent rules, HOA
documents, short-term-rental ordinances, and landlord-tenant law from scattered,
often-stale sources. This Skill makes that first-pass policy diligence
**structured, repeatable, and honest about uncertainty**. For every address it
covers four topics and one synthesis:

1. **Short-term rental (STR) rules** — permits, fees, caps, enforcement
2. **Landlord–tenant law** — deposits, return deadlines, penalties (state level)
3. **Rent control** — state and city regimes, allowed increases, coverage rules
4. **HOA / deed restrictions** — what state law allows, what needs per-parcel checks
5. **High-Attention Flags** — a severity table of anything that could change the buy decision

Every fact carries a source link, an "as of" date, and a **✅ official / ⚠ secondary**
tag. When an official .gov source and a blog disagree, the official source wins.
Regulatory facts are never answered from memory — rules change too often.

## What's in this folder

```
property-policy-research/          ← the Skill (this is what you install)
│   ├── SKILL.md                   ← instructions the agent follows
│   └── references/
│       └── policy-topics.md       ← search-query patterns + source-quality ladder
├── knowledge_bank/                ← example outputs
│   ├── tx-78704/policy-notes.md   ← Austin, TX (STR-friendly, no rent control)
│   └── ca-90026/policy-notes.md   ← Los Angeles, CA (heavily regulated)
└── Property-Policy-Brief-LA-90026.html  ← example polished investor brief
```

> **This project's copy** (`.claude/skills/property-policy-research/` in NorthStar)
> is just the Skill itself — `SKILL.md` and `references/`. The example outputs
> above shipped with the standalone Lab 5 package; in NorthStar, real researched
> notes for the same three markets live at the project root in
> `knowledge_bank/researched/zips/{78704,90026,11215}/policy-notes.md` instead.

---

## Using it with Claude (Claude Code / Cowork / claude.ai)

### Claude Code

Copy the `property-policy-research` folder to one of these locations:

| Location | Scope |
|---|---|
| `C:\Users\<you>\.claude\skills\property-policy-research\` | All projects (recommended) |
| `<project>\.claude\skills\property-policy-research\` | One project only |

Then **start a new session** (skills load at session start) and just ask naturally:

> "Run policy diligence on 250 5th Ave, Brooklyn, NY 11215"
> "Can I Airbnb a condo in Park Slope?"
> "What are the rental rules in Denver, CO?"

You do not need to name the Skill — Claude matches your request against the
Skill's description and activates it automatically. Output is written to
`knowledge_bank/researched/zips/<zip>/policy-notes.md` under your current
working folder.

> **Why `researched/`:** NorthStar splits its knowledge bank into two roots.
> `researched/` is written *only* by this Skill; `user/` holds notes a person
> added by hand or through the app's form, and the app refuses to write into
> `researched/` itself. That separation is what lets the app label a finding
> AI-researched-and-cited rather than merely typed in, so this Skill must always
> write under `researched/` and never under `user/`. The standalone Lab 5 copy
> used a flat `<state>-<zip>/` folder; NorthStar still reads those as a legacy
> source, so older notes keep working.

### Claude Cowork / claude.ai

Cowork and claude.ai share the same skill system, so one upload covers both.

**Step 1 — Package the Skill as a `.skill` file.**
A `.skill` file is just a zip with a different extension. In File Explorer:

1. Right-click the `property-policy-research` **folder** (the folder itself, not
   the files inside it) → **Compress to ZIP file**. `SKILL.md` must end up one
   level inside the zip (`property-policy-research/SKILL.md`), not at the root.
2. Rename `property-policy-research.zip` → `property-policy-research.skill`
   (confirm the extension-change warning).

**Step 2 — Upload it.**
In claude.ai or Cowork: **Settings → Capabilities → Skills → Upload skill**, and
select the `.skill` file. (Menu names vary slightly by version — look for
"Skills" or "Capabilities" in Settings.)

**Step 3 — Use it.**
Start a new conversation and ask naturally — *"Can I Airbnb a condo in Park
Slope, Brooklyn?"* — the Skill triggers automatically. Make sure **web search is
enabled** for the conversation.

**Cowork note:** Cowork works inside a folder you point it at. Open it on the
folder where you want results, and the
`knowledge_bank/researched/zips/<zip>/policy-notes.md` output lands there. In
claude.ai (no file system), the policy note is produced as a document in the
chat instead — same content, no saved file.

**No-upload fallback:** in Cowork you can skip packaging entirely — put the
`property-policy-research` folder inside your working folder and say *"Follow
the instructions in property-policy-research/SKILL.md for [address]."*

## Using it with Codex Desktop

Codex doesn't auto-discover skill folders the way Claude does, so you wire it
up through the project folder and `AGENTS.md` (Codex's memory/context file).

**Step 1 — Turn on web search.**
Open the Plugins panel (search "plugins and skills" and check the "Added" list).
Web search is usually on by default; confirm it. Without a search tool the Skill
is designed to stop rather than answer from memory, so this is required.

**Step 2 — Put the Skill in your project folder.**
Copy the whole `property-policy-research/` folder into the project folder you
point Codex at:

```
your-project\
├── AGENTS.md
├── property-policy-research\
│   ├── SKILL.md
│   └── references\policy-topics.md
└── knowledge_bank\
    └── researched\zips\<zip>\policy-notes.md   ← outputs appear here
```

**Step 3 — Register it in `AGENTS.md`.**
Add this to `AGENTS.md` in the project root (create the file if it doesn't exist):

```markdown
## Skills
For any property policy, rental-rule, STR/Airbnb, HOA, or rent-control research
request, follow the instructions in `property-policy-research/SKILL.md` exactly,
including its web-search requirement and output format.
```

**Step 4 — Use it.**
Ask naturally: *"Research rental policy for 250 5th Ave, Brooklyn, NY 11215."*
Because `AGENTS.md` is loaded every session, Codex routes matching requests to
the Skill without you naming it.

**If Codex answers from memory instead of searching:** name the tool explicitly
once — *"Use web search; follow property-policy-research/SKILL.md"* — and
consider making the `AGENTS.md` line more forceful ("never answer regulatory
questions from memory; always run web search first").

## Using it with any other AI tool

The Skill is plain English — no platform lock-in. Minimum requirements: the
agent can (a) search the web and (b) write files. Paste or attach `SKILL.md`
and say: *"Follow these instructions for [address]."* If the tool can't write
files, ask it to output the policy note as markdown in the chat instead.

---

## What good output looks like

Every bullet in a policy note follows this pattern:

> - **License term:** Two years (changed from one year in October 2025). *Note:
>   several third-party guides still describe licensing as "annual" — the official
>   city page supersedes them.* — [City of Austin](https://www.austintexas.gov/development-services/short-term-rentals)
>   — as of 2026-07-19 ✅ official

And every note ends with a High-Attention Flags table (HIGH / MEDIUM / INFO / LOW)
summarizing what could materially change the investment decision. When the
research produces a clear number or yes/no answer, the note also closes with a
`## NorthStar Machine-Readable Summary` block (`rent_growth_cap_percent`,
`short_term_rental_allowed`, `security_deposit_cap_months`) that NorthStar checks
against the investor's own assumptions — see Step 5b of `SKILL.md`.

For worked examples, read the bundled notes at
`knowledge_bank/researched/zips/78704` (Austin) and `.../90026` (Los Angeles):
near-opposite regulatory environments, which is exactly what the Skill is built
to surface.

## Customizing

- **Fixed output location:** by default output lands in
  `knowledge_bank/researched/` under the current working folder. To pin it to one
  path, edit Step 5 of `SKILL.md`.
- **More topics** (e.g., property-tax rules, zoning, insurance mandates): add a
  numbered section to the Output Format in `SKILL.md` and a matching entry with
  query patterns in `references/policy-topics.md`.
- **Different audience:** the tone constraints ("1–3 line bullets, investor
  audience") live in the Constraints section of `SKILL.md`.

## Limits and responsible use

This is **decision support, not legal advice**. The Skill is designed to say
"unverified — confirm with the authority" rather than guess: parcel-level HOA
CC&Rs are usually not searchable, and some official city pages block automated
access (facts from those are tagged ⚠ secondary). Confirm anything tagged ⚠,
and anything load-bearing, with the issuing authority or a professional before
acting on it.
