"""
tests/test_agent.py — Phase 4 acceptance tests for the Agent API.

Tests the streaming run endpoint, thread creation, tracing, and facts.
Mocks out the LangGraph execution using a mock LLM so no API calls are made.

Acceptance criteria (T-05):
  ✅ POST /api/threads creates a thread
  ✅ GET /api/threads lists threads
  ✅ POST /api/threads/{id}/run streams Server-Sent Events (SSE)
  ✅ GET /api/threads/{id}/trace returns message history
  ✅ GET /api/facts returns facts from the store
  ✅ Unauthenticated requests are rejected (401)
"""

from __future__ import annotations

import json
import pytest
from httpx import AsyncClient

from tests.test_graph import _make_finish_llm
from app.graph.builder import build_graph
from app.graph.tools import load_agent_tools
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
async def auth_client(async_client: AsyncClient) -> AsyncClient:
    """Register a user, login, and return an authenticated client."""
    email = "agent_test@example.com"
    password = "SuperSecretPassword123!"
    
    # Register
    await async_client.post(
        "/api/auth/register",
        json={"email": email, "username": "agent_test", "password": password}
    )
    
    # Login
    login_res = await async_client.post(
        "/api/auth/login",
        json={"email": email, "password": password}
    )
    token = login_res.json()["access_token"]
    
    # Set Authorization header
    async_client.headers["Authorization"] = f"Bearer {token}"
    return async_client


async def _register_and_login(
    client: AsyncClient,
    *,
    email: str,
    username: str,
) -> str:
    password = "SuperSecretPassword123!"
    await client.post(
        "/api/auth/register",
        json={"email": email, "username": username, "password": password},
    )
    login_res = await client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    return login_res.json()["access_token"]


@pytest.fixture(autouse=True)
async def mock_graph_state():
    """
    Override the production graph in app.state with a mocked one
    that always finishes immediately, using in-memory backends.
    """
    from app.main import app
    tools = await load_agent_tools(use_mock=True)
    llm = _make_finish_llm()
    graph = build_graph(tools, supervisor_llm=llm, worker_llm=llm)
    
    app.state.checkpointer = MemorySaver()
    app.state.store = InMemoryStore()
    app.state.graph = graph.compile(
        checkpointer=app.state.checkpointer,
        store=app.state.store
    )
    return app.state.graph


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_unauthenticated_requests_rejected(async_client: AsyncClient):
    res = await async_client.post("/api/threads", json={"title": "Test"})
    assert res.status_code == 401

    res = await async_client.post("/api/threads/123/run", json={"message": "hi"})
    assert res.status_code == 401


@pytest.mark.anyio
async def test_create_thread(auth_client: AsyncClient):
    res = await auth_client.post("/api/threads", json={"title": "My Thread"})
    assert res.status_code == 201
    data = res.json()
    assert "thread_id" in data
    assert data["title"] == "My Thread"


@pytest.mark.anyio
async def test_list_threads(auth_client: AsyncClient):
    res = await auth_client.get("/api/threads")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


@pytest.mark.anyio
async def test_run_agent_streams_sse(auth_client: AsyncClient):
    """Test that the run endpoint returns valid Server-Sent Events."""
    # 1. Create a thread
    thread_res = await auth_client.post("/api/threads", json={"title": "Stream Test"})
    thread_id = thread_res.json()["thread_id"]

    # 2. Run the agent (we have to use httpx stream to read SSE)
    events = []
    async with auth_client.stream(
        "POST", 
        f"/api/threads/{thread_id}/run", 
        json={"message": "Hello OrqFlow!"}
    ) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        
        async for line in response.aiter_lines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("event: "):
                events.append({"event": line.replace("event: ", "")})
            elif line.startswith("data: "):
                events[-1]["data"] = json.loads(line.replace("data: ", ""))

    # Mock LLM returns FINISH immediately, so we should at least see a "done" event
    assert len(events) > 0
    done_events = [e for e in events if e["event"] == "done"]
    assert len(done_events) == 1
    assert done_events[0]["data"]["status"] == "completed"


@pytest.mark.anyio
async def test_get_trace(auth_client: AsyncClient):
    """Test that trace returns the message history for a thread."""
    thread_res = await auth_client.post("/api/threads", json={"title": "Trace Test"})
    thread_id = thread_res.json()["thread_id"]

    # Run something so the checkpointer saves state
    async with auth_client.stream(
        "POST", 
        f"/api/threads/{thread_id}/run", 
        json={"message": "Trace me"}
    ) as response:
        async for _ in response.aiter_lines():
            pass

    # Get the trace
    res = await auth_client.get(f"/api/threads/{thread_id}/trace")
    assert res.status_code == 200
    data = res.json()
    
    assert "messages" in data
    assert isinstance(data["messages"], list)
    assert len(data["messages"]) > 0
    assert data["messages"][0]["type"] == "human"
    assert data["messages"][0]["content"] == "Trace me"


@pytest.mark.anyio
async def test_list_facts(auth_client: AsyncClient):
    """Test that facts endpoint returns user's long-term memory."""
    # Our mock InMemoryStore is empty initially
    res = await auth_client.get("/api/facts")
    assert res.status_code == 200
    assert res.json() == []


@pytest.mark.anyio
async def test_user_cannot_run_or_trace_another_users_thread(async_client: AsyncClient):
    token_a = await _register_and_login(
        async_client, email="owner@example.com", username="owneruser"
    )
    token_b = await _register_and_login(
        async_client, email="intruder@example.com", username="intruderuser"
    )

    thread_res = await async_client.post(
        "/api/threads",
        json={"title": "Private Thread"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    thread_id = thread_res.json()["thread_id"]

    run_res = await async_client.post(
        f"/api/threads/{thread_id}/run",
        json={"message": "hello"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert run_res.status_code == 404

    trace_res = await async_client.get(
        f"/api/threads/{thread_id}/trace",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert trace_res.status_code == 404


@pytest.mark.anyio
async def test_user_cannot_read_another_users_run_trace(async_client: AsyncClient):
    token_a = await _register_and_login(
        async_client, email="runowner@example.com", username="runowner"
    )
    token_b = await _register_and_login(
        async_client, email="runintruder@example.com", username="runintruder"
    )

    thread_res = await async_client.post(
        "/api/threads",
        json={"title": "Run Trace Thread"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    thread_id = thread_res.json()["thread_id"]

    run_id = None
    async with async_client.stream(
        "POST",
        f"/api/threads/{thread_id}/run",
        json={"message": "Trace ownership"},
        headers={"Authorization": f"Bearer {token_a}"},
    ) as response:
        assert response.status_code == 200
        async for line in response.aiter_lines():
            line = line.strip()
            if line.startswith("data: "):
                payload = json.loads(line.replace("data: ", ""))
                run_id = payload.get("run_id") or run_id

    assert run_id is not None
    trace_res = await async_client.get(
        f"/api/runs/{run_id}/trace",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert trace_res.status_code == 404
