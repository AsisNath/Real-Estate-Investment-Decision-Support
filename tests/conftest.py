"""Shared test setup.

The one thing that matters here: tests must never call a paid API. `/api/analyze`
now kicks off automatic policy research, and a developer with a working key in
`.env` would otherwise be billed - and would hit the network - just by running
`pytest`. The kill switch makes that impossible.
"""

import pytest

from app import policy_research


@pytest.fixture(autouse=True)
def no_paid_research(monkeypatch):
    monkeypatch.setenv("NORTHSTAR_DISABLE_AUTO_RESEARCH", "1")
    # Research can also run by shelling out to a signed-in agent CLI. On a
    # developer machine that CLI is usually present and logged in, so without
    # this a test that stubs the API path would silently launch the real thing
    # and spend the developer's own quota.
    monkeypatch.setattr(policy_research, "find_agent_cli", lambda: None)
    policy_research.reset()
    yield
    policy_research.reset()
