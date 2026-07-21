"""
app/routers/agent_router.py — Core API for LangGraph interactions.

Endpoints:
  - POST /api/threads            → Create a new conversation thread.
  - GET  /api/threads            → List all threads for the current user.
  - POST /api/threads/{id}/run   → Execute the graph and stream SSE back.
  - GET  /api/threads/{id}/trace → Fetch historical trace/messages from checkpointer.
  - GET  /api/runs/{id}/trace    → Fetch step observability rows from agent_steps table.
  - GET  /api/facts              → Fetch long-term memory facts for the user.
  - GET  /api/users/me/facts     → Alias for /api/facts.
  - DELETE /api/users/me/facts/{key} → Delete a long-term memory fact.
  - GET  /api/mcp/health         → Check health of all 3 MCP servers.

Security:
  - All endpoints require get_current_user (JWT).
"""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

import httpx
import structlog
from fastapi import APIRouter, Depends, Request
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.config import settings
from app.dependencies import get_current_user, get_db
from app.errors import AppError
from app.models import AgentRun, AgentStep, Thread, User
from app.recorder import StepRecorder

router = APIRouter(prefix="/api", tags=["Agent"])
logger = structlog.get_logger()


# ── Request / Response Models ─────────────────────────────────────────────────


class CreateThreadRequest(BaseModel):
    title: str = Field(default="New Thread", min_length=1, max_length=120)


class ThreadResponse(BaseModel):
    thread_id: str
    title: str


class RunRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)


# ── Helper: translate_event ───────────────────────────────────────────────────


def translate_event(mode: str, chunk: Any, run_id: str) -> list[tuple[str, dict]]:
    """Map LangGraph streaming modes onto OrqFlow SSE event contract."""
    events = []
    ts = time.time()
    if mode == "updates":
        for node_name, update in chunk.items():
            if not isinstance(update, dict):
                continue
            step_index = update.get("step_count", 0)
            events.append(
                (
                    "node_start",
                    {"run_id": run_id, "node": node_name, "step_index": step_index, "ts": ts},
                )
            )
            if node_name == "supervisor" and "next" in update:
                events.append(
                    (
                        "routing",
                        {
                            "run_id": run_id,
                            "next_agent": update["next"],
                            "reasoning": update.get("routing_reasoning", ""),
                        },
                    )
                )
            events.append(
                (
                    "node_end",
                    {
                        "run_id": run_id,
                        "node": node_name,
                        "step_index": step_index,
                        "latency_ms": 0,
                        "ts": ts,
                    },
                )
            )
            if (
                node_name == "responder"
                and "messages" in update
                and isinstance(update["messages"], list)
                and update["messages"]
            ):
                last_msg = update["messages"][-1]
                if hasattr(last_msg, "content") and last_msg.content:
                    events.append(
                        (
                            "responder_message",
                            {"run_id": run_id, "node": "responder", "text": str(last_msg.content)},
                        )
                    )
            events.append(
                ("step", {"node": node_name, "next": update.get("next"), "step_count": step_index})
            )
    elif mode == "messages":
        if isinstance(chunk, tuple) and len(chunk) >= 1:
            msg = chunk[0]
            metadata = chunk[1] if len(chunk) > 1 and isinstance(chunk[1], dict) else {}
            node_name = metadata.get("langgraph_node", getattr(msg, "name", ""))
            if node_name == "responder" and hasattr(msg, "content") and msg.content:
                events.append(
                    ("token", {"run_id": run_id, "node": "responder", "token": str(msg.content)})
                )
    elif mode == "custom":
        if isinstance(chunk, dict) and "event_type" in chunk:
            evt_type = chunk["event_type"]
            if evt_type in ("tool_call", "tool_result"):
                events.append((evt_type, {"run_id": run_id, **chunk, "ts": ts}))
            # Bug 7 fix: surface model_switch events so frontend can notify user
            elif evt_type == "model_switch":
                events.append(
                    (
                        "model_switch",
                        {
                            "run_id": run_id,
                            "from_model": chunk.get("from_model", "unknown"),
                            "to_model": chunk.get("to_model", "unknown"),
                            "reason": chunk.get("reason", "error"),
                            "ts": ts,
                        },
                    )
                )
    return events


