"""Tests for the Policy Brief generator.

The brief is the Lab 5 "polished deliverable" turned into something the app
produces on demand. The rules that matter: it must never invent content the note
does not contain, and it must never let note text become markup.
"""

import re

import pytest

from app.policy_brief import build_brief, build_brief_html


NOTE = """# Policy Notes - Somewhere, ST 12345 (Example County)

**Property context:** Suburban rental
**Researched:** 2026-07-20
**Method:** Web search

## 1. Short-Term Rental (STR) Rules - HIGH ATTENTION

- **A permit is required.** - [City](https://city.example.gov) - as of 2026-07-20 OK official
- Fee is $100. - [A blog](https://blog.example.com) - as of 2026-07-20 confirm with city

## 4. HOA / Deed Restrictions - VERIFY PER-PROPERTY

- **Unverified for this specific property:** obtain the recorded CC&Rs.

## 5. High-Attention Flags (summary for NorthStar report)

| Flag | Severity | Why |
|---|---|---|
| Rentals capped by HOA | HIGH | Can void the rental strategy |
| Permit renewal burden | MEDIUM | Recurring compliance cost |

## NorthStar Machine-Readable Summary

- rent_growth_cap_percent: 2.5
- short_term_rental_allowed: false
"""


def test_brief_is_a_standalone_html_document():
    html = build_brief_html(NOTE, "researched/zips/12345/policy-notes.md")

    assert html.startswith("<!DOCTYPE html>")
    # Self-contained: no external CSS or scripts, so it opens and prints anywhere.
    assert "<style>" in html
    assert "<link" not in html and "<script" not in html


def test_brief_carries_the_northstar_identity():
    html = build_brief_html(NOTE, "researched/zips/12345/policy-notes.md")

    assert "NorthStar Property Investment Consulting" in html
    assert "Property Policy Brief" in html
    assert "not legal, tax, or investment advice" in html


def test_brief_renders_sections_and_severity_chips():
    html = build_brief_html(NOTE, "researched/zips/12345/policy-notes.md")

    assert "Short-Term Rental (STR) Rules" in html
    # The severity marker is lifted out of the heading into a chip.
    assert 'class="sev high"' in html
    assert "HIGH ATTENTION" not in html
    assert 'class="sev med"' in html


def test_flags_table_becomes_a_styled_table():
    html = build_brief_html(NOTE, "researched/zips/12345/policy-notes.md")

    assert "<table>" in html and "<th>" in html
    assert "Rentals capped by HOA" in html
    # The |---|---| separator must not become a table row.
    assert "<td>---</td>" not in html


def test_source_tags_become_chips():
    html = build_brief_html(NOTE.replace("OK official", "\u2705 official"), "n.md")

    assert 'class="tag official"' in html


def test_bottom_line_is_built_from_the_notes_own_flags():
    html = build_brief_html(NOTE, "researched/zips/12345/policy-notes.md")

    assert "Bottom line for an investor" in html
    assert "1 high-attention issue" in html
    # Declared facts are surfaced, translated into investor language.
    assert "Not available" in html  # short_term_rental_allowed: false
    assert "2.5% per year" in html


def test_a_clean_note_gets_a_positive_bottom_line():
    clean = "# Policy Notes - Quiet Town\n\n## 1. Rules\n\n- Nothing notable.\n"

    html = build_brief_html(clean, "n.md")

    assert "callout positive" in html
    assert "no high-attention regulatory issues" in html


def test_machine_readable_block_is_not_shown_to_a_client():
    html = build_brief_html(NOTE, "researched/zips/12345/policy-notes.md")

    assert "Machine-Readable" not in html
    assert "rent_growth_cap_percent" not in html


def test_note_content_cannot_inject_markup():
    hostile = (
        "# Policy Notes - Somewhere\n\n"
        "## 1. Rules\n\n"
        "- <script>alert(1)</script> and <img src=x onerror=alert(1)>\n"
    )

    html = build_brief_html(hostile, "n.md")

    # What matters is that no live tag survives. The payload text may still
    # appear, escaped, as visible content - that is inert and correct.
    assert "<script" not in html.lower()
    assert not re.search(r"<img", html, re.I)
    assert "&lt;script&gt;" in html and "&lt;img" in html


def test_links_survive_but_are_attribute_escaped():
    html = build_brief_html(NOTE, "n.md")

    assert '<a href="https://city.example.gov">City</a>' in html


def test_brief_names_the_source_note_for_traceability():
    html = build_brief_html(NOTE, "researched/zips/12345/policy-notes.md")

    assert "researched/zips/12345/policy-notes.md" in html


def test_build_brief_reads_from_disk_and_names_the_download(tmp_path):
    folder = tmp_path / "researched" / "zips" / "12345"
    folder.mkdir(parents=True)
    (folder / "policy-notes.md").write_text(NOTE, encoding="utf-8")

    brief = build_brief("researched/zips/12345/policy-notes.md", root=tmp_path)

    assert brief["filename"].startswith("policy-brief-")
    assert brief["filename"].endswith(".html")
    assert "Property Policy Brief" in brief["html"]


def test_build_brief_refuses_a_missing_note(tmp_path):
    with pytest.raises(FileNotFoundError):
        build_brief("researched/zips/00000/policy-notes.md", root=tmp_path)


def test_build_brief_refuses_a_pdf(tmp_path):
    folder = tmp_path / "user" / "zips" / "12345"
    folder.mkdir(parents=True)
    (folder / "hoa.pdf").write_bytes(b"%PDF-1.4")

    with pytest.raises(ValueError):
        build_brief("user/zips/12345/hoa.pdf", root=tmp_path)


def test_build_brief_blocks_path_traversal(tmp_path):
    for attempt in ("../escape.md", "zips/../../escape.md", "C:/Windows/evil.md"):
        with pytest.raises((ValueError, FileNotFoundError)):
            build_brief(attempt, root=tmp_path)


def test_heading_marker_is_removed_without_orphaning_punctuation():
    """"Rent Control - WARN HIGH ATTENTION (two regimes)" must not keep the dash."""
    note = (
        "# Policy Notes - Somewhere\n\n"
        "## 3. Rent Control \u2014 \u26a0 HIGH ATTENTION (two overlapping regimes)\n\n"
        "- A fact.\n"
    )

    html = build_brief_html(note, "n.md")

    assert "Rent Control (two overlapping regimes)" in html
    assert "\u26a0 (two" not in html
    assert 'class="sev high"' in html
