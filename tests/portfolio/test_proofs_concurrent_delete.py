"""Proof 6 — a concurrent delete wins; finalisation never resurrects anything."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.portfolio import lease_writes
from app.modules.portfolio.schemas import ValidateRequest
from app.modules.portfolio.service import PortfolioService
from app.modules.portfolio.validation import ValidationService
from app.shared.errors import AppError
from tests.portfolio import samples
from tests.portfolio.fakes import FakeStorage
from tests.portfolio.items import item, published
from tests.portfolio.leases import lease_for
from tests.portfolio.proofs_rows import reservation
from tests.portfolio.proofs_wiring import PROFILE, QUARANTINE, USER, VALIDATED, wire
from tests.portfolio.session_double import ScriptedSession

PNG = samples.image_bytes("PNG")


def test_a_delete_during_validation_wins_and_nothing_is_recreated() -> None:
    row = item(PROFILE, state="pending")
    upload = reservation(row.id, PNG)
    storage = FakeStorage()
    storage.put(QUARANTINE, upload.quarantine_key, PNG, "image/png")
    # The owner deleted the item while the bytes were being copied: `db.get` finds nothing.
    gone = ScriptedSession(None)
    context, _, factory = wire(ScriptedSession(PROFILE, row, upload), gone, storage=storage)
    with pytest.raises(AppError) as raised:
        ValidationService(context).validate(USER, row.id, ValidateRequest(upload_id=upload.id))
    assert (raised.value.code, raised.value.status) == ("NOT_FOUND", 404)
    assert gone.added == [] and gone.deleted == [] and gone.flushes == 0
    # The copy is an orphan the cleanup sweep removes; it is never committed anywhere.
    assert len(storage.buckets[VALIDATED]) == 1 and factory.exhausted()


def test_finalisation_refuses_an_item_whose_lease_was_taken_over() -> None:
    row = item(PROFILE, state="validating")
    upload = reservation(row.id, PNG, lease_until=datetime.now(UTC))
    lease = lease_for(PNG)
    session = ScriptedSession(row, upload)
    context, _, _ = wire(session)
    with pytest.raises(AppError) as raised:
        lease_writes.finalize(context, lease, "items/other/key", lease.sha256)
    assert (raised.value.code, raised.value.status) == ("INVALID_STATE", 409)
    assert row.state == "validating" and session.added == [] and session.flushes == 0


@pytest.mark.parametrize("write", [lease_writes.release, lease_writes.reject])
def test_releasing_or_rejecting_a_deleted_item_is_a_silent_no_op(write) -> None:  # noqa: ANN001
    session = ScriptedSession(None)
    context, _, factory = wire(session)
    lease = lease_for(PNG)
    if write is lease_writes.reject:
        write(context, lease, "SHA256_MISMATCH")
    else:
        write(context, lease)
    assert session.added == [] and session.deleted == [] and session.flushes == 0
    assert factory.exhausted()


def test_deleting_an_item_drops_its_row_and_both_objects() -> None:
    row = published(PROFILE)
    upload = reservation(row.id, PNG)
    storage = FakeStorage()
    storage.put(QUARANTINE, upload.quarantine_key, PNG, "image/png")
    storage.put(VALIDATED, str(row.object_key), PNG, "image/png")
    session = ScriptedSession(PROFILE, row, upload)
    context, _, factory = wire(session, storage=storage)
    PortfolioService(context).delete(USER, row.id)
    assert session.deleted == [row] and session.added == []
    assert storage.buckets[QUARANTINE] == {} and storage.buckets[VALIDATED] == {}
    assert factory.exhausted()


def test_deleting_an_absent_or_third_party_item_is_not_found() -> None:
    context, store, _ = wire(ScriptedSession(PROFILE, None))
    with pytest.raises(AppError) as raised:
        PortfolioService(context).delete(USER, uuid4())
    assert (raised.value.code, raised.value.status) == ("NOT_FOUND", 404)
    assert store.buckets == {}
