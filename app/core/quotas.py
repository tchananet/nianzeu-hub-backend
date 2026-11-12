import re
from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import transaction
from app.core.primitives import Clock, utc_now
from app.shared.errors import DependencyUnavailable, RateLimited

INCREMENT = text("""
INSERT INTO rate_limit_windows (scope, key_hash, window_start, expires_at, count)
VALUES (:scope, :key_hash, :start, :expires, 1)
ON CONFLICT (scope, key_hash, window_start)
DO UPDATE SET count = rate_limit_windows.count + 1
RETURNING count
""")


def consume(
    factory: sessionmaker[Session],
    scope: str,
    key_hash: str,
    limit: int,
    seconds: int,
    clock: Clock = utc_now,
) -> None:
    if not 1 <= len(scope) <= 40 or not re.fullmatch(r"[0-9a-f]{64}", key_hash):
        raise ValueError("Invalid quota key")
    if limit < 1 or seconds < 1:
        raise ValueError("Positive quota limits required")
    now = clock()
    if now.utcoffset() != timedelta(0):
        raise ValueError("UTC aware clock required")
    start = datetime.fromtimestamp(int(now.timestamp()) // seconds * seconds, UTC)
    end = start + timedelta(seconds=seconds)
    try:
        # Separate committed transaction: failed requests and refusals count too.
        with transaction(factory) as session:
            count = session.execute(
                INCREMENT,
                dict(
                    scope=scope,
                    key_hash=key_hash,
                    start=start,
                    expires=end,
                ),
            ).scalar_one()
    except SQLAlchemyError:
        raise DependencyUnavailable() from None
    if count > limit:
        remaining = (end - now).total_seconds()
        raise RateLimited(max(1, int(-(-remaining // 1))))


def purge_expired(factory: sessionmaker[Session], clock: Clock = utc_now) -> int:
    now = clock()
    if now.utcoffset() != timedelta(0):
        raise ValueError("UTC aware clock required")
    try:
        with transaction(factory) as session:
            result = session.execute(
                text("DELETE FROM rate_limit_windows WHERE expires_at < :cutoff RETURNING scope"),
                {"cutoff": now - timedelta(hours=24)},
            )
            return len(result.all())
    except SQLAlchemyError:
        raise DependencyUnavailable() from None
