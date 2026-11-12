import re
from datetime import timedelta
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from app.core.primitives import Clock, utc_now
from app.modules.profiles.repository import public_profile, transaction
from app.modules.profiles.view_models import ProfileView, ViewDedup


class ViewsService:
    def __init__(self, factory: sessionmaker[Session], clock: Clock = utc_now) -> None:
        self.factory, self.clock = factory, clock

    def record(self, profile_id: UUID, visitor_hash: str) -> None:
        if re.fullmatch(r"[0-9a-f]{64}", visitor_hash) is None:
            raise ValueError("Hashed visitor identifier required")
        now = self.clock()
        if now.utcoffset() != timedelta(0):
            raise ValueError("UTC clock required")
        with transaction(self.factory) as db:
            public_profile(db, profile_id)
            inserted = db.scalar(insert(ViewDedup).values(
                profile_id=profile_id, day=now.date(), visitor_hash=visitor_hash,
                expires_at=now + timedelta(hours=48),
            ).on_conflict_do_nothing().returning(ViewDedup.profile_id))
            if inserted is not None:
                db.execute(insert(ProfileView).values(
                    profile_id=profile_id, day=now.date(), count=1)
                           .on_conflict_do_update(index_elements=["profile_id", "day"],
                                                 set_={"count": ProfileView.count + 1}))

    def purge(self) -> tuple[int, int]:
        now = self.clock()
        with transaction(self.factory) as db:
            dedup = db.execute(delete(ViewDedup).where(ViewDedup.expires_at <= now)
                               .returning(ViewDedup.profile_id)).all()
            aggregates = db.execute(delete(ProfileView).where(
                ProfileView.day < now.date() - timedelta(days=90),
            ).returning(ProfileView.profile_id)).all()
            return len(dedup), len(aggregates)
