"""The A01 load schedule, pure and unit-testable.

docs/contracts/verification.md, Q02: 5 min warm-up, 5 min linear ramp 0->100
users, 20 min plateau at 100, 2 min ramp-down. Only plateau samples are scored,
so warm-up and ramp cannot flatter p95.
"""

from __future__ import annotations

from dataclasses import dataclass

from tests.load.config import LoadConfig


@dataclass(frozen=True)
class Phases:
    warmup_s: int
    ramp_s: int
    plateau_s: int
    rampdown_s: int

    @property
    def plateau_start_s(self) -> int:
        return self.warmup_s + self.ramp_s

    @property
    def plateau_end_s(self) -> int:
        return self.plateau_start_s + self.plateau_s

    @property
    def total_s(self) -> int:
        return self.plateau_end_s + self.rampdown_s

    def active_users(self, elapsed_s: float, users: int) -> int:
        """Users running at ``elapsed_s``; warm-up holds 10% of the target."""
        if elapsed_s < self.warmup_s:
            return max(1, users // 10)
        if elapsed_s < self.plateau_start_s:
            progress = (elapsed_s - self.warmup_s) / max(1, self.ramp_s)
            return max(1, int(users * progress))
        if elapsed_s < self.plateau_end_s:
            return users
        remaining = 1 - (elapsed_s - self.plateau_end_s) / max(1, self.rampdown_s)
        return max(0, int(users * remaining))

    def in_plateau(self, elapsed_s: float) -> bool:
        return self.plateau_start_s <= elapsed_s < self.plateau_end_s


def phases_of(config: LoadConfig) -> Phases:
    return Phases(config.warmup_s, config.ramp_s, config.plateau_s, config.rampdown_s)
