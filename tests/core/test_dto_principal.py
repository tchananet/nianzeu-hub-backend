from typing import Annotated
from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.shared.dto import DTO, Pagination
from app.shared.http_errors import install_error_handlers
from app.shared.principal import Principal, require_principal


@pytest.mark.parametrize(
    "values",
    [
        {"page": True},
        {"page": "1"},
        {"page": 0},
        {"page_size": 51},
        {"page": 500, "page_size": 50},
        {"unknown": 1},
    ],
)
def test_pagination_rejects_invalid(values):
    with pytest.raises(ValidationError):
        Pagination.model_validate(values)


def test_pagination_and_text():
    assert Pagination(page=2).offset == 20

    class Label(DTO):
        label: str

    assert Label(label=" <b>text</b> ").label == "<b>text</b>"
    with pytest.raises(ValidationError):
        Label(label="text\x00")


def test_principal_override_needs_no_shared_edit():
    app = FastAPI()
    install_error_handlers(app)

    @app.get("/private")
    def private(principal: Annotated[Principal, Depends(require_principal)]):
        return {"user_id": str(principal.user_id)}

    principal = Principal(uuid4(), uuid4())
    with TestClient(app) as client:
        assert client.get("/private").status_code == 401
        app.dependency_overrides[require_principal] = lambda: principal
        assert client.get("/private").json() == {"user_id": str(principal.user_id)}
