import json
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.modules.discovery.projection import summary
from app.modules.discovery.responses import ProfileSummary
from app.modules.profiles.responses import SkillRead
from tests.discovery.rows import PRIVATE_MARKERS, PUBLIC_FIELDS, profile_row

SKILL = SkillRead(id=uuid4(), name="Python")


def test_summary_declares_exactly_the_contract_fields():
    assert set(ProfileSummary.model_fields) == PUBLIC_FIELDS


def test_summary_never_exposes_private_data():
    dumped = summary(profile_row(), [SKILL]).model_dump(mode="json")
    assert set(dumped) == PUBLIC_FIELDS
    blob = json.dumps(dumped)
    for marker in PRIVATE_MARKERS:
        assert marker not in blob, marker
    assert dumped["skills"] == [{"id": str(SKILL.id), "name": "Python"}]
    assert dumped["rate"] == {"amount": "15000.00", "currency": "XAF", "unit": "hour"}


def test_absent_rate_and_skills_stay_explicit():
    row = profile_row(rate_amount=None, rate_currency=None, rate_unit=None)
    dumped = summary(row, []).model_dump(mode="json")
    assert dumped["rate"] is None and dumped["skills"] == []
    assert set(dumped) == PUBLIC_FIELDS


@pytest.mark.parametrize("extra", [
    {"bio": "secret-bio"}, {"user_id": str(uuid4())},
    {"contacts": {"email": "a@b.co", "phone": None, "whatsapp": None}},
    {"experiences": []}, {"certifications": []},
])
def test_summary_rejects_injected_private_fields(extra):
    payload = summary(profile_row(), [SKILL]).model_dump() | extra
    with pytest.raises(ValidationError):
        ProfileSummary.model_validate(payload)


@pytest.mark.parametrize("field,value", [
    ("availability", "weekly"), ("experience_level", "expert"),
])
def test_summary_enums_stay_strict(field, value):
    payload = summary(profile_row(), [SKILL]).model_dump() | {field: value}
    with pytest.raises(ValidationError):
        ProfileSummary.model_validate(payload)
