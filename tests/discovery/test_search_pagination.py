import json

import pytest

from app.modules.profiles.service import ProfilesService
from tests.discovery.rows import PRIVATE_MARKERS, PUBLIC_FIELDS
from tests.discovery.seeds import MARKER, names, search

pytestmark = pytest.mark.integration
LEAKS = ("public@example.com", "+237600000001", "+237600000002", *PRIVATE_MARKERS)


def expected_order(seeded):
    """updated_at DESC then id ASC: ada and grace share an instant, so UUID decides."""
    tied = sorted([seeded["ada"][1], seeded["grace"][1]])
    reverse = {profile_id: name for name, (_, profile_id) in seeded.items()}
    return ["linus", "alan", *(reverse[profile_id] for profile_id in tied)]


def test_order_is_updated_at_desc_then_uuid(discovery_db):
    factory, seeded = discovery_db
    assert names(seeded, search(factory, q=MARKER)) == expected_order(seeded)


def test_pages_partition_the_result_without_overlap(discovery_db):
    factory, seeded = discovery_db
    collected = []
    for page_number in (1, 2, 3, 4):
        page = search(factory, q=MARKER, page=page_number, page_size=1)
        assert (page.page, page.page_size, page.total) == (page_number, 1, 4)
        collected.extend(names(seeded, page))
    assert collected == expected_order(seeded)
    assert search(factory, q=MARKER, page=5, page_size=1).items == []


def test_total_follows_the_same_filters_as_the_page(discovery_db):
    factory, _ = discovery_db
    page = search(factory, q=MARKER, page_size=2)
    assert page.total == 4 and len(page.items) == 2
    assert search(factory, q=MARKER, country_code="CM", page_size=1).total == 3
    assert search(factory, q=MARKER, availability="freelance").total == 1


def test_repeated_identical_queries_are_deterministic(discovery_db):
    factory, seeded = discovery_db
    runs = [names(seeded, search(factory, q=MARKER, page_size=3)) for _ in range(3)]
    assert runs[0] == runs[1] == runs[2] == expected_order(seeded)[:3]


def test_search_never_returns_private_data(discovery_db):
    factory, _ = discovery_db
    page = search(factory, q=MARKER)
    blob = json.dumps(page.model_dump(mode="json"))
    for item in page.items:
        assert set(item.model_dump()) == PUBLIC_FIELDS
    for marker in LEAKS:
        assert marker not in blob, marker


def test_rate_is_returned_as_the_contract_string(discovery_db):
    factory, seeded = discovery_db
    page = search(factory, q=MARKER, experience_level="senior")
    rates = {name: item.rate for name, item in zip(names(seeded, page), page.items, strict=True)}
    assert rates["ada"] is None
    assert rates["alan"] is not None
    assert rates["alan"].model_dump() == {"amount": "15000.00", "currency": "XAF",
                                          "unit": "hour"}


def test_deleted_profile_disappears_from_search(discovery_db):
    factory, seeded = discovery_db
    ProfilesService(factory).delete(seeded["linus"][0])
    page = search(factory, q=MARKER)
    assert "linus" not in names(seeded, page) and page.total == 3
