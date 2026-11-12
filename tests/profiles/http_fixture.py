from unittest.mock import Mock
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient

from app.core.primitives import utc_now
from app.modules.contact.routes import create_router as contact_router
from app.modules.contact.service import ContactService
from app.modules.profiles.access import no_query, private_headers
from app.modules.profiles.responses import ProfileOwner
from app.modules.profiles.routes import create_router
from app.modules.profiles.schemas import ProfileWrite
from app.modules.profiles.service import ProfilesService
from app.modules.profiles.views import ViewsService
from app.shared.http_errors import install_error_handlers
from app.shared.principal import Principal
from tests.profiles.payloads import profile_payload


class TestAccess:
    __test__ = False

    def __init__(self):
        self.principal = Principal(uuid4(), uuid4())

    def owner(self, request: Request, response: Response) -> Principal:
        no_query(request)
        private_headers(response)
        return self.principal

    def public(self, request: Request, response: Response) -> None:
        no_query(request)
        private_headers(response)

    def public_limit(self, request: Request) -> None:
        return None

    def view(self, request: Request, response: Response) -> str:
        self.public(request, response)
        return "a" * 64


def http_fixture():
    access = TestAccess()
    service, contacts, views = Mock(spec=ProfilesService), Mock(spec=ContactService), Mock()
    parsed = ProfileWrite.model_validate(profile_payload()).model_dump()
    for name in ("experiences", "certifications"):
        parsed[name] = [{**item, "id": uuid4()} for item in parsed[name]]
    owner = ProfileOwner.model_validate({**parsed, "id": uuid4(),
                                        "user_id": access.principal.user_id,
                                        "created_at": utc_now(), "updated_at": utc_now()})
    service.put.return_value = owner, True
    service.get_owner.return_value = owner
    contacts.get_owner.return_value = owner.contacts
    contacts.put.return_value = owner.contacts
    views = Mock(spec=ViewsService)
    app = FastAPI()
    install_error_handlers(app)
    app.include_router(contact_router(contacts, access))
    app.include_router(create_router(service, views, access))
    return TestClient(app), service, contacts, views, owner
