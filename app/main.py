from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

from fastapi import FastAPI
from minio import Minio
from minio.error import MinioException, S3Error
from sqlalchemy.exc import SQLAlchemyError
from urllib3 import PoolManager, Timeout
from urllib3.exceptions import HTTPError

from app.core.config import Settings
from app.core.database import build_engine, check_database
from app.core.request_context import RequestContext
from app.shared.errors import DependencyUnavailable
from app.shared.http_errors import install_error_handlers
from app.wiring import build_routers


def storage_client(settings: Settings) -> Minio:
    endpoint = urlsplit(settings.storage_endpoint)
    return Minio(
        endpoint.netloc,
        access_key=settings.storage_access_key.get_secret_value(),
        secret_key=settings.storage_secret_key.get_secret_value(),
        secure=endpoint.scheme == "https",
        region="us-east-1",
        http_client=PoolManager(timeout=Timeout(connect=2, read=2), retries=False),
    )


def initialize_buckets() -> None:
    settings = Settings()
    client = storage_client(settings)
    for bucket in (settings.quarantine_bucket, settings.validated_bucket):
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
        client.delete_bucket_policy(bucket)


def check_buckets(client: Minio, settings: Settings) -> None:
    for bucket in (settings.quarantine_bucket, settings.validated_bucket):
        if not client.bucket_exists(bucket):
            raise DependencyUnavailable()
        try:
            client.get_bucket_policy(bucket)
        except S3Error as error:
            if error.code != "NoSuchBucketPolicy":
                raise
        else:
            # Fail closed: bootstrap never installs an anonymous access policy.
            raise DependencyUnavailable()


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

    application = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    application.state.settings = settings
    application.state.engine = engine
    application.state.storage = storage_client(settings)
    install_error_handlers(application)
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
