"""Parses M03's hand-written DDL so the ORM tables can be compared against it."""

import re
from dataclasses import dataclass, field
from pathlib import Path

SQL_DIR = Path(__file__).resolve().parents[2] / "migrations" / "versions"
FLAGS = ("NOT NULL", "PRIMARY KEY", "UNIQUE")
COLUMN_START = re.compile(r"^[a-z_][a-z0-9_]*\s")


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
    checks: set[str] = field(default_factory=set)
    indexes: dict[str, list[str]] = field(default_factory=dict)


def body_of(sql: str, start: int) -> str:
    depth, index = 0, start
    while index < len(sql):
        if sql[index] == "(":
            depth += 1
        elif sql[index] == ")":
            depth -= 1
            if depth == 0:
                return sql[start + 1 : index]
        index += 1
    raise ValueError("Unbalanced CREATE TABLE body")


def split_top_level(body: str) -> list[str]:
    parts, depth, current = [], 0, ""
    for char in body:
        if char == "," and depth == 0:
            parts.append(current.strip())
            current = ""
            continue
        depth += (char == "(") - (char == ")")
        current += char
    parts.append(current.strip())
    return [part for part in parts if part]


def read_column(table: Table, part: str) -> None:
    name, remainder = part.split(maxsplit=1)
    without_check = re.sub(r"\s*CHECK\s*\(.*\)\s*$", "", remainder, flags=re.DOTALL)
    without_ref = re.sub(r"\s*REFERENCES\s.*$", "", without_check, flags=re.DOTALL)
    type_sql = without_ref
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
    if "CHECK" in remainder:
        # PostgreSQL names an inline column check <table>_<column>_check.
        table.checks.add(f"{table.name}_{name}_check")


def parse(filename: str) -> Table:
    sql = (SQL_DIR / filename).read_text(encoding="utf-8")
    match = re.search(r"CREATE TABLE (\w+)\s*\(", sql)
    if match is None:
        raise ValueError(f"No CREATE TABLE in {filename}")
    table = Table(name=match.group(1))
    for part in split_top_level(body_of(sql, match.end() - 1)):
        named = re.match(r"CONSTRAINT (\w+) CHECK", part, flags=re.DOTALL)
        if named is not None:
            table.checks.add(named.group(1))
        elif COLUMN_START.match(part):
            read_column(table, part)
        else:
            raise ValueError(f"Unsupported table element: {part[:40]}")
    for name, columns in re.findall(r"CREATE INDEX (\w+)\s+ON \w+\s*\(([^)]*)\)", sql):
        table.indexes[name] = [column.strip() for column in columns.split(",")]
    return table
