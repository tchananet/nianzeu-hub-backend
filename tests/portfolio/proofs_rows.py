"""Row builders for the O01 proofs: a lockable user and a reservation row."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.modules.portfolio import states
from app.modules.portfolio.download import sha256_hex
from app.modules.portfolio.models import PortfolioUpload


class ActiveUser:
    """`repository.lock_user` reads nothing but `is_active` off the locked row."""

    __test__ = False
    is_active = True


def reservation(item_id: UUID, payload: bytes = b"", **overrides: object) -> PortfolioUpload:
    now = datetime.now(UTC)
    fields: dict[str, object] = {
        "id": uuid4(),
        "item_id": item_id,
        "quarantine_key": f"quarantine/{uuid4().hex}/{uuid4().hex}",
        "filename": "shot.png",
        "media_type": "image/png",
        "size_bytes": len(payload) or 1024,
        "sha256": sha256_hex(payload),
        "created_at": now,
        "expires_at": now + timedelta(seconds=states.UPLOAD_TTL_SECONDS),
        "lease_until": None,
        "reservation_active": True,
    }
    return PortfolioUpload(**(fields | overrides))
