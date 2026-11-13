"""The A01 plateau thresholds, quoted from docs/contracts/verification.md.

> Seuils plateau : p95 lectures JSON <=500 ms, p95 mutations <=1000 ms ; erreurs
> inattendues <1% (inclut timeout, 5xx, 429 non prevus) [...] debit realise >=25
> requetes/s, pas de diminution >20% entre premiere et derniere tranche 5 min.
> CPU moyenne <80%, RAM <85%, aucun OOM, connexions API <=20 et total DB <=40.

Nothing here is invented: every number is the architect's, and the resource
limits are evaluated by the operator from host metrics, not by this harness.
"""

from __future__ import annotations

from dataclasses import dataclass

from tests.load.metrics import MUTATION_JOURNEYS, READ_JOURNEYS, Recorder

READ_P95_MS = 500.0
MUTATION_P95_MS = 1000.0
MAX_ERROR_RATE = 0.01
MIN_THROUGHPUT_RPS = 25.0
MAX_THROUGHPUT_DECAY = 0.20
MAX_CPU_PERCENT = 80.0
MAX_RAM_PERCENT = 85.0
MAX_API_CONNECTIONS = 20
MAX_DB_CONNECTIONS = 40


@dataclass(frozen=True)
class Check:
    name: str
    observed: float
    limit: float
    passed: bool

    def line(self) -> str:
        mark = "PASS" if self.passed else "FAIL"
        return f"{mark} {self.name}: {self.observed:g} (limit {self.limit:g})"


def evaluate(plateau: Recorder, duration_s: float) -> list[Check]:
    """Score the latency, error-rate and throughput thresholds the harness can see."""
    checks: list[Check] = []
    for name, stats in sorted(plateau.journeys.items()):
        if name in READ_JOURNEYS:
            limit = READ_P95_MS
        elif name in MUTATION_JOURNEYS:
            limit = MUTATION_P95_MS
        else:
            continue
        observed = stats.summary()["p95_ms"]
        checks.append(Check(f"p95 {name}", observed, limit, observed <= limit))
    rate = plateau.error_rate()
    checks.append(Check("unexpected error rate", rate, MAX_ERROR_RATE, rate < MAX_ERROR_RATE))
    rps = plateau.throughput(duration_s)
    checks.append(Check("throughput rps", rps, MIN_THROUGHPUT_RPS, rps >= MIN_THROUGHPUT_RPS))
    return checks


def decay(first_slice: int, last_slice: int) -> Check:
    """Throughput must not fall by more than 20% between the first and last 5 min."""
    observed = 0.0 if not first_slice else 1 - last_slice / first_slice
    return Check("throughput decay", observed, MAX_THROUGHPUT_DECAY,
                 observed <= MAX_THROUGHPUT_DECAY)


def all_passed(checks: list[Check]) -> bool:
    return all(check.passed for check in checks)
