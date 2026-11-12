import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from tests.migrations.identity.helpers import NOW
from tests.migrations.portfolio.helpers import final_metadata, item, validated_item

pytestmark = pytest.mark.integration
FINAL_FIELDS = ["object_key", "filename", "media_type", "size_bytes", "sha256", "validated_at"]
OPEN_STATES = ["draft", "pending", "validating", "rejected"]


@pytest.mark.parametrize("state", OPEN_STATES)
@pytest.mark.parametrize("field", FINAL_FIELDS)
def test_open_states_reject_final_metadata(portfolio_db, owned_profile, state, field):
    value = final_metadata()[field]
    with pytest.raises(IntegrityError), portfolio_db.begin_nested():
        item(portfolio_db, owned_profile, state=state, **{field: value})


@pytest.mark.parametrize("state", OPEN_STATES)
def test_open_states_accepted_without_metadata(portfolio_db, owned_profile, state):
    item(portfolio_db, owned_profile, state=state)
    assert portfolio_db.execute(text("SELECT state FROM portfolio_items")).scalar_one() == state


@pytest.mark.parametrize("state", ["validated", "published"])
@pytest.mark.parametrize("field", FINAL_FIELDS)
def test_final_states_require_every_metadata(portfolio_db, owned_profile, state, field):
    extra = {"published_at": NOW} if state == "published" else {}
    with pytest.raises(IntegrityError), portfolio_db.begin_nested():
        validated_item(portfolio_db, owned_profile, state=state, **{field: None}, **extra)


def test_published_requires_published_at_and_others_forbid_it(portfolio_db, owned_profile):
    with pytest.raises(IntegrityError), portfolio_db.begin_nested():
        validated_item(portfolio_db, owned_profile, state="published")
    with pytest.raises(IntegrityError), portfolio_db.begin_nested():
        validated_item(portfolio_db, owned_profile, published_at=NOW)
    with pytest.raises(IntegrityError), portfolio_db.begin_nested():
        item(portfolio_db, owned_profile, published_at=NOW)
    validated_item(portfolio_db, owned_profile, state="published", published_at=NOW)
    assert portfolio_db.execute(
        text("SELECT published_at FROM portfolio_items")
    ).scalar_one() == NOW


def test_state_machine_transitions_allowed_by_checks(portfolio_db, owned_profile):
    ident = item(portfolio_db, owned_profile)
    for state in ("pending", "validating", "rejected", "pending", "validating"):
        portfolio_db.execute(
            text("UPDATE portfolio_items SET state=:state WHERE id=:id"),
            {"state": state, "id": ident},
        )
    columns = ", ".join(f"{field}=:{field}" for field in FINAL_FIELDS)
    portfolio_db.execute(
        text(f"UPDATE portfolio_items SET state='validated', {columns} WHERE id=:id"),
        {**final_metadata(), "id": ident},
    )
    portfolio_db.execute(
        text("UPDATE portfolio_items SET state='published', published_at=:now WHERE id=:id"),
        {"now": NOW, "id": ident},
    )
    portfolio_db.execute(
        text("UPDATE portfolio_items SET state='validated', published_at=NULL WHERE id=:id"),
        {"id": ident},
    )
    row = portfolio_db.execute(text("SELECT state, published_at FROM portfolio_items"))
    assert row.one() == ("validated", None)
