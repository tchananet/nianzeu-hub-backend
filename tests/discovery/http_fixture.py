from unittest.mock import Mock
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.modules.discovery.projection import summary
from app.modules.discovery.responses import ProfileSummary
from app.modules.discovery.routes import create_router
from app.modules.discovery.service import DiscoveryService
from app.modules.profiles.responses import SkillRead
from app.shared.dto import Page
from app.shared.http_errors import install_error_handlers
from tests.discovery.rows import profile_row


class StubReads:
    """Records the shared public-read quota calls instead of touching PostgreSQL."""

    __test__ = False

    def __init__(self):
        self.calls: list[str] = []

    def public_limit(self, request: Request) -> None:
        self.calls.append(request.url.query)


def one_page():
    item = summary(profile_row(), [SkillRead(id=uuid4(), name="Python")])
    return Page[ProfileSummary](items=[item], page=1, page_size=20, total=1)


def http_fixture(page=None):
    access = StubReads()
    service = Mock(spec=DiscoveryService)
    service.search.return_value = page or Page[ProfileSummary](
        items=[], page=1, page_size=20, total=0)
    app = FastAPI()
    install_error_handlers(app)
    app.include_router(create_router(service, access))
    return TestClient(app), service, access
