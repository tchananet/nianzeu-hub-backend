"""The ORM declaration is QA's mirror of M03: any drift from the real DDL is a defect."""

from sqlalchemy import CheckConstraint, Column, Table
from sqlalchemy.dialects import postgresql

from app.modules.portfolio.models import PortfolioItem, PortfolioUpload
from app.modules.profiles.models import Profile
from tests.portfolio import ddl

DIALECT = postgresql.dialect()
ALIASES = {"TIMESTAMPTZ": "TIMESTAMP WITH TIME ZONE"}
TABLES = (
    (PortfolioItem.__table__, "0003_portfolio_search_items.sql"),
    (PortfolioUpload.__table__, "0003_portfolio_search_uploads.sql"),
)
# Importing the parent table resolves the foreign-key column types in shared metadata.
assert Profile.__tablename__ == "talent_profiles"


def rendered(column: Column[object]) -> str:
    return str(column.type.compile(DIALECT)).upper()


def cascade_of(column: Column[object]) -> str | None:
    for key in column.foreign_keys:
        return f"{key.column.table.name}.{key.column.name}.{key.ondelete}".upper()
    return None


def orm_checks(table: Table) -> set[str]:
    return {str(item.name) for item in table.constraints if isinstance(item, CheckConstraint)}


def test_every_ddl_column_exists_with_the_same_type_nullability_and_cascade() -> None:
    for table, filename in TABLES:
        source = ddl.parse(filename)
        assert table.name == source.name
        assert set(table.columns.keys()) == set(source.columns.keys())
        for name, expected in source.columns.items():
            column = table.columns[name]
            assert rendered(column) == ALIASES.get(expected.type_sql, expected.type_sql), name
            assert column.nullable is expected.nullable, name
            assert bool(column.unique) is expected.unique, name
            assert column.primary_key is expected.primary, name
            assert cascade_of(column) == expected.references, name


def test_check_constraint_names_match_the_migration_exactly() -> None:
    """Names matter: alembic autogenerate and QA both compare constraints by name."""
    for table, filename in TABLES:
        assert orm_checks(table) == ddl.parse(filename).checks, table.name


def test_declared_indexes_match_the_migration() -> None:
    for table, filename in TABLES:
        declared = {
            index.name: [column.name for column in index.columns] for index in table.indexes
        }
        assert declared == ddl.parse(filename).indexes, table.name


def test_size_ceilings_are_expressed_on_both_tables() -> None:
    """data.md only implies the 100 MiB ceiling; M03 writes it on items and uploads alike."""
    for table, _ in TABLES:
        texts = [
            str(item.sqltext) for item in table.constraints if isinstance(item, CheckConstraint)
        ]
        assert any("104857600" in text for text in texts), table.name
