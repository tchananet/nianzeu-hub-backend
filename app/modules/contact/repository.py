from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.contact.models import Contact
from app.modules.contact.schemas import ContactWrite


def read_contact(db: Session, profile_id: UUID) -> ContactWrite:
    row = db.get(Contact, profile_id)
    if row is None:
        raise RuntimeError("Profile contact invariant violated")
    return ContactWrite.model_validate({
        name: getattr(row, name) for name in ContactWrite.model_fields
    })


def write_contact(db: Session, profile_id: UUID, data: ContactWrite) -> None:
    row = db.get(Contact, profile_id)
    if row is None:
        row = Contact(profile_id=profile_id)
        db.add(row)
    for name, value in data.model_dump().items():
        setattr(row, name, value)
    db.flush()
