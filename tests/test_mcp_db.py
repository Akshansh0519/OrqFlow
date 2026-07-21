"""
tests/test_mcp_db.py — Phase 2 acceptance tests for the DB MCP server.

Tests the validation logic directly (no running server needed):
  ✅ SELECT is accepted
  ✅ Non-SELECT statements are rejected (INSERT, UPDATE, DELETE, DROP, etc.)
  ✅ SQL injection via stacked statements is rejected
  ✅ Empty query is rejected
  ✅ list_tables() returns expected tables
  ✅ describe_table() returns columns for a known table
  ✅ describe_table() raises for unknown table

Isolation proof test:
  ✅ _validate_select_only can be called without any DB connection
     (proves the validation layer is independent of the infrastructure layer)
"""

from __future__ import annotations

import pytest

# Import validation function and tools directly — no MCP transport needed
from mcp_servers.db_server import (
    _validate_select_only,
    _validate_company_ops_scope,
    list_tables,
    describe_table,
    query_database,
)


# ── SQL Validation ────────────────────────────────────────────────────────────

class TestValidateSelectOnly:

    def test_simple_select_passes(self):
        # Should not raise
        _validate_select_only("SELECT * FROM employees")

    def test_select_with_where_passes(self):
        _validate_select_only("SELECT id, name FROM employees WHERE department = 'Engineering'")

    def test_select_with_join_passes(self):
        _validate_select_only(
            "SELECT e.name, p.name FROM employees e JOIN projects p ON p.owner_id = e.id"
        )

    def test_insert_is_rejected(self):
        with pytest.raises(ValueError, match="Only SELECT"):
            _validate_select_only("INSERT INTO employees (name) VALUES ('hacker')")

    def test_update_is_rejected(self):
        with pytest.raises(ValueError, match="Only SELECT"):
            _validate_select_only("UPDATE employees SET salary = 0")

    def test_delete_is_rejected(self):
        with pytest.raises(ValueError, match="Only SELECT"):
            _validate_select_only("DELETE FROM employees")

    def test_drop_is_rejected(self):
        with pytest.raises(ValueError, match="Only SELECT"):
            _validate_select_only("DROP TABLE employees")

    def test_stacked_statements_rejected(self):
        """Classic SQL injection pattern: valid SELECT followed by DROP."""
        with pytest.raises(ValueError):
            _validate_select_only("SELECT * FROM employees; DROP TABLE employees")

    def test_empty_query_rejected(self):
        with pytest.raises(ValueError, match="empty"):
            _validate_select_only("")

    def test_whitespace_only_rejected(self):
        with pytest.raises(ValueError, match="empty"):
            _validate_select_only("   ")

    def test_truncate_rejected(self):
        with pytest.raises(ValueError, match="Only SELECT"):
            _validate_select_only("TRUNCATE TABLE employees")

    def test_alter_rejected(self):
        with pytest.raises(ValueError, match="Only SELECT"):
            _validate_select_only("ALTER TABLE employees ADD COLUMN hacked BOOLEAN")


class TestCompanyOpsScope:

    def test_company_ops_table_passes(self):
        _validate_company_ops_scope("SELECT * FROM employees")

    def test_app_user_table_rejected(self):
        with pytest.raises(ValueError, match="app-owned"):
            _validate_company_ops_scope("SELECT email, password_hash FROM users")

    def test_query_without_demo_table_rejected(self):
        with pytest.raises(ValueError, match="must reference"):
            _validate_company_ops_scope("SELECT 1")


# ── list_tables ───────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_list_tables_returns_all_tables():
    tables = await list_tables()
    assert isinstance(tables, list)
    assert "employees" in tables
    assert "projects" in tables
    assert "tasks" in tables
    assert "time_logs" in tables


@pytest.mark.anyio
async def test_list_tables_returns_strings():
    tables = await list_tables()
    assert all(isinstance(t, str) for t in tables)


# ── describe_table ────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_describe_employees_table():
    result = await describe_table("employees")
    assert result["table"] == "employees"
    assert "id" in result["columns"]
    assert "name" in result["columns"]


@pytest.mark.anyio
async def test_describe_unknown_table_raises():
    with pytest.raises(ValueError, match="Unknown table"):
        await describe_table("nonexistent_table")


@pytest.mark.anyio
async def test_describe_all_known_tables():
    for table in ["employees", "projects", "tasks", "time_logs"]:
        result = await describe_table(table)
        assert result["table"] == table
        assert len(result["columns"]) > 0


# ── query_database (mock mode) ────────────────────────────────────────────────

@pytest.mark.anyio
async def test_query_employees_returns_rows():
    rows = await query_database("SELECT * FROM employees")
    assert isinstance(rows, list)
    assert len(rows) > 0
    assert "name" in rows[0]


@pytest.mark.anyio
async def test_query_rejects_insert_before_execution():
    """Validation must fire before any DB call is attempted."""
    with pytest.raises(ValueError, match="Only SELECT"):
        await query_database("INSERT INTO employees (name) VALUES ('bad actor')")


@pytest.mark.anyio
async def test_query_rejects_stacked_injection():
    with pytest.raises(ValueError):
        await query_database("SELECT 1; DROP TABLE employees")
