from uuid import uuid4

import pytest

from tests.discovery.seeds import DESIGN, MARKER, PYTHON, REACT, names, search

pytestmark = pytest.mark.integration
BACKSLASH = chr(92)


def found(factory, seeded, **kwargs):
    return sorted(names(seeded, search(factory, q=MARKER, **kwargs)))


def test_keyword_matches_display_name_headline_and_bio(discovery_db):
    factory, seeded = discovery_db
    assert found(factory, seeded) == ["ada", "alan", "grace", "linus"]
    assert sorted(names(seeded, search(factory, q="grace hopper"))) == ["grace"]
    assert sorted(names(seeded, search(factory, q="DEVOPS"))) == ["linus"]
    assert sorted(names(seeded, search(factory, q="of maths"))) == ["alan"]


def test_keyword_is_case_insensitive_and_keeps_wildcards_literal(discovery_db):
    factory, seeded = discovery_db
    assert sorted(names(seeded, search(factory, q="aDa"))) == ["ada", "alan"]
    assert sorted(names(seeded, search(factory, q="100%"))) == ["grace"]
    # A lone % must not act as a wildcard: of this test's seeds, only the one whose
    # bio really contains "100%" may match. Every suite shares one database, so rows
    # seeded elsewhere are ignored -- this asserts the escaping, not the table size.
    wildcard = [name for name in names(seeded, search(factory, q="%"))
                if not name.startswith("foreign:")]
    assert sorted(wildcard) == ["grace"]
    for injection in ["_", BACKSLASH, f"{MARKER}%", "' OR 1=1 --"]:
        assert search(factory, q=injection).total == 0, injection


def test_keyword_keeps_accents(discovery_db):
    factory, seeded = discovery_db
    assert found(factory, seeded, city="Yaounde") == []
    assert found(factory, seeded, city="yaoundé") == ["alan"]


@pytest.mark.parametrize("filters,expected", [
    ({"availability": "immediate"}, ["ada", "alan"]),
    ({"availability": "freelance"}, ["grace"]),
    ({"availability": "full-time"}, ["linus"]),
    ({"experience_level": "senior"}, ["ada", "alan"]),
    ({"experience_level": "junior"}, ["grace"]),
    ({"city": "douala"}, ["ada", "grace"]),
    ({"city": "DOUALA"}, ["ada", "grace"]),
    ({"country_code": "CM"}, ["ada", "alan", "grace"]),
    ({"country_code": "FR"}, ["linus"]),
    ({"skill_id": [PYTHON]}, ["ada", "grace"]),
    ({"skill_id": [REACT]}, ["grace"]),
    ({"skill_id": [PYTHON, REACT]}, ["grace"]),
    ({"skill_id": [PYTHON, DESIGN]}, []),
    ({"skill_id": [REACT, DESIGN]}, []),
])
def test_each_filter_and_skill_conjunction(discovery_db, filters, expected):
    factory, seeded = discovery_db
    assert found(factory, seeded, **filters) == expected


def test_every_filter_combined(discovery_db):
    factory, seeded = discovery_db
    assert found(factory, seeded, skill_id=[PYTHON, REACT], city="Douala", country_code="CM",
                 availability="freelance", experience_level="junior") == ["grace"]
    assert found(factory, seeded, skill_id=[PYTHON], city="Douala", country_code="CM",
                 availability="immediate", experience_level="senior") == ["ada"]
    assert found(factory, seeded, skill_id=[PYTHON], country_code="FR") == []


def test_unknown_but_well_formed_skill_returns_an_empty_page(discovery_db):
    factory, _ = discovery_db
    page = search(factory, skill_id=[str(uuid4())])
    assert page.items == [] and page.total == 0
    assert (page.page, page.page_size) == (1, 20)
