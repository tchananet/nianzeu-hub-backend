"""Proof 7 — public content exists only while the row says published.

`Mirror` re-reads the live row and applies the very predicate the production query
carries, so unpublishing and deleting really drive the answer instead of a queued one.
"""

import anyio
import pytest
from starlette.responses import StreamingResponse

from app.modules.portfolio.content import ContentService
from app.modules.portfolio.publishing import PublishingService
from app.modules.portfolio.service import PortfolioService
from app.shared.errors import AppError
from tests.portfolio.fakes import FakeStorage
from tests.portfolio.items import published, validated
from tests.portfolio.proofs_wiring import PROFILE, USER, VALIDATED, Mirror, wire
from tests.portfolio.session_double import ScriptedSession

BODY = b"x" * 1024


def drain(response: StreamingResponse) -> bytes:
    async def read() -> bytes:
        return b"".join([chunk async for chunk in response.body_iterator])

    return anyio.run(read)


def unreadable(content: ContentService, item_id: object) -> AppError:
    with pytest.raises(AppError) as raised:
        content.stream(item_id)  # type: ignore[arg-type]
    return raised.value


def test_a_validated_item_that_was_never_published_is_not_readable() -> None:
    row = validated(PROFILE)
    context, _, _ = wire(Mirror(row))
    error = unreadable(ContentService(context), row.id)
    assert (error.code, error.status) == ("NOT_FOUND", 404)


def test_content_follows_publication_through_unpublish_and_delete() -> None:
    row = published(PROFILE)
    storage = FakeStorage()
    storage.put(VALIDATED, str(row.object_key), BODY, "image/png")
    context, _, factory = wire(
        Mirror(row),  # first public read, while published
        ScriptedSession(PROFILE, row),  # unpublish
        Mirror(row),  # read refused: the row is no longer published
        ScriptedSession(PROFILE, row),  # publish, state read
        ScriptedSession(PROFILE, row),  # publish, commit
        Mirror(row),  # readable again
        ScriptedSession(PROFILE, row, None),  # delete
        Mirror(None),  # the row is gone
        storage=storage,
    )
    content = ContentService(context)
    publishing, service = PublishingService(context), PortfolioService(context)

    assert drain(content.stream(row.id)) == BODY
    assert publishing.unpublish(USER, row.id).state == "validated"
    assert unreadable(content, row.id).status == 404
    assert publishing.publish(USER, row.id).state == "published"
    assert drain(content.stream(row.id)) == BODY

    service.delete(USER, row.id)
    assert storage.buckets[VALIDATED] == {}, "The final object goes with the row"
    assert unreadable(content, row.id).status == 404
    assert factory.exhausted() and content.slots.used == 0


def test_every_public_read_re_checks_the_database() -> None:
    row = published(PROFILE)
    storage = FakeStorage()
    storage.put(VALIDATED, str(row.object_key), BODY, "image/png")
    first, second = Mirror(row), Mirror(row)
    context, _, _ = wire(first, second, storage=storage)
    content = ContentService(context)
    drain(content.stream(row.id))
    drain(content.stream(row.id))
    # Two reads, two transactions: no cached authorisation survives a state change.
    assert (first.reads, second.reads) == (1, 1)