async def _get_thread_for_user(
    db: AsyncSession,
    thread_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Thread | None:
    result = await db.execute(
        select(Thread).where(Thread.id == thread_id, Thread.user_id == user_id)
    )
    return result.scalar_one_or_none()


# ── Thread Management ─────────────────────────────────────────────────────────


@router.post("/threads", status_code=201)
async def create_thread(
    body: CreateThreadRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ThreadResponse:
    """Create a new conversation thread."""
    thread_uuid = uuid.uuid4()
    thread_id = str(thread_uuid)
    try:
        thread = Thread(id=thread_uuid, user_id=user.id, title=body.title)
        db.add(thread)
        await db.commit()
    except Exception as exc:
        await db.rollback()
        logger.error("create_thread_failed", user_id=str(user.id), exc=str(exc))
        raise AppError("Failed to create thread", status_code=500, code="THREAD_CREATE_FAILED")
    return ThreadResponse(thread_id=thread_id, title=body.title)


@router.get("/threads")
async def list_threads(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ThreadResponse]:
    """List threads for the user."""
    stmt = select(Thread).where(Thread.user_id == user.id).order_by(Thread.created_at.desc())
    result = await db.execute(stmt)
    threads = result.scalars().all()
    return [ThreadResponse(thread_id=str(t.id), title=t.title) for t in threads]


# ── Run (SSE Streaming) ───────────────────────────────────────────────────────


@router.post("/threads/{thread_id}/run")
async def run_agent(
    thread_id: str,
    body: RunRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventSourceResponse:
    """Execute the agent graph for a thread and stream results via SSE."""
    graph = request.app.state.graph
    if not graph:
        raise AppError("Graph not initialized", status_code=500)
    try:
        thread_uuid = uuid.UUID(thread_id)
    except ValueError:
        raise AppError("Invalid thread_id format", status_code=400)

    existing_thread = await db.scalar(select(Thread).where(Thread.id == thread_uuid))
    if existing_thread is not None:
        owned_thread = await _get_thread_for_user(db, thread_uuid, user.id)
        if owned_thread is None:
            raise AppError("Thread not found", status_code=404, code="THREAD_NOT_FOUND")

    run_uuid = uuid.uuid4()
    run_id = str(run_uuid)
    config = {
        "configurable": {
            "thread_id": thread_id,
            "user_id": str(user.id),
            "run_id": run_id,
        }
    }

    input_state = {
        "messages": [HumanMessage(content=body.message)],
        "thread_id": thread_id,
        "user_id": str(user.id),
        "run_id": run_id,
        "next": "",
        "step_count": 0,
        "tool_calls_this_run": 0,
        "failed_specialists": [],  # Bug 3 fix: initialize empty for each run
    }

    async def event_generator() -> AsyncGenerator[dict, None]:
        try:
            thread = await _get_thread_for_user(db, thread_uuid, user.id)
            if thread is None:
                new_thread = Thread(
                    id=thread_uuid,
                    user_id=user.id,
                    title=(body.message[:35] + "...") if len(body.message) > 35 else body.message,
                )
                db.add(new_thread)
                await db.flush()

            run_row = AgentRun(
                id=run_uuid,
                thread_id=thread_uuid,
                status="RUNNING",
                started_at=datetime.now(UTC).replace(tzinfo=None),
            )
            db.add(run_row)
            await db.commit()
        except Exception as exc:
            logger.warning("create_run_row_failed", thread_id=thread_id, exc=str(exc))
            await db.rollback()
            yield {
                "event": "error",
                "data": json.dumps({"run_id": run_id, "message": "Failed to create run record"}),
            }
            return

        async with StepRecorder.for_run(thread_id=thread_id, run_id=run_uuid) as recorder:
            config["configurable"]["step_recorder"] = recorder
            try:
                async for mode, chunk in graph.astream(
                    input_state, config=config, stream_mode=["updates", "messages", "custom"]
                ):
                    for event_name, payload in translate_event(mode, chunk, run_id):
                        if event_name in ("node_start", "node_end", "tool_call", "tool_result"):
                            await recorder._insert(
                                step_index=payload.get("step_index") or recorder._step_index,
                                node_name=payload.get("node", "unknown"),
                                event_type=event_name,
                                tool_name=payload.get("tool_name"),
                                latency_ms=payload.get("latency_ms"),
                                payload_preview=str(payload)[:300],
                            )
                            if event_name == "node_start":
                                recorder._step_index += 1

                        yield {
                            "event": event_name,
                            "data": json.dumps(payload),
                        }

                yield {
                    "event": "run_complete",
                    "data": json.dumps(recorder.summary()),
                }
                yield {
                    "event": "done",
                    "data": json.dumps({"status": "completed", "run_id": run_id}),
                }
            except Exception as exc:
                recorder.mark_failed()
                # Bug 6 fix: classify the error so the user gets a meaningful message
                err_str = str(exc).lower()
                is_rate_limit = (
                    "429" in err_str
                    or "rate limit" in err_str
                    or "rate_limit_exceeded" in err_str
                    or "quota" in err_str
                    or "tokens per minute" in err_str
                    or "tokens per day" in err_str
                )
                if is_rate_limit:
                    user_message = (
                        "⚠️ **All AI models are temporarily at capacity.** "
                        "Groq daily/minute quota reached. This typically resets within "
                        "1 minute (per-minute limit) or up to 40 minutes (daily quota). "
                        "Please try again shortly."
                    )
                else:
                    user_message = f"❌ Agent encountered an error: {exc}"
                yield {
                    "event": "error",
                    "data": json.dumps(
                        {
                            "run_id": run_id,
                            "message": user_message,
                            "error": str(exc),
                            "is_rate_limit": is_rate_limit,
                        }
                    ),
                }

    return EventSourceResponse(
        event_generator(),
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


# ── Trace & Observability ─────────────────────────────────────────────────────


@router.get("/threads/{thread_id}/trace")
async def get_thread_trace(
    thread_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get the full message history for a thread from the checkpointer."""
    graph = request.app.state.graph
    if not graph:
        raise AppError("Graph not initialized", status_code=500)
    try:
        thread_uuid = uuid.UUID(thread_id)
    except ValueError:
        raise AppError("Invalid thread_id format", status_code=400)
    owned_thread = await _get_thread_for_user(db, thread_uuid, user.id)
    if owned_thread is None:
        raise AppError("Thread not found", status_code=404, code="THREAD_NOT_FOUND")

    config = {"configurable": {"thread_id": thread_id}}
    state = await graph.aget_state(config)

    if not state or not state.values:
        return {"messages": []}

    messages = []
    for msg in state.values.get("messages", []):
        msg_dict = {
            "type": msg.type,
            "content": msg.content,
        }
        if hasattr(msg, "name") and msg.name:
            msg_dict["name"] = msg.name
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            msg_dict["tool_calls"] = msg.tool_calls
        messages.append(msg_dict)

    return {"messages": messages}


@router.get("/runs/{run_id}/trace")
async def get_run_trace(
    run_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Fetch step observability rows from agent_steps table."""
    try:
        run_uuid = uuid.UUID(run_id)
    except ValueError:
        raise AppError("Invalid run_id format", status_code=400)

    owned_run = await db.scalar(
        select(AgentRun.id)
        .join(Thread, AgentRun.thread_id == Thread.id)
        .where(AgentRun.id == run_uuid, Thread.user_id == user.id)
    )
    if owned_run is None:
        raise AppError("Run not found", status_code=404, code="RUN_NOT_FOUND")

    result = await db.execute(
        select(AgentStep)
        .join(AgentRun, AgentStep.run_id == AgentRun.id)
        .join(Thread, AgentRun.thread_id == Thread.id)
        .where(AgentStep.run_id == run_uuid)
        .where(Thread.user_id == user.id)
        .order_by(AgentStep.step_index)
    )
    steps = result.scalars().all()
    return {
        "run_id": run_id,
        "steps": [
            {
                "step_index": s.step_index,
                "node_name": s.node_name,
                "event_type": s.event_type,
                "tool_name": s.tool_name,
                "latency_ms": s.latency_ms,
                "payload_preview": s.payload_preview,
                "created_at": s.created_at.isoformat(),
            }
            for s in steps
        ],
    }


# ── Facts ─────────────────────────────────────────────────────────────────────


@router.get("/facts")
@router.get("/users/me/facts")
async def list_facts(
    request: Request,
    user: User = Depends(get_current_user),
) -> list[dict]:
    """List long-term memory facts for the user from the store."""
    store = request.app.state.store
    if not store:
        return []

    namespace = (str(user.id), "facts")
    items = await store.asearch(namespace)

    return [{"key": item.key, "value": item.value} for item in items]


@router.delete("/users/me/facts/{fact_key}", status_code=204, response_model=None)
async def delete_fact(
    fact_key: str,
    request: Request,
    user: User = Depends(get_current_user),
) -> None:
    """Delete a long-term memory fact."""
    store = request.app.state.store
    if not store:
        return

    namespace = (str(user.id), "facts")
    await store.adelete(namespace, fact_key)


# ── MCP Health ────────────────────────────────────────────────────────────────


@router.get("/mcp/health")
async def check_mcp_health(
    user: User = Depends(get_current_user),
) -> dict:
    """Check health status of all 3 MCP servers."""
    urls = {
        "db": settings.MCP_DB_URL,
        "search": settings.MCP_SEARCH_URL,
        "files": settings.MCP_FILES_URL,
    }
    status = {}
    async with httpx.AsyncClient(timeout=2.0, follow_redirects=True) as client:
        for name, url in urls.items():
            try:
                res = await client.get(url)
                status[name] = (
                    "ok" if res.status_code in (200, 202, 406) else f"error ({res.status_code})"
                )
            except Exception as exc:
                status[name] = f"unreachable ({type(exc).__name__})"
    return {
        "status": "ok" if all(v == "ok" for v in status.values()) else "degraded",
        "servers": status,
    }
