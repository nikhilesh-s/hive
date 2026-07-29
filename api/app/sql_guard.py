"""
Validates and constrains LLM-generated SQL before it ever reaches a database
connection, replacing a substring blocklist (`if "drop" in sql.lower()`)
with real AST-level checks via sqlglot.

This is a second layer of defense, not the only one: the query this
validates should also only ever run through a Postgres role scoped to
SELECT on `western_blot_records` (see db.py), so a bug here can't turn
into a full-database compromise.
"""

import sqlglot
from sqlglot import exp

from .config import settings


class SQLGuardError(ValueError):
    pass


# Only functions the generated SQL is realistically expected to need for
# ILIKE-based text search. Anything not in this list is rejected, which
# blocks pg_sleep(), dblink(), pg_read_file(), etc. by construction rather
# than by trying to enumerate every dangerous function.
ALLOWED_FUNCTIONS = {"lower", "upper", "coalesce", "count"}

# Node types that mean this isn't a plain, single SELECT.
DISALLOWED_NODE_TYPES = (
    exp.Union,
    exp.Except,
    exp.Intersect,
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Alter,
    exp.Create,
    exp.Command,
    exp.Into,
)


def guard_and_limit_sql(raw_sql: str, requested_limit: int) -> str:
    """
    Raises SQLGuardError if raw_sql is anything other than a single SELECT
    against settings.table_name. Otherwise returns the SQL rewritten with a
    server-enforced LIMIT, ignoring whatever (if anything) the LLM put there.
    """
    cleaned = raw_sql.strip().rstrip(";")

    try:
        statements = [s for s in sqlglot.parse(cleaned, read="postgres") if s is not None]
    except Exception as e:
        raise SQLGuardError(f"Could not parse generated SQL: {e}") from e

    if len(statements) != 1:
        raise SQLGuardError("Exactly one SQL statement is required")

    stmt = statements[0]
    if not isinstance(stmt, exp.Select):
        raise SQLGuardError("Only SELECT statements are allowed")

    for node in stmt.walk():
        if isinstance(node, DISALLOWED_NODE_TYPES):
            raise SQLGuardError(f"'{type(node).__name__}' is not allowed in a search query")

    tables = {t.name.lower() for t in stmt.find_all(exp.Table)}
    if not tables:
        raise SQLGuardError("Query must reference a table")
    if tables != {settings.table_name.lower()}:
        raise SQLGuardError(f"Query may only reference {settings.table_name}")

    for func in stmt.find_all(exp.Anonymous):
        name = str(func.this).lower()
        if name not in ALLOWED_FUNCTIONS:
            raise SQLGuardError(f"Function '{name}' is not allowed")

    limit_value = max(1, min(requested_limit, settings.max_search_limit))
    existing_limit_node = stmt.args.get("limit")
    if existing_limit_node is not None:
        try:
            existing_value = int(str(existing_limit_node.expression.this))
            limit_value = min(existing_value, limit_value)
        except (AttributeError, ValueError):
            pass

    stmt.set("limit", exp.Limit(expression=exp.Literal.number(limit_value)))

    return stmt.sql(dialect="postgres")
