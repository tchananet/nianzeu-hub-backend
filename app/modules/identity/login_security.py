from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.identity.models import LoginSession, User
from app.modules.identity.sessions import active, check_csrf, token_digest


def lock_login(db: Session, email: str, token: str | None,
               csrf: str | None, now: datetime) -> LoginSession | None:
    target = db.scalar(select(User.id).where(User.email == email))
    previous = db.scalar(select(LoginSession).where(
        LoginSession.token_hash == token_digest(token)))
    ids = {target} if target is not None else set()
    if previous is not None:
        ids.add(previous.user_id)
    # Stable ordering also covers concurrent A->B and B->A session rotations.
    users = db.scalars(
        select(User).where(User.id.in_(ids)).order_by(User.id).with_for_update()).all()
    if previous is not None:
        db.refresh(previous, with_for_update=True)
        enabled = any(u.id == previous.user_id and u.is_active for u in users)
        if enabled and active(previous, now):
            check_csrf(previous, csrf)
            return previous
    return None
