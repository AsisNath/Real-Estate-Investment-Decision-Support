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

Do not store passwords, API keys, bank information, or sensitive personal information here.
