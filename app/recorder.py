"""
app/recorder.py — StepRecorder: per-run observability context manager.

Every node entry/exit and tool call is timed and written asynchronously
to the agent_steps table. This is the observability read model (Card 6).

Design decisions:
  - StepRecorder owns its own DB session (not the FastAPI request session)
    so it can write from inside graph nodes without threading a FastAPI
    dependency through LangGraph's config dict.
  - Writes are fire-and-forget (await inside timed()) — they do NOT block
    the graph from continuing. A failed write is logged, not re-raised.
  - Recorder is OPTIONAL in all node code. Nodes check `if recorder:`
    before using it, so tests without a recorder pass through cleanly.

Bug 4 fix: Added _session_healthy flag. When the SQLAlchemy asyncpg session
  enters an aborted transaction state (e.g., after a connection timeout during
  an LLM rate-limit delay), the flag is set to False. On the next _insert()
  call, a fresh session is created from the factory so subsequent writes succeed.
  This prevents the "Can't reconnect until invalid transaction is rolled back"
  cascade that caused 10-20 failures per run after a single DB hiccup.

Usage in an agent_router run:
    async with StepRecorder.for_run(thread_id, run_id) as recorder:
        config = {"configurable": {"step_recorder": recorder, ...}}
        async for chunk in graph.astream(state, config=config):
            ...

Usage inside a graph node:
    recorder = config.get("configurable", {}).get("step_recorder")
    if recorder:
        async with recorder.timed("supervisor", "llm_call"):
            result = await llm.ainvoke(...)
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()


class StepRecorder:
    """
    Context manager + observability sink for one agent run.

    Thread safety: one StepRecorder per run, never shared.
    """

    def __init__(
        self,
        run_id: uuid.UUID,
        thread_id: str,
        session: AsyncSession | None,
    ) -> None:
        self.run_id = run_id
        self.thread_id = thread_id
        self._session = session
        self._lock = asyncio.Lock()
        self._step_index = 0
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self._status_override: str | None = None
        # Bug 4 fix: track session health to auto-recreate on poison
        self._session_healthy = True

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    @asynccontextmanager
    async def for_run(
        cls,
        thread_id: str,
        run_id: uuid.UUID,
        session: AsyncSession | None = None,
    ) -> AsyncGenerator[StepRecorder, None]:
        """
        Async context manager that creates a recorder and commits/closes
        the session when the run ends.
        """
        from app.database import get_async_session

        created_session = False
        if session is None:
            session = get_async_session()()
            created_session = True

        recorder = cls(run_id=run_id, thread_id=thread_id, session=session)
        start_time = time.monotonic()
        status = "COMPLETE"
        try:
            yield recorder
        except Exception:
            status = "FAILED"
            raise
        finally:
            if session:
                async with recorder._lock:
                    try:
                        elapsed_ms = int((time.monotonic() - start_time) * 1000)
                        final_status = recorder._status_override or status
                        # Bug 4 fix: use current session (may have been replaced)
                        active_session = recorder._session
                        if active_session and recorder._session_healthy:
                            await active_session.execute(
                                text("""
                                UPDATE agent_runs
                                SET status = :status,
                                    ended_at = :now,
                                    total_latency_ms = :latency,
                                    total_prompt_tokens = :prompt_tokens,
                                    total_completion_tokens = :completion_tokens
                                WHERE id = :run_id
                                """),
                                {
                                    "status": final_status,
                                    "now": datetime.now(UTC).replace(tzinfo=None),
                                    "latency": elapsed_ms,
                                    "prompt_tokens": recorder.total_prompt_tokens,
                                    "completion_tokens": recorder.total_completion_tokens,
                                    "run_id": run_id,
                                },
                            )
                            await active_session.commit()
                    except Exception as exc:
                        try:
                            if recorder._session:
                                await recorder._session.rollback()
                        except Exception:
                            pass
                        logger.error("recorder_update_run_failed", exc=str(exc))
                if created_session:
                    try:
                        if recorder._session:
                            await recorder._session.close()
                    except Exception:
                        pass

    # ── Bug 4: Session health management ─────────────────────────────────────

    async def _reset_session(self) -> None:
        """
        Bug 4 fix: Create a fresh session when the current one is poisoned.
        Called automatically at the start of _insert() when _session_healthy=False.
        """
        from app.database import get_async_session

        try:
            if self._session:
                await self._session.close()
        except Exception:
            pass
        try:
            self._session = get_async_session()()
            self._session_healthy = True
            logger.info("recorder_session_recreated", run_id=str(self.run_id))
        except Exception as exc:
            self._session = None
            logger.error("recorder_session_recreate_failed", exc=str(exc))

    # ── Timing context manager ────────────────────────────────────────────────

    @asynccontextmanager
    async def timed(
        self,
        node_name: str,
        event_type: str,
        tool_name: str | None = None,
        payload_preview: str | None = None,
    ) -> AsyncGenerator[StepRecorder, None]:
        """
        Async context manager that records a start row and then, on exit,
        updates it with elapsed latency.

        Usage:
            async with recorder.timed("supervisor", "llm_call"):
                result = await llm.ainvoke(...)
        """
        step_idx = self._step_index
        self._step_index += 1
        start = time.monotonic()

        # Record start event
        await self._insert(
            step_index=step_idx,
            node_name=node_name,
            event_type=f"{event_type}_start",
            tool_name=tool_name,
            latency_ms=None,
            payload_preview=payload_preview,
        )

        try:
            yield self
        finally:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            await self._insert(
                step_index=step_idx,
                node_name=node_name,
                event_type=f"{event_type}_end",
                tool_name=tool_name,
                latency_ms=elapsed_ms,
                payload_preview=None,
            )

    # ── Token accounting ──────────────────────────────────────────────────────

    def record_usage(self, prompt_tokens: int, completion_tokens: int) -> None:
        """Accumulate token counts. Call after each LLM response."""
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens

    def mark_failed(self) -> None:
        """Mark the enclosing run failed even if the SSE error is handled."""
        self._status_override = "FAILED"

    # ── Summary for run_complete SSE event ────────────────────────────────────

    def summary(self) -> dict:
        """Return a summary dict for the run_complete SSE event."""
        return {
            "run_id": str(self.run_id),
            "total_steps": self._step_index,
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
        }

    # ── Internal DB write ─────────────────────────────────────────────────────

    async def _insert(
        self,
        step_index: int,
        node_name: str,
        event_type: str,
        tool_name: str | None,
        latency_ms: int | None,
        payload_preview: str | None,
    ) -> None:
        """
        Insert one row into agent_steps. Fails silently — observability
        must not block or crash the agent run.

        Bug 4 fix: If the session was previously poisoned by a failed transaction,
        automatically recreate it before attempting the insert.
        """
        if self._session is None:
            return  # Tests with no DB session: skip silently

        async with self._lock:
            # Bug 4 fix: auto-heal poisoned session before insert
            if not self._session_healthy:
                await self._reset_session()
                if self._session is None:
                    return

            try:
                await self._session.execute(
                    text(
                        """
                        INSERT INTO agent_steps
                            (id, run_id, step_index, node_name, event_type,
                             tool_name, latency_ms, payload_preview, created_at)
                        VALUES
                            (:id, :run_id, :step_index, :node_name, :event_type,
                             :tool_name, :latency_ms, :payload_preview, :created_at)
                        """
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "run_id": str(self.run_id),
                        "step_index": step_index,
                        "node_name": node_name,
                        "event_type": event_type,
                        "tool_name": tool_name,
                        "latency_ms": latency_ms,
                        "payload_preview": (payload_preview or "")[:300],
                        "created_at": datetime.now(UTC).replace(tzinfo=None),
                    },
                )
                # Flush immediately so rows are visible even if the run crashes
                await self._session.flush()
            except Exception as exc:
                # Bug 4 fix: mark session as unhealthy so next call recreates it
                self._session_healthy = False
                try:
                    await self._session.rollback()
                except Exception:
                    pass  # rollback also failed — session is fully poisoned
                logger.warning(
                    "step_recorder_write_failed",
                    node_name=node_name,
                    event_type=event_type,
                    error=str(exc),
                )
