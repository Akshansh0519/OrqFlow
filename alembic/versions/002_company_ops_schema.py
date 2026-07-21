"""Company ops schema and seed data for MCP DB query server.

Revision ID: 002
Revises: 001
Create Date: 2026-06-27
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create company_ops schema
    op.execute("CREATE SCHEMA IF NOT EXISTS company_ops;")

    # Create read-only role if not exists and grant privileges
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'orqflow_readonly') THEN
            CREATE ROLE orqflow_readonly WITH LOGIN PASSWORD 'readonly_pass';
        END IF;
    END
    $$;
    """)
    op.execute("GRANT USAGE ON SCHEMA company_ops TO orqflow_readonly;")

    # Create employees table
    employees_table = op.create_table(
        "employees",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("department", sa.String(length=50), nullable=False),
        sa.Column("salary", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema="company_ops",
    )

    # Create projects table
    projects_table = op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["company_ops.employees.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="company_ops",
    )

    # Create tasks table
    tasks_table = op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("assignee_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("done", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["company_ops.projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assignee_id"], ["company_ops.employees.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="company_ops",
    )

    # Create time_logs table
    time_logs_table = op.create_table(
        "time_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("hours", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["company_ops.tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["employee_id"], ["company_ops.employees.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="company_ops",
    )

    # Grant select permissions
    op.execute("GRANT SELECT ON ALL TABLES IN SCHEMA company_ops TO orqflow_readonly;")
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA company_ops GRANT SELECT ON TABLES TO orqflow_readonly;"
    )

    # Seed data
    op.bulk_insert(
        employees_table,
        [
            {"id": 1, "name": "Alice Chen", "department": "Engineering", "salary": 120000},
            {"id": 2, "name": "Bob Sharma", "department": "Product", "salary": 110000},
            {"id": 3, "name": "Carol Singh", "department": "Engineering", "salary": 125000},
        ],
    )

    op.bulk_insert(
        projects_table,
        [
            {"id": 1, "name": "OrqFlow v1", "status": "active", "owner_id": 1},
            {"id": 2, "name": "Dashboard Redesign", "status": "planning", "owner_id": 2},
        ],
    )

    op.bulk_insert(
        tasks_table,
        [
            {"id": 1, "project_id": 1, "assignee_id": 1, "title": "Set up CI", "done": True},
            {
                "id": 2,
                "project_id": 1,
                "assignee_id": 3,
                "title": "Write auth module",
                "done": True,
            },
            {
                "id": 3,
                "project_id": 1,
                "assignee_id": 1,
                "title": "Build MCP servers",
                "done": False,
            },
        ],
    )

    op.bulk_insert(
        time_logs_table,
        [
            {"id": 1, "task_id": 1, "employee_id": 1, "hours": 4.0},
            {"id": 2, "task_id": 2, "employee_id": 3, "hours": 6.5},
            {"id": 3, "task_id": 3, "employee_id": 1, "hours": 2.0},
        ],
    )


def downgrade() -> None:
    op.drop_table("time_logs", schema="company_ops")
    op.drop_table("tasks", schema="company_ops")
    op.drop_table("projects", schema="company_ops")
    op.drop_table("employees", schema="company_ops")
    op.execute("REVOKE ALL ON SCHEMA company_ops FROM orqflow_readonly;")
    op.execute("DROP ROLE IF EXISTS orqflow_readonly;")
    op.execute("DROP SCHEMA IF EXISTS company_ops CASCADE;")
