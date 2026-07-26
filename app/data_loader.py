from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.knowledge_bank import (
    RESEARCHED_ROOT,
    USER_ROOT,
    describe_source,
    is_trace_file,
    parse_policy_note,
    render_markdown,
)


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
KNOWLEDGE_BANK_DIR = BASE_DIR / "knowledge_bank"


@lru_cache(maxsize=8)
def load_json(filename: str) -> dict[str, Any]:
    with (DATA_DIR / filename).open("r", encoding="utf-8") as file:
        return json.load(file)


def normalize_state(state: str) -> str:
    return state.strip().upper()


def load_market_context(zip_code: str, state: str) -> dict[str, Any]:
    data = load_json("market_data.json")
    zip_code = zip_code.strip()
    state = normalize_state(state)

    if zip_code in data["zip_markets"]:
        result = dict(data["zip_markets"][zip_code])
        result["match_level"] = "zip"
        result["missing_data_flags"] = []
        return result

    if state in data["state_defaults"]:
        result = dict(data["state_defaults"][state])
        result["match_level"] = "state"
        result["missing_data_flags"] = [
            "Local ZIP-level market data was not found. This section uses state-level sample data and should be verified."
        ]
        return result

    result = dict(data["national_default"])
    result["match_level"] = "national"
    result["missing_data_flags"] = [
        "Local market data was not found. This section uses generic national sample data and should be verified."
    ]
    return result


def _normalize_city(value: str) -> str:
    """Normalize a city name for comparison, treating "Saint" and "St." the same."""
    cleaned = re.sub(r"[^a-z]+", " ", value.lower()).strip()
    words = ["st" if word == "saint" else word for word in cleaned.split()]
    return " ".join(words)


