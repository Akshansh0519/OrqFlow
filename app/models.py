"""
app/models.py — SQLAlchemy ORM models (LOCKED SCHEMA).

This is the app-owned schema. LangGraph manages its own internal tables
(checkpointer, store) separately — do NOT mix them here.

Tables:
  users       → registered accounts
  threads     → one LangGraph thread per row (thread_id == Thread.id)
  agent_runs  → one run per POST /api/threads/{id}/run
  agent_steps → one row per node visit / tool call (observability read model)

No long_term_facts table — facts live ONLY in LangGraph's PostgresStore.
See prep/cards/card-04-postgres-store.md for why.
"""

from __future__ import annotations

import uuid
from datetime import datetime, UTC

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
    )

    threads: Mapped[list[Thread]] = relationship(back_populates="user")


class Thread(Base):
    __tablename__ = "threads"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(
        String(120), nullable=False, default="New conversation"
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
    )

    user: Mapped[User] = relationship(back_populates="threads")
    runs: Mapped[list[AgentRun]] = relationship(back_populates="thread")

    __table_args__ = (Index("ix_threads_user_id", "user_id"),)


class AgentRun(Base):
    """
    One row per POST /api/threads/{id}/run call.

    status:  RUNNING → COMPLETE | FAILED
    total_prompt_tokens / total_completion_tokens: denormalized sums,
      updated incrementally by StepRecorder.record_usage().
      Avoids SUM() aggregation on every dashboard read.
    """

    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("threads.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="RUNNING")
    started_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
    )
    ended_at: Mapped[datetime | None] = mapped_column(nullable=True, default=None)
    total_latency_ms: Mapped[int | None] = mapped_column(nullable=True, default=None)
    total_prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_completion_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    thread: Mapped[Thread] = relationship(back_populates="runs")
    steps: Mapped[list[AgentStep]] = relationship(
        back_populates="run",
        order_by="AgentStep.step_index",
    )

    __table_args__ = (Index("ix_agent_runs_thread_id", "thread_id"),)


class AgentStep(Base):
    """
    One row per node visit or tool call in an agent run.

    This is the observability read model — NOT a checkpoint.
    See prep/cards/card-06-observability-table.md for the design rationale.

    Composite index (run_id, step_index) makes trace queries O(steps in run)
    regardless of total row count.

    payload_preview: truncated to 300 chars — NOT a full audit log.
    """

    __tablename__ = "agent_steps"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False
    )
    step_index: Mapped[int] = mapped_column(Integer, nullable=False)
    node_name: Mapped[str] = mapped_column(String(50), nullable=False)
    # event_type: node_start | node_end | tool_call | tool_result | llm_call
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)
    tool_name: Mapped[str | None] = mapped_column(String(50), nullable=True, default=None)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    completion_tokens: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=None
    )
    # Truncated preview of the input/output payload — 300 chars max
    payload_preview: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
    )

    run: Mapped[AgentRun] = relationship(back_populates="steps")

    __table_args__ = (
        # Critical for trace queries: filter on run_id, sort by step_index
        Index("ix_agent_steps_run_id_step_index", "run_id", "step_index"),
    )
