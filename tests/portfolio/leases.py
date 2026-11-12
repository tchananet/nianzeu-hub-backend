from datetime import UTC, datetime, timedelta
from unittest.mock import Mock
from uuid import uuid4

from app.modules.portfolio.context import PortfolioContext
from app.modules.portfolio.download import sha256_hex
from app.modules.portfolio.lease import Lease

QUARANTINE, VALIDATED = "quarantine-test", "validated-test"


def context(storage: object, factory: object | None = None) -> PortfolioContext:
    return PortfolioContext(
        factory=factory or Mock(),
        storage=storage,
        quarantine_bucket=QUARANTINE,
        validated_bucket=VALIDATED,
        clock=lambda: datetime.now(UTC),
    )


def lease_for(
    payload: bytes,
    item_type: str = "image",
    media_type: str = "image/png",
    filename: str = "shot.png",
    key: str = "quarantine/one/two",
) -> Lease:
    return Lease(
        user_id=uuid4(),
        item_id=uuid4(),
        upload_id=uuid4(),
        item_type=item_type,
        quarantine_key=key,
        filename=filename,
        media_type=media_type,
        size_bytes=len(payload),
        sha256=sha256_hex(payload),
        lease_until=datetime.now(UTC) + timedelta(seconds=60),
    )
