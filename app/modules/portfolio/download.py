import hashlib
from collections.abc import Iterator

from app.modules.portfolio.deadline import Deadline
from app.modules.portfolio.errors import rejected_limit
from app.modules.portfolio.limits import VALIDATION_MEMORY_BYTES


def read_bounded(chunks: Iterator[bytes], deadline: Deadline, limit: int) -> bytes:
    """Memory-bounded read; nothing is ever written to the container filesystem."""
    capped = min(limit, VALIDATION_MEMORY_BYTES)
    buffer = bytearray()
    for chunk in chunks:
        deadline.check()
        if len(buffer) + len(chunk) > capped:
            raise rejected_limit()
        buffer.extend(chunk)
    return bytes(buffer)


def hash_stream(chunks: Iterator[bytes], deadline: Deadline, limit: int) -> tuple[str, int]:
    """Streaming digest for the final copy: no buffer is retained."""
    capped = min(limit, VALIDATION_MEMORY_BYTES)
    digest, total = hashlib.sha256(), 0
    for chunk in chunks:
        deadline.check()
        total += len(chunk)
        if total > capped:
            raise rejected_limit()
        digest.update(chunk)
    return digest.hexdigest(), total


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
