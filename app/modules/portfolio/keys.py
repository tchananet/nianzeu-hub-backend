from uuid import UUID, uuid4

QUARANTINE_PREFIX = "quarantine/"
FINAL_PREFIX = "items/"


def quarantine_key() -> str:
    """Opaque random key; never derived from client input and never reused."""
    return f"{QUARANTINE_PREFIX}{uuid4().hex}/{uuid4().hex}"


def final_key(item_id: UUID) -> str:
    """Fresh immutable destination key so a replayed form can never overwrite it."""
    return f"{FINAL_PREFIX}{item_id}/{uuid4().hex}"
