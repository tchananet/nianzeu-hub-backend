"""Download slots must come back, including when nobody reads the response body.

The public content route holds a bounded number of concurrent downloads. A slot that is
taken and never returned is permanent: once enough leak, every public read answers 503
for the lifetime of the process.
"""

import gc

import anyio
import pytest

from app.modules.portfolio.concurrency import Slots
from app.modules.portfolio.content import ContentService
from app.modules.portfolio.context import PortfolioContext
from app.shared.errors import DependencyUnavailable
from tests.portfolio.fakes import FakeStorage
from tests.portfolio.items import published
from tests.portfolio.session_double import ScriptedFactory, ScriptedSession

VALIDATED = "validated"


def drain(response) -> bytes:
    """StreamingResponse exposes an async iterator, so read it on an event loop."""
    async def read() -> bytes:
        return b"".join([chunk async for chunk in response.body_iterator])

    return anyio.run(read)


def service(*rows, capacity=2):
    storage = FakeStorage()
    for row in rows:
        storage.put(VALIDATED, str(row.object_key), b"x" * int(row.size_bytes or 0), "image/png")
    factory = ScriptedFactory(*(ScriptedSession(row) for row in rows))
    context = PortfolioContext(
        factory=factory,  # type: ignore[arg-type]
        storage=storage,
        quarantine_bucket="quarantine",
        validated_bucket=VALIDATED,
    )
    slots = Slots(capacity, DependencyUnavailable)
    return ContentService(context, slots=slots), slots


def test_a_consumed_response_returns_its_slot() -> None:
    item = published()
    content, slots = service(item)
    response = content.stream(item.id)
    assert drain(response) == b"x" * 1024
    assert slots.used == 0


def test_a_discarded_response_returns_its_slot() -> None:
    # Starlette stops iterating when the client disconnects, so the body may never be
    # read. The slot must still be reclaimed once the response is dropped.
    item = published()
    content, slots = service(item)
    response = content.stream(item.id)
    assert slots.used == 1
    del response
    gc.collect()
    assert slots.used == 0


def test_capacity_is_enforced_while_downloads_are_in_flight() -> None:
    first, second, third = published(), published(), published()
    content, slots = service(first, second, third, capacity=2)
    held = [content.stream(first.id), content.stream(second.id)]
    assert slots.used == 2
    with pytest.raises(DependencyUnavailable):
        content.stream(third.id)
    for response in held:
        drain(response)
    assert slots.used == 0
