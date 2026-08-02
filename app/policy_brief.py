"""Turn a policy note into a client-ready Policy Brief.

Lab 5 produced three things: the research Skill, the `knowledge_bank/` notes it
writes, and one hand-built `Property-Policy-Brief-LA-90026.html` - a polished,
printable brief for the investor. The first two were already integrated into
NorthStar. This module integrates the third, and turns it from a one-off artifact
into a generator: *any* note in the knowledge bank can now be rendered as a brief.

Why this belongs in the product rather than as a saved file: NorthStar is a
consulting tool, so the deliverable a client actually receives matters. A raw
markdown note is a working document; a brief is what you hand someone. Generating
it means it can never fall out of sync with the note it came from.

The visual language deliberately matches the Lab 5 brief - same palette, severity
chips, official/secondary tags, and print stylesheet - so the output is
recognisable as the same deliverable, produced automatically.

Nothing here invents content. Every line in a brief comes from the note; if the
note omits a section, the brief omits it too.
"""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any

from app.knowledge_bank import parse_policy_note, safe_note_path


# Severity words that may appear in a note's section headings, mapped to the chip
# shown beside the heading in the brief.
# The marker is consumed together with the separators a note writes around it
# ("— ⚠ HIGH ATTENTION"), otherwise stripping the words alone leaves an orphaned
# dash and warning sign stranded in the middle of the heading.
_MARKER = r"[\s—–\-·]*⚠?\s*{}\s*"
_HEADING_CHIPS = [
    (re.compile(_MARKER.format("HIGH ATTENTION"), re.I), "high", "High attention"),
    (re.compile(_MARKER.format("VERIFY PER-?PROPERTY"), re.I), "med", "Verify per-property"),
    (re.compile(_MARKER.format(r"INFO(?:\s*\(positive\))?\b"), re.I), "info", "Informational"),
]

_SEVERITY_CHIP = {
    "high": ("high", "HIGH"),
    "medium": ("med", "MEDIUM"),
    "low": ("low", "LOW"),
}

_STYLE = """
:root {
  --ink:#1f2733; --muted:#5b6b7c; --brand:#1d5c4d; --brand-light:#eaf3f0;
  --high:#b3261e; --high-bg:#fdecea; --med:#9a6b00; --med-bg:#fdf4e3;
  --info:#2a5d8f; --info-bg:#e9f1f8; --low:#4d6657; --low-bg:#eef3ef;
  --rule:#d9e0e7;
}
* { box-sizing:border-box; margin:0; padding:0; }
body { font-family:"Segoe UI", system-ui, -apple-system, sans-serif; color:var(--ink);
       background:#f4f6f8; line-height:1.55; }
.page { max-width:860px; margin:24px auto; background:#fff; padding:48px 56px;
        box-shadow:0 2px 14px rgba(20,30,40,.08); }
header { border-bottom:3px solid var(--brand); padding-bottom:18px; margin-bottom:26px; }
.kicker { color:var(--brand); font-size:12px; font-weight:700; letter-spacing:.14em;
          text-transform:uppercase; }
h1 { font-size:27px; margin-top:6px; letter-spacing:-.01em; }
.meta { color:var(--muted); font-size:13px; margin-top:8px; }
.meta strong { color:var(--ink); }
h2 { font-size:15px; color:var(--brand); text-transform:uppercase; letter-spacing:.08em;
     margin:30px 0 12px; padding-top:18px; border-top:1px solid var(--rule); }
h2:first-of-type { border-top:none; padding-top:0; }
p, li { font-size:14.5px; }
ul { padding-left:20px; margin:8px 0 4px; }
li { margin-bottom:8px; }
.tag { display:inline-block; font-size:11px; font-weight:700; padding:1px 8px;
       border-radius:10px; vertical-align:1px; white-space:nowrap; }
.tag.official { background:var(--low-bg); color:var(--low); }
.tag.secondary { background:var(--med-bg); color:var(--med); }
.callout { background:var(--high-bg); border-left:4px solid var(--high); padding:14px 18px;
           margin:18px 0; border-radius:0 6px 6px 0; }
.callout.positive { background:var(--brand-light); border-left-color:var(--brand); }
.callout h3 { font-size:14px; margin-bottom:4px; color:var(--high); }
.callout.positive h3 { color:var(--brand); }
.callout ul { margin-top:8px; }
table { width:100%; border-collapse:collapse; margin:12px 0 6px; font-size:13.5px; }
th { text-align:left; background:var(--brand); color:#fff; padding:9px 12px; font-weight:600; }
td { padding:9px 12px; border-bottom:1px solid var(--rule); vertical-align:top; }
.sev { font-weight:700; font-size:11.5px; padding:2px 9px; border-radius:10px; white-space:nowrap; }
.sev.high { background:var(--high-bg); color:var(--high); }
.sev.med  { background:var(--med-bg);  color:var(--med); }
.sev.info { background:var(--info-bg); color:var(--info); }
.sev.low  { background:var(--low-bg);  color:var(--low); }
a { color:var(--info); text-decoration:none; }
a:hover { text-decoration:underline; }
.src { color:var(--muted); font-size:12.5px; }
.facts { margin:14px 0 4px; border-left:3px solid var(--brand); padding-left:14px; }
.facts dt { font-size:12px; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); }
.facts dd { font-size:15px; font-weight:600; margin-bottom:8px; }
footer { margin-top:34px; padding-top:14px; border-top:1px solid var(--rule);
         color:var(--muted); font-size:12px; }
@media print {
  body { background:#fff; }
  .page { box-shadow:none; margin:0; padding:24px 8px; max-width:100%; }
}
"""


