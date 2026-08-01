"""Reading, rendering, and writing knowledge-bank policy notes.

The knowledge bank is a plain folder of .md/.txt files. Notes written by the
property-policy-research Skill follow a known structure, so this module can pull
research dates, high-attention flags, verification counts, diligence items, and
optional machine-readable facts out of them. Notes a user writes by hand still
work: anything the parser cannot find is simply reported as absent.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_BANK_DIR = BASE_DIR / "knowledge_bank"

# Analysis trails live outside the knowledge bank on purpose. The knowledge bank
# holds policy knowledge the app *reads* and has exactly two roots (researched/
# and user/); a trail is an audit record of what the app *did*, which is a
# different kind of thing and would otherwise appear as a third root.
LOGS_DIR = BASE_DIR / "logs"

NOTE_SUFFIXES = {".md", ".txt"}
MAX_NOTE_BYTES = 200_000
STALE_AFTER_DAYS = 120

# Two top-level roots, each holding the same global/states/zips/cities/properties
# taxonomy. RESEARCHED_ROOT is written only by the property-policy-research Skill
# (live web search, verified against official sources). USER_ROOT is written by
# the in-app "Add a note" form or by hand. The app reads both the same way, but
# every note it surfaces is tagged with which one it came from, so an investor
# can tell a Skill-verified fact from something a person typed in.
RESEARCHED_ROOT = "researched"
USER_ROOT = "user"
TAXONOMY_FOLDERS = ("global", "states", "zips", "cities", "properties")

# Files beginning with "_" are written by the app, not by a researcher. They are
# kept beside the notes for traceability but never read as policy findings.
TRACE_PREFIX = "_"
ANALYSIS_LOG_NAME = "_analysis-log.md"
MAX_LOG_ENTRIES = 40

_SEVERITY_MAP = {"HIGH": "high", "MEDIUM": "medium", "LOW": "low", "INFO": "low"}
_DATE_FORMATS = ("%B %d, %Y", "%b %d, %Y", "%B %d %Y", "%Y-%m-%d", "%m/%d/%Y")
_DILIGENCE_HINTS = ("unverified", "confirm with", "obtain ", "confirm directly")


# ---------------------------------------------------------------- parsing


def _parse_date(text: str) -> date | None:
    match = re.match(
        r"\s*([A-Za-z]+ \d{1,2},? \d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})",
        text,
    )
    if not match:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(match.group(1), fmt).date()
        except ValueError:
            continue
    return None


def _strip_markdown(text: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[*_`]+", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _coerce(value: str) -> Any:
    lowered = value.strip().lower()
    if lowered in {"true", "yes"}:
        return True
    if lowered in {"false", "no"}:
        return False
    if lowered in {"none", "null", "n/a", ""}:
        return None
    try:
        number = float(value)
        return int(number) if number.is_integer() else number
    except ValueError:
        return value.strip()


def _section_after(content: str, heading_pattern: str) -> str:
    parts = re.split(heading_pattern, content, flags=re.M | re.I)
    if len(parts) < 2:
        return ""
    body: list[str] = []
    for line in parts[1].splitlines():
        if line.strip().startswith("#"):
            break
        body.append(line)
    return "\n".join(body)


def parse_policy_note(content: str) -> dict[str, Any]:
    """Pull structured findings out of a policy note.

    Returns the note's heading, research date, high-attention flags, counts of
    official versus secondary citations, diligence follow-ups, and any
    machine-readable facts the note declares.
    """
    heading_match = re.search(r"^#\s+(.+)$", content, re.M)
    heading = heading_match.group(1).strip() if heading_match else ""
    place = re.sub(r"^Policy Notes\s*[-–—]\s*", "", heading).strip()

    researched_match = re.search(r"^\*\*Researched:\*\*\s*(.+)$", content, re.M)
    researched = researched_match.group(1).strip() if researched_match else None
    researched_date = _parse_date(researched) if researched else None

    flags: list[dict[str, str]] = []
    for line in _section_after(content, r"^##\s*\d*\.?\s*High-Attention Flags.*$").splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 3 or cells[0].lower() == "flag" or set(cells[0]) <= {"-", ":"}:
            continue
        token = re.sub(r"[^A-Za-z]", "", cells[1].split("(")[0]).upper()
        flags.append(
            {
                "level": _SEVERITY_MAP.get(token, "medium"),
                "title": cells[0],
                "detail": cells[2],
            }
        )

    facts: dict[str, Any] = {}
    for line in _section_after(content, r"^##.*Machine-Readable.*$").splitlines():
        match = re.match(r"^\s*[-*]\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$", line)
        if match:
            facts[match.group(1).lower()] = _coerce(match.group(2))

    diligence: list[str] = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line.startswith(("-", "*")):
            continue
        lowered = line.lower()
        if any(hint in lowered for hint in _DILIGENCE_HINTS):
            item = _strip_markdown(line.lstrip("-* ").strip())
            if item and item not in diligence:
                diligence.append(item)

    return {
        "heading": heading,
        "place": place,
        "researched": researched,
        "researched_date": researched_date.isoformat() if researched_date else None,
        "days_old": (date.today() - researched_date).days if researched_date else None,
        "is_stale": bool(researched_date and (date.today() - researched_date).days > STALE_AFTER_DAYS),
        "flags": flags,
        "facts": facts,
        "diligence": diligence[:8],
        "official_citations": len(re.findall(r"✅\s*official", content, re.I)),
        "secondary_citations": len(re.findall(r"⚠\s*secondary", content, re.I)),
    }


# ---------------------------------------------------------------- rendering


def render_markdown(content: str) -> str:
    """Render a note to HTML, falling back to preformatted text if needed.

    The `markdown` package is optional: the app must still run when it is not
    installed, just with a plainer view.
    """
    try:
        import markdown as markdown_lib
    except ImportError:
        escaped = (
            content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )
        return f"<pre class=\"note-plain\">{escaped}</pre>"

    html = markdown_lib.markdown(content, extensions=["tables", "sane_lists"])
    # Local files, but never let a note inject scripts into the page.
    html = re.sub(r"(?is)<script.*?</script>", "", html)
    html = re.sub(r"(?i)\son\w+\s*=\s*\"[^\"]*\"", "", html)
    return html


# ---------------------------------------------------------------- inventory


def describe_source(relative_folder: str) -> str:
    """Which root a note lives under: researched (AI), user, or legacy/uncategorized."""
    top = relative_folder.strip("/").split("/")[0] if relative_folder.strip("/") else ""
    if top == RESEARCHED_ROOT:
        return "researched"
    if top == USER_ROOT:
        return "user"
    return "legacy"


def describe_scope(relative_folder: str) -> str:
    """Human-readable description of which properties a folder applies to."""
    folder = relative_folder.strip("/")
    parts = folder.split("/") if folder else []
    if parts and parts[0] in (RESEARCHED_ROOT, USER_ROOT):
        parts = parts[1:]
    folder = "/".join(parts)

    if folder in {"", "."}:
        return "Loose notes in the knowledge-bank root"
    if folder == "global":
        return "Every property"
    if parts[0] == "states" and len(parts) > 1:
        return f"Any property in {parts[1].upper()}"
    if parts[0] == "zips" and len(parts) > 1:
        return f"ZIP {parts[1]}"
    if parts[0] == "cities" and len(parts) > 1:
        return f"City folder {parts[1]}"
    if parts[0] == "properties" and len(parts) > 1:
        return f"Property folder {parts[1]}"
    legacy = re.fullmatch(r"([a-zA-Z]{2})-(\d{5})", parts[0])
    if legacy:
        return f"{legacy.group(1).upper()} {legacy.group(2)} (legacy folder)"
    return f"Folder {folder}"


def is_trace_file(name: str) -> bool:
    """True for app-written trace files, which are never parsed as policy notes."""
    return name.startswith(TRACE_PREFIX)


def _is_note(path: Path) -> bool:
    return (
        path.is_file()
        and path.suffix.lower() in NOTE_SUFFIXES
        and path.name.lower() != "readme.md"
        and not is_trace_file(path.name)
    )


def scan_knowledge_bank(
    root: Path | None = None,
    logs_root: Path | None = None,
) -> dict[str, Any]:
    """Inventory every note in the knowledge bank, plus the analysis trails.

    Notes come from `root` (the knowledge bank); trails come from `logs_root`,
    which is a separate directory so the knowledge bank keeps exactly two roots.
    """
    root = root or KNOWLEDGE_BANK_DIR
    notes: list[dict[str, Any]] = []

    if root.exists():
        for path in sorted(root.rglob("*")):
            if not _is_note(path):
                continue
            content = path.read_text(encoding="utf-8", errors="ignore")
            parsed = parse_policy_note(content)
            relative = path.relative_to(root)
            folder = relative.parent.as_posix()
            notes.append(
                {
                    "relative_path": relative.as_posix(),
                    "folder": folder,
                    "name": path.name,
                    "source": describe_source(folder),
                    "applies_to": describe_scope(folder),
                    "place": parsed["place"] or path.stem,
                    "researched": parsed["researched"],
                    "days_old": parsed["days_old"],
                    "is_stale": parsed["is_stale"],
                    "flag_counts": {
                        level: sum(1 for flag in parsed["flags"] if flag["level"] == level)
                        for level in ("high", "medium", "low")
                    },
                    "flags": parsed["flags"],
                    "official_citations": parsed["official_citations"],
                    "secondary_citations": parsed["secondary_citations"],
                    "diligence_count": len(parsed["diligence"]),
                    "facts": parsed["facts"],
                    "size_bytes": path.stat().st_size,
                }
            )

    # Trails are scanned from the logs directory, not the knowledge bank, so the
    # knowledge bank keeps exactly two roots.
    traces: list[dict[str, Any]] = []
    logs_root = logs_root or LOGS_DIR
    if logs_root.exists():
        for path in sorted(logs_root.rglob(f"{TRACE_PREFIX}*")):
            if not path.is_file() or path.suffix.lower() not in NOTE_SUFFIXES:
                continue
            content = path.read_text(encoding="utf-8", errors="ignore")
            relative = path.relative_to(logs_root)
            traces.append(
                {
                    "relative_path": relative.as_posix(),
                    "name": path.name,
                    "applies_to": describe_scope(relative.parent.as_posix()),
                    "entry_count": len(re.findall(r"^##\s", content, re.M)),
                    "size_bytes": path.stat().st_size,
                }
            )

    return {
        "folder_path": str(root),
        "logs_path": str(logs_root),
        "note_count": len(notes),
        "notes": notes,
        "traces": traces,
        "high_flag_total": sum(note["flag_counts"]["high"] for note in notes),
        "stale_count": sum(1 for note in notes if note["is_stale"]),
        "stale_after_days": STALE_AFTER_DAYS,
    }


def read_trace(relative_path: str, root: Path | None = None) -> dict[str, Any]:
    """Read an app-written trace file so the user can inspect the audit trail.

    `root` is the logs directory, not the knowledge bank - trails live outside
    it so the knowledge bank keeps exactly two roots.
    """
    root = root or LOGS_DIR
    path = safe_note_path(relative_path, root)
    if not path.exists() or not path.is_file() or not is_trace_file(path.name):
        raise FileNotFoundError(relative_path)

    content = path.read_text(encoding="utf-8", errors="ignore")
    relative = path.relative_to(root.resolve())
    return {
        "relative_path": relative.as_posix(),
        "name": path.name,
        "applies_to": describe_scope(relative.parent.as_posix()),
        "content": content,
        "html": render_markdown(content),
    }


def record_analysis(report: dict[str, Any], root: Path | None = None) -> str | None:
    """Append what an analysis actually used to that ZIP's audit trail.

    This is the traceability record: months later the user can open the folder
    for a ZIP and see which market record, which policy record, and which notes
    produced a given recommendation. Never raises - a failed write must not
    break an analysis.

    `root` is the logs directory. Trails deliberately do not live in the
    knowledge bank: that folder holds policy knowledge the app reads and has
    exactly two roots (researched/ and user/), while this is app output.
    """
    root = root or LOGS_DIR
    try:
        prop = report.get("property", {})
        zip_code = re.sub(r"[^0-9]", "", str(prop.get("zip_code", "")))[:5]
        if len(zip_code) != 5:
            return None

        policy = report.get("policy", {})
        market = report.get("market", {})
        knowledge_bank = report.get("knowledge_bank", {})
        recommendation = report.get("recommendation", {})

        notes_read = [doc["relative_path"] for doc in knowledge_bank.get("documents", [])]
        applied_flags = [
            f"{flag['title']} ({flag['level']})"
            for flag in policy.get("restriction_flags", [])
        ]
        conflicts = [item["title"] for item in report.get("assumption_conflicts", [])]

        lines = [
            f"## {datetime.now().strftime('%Y-%m-%d %H:%M')} - "
            f"{prop.get('address', '')}, {prop.get('city', '')}, "
            f"{prop.get('state', '')} {prop.get('zip_code', '')}",
            "",
            f"- Recommendation: {recommendation.get('status', 'n/a')} "
            f"(overall risk: {report.get('overall_risk', 'n/a')})",
            f"- Market record: {market.get('market_name', 'n/a')} "
            f"[{market.get('match_level', 'n/a')}-level match]",
            f"- Policy record: {policy.get('jurisdiction_name', 'n/a')} "
            f"[{policy.get('match_level', 'n/a')}-level match]",
            f"- Jurisdictions reviewed: {'; '.join(policy.get('jurisdiction_levels', [])) or 'n/a'}",
            f"- Knowledge-bank notes read: {', '.join(notes_read) if notes_read else 'none'}",
            f"- Address check: {report.get('location_check', {}).get('status', 'n/a')}",
            f"- Policy flags applied: {'; '.join(applied_flags) if applied_flags else 'none'}",
            f"- Assumption conflicts: {'; '.join(conflicts) if conflicts else 'none'}",
            "",
        ]
        entry = "\n".join(lines)

        target = root / "zips" / zip_code / ANALYSIS_LOG_NAME
        target.parent.mkdir(parents=True, exist_ok=True)

        header = (
            f"# Analysis trail - ZIP {zip_code}\n\n"
            "Written by NorthStar each time a property in this ZIP is analyzed, so the "
            "sources behind a past recommendation can be traced. This file is a record, "
            "not policy research: NorthStar never reads it back into a report.\n\n"
        )
        existing = ""
        if target.exists():
            previous = target.read_text(encoding="utf-8", errors="ignore")
            # Keep everything from the first entry heading onward; splitting on
            # blank lines would eat the first entry's own heading.
            start = previous.find("\n## ")
            existing = previous[start + 1 :] if start != -1 else ""

        entries = [block for block in re.split(r"\n(?=## )", existing.strip()) if block.strip()]
        entries.insert(0, entry.strip())
        target.write_text(
            header + "\n\n".join(entries[:MAX_LOG_ENTRIES]) + "\n",
            encoding="utf-8",
        )
        return target.relative_to(root.resolve()).as_posix()
    except (OSError, ValueError, KeyError, TypeError):
        return None


def read_note(relative_path: str, root: Path | None = None) -> dict[str, Any]:
    """Read one note for display. Raises ValueError if the path escapes the bank."""
    root = root or KNOWLEDGE_BANK_DIR
    path = safe_note_path(relative_path, root)
    if not path.exists() or not _is_note(path):
        raise FileNotFoundError(relative_path)

    content = path.read_text(encoding="utf-8", errors="ignore")
    parsed = parse_policy_note(content)
    folder = path.relative_to(root.resolve()).parent.as_posix()
    return {
        "relative_path": path.relative_to(root.resolve()).as_posix(),
        "name": path.name,
        "source": describe_source(folder),
        "applies_to": describe_scope(folder),
        "content": content,
        "html": render_markdown(content),
        **{key: parsed[key] for key in ("place", "researched", "days_old", "is_stale", "flags", "facts", "diligence", "official_citations", "secondary_citations")},
    }


# ---------------------------------------------------------------- writing


def safe_note_path(relative_path: str, root: Path | None = None) -> Path:
    """Resolve a path inside the knowledge bank, refusing anything that escapes it."""
    root = (root or KNOWLEDGE_BANK_DIR).resolve()
    raw = str(relative_path).replace("\\", "/").strip()

    # An absolute path is refused rather than quietly reinterpreted as a
    # relative one, so "/etc/passwd" never becomes knowledge_bank/etc/passwd.
    if raw.startswith("/") or re.match(r"^[A-Za-z]:", raw):
        raise ValueError("Use a path relative to the knowledge_bank folder.")

    cleaned = raw.strip("/")
    if not cleaned or ".." in cleaned.split("/") or ":" in cleaned:
        raise ValueError("Invalid path.")

    candidate = (root / cleaned).resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError("Path must stay inside the knowledge_bank folder.")
    return candidate


def _clean_segment(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "_", value.strip()).strip("._-")
    return slug


def build_folder(scope: str, value: str = "", state: str = "") -> str:
    """Turn a scope choice from the in-app form into a knowledge-bank folder path.

    Everything created through this function is user-provided by definition
    (a person filled out a web form), so every result is rooted under
    USER_ROOT. AI-researched notes are written by the Skill directly to
    RESEARCHED_ROOT and never go through this function.
    """
    scope = (scope or "").strip().lower()
    value = (value or "").strip()

    if scope == "global":
        sub = "global"
    elif scope == "state":
        if not re.fullmatch(r"[A-Za-z]{2}", value):
            raise ValueError("State must be a two-letter abbreviation.")
        sub = f"states/{value.upper()}"
    elif scope == "zip":
        if not re.fullmatch(r"\d{5}", value):
            raise ValueError("ZIP must be five digits.")
        sub = f"zips/{value}"
    elif scope == "city":
        if not value:
            raise ValueError("City is required.")
        suffix = f"_{state.strip().upper()}" if state.strip() else ""
        sub = f"cities/{_clean_segment(value).lower()}{suffix.lower()}"
    elif scope == "property":
        if not value:
            raise ValueError("Address is required.")
        sub = f"properties/{_clean_segment(value).lower()}"
    elif scope == "custom":
        cleaned = "/".join(
            _clean_segment(part) for part in value.replace("\\", "/").split("/") if part.strip()
        )
        if not cleaned:
            raise ValueError("Folder is required.")
        sub = cleaned
    else:
        raise ValueError(f"Unknown scope: {scope}")

    return f"{USER_ROOT}/{sub}"


def create_note(
    folder: str,
    filename: str,
    content: str,
    overwrite: bool = False,
    root: Path | None = None,
) -> dict[str, Any]:
    """Write a user-supplied policy note into the knowledge bank.

    Refuses to write into RESEARCHED_ROOT: that folder is reserved for the
    property-policy-research Skill, which writes there directly (not through
    this function), so a note's presence there is a trustworthy signal that it
    was actually researched, not just labeled that way.
    """
    root = root or KNOWLEDGE_BANK_DIR
    if folder.strip("/").split("/")[0] == RESEARCHED_ROOT:
        raise ValueError(
            f"'{RESEARCHED_ROOT}/' is reserved for the property-policy-research Skill. "
            f"Use '{USER_ROOT}/' (or the Add note form, which does this for you) for your own notes."
        )
    if not content or not content.strip():
        raise ValueError("The note is empty.")
    if len(content.encode("utf-8")) > MAX_NOTE_BYTES:
        raise ValueError(f"The note is larger than {MAX_NOTE_BYTES // 1000} KB.")

    name = _clean_segment(filename or "policy-notes.md")
    if not name:
        raise ValueError("Invalid file name.")
    if Path(name).suffix.lower() not in NOTE_SUFFIXES:
        name = f"{name}.md"

    target = safe_note_path(f"{folder}/{name}" if folder else name, root)
    if target.exists() and not overwrite:
        raise FileExistsError(
            f"{target.name} already exists in that folder. Choose another name or allow overwrite."
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content.strip() + "\n", encoding="utf-8")

    relative = target.relative_to(root.resolve()).as_posix()
    parsed = parse_policy_note(content)
    return {
        "relative_path": relative,
        "applies_to": describe_scope(target.relative_to(root.resolve()).parent.as_posix()),
        "flag_count": len(parsed["flags"]),
        "overwritten": overwrite,
    }
