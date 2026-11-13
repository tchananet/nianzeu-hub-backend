"""Proof 2 — forged MIME, wrong sha, wrong extension, oversize and garbage are refused.

Each refusal must carry the contract code, move the item to rejected and release the
reserved bytes, all through the real `ValidationService` pipeline.
"""

import pytest

from app.modules.portfolio import limits
from app.modules.portfolio.schemas import ValidateRequest
from app.modules.portfolio.validation import ValidationService
from app.shared.errors import AppError
from tests.portfolio import samples
from tests.portfolio.fakes import FakeStorage
from tests.portfolio.items import item
from tests.portfolio.proofs_rows import reservation
from tests.portfolio.proofs_wiring import PROFILE, QUARANTINE, USER, wire
from tests.portfolio.session_double import ScriptedSession

PNG = samples.image_bytes("PNG")


def refused(payload: bytes, **overrides: object) -> tuple[AppError, object, object]:
    row = item(PROFILE, state="pending")
    upload = reservation(row.id, payload, **overrides)
    storage = FakeStorage()
    storage.put(QUARANTINE, upload.quarantine_key, payload, str(upload.media_type))
    # Second session is the rejection write: locked item row, then its reservation.
    context, _, factory = wire(
        ScriptedSession(PROFILE, row, upload),
        ScriptedSession(row, upload),
        storage=storage,
    )
    with pytest.raises(AppError) as raised:
        ValidationService(context).validate(
            USER, row.id, ValidateRequest(upload_id=upload.id)
        )
    assert factory.exhausted(), "The rejection write must happen in its own transaction"
    assert row.state == "rejected" and upload.reservation_active is False
    assert upload.lease_until is None
    return raised.value, row, upload


def test_a_forged_media_type_never_passes_signature_sniffing() -> None:
    # Real PNG bytes announced as JPEG with a matching extension: only the bytes decide.
    error, row, _ = refused(PNG, media_type="image/jpeg", filename="shot.jpg")
    assert (error.code, error.status) == ("UNSUPPORTED_MEDIA_TYPE", 415)
    assert row.rejection_code == "UNSUPPORTED_MEDIA_TYPE"


def test_an_extension_contradicting_the_declared_type_is_unsupported() -> None:
    error, row, _ = refused(PNG, filename="shot.pdf")
    assert (error.code, error.status) == ("UNSUPPORTED_MEDIA_TYPE", 415)
    assert row.rejection_code == "UNSUPPORTED_MEDIA_TYPE"


def test_a_wrong_sha256_is_an_invalid_upload() -> None:
    error, row, _ = refused(PNG, sha256="0" * 64)
    assert (error.code, error.status) == ("INVALID_UPLOAD", 400)
    assert row.rejection_code == "SHA256_MISMATCH"


def test_unparseable_content_behind_a_valid_signature_is_an_invalid_upload() -> None:
    error, row, _ = refused(PNG[:8] + b"\x00" * 64)
    assert (error.code, error.status) == ("INVALID_UPLOAD", 400)
    assert row.rejection_code == "IMAGE_UNREADABLE"


def test_an_object_larger_than_the_type_budget_is_too_large(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(limits.MAX_BYTES, "image", 4)
    error, row, _ = refused(PNG)
    assert (error.code, error.status) == ("FILE_TOO_LARGE", 413)
    assert row.rejection_code == "FILE_TOO_LARGE"


def test_a_size_that_drifted_from_the_reservation_is_an_invalid_upload() -> None:
    error, row, _ = refused(PNG, size_bytes=len(PNG) - 1)
    assert (error.code, error.status) == ("INVALID_UPLOAD", 400)
    assert row.rejection_code == "SIZE_MISMATCH"