def _esc(text: str) -> str:
    return html.escape(text, quote=False)


def _inline_markdown(text: str) -> str:
    """Convert the inline markdown a note bullet uses into safe HTML.

    Escaping happens first, so nothing in a note can inject markup into a brief
    that a user may hand to a client.
    """
    out = _esc(text)
    out = re.sub(
        r"\[([^\]]+)\]\((https?://[^\s)]+)\)",
        lambda m: f'<a href="{html.escape(m.group(2), quote=True)}">{m.group(1)}</a>',
        out,
    )
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", out)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    # Source-quality tags become chips, matching the Lab 5 brief.
    out = re.sub(r"✅\s*official", '<span class="tag official">✅ official</span>', out, flags=re.I)
    out = re.sub(
        r"⚠\s*(secondary|unverified)",
        lambda m: f'<span class="tag secondary">⚠ {m.group(1)}</span>',
        out,
        flags=re.I,
    )
    return out


def _heading_chip(heading: str) -> tuple[str, str]:
    """Strip a severity marker out of a heading and return it as a chip."""
    for pattern, css, label in _HEADING_CHIPS:
        if pattern.search(heading):
            cleaned = pattern.sub(" ", heading)
            cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" —-–·⚠").strip()
            # A heading like "Rent Control — ⚠ HIGH ATTENTION (two regimes)"
            # must not be left as "Rent Control — ⚠ (two regimes)".
            cleaned = re.sub(r"[—–\-·]\s*\(", "(", cleaned).strip()
            return cleaned, f' <span class="sev {css}">{label}</span>'
    return heading.strip(" —-–·").strip(), ""


def _split_sections(content: str) -> list[tuple[str, list[str]]]:
    """Break a note into (heading, body-lines) pairs on its `## ` headings."""
    sections: list[tuple[str, list[str]]] = []
    heading = ""
    body: list[str] = []
    for line in content.splitlines():
        if line.startswith("## "):
            if heading or body:
                sections.append((heading, body))
            heading, body = line[3:].strip(), []
        elif not line.startswith("# "):
            body.append(line)
    if heading or body:
        sections.append((heading, body))
    return sections