def _merge_policy_records(
    records: list[dict[str, Any]],
    city: str = "",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Combine restriction flags and source links from every matched jurisdiction level.

    Most-specific record first. Duplicates are dropped (same flag title, or same
    link URL + category), and every item keeps a jurisdiction label so the report
    can group city/county, state, HOA, and other rules. Links tagged with
    applies_to_city belong to one specific city's rules and are skipped unless
    the analyzed property is in that city.
    """
    flags: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []
    seen_flags: set[str] = set()
    seen_links: set[tuple[str, str]] = set()
    city_norm = _normalize_city(city)

    for index, record in enumerate(records):
        fallback_jurisdiction = record.get("jurisdiction_name", "Unknown jurisdiction")
        for flag in record.get("restriction_flags", []):
            # Flags marked fallback_only warn that local rules are unresolved;
            # skip them when a more specific record already resolved those rules.
            if index > 0 and flag.get("fallback_only"):
                continue
            if flag["title"] in seen_flags:
                continue
            seen_flags.add(flag["title"])
            item = dict(flag)
            item.pop("fallback_only", None)
            item.setdefault("jurisdiction", fallback_jurisdiction)
            flags.append(item)
        for link in record.get("links", []):
            applies_to_city = link.get("applies_to_city")
            if applies_to_city and _normalize_city(applies_to_city) != city_norm:
                continue
            key = (link["url"], link.get("category", ""))
            if key in seen_links:
                continue
            seen_links.add(key)
            item = dict(link)
            item.pop("applies_to_city", None)
            item.setdefault("jurisdiction", fallback_jurisdiction)
            links.append(item)

    return flags, links


def load_policy_context(zip_code: str, state: str, city: str = "") -> dict[str, Any]:
    """Build a layered policy context covering every jurisdiction level that matches.

    The most specific record (ZIP-level, which represents the city/county rules)
    drives the summaries and risk level, but restriction flags and source links
    are merged across city/county, state, and national levels so the report shows
    all local law, HOA, and policy issues that might affect the investment.
    """
    data = load_json("policy_data.json")
    zip_code = zip_code.strip()
    state = normalize_state(state)

    matched: list[dict[str, Any]] = []
    if zip_code in data["zip_policies"]:
        matched.append(data["zip_policies"][zip_code])
    if state in data["state_policies"]:
        matched.append(data["state_policies"][state])

    if matched:
        result = dict(matched[0])
        if zip_code in data["zip_policies"]:
            result["match_level"] = "zip"
            result["missing_data_flags"] = []
        else:
            place = f"{city.strip()}, {state}" if city.strip() else f"ZIP {zip_code}"
            result["match_level"] = "state"
            result["missing_data_flags"] = [
                f"No city or county policy record was found for {place}. "
                f"The rules below are {state} state-level only — city, county, and HOA "
                "requirements for this address still need to be verified."
            ]
    else:
        matched.append(data["national_default"])
        result = dict(data["national_default"])
        result["match_level"] = "national"
        result["missing_data_flags"] = [
            "Local policy data was not found. Treat this as a due-diligence gap."
        ]

    flags, links = _merge_policy_records(matched, city)
    result["restriction_flags"] = flags
    result["links"] = links
    result["jurisdiction_levels"] = [
        record.get("jurisdiction_name", "Unknown jurisdiction") for record in matched
    ]
    return result


def state_for_zip(zip_code: str) -> str | None:
    """State that owns this ZIP's three-digit prefix, or None if unlisted."""
    digits = re.sub(r"[^0-9]", "", zip_code)[:5]
    if len(digits) < 3:
        return None

    prefix = digits[:3]
    for start, end, state in load_json("zip_directory.json")["state_prefixes"]:
        if start <= prefix <= end:
            return state
    return None


def check_location_consistency(city: str, state: str, zip_code: str) -> dict[str, Any]:
    """Warn when the city, state, and ZIP the user typed do not describe one place.

    A mismatch means the market and policy sections could describe the wrong
    location entirely, so it is surfaced before the investor reads the numbers.
    Checks that cannot be made (unlisted ZIP or prefix) are reported as
    unverified rather than treated as a pass.
    """
    directory = load_json("zip_directory.json")
    state = normalize_state(state)
    city = city.strip()
    digits = re.sub(r"[^0-9]", "", zip_code)[:5]

    warnings: list[str] = []
    unverified: list[str] = []
    place = directory["zip_places"].get(digits)
    expected_state = state_for_zip(digits)

    if len(digits) != 5:
        warnings.append(
            f"\"{zip_code}\" is not a five-digit U.S. ZIP code, so the location could not be checked."
        )
        return {
            "status": "warning",
            "warnings": warnings,
            "unverified": unverified,
            "expected_city": None,
            "expected_county": None,
            "expected_state": None,
        }

    if expected_state and expected_state != state:
        warnings.append(
            f"ZIP {digits} belongs to {expected_state}, but the state entered is {state}. "
            "Confirm the address before using this report."
        )
    elif not expected_state:
        unverified.append(
            f"ZIP {digits} is outside the built-in ZIP prefix ranges, so the state could not be confirmed."
        )

    if place:
        if _normalize_city(place["city"]) != _normalize_city(city):
            warnings.append(
                f"ZIP {digits} is {place['city']}, {place['state']} ({place['county']}), "
                f"but the city entered is \"{city}\". Local rules differ by city and county, "
                "so confirm which one applies to this address."
            )
    else:
        unverified.append(
            f"ZIP {digits} is not in the built-in location directory, so the city could not be "
            "confirmed. Verify the city and county for this address."
        )

    if warnings:
        status = "warning"
    elif unverified:
        status = "unverified"
    else:
        status = "ok"

    return {
        "status": status,
        "warnings": warnings,
        "unverified": unverified,
        "expected_city": place["city"] if place else None,
        "expected_county": place["county"] if place else None,
        "expected_state": expected_state,
    }


def load_sample_properties() -> list[dict[str, Any]]:
    return load_json("sample_properties.json")["properties"]


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _read_text_file(path: Path, max_chars: int = 2200) -> dict[str, Any]:
    content = path.read_text(encoding="utf-8", errors="ignore").strip()
    excerpt = content[:max_chars]
    if len(content) > max_chars:
        excerpt += "\n\n[Excerpt truncated in report. Open the file for the full text.]"

    parsed = parse_policy_note(content)
    relative = path.relative_to(KNOWLEDGE_BANK_DIR)
    return {
        "name": path.name,
        "relative_path": relative.as_posix(),
        "source": describe_source(relative.parent.as_posix()),
        "excerpt": excerpt,
        "html": render_markdown(content),
        "place": parsed["place"],
        "researched": parsed["researched"],
        "days_old": parsed["days_old"],
        "is_stale": parsed["is_stale"],
        "flag_count": len(parsed["flags"]),
        "flags": parsed["flags"],
        "facts": parsed["facts"],
        "diligence": parsed["diligence"],
        "official_citations": parsed["official_citations"],
        "secondary_citations": parsed["secondary_citations"],
    }


def load_knowledge_bank_context(address: str, city: str, state: str, zip_code: str) -> dict[str, Any]:
    """Read every policy note that matches this property, AI-researched or user-added.

    Two roots hold the same global/states/zips/cities/properties taxonomy:
    RESEARCHED_ROOT (written only by the property-policy-research Skill) and
    USER_ROOT (written by the in-app form or by hand). Both are searched at
    every specificity tier, broadest to most specific, so a more specific
    folder always outranks a broader one regardless of which root it is in.
    Legacy flat `state-zip` folders from before this split are still read.
    """
    state = normalize_state(state)
    zip_code = zip_code.strip()
    city_slug = _slug(f"{city}_{state}")
    address_slug = _slug(f"{address}_{zip_code}")
    state_lower = state.lower()

    tiers = [
        "global",
        f"states/{state}",
        f"zips/{zip_code}",
        f"cities/{city_slug}",
        f"properties/{address_slug}",
    ]
    candidate_dirs = []
    for tier in tiers:
        candidate_dirs.append(KNOWLEDGE_BANK_DIR / RESEARCHED_ROOT / tier)
        candidate_dirs.append(KNOWLEDGE_BANK_DIR / USER_ROOT / tier)
    candidate_dirs += [
        # Legacy folders from before the researched/user split, e.g.
        # knowledge_bank/tx-78704/policy-notes.md
        KNOWLEDGE_BANK_DIR / f"{state_lower}-{zip_code}",
        KNOWLEDGE_BANK_DIR / f"{state_lower}-{_slug(city)}",
    ]

    documents: list[dict[str, str]] = []
    for directory in candidate_dirs:
        if not directory.exists() or not directory.is_dir():
            continue
        for path in sorted(directory.glob("*")):
            if (
                path.is_file()
                and path.suffix.lower() in {".md", ".txt"}
                and path.name.lower() != "readme.md"
                # Analysis trails are written by the app; reading them back
                # would feed the report its own past output.
                and not is_trace_file(path.name)
            ):
                documents.append(_read_text_file(path))

    # Flags parsed out of researched policy notes, so the report can act on them
    # rather than leaving the findings buried in a text excerpt.
    researched_flags: list[dict[str, str]] = []
    diligence_items: list[dict[str, str]] = []
    declared_facts: dict[str, Any] = {}
    stale_notes: list[str] = []

    for document in documents:
        for flag in document["flags"]:
            item = dict(flag)
            item["category"] = "Researched policy note"
            item["jurisdiction"] = document["place"] or document["relative_path"]
            item["source_document"] = document["relative_path"]
            if document["researched"]:
                item["researched"] = document["researched"]
            researched_flags.append(item)

        for entry in document["diligence"]:
            diligence_items.append({"item": entry, "source_document": document["relative_path"]})

        # A more specific note wins: candidate_dirs runs general to specific.
        for key, value in document["facts"].items():
            declared_facts[key] = {"value": value, "source_document": document["relative_path"]}

        if document["is_stale"]:
            stale_notes.append(document["relative_path"])

    return {
        "folder_path": str(KNOWLEDGE_BANK_DIR),
        "documents": documents,
        "researched_flags": researched_flags,
        "diligence_items": diligence_items,
        "declared_facts": declared_facts,
        "stale_notes": stale_notes,
        "searched_locations": [
            directory.relative_to(KNOWLEDGE_BANK_DIR).as_posix() for directory in candidate_dirs
        ],
        "instructions": (
            "Add local-law, HOA, condo, lease, lender, or rental-policy notes through the "
            "Knowledge Bank page, or as .md/.txt files under knowledge_bank/user/global, "
            "knowledge_bank/user/states/STATE, knowledge_bank/user/zips/ZIP, "
            "knowledge_bank/user/cities/city_state, or knowledge_bank/user/properties/address_zip. "
            "knowledge_bank/researched/ holds source-cited notes written by the "
            "property-policy-research agent Skill and should not be edited by hand."
        ),
    }
