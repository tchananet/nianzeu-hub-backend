"""Publishing service wired to scripted sessions and in-memory buckets."""

from uuid import uuid4

from app.modules.portfolio.context import PortfolioContext
from app.modules.portfolio.publishing import PublishingService
from tests.portfolio.fakes import FakeStorage
from tests.portfolio.session_double import ScriptedFactory, ScriptedSession

QUARANTINE, VALIDATED = "quarantine", "validated"
USER = uuid4()
PROFILE = uuid4()


def build(*sessions: ScriptedSession, storage: FakeStorage | None = None,
          error: Exception | None = None):
    store = storage if storage is not None else FakeStorage()
    factory = ScriptedFactory(*sessions, error=error)
    context = PortfolioContext(
        factory=factory,  # type: ignore[arg-type]
        storage=store,
        quarantine_bucket=QUARANTINE,
        validated_bucket=VALIDATED,
    )
    return PublishingService(context), store, factory


def stored(store: FakeStorage, key: str, size: int) -> None:
    store.put(VALIDATED, key, b"x" * size, "image/png")
