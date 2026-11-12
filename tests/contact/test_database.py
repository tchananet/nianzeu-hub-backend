import pytest

from app.modules.contact.schemas import ContactWrite
from app.modules.contact.service import ContactService
from app.modules.profiles.schemas import ProfileWrite
from app.modules.profiles.service import ProfilesService
from app.shared.errors import AppError
from tests.profiles.payloads import profile_payload

pytestmark = pytest.mark.integration


def test_owner_only_update_and_consistent_public_projection(profile_db):
    factory, (a, b) = profile_db
    profiles, contacts = ProfilesService(factory), ContactService(factory)
    profile, _ = profiles.put(a, ProfileWrite.model_validate(profile_payload()))
    data = ContactWrite.model_validate({**profile_payload()["contacts"], "email_visible": True,
                                       "phone_visible": False})
    with pytest.raises(AppError) as error:
        contacts.put(b, data)
    assert error.value.status == 404
    assert contacts.get_owner(a).email_visible is False
    assert contacts.put(a, data) == data
    expected = {"email": "private@example.com", "phone": None, "whatsapp": None}
    assert contacts.get_public(profile.id).model_dump() == expected
    assert profiles.get_public(profile.id).contacts.model_dump() == expected
    assert profiles.get_owner(a).contacts == data
