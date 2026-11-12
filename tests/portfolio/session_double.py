"""Session doubles for logic that must be proven without PostgreSQL.

They replay queued lookup results in call order, so the production code path, its guard
order and its row mutations are all real; only SQL execution and locking are simulated.
SQL semantics (FOR UPDATE, constraints, isolation) stay covered by the database tests.
"""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.exc import OperationalError


def unavailable() -> OperationalError:
    return OperationalError("SELECT 1", {}, Exception("connection refused"))


class ScriptedSession:
    """Each scalar()/get() call pops the next queued row; mutations are recorded."""

    __test__ = False

    def __init__(self, *results: object) -> None:
        self.results = list(results)
        self.statements: list[object] = []
        self.added: list[object] = []
        self.deleted: list[object] = []
        self.flushes = 0

    def pop(self, statement: object) -> object:
        self.statements.append(statement)
        if not self.results:
            raise AssertionError("Unexpected extra query; the double ran out of rows")
        return self.results.pop(0)

    def scalar(self, statement: object) -> object:
        return self.pop(statement)

    def scalars(self, statement: object) -> object:
        return self.pop(statement)

    def get(self, entity: object, ident: object, with_for_update: bool = False) -> object:
        assert with_for_update, "Lease rows must always be locked for update"
        return self.pop((entity, ident))

    def add(self, row: object) -> None:
        self.added.append(row)

    def delete(self, row: object) -> None:
        self.deleted.append(row)

    def flush(self) -> None:
        self.flushes += 1


class ScriptedFactory:
    """Hands out one scripted session per transaction; `error` simulates a dead database."""

    __test__ = False

    def __init__(self, *sessions: ScriptedSession, error: Exception | None = None) -> None:
        self.sessions = list(sessions)
        self.error = error
        self.opened: list[ScriptedSession] = []

    @contextmanager
    def begin(self) -> Iterator[ScriptedSession]:
        if self.error is not None:
            raise self.error
        if not self.sessions:
            raise AssertionError("Unexpected extra transaction opened")
        session = self.sessions.pop(0)
        self.opened.append(session)
        yield session

    def exhausted(self) -> bool:
        return not self.sessions
