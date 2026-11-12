from contextlib import contextmanager

from sqlalchemy import event, select, text
from sqlalchemy.engine import Engine

from app.modules.discovery.filters import conditions
from app.modules.discovery.schemas import SearchQuery
from app.modules.profiles.models import Profile


def page_statement(**kwargs):
    """Same shape as repository.page_matches, rebuilt here so EXPLAIN can read it."""
    query = SearchQuery.model_validate(kwargs)
    return (
        select(Profile.id)
        .where(*conditions(query))
        .order_by(Profile.updated_at.desc(), Profile.id.asc())
        .offset(query.offset)
        .limit(query.page_size)
    )


def plan_of(db, statement, seqscan=False):
    """EXPLAIN with sequential scans penalised: proves an index path exists and is usable.

    Compiled against the live connection dialect so escapes and the driver paramstyle
    match what the application really sends; expanding IN lists are rendered inline.
    """
    db.execute(text(f"SET LOCAL enable_seqscan = {'on' if seqscan else 'off'}"))
    connection = db.connection()
    compiled = statement.compile(
        dialect=connection.dialect, compile_kwargs={"render_postcompile": True})
    rows = connection.exec_driver_sql(f"EXPLAIN {compiled}", dict(compiled.params))
    return "\n".join(row[0] for row in rows)


def index_definitions(db, table):
    return list(db.execute(
        text("SELECT indexdef FROM pg_indexes WHERE schemaname = 'public' AND tablename = :name"),
        {"name": table},
    ).scalars())


@contextmanager
def counted_statements():
    recorded: list[str] = []

    def record(connection, cursor, statement, parameters, context, executemany):
        recorded.append(statement)

    event.listen(Engine, "before_cursor_execute", record)
    try:
        yield recorded
    finally:
        event.remove(Engine, "before_cursor_execute", record)
