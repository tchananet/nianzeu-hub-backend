"""Proof 3 — the 20-item and 200 MiB owner limits, and the stale upload.

Both quotas are recomputed from rows under the owner-wide lock, so the proof drives the
real services and only feeds them the row counts a locked transaction would have read.
"""

from uuid import uuid4

import pytest

from app.modules.portfolio import states
from app.modules.portfolio.schemas import ItemCreate, UploadRequest, ValidateRequest
from app.modules.portfolio.service import PortfolioService
from app.modules.portfolio.uploads import UploadService
from app.modules.portfolio.validation import ValidationService
from app.shared.errors import AppError
from tests.portfolio.items import item
from tests.portfolio.proofs_rows import ActiveUser, reservation
from tests.portfolio.proofs_wiring import PROFILE, USER, wire
from tests.portfolio.session_double import ScriptedSession

CREATE = ItemCreate(title="Case study", description="Details", type="image")


def ticket_for(size: int) -> UploadRequest:
    return UploadRequest(
        item_id=uuid4(),  # type: ignore[arg-type]
        filename="shot.png",
        media_type="image/png",
        size_bytes=size,
        sha256="a" * 64,
    )


def issue(stored: int, reserved: int, size: int) -> tuple[UploadService, ScriptedSession]:
    session = ScriptedSession(ActiveUser(), PROFILE, item(PROFILE), None, stored, reserved)
    context, _, _ = wire(session)
    return UploadService(context), session


def test_a_twenty_first_item_is_refused() -> None:
    session = ScriptedSession(ActiveUser(), PROFILE, states.ITEM_QUOTA)
    context, _, _ = wire(session)
    with pytest.raises(AppError) as raised:
        PortfolioService(context).create(USER, CREATE)
    assert (raised.value.code, raised.value.status) == ("QUOTA_EXCEEDED", 409)
    assert session.added == [] and session.flushes == 0


def test_the_twentieth_item_still_fits() -> None:
    session = ScriptedSession(ActiveUser(), PROFILE, states.ITEM_QUOTA - 1)
    context, _, _ = wire(session)
    created = PortfolioService(context).create(USER, CREATE)
    assert created.state == "draft" and len(session.added) == 1


@pytest.mark.parametrize(
    ("stored", "reserved", "size"),
    [
        (states.BYTE_QUOTA - 1024, 0, 1025),  # stored bytes alone overflow
        (0, states.BYTE_QUOTA, 1),  # an active reservation counts like stored bytes
        (states.BYTE_QUOTA // 2, states.BYTE_QUOTA // 2, 1),  # both sources are summed
    ],
)
def test_crossing_two_hundred_mebibytes_is_refused(stored: int, reserved: int, size: int) -> None:
    uploads, session = issue(stored, reserved, size)
    with pytest.raises(AppError) as raised:
        uploads.issue(USER, ticket_for(size))
    assert (raised.value.code, raised.value.status) == ("QUOTA_EXCEEDED", 409)
    assert session.added == [] and session.flushes == 0


def test_a_reservation_landing_exactly_on_the_byte_quota_is_accepted() -> None:
    uploads, session = issue(states.BYTE_QUOTA - 1024, 0, 1024)
    ticket = uploads.issue(USER, ticket_for(1024))
    assert ticket.method == "POST" and len(session.added) == 1


def test_validating_a_stale_upload_is_refused_and_frees_its_bytes() -> None:
    row = item(PROFILE, state="pending")
    stale = reservation(row.id)
    stale.expires_at = row.created_at  # already past when the lease is attempted
    session = ScriptedSession(PROFILE, row, stale)
    context, _, factory = wire(session)
    with pytest.raises(AppError) as raised:
        ValidationService(context).validate(USER, row.id, ValidateRequest(upload_id=stale.id))
    assert (raised.value.code, raised.value.status) == ("UPLOAD_EXPIRED", 409)
    assert row.state == "rejected" and row.rejection_code == "UPLOAD_EXPIRED"
    assert stale.reservation_active is False and session.flushes == 1
    assert factory.exhausted(), "No storage I/O and no second transaction"
