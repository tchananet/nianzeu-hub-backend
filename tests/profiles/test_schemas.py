import pytest
from pydantic import ValidationError

from app.modules.profiles.entries import CertificationWrite, ExperienceWrite
from app.modules.profiles.schemas import Rate


@pytest.mark.parametrize("amount", ["0.00", "1.50", "1", "1e2", "100000000.00", 100, True])
def test_invalid_xaf(amount):
    with pytest.raises(ValidationError):
        Rate.model_validate({"amount": amount, "currency": "XAF", "unit": "hour"})


def test_xaf_and_dates():
    assert Rate(amount="15000.00", currency="XAF", unit="day").amount == "15000.00"
    data = dict(title="Developer", organization="Company", description="",
                start_date="2020-01-01", end_date=None)
    assert ExperienceWrite.model_validate(data).end_date is None
    for changes in [{"start_date": "2999-01-01"}, {"end_date": "2019-01-01"},
                    {"start_date": "2020-01"}, {"isCurrent": True}]:
        with pytest.raises(ValidationError):
            ExperienceWrite.model_validate({**data, **changes})


def test_certification_url_and_expiry():
    data = dict(name="Certificate", issuer="Issuer", issued_on="2020-01-01",
                expires_on="2999-01-01", credential_url="https://example.com/certificate")
    CertificationWrite.model_validate(data)
    for changes in [{"credential_url": "http://example.com"},
                    {"credential_url": "https://user:pass@example.com"},
                    {"expires_on": "2019-01-01"}]:
        with pytest.raises(ValidationError):
            CertificationWrite.model_validate({**data, **changes})
