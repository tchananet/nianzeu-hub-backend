"""Proof 5 — storage outage and saturation: 503 with the lease put back, never lost."""

import pytest

from app.modules.portfolio.concurrency import Slots
from app.modules.portfolio.errors import validation_busy
from app.modules.portfolio.schemas import ValidateRequest
from app.modules.portfolio.validation import ValidationService
from app.shared.errors import AppError, StorageUnavailable
from tests.portfolio import samples
from tests.portfolio.fakes import FakeStorage
from tests.portfolio.items import item
from tests.portfolio.proofs_rows import reservation
from tests.portfolio.proofs_wiring import PROFILE, QUARANTINE, USER, wire
from tests.portfolio.session_double import ScriptedSession

PNG = samples.image_bytes("PNG")


def attempt(storage: FakeStorage, slots: Slots | None = None):  # noqa: ANN201
    row = item(PROFILE, state="pending")
    upload = reservation(row.id, PNG)
    context, _, factory = wire(
        ScriptedSession(PROFILE, row, upload),
        ScriptedSession(row, upload),
        storage=storage,
    )
    validation = ValidationService(context, slots=slots)
    with pytest.raises(AppError) as raised:
        validation.validate(USER, row.id, ValidateRequest(upload_id=upload.id))
    return raised.value, row, upload, factory, validation


def test_a_storage_outage_returns_the_item_to_pending_with_its_bytes_reserved() -> None:
    storage = FakeStorage(unavailable=True)
    error, row, upload, factory, validation = attempt(storage)
    assert (error.code, error.status) == ("DEPENDENCY_UNAVAILABLE", 503)
    # The lease is handed back, not consumed: a retry can pick the same reservation up.
    assert row.state == "pending" and row.rejection_code is None
    assert upload.lease_until is None and upload.reservation_active is True
    assert factory.exhausted() and validation.slots.used == 0


def test_an_absent_quarantine_object_returns_the_item_to_pending() -> None:
    # Nothing was ever uploaded against the presigned POST: the client must retry.
    error, row, upload, factory, _ = attempt(FakeStorage())
    assert (error.code, error.status) == ("INVALID_STATE", 409)
    assert row.state == "pending" and upload.reservation_active is True
    assert upload.lease_until is None and factory.exhausted()


def test_an_outage_after_a_successful_read_releases_the_lease_too() -> None:
    # The object was read, the content accepted, and storage died on the final copy.
    row = item(PROFILE, state="pending")
    upload = reservation(row.id, PNG)
    storage = FakeStorage()
    storage.put(QUARANTINE, upload.quarantine_key, PNG, "image/png")

    def outage(*args: object, **kwargs: object) -> None:
        raise StorageUnavailable()

    storage.copy = outage  # type: ignore[method-assign]
    context, _, factory = wire(
        ScriptedSession(PROFILE, row, upload),
        ScriptedSession(row, upload),
        storage=storage,
    )
    with pytest.raises(AppError) as raised:
        ValidationService(context).validate(USER, row.id, ValidateRequest(upload_id=upload.id))
    assert (raised.value.code, raised.value.status) == ("DEPENDENCY_UNAVAILABLE", 503)
    assert row.state == "pending" and row.rejection_code is None
    assert upload.reservation_active is True and factory.exhausted()


def test_saturation_is_refused_before_any_state_change() -> None:
    slots = Slots(1, validation_busy)
    slots.acquire()
    error, row, upload, factory, _ = attempt(FakeStorage(), slots=slots)
    assert (error.code, error.status) == ("VALIDATION_BUSY", 503)
    # No transaction was ever opened, so nothing could have moved.
    assert factory.opened == [] and row.state == "pending"
    assert upload.lease_until is None and slots.used == 1
