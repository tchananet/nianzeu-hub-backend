from collections.abc import Callable
from time import monotonic

from app.modules.portfolio.errors import rejected_limit
from app.modules.portfolio.limits import VALIDATION_TIMEOUT_SECONDS


class Deadline:
    """Wall-clock budget checked between phases and between stream chunks."""

    def __init__(
        self,
        seconds: int = VALIDATION_TIMEOUT_SECONDS,
        ticker: Callable[[], float] = monotonic,
    ) -> None:
        self.ticker = ticker
        self.expires_at = ticker() + seconds

    def check(self) -> None:
        if self.ticker() > self.expires_at:
            raise rejected_limit()
