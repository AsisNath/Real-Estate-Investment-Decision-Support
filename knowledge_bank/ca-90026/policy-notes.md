# Policy Notes — Los Angeles, CA 90026 (Los Angeles County)

**Property context:** Residential rental property, City of Los Angeles (Echo Park/Silver Lake area), ZIP 90026
**Researched:** July 19, 2026
**Method:** Web search + verification against official (.gov) sources where available. Note: the City of LA housing department page (housing.lacity.gov) blocks automated fetching; facts sourced only from secondary guides are tagged accordingly.

---

## 1. Short-Term Rental (STR) Rules — ⚠ HIGH ATTENTION

- **Primary-residence only.** LA's Home-Sharing Ordinance allows STR (<30 days) only in the host's primary residence (lived in ≥6 months/year). **A non-owner-occupied investment property cannot legally operate as an STR in the City of LA.** — [LA City Planning — Home-Sharing](https://planning.lacity.gov/project-review/home-sharing) — as of 2026-07-19 ✅ official
- **Registration required:** Home-Sharing Registration Number ($89/year, renewed annually) must appear in all listings. — [LAHD Home-Sharing Ordinance](https://housing.lacity.gov/articles/home-sharing-ordinance) — as of 2026-07-19 ✅ official (page identified; details cross-checked via secondary guides)
- **120-day annual cap** unless Extended Home-Sharing approval is obtained (public hearing; clean 3-year citation history required). — [LA City Planning FAQ](https://planning.lacity.gov/odocument/1dab409a-d9cb-47f2-9a29-0348389cf752/FAQ.pdf) — as of 2026-07-19 ✅ official
- **RSO units and most ADUs are ineligible** for home-sharing entirely. — [LA City Planning](https://planning.lacity.gov/project-review/home-sharing) — as of 2026-07-19 ✅ official
- **Penalties:** up to $2,000/day. — [Guestable guide](https://www.guestable.com/blog/short-term-rentals-los-angeles/) — as of 2026-07-19 ⚠ secondary; confirm with city
- **⚠ Active state-level enforcement:** SB 346 requires Airbnb/VRBO to share host data (name, address, nights booked, registration status) with cities; LA City Attorney has been delisting non-compliant hosts since 2025. — [Minut guide](https://www.minut.com/blog/los-angeles-airbnb-laws) — as of 2026-07-19 ⚠ secondary; statute is real, enforcement detail secondary

## 2. Landlord–Tenant Law (State of California)

- **Deposit capped at one month's rent** (AB 12, effective 2024-07-01), furnished or not. Small-landlord exception (≤2 properties / ≤4 units): two months, unless tenant is a service member. — [California Apartment Association](https://caanet.org/new-law-limiting-security-deposits-now-in-effect/) — as of 2026-07-19 ⚠ secondary (industry assoc.); statute: Civ. Code § 1950.5
- **Return deadline: 21 days** after move-out, with itemized statement of deductions. — [CA Attorney General consumer alert](https://oag.ca.gov/system/files/media/Know-Your-Rights-Security-Deposits-English.pdf) — as of 2026-07-19 ✅ official
- **Bad-faith retention penalty:** up to 2× the deposit. — [CA AG](https://oag.ca.gov/system/files/media/Know-Your-Rights-Security-Deposits-English.pdf) — as of 2026-07-19 ✅ official

## 3. Rent Control — ⚠ HIGH ATTENTION (two overlapping regimes)

- **City RSO (stricter, controls if applicable):** covers most rental units first occupied on or before **1978-10-01** in the City of LA. Allowed annual increase currently **3% (through 2027-06-30)**; from **2026-07-01** the formula drops to 90% of CPI with a **4% max / 1% min**, and as of **2026-02-02** the extra utilities percentage and +10% additional-dependent increase were eliminated. — [RentCeiling summary](https://rentceiling.com/los-angeles), [AAGLA alert](https://members.aagla.org/news/news-alert-la-city-passes-severely-reduced-rso-formula-ordinance) — as of 2026-07-19 ⚠ secondary; housing.lacity.gov blocked automated verification — **confirm exact figure with LAHD before underwriting**
- **State AB 1482 (fallback for non-RSO units):** cap = 5% + regional CPI, max 10%. LA metro: **8.7% effective 2026-08-01 through 2027-07-31** (8.0% before that). Applies to most units 15+ years old not otherwise exempt. — [LA County DCBA](https://dcba.lacounty.gov/portfolio/rent-increases/) — as of 2026-07-19 ✅ official
- **Investor implication:** a pre-1979 building in 90026 is almost certainly RSO — rent growth assumption must be ~3–4%, NOT market rate, and NOT the 8.7% state cap. Build-year is the single most valuable diligence fact for this ZIP.

## 4. HOA / Deed Restrictions — ⚠ VERIFY PER-PROPERTY

- California **Civil Code § 4741** bars HOAs from banning rentals outright or capping rentals below 25% of units; ADUs don't count toward the cap. — [FindHOALaw](https://findhoalaw.com/limitations-on-rental-prohibitions/) — as of 2026-07-19 ⚠ secondary legal summary; statute citation verifiable
- HOAs **may prohibit rentals of 30 days or less** (i.e., ban STRs) and impose reasonable registration rules. Willful § 4741 violation: actual damages + $1,000 civil penalty. — [Feldsott Lee & Nichter](https://cahoalaw.com/can-your-hoa-regulate-short-term-rentals-in-california-what-you-need-to-know/) — as of 2026-07-19 ⚠ secondary
- **Unverified for this specific property:** whether the parcel is in an HOA/condo regime and what its CC&Rs say. Obtain recorded CC&Rs (LA County Registrar-Recorder) before underwriting.

## 5. High-Attention Flags (summary for NorthStar report)

| Flag | Severity | Why |
|---|---|---|
| STR effectively unavailable for investment property (primary-residence-only rule) | HIGH | Removes the STR revenue scenario entirely for non-owner-occupants |
| RSO likely applies if building pre-Oct-1978 | HIGH | Caps rent growth at ~3–4%/yr; overrides market-rate assumptions; also blocks home-sharing |
| RSO exact cap unverified against official page | MEDIUM | City site blocked automated check — confirm 3% figure with LAHD directly |
| AB 1482 cap 8.7% (Aug 2026–Jul 2027) if not RSO | INFO | Still a real ceiling on rent-growth assumptions, unlike Texas |
| Deposit capped at 1 month (AB 12) | LOW | Affects cash buffer modeling, minor |

## NorthStar Machine-Readable Summary

Values below summarize the cited findings above so NorthStar can check them against the investor's own assumptions. The rent cap reflects the City RSO formula (90% of CPI, 4% maximum) that applies to most pre-October-1978 units in this ZIP; a confirmed non-RSO unit falls under the AB 1482 cap instead.

- short_term_rental_allowed: false
- rent_growth_cap_percent: 4
- security_deposit_cap_months: 1
