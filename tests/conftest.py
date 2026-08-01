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
    policy_research.reset()
    yield
    policy_research.reset()
