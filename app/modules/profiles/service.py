from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from app.core.primitives import Clock, utc_now
from app.modules.profiles import projections
from app.modules.profiles.repository import own_profile, public_profile, transaction
from app.modules.profiles.responses import ProfileOwner, ProfilePublic
from app.modules.profiles.schemas import ProfileWrite
from app.modules.profiles.writes import replace


class ProfilesService:
    def __init__(self, factory: sessionmaker[Session], clock: Clock = utc_now) -> None:
        self.factory, self.clock = factory, clock

    def get_owner(self, user_id: UUID) -> ProfileOwner:
        with transaction(self.factory) as db:
            return projections.owner(db, own_profile(db, user_id))

    def get_public(self, profile_id: UUID) -> ProfilePublic:
        with transaction(self.factory) as db:
            return projections.public(db, public_profile(db, profile_id))

    def put(self, user_id: UUID, data: ProfileWrite) -> tuple[ProfileOwner, bool]:
        with transaction(self.factory) as db:
            row, created = replace(db, user_id, data, self.clock())
            return projections.owner(db, row), created

    def delete(self, user_id: UUID) -> None:
        with transaction(self.factory) as db:
            db.delete(own_profile(db, user_id, write=True))
