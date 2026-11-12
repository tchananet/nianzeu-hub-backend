import pytest
from pydantic import ValidationError

from app.modules.profiles.schemas import ProfileWrite
from tests.profiles.payloads import profile_payload


@pytest.mark.parametrize("changes", [
    {"country_code": "XX"}, {"country_code": "cm"}, {"availability": "soon"},
    {"experience_level": "expert"}, {"display_name": " "}, {"photoHint": "avatar"},
    {"user_id": "00000000-0000-4000-8000-000000000001"},
    {"skill_ids": ["00000000-0000-4000-8000-000000000001"] * 2},
    {"skill_ids": [123]}, {"unexpected": True},
])
def test_invalid_profile(changes):
    with pytest.raises(ValidationError):
        ProfileWrite.model_validate({**profile_payload(), **changes})


def test_complete_put_and_collection_limits():
    data = profile_payload()
    parsed = ProfileWrite.model_validate(data)
    assert str(parsed.skill_ids[0]) == data["skill_ids"][0]
    for field in data:
        with pytest.raises(ValidationError):
            ProfileWrite.model_validate(
                {key: value for key, value in data.items() if key != field})
    for field in ["experiences", "certifications"]:
        with pytest.raises(ValidationError):
            ProfileWrite.model_validate({**data, field: data[field] * 21})