def _render_body(lines: list[str]) -> str:
    """Render a section body, handling bullets, markdown tables, and paragraphs."""
    parts: list[str] = []
    bullets: list[str] = []
    table: list[str] = []

    def flush_bullets() -> None:
        if bullets:
            items = "".join(f"<li>{_inline_markdown(b)}</li>" for b in bullets)
            parts.append(f"<ul>{items}</ul>")
            bullets.clear()

    def flush_table() -> None:
        if not table:
            return
        rows = [
            [cell.strip() for cell in row.strip().strip("|").split("|")]
            for row in table
            # The |---|---| separator row carries no content.
            if not re.fullmatch(r"\s*\|?[\s:|-]+\|?\s*", row)
        ]
        table.clear()
        if not rows:
            return
        head, *rest = rows
        html_rows = [
            "<tr>" + "".join(f"<th>{_inline_markdown(c)}</th>" for c in head) + "</tr>"
        ]
        for row in rest:
            cells = []
            for cell in row:
                chip = _severity_cell(cell)
                cells.append(f"<td>{chip or _inline_markdown(cell)}</td>")
            html_rows.append("<tr>" + "".join(cells) + "</tr>")
        parts.append("<table>" + "".join(html_rows) + "</table>")

    for raw in lines:
        line = raw.rstrip()
        if line.lstrip().startswith("|"):
            flush_bullets()
            table.append(line)
            continue
        flush_table()
        if re.match(r"\s*[-*]\s+", line):
            bullets.append(re.sub(r"^\s*[-*]\s+", "", line))
        elif line.strip():
            flush_bullets()
            parts.append(f"<p>{_inline_markdown(line.strip())}</p>")
        else:
            flush_bullets()

    flush_bullets()
    flush_table()
    return "".join(parts)


def _severity_cell(cell: str) -> str:
    """Render a lone severity word in a flags table as a coloured chip."""
    word = cell.strip().upper()
    mapping = {
        "HIGH": ("high", "HIGH"),
        "MEDIUM": ("med", "MEDIUM"),
        "MED": ("med", "MEDIUM"),
        "LOW": ("low", "LOW"),
        "INFO": ("info", "INFO"),
        "INFO (POSITIVE)": ("info", "INFO"),
    }
    if word in mapping:
        css, label = mapping[word]
        return f'<span class="sev {css}">{label}</span>'
    return ""


_FACT_LABELS = {
    "rent_growth_cap_percent": "Legal rent-growth cap",
    "short_term_rental_allowed": "Short-term rental",
    "security_deposit_cap_months": "Security deposit cap",
}


def _format_fact(key: str, value: Any) -> str:
    if value is None:
        return "No limit found"
    if isinstance(value, bool):
        return "Permitted" if value else "Not available"
    if key == "rent_growth_cap_percent":
        return f"{value:g}% per year"
    if key == "security_deposit_cap_months":
        return f"{value:g} month" + ("" if value == 1 else "s")
    return str(value)


