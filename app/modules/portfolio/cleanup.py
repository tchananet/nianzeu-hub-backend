import argparse
import json
import logging
import sys

from app.core.config import Settings
from app.core.database import build_engine, session_factory
from app.modules.portfolio.context import build_context
from app.modules.portfolio.maintenance import CleanupService
from app.modules.portfolio.minio_client import build_client
from app.modules.portfolio.minio_storage import MinioStorage
from app.modules.portfolio.storage import sweepable

logger = logging.getLogger("app.portfolio.cleanup")


def build_service() -> CleanupService:
    settings = Settings()
    storage = MinioStorage(build_client(settings), settings.storage_public_endpoint)
    engine = build_engine(settings)
    context = build_context(session_factory(engine), storage, settings)
    return CleanupService(context, sweepable(storage))


def main(argv: list[str] | None = None) -> int:
    """`python -m app.modules.portfolio.cleanup --once`; safe to re-run at any time."""
    parser = argparse.ArgumentParser(prog="portfolio-cleanup", add_help=True)
    parser.add_argument("--once", action="store_true", help="run a single idempotent pass")
    options = parser.parse_args(argv)
    if not options.once:
        parser.error("--once is required; no daemon mode is provided")
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    report = build_service().run_once()
    logger.info(json.dumps(report._asdict()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
