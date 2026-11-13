"""Wiring shared by the O01 proof files: scripted sessions plus in-memory buckets."""

from typing import Any
from uuid import uuid4

from app.modules.portfolio import states
from app.modules.portfolio.context import PortfolioContext
from app.modules.portfolio.models import PortfolioItem
from tests.portfolio.fakes import FakeStorage
from tests.portfolio.session_double import ScriptedFactory, ScriptedSession

QUARANTINE, VALIDATED = "quarantine", "validated"
USER, PROFILE = uuid4(), uuid4()


class Rows:
    """Minimal `Result` shape: the expiry sweeps only ever call `.all()`."""

    def __init__(self, value: list[Any]) -> None:
        self.value = value

    def all(self) -> list[Any]:
        return self.value


class ExecSession(ScriptedSession):
    """Adds the `execute(...).all()` call shape used by `expiry.mark`."""

    def execute(self, statement: object) -> Rows:
        popped = self.pop(statement)
        assert isinstance(popped, list)
        return Rows(popped)


class Mirror:
    """Public content lookup answered from the live row, honouring the state predicate.

    Unlike a scripted queue this re-reads the row on every call and applies the very
    filter the production query carries, so publishing changes really drive the answer.
    """

    __test__ = False

    def __init__(self, row: PortfolioItem | None = None) -> None:
        self.row = row
        self.reads = 0

    def scalar(self, statement: Any) -> PortfolioItem | None:
        compiled = statement.compile()
        assert "portfolio_items.state =" in str(compiled), "Lookup must filter on state"
        assert states.PUBLISHED in compiled.params.values(), "Filter must be 'published'"
        self.reads += 1
        if self.row is None or self.row.state != states.PUBLISHED:
            return None
        return self.row


def wire(
    *sessions: Any, storage: FakeStorage | None = None, error: Exception | None = None
) -> tuple[PortfolioContext, FakeStorage, ScriptedFactory]:
    store = storage if storage is not None else FakeStorage()
    factory = ScriptedFactory(*sessions, error=error)
    context = PortfolioContext(
        factory=factory,  # type: ignore[arg-type]
        storage=store,
        quarantine_bucket=QUARANTINE,
        validated_bucket=VALIDATED,
    )
    return context, store, factory
