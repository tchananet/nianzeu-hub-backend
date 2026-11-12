import pytest

from app.modules.portfolio.deadline import Deadline
from app.modules.portfolio.download import hash_stream, read_bounded, sha256_hex
from app.modules.portfolio.errors import Rejected


def clock(values: list[float]):
    return lambda: values.pop(0) if len(values) > 1 else values[0]


def test_read_bounded_refuses_more_bytes_than_announced() -> None:
    with pytest.raises(Rejected) as error:
        read_bounded(iter([b"a" * 10, b"b" * 10]), Deadline(), 15)
    assert error.value.rejection_code == "VALIDATION_LIMIT"
    assert error.value.error.code == "INVALID_UPLOAD"


def test_read_bounded_returns_exact_payload() -> None:
    assert read_bounded(iter([b"ab", b"cd"]), Deadline(), 4) == b"abcd"


def test_hash_stream_matches_buffered_digest_without_retaining_bytes() -> None:
    payload = b"portfolio" * 100
    digest, total = hash_stream(iter([payload[:100], payload[100:]]), Deadline(), len(payload))
    assert (digest, total) == (sha256_hex(payload), len(payload))


def test_expired_deadline_stops_the_stream() -> None:
    deadline = Deadline(seconds=30, ticker=clock([0.0, 100.0]))
    with pytest.raises(Rejected) as error:
        read_bounded(iter([b"a", b"b"]), deadline, 10)
    assert error.value.rejection_code == "VALIDATION_LIMIT"
