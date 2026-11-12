import pytest
from pydantic import ValidationError

from app.modules.contact.schemas import ContactWrite, public_contacts


def payload():
    return dict(email="PRIVATE@example.com", phone="+237699000000", whatsapp=None,
                email_visible=False, phone_visible=True, whatsapp_visible=False)


def test_projection_masks_private_values_and_flags():
    value = ContactWrite.model_validate(payload())
    assert value.email == "private@example.com"
    assert public_contacts(value).model_dump() == {
        "email": None, "phone": "+237699000000", "whatsapp": None,
    }


@pytest.mark.parametrize("changes", [
    {"phone": "699000000"}, {"phone": "+012345678"}, {"phone": "+237 699000000"},
    {"whatsapp_visible": True}, {"email_visible": 1}, {"useInternalForm": True},
])
def test_invalid_contact(changes):
    with pytest.raises(ValidationError):
        ContactWrite.model_validate({**payload(), **changes})
