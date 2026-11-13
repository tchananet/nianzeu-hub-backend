"""Render a run into the table docs/qa/load.md expects an operator to paste back.

Latency, errors, throughput and the 429 rate come from the harness. CPU, RAM and
connection counts do not: they are host and PostgreSQL facts the operator records
alongside, and the renderer prints them as explicit gaps rather than zeros.
"""

from __future__ import annotations

import json
from collections import Counter

from tests.load.config import LoadConfig
from tests.load.metrics import Recorder
from tests.load.runner import RunResult
from tests.load.thresholds import Check, all_passed, evaluate

OPERATOR_SUPPLIED = (
    "cpu_mean_percent", "cpu_peak_percent", "ram_peak_percent", "oom_events",
    "api_connections_peak", "db_connections_peak", "commit_sha", "vps_spec",
)


def minute_table(recorder: Recorder) -> list[dict[str, object]]:
    """Per-minute counts, as A01 asks ('relever CPU/RAM chaque minute')."""
    return [
        {"minute": minute, **{key: value for key, value in sorted(counts.items())}}
        for minute, counts in sorted(recorder.buckets.items())
    ]


def status_breakdown(recorder: Recorder) -> dict[str, int]:
    merged: Counter[int] = recorder.statuses()
    return {str(status): count for status, count in sorted(merged.items())}


def payload(config: LoadConfig, result: RunResult, checks: list[Check]) -> dict[str, object]:
    plateau = result.plateau
    return {
        "target_host": config.host,
        "run_id": config.run_id,
        "seed": config.seed,
        "accounts": config.accounts,
        "users": config.users,
        "sources": config.sources,
        "plateau_duration_s": result.plateau_duration_s,
        "login_failures": result.login_failures,
        "journeys": {name: stats.summary() for name, stats in sorted(plateau.journeys.items())},
        "status_breakdown": status_breakdown(plateau),
        "error_rate": round(plateau.error_rate(), 5),
        "rate_limited_rate": round(plateau.rate_limited_rate(), 5),
        "throughput_rps": round(plateau.throughput(result.plateau_duration_s), 2),
        "per_minute": minute_table(result.whole_run),
        "checks": [check.line() for check in checks],
        "verdict": "PASS" if all_passed(checks) else "FAIL",
        "not_measured_by_harness": {key: None for key in OPERATOR_SUPPLIED},
    }


def render(config: LoadConfig, result: RunResult) -> str:
    """JSON, so the operator can attach it verbatim without retyping numbers."""
    checks = evaluate(result.plateau, result.plateau_duration_s)
    return json.dumps(payload(config, result, checks), indent=2, sort_keys=False)
