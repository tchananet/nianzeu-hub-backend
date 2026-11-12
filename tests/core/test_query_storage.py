from datetime import UTC, datetime
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.shared.dto import Pagination
from app.shared.errors import StorageUnavailable
from app.shared.http_errors import install_error_handlers
from app.shared.ports import StoragePort
from app.shared.query import pagination
from app.shared.storage_disabled import DisabledStorage


@pytest.mark.parametrize(
    "query",
    [
        "page=1&page=2",
        "other=1",
        "page=true",
        "page=-1",
        "page=0",
        "page=500&page_size=50",
        "page=999999",
    ],
)
def test_query_invalid(query):
    app = FastAPI()
    install_error_handlers(app)

    @app.get("/")
    def route(params: Annotated[Pagination, Depends(pagination)]):
        return params

    with TestClient(app) as client:
        assert client.get("/?" + query).status_code == 422
        assert client.get("/?page=2").json() == {"page": 2, "page_size": 20}


def test_disabled_storage_all_operations_fail():
    storage: StoragePort = DisabledStorage()
    operations = [
        lambda: storage.head("bucket", "key"),
        lambda: storage.read_stream("bucket", "key"),
        lambda: storage.delete("bucket", "key"),
        lambda: storage.copy("bucket", "key", "other", "new", "etag"),
        lambda: storage.presign_post("bucket", "key", "image/png", 1, datetime.now(UTC)),
    ]
    for operation in operations:
        with pytest.raises(StorageUnavailable):
            operation()
