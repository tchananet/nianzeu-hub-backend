"""Proof 9 (command) — `python -m ...cleanup --once` reports instead of crashing."""

import json
from datetime import UTC, datetime, timedelta

import pytest

from app.modules.portfolio import cleanup
from app.modules.portfolio.maintenance import CleanupReport, CleanupService
from app.modules.portfolio.storage import sweepable
from tests.portfolio.fakes import FakeStorage
from tests.portfolio.proofs_wiring import ExecSession, wire
from tests.portfolio.session_double import ScriptedFactory, ScriptedSession, unavailable

KEPT = "quarantine/kept/key"
IDLE: list[ScriptedFactory] = []  # factories handed out by idle_service, in order


def dead_service() -> CleanupService:
    context, _, _ = wire(error=unavailable())
    return CleanupService(context, sweepable(FakeStorage()))


def idle_service() -> CleanupService:
    """Nothing expired and the one stale object is still referenced: a true no-op pass."""
    storage = FakeStorage()
    storage.put("quarantine", KEPT, b"a", modified=datetime.now(UTC) - timedelta(days=2))
    context, _, factory = wire(
        ExecSession([]), ExecSession([]), ScriptedSession([KEPT]), storage=storage
    )
    IDLE.append(factory)
    return CleanupService(context, sweepable(storage))


def test_an_unreachable_database_exits_with_a_readable_status(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(cleanup, "build_service", dead_service)
    with caplog.at_level("ERROR", logger="app.portfolio.cleanup"):
        assert cleanup.main(["--once"]) == 75
    assert json.loads(caplog.messages[-1]) == {"code": "DEPENDENCY_UNAVAILABLE", "deleted": 0}


def test_a_pass_with_nothing_to_do_succeeds_and_can_be_repeated(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    IDLE.clear()
    monkeypatch.setattr(cleanup, "build_service", idle_service)
    with caplog.at_level("INFO", logger="app.portfolio.cleanup"):
        assert cleanup.main(["--once"]) == 0
        assert cleanup.main(["--once"]) == 0
    empty = CleanupReport(0, 0, 0, 0)._asdict()
    assert [json.loads(message) for message in caplog.messages[-2:]] == [empty, empty]
    assert [factory.exhausted() for factory in IDLE] == [True, True]


def test_the_command_refuses_to_run_without_once() -> None:
    with pytest.raises(SystemExit) as raised:
        cleanup.main([])
    assert raised.value.code == 2
