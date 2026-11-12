from uuid import UUID

import pytest

from app.modules.discovery.filters import skill_subquery
from tests.discovery.explain import counted_statements, page_statement, plan_of
from tests.discovery.seeds import MARKER, PYTHON, REACT, search

pytestmark = pytest.mark.integration
SKILLS = [UUID(PYTHON), UUID(REACT)]


def test_default_ordering_walks_the_updated_at_index_without_sorting(discovery_db):
    factory, _ = discovery_db
    with factory.begin() as db:
        plan = plan_of(db, page_statement(page_size=20))
    assert "talent_profiles" in plan
    assert "Index Scan" in plan or "Index Only Scan" in plan, plan
    assert "Sort" not in plan, plan


@pytest.mark.parametrize("filters", [
    {"availability": "immediate"}, {"experience_level": "senior"},
    {"city": "douala", "country_code": "CM"},
])
def test_scalar_filters_reach_an_index_path(discovery_db, filters):
    factory, _ = discovery_db
    with factory.begin() as db:
        plan = plan_of(db, page_statement(**filters))
    assert "Seq Scan on talent_profiles" not in plan, plan
    assert "Index" in plan, plan


def test_skill_conjunction_reaches_the_profile_skills_index(discovery_db):
    factory, _ = discovery_db
    with factory.begin() as db:
        plan = plan_of(db, skill_subquery(SKILLS))
    assert "profile_skills" in plan
    assert "Seq Scan on profile_skills" not in plan, plan
    assert "Index" in plan, plan


def test_keyword_scan_stays_bounded_and_needs_no_extra_index(discovery_db):
    factory, _ = discovery_db
    with factory.begin() as db:
        plan = plan_of(db, page_statement(q=MARKER), seqscan=True)
    # profiles.md accepts a bounded scan for substring q at the 500 account target.
    assert "talent_profiles" in plan and "Limit" in plan, plan


@pytest.mark.parametrize("page_size", [1, 20, 50])
def test_statement_count_is_bounded_and_independent_of_page_size(discovery_db, page_size):
    factory, _ = discovery_db
    with counted_statements() as recorded:
        page = search(factory, q=MARKER, page_size=page_size)
    selects = [one for one in recorded if one.lstrip().upper().startswith("SELECT")]
    assert page.total == 4
    assert len(selects) == 3, selects
    assert len(recorded) <= 5, recorded


def test_empty_result_skips_the_skills_statement(discovery_db):
    factory, _ = discovery_db
    with counted_statements() as recorded:
        search(factory, q="no-such-profile-token")
    selects = [one for one in recorded if one.lstrip().upper().startswith("SELECT")]
    assert len(selects) == 2, selects
    assert not [one for one in selects if "profile_skills" in one]
