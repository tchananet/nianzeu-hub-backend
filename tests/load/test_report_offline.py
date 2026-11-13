"""Offline check of the reporting path: a synthetic run renders without a target."""

from __future__ import annotations

import json

from tests.load.config import LoadConfig
from tests.load.report import OPERATOR_SUPPLIED, render
from tests.load.runner import RunResult

CONFIG = LoadConfig(base_url="http://127.0.0.1:8000", origin="http://127.0.0.1:3000",
                    password="x" * 16, run_id="offline")


def _result() -> RunResult:
    result = RunResult(plateau_duration_s=1200.0)
    for index in range(40000):
        result.plateau.record("search", 200, 20.0 + index % 50, index // 1000)
    for index in range(2000):
        result.plateau.record("profile_update", 200, 300.0, index // 100)
    result.plateau.fail("search", "timeout", 3)
    return result


def test_a_healthy_synthetic_run_renders_a_pass_verdict():
    payload = json.loads(render(CONFIG, _result()))
    assert payload["verdict"] == "PASS"
    assert payload["throughput_rps"] == 35.0
    assert payload["journeys"]["search"]["p99_ms"] <= 70.0
    assert payload["status_breakdown"] == {"200": 42000}
    assert payload["per_minute"] == []


def test_host_metrics_are_published_as_explicit_gaps():
    payload = json.loads(render(CONFIG, _result()))
    gaps = payload["not_measured_by_harness"]
    assert set(gaps) == set(OPERATOR_SUPPLIED)
    assert all(value is None for value in gaps.values())


def test_a_slow_mutation_fails_the_verdict():
    result = _result()
    result.plateau.journeys["profile_update"].latencies_ms = [2000.0] * 2000
    payload = json.loads(render(CONFIG, result))
    assert payload["verdict"] == "FAIL"
    assert any("FAIL p95 profile_update" in line for line in payload["checks"])
