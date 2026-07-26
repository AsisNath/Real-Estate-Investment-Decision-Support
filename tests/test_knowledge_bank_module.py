"""Tests for browsing, rendering, and writing knowledge-bank notes."""

import pytest

from app.knowledge_bank import (
    build_folder,
    create_note,
    describe_scope,
    describe_source,
    parse_policy_note,
    read_note,
    render_markdown,
    safe_note_path,
    scan_knowledge_bank,
)


NOTE = """# Policy Notes - Somewhere, ST 12345 (Example County)

**Researched:** 2026-07-20
**Method:** Web search

## 1. Rules

- Deposit capped. - [State AG](https://ag.example.gov) - as of 2026-07-20 OK official
- Fee is $100. - [A blog](https://blog.example.com) - as of 2026-07-20 confirm with city
- **Unverified for this specific property:** obtain the recorded CC&Rs from the county.

## 5. High-Attention Flags (summary for NorthStar report)

| Flag | Severity | Why |
|---|---|---|
| Rentals capped by HOA | HIGH | Can void the rental strategy |

## NorthStar Machine-Readable Summary

- rent_growth_cap_percent: 2.5
- short_term_rental_allowed: false
- security_deposit_cap_months: none
"""


def test_parses_facts_with_types():
    facts = parse_policy_note(NOTE)["facts"]

    assert facts["rent_growth_cap_percent"] == 2.5
    assert facts["short_term_rental_allowed"] is False
    assert facts["security_deposit_cap_months"] is None


def test_parses_diligence_items():
    diligence = parse_policy_note(NOTE)["diligence"]

    assert any("recorded CC&Rs" in item for item in diligence)
    # Markdown formatting is stripped for display.
    assert not any("**" in item for item in diligence)


def test_computes_note_age_and_staleness():
    parsed = parse_policy_note(NOTE)

    assert parsed["researched_date"] == "2026-07-20"
    assert parsed["days_old"] is not None and parsed["days_old"] >= 0


def test_handles_note_without_any_structure():
    parsed = parse_policy_note("Just a plain text note about a lease.")

    assert parsed["flags"] == []
    assert parsed["facts"] == {}
    assert parsed["researched"] is None


def test_render_markdown_produces_links_and_tables():
    html = render_markdown(NOTE)

    assert "<table>" in html
    assert 'href="https://ag.example.gov"' in html


def test_render_markdown_strips_scripts():
    html = render_markdown("# Title\n\n<script>alert(1)</script>\n")

    assert "<script>" not in html


def test_describe_scope_explains_folders():
    assert describe_scope("global") == "Every property"
    assert describe_scope("states/TX") == "Any property in TX"
    assert describe_scope("zips/78704") == "ZIP 78704"
    assert "TX 78704" in describe_scope("tx-78704")


def test_describe_scope_strips_the_root_prefix():
    assert describe_scope("researched/zips/78704") == "ZIP 78704"
    assert describe_scope("user/states/TX") == "Any property in TX"
    assert describe_scope("user/global") == "Every property"


def test_describe_source_identifies_the_root():
    assert describe_source("researched/zips/78704") == "researched"
    assert describe_source("user/global") == "user"
    assert describe_source("tx-78704") == "legacy"
    assert describe_source("zips/78704") == "legacy"


def test_scan_reports_every_note(tmp_path):
    (tmp_path / "researched" / "zips" / "12345").mkdir(parents=True)
    (tmp_path / "researched" / "zips" / "12345" / "policy-notes.md").write_text(NOTE, encoding="utf-8")
    (tmp_path / "README.md").write_text("# ignore me", encoding="utf-8")

    inventory = scan_knowledge_bank(tmp_path)

    assert inventory["note_count"] == 1
    assert inventory["high_flag_total"] == 1
    note = inventory["notes"][0]
    assert note["applies_to"] == "ZIP 12345"
    assert note["source"] == "researched"
    assert note["flag_counts"]["high"] == 1
    assert note["diligence_count"] >= 1


def test_scan_of_empty_bank(tmp_path):
    inventory = scan_knowledge_bank(tmp_path)

    assert inventory["note_count"] == 0
    assert inventory["notes"] == []


def test_build_folder_for_each_scope():
    # Every scope choice lands under user/: build_folder backs the in-app
    # form, and anything a form submits is user-provided by definition.
    assert build_folder("global") == "user/global"
    assert build_folder("state", "tx") == "user/states/TX"
    assert build_folder("zip", "78704") == "user/zips/78704"
    assert build_folder("city", "Saint Charles", "MO") == "user/cities/saint_charles_mo"
    assert build_folder("custom", "lenders/acme bank") == "user/lenders/acme_bank"


def test_build_folder_rejects_bad_values():
    with pytest.raises(ValueError):
        build_folder("zip", "787")
    with pytest.raises(ValueError):
        build_folder("state", "Texas")
    with pytest.raises(ValueError):
        build_folder("nonsense", "x")
    with pytest.raises(ValueError):
        # The old Lab-5-style "researched" scope is gone: only the Skill
        # itself writes into researched/, never the in-app form.
        build_folder("researched", "78704", "tx")


def test_create_note_refuses_the_researched_root(tmp_path):
    with pytest.raises(ValueError):
        create_note("researched/zips/78704", "note.md", "content", root=tmp_path)

    assert not (tmp_path / "researched").exists()


def test_create_and_read_a_user_note(tmp_path):
    result = create_note("zips/46202", "hoa-rules.md", "# My HOA rules\n\n- No rentals.\n", root=tmp_path)

    assert result["relative_path"] == "zips/46202/hoa-rules.md"
    assert result["applies_to"] == "ZIP 46202"

    note = read_note("zips/46202/hoa-rules.md", root=tmp_path)
    assert "My HOA rules" in note["content"]
    assert "<h1" in note["html"]


def test_create_note_adds_missing_extension(tmp_path):
    result = create_note("global", "lender-terms", "Some terms.", root=tmp_path)

    assert result["relative_path"].endswith("lender-terms.md")


def test_create_note_refuses_overwrite_unless_asked(tmp_path):
    create_note("global", "note.md", "first", root=tmp_path)

    with pytest.raises(FileExistsError):
        create_note("global", "note.md", "second", root=tmp_path)

    create_note("global", "note.md", "second", overwrite=True, root=tmp_path)
    assert read_note("global/note.md", root=tmp_path)["content"].strip() == "second"


def test_create_note_rejects_empty_content(tmp_path):
    with pytest.raises(ValueError):
        create_note("global", "note.md", "   ", root=tmp_path)


def test_path_traversal_is_blocked(tmp_path):
    for attempt in ("../escape.md", "zips/../../escape.md", "/etc/passwd", "C:/Windows/evil.md"):
        with pytest.raises(ValueError):
            safe_note_path(attempt, tmp_path)


def test_create_note_cannot_escape_the_folder(tmp_path):
    with pytest.raises(ValueError):
        create_note("../outside", "evil.md", "content", root=tmp_path)

    assert not (tmp_path.parent / "outside").exists()
