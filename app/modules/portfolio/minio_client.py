from urllib.parse import urlsplit

from minio import Minio

from app.core.config import Settings


def build_client(settings: Settings) -> Minio:
    """Internal endpoint for server-side calls; presigned POST forms carry the public URL."""
    url = urlsplit(settings.storage_endpoint)
    if not url.hostname:
        raise ValueError("Storage endpoint without host")
    port = f":{url.port}" if url.port else ""
    return Minio(
        f"{url.hostname}{port}",
        access_key=settings.storage_access_key.get_secret_value(),
        secret_key=settings.storage_secret_key.get_secret_value(),
        secure=url.scheme == "https",
    )
