from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, MetaData, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import Settings


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(table_name)s_%(column_0_name)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


def build_engine(settings: Settings) -> Engine:
    return create_engine(
        settings.database_url.get_secret_value(),
        pool_size=settings.pool_size,
        max_overflow=settings.max_overflow,
        pool_timeout=settings.pool_timeout,
        pool_pre_ping=True,
        hide_parameters=True,
        connect_args={
            "connect_timeout": 3,
            "options": f"-c statement_timeout={settings.statement_timeout_ms} -c timezone=UTC",
        },
    )


def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False)


@contextmanager
def transaction(factory: sessionmaker[Session]) -> Iterator[Session]:
    with factory.begin() as session:
        yield session


def check_database(engine: Engine) -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
