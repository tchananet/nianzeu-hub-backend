from uuid import uuid4

import pytest
from fastapi.exceptions import RequestValidationError

from app.modules.contact.service import ContactService
from app.modules.profiles.schemas import ProfileWrite
from app.modules.profiles.service import ProfilesService
from app.shared.errors import AppError
from tests.profiles.payloads import profile_payload

pytestmark = pytest.mark.integration


def test_create_replace_privacy_delete_and_recreate(profile_db):
    factory, (a, b) = profile_db
    service, contacts = ProfilesService(factory), ContactService(factory)
    data = ProfileWrite.model_validate(profile_payload())
    owner, created = service.put(a, data)
    assert created and owner.user_id == a
    public = service.get_public(owner.id).model_dump()
    assert "user_id" not in public and "skill_ids" not in public
    assert public["contacts"] == {"email": None, "phone": "+237699000000", "whatsapp": None}
    assert contacts.get_public(owner.id).model_dump() == public["contacts"]
    with pytest.raises(AppError) as error:
        service.get_owner(b)
    assert error.value.status == 404
    updated, created = service.put(a, data)
    assert not created and updated.id == owner.id
    assert updated.experiences[0].id != owner.experiences[0].id
    assert updated.certifications[0].id != owner.certifications[0].id
    service.delete(a)
    for call in [lambda: service.get_public(owner.id), lambda: contacts.get_public(owner.id),
                 lambda: service.delete(a)]:
        with pytest.raises(AppError) as error:
            call()
        assert error.value.status == 404
    recreated, created = service.put(a, data)
    assert created and recreated.id != owner.id


def test_unknown_skill_rolls_back_entire_put(profile_db):
    factory, (a, _) = profile_db
    service = ProfilesService(factory)
    original, _ = service.put(a, ProfileWrite.model_validate(profile_payload()))
    data = ProfileWrite.model_validate({**profile_payload(), "display_name": "Changed",
                                       "skill_ids": [str(uuid4())]})
    with pytest.raises(RequestValidationError):
        service.put(a, data)
    assert service.get_owner(a) == original
