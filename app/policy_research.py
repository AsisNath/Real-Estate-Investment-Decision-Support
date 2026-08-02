"""Automatic policy research for addresses that have no researched note yet.

Until now, filling `knowledge_bank/researched/` was a manual step: the app told
the user to paste a prompt into a chat, and the property-policy-research Skill
did the work. This module removes that step. When an analysis runs against a
location with no researched note, the app calls the Claude API itself - with
live web search - and writes the resulting note into the same folder the Skill
writes to, in the same format.

Three properties of that design matter:

1. **The Skill file is still the single source of truth for the note format.**
   The system prompt below is the Skill's own `SKILL.md`, read off disk. Editing
   the Skill changes both the manual path and this automatic one, so the two can
   never drift apart.

2. **Research runs in the background.** A real research pass makes a dozen web
   searches and takes one to three minutes. Blocking `/api/analyze` on that would
   make the app feel broken, so `/api/analyze` returns immediately and the browser
   polls `/api/research/status`.

3. **It degrades to the old behaviour, never to a wrong answer.** No API key, no
   `anthropic` package, no internet, or a failed call all leave the researched
   folder untouched and the report falls back to the copy-this-prompt panel. The
   deterministic financial model never depends on this module.

Cost note: each new address costs one Opus request with web search. A note is
researched once and then reused forever, and a failure is remembered so a broken
key cannot re-bill on every analysis.
"""

from __future__ import annotations

import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.knowledge_bank import parse_policy_note


BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_BANK_DIR = BASE_DIR / "knowledge_bank"
SKILL_FILE = BASE_DIR / ".claude" / "skills" / "property-policy-research" / "SKILL.md"
ENV_FILE = BASE_DIR / ".env"

# The claude-api guidance is explicit: use Opus unless the user picks otherwise.
# Policy research is exactly the intelligence-sensitive, verification-heavy work
# that a cheaper model gets wrong in ways that are hard to notice.
MODEL = "claude-opus-5"
EFFORT = "high"
MAX_TOKENS = 32000

# Server-side tool versions with dynamic filtering. These require Opus 4.6+ /
# Sonnet 4.6+; MODEL above satisfies that.
WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search", "max_uses": 14}
WEB_FETCH_TOOL = {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 10}

# A server-side tool loop can stop with `pause_turn` when it hits its own
# iteration cap. Re-sending resumes it; this bounds how many times we will.
MAX_CONTINUATIONS = 5

NOTE_FILENAME = "policy-notes.md"

_lock = threading.Lock()
_jobs: dict[str, dict[str, Any]] = {}


# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------


