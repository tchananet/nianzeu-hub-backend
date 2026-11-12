import hmac
import re
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.primitives import new_secret, secret_hash
from app.modules.identity.models import LoginSession, User
from app.shared.errors import AppError


def token_digest(token: str | None) -> str | None:
    if token is None or re.fullmatch(r"[A-Za-z0-9_-]{43}", token) is None:
        return None
    return secret_hash(token)


def active(session: LoginSession, now: datetime) -> bool:
    return (session.revoked_at is None and session.expires_at > now
            and session.last_seen_at > now - timedelta(hours=24))


def resolve(db: Session, token: str | None, now: datetime) -> tuple[User, LoginSession]:
    digest = token_digest(token)
    row = db.scalar(select(LoginSession).where(LoginSession.token_hash == digest))
    if row is None:
        raise AppError("AUTH_REQUIRED", 401, "Authentication required")
    # Same lock order as login: user first, then session. Refresh after waiting.
    user = db.scalar(select(User).where(User.id == row.user_id).with_for_update())
    db.refresh(row, with_for_update=True)
    if user is None or not user.is_active or not active(row, now):
        raise AppError("AUTH_REQUIRED", 401, "Authentication required")
    row.last_seen_at = max(row.last_seen_at, now)
    return user, row


def check_csrf(session: LoginSession, supplied: str | None) -> None:
    if supplied is None or not hmac.compare_digest(
        session.csrf_token.encode("utf-8"), supplied.encode("utf-8"),
    ):
        raise AppError("CSRF_FAILED", 403, "CSRF validation failed")


def issue(db: Session, user: User, now: datetime) -> tuple[LoginSession, str]:
    # Caller holds the user's FOR UPDATE lock until commit.
    rows = db.scalars(select(LoginSession).where(
        LoginSession.user_id == user.id, LoginSession.revoked_at.is_(None),
    ).order_by(LoginSession.created_at, LoginSession.id)).all()
    live = [row for row in rows if active(row, now)]
    for row in live[:max(0, len(live) - 4)]:
        row.revoked_at = now
    secret = new_secret()
    session = LoginSession(
        id=uuid4(), user_id=user.id, token_hash=secret_hash(secret), csrf_token=new_secret(),
        created_at=now, last_seen_at=now, expires_at=now + timedelta(days=7), revoked_at=None,
    )
    db.add(session)
    db.flush()
    return session, secret
