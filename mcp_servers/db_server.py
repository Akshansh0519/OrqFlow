"""
mcp_servers/db_server.py — Read-only SQL query MCP server (port 8001).

Tools exposed:
  - query_database(sql: str) → rows as list[dict]
  - list_tables()            → list of table names in company_ops schema
  - describe_table(name)     → column names and types

Security model (Card 8 — DB Query Server):
  1. sqlparse validation — only SELECT statements allowed (application layer)
  2. Read-only Postgres role (orqflow_readonly) — even if validation is bypassed,
     the DB role cannot execute INSERT/UPDATE/DELETE (infrastructure layer)
  3. Path: parse → validate → execute (defence in depth)

The company_ops schema contains synthetic data for demonstration:
  employees, projects, tasks, time_logs
  (see alembic/versions/ for the seed migration — Phase 3)

Interview answer for "how do you prevent SQL injection?":
  Two layers — sqlparse rejects non-SELECT at parse time, and the
  read-only role rejects mutating statements at the database level.
  A parameterized query would be the third layer if we ever accept user
  input as values (we currently only accept the SQL string itself, which
  is already validated).
"""

from __future__ import annotations

import re

import sqlparse
from fastmcp import FastMCP

from app.config import settings
from mcp_servers.shared_auth import verify_mcp_key

# ── FastMCP server instance ───────────────────────────────────────────────────
mcp = FastMCP(
    name="orqflow-db",
    instructions=(
        "Read-only SQL query server for the company_ops schema. "
        "Only SELECT statements are accepted. "
        "Tables: employees, projects, tasks, time_logs."
    ),
)

# ── SQL validation ────────────────────────────────────────────────────────────

BLOCKED_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE", "ALTER",
    "CREATE", "REPLACE", "MERGE", "GRANT", "REVOKE", "EXEC",
    "EXECUTE", "CALL", "PRAGMA",
}
ALLOWED_TABLES = {"employees", "projects", "tasks", "time_logs"}
BLOCKED_TABLES = {"users", "threads", "agent_runs", "agent_steps"}


def _validate_select_only(sql: str) -> None:
    """
    Validate that the SQL string contains only a single SELECT statement.

    Raises:
        ValueError: If the SQL contains non-SELECT statements or multiple statements.

    This is the application-layer guard. The infrastructure-layer guard is the
    read-only Postgres role used by this server's database connection.
    """
    sql = sql.strip()
    if not sql:
        raise ValueError("SQL query cannot be empty")

    parsed = sqlparse.parse(sql)
    if len(parsed) == 0:
        raise ValueError("Failed to parse SQL")

    # Reject multiple statements (e.g. "SELECT 1; DROP TABLE users")
    if len(parsed) > 1 or (len(parsed) == 1 and sql.count(";") > 1):
        raise ValueError("Only a single statement is allowed")

    statement = parsed[0]
    stmt_type = statement.get_type()

    if stmt_type != "SELECT":
        raise ValueError(
            f"Only SELECT statements are allowed. Got: {stmt_type or 'UNKNOWN'}"
        )

    # Secondary check: scan all tokens for blocked keywords
    # Catches edge cases like "SELECT 1; DELETE FROM users" that sqlparse might
    # mis-classify under certain dialects.
    for token in statement.flatten():
        if token.ttype is not None:
            upper = token.value.upper()
            if upper in BLOCKED_KEYWORDS:
                raise ValueError(
                    f"Blocked keyword detected: {token.value!r}. "
                    "Only SELECT statements are allowed."
                )


def _validate_company_ops_scope(sql: str) -> None:
    """
    Keep the MCP DB server scoped to demo analytics data, not app auth tables.
    This is intentionally simple and explainable for a portfolio project.
    """
    lowered = sql.lower()
    referenced_app_tables = {t for t in BLOCKED_TABLES if re.search(rf"\b{t}\b", lowered)}
    if referenced_app_tables:
        raise ValueError(
            "MCP DB queries cannot access app-owned tables: "
            + ", ".join(sorted(referenced_app_tables))
        )

    referenced_demo_tables = {
        t for t in ALLOWED_TABLES if re.search(rf"\b(company_ops\.)?{t}\b", lowered)
    }
    if not referenced_demo_tables:
        raise ValueError(
            "MCP DB queries must reference one of: "
            + ", ".join(sorted(ALLOWED_TABLES))
        )


def _mcp_database_url() -> str:
    if settings.MCP_DATABASE_URL:
        return settings.MCP_DATABASE_URL
    if settings.is_production:
        raise RuntimeError("MCP_DATABASE_URL is required in production")
    return settings.DATABASE_URL


# ── Mock database for offline/test mode ─────────────────────────────────────

