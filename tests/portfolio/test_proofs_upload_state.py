"""Proof 1/2 — the reservation gate: only draft/rejected, and declarations are screened.

`upload-url` is the entry transition of the machine: publish/unpublish are proven in
test_publish_state.py and test_unpublish_state.py, this file covers what they do not.
"""

from uuid import uuid4

import pytest

from app.modules.portfolio.limits import MIB
from app.modules.portfolio.schemas import UploadRequest
from app.modules.portfolio.uploads import UploadService
from app.shared.errors import AppError
from tests.portfolio.items import item
from tests.portfolio.proofs_rows import ActiveUser
from tests.portfolio.proofs_wiring import PROFILE, USER, wire
from tests.portfolio.session_double import ScriptedSession

DIGEST = "a" * 64


def request(**overrides: object) -> UploadRequest:
    fields: dict[str, object] = {
        "item_id": uuid4(),
        "filename": "shot.png",
        "media_type": "image/png",
        "size_bytes": 1024,
        "sha256": DIGEST,
    }
    return UploadRequest(**(fields | overrides))  # type: ignore[arg-type]


def service(*results: object) -> tuple[UploadService, ScriptedSession]:
    session = ScriptedSession(*results)
    context, _, _ = wire(session)
    return UploadService(context), session


def refused(*results: object, **overrides: object) -> AppError:
    uploads, session = service(*results)
    with pytest.raises(AppError) as raised:
        uploads.issue(USER, request(**overrides))
    # Nothing was reserved and no state moved: the guard fired before any write.
    assert session.added == [] and session.flushes == 0
    return raised.value


@pytest.mark.parametrize("state", ["pending", "validating", "validated", "published"])
def test_reserving_an_upload_outside_draft_or_rejected_is_refused(state: str) -> None:
    error = refused(ActiveUser(), PROFILE, item(PROFILE, state=state))
    assert (error.code, error.status) == ("INVALID_STATE", 409)


@pytest.mark.parametrize("state", ["draft", "rejected"])
def test_the_two_uploadable_states_pass_the_state_guard(state: str) -> None:
    # Reaching the quota lookups proves the state guard let this transition through.
    uploads, session = service(ActiveUser(), PROFILE, item(PROFILE, state=state), None, 0, 0)
    ticket = uploads.issue(USER, request())
    assert ticket.method == "POST" and session.added != []


def test_an_owner_without_a_profile_cannot_reserve_anything() -> None:
    error = refused(ActiveUser(), None)
    assert (error.code, error.status) == ("PROFILE_REQUIRED", 409)


def test_a_disabled_or_absent_owner_is_rejected_before_the_profile_lookup() -> None:
    error = refused(None)
    assert (error.code, error.status) == ("AUTH_REQUIRED", 401)


@pytest.mark.parametrize(
    ("media_type", "filename"),
    [
        ("application/pdf", "shot.pdf"),  # forged type for an image item
        ("image/png", "shot.jpg"),  # extension that contradicts the declared type
        ("image/gif", "shot.gif"),  # type outside the contract table
    ],
)
def test_a_declaration_that_does_not_match_the_item_type_is_unsupported(
    media_type: str, filename: str
) -> None:
    error = refused(
        ActiveUser(), PROFILE, item(PROFILE), media_type=media_type, filename=filename
    )
    assert (error.code, error.status) == ("UNSUPPORTED_MEDIA_TYPE", 415)


def test_a_declared_size_above_the_type_budget_is_refused_before_signing() -> None:
    error = refused(ActiveUser(), PROFILE, item(PROFILE), size_bytes=10 * MIB + 1)
    assert (error.code, error.status) == ("FILE_TOO_LARGE", 413)
