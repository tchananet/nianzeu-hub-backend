"""Proof 9 — `cleanup --once` is idempotent and deletes nothing without a database."""

from datetime import UTC, datetime, timedelta

import pytest

from app.modules.portfolio.maintenance import ORPHAN_AGE_HOURS, CleanupReport, CleanupService
from app.modules.portfolio.storage import sweepable
from app.shared.errors import DependencyUnavailable
from tests.portfolio.fakes import FakeStorage
from tests.portfolio.items import item, validated
from tests.portfolio.proofs_rows import reservation
from tests.portfolio.proofs_wiring import PROFILE, QUARANTINE, VALIDATED, ExecSession, wire
from tests.portfolio.session_double import ScriptedSession, unavailable

NOW = datetime.now(UTC)
OLD = NOW - timedelta(hours=ORPHAN_AGE_HOURS + 1)


def filled() -> tuple[FakeStorage, str, str]:
    """One stale orphan and one stale but still referenced object per bucket."""
    storage, live = FakeStorage(), validated(PROFILE)
    storage.put(QUARANTINE, "quarantine/live/key", b"a", modified=OLD)
    storage.put(QUARANTINE, "quarantine/orphan/key", b"b", modified=OLD)
    storage.put(QUARANTINE, "quarantine/fresh/key", b"c", modified=NOW)
    storage.put(VALIDATED, str(live.object_key), b"d", modified=OLD)
    storage.put(VALIDATED, "items/orphan/key", b"e", modified=OLD)
    return storage, "quarantine/live/key", str(live.object_key)


def pair(state: str, **overrides: object):  # noqa: ANN201
    row = item(PROFILE, state=state)
    return row, reservation(row.id, **overrides)


def test_a_first_pass_rejects_stale_rows_and_drops_only_unreferenced_objects() -> None:
    storage, live_quarantine, live_final = filled()
    stale, lease = pair("pending"), pair("validating", lease_until=OLD)
    context, _, factory = wire(
        ExecSession([stale]),
        ExecSession([lease]),
        ScriptedSession([live_quarantine]),
        ScriptedSession([live_final]),
        storage=storage,
    )
    report = CleanupService(context, sweepable(storage)).run_once()
    assert report == CleanupReport(1, 1, 1, 1) and factory.exhausted()
    assert sorted(storage.buckets[QUARANTINE]) == ["quarantine/fresh/key", live_quarantine]
    assert sorted(storage.buckets[VALIDATED]) == [live_final]
    # Rejected rows no longer match either expiry predicate, which is what makes a
    # second pass a no-op rather than a repeat of the same work.
    for row, upload in (stale, lease):
        assert row.state == "rejected" and upload.reservation_active is False
        assert upload.lease_until is None


def test_a_second_pass_over_the_same_state_changes_nothing() -> None:
    storage, live_quarantine, live_final = filled()
    del storage.buckets[QUARANTINE]["quarantine/orphan/key"]
    del storage.buckets[VALIDATED]["items/orphan/key"]
    context, _, factory = wire(
        ExecSession([]),
        ExecSession([]),
        ScriptedSession([live_quarantine]),
        ScriptedSession([live_final]),
        storage=storage,
    )
    before = {bucket: dict(keys) for bucket, keys in storage.buckets.items()}
    assert CleanupService(context, sweepable(storage)).run_once() == CleanupReport(0, 0, 0, 0)
    assert storage.buckets == before and factory.exhausted()


def test_an_unreachable_database_deletes_nothing_at_all() -> None:
    storage, _, _ = filled()
    before = {bucket: dict(keys) for bucket, keys in storage.buckets.items()}
    context, _, _ = wire(storage=storage, error=unavailable())
    with pytest.raises(DependencyUnavailable):
        CleanupService(context, sweepable(storage)).run_once()
    assert storage.buckets == before


def test_an_adapter_without_listing_skips_the_object_sweep() -> None:
    context, _, factory = wire(ExecSession([]), ExecSession([]))
    report = CleanupService(context, sweeper=None).run_once()
    assert report == CleanupReport(0, 0, 0, 0) and factory.exhausted()