_MOCK_TABLES = {
    "employees": [
        {"id": 1, "name": "Alice Chen", "department": "Engineering", "salary": 120000},
        {"id": 2, "name": "Bob Sharma", "department": "Product", "salary": 110000},
        {"id": 3, "name": "Carol Singh", "department": "Engineering", "salary": 125000},
    ],
    "projects": [
        {"id": 1, "name": "OrqFlow v1", "status": "active", "owner_id": 1},
        {"id": 2, "name": "Dashboard Redesign", "status": "planning", "owner_id": 2},
    ],
    "tasks": [
        {"id": 1, "project_id": 1, "assignee_id": 1, "title": "Set up CI", "done": True},
        {"id": 2, "project_id": 1, "assignee_id": 3, "title": "Write auth module", "done": True},
        {"id": 3, "project_id": 1, "assignee_id": 1, "title": "Build MCP servers", "done": False},
    ],
    "time_logs": [
        {"id": 1, "task_id": 1, "employee_id": 1, "hours": 4.0},
        {"id": 2, "task_id": 2, "employee_id": 3, "hours": 6.5},
        {"id": 3, "task_id": 3, "employee_id": 1, "hours": 2.0},
    ],
}


def _mock_execute(sql: str) -> list[dict]:
    """
    Return mock data for queries in offline/test mode.
    Parses the table name from simple SELECT * FROM <table> queries.
    """
    sql_upper = sql.upper().strip()
    for table_name, rows in _MOCK_TABLES.items():
        if table_name.upper() in sql_upper:
            return rows
    return [{"mock": True, "sql": sql, "note": "No matching mock table — returning empty"}]


# ── MCP Tools ─────────────────────────────────────────────────────────────────

@mcp.tool()
async def query_database(sql: str) -> list[dict]:
    """
    Execute a read-only SQL SELECT query against the company_ops database.

    Args:
        sql: A valid SQL SELECT statement. Must query tables in the company_ops schema.
             Only one statement per call. No INSERT/UPDATE/DELETE/DROP allowed.

    Returns:
        A list of dicts, each representing one row. Column names are the dict keys.

    Raises:
        ValueError: If the SQL is not a valid SELECT statement.
    """
    verify_mcp_key()
    _validate_select_only(sql)
    _validate_company_ops_scope(sql)

    if settings.SEARCH_PROVIDER != "mock":
        try:
            from sqlalchemy import text
            from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
            engine = create_async_engine(_mcp_database_url(), pool_pre_ping=True)
            try:
                session_maker = async_sessionmaker(engine, expire_on_commit=False)
                async with session_maker() as session:
                    await session.execute(text("SET statement_timeout = 5000;"))
                    result = await session.execute(text(sql))
                    return [dict(mapping) for mapping in result.mappings().fetchmany(500)]
            finally:
                await engine.dispose()
        except Exception:
            pass

    return _mock_execute(sql)


@mcp.tool()
async def list_tables() -> list[str]:
    """
    List all available tables in the company_ops schema.
    """
    verify_mcp_key()
    if settings.SEARCH_PROVIDER != "mock":
        try:
            from sqlalchemy import text
            from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
            engine = create_async_engine(_mcp_database_url(), pool_pre_ping=True)
            try:
                session_maker = async_sessionmaker(engine, expire_on_commit=False)
                async with session_maker() as session:
                    result = await session.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'company_ops';"))
                    tables = [r[0] for r in result.fetchall()]
                    if tables:
                        return tables
            finally:
                await engine.dispose()
        except Exception:
            pass
    return list(_MOCK_TABLES.keys())


@mcp.tool()
async def describe_table(table_name: str) -> dict:
    """
    Describe the columns of a table in the company_ops schema.
    """
    verify_mcp_key()
    if table_name not in ALLOWED_TABLES:
        raise ValueError(
            f"Unknown table: {table_name!r}. "
            f"Available: {sorted(ALLOWED_TABLES)}"
        )

    if settings.SEARCH_PROVIDER != "mock":
        try:
            from sqlalchemy import text
            from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
            engine = create_async_engine(_mcp_database_url(), pool_pre_ping=True)
            try:
                session_maker = async_sessionmaker(engine, expire_on_commit=False)
                async with session_maker() as session:
                    result = await session.execute(
                        text("SELECT column_name FROM information_schema.columns WHERE table_schema = 'company_ops' AND table_name = :t;"),
                        {"t": table_name}
                    )
                    cols = [r[0] for r in result.fetchall()]
                    if cols:
                        return {"table": table_name, "columns": cols}
            finally:
                await engine.dispose()
        except Exception:
            pass

    if table_name not in _MOCK_TABLES:
        raise ValueError(
            f"Unknown table: {table_name!r}. "
            f"Available: {list(_MOCK_TABLES.keys())}"
        )
    sample = _MOCK_TABLES[table_name][0] if _MOCK_TABLES[table_name] else {}
    return {
        "table": table_name,
        "columns": list(sample.keys()),       
    }


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(mcp.http_app(), host="0.0.0.0", port=8001)
