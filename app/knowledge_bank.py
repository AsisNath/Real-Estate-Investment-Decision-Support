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

NOTE_SUFFIXES = {".md", ".txt"}
MAX_NOTE_BYTES = 200_000
STALE_AFTER_DAYS = 120

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


def describe_scope(relative_folder: str) -> str:
    """Human-readable description of which properties a folder applies to."""
    folder = relative_folder.strip("/")
    if folder in {"", "."}:
        return "Loose notes in the knowledge-bank root"
    if folder == "global":
        return "Every property"
    parts = folder.split("/")
    if parts[0] == "states" and len(parts) > 1:
        return f"Any property in {parts[1].upper()}"
    if parts[0] == "zips" and len(parts) > 1:
        return f"ZIP {parts[1]}"
    if parts[0] == "cities" and len(parts) > 1:
        return f"City folder {parts[1]}"
    if parts[0] == "properties" and len(parts) > 1:
        return f"Property folder {parts[1]}"
    researched = re.fullmatch(r"([a-zA-Z]{2})-(\d{5})", parts[0])
    if researched:
        return f"{researched.group(1).upper()} {researched.group(2)} (researched note)"
    return f"Folder {folder}"


def _is_note(path: Path) -> bool:
    return (
        path.is_file()
        and path.suffix.lower() in NOTE_SUFFIXES
        and path.name.lower() != "readme.md"
    )


def scan_knowledge_bank(root: Path | None = None) -> dict[str, Any]:
    """Inventory every note in the knowledge bank, whoever created it."""
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

    return {
        "folder_path": str(root),
        "note_count": len(notes),
        "notes": notes,
        "high_flag_total": sum(note["flag_counts"]["high"] for note in notes),
        "stale_count": sum(1 for note in notes if note["is_stale"]),
        "stale_after_days": STALE_AFTER_DAYS,
    }


def read_note(relative_path: str, root: Path | None = None) -> dict[str, Any]:
    """Read one note for display. Raises ValueError if the path escapes the bank."""
    root = root or KNOWLEDGE_BANK_DIR
    path = safe_note_path(relative_path, root)
    if not path.exists() or not _is_note(path):
        raise FileNotFoundError(relative_path)

    content = path.read_text(encoding="utf-8", errors="ignore")
    parsed = parse_policy_note(content)
    return {
        "relative_path": path.relative_to(root.resolve()).as_posix(),
        "name": path.name,
        "applies_to": describe_scope(path.relative_to(root.resolve()).parent.as_posix()),
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
    """Turn a scope choice from the UI into a knowledge-bank folder path."""
    scope = (scope or "").strip().lower()
    value = (value or "").strip()

    if scope == "global":
        return "global"
    if scope == "state":
        if not re.fullmatch(r"[A-Za-z]{2}", value):
            raise ValueError("State must be a two-letter abbreviation.")
        return f"states/{value.upper()}"
    if scope == "zip":
        if not re.fullmatch(r"\d{5}", value):
            raise ValueError("ZIP must be five digits.")
        return f"zips/{value}"
    if scope == "city":
        if not value:
            raise ValueError("City is required.")
        suffix = f"_{state.strip().upper()}" if state.strip() else ""
        return f"cities/{_clean_segment(value).lower()}{suffix.lower()}"
    if scope == "property":
        if not value:
            raise ValueError("Address is required.")
        return f"properties/{_clean_segment(value).lower()}"
    if scope == "researched":
        if not re.fullmatch(r"[A-Za-z]{2}", state.strip()) or not re.fullmatch(r"\d{5}", value):
            raise ValueError("A researched note needs a two-letter state and a five-digit ZIP.")
        return f"{state.strip().lower()}-{value}"
    if scope == "custom":
        cleaned = "/".join(
            _clean_segment(part) for part in value.replace("\\", "/").split("/") if part.strip()
        )
        if not cleaned:
            raise ValueError("Folder is required.")
        return cleaned
    raise ValueError(f"Unknown scope: {scope}")


def create_note(
    folder: str,
    filename: str,
    content: str,
    overwrite: bool = False,
    root: Path | None = None,
) -> dict[str, Any]:
    """Write a user-supplied policy note into the knowledge bank."""
    root = root or KNOWLEDGE_BANK_DIR
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
