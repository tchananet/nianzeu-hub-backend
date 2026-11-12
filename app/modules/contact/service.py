from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from app.core.primitives import Clock, utc_now
from app.modules.contact.repository import read_contact, write_contact
from app.modules.contact.schemas import ContactPublic, ContactWrite, public_contacts
from app.modules.profiles.repository import own_profile, public_profile, transaction


class ContactService:
    def __init__(self, factory: sessionmaker[Session], clock: Clock = utc_now) -> None:
        self.factory, self.clock = factory, clock

    def get_owner(self, user_id: UUID) -> ContactWrite:
        with transaction(self.factory) as db:
            return read_contact(db, own_profile(db, user_id).id)

    def get_public(self, profile_id: UUID) -> ContactPublic:
        with transaction(self.factory) as db:
            return public_contacts(read_contact(db, public_profile(db, profile_id).id))

    def put(self, user_id: UUID, data: ContactWrite) -> ContactWrite:
        with transaction(self.factory) as db:
            row = own_profile(db, user_id, write=True)
            write_contact(db, row.id, data)
            row.updated_at = self.clock()
            return read_contact(db, row.id)
