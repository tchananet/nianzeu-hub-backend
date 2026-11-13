"""Offline checks of the harness's pure parts: no network, no target, always runs.
They prove the harness is wired correctly; they prove nothing about capacity."""

from __future__ import annotations

import pytest

from tests.load import cleanup
from tests.load.config import LoadConfig, ProductionTargetRefused, target_is_disposable
from tests.load.corpus import accounts, profile_body, source_address
from tests.load.journeys import MIX, mix_is_valid
from tests.load.metrics import Recorder, percentile
from tests.load.phases import Phases
from tests.load.seeding import registration_budget
from tests.load.thresholds import all_passed, evaluate

CONFIG = LoadConfig(base_url="http://127.0.0.1:8000", origin="http://127.0.0.1:3000",
                    password="x" * 16, run_id="offline", accounts=20, sources=4)


@pytest.mark.parametrize("host", ["127.0.0.1", "10.0.0.5", "api.test.example",
                                  "staging-api.example.com", "localhost"])
def test_disposable_hosts_accepted(host):
    assert target_is_disposable(host)


@pytest.mark.parametrize("host", ["api.diddifree.com", "diddifree.com", "8.8.8.8", ""])
def test_production_looking_hosts_refused(host):
    assert not target_is_disposable(host)


def test_config_refuses_a_production_target(monkeypatch):
    for name, value in [("Q02_TARGET_URL", "https://api.diddifree.com"),
                        ("Q02_ORIGIN", "https://diddifree.com"),
                        ("Q02_SEED_PASSWORD", "x" * 16), ("Q02_RUN_ID", "r1"),
                        ("Q02_TARGET_ACK", "api.diddifree.com")]:
        monkeypatch.setenv(name, value)
    from tests.load.config import from_env
    with pytest.raises(ProductionTargetRefused, match="not provably a test target"):
        from_env()


def test_mix_follows_the_architect_split():
    assert mix_is_valid()
    assert dict(MIX)["search"] == 50 and dict(MIX)["profile_update"] == 5


def test_corpus_is_identifiable_and_spread_over_sources():
    corpus = accounts(CONFIG)
    assert len(corpus) == 20
    assert all(account.email.startswith("q02-offline-") for account in corpus)
    assert len({account.source for account in corpus}) == 4
    assert source_address(0) == "203.0.113.1"


def test_profile_body_is_a_complete_write_payload():
    body = profile_body(accounts(CONFIG)[0], ["11111111-1111-1111-1111-111111111111"], 7)
    assert set(body) >= {"display_name", "headline", "city", "country_code", "rate",
                         "skill_ids", "experiences", "certifications", "contacts"}
    assert body["country_code"] == "CM"


def test_registration_budget_blocks_an_impossible_seed():
    assert registration_budget(CONFIG) == 20
    assert registration_budget(LoadConfig(base_url="http://localhost", origin="http://localhost",
                                          password="x", run_id="r", sources=100)) == 500


def test_percentiles_use_nearest_rank():
    assert percentile([], 0.95) == 0.0
    assert percentile([float(n) for n in range(1, 101)], 0.95) == 95.0
    assert percentile([5.0], 0.99) == 5.0


def test_phases_schedule_matches_a01():
    phases = Phases(300, 300, 1200, 120)
    assert (phases.plateau_start_s, phases.plateau_end_s, phases.total_s) == (600, 1800, 1920)
    assert phases.active_users(0, 100) == 10
    assert phases.active_users(450, 100) == 50
    assert phases.active_users(1000, 100) == 100
    assert phases.active_users(1860, 100) == 50
    assert phases.in_plateau(700) and not phases.in_plateau(599)


def test_unexpected_429_counts_as_an_error_and_fails_the_verdict():
    recorder = Recorder()
    for _ in range(99):
        recorder.record("search", 200, 10.0, 0)
    recorder.record("search", 429, 5.0, 0)
    assert recorder.error_rate() == pytest.approx(0.01)
    assert recorder.rate_limited_rate() == pytest.approx(0.01)
    assert not all_passed(evaluate(recorder, 1200.0))


def test_cleanup_sql_targets_only_the_run_prefix():
    sql = cleanup.removal_sql("abc123")
    assert "LIKE 'q02-abc123-%'" in sql
    with pytest.raises(ValueError):
        cleanup.removal_sql("a'; DROP TABLE users; --")
