"""Proof 4 — once validation committed, overwriting the quarantine changes nothing.

The whole `ValidationService` pipeline runs here, so the final key, the recomputed
digest and the committed row all come from production code, not from a fixture.
"""

from app.modules.portfolio.download import sha256_hex
from app.modules.portfolio.schemas import UploadRequest, ValidateRequest
from app.modules.portfolio.uploads import UploadService
from app.modules.portfolio.validation import ValidationService
from tests.portfolio import samples
from tests.portfolio.fakes import FakeStorage
from tests.portfolio.items import item
from tests.portfolio.proofs_rows import ActiveUser, reservation
from tests.portfolio.proofs_wiring import PROFILE, QUARANTINE, USER, VALIDATED, wire
from tests.portfolio.session_double import ScriptedSession

PNG = samples.image_bytes("PNG")
FORGED = samples.image_bytes("PNG", width=32, height=32)


def validated_once():  # noqa: ANN201
    row = item(PROFILE, state="pending")
    upload = reservation(row.id, PNG)
    storage = FakeStorage()
    storage.put(QUARANTINE, upload.quarantine_key, PNG, "image/png")
    context, _, factory = wire(
        ScriptedSession(PROFILE, row, upload),
        ScriptedSession(row, upload),
        storage=storage,
    )
    result = ValidationService(context).validate(
        USER, row.id, ValidateRequest(upload_id=upload.id)
    )
    assert factory.exhausted()
    return result, row, upload, storage


def test_validation_commits_a_fresh_final_key_and_a_recomputed_digest() -> None:
    result, row, upload, storage = validated_once()
    assert result.state == "validated" and result.file is not None
    assert result.file.sha256 == sha256_hex(PNG)
    assert row.object_key is not None and row.object_key.startswith("items/")
    assert row.object_key != upload.quarantine_key
    # The reservation is consumed: its bytes stop counting against the owner quota.
    assert upload.reservation_active is False and upload.lease_until is None
    assert storage.buckets[VALIDATED][row.object_key].data == PNG


def test_overwriting_the_quarantine_afterwards_cannot_touch_the_final_copy() -> None:
    _, row, upload, storage = validated_once()
    key = str(row.object_key)
    storage.put(QUARANTINE, upload.quarantine_key, FORGED, "image/png")
    assert storage.buckets[QUARANTINE][upload.quarantine_key].data == FORGED
    # Different bucket, unguessable fresh key, already-copied bytes: nothing moves.
    assert storage.buckets[VALIDATED][key].data == PNG
    assert row.sha256 == sha256_hex(PNG) and row.size_bytes == len(PNG)


def test_the_ticket_only_ever_authorises_a_quarantine_key() -> None:
    _, row, upload, storage = validated_once()
    request = UploadRequest(
        item_id=row.id,  # type: ignore[arg-type]
        filename="shot.png",
        media_type="image/png",
        size_bytes=len(PNG),
        sha256=sha256_hex(PNG),
    )
    context, _, _ = wire(
        ScriptedSession(ActiveUser(), PROFILE, item(PROFILE), None, 0, 0), storage=storage
    )
    UploadService(context).issue(USER, request)
    bucket, key, media_type, size = storage.signed[-1]
    # The client never names a key, and the signature is confined to the quarantine.
    assert bucket == QUARANTINE and key.startswith("quarantine/")
    assert (media_type, size) == ("image/png", len(PNG))
    assert key not in (upload.quarantine_key, row.object_key)
