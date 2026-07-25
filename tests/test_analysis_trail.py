"""Tests for the analysis trail written beside each ZIP's notes."""

import pytest

import app.data_loader as data_loader
import app.knowledge_bank as knowledge_bank
from app.knowledge_bank import (
    ANALYSIS_LOG_NAME,
    is_trace_file,
    read_trace,
    record_analysis,
    scan_knowledge_bank,
)


REPORT = {
    "property": {"address": "725 N Delaware St", "city": "Indianapolis", "state": "IN", "zip_code": "46202"},
    "market": {"market_name": "Indianapolis sample", "match_level": "zip"},
    "policy": {
        "jurisdiction_name": "Indianapolis / Marion County sample",
        "match_level": "zip",
        "jurisdiction_levels": ["Indianapolis / Marion County sample"],
        "restriction_flags": [{"title": "STR permit required", "level": "high"}],
    },
    "knowledge_bank": {"documents": [{"relative_path": "zips/46202/hoa.md"}]},
    "location_check": {"status": "ok"},
    "assumption_conflicts": [],
    "recommendation": {"status": "Investigate Further"},
    "overall_risk": "medium",
}


def test_records_the_sources_behind_a_recommendation(tmp_path):
    relative = record_analysis(REPORT, root=tmp_path)

    assert relative == f"zips/46202/{ANALYSIS_LOG_NAME}"
    content = (tmp_path / "zips" / "46202" / ANALYSIS_LOG_NAME).read_text(encoding="utf-8")
    assert "725 N Delaware St" in content
    assert "Investigate Further" in content
    assert "Indianapolis / Marion County sample" in content
    assert "zips/46202/hoa.md" in content
    assert "STR permit required (high)" in content


def test_appends_newest_entry_first(tmp_path):
    record_analysis(REPORT, root=tmp_path)
    second = dict(REPORT)
    second["recommendation"] = {"status": "Reject"}
    record_analysis(second, root=tmp_path)

    content = (tmp_path / "zips" / "46202" / ANALYSIS_LOG_NAME).read_text(encoding="utf-8")
    assert content.count("## ") == 2
    assert content.index("Reject") < content.index("Investigate Further")


def test_log_is_capped(tmp_path, monkeypatch):
    monkeypatch.setattr(knowledge_bank, "MAX_LOG_ENTRIES", 3)
    for _ in range(6):
        record_analysis(REPORT, root=tmp_path)

    content = (tmp_path / "zips" / "46202" / ANALYSIS_LOG_NAME).read_text(encoding="utf-8")
    assert content.count("## ") == 3


def test_bad_zip_is_skipped_quietly(tmp_path):
    report = dict(REPORT)
    report["property"] = {"address": "x", "city": "y", "state": "ZZ", "zip_code": "bad"}

    assert record_analysis(report, root=tmp_path) is None
    assert not list(tmp_path.rglob("*.md"))


def test_write_failure_never_breaks_analysis(tmp_path, monkeypatch):
    def boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("pathlib.Path.write_text", boom)
    assert record_analysis(REPORT, root=tmp_path) is None


def test_trace_files_are_not_read_as_policy_notes(tmp_path, monkeypatch):
    record_analysis(REPORT, root=tmp_path)
    monkeypatch.setattr(data_loader, "KNOWLEDGE_BANK_DIR", tmp_path)

    context = data_loader.load_knowledge_bank_context(
        "725 N Delaware St", "Indianapolis", "IN", "46202"
    )

    assert context["documents"] == []
    assert context["researched_flags"] == []


def test_scan_lists_traces_separately(tmp_path):
    record_analysis(REPORT, root=tmp_path)
    (tmp_path / "zips" / "46202" / "hoa.md").write_text("# HOA note", encoding="utf-8")

    inventory = scan_knowledge_bank(tmp_path)

    assert [note["name"] for note in inventory["notes"]] == ["hoa.md"]
    assert [trace["name"] for trace in inventory["traces"]] == [ANALYSIS_LOG_NAME]
    assert inventory["traces"][0]["entry_count"] == 1


def test_read_trace_returns_rendered_html(tmp_path):
    record_analysis(REPORT, root=tmp_path)

    trace = read_trace(f"zips/46202/{ANALYSIS_LOG_NAME}", root=tmp_path)

    assert "Analysis trail" in trace["content"]
    assert "<h2" in trace["html"]


def test_read_trace_refuses_a_normal_note(tmp_path):
    (tmp_path / "global").mkdir()
    (tmp_path / "global" / "note.md").write_text("# note", encoding="utf-8")

    with pytest.raises(FileNotFoundError):
        read_trace("global/note.md", root=tmp_path)


def test_is_trace_file():
    assert is_trace_file("_analysis-log.md")
    assert not is_trace_file("policy-notes.md")