def load_env_file(path: Path = ENV_FILE) -> None:
    """Read KEY=value lines from a local .env into the environment.

    Keeps the API key out of the repository and out of the launcher script. An
    existing environment variable always wins, so an operator who exports the
    key directly is not overridden by a stale file.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return

    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _profile_dir() -> Path:
    """Where the Anthropic SDK and `ant` CLI keep OAuth login profiles."""
    if os.name == "nt":
        base = os.environ.get("APPDATA")
        if base:
            return Path(base) / "Anthropic"
    return Path.home() / ".config" / "anthropic"


def has_credentials() -> bool:
    """Can the SDK authenticate at all?

    An unset ANTHROPIC_API_KEY does not mean there are no credentials: the SDK
    also resolves an OAuth profile saved by `ant auth login`, which lets someone
    with a Claude login use this without creating or pasting an API key. Checking
    only the env var would tell those users the feature is unavailable when it is
    not.
    """
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return True

    credentials = _profile_dir() / "credentials"
    try:
        return any(credentials.glob("*.json"))
    except OSError:
        return False


def availability() -> dict[str, Any]:
    """Can this machine run automatic research right now?

    Answers before any billing happens, so the UI can be honest about whether
    the user needs to fall back to the manual prompt.
    """
    load_env_file()

    if os.environ.get("NORTHSTAR_DISABLE_AUTO_RESEARCH", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }:
        # The kill switch. The test suite sets this so a developer who has a key
        # in .env never gets billed by running `pytest`, and it lets anyone
        # demo the app in its original fully-offline mode.
        return {
            "available": False,
            "reason": "Automatic research is turned off (NORTHSTAR_DISABLE_AUTO_RESEARCH is set).",
        }

    try:
        import anthropic  # noqa: F401
    except ImportError:
        return {
            "available": False,
            "reason": (
                "The `anthropic` package is not installed. Run "
                "`pip install -r requirements.txt` and restart the app."
            ),
        }

    if not has_credentials():
        return {
            "available": False,
            "reason": (
                "No Anthropic credentials found. Run Setup_Research.bat to create "
                "your .env file and paste an API key into it, then restart the app."
            ),
        }

    if not SKILL_FILE.exists():
        return {
            "available": False,
            "reason": f"The research Skill is missing at {SKILL_FILE.name}.",
        }

    return {"available": True, "reason": ""}


# --------------------------------------------------------------------------
# Job bookkeeping
# --------------------------------------------------------------------------


def note_path(zip_code: str) -> Path:
    return KNOWLEDGE_BANK_DIR / "researched" / "zips" / zip_code / NOTE_FILENAME


def _job_key(zip_code: str) -> str:
    return zip_code.strip()


def _snapshot(zip_code: str) -> dict[str, Any]:
    """Current state for one ZIP, safe to hand to the browser."""
    key = _job_key(zip_code)
    with _lock:
        job = dict(_jobs.get(key, {}))

    if job.get("state") == "running":
        return {
            "zip_code": key,
            "state": "running",
            "message": "Researching local rental policy with live web search. This usually takes one to three minutes.",
            "started_at": job.get("started_at"),
        }
    if job.get("state") == "failed":
        return {
            "zip_code": key,
            "state": "failed",
            "message": job.get("error", "The research call failed."),
            "started_at": job.get("started_at"),
        }
    if note_path(key).exists():
        return {
            "zip_code": key,
            "state": "done",
            "message": "A researched policy note is on file for this ZIP.",
            "relative_path": f"researched/zips/{key}/{NOTE_FILENAME}",
        }
    return {"zip_code": key, "state": "idle", "message": ""}


def status(zip_code: str) -> dict[str, Any]:
    """Poll target for the browser."""
    snapshot = _snapshot(zip_code)
    snapshot["availability"] = availability()
    return snapshot


def note_is_stale(zip_code: str) -> bool:
    """Is the existing note past the freshness window?

    Regulations change; a note researched two years ago is not evidence about
    today. Staleness is read from the note itself rather than the file's mtime,
    because copying or re-saving a file does not make its facts current.
    """
    path = note_path(_job_key(zip_code))
    try:
        return bool(parse_policy_note(path.read_text(encoding="utf-8", errors="ignore"))["is_stale"])
    except (OSError, KeyError):
        return False


def request_research(
    address: str,
    city: str,
    state: str,
    zip_code: str,
    force: bool = False,
    refresh_stale: bool = False,
) -> dict[str, Any]:
    """Start a background research pass for this address if one is warranted.

    Returns immediately. Doing nothing is a normal, common outcome: a current
    note may already exist, a pass may already be running, or a previous attempt
    may have failed and we refuse to re-bill for it without an explicit `force`.

    `refresh_stale` lets an existing but out-of-date note be researched again.
    Without it a stale note blocked its own refresh forever - the report asked
    for research because the note was stale, and this function declined because
    a file was present.
    """
    key = _job_key(zip_code)
    if not re.fullmatch(r"\d{5}", key):
        return {"zip_code": key, "state": "idle", "message": "", "availability": availability()}

    if note_path(key).exists() and not force:
        if not (refresh_stale and note_is_stale(key)):
            return status(key)

    ready = availability()
    if not ready["available"]:
        return {
            "zip_code": key,
            "state": "unavailable",
            "message": ready["reason"],
            "availability": ready,
        }

    # Decide inside the lock, report outside it. `status()` takes the same lock,
    # and it is a plain (non-reentrant) Lock, so calling it from in here would
    # deadlock the request thread - which is exactly what happens when a second
    # analysis of the same address arrives while research is running.
    with _lock:
        existing_state = _jobs.get(key, {}).get("state")
        # A failure that repeats on every analysis is a cost leak and a
        # nuisance. Surface it once and wait to be asked again.
        already_handled = existing_state == "running" or (
            existing_state == "failed" and not force
        )
        if not already_handled:
            _jobs[key] = {
                "state": "running",
                "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }

    if already_handled:
        return status(key)

    worker = threading.Thread(
        target=_run_research,
        args=(address, city, state, key),
        name=f"policy-research-{key}",
        daemon=True,
    )
    worker.start()
    return status(key)


def reset(zip_code: str | None = None) -> None:
    """Forget remembered job state. Used by tests and by an explicit retry."""
    with _lock:
        if zip_code is None:
            _jobs.clear()
        else:
            _jobs.pop(_job_key(zip_code), None)


# --------------------------------------------------------------------------
# The research pass
# --------------------------------------------------------------------------


def build_task_prompt(address: str, city: str, state: str, zip_code: str) -> str:
    """The instruction sent to the model, mirroring the manual copy-paste prompt."""
    return (
        f"Run policy diligence on {address}, {city}, {state.upper()} {zip_code}.\n\n"
        "Follow the Property Policy Research workflow exactly. Use web search for "
        "every regulatory fact and verify load-bearing facts against official "
        "(.gov or statute) sources.\n\n"
        "You are running inside an automated backend and cannot write files. Do not "
        "call any file-writing tool and do not describe saving the file. Instead, "
        "return the finished note as your final message: plain Markdown starting "
        "with the `# Policy Notes - ...` heading and ending with the last section. "
        "No preamble, no closing commentary, no code fences around the note."
    )


def _system_prompt() -> str:
    """The Skill itself, so the automatic path cannot drift from the manual one."""
    skill = SKILL_FILE.read_text(encoding="utf-8")
    # Strip the YAML frontmatter: it is trigger metadata for the Skill loader,
    # not instructions for the model.
    body = re.sub(r"^---\n.*?\n---\n", "", skill, count=1, flags=re.DOTALL)
    return (
        "You are the property-policy-research Skill running inside the NorthStar "
        "Property Investment Consulting app. Follow these instructions exactly.\n\n"
        f"{body}"
    )


def _collect_text(message: Any) -> str:
    return "".join(block.text for block in message.content if block.type == "text")


def _looks_like_a_note(text: str) -> bool:
    """Refuse to save something that is not actually a policy note.

    A refusal, an apology, or a "here is what I found" chat reply would otherwise
    be parsed as policy and shown next to the financial model.
    """
    stripped = text.strip()
    return stripped.startswith("# Policy Notes") and "## 1." in stripped


def _run_research(address: str, city: str, state: str, zip_code: str) -> None:
    try:
        note = _call_claude(address, city, state, zip_code)
    except Exception as error:  # noqa: BLE001 - a background thread must not die silently
        _record_failure(zip_code, _describe_error(error))
        return

    if not _looks_like_a_note(note):
        _record_failure(
            zip_code,
            "The research call returned something that is not a policy note, so "
            "nothing was saved. Use the copy-and-paste prompt below instead.",
        )
        return

    try:
        target = note_path(zip_code)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(note.strip() + "\n", encoding="utf-8")
    except OSError as error:
        _record_failure(zip_code, f"Could not write the note: {error}")
        return

    with _lock:
        _jobs.pop(_job_key(zip_code), None)


def _call_claude(address: str, city: str, state: str, zip_code: str) -> str:
    import anthropic

    client = anthropic.Anthropic()
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": build_task_prompt(address, city, state, zip_code)}
    ]

    for _ in range(MAX_CONTINUATIONS):
        # Streaming, not blocking: a research pass runs for minutes and a large
        # max_tokens on a non-streaming request risks an HTTP timeout.
        with client.messages.stream(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=_system_prompt(),
            thinking={"type": "adaptive"},
            output_config={"effort": EFFORT},
            tools=[WEB_SEARCH_TOOL, WEB_FETCH_TOOL],
            messages=messages,
        ) as stream:
            message = stream.get_final_message()

        if message.stop_reason == "refusal":
            raise RuntimeError(
                "Claude declined this research request. Nothing was saved."
            )

        if message.stop_reason == "pause_turn":
            # The server-side search loop hit its iteration cap. Re-send the
            # conversation as-is and it resumes where it stopped.
            messages = messages[:1] + [{"role": "assistant", "content": message.content}]
            continue

        return _collect_text(message)

    raise RuntimeError(
        "The research pass did not finish after several continuations. Nothing was saved."
    )


def _describe_error(error: Exception) -> str:
    """Turn an SDK exception into something an investor can act on."""
    try:
        import anthropic
    except ImportError:
        return f"Automatic research failed: {error}"

    if isinstance(error, anthropic.AuthenticationError):
        return "The Anthropic API key was rejected. Check the key in your .env file."
    if isinstance(error, anthropic.PermissionDeniedError):
        return "This API key does not have access to the model or the web search tool."
    if isinstance(error, anthropic.RateLimitError):
        return "The Anthropic API rate limit was hit. Try the research again shortly."
    if isinstance(error, anthropic.APIConnectionError):
        return (
            "Could not reach the Anthropic API. Automatic research needs an internet "
            "connection; the rest of this report does not."
        )
    if isinstance(error, anthropic.APIStatusError):
        return f"The Anthropic API returned an error ({error.status_code}). Nothing was saved."
    return f"Automatic research failed: {error}"


def _record_failure(zip_code: str, message: str) -> None:
    with _lock:
        _jobs[_job_key(zip_code)] = {
            "state": "failed",
            "error": message,
            "started_at": _jobs.get(_job_key(zip_code), {}).get("started_at"),
        }
