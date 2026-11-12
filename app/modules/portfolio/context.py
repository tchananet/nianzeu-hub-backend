from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.primitives import Clock, utc_now
from app.shared.ports import StoragePort


@dataclass(frozen=True)
class PortfolioContext:
    """Injected collaborators; buckets come from validated Settings, never from clients."""

    factory: sessionmaker[Session]
    storage: StoragePort
    quarantine_bucket: str
    validated_bucket: str
    clock: Clock = utc_now


def build_context(
    factory: sessionmaker[Session],
    storage: StoragePort,
    settings: Settings,
    clock: Clock = utc_now,
) -> PortfolioContext:
    return PortfolioContext(
        factory=factory,
        storage=storage,
        quarantine_bucket=settings.quarantine_bucket,
        validated_bucket=settings.validated_bucket,
        clock=clock,
    )
