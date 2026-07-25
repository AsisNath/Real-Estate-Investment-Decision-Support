# NorthStar Knowledge Bank

Use this folder for local policy, HOA, condo, lease, lender, or rental-law notes that are not available from the built-in sample source links.

NorthStar reads `.md` and `.txt` files from these locations for each analysis:

- `knowledge_bank/global`
- `knowledge_bank/states/STATE`
- `knowledge_bank/zips/ZIP`
- `knowledge_bank/cities/city_state`
- `knowledge_bank/properties/address_zip`
- `knowledge_bank/state-zip` (e.g. `tx-78704`, written by the policy research Skill)
- `knowledge_bank/state-city_slug` (e.g. `tx-austin`, written by the policy research Skill)

Examples:

- Indiana statewide notes: `knowledge_bank/states/IN/landlord_tenant_notes.md`
- ZIP-specific notes: `knowledge_bank/zips/46202/rental_policy_notes.md`
- City-specific notes: `knowledge_bank/cities/indianapolis_in/short_term_rental_notes.md`
- Property-specific HOA notes: `knowledge_bank/properties/725_n_delaware_st_46202/hoa_restrictions.md`

Suggested file topics:

- Rent increase limits or rent-control rules
- Landlord registration or rental licensing
- Short-term rental permits, caps, taxes, or enforcement
- HOA, condo, deed, or subdivision rental restrictions
- Local inspection, occupancy, zoning, or nuisance rules
- Property-tax or insurance notes that affect the investment

## Automatic policy notes

Notes can also be generated automatically by the `property-policy-research` agent Skill (in `.claude/skills/`). Given an address, it web-searches short-term rental permits, landlord-tenant law, rent control, and HOA restrictions, then writes `policy-notes.md` into `knowledge_bank/<state>-<zip>/`. Every fact in a generated note includes a source link, an "as of" date, and an official (✅) or secondary (⚠) tag. Facts tagged secondary should be confirmed with the issuing authority before relying on them.

## Adding notes from inside the app

Open `http://localhost:8000/knowledge-bank` while NorthStar is running. That page lists every note in this folder and has an "Add a local policy note" form: choose where the note applies (ZIP, state, city, one property, everywhere, or a custom folder), paste the text, and save. The file is written straight into this folder, and the next analysis of a matching property picks it up. The "Insert template" button fills in the structure described below.

You can also just drop `.md` or `.txt` files into these folders by hand. Both routes are equivalent.

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

Do not store passwords, API keys, bank information, or sensitive personal information here.
