"""Private bucket bootstrap and the readiness assertion over them.

Both private buckets must exist and carry no policy. S3 implementations disagree on
what they answer when a policy is absent — and on whether they implement bucket
policies at all — so "absent" is a set of codes rather than one. A policy that really
is present still fails closed, which is the behaviour the contract asks for.
"""

import logging
from time import sleep
from urllib.parse import urlsplit

from minio import Minio
from minio.error import MinioException, S3Error
from urllib3 import PoolManager, Timeout
from urllib3.exceptions import HTTPError

from app.core.config import Settings
from app.shared.errors import DependencyUnavailable

NO_POLICY = frozenset({"NoSuchBucketPolicy", "NotImplemented"})
# Readiness must answer quickly; creating the first bucket on a cold volume is slow.
PROBE_READ_SECONDS = 2
BOOTSTRAP_READ_SECONDS = 30
logger = logging.getLogger("app.buckets")


def storage_client(settings: Settings, read_seconds: int = PROBE_READ_SECONDS) -> Minio:
    endpoint = urlsplit(settings.storage_endpoint)
    return Minio(
        endpoint.netloc,
        access_key=settings.storage_access_key.get_secret_value(),
        secret_key=settings.storage_secret_key.get_secret_value(),
        secure=endpoint.scheme == "https",
        region="us-east-1",
        http_client=PoolManager(
            timeout=Timeout(connect=2, read=read_seconds), retries=False
        ),
    )


def clear_policy(client: Minio, bucket: str) -> None:
    """Leave the bucket with no policy. Nothing to delete is success, not failure."""
    try:
        client.delete_bucket_policy(bucket)
    except S3Error as error:
        if error.code not in NO_POLICY:
            raise


def ensure_bucket(client: Minio, bucket: str, attempts: int, pause: float) -> None:
    """Bootstrap races a storage service that may still be warming up.

    A healthy master does not mean the S3 gateway is answering yet, and the first
    bucket on a cold volume can take longer than one request timeout. Retry instead
    of failing the deployment; a genuine refusal still surfaces on the last attempt.
    """
    for remaining in range(attempts, 0, -1):
        try:
            if not client.bucket_exists(bucket):
                client.make_bucket(bucket)
            return
        except (MinioException, HTTPError, OSError):
            if remaining == 1:
                raise
            logger.warning("Storage not ready for %s, retrying", bucket)
            sleep(pause)


def initialize_buckets(attempts: int = 10, pause: float = 3.0) -> None:
    settings = Settings()
    client = storage_client(settings, BOOTSTRAP_READ_SECONDS)
    for bucket in (settings.quarantine_bucket, settings.validated_bucket):
        ensure_bucket(client, bucket, attempts, pause)
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
