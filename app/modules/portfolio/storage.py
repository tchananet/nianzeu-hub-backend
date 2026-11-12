from collections.abc import Iterator
from datetime import datetime
from typing import Protocol

from app.shared.ports import StoragePort


class SweepPort(Protocol):
    """Listing capability needed by cleanup only; StoragePort stays untouched (F01 owns it)."""

    def list_keys(self, bucket: str, prefix: str) -> Iterator[tuple[str, datetime]]: ...


class PortfolioStorage(StoragePort, SweepPort, Protocol):
    pass


def sweepable(storage: StoragePort) -> SweepPort | None:
    """Adapters without listing (such as DisabledStorage) simply skip the object sweep."""
    candidate = getattr(storage, "list_keys", None)
    return storage if callable(candidate) else None  # type: ignore[return-value]
