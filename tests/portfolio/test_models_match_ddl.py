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


def orm_checks(table: Table) -> dict[str, list[str]]:
    checks = (item for item in table.constraints if isinstance(item, CheckConstraint))
    return {str(item.name): ddl.normalise(str(item.sqltext)) for item in checks}


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


def test_check_constraints_match_the_migration_by_name_and_by_predicate() -> None:
    """Names alone proved nothing (QA O01, D3): the predicate carries the guarantee."""
    for table, filename in TABLES:
        assert orm_checks(table) == ddl.parse(filename).checks, table.name


def test_declared_indexes_match_the_migration() -> None:
    for table, filename in TABLES:
        declared = {
            index.name: [column.name for column in index.columns] for index in table.indexes
        }
        assert declared == ddl.parse(filename).indexes, table.name


def test_the_size_ceiling_of_data_md_is_written_on_items_and_uploads_alike() -> None:
    """data.md only implies the 100 MiB ceiling; M03 writes it on both tables."""
    for table, filename in TABLES:
        assert "104857600" in ddl.parse(filename).checks[f"ck_{table.name}_size"], table.name


def test_a_divergent_bound_or_operator_fails_even_under_the_right_name() -> None:
    """The proof the comparison bites: same names, one predicate off, still caught."""
    table, declared = TABLES[0][0], ddl.parse(TABLES[0][1]).checks
    wrong = {
        # A loosened lower bound and a ceiling ten times too small, as QA O01 D3 names.
        "ck_portfolio_items_size": (
            "size_bytes IS NULL OR (size_bytes >= 0 AND size_bytes <= 10485760)"
        ),
        "ck_portfolio_items_type": "type IN ('image', 'pdf', 'video', 'audio')",
        "ck_portfolio_items_published_at": "(state = 'published') != (published_at IS NOT NULL)",
        "ck_portfolio_items_sha256": "sha256 IS NULL OR sha256 ~ '^[0-9a-f]{32}$'",
    }
    for name, predicate in wrong.items():
        mutated = orm_checks(table) | {name: ddl.normalise(predicate)}
        assert set(mutated) == set(declared), name
        assert mutated != declared, name


def test_layout_alone_is_never_reported_as_drift() -> None:
    """The flip side: reformatting the same predicate must keep the suite green."""
    assert ddl.normalise("size_bytes>=1\n   AND size_bytes <= 104857600") == ddl.normalise(
        "(SIZE_BYTES >= 1 and size_bytes <=   104857600)"
    )
