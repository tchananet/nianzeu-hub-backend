from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from minio.error import MinioException
from sqlalchemy.exc import SQLAlchemyError
from urllib3.exceptions import HTTPError

# Re-exported: docker-compose bootstraps the buckets through app.main.
from app.core.buckets import check_buckets, initialize_buckets, storage_client
from app.core.config import Settings
from app.core.database import build_engine, check_database
from app.core.json_transport import JsonTransport
from app.core.request_context import RequestContext
from app.shared.errors import DependencyUnavailable
from app.shared.http_errors import install_error_handlers
from app.wiring import build_routers

__all__ = ["check_buckets", "create_app", "initialize_buckets", "storage_client"]


def create_app() -> FastAPI:
    # Built here rather than in the lifespan: routing needs the collaborators before
    # the application starts serving. The lifespan only releases the pool.
    settings = Settings()
    engine = build_engine(settings)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            engine.dispose()

    # Not published by accident: the schema names every route. APP_DOCS_ENABLED=true.
    docs = settings.docs_enabled or settings.environment in {"local", "test"}
    application = FastAPI(
        lifespan=lifespan, title="nianzeuhub backend", version="1", redoc_url=None,
        docs_url="/api/v1/docs" if docs else None,
        openapi_url="/api/v1/openapi.json" if docs else None,
    )
    application.state.settings = settings
    application.state.engine = engine
    application.state.storage = storage_client(settings)
    install_error_handlers(application)
    # Added before RequestContext so it ends up inside it: the transport limit is the
    # first control of http.md, but its refusals still need a request id.
    application.add_middleware(JsonTransport)
    application.add_middleware(RequestContext)
    for router in build_routers(settings, engine):
        application.include_router(router)

    @application.get("/health/live")
    def live() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/health/ready")
    def ready() -> dict[str, str]:
        try:
            check_database(application.state.engine)
            check_buckets(application.state.storage, application.state.settings)
        except (SQLAlchemyError, MinioException, HTTPError, OSError):
            raise DependencyUnavailable() from None
        return {"status": "ready"}

    return application
