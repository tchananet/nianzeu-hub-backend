"""Parses M03's hand-written DDL so the ORM tables can be compared against it."""

import re
from dataclasses import dataclass, field
from pathlib import Path

SQL_DIR = Path(__file__).resolve().parents[2] / "migrations" / "versions"
FLAGS = ("NOT NULL", "PRIMARY KEY", "UNIQUE")
COLUMN_START = re.compile(r"^[a-z_][a-z0-9_]*\s")
# A quoted literal, a word, a number, a grouping character or a comparison operator.
TOKEN = re.compile(r"'[^']*'|[A-Za-z_][A-Za-z0-9_]*|\d+|[(),]|[<>!~]=?|=|\S")


@dataclass
class Column:
    type_sql: str
    nullable: bool
    unique: bool
    primary: bool
    references: str | None = None


@dataclass
class Table:
    name: str
    columns: dict[str, Column] = field(default_factory=dict)
    checks: dict[str, list[str]] = field(default_factory=dict)
    indexes: dict[str, list[str]] = field(default_factory=dict)


def normalise(predicate: str) -> list[str]:
    """Canonical tokens: layout and a wrapping parenthesis pair fold away, bounds never."""
    # Keywords and identifiers upper-case; a quoted literal keeps its exact bytes.
    tokens = [t if t.startswith("'") else t.upper() for t in TOKEN.findall(predicate)]
    while tokens[:1] == ["("] and tokens[-1:] == [")"]:
        depth = 0
        for index, token in enumerate(tokens):
            depth += (token == "(") - (token == ")")
            if depth == 0 and index < len(tokens) - 1:
                return tokens
        tokens = tokens[1:-1]
    return tokens


def body_of(sql: str, start: int) -> str:
    depth = 0
    for index in range(start, len(sql)):
        depth += (sql[index] == "(") - (sql[index] == ")")
        if depth == 0:
            return sql[start + 1 : index]
    raise ValueError("Unbalanced CREATE TABLE body")


def split_top_level(body: str) -> list[str]:
    parts, depth = [""], 0
    for char in body:
        if char == "," and depth == 0:
            parts.append("")
            continue
        depth += (char == "(") - (char == ")")
        parts[-1] += char
    return [part.strip() for part in parts if part.strip()]


def read_column(table: Table, part: str) -> None:
    name, remainder = part.split(maxsplit=1)
    type_sql = re.sub(r"\s*(CHECK\s*\(.*\)|REFERENCES\s.*)$", "", remainder, flags=re.DOTALL)
    for flag in FLAGS:
        type_sql = type_sql.replace(flag, "")
    reference = re.search(r"REFERENCES (\w+)\((\w+)\) ON DELETE (\w+)", remainder)
    table.columns[name] = Column(
        type_sql=" ".join(type_sql.split()).upper(),
        nullable="NOT NULL" not in remainder and "PRIMARY KEY" not in remainder,
        unique="UNIQUE" in remainder,
        primary="PRIMARY KEY" in remainder,
        references=None if reference is None else ".".join(reference.groups()).upper(),
    )
    # PostgreSQL names an inline column check <table>_<column>_check.
    inline = re.search(r"CHECK\s*\((.*)\)\s*$", remainder, flags=re.DOTALL)
    if inline is not None:
        table.checks[f"{table.name}_{name}_check"] = normalise(inline.group(1))


def parse(filename: str) -> Table:
    sql = (SQL_DIR / filename).read_text(encoding="utf-8")
    match = re.search(r"CREATE TABLE (\w+)\s*\(", sql)
    if match is None:
        raise ValueError(f"No CREATE TABLE in {filename}")
    table = Table(name=match.group(1))
    for part in split_top_level(body_of(sql, match.end() - 1)):
        named = re.match(r"CONSTRAINT (\w+) CHECK\s*\((.*)\)$", part, flags=re.DOTALL)
        if named is not None:
            table.checks[named.group(1)] = normalise(named.group(2))
        elif COLUMN_START.match(part):
            read_column(table, part)
        else:
            raise ValueError(f"Unsupported table element: {part[:40]}")
    for name, columns in re.findall(r"CREATE INDEX (\w+)\s+ON \w+\s*\(([^)]*)\)", sql):
        table.indexes[name] = [column.strip() for column in columns.split(",")]
    return table
