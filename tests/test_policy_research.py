"""Tests for automatic policy research.

None of these make a network call. The point of the module is that every path
that could reach the API is guarded, so the guards are what get tested.
"""

import pytest

from app import policy_research


def test_kill_switch_blocks_research_even_with_a_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-not-a-real-key")
    monkeypatch.setenv("NORTHSTAR_DISABLE_AUTO_RESEARCH", "1")

    ready = policy_research.availability()

    assert ready["available"] is False
    assert "turned off" in ready["reason"]


def test_missing_key_is_reported_not_crashed(monkeypatch):
    monkeypatch.delenv("NORTHSTAR_DISABLE_AUTO_RESEARCH", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    # A real .env on the developer's machine must not leak into this test.
    monkeypatch.setattr(policy_research, "load_env_file", lambda *a, **k: None)

    ready = policy_research.availability()

    assert ready["available"] is False
    # The message must name a concrete remedy, not just state a failure.
    assert "Setup_Research.bat" in ready["reason"]


def test_env_file_does_not_override_a_real_environment_variable(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "from-environment")
    env = tmp_path / ".env"
    env.write_text("ANTHROPIC_API_KEY=from-file\n", encoding="utf-8")

    policy_research.load_env_file(env)

    import os

    assert os.environ["ANTHROPIC_API_KEY"] == "from-environment"


def test_env_file_parses_comments_and_quotes(tmp_path, monkeypatch):
    monkeypatch.delenv("NORTHSTAR_TEST_VALUE", raising=False)
    env = tmp_path / ".env"
    env.write_text(
        "# a comment\n\nNORTHSTAR_TEST_VALUE=\"quoted value\"\nmalformed line\n",
        encoding="utf-8",
    )

    policy_research.load_env_file(env)

    import os

    assert os.environ["NORTHSTAR_TEST_VALUE"] == "quoted value"


def test_missing_env_file_is_not_an_error(tmp_path):
    policy_research.load_env_file(tmp_path / "does-not-exist.env")


def test_request_research_is_a_noop_when_unavailable(monkeypatch):
    # conftest sets the kill switch, so this is the default state under pytest.
    result = policy_research.request_research(
        "1 Main St", "Indianapolis", "IN", "46202"
    )

    assert result["state"] in {"unavailable", "done"}


def test_request_research_refuses_a_malformed_zip():
    result = policy_research.request_research("1 Main St", "Austin", "TX", "787")

    assert result["state"] == "idle"


def test_status_reports_done_for_a_zip_with_a_bundled_note():
    # 46202 ships with a researched note, so no research should ever be started.
    assert policy_research.status("46202")["state"] == "done"


def test_status_reports_idle_for_an_unresearched_zip():
    assert policy_research.status("00001")["state"] == "idle"


def test_a_failure_is_remembered_so_the_api_is_not_re_billed(monkeypatch):
    monkeypatch.setattr(
        policy_research, "availability", lambda: {"available": True, "reason": ""}
    )
    calls = []
    monkeypatch.setattr(
        policy_research,
        "_call_claude",
        lambda *args: calls.append(args) or (_ for _ in ()).throw(RuntimeError("boom")),
    )

    policy_research.request_research("1 Main St", "Nowhere", "KS", "67501")
    # The worker thread runs immediately; wait for it rather than sleeping.
    for thread in _research_threads("67501"):
        thread.join(timeout=10)

    assert policy_research.status("67501")["state"] == "failed"
    assert len(calls) == 1

    # A second analysis of the same address must not call the API again.
    policy_research.request_research("1 Main St", "Nowhere", "KS", "67501")
    assert len(calls) == 1

    # ...but an explicit retry may.
    policy_research.request_research("1 Main St", "Nowhere", "KS", "67501", force=True)
    for thread in _research_threads("67501"):
        thread.join(timeout=10)
    assert len(calls) == 2


def test_re_entering_while_a_pass_is_running_does_not_deadlock(monkeypatch):
    """A second analysis of the same address must not hang the request thread.

    `request_research` used to call `status()` while holding a non-reentrant
    lock, so this exact sequence deadlocked the server.
    """
    import threading

    release = threading.Event()
    monkeypatch.setattr(
        policy_research, "availability", lambda: {"available": True, "reason": ""}
    )
    monkeypatch.setattr(
        policy_research, "_call_claude", lambda *args: release.wait(10) and ""
    )

    policy_research.request_research("1 Main St", "Nowhere", "KS", "67504")
    try:
        # While the first pass is still blocked, ask again.
        second = policy_research.request_research("1 Main St", "Nowhere", "KS", "67504")
        assert second["state"] == "running"
        assert policy_research.status("67504")["state"] == "running"
    finally:
        release.set()
        for thread in _research_threads("67504"):
            thread.join(timeout=10)


def test_a_reply_that_is_not_a_policy_note_is_never_saved(monkeypatch, tmp_path):
    monkeypatch.setattr(
        policy_research, "availability", lambda: {"available": True, "reason": ""}
    )
    monkeypatch.setattr(policy_research, "KNOWLEDGE_BANK_DIR", tmp_path)
    monkeypatch.setattr(
        policy_research,
        "_call_claude",
        lambda *args: "I'm sorry, I could not research that address.",
    )

    policy_research.request_research("1 Main St", "Nowhere", "KS", "67502")
    for thread in _research_threads("67502"):
        thread.join(timeout=10)

    assert not policy_research.note_path("67502").exists()
    assert policy_research.status("67502")["state"] == "failed"


def test_a_real_note_is_saved_to_the_researched_root(monkeypatch, tmp_path):
    note = (
        "# Policy Notes - Nowhere, KS 67503 (Reno County)\n\n"
        "**Researched:** 2026-08-01\n\n"
        "## 1. Short-Term Rental (STR) Rules\n\n"
        "- No STR ordinance found. - [City](https://example.gov) - as of 2026-08-01\n"
    )
    monkeypatch.setattr(
        policy_research, "availability", lambda: {"available": True, "reason": ""}
    )
    monkeypatch.setattr(policy_research, "KNOWLEDGE_BANK_DIR", tmp_path)
    monkeypatch.setattr(policy_research, "_call_claude", lambda *args: note)

    policy_research.request_research("1 Main St", "Nowhere", "KS", "67503")
    for thread in _research_threads("67503"):
        thread.join(timeout=10)

    saved = policy_research.note_path("67503")
    assert saved.exists()
    assert saved.read_text(encoding="utf-8").startswith("# Policy Notes")
    # The note must land under researched/, the root only the Skill may write to.
    assert saved.relative_to(tmp_path).parts[0] == "researched"
    assert policy_research.status("67503")["state"] == "done"


def test_the_system_prompt_is_the_skill_itself():
    prompt = policy_research._system_prompt()

    # Frontmatter is stripped; the workflow the manual path uses is kept.
    assert not prompt.lstrip().startswith("---")
    assert "Use web search for every regulatory fact" in prompt
    assert "NorthStar Machine-Readable Summary" in prompt


def test_the_task_prompt_names_the_exact_address():
    prompt = policy_research.build_task_prompt(
        "2682 Bennington Pl", "Maryland Heights", "mo", "63043"
    )

    assert "2682 Bennington Pl, Maryland Heights, MO 63043" in prompt
    # The backend has no filesystem tools, so the model must return the note.
    assert "cannot write files" in prompt


def _research_threads(zip_code: str):
    import threading

    return [
        thread
        for thread in threading.enumerate()
        if thread.name == f"policy-research-{zip_code}"
    ]


def test_a_stale_note_can_refresh_itself(monkeypatch, tmp_path):
    """A stale note used to block its own refresh forever.

    The report asks for research precisely because the note is old; the presence
    of the file on disk must not be the reason research is declined.
    """
    monkeypatch.setattr(
        policy_research, "availability", lambda: {"available": True, "reason": ""}
    )
    monkeypatch.setattr(policy_research, "KNOWLEDGE_BANK_DIR", tmp_path)

    stale = policy_research.note_path("67510")
    stale.parent.mkdir(parents=True)
    stale.write_text(
        "# Policy Notes - Old Town\n\n**Researched:** 2019-01-01\n\n"
        "## 1. Rules\n\n- Something from years ago.\n",
        encoding="utf-8",
    )
    assert policy_research.note_is_stale("67510") is True

    calls = []
    fresh = (
        "# Policy Notes - Old Town, KS 67510\n\n**Researched:** 2026-08-02\n\n"
        "## 1. Short-Term Rental (STR) Rules\n\n- Fresh finding.\n"
    )
    monkeypatch.setattr(
        policy_research, "_call_claude", lambda *a: calls.append(a) or fresh
    )

    # Without permission, an existing file still wins - that is the cost guard.
    policy_research.request_research("1 Main St", "Old Town", "KS", "67510")
    assert calls == []

    # With permission, the stale note is replaced.
    policy_research.request_research(
        "1 Main St", "Old Town", "KS", "67510", refresh_stale=True
    )
    for thread in _research_threads("67510"):
        thread.join(timeout=10)

    assert len(calls) == 1
    assert "Fresh finding" in stale.read_text(encoding="utf-8")
    assert policy_research.note_is_stale("67510") is False


def test_a_current_note_is_never_re_researched(monkeypatch, tmp_path):
    monkeypatch.setattr(
        policy_research, "availability", lambda: {"available": True, "reason": ""}
    )
    monkeypatch.setattr(policy_research, "KNOWLEDGE_BANK_DIR", tmp_path)

    current = policy_research.note_path("67511")
    current.parent.mkdir(parents=True)
    current.write_text(
        "# Policy Notes - New Town\n\n**Researched:** 2026-08-01\n\n"
        "## 1. Rules\n\n- Recent finding.\n",
        encoding="utf-8",
    )

    calls = []
    monkeypatch.setattr(policy_research, "_call_claude", lambda *a: calls.append(a) or "")

    policy_research.request_research(
        "1 Main St", "New Town", "KS", "67511", refresh_stale=True
    )

    assert calls == [], "a fresh note must never be re-billed"


def test_credentials_are_found_from_an_oauth_profile(monkeypatch, tmp_path):
    """A Claude login counts: users should not need to mint an API key."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    credentials = tmp_path / "credentials"
    credentials.mkdir()
    (credentials / "default.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(policy_research, "_profile_dir", lambda: tmp_path)

    assert policy_research.has_credentials() is True


def test_no_credentials_anywhere_is_reported_not_assumed(monkeypatch, tmp_path):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    monkeypatch.setattr(policy_research, "_profile_dir", lambda: tmp_path / "nope")

    assert policy_research.has_credentials() is False


def test_an_agent_cli_is_preferred_over_an_api_key(monkeypatch):
    """A signed-in CLI needs no configuration, so it wins."""
    monkeypatch.delenv("NORTHSTAR_DISABLE_AUTO_RESEARCH", raising=False)
    monkeypatch.setattr(policy_research, "load_env_file", lambda *a, **k: None)
    monkeypatch.setattr(
        policy_research, "find_agent_cli", lambda: ("C:/npm/codex.cmd", ["exec", "-"])
    )

    ready = policy_research.availability()

    assert ready["available"] is True
    assert ready["backend"] == "cli:codex"


def test_no_cli_and_no_key_names_both_ways_to_fix_it(monkeypatch):
    monkeypatch.delenv("NORTHSTAR_DISABLE_AUTO_RESEARCH", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    monkeypatch.setattr(policy_research, "load_env_file", lambda *a, **k: None)
    monkeypatch.setattr(policy_research, "find_agent_cli", lambda: None)
    monkeypatch.setattr(policy_research, "has_credentials", lambda: False)

    ready = policy_research.availability()

    assert ready["available"] is False
    assert "codex" in ready["reason"] and "Setup_Research.bat" in ready["reason"]


def test_note_is_extracted_from_a_cli_transcript():
    """A CLI wraps the answer in a banner, tool calls, and a token count."""
    transcript = (
        "--------\nworkdir: C:\\project\nmodel: gpt-5.5\n--------\n"
        "user\nRun policy diligence...\n"
        "web search: Ballwin short term rental\n"
        "codex\n"
        "# Policy Notes - Ballwin, MO 63021\n\n"
        "## 1. Short-Term Rental (STR) Rules\n\n- A finding.\n"
        "tokens used\n24,492\n"
    )

    note = policy_research._extract_note(transcript)

    assert note.startswith("# Policy Notes - Ballwin")
    assert "- A finding." in note
    assert "tokens used" not in note
    assert "workdir" not in note and "web search:" not in note


def test_the_longest_copy_wins_when_a_cli_echoes_its_answer():
    """CLIs often print the final message twice; a truncated echo must not win."""
    transcript = (
        "codex\n# Policy Notes - X\n\n## 1. Rules\n\n- Full body here.\n"
        "tokens used\n100\n"
        "# Policy Notes - X\n"
    )

    note = policy_research._extract_note(transcript)

    assert "Full body here." in note


def test_a_cli_that_cannot_search_the_web_writes_nothing(monkeypatch, tmp_path):
    """The Skill forbids answering regulatory questions from memory."""
    import subprocess

    monkeypatch.setattr(
        policy_research, "find_agent_cli", lambda: ("codex", ["exec", "-"])
    )
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a, 0, "NO_WEB_SEARCH", ""),
    )

    with pytest.raises(RuntimeError, match="web search"):
        policy_research._call_agent_cli("1 Main St", "Nowhere", "KS", "67520")


def test_a_failing_cli_reports_its_exit_code(monkeypatch):
    import subprocess

    monkeypatch.setattr(
        policy_research, "find_agent_cli", lambda: ("codex", ["exec", "-"])
    )
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a, 1, "", "not logged in"),
    )

    with pytest.raises(RuntimeError, match="exited with code 1"):
        policy_research._call_agent_cli("1 Main St", "Nowhere", "KS", "67521")
