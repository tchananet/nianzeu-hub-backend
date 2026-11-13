"""Proof 1 — `validate` is accepted from pending only, plus the recoverable expired lease."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.modules.portfolio import lease_acquire
from app.modules.portfolio.lease import Lease
from app.modules.portfolio.schemas import ValidateRequest
from app.modules.portfolio.validation import ValidationService
from app.shared.errors import AppError
from tests.portfolio.items import item, published, validated
from tests.portfolio.proofs_rows import reservation
from tests.portfolio.proofs_wiring import PROFILE, USER, wire
from tests.portfolio.session_double import ScriptedSession


def service(*results: object) -> tuple[ValidationService, ScriptedSession]:
    session = ScriptedSession(*results)
    context, _, _ = wire(session)
    return ValidationService(context), session


def refused(*results: object, upload_id: object = None) -> AppError:
    validation, session = service(*results)
    data = ValidateRequest(upload_id=upload_id or uuid4())  # type: ignore[arg-type]
    with pytest.raises(AppError) as raised:
        validation.validate(USER, uuid4(), data)
    # A refusal must never strand the concurrency slot it took on entry.
    assert validation.slots.used == 0 and session.added == []
    return raised.value


@pytest.mark.parametrize("state", ["draft", "rejected"])
def test_validating_an_item_with_no_live_reservation_is_refused(state: str) -> None:
    row = item(PROFILE, state=state)
    error = refused(PROFILE, row, reservation(row.id))
    assert (error.code, error.status) == ("INVALID_STATE", 409)


def test_a_concurrent_validation_holding_a_live_lease_is_refused() -> None:
    row = item(PROFILE, state="validating")
    live = reservation(row.id, lease_until=datetime.now(UTC) + timedelta(seconds=30))
    error = refused(PROFILE, row, live, upload_id=live.id)
    assert (error.code, error.status) == ("INVALID_STATE", 409)
    assert row.state == "validating" and live.lease_until is not None


def test_a_pending_item_whose_upload_id_does_not_match_is_refused() -> None:
    row = item(PROFILE, state="pending")
    error = refused(PROFILE, row, reservation(row.id))
    assert (error.code, error.status) == ("INVALID_STATE", 409)


def test_a_pending_item_without_any_reservation_row_is_refused() -> None:
    error = refused(PROFILE, item(PROFILE, state="pending"), None)
    assert (error.code, error.status) == ("INVALID_STATE", 409)


@pytest.mark.parametrize("builder", [validated, published])
def test_replaying_validate_on_a_finished_item_returns_it_unchanged(builder) -> None:  # noqa: ANN001
    row = builder(PROFILE)
    done = reservation(row.id)
    validation, session = service(PROFILE, row, done)
    result = validation.validate(USER, row.id, ValidateRequest(upload_id=done.id))
    assert result.state == row.state and session.flushes == 0
    assert validation.slots.used == 0


def test_a_finished_item_with_a_foreign_upload_id_is_refused() -> None:
    row = validated(PROFILE)
    error = refused(PROFILE, row, reservation(row.id))
    assert (error.code, error.status) == ("INVALID_STATE", 409)


def test_an_expired_lease_is_recoverable_by_a_new_validation() -> None:
    now = datetime.now(UTC)
    row = item(PROFILE, state="validating")
    stale = reservation(row.id, lease_until=now - timedelta(seconds=1))
    context, _, factory = wire(ScriptedSession(PROFILE, row, stale))
    outcome = lease_acquire.acquire(context, USER, row.id, stale.id, now)
    assert isinstance(outcome, Lease) and outcome.upload_id == stale.id
    # The stale lease was replaced by a fresh one; the item stays in validating.
    assert stale.lease_until == now + timedelta(seconds=60)
    assert row.state == "validating" and factory.exhausted()
