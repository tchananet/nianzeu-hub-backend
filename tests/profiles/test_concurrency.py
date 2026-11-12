from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.modules.profiles.schemas import ProfileWrite
from app.modules.profiles.service import ProfilesService
from app.modules.profiles.view_models import ProfileView, ViewDedup
from app.modules.profiles.views import ViewsService
from tests.profiles.payloads import profile_payload

pytestmark = pytest.mark.integration


def test_concurrent_create_serializes_to_one_profile(profile_db):
    factory, (a, _) = profile_db
    service = ProfilesService(factory)
    data = ProfileWrite.model_validate(profile_payload())
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: service.put(a, data), range(2)))
    assert sorted(created for _, created in results) == [False, True]
    assert results[0][0].id == results[1][0].id


def test_views_deduplicate_and_expire(profile_db):
    factory, (a, _) = profile_db
    row, _ = ProfilesService(factory).put(a, ProfileWrite.model_validate(profile_payload()))
    now = [datetime(2026, 1, 1, tzinfo=UTC)]
    service = ViewsService(factory, lambda: now[0])
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: service.record(row.id, "a" * 64), range(4)))
    with factory() as db:
        assert db.scalar(select(ProfileView.count).where(ProfileView.profile_id == row.id)) == 1
        assert db.scalar(select(func.count()).select_from(ViewDedup)
                         .where(ViewDedup.profile_id == row.id)) == 1
    now[0] += timedelta(days=1)
    service.record(row.id, "a" * 64)
    now[0] += timedelta(days=92)
    dedup, aggregates = service.purge()
    assert dedup >= 2 and aggregates >= 2
