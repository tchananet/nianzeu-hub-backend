from urllib.parse import urlsplit

from minio import Minio
from urllib3 import PoolManager, Timeout

from app.core.config import Settings

READ_TIMEOUT_SECONDS = 120


def build_client(settings: Settings) -> Minio:
    """Internal endpoint for server-side calls; presigned POST forms carry the public URL."""
    endpoint = urlsplit(settings.storage_endpoint)
    if not endpoint.netloc:
        raise ValueError("Storage endpoint without host")
    return Minio(
        endpoint.netloc,
        access_key=settings.storage_access_key.get_secret_value(),
        secret_key=settings.storage_secret_key.get_secret_value(),
        secure=endpoint.scheme == "https",
        region="us-east-1",
        http_client=PoolManager(
            timeout=Timeout(connect=2, read=READ_TIMEOUT_SECONDS), retries=False
        ),
    )
