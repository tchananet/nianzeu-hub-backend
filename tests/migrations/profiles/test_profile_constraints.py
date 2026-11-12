from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DataError, IntegrityError

from tests.migrations.identity.helpers import user
from tests.migrations.profiles.helpers import profile

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("changes", [
    {"display_name": ""}, {"headline": ""}, {"city": ""}, {"country_code": "cm"},
    {"availability": "unknown"}, {"experience_level": "expert"}, {"bio": None},
    {"display_name": "x" * 101}, {"bio": "x" * 5001}, {"user_id": uuid4()},
])
def test_invalid_profile(profiles_db, changes):
    with pytest.raises((IntegrityError, DataError)), profiles_db.begin_nested():
        profile(profiles_db, **changes)


def test_one_profile_per_user(profiles_db):
    owner = user(profiles_db)
    profile(profiles_db, user_id=owner)
    with pytest.raises(IntegrityError), profiles_db.begin_nested():
        profile(profiles_db, user_id=owner)


@pytest.mark.parametrize("amount,currency,unit", [
    (1, None, None), (None, "XAF", None), (None, None, "day"),
    (1, "XAF", None), (1, None, "hour"), (None, "XAF", "hour"),
    (0, "XAF", "hour"), (-1, "XAF", "hour"), ("1.50", "XAF", "hour"),
    (1, "USD", "hour"), (1, "XAF", "month"), ("100000000.00", "XAF", "day"),
])
def test_invalid_rate(profiles_db, amount, currency, unit):
    with pytest.raises((IntegrityError, DataError)), profiles_db.begin_nested():
        profile(profiles_db, rate_amount=amount, rate_currency=currency, rate_unit=unit)


@pytest.mark.parametrize("unit", ["hour", "day", "project"])
def test_valid_integer_rate(profiles_db, unit):
    ident = profile(profiles_db, rate_amount="15000.00", rate_currency="XAF", rate_unit=unit)
    assert profiles_db.execute(
        text("SELECT rate_amount FROM talent_profiles WHERE id=:id"), {"id": ident}
    ).scalar_one() == Decimal("15000.00")
