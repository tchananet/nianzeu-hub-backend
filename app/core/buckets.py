"""Private bucket bootstrap and the readiness assertion over them.

Both private buckets must exist and carry no policy. S3 implementations disagree on
what they answer when a policy is absent — and on whether they implement bucket
policies at all — so "absent" is a set of codes rather than one. A policy that really
is present still fails closed, which is the behaviour the contract asks for.
"""

from urllib.parse import urlsplit

from minio import Minio
from minio.error import S3Error
from urllib3 import PoolManager, Timeout

from app.core.config import Settings
from app.shared.errors import DependencyUnavailable

NO_POLICY = frozenset({"NoSuchBucketPolicy", "NotImplemented"})


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


def clear_policy(client: Minio, bucket: str) -> None:
    """Leave the bucket with no policy. Nothing to delete is success, not failure."""
    try:
        client.delete_bucket_policy(bucket)
    except S3Error as error:
        if error.code not in NO_POLICY:
            raise


def initialize_buckets() -> None:
    settings = Settings()
    client = storage_client(settings)
    for bucket in (settings.quarantine_bucket, settings.validated_bucket):
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
        clear_policy(client, bucket)


def check_buckets(client: Minio, settings: Settings) -> None:
    for bucket in (settings.quarantine_bucket, settings.validated_bucket):
        if not client.bucket_exists(bucket):
            raise DependencyUnavailable()
        try:
            client.get_bucket_policy(bucket)
        except S3Error as error:
            if error.code not in NO_POLICY:
                raise
        else:
            # Fail closed: bootstrap never installs an anonymous access policy.
            raise DependencyUnavailable()
