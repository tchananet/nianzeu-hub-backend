import pytest

from app.modules.portfolio import limits, validation_io
from app.modules.portfolio.deadline import Deadline
from app.modules.portfolio.download import sha256_hex
from app.modules.portfolio.errors import Rejected
from app.shared.errors import StorageInvalid
from tests.portfolio import samples
from tests.portfolio.fakes import FakeStorage
from tests.portfolio.leases import QUARANTINE, VALIDATED, context, lease_for


def prepared() -> tuple[FakeStorage, bytes, object]:
    payload = samples.image_bytes("PNG")
    storage = FakeStorage()
    lease = lease_for(payload)
    storage.put(QUARANTINE, lease.quarantine_key, payload, "image/png")
    return storage, payload, lease


def test_fetch_returns_content_and_an_etag_that_is_not_the_sha() -> None:
    storage, payload, lease = prepared()
    content, etag = validation_io.fetch(context(storage), lease, Deadline())
    assert content == payload
    assert etag != sha256_hex(payload) and len(etag) == 32


def test_oversized_object_is_refused_before_reading(monkeypatch: pytest.MonkeyPatch) -> None:
    storage, _, lease = prepared()
    monkeypatch.setitem(limits.MAX_BYTES, "image", 4)
    with pytest.raises(Rejected) as error:
        validation_io.fetch(context(storage), lease, Deadline())
    assert error.value.error.status == 413


def test_real_size_must_equal_the_announced_size() -> None:
    storage, payload, lease = prepared()
    storage.put(QUARANTINE, lease.quarantine_key, payload + b"extra", "image/png")
    with pytest.raises(Rejected) as error:
        validation_io.fetch(context(storage), lease, Deadline())
    assert error.value.rejection_code == "SIZE_MISMATCH"
    assert error.value.error.status == 400


def test_store_recomputes_the_sha_on_the_final_copy() -> None:
    storage, payload, lease = prepared()
    ctx = context(storage)
    _, etag = validation_io.fetch(ctx, lease, Deadline())
    key, digest = validation_io.store(ctx, lease, etag, Deadline())
    assert digest == sha256_hex(payload) and key.startswith("items/")
    assert storage.buckets[VALIDATED][key].data == payload


def test_quarantine_overwrite_cannot_change_the_final_copy() -> None:
    storage, payload, lease = prepared()
    ctx = context(storage)
    _, etag = validation_io.fetch(ctx, lease, Deadline())
    key, digest = validation_io.store(ctx, lease, etag, Deadline())
    storage.put(QUARANTINE, lease.quarantine_key, b"replaced payload", "image/png")
    assert storage.buckets[VALIDATED][key].data == payload
    assert digest == sha256_hex(payload)


def test_copy_requires_the_source_etag_to_still_match() -> None:
    storage, payload, lease = prepared()
    ctx = context(storage)
    _, etag = validation_io.fetch(ctx, lease, Deadline())
    storage.put(QUARANTINE, lease.quarantine_key, payload[::-1], "image/png")
    with pytest.raises(StorageInvalid):
        validation_io.store(ctx, lease, etag, Deadline())


def test_corrupted_final_copy_is_removed_and_never_committed() -> None:
    storage, payload, lease = prepared()

    def tampering(source_bucket, source_key, bucket, key, source_etag):  # noqa: ANN001
        storage.put(bucket, key, payload[:-1], "image/png")

    ctx = context(storage)
    _, etag = validation_io.fetch(ctx, lease, Deadline())
    storage.copy = tampering  # type: ignore[method-assign]
    with pytest.raises(StorageInvalid):
        validation_io.store(ctx, lease, etag, Deadline())
    assert storage.buckets.get(VALIDATED, {}) == {}
