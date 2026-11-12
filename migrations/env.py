import os

from alembic import context
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import make_url

config = context.config


def migrate(connection):
    if connection.dialect.name != "postgresql":
        raise RuntimeError("PostgreSQL is required for migrations")
    context.configure(
        connection=connection,
        target_metadata=None,
        version_table_schema=config.attributes.get("version_table_schema"),
        transactional_ddl=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run():
    supplied = config.attributes.get("connection")
    if supplied is not None:
        migrate(supplied)
        return
    raw = os.environ.get("APP_DATABASE_URL")
    if not raw:
        raise RuntimeError("APP_DATABASE_URL is required for migrations")
    try:
        url = make_url(raw)
    except Exception:
        raise RuntimeError("Invalid PostgreSQL migration URL") from None
    if url.drivername != "postgresql+psycopg" or not url.host or not url.database or url.query:
        raise RuntimeError("PostgreSQL psycopg URL without query options required")
    if context.is_offline_mode():
        raise RuntimeError("Offline migrations are unsupported; use real PostgreSQL")
    engine = create_engine(
        url, poolclass=pool.NullPool, hide_parameters=True,
        connect_args={"connect_timeout": 3, "options": "-c lock_timeout=3000 -c timezone=UTC"},
    )
    try:
        with engine.connect() as connection:
            migrate(connection)
    finally:
        engine.dispose()


run()
