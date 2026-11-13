"""Latency and error accounting. Pure: no I/O, no clock, fully unit-testable."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field

READ_JOURNEYS = frozenset({"search", "public_profile", "public_contacts", "private_read"})
MUTATION_JOURNEYS = frozenset({"profile_update", "portfolio_create"})
EXPECTED = frozenset({200, 201, 204, 304, 404})
"""404 is expected: a visitor may read a profile another virtual user just unpublished."""


def percentile(values: list[float], fraction: float) -> float:
    """Nearest-rank percentile on a copy; 0.0 for an empty sample."""
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(0, min(len(ordered) - 1, math.ceil(fraction * len(ordered)) - 1))
    return ordered[rank]


@dataclass
class JourneyStats:
    name: str
    latencies_ms: list[float] = field(default_factory=list)
    statuses: Counter[int] = field(default_factory=Counter)
    failures: Counter[str] = field(default_factory=Counter)

    @property
    def count(self) -> int:
        return len(self.latencies_ms) + sum(self.failures.values())

    @property
    def unexpected(self) -> int:
        """Timeouts, 5xx and every 429: A01 counts unforeseen 429 as an error."""
        return sum(self.failures.values()) + sum(
            n for status, n in self.statuses.items() if status not in EXPECTED
        )

    @property
    def rate_limited(self) -> int:
        return self.statuses.get(429, 0)

    def summary(self) -> dict[str, float]:
        return {
            "count": float(self.count),
            "p50_ms": round(percentile(self.latencies_ms, 0.50), 1),
            "p95_ms": round(percentile(self.latencies_ms, 0.95), 1),
            "p99_ms": round(percentile(self.latencies_ms, 0.99), 1),
            "unexpected": float(self.unexpected),
            "rate_limited": float(self.rate_limited),
        }


@dataclass
class Recorder:
    """Thread-safe enough for CPython's GIL: every mutation is a single bytecode append."""

    journeys: dict[str, JourneyStats] = field(default_factory=dict)
    buckets: dict[int, Counter[str]] = field(default_factory=dict)

    def _stats(self, name: str) -> JourneyStats:
        return self.journeys.setdefault(name, JourneyStats(name))

    def record(self, name: str, status: int, elapsed_ms: float, minute: int) -> None:
        stats = self._stats(name)
        stats.latencies_ms.append(elapsed_ms)
        stats.statuses[status] += 1
        self.buckets.setdefault(minute, Counter())[f"status_{status}"] += 1

    def fail(self, name: str, reason: str, minute: int) -> None:
        self._stats(name).failures[reason] += 1
        self.buckets.setdefault(minute, Counter())[f"failed_{reason}"] += 1

    @property
    def total(self) -> int:
        return sum(stats.count for stats in self.journeys.values())

    @property
    def unexpected(self) -> int:
        return sum(stats.unexpected for stats in self.journeys.values())

    def error_rate(self) -> float:
        return 0.0 if not self.total else self.unexpected / self.total

    def rate_limited_rate(self) -> float:
        limited = sum(stats.rate_limited for stats in self.journeys.values())
        return 0.0 if not self.total else limited / self.total

    def throughput(self, duration_s: float) -> float:
        return 0.0 if duration_s <= 0 else self.total / duration_s

    def statuses(self) -> Counter[int]:
        merged: Counter[int] = Counter()
        for stats in self.journeys.values():
            merged.update(stats.statuses)
        return merged
