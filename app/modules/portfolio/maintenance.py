from dataclasses import dataclass
from datetime import timedelta
from typing import NamedTuple

from app.modules.portfolio import expiry, sweep
from app.modules.portfolio.context import PortfolioContext
from app.modules.portfolio.storage import SweepPort

ORPHAN_AGE_HOURS = 24


class CleanupReport(NamedTuple):
    expired_uploads: int
    expired_leases: int
    quarantine_removed: int
    final_removed: int


@dataclass(frozen=True)
class CleanupService:
    """Idempotent maintenance: nothing is deleted when the database is unreachable."""

    context: PortfolioContext
    sweeper: SweepPort | None = None

    def run_once(self) -> CleanupReport:
        now = self.context.clock()
        cutoff = now - timedelta(hours=ORPHAN_AGE_HOURS)
        return CleanupReport(
            expired_uploads=expiry.expire_reservations(self.context, now),
            expired_leases=expiry.expire_leases(self.context, now),
            quarantine_removed=sweep.sweep_quarantine(self.context, self.sweeper, cutoff),
            final_removed=sweep.sweep_final(self.context, self.sweeper, cutoff),
        )
