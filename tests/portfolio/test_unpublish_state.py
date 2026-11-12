"""Unpublishing returns an item to validated and is idempotent there."""

from uuid import uuid4

import pytest

from app.shared.errors import AppError, DependencyUnavailable
from tests.portfolio.items import item, published, validated
from tests.portfolio.publishing_fixture import PROFILE, USER, build
from tests.portfolio.session_double import ScriptedSession, unavailable


def test_unpublishing_a_published_item_withdraws_it():
    row = published(PROFILE)
    session = ScriptedSession(PROFILE, row)
    service, _, factory = build(session)
    result = service.unpublish(USER, row.id)
    assert result.state == "validated" and result.published_at is None
    # The final file metadata survives: only publication is withdrawn.
    assert row.object_key is not None and row.validated_at is not None
    assert session.flushes == 1 and factory.exhausted()


def test_unpublishing_a_validated_item_is_idempotent():
    row = validated(PROFILE)
    session = ScriptedSession(PROFILE, row)
    service, _, _ = build(session)
    result = service.unpublish(USER, row.id)
    assert result.state == "validated"
    assert session.flushes == 0


@pytest.mark.parametrize("state", ["draft", "pending", "validating", "rejected"])
def test_unpublishing_an_unvalidated_item_is_refused(state):
    service, _, _ = build(ScriptedSession(PROFILE, item(PROFILE, state=state)))
    with pytest.raises(AppError) as raised:
        service.unpublish(USER, uuid4())
    assert (raised.value.code, raised.value.status) == ("INVALID_STATE", 409)


def test_unpublishing_a_third_party_item_is_not_found():
    service, _, _ = build(ScriptedSession(PROFILE, None))
    with pytest.raises(AppError) as raised:
        service.unpublish(USER, uuid4())
    assert raised.value.status == 404


def test_unpublishing_during_a_database_outage_changes_nothing():
    service, _, _ = build(error=unavailable())
    with pytest.raises(DependencyUnavailable):
        service.unpublish(USER, uuid4())
