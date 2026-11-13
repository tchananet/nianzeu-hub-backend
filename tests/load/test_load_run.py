"""The executable Q02 run. Gated twice: the ``load`` marker and ``Q02_LOAD_TEST=1``.

``pytest -q`` collects this module and skips it, so the default suite is unaffected.
To obtain real numbers, see the operator procedure in docs/qa/load.md.
"""

from __future__ import annotations

import os

import pytest

from tests.load import attribution, report, runner, seeding
from tests.load.config import from_env

pytestmark = [
    pytest.mark.load,
    pytest.mark.skipif(
        os.getenv("Q02_LOAD_TEST") != "1",
        reason="Q02 load run: needs Q02_LOAD_TEST=1 and an authorised test VPS",
    ),
]


@pytest.fixture(scope="module")
def config():
    return from_env()


def test_quota_attribution_is_per_source(config):
    """Preflight. Without this, the run would measure its own rate limiting."""
    result = attribution.require_per_source(config)
    print(f"quota attribution: {result.verdict()} ({result.burn_statuses})")


def test_refusal_path_is_the_contracted_429(config):
    """The separate quota scenario: one source, 429 expected, thresholds N/A."""
    statuses = attribution.refusal_scenario(config)
    assert statuses.get(429, 0) > 0, statuses
    assert statuses.get(200, 0) > 0, statuses


def test_plateau_meets_a01_thresholds(config, capsys):
    outcome = seeding.seed(config)
    assert outcome.complete, f"seeding incomplete: {outcome.refused}"
    skills = seeding.skill_ids(config)
    profile_ids = sorted(outcome.profile_ids.values())
    result = runner.run(config, profile_ids, skills)
    rendered = report.render(config, result)
    with capsys.disabled():
        print(rendered)
    assert result.login_failures == 0, f"{result.login_failures} virtual users never logged in"
    assert '"verdict": "PASS"' in rendered, rendered
