"""Publication refuses anything that is not a validated item with a real final object."""

from uuid import uuid4

import pytest

from app.shared.errors import AppError, DependencyUnavailable
from tests.portfolio.items import item, published, validated
from tests.portfolio.publishing_fixture import PROFILE, USER, build, stored
from tests.portfolio.session_double import ScriptedSession, unavailable


@pytest.mark.parametrize("state", ["draft", "pending", "validating", "rejected"])
def test_publishing_before_validation_is_refused(state):
    service, _, _ = build(ScriptedSession(PROFILE, item(PROFILE, state=state)))
    with pytest.raises(AppError) as raised:
        service.publish(USER, uuid4())
    assert (raised.value.code, raised.value.status) == ("INVALID_STATE", 409)


def test_publishing_an_already_published_item_is_idempotent():
    row = published(PROFILE)
    session = ScriptedSession(PROFILE, row)
    service, _, factory = build(session)
    result = service.publish(USER, row.id)
    assert result.state == "published"
    assert result.published_at == row.published_at
    # No second transaction and no write: the timestamps must not move.
    assert session.flushes == 0 and factory.exhausted()


def test_publishing_without_the_final_object_fails_closed():
    service, _, _ = build(ScriptedSession(PROFILE, validated(PROFILE)))
    with pytest.raises(DependencyUnavailable):
        service.publish(USER, uuid4())


def test_publishing_refuses_an_object_whose_size_drifted():
    row = validated(PROFILE)
    service, store, _ = build(ScriptedSession(PROFILE, row))
    stored(store, str(row.object_key), 10)  # recorded size is 1024
    with pytest.raises(DependencyUnavailable):
        service.publish(USER, row.id)


def test_publishing_a_validated_item_marks_it_published():
    row = validated(PROFILE)
    read, write = ScriptedSession(PROFILE, row), ScriptedSession(PROFILE, row)
    service, store, factory = build(read, write)
    stored(store, str(row.object_key), 1024)
    result = service.publish(USER, row.id)
    assert result.state == "published" and result.published_at is not None
    assert row.state == "published" and write.flushes == 1
    assert factory.exhausted()


def test_a_third_party_or_absent_item_is_not_found():
    service, _, _ = build(ScriptedSession(PROFILE, None))
    with pytest.raises(AppError) as raised:
        service.publish(USER, uuid4())
    assert (raised.value.code, raised.value.status) == ("NOT_FOUND", 404)


def test_an_owner_without_a_profile_learns_nothing_about_the_item():
    # Item routes must not reveal whether the profile or the item is the missing one.
    service, _, _ = build(ScriptedSession(None))
    with pytest.raises(AppError) as raised:
        service.publish(USER, uuid4())
    assert (raised.value.code, raised.value.status) == ("NOT_FOUND", 404)


def test_a_database_outage_surfaces_as_a_dependency_failure():
    service, _, _ = build(error=unavailable())
    with pytest.raises(DependencyUnavailable):
        service.publish(USER, uuid4())