def _bottom_line(parsed: dict[str, Any]) -> str:
    """Build the 'Bottom line for an investor' callout.

    The Lab 5 brief opened with a hand-written synthesis. Writing prose from
    thin air is exactly what this project refuses to do elsewhere, so this is
    assembled strictly from what the note already states: its own high-severity
    flags and its declared machine-readable facts.
    """
    high = [f for f in parsed["flags"] if f["level"] == "high"]
    medium = [f for f in parsed["flags"] if f["level"] == "medium"]
    facts = parsed.get("facts") or {}

    if high:
        css, heading = "", "Bottom line for an investor"
        lead = (
            f"This location carries <strong>{len(high)} high-attention "
            f"{'issue' if len(high) == 1 else 'issues'}</strong> that can change the "
            "investment decision on their own."
        )
        listed = high[:3]
    elif medium:
        css, heading = "", "Bottom line for an investor"
        lead = (
            f"No high-attention issues were found, but <strong>{len(medium)} item"
            f"{'' if len(medium) == 1 else 's'}</strong> need confirmation before underwriting."
        )
        listed = medium[:3]
    else:
        css, heading = " positive", "Bottom line for an investor"
        lead = "The research surfaced no high-attention regulatory issues for this location."
        listed = []

    items = "".join(f"<li>{_inline_markdown(f['title'])}</li>" for f in listed)
    body = f"<p>{lead}</p>" + (f"<ul>{items}</ul>" if items else "")

    if facts:
        rows = "".join(
            f"<dt>{_esc(_FACT_LABELS.get(k, k.replace('_', ' ').title()))}</dt>"
            f"<dd>{_esc(_format_fact(k, v))}</dd>"
            for k, v in facts.items()
        )
        body += f'<dl class="facts">{rows}</dl>'

    return f'<div class="callout{css}"><h3>{heading}</h3>{body}</div>'


def build_brief_html(content: str, relative_path: str) -> str:
    """Render one policy note as a standalone, printable Policy Brief."""
    parsed = parse_policy_note(content)

    title = parsed["heading"] or parsed["place"] or relative_path
    title = re.sub(r"^Policy Notes\s*[—–-]\s*", "", title).strip()

    meta_bits = []
    if parsed["place"]:
        meta_bits.append(f"<strong>Jurisdiction:</strong> {_esc(parsed['place'])}")
    if parsed["researched"]:
        meta_bits.append(f"<strong>Researched:</strong> {_esc(parsed['researched'])}")
    citations = parsed["official_citations"] + parsed["secondary_citations"]
    if citations:
        meta_bits.append(
            f"<strong>Sources:</strong> {parsed['official_citations']} official / "
            f"{parsed['secondary_citations']} secondary"
        )
    if parsed["is_stale"]:
        meta_bits.append(
            f'<strong style="color:#9a6b00">Stale:</strong> {parsed["days_old"]} days old'
        )

    sections: list[str] = []
    for heading, body in _split_sections(content):
        if not heading:
            continue
        # The machine-readable block is for the app, not for a client brief.
        if heading.lower().startswith("northstar machine-readable"):
            continue
        clean, chip = _heading_chip(heading)
        rendered = _render_body(body)
        if not rendered:
            continue
        sections.append(f"<h2>{_esc(clean)}{chip}</h2>{rendered}")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Property Policy Brief — {_esc(title)}</title>
<style>{_STYLE}</style>
</head>
<body>
<div class="page">
<header>
  <div class="kicker">NorthStar Property Investment Consulting · Policy Diligence Layer</div>
  <h1>Property Policy Brief — {_esc(title)}</h1>
  <div class="meta">{' &nbsp;·&nbsp; '.join(meta_bits)}</div>
</header>
{_bottom_line(parsed)}
{''.join(sections)}
<footer>
  Generated by NorthStar from <code>{_esc(relative_path)}</code>, written by the
  <strong>property-policy-research</strong> Skill ·
  Decision-support only — not legal, tax, or investment advice. Facts tagged ⚠ should be
  confirmed with the issuing authority before underwriting.
</footer>
</div>
</body>
</html>
"""


def build_brief(relative_path: str, root: Path | None = None) -> dict[str, str]:
    """Read a note off disk and render its brief. Raises like `read_note` does."""
    path = safe_note_path(relative_path, root)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(relative_path)
    if path.suffix.lower() not in {".md", ".txt"}:
        raise ValueError("A policy brief can only be generated from a .md or .txt note.")

    content = path.read_text(encoding="utf-8", errors="ignore")
    slug = re.sub(r"[^a-z0-9]+", "-", relative_path.lower()).strip("-")
    return {
        "html": build_brief_html(content, relative_path),
        "filename": f"policy-brief-{slug}.html",
        "relative_path": relative_path,
    }
