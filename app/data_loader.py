from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any


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


def load_policy_context(zip_code: str, state: str) -> dict[str, Any]:
    data = load_json("policy_data.json")
    zip_code = zip_code.strip()
    state = normalize_state(state)

    if zip_code in data["zip_policies"]:
        result = dict(data["zip_policies"][zip_code])
        result["match_level"] = "zip"
        result["missing_data_flags"] = []
        return result

    if state in data["state_policies"]:
        result = dict(data["state_policies"][state])
        result["match_level"] = "state"
        result["missing_data_flags"] = [
            "Address-specific rental rules and HOA restrictions were not found. Verify city, county, and HOA documents."
        ]
        return result

    result = dict(data["national_default"])
    result["match_level"] = "national"
    result["missing_data_flags"] = [
        "Local policy data was not found. Treat this as a due-diligence gap."
    ]
    return result


def load_sample_properties() -> list[dict[str, Any]]:
    return load_json("sample_properties.json")["properties"]


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _read_text_file(path: Path, max_chars: int = 2200) -> dict[str, str]:
    content = path.read_text(encoding="utf-8", errors="ignore").strip()
    excerpt = content[:max_chars]
    if len(content) > max_chars:
        excerpt += "\n\n[Excerpt truncated in report. Open the file for the full text.]"
    return {
        "name": path.name,
        "relative_path": path.relative_to(KNOWLEDGE_BANK_DIR).as_posix(),
        "excerpt": excerpt,
    }


def load_knowledge_bank_context(address: str, city: str, state: str, zip_code: str) -> dict[str, Any]:
    """Read local user-supplied policy notes for the selected property.

    The MVP does not analyze uploaded documents yet, so this folder is the manual
    bridge: users can place .md or .txt notes here and the report will surface
    them alongside online source links.
    """
    state = normalize_state(state)
    zip_code = zip_code.strip()
    city_slug = _slug(f"{city}_{state}")
    address_slug = _slug(f"{address}_{zip_code}")
    state_lower = state.lower()

    candidate_dirs = [
        KNOWLEDGE_BANK_DIR / "global",
        KNOWLEDGE_BANK_DIR / "states" / state,
        KNOWLEDGE_BANK_DIR / "zips" / zip_code,
        KNOWLEDGE_BANK_DIR / "cities" / city_slug,
        KNOWLEDGE_BANK_DIR / "properties" / address_slug,
        # Folders written by the property-policy-research agent Skill,
        # e.g. knowledge_bank/tx-78704/policy-notes.md
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
            ):
                documents.append(_read_text_file(path))

    return {
        "folder_path": str(KNOWLEDGE_BANK_DIR),
        "documents": documents,
        "searched_locations": [
            directory.relative_to(KNOWLEDGE_BANK_DIR).as_posix() for directory in candidate_dirs
        ],
        "instructions": (
            "Add local-law, HOA, condo, lease, lender, or rental-policy notes as .md or .txt files "
            "inside knowledge_bank/global, knowledge_bank/states/STATE, knowledge_bank/zips/ZIP, "
            "knowledge_bank/cities/city_state, or knowledge_bank/properties/address_zip. "
            "Notes can also be generated automatically by the property-policy-research agent Skill, "
            "which writes source-cited policy notes to knowledge_bank/state-zip (for example tx-78704). "
            "A future hosted version can replace this folder with document upload."
        ),
    }
