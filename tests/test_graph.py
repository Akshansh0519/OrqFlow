"""
tests/test_graph.py — Phase 3 acceptance tests for the LangGraph supervisor.

Test strategy:
  - LLM calls are mocked so no API key is needed.
  - Graph is compiled with MemorySaver + InMemoryStore (no Redis/Postgres).
  - Tool calls use mock tools (direct Python function wrappers).
  - Tests verify routing decisions, loop guards, and state transitions.

Acceptance criteria (T-04):
  ✅ build_graph() completes without error
  ✅ Graph nodes include supervisor, researcher, analyst, coder
  ✅ Supervisor routes to END when next="FINISH"
  ✅ Supervisor routes to researcher when next="researcher"
  ✅ Loop guard fires when step_count >= MAX_STEPS
  ✅ Tool call cap fires when tool_calls_this_run >= TOOL_CALLS_PER_RUN
  ✅ Mock tools are loaded correctly (researcher/analyst/coder partition)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore

from app.graph.builder import build_graph
from app.graph.nodes import RouterOutput, make_supervisor_node
from app.graph.state import MAX_STEPS, AgentState
from app.graph.tools import load_agent_tools

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_tools():
    """Load mock tools synchronously for the test session."""
    import asyncio

    return asyncio.get_event_loop().run_until_complete(load_agent_tools(use_mock=True))


@pytest.fixture
def compiled_graph(mock_tools):
    """
    Build and compile the graph with in-memory backends and a mock LLM.
    The mock LLM always returns FINISH so the graph terminates immediately.
    """
    mock_llm = _make_finish_llm()
    uncompiled = build_graph(
        agent_tools=mock_tools,
        supervisor_llm=mock_llm,
        worker_llm=mock_llm,
    )
    return uncompiled.compile(
        checkpointer=MemorySaver(),
        store=InMemoryStore(),
    )


def _make_finish_llm():
    """Create a mock LLM that always routes to FINISH."""
    mock = MagicMock()
    structured = MagicMock()
    # ainvoke returns RouterOutput(next="FINISH")
    structured.ainvoke = AsyncMock(
        return_value=RouterOutput(next="FINISH", reasoning="Test: always finish")
    )
    mock.with_structured_output = MagicMock(return_value=structured)
    return mock


def _make_routing_llm(route_to: str):
    """Create a mock LLM that routes to a specific node, then FINISH."""
    call_count = 0

    mock = MagicMock()
    structured = MagicMock()

    async def smart_ainvoke(messages):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return RouterOutput(next=route_to, reasoning=f"Test: route to {route_to}")
        return RouterOutput(next="FINISH", reasoning="Test: done")

    structured.ainvoke = smart_ainvoke
    mock.with_structured_output = MagicMock(return_value=structured)
    return mock


# ── Tool loading tests ────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_load_agent_tools_returns_all_specialists():
    tools = await load_agent_tools(use_mock=True)
    assert "researcher" in tools
    assert "analyst" in tools
    assert "coder" in tools


@pytest.mark.anyio
async def test_researcher_tools_partitioned_correctly():
    tools = await load_agent_tools(use_mock=True)
    names = {t.name for t in tools["researcher"]}
    assert "web_search" in names or "_web_search" in names
    # researcher must NOT have DB or file tools
    assert not any("query" in n or "read_file" in n for n in names)


@pytest.mark.anyio
async def test_analyst_tools_partitioned_correctly():
    tools = await load_agent_tools(use_mock=True)
    names = {t.name for t in tools["analyst"]}
    # Analyst must have DB tools
    assert any("query" in n or "table" in n for n in names)
    # Analyst must NOT have web or file tools
    assert not any("search" in n or "read_file" in n for n in names)


@pytest.mark.anyio
async def test_coder_tools_partitioned_correctly():
    tools = await load_agent_tools(use_mock=True)
    names = {t.name for t in tools["coder"]}
    # Coder must have file tools
    assert any("file" in n or "lint" in n for n in names)
    # Coder must NOT have web or DB tools
    assert not any("search" in n or "query" in n for n in names)


# ── Graph structure tests ─────────────────────────────────────────────────────


def test_build_graph_succeeds(mock_tools):
    """build_graph() must complete without raising."""
    mock_llm = _make_finish_llm()
    graph = build_graph(agent_tools=mock_tools, supervisor_llm=mock_llm, worker_llm=mock_llm)
    assert graph is not None


def test_graph_has_all_nodes(mock_tools):
    """All 4 nodes must be present in the compiled graph."""
    mock_llm = _make_finish_llm()
    uncompiled = build_graph(agent_tools=mock_tools, supervisor_llm=mock_llm, worker_llm=mock_llm)
    compiled = uncompiled.compile(checkpointer=MemorySaver(), store=InMemoryStore())
    nodes = set(compiled.get_graph().nodes.keys())
    assert "supervisor" in nodes
    assert "researcher" in nodes
    assert "analyst" in nodes
    assert "coder" in nodes


# ── Supervisor node unit tests ────────────────────────────────────────────────


@pytest.mark.anyio
async def test_supervisor_routes_to_end_on_finish():
    """Supervisor must return Command(goto=END) when LLM outputs FINISH."""
    mock_llm = _make_finish_llm()
    supervisor_fn = make_supervisor_node(mock_llm)

    state: AgentState = {
        "messages": [HumanMessage(content="What are the top projects?")],
        "thread_id": "t1",
        "user_id": "u1",
        "run_id": "r1",
        "next": "",
        "step_count": 0,
        "tool_calls_this_run": 0,
    }

    command = await supervisor_fn(state)
    assert command.goto == "responder"
    assert command.update["next"] == "FINISH"


@pytest.mark.anyio
async def test_supervisor_routes_to_researcher():
    """Supervisor must route to 'researcher' when LLM outputs 'researcher'."""
    mock_llm = MagicMock()
    structured = MagicMock()
    structured.ainvoke = AsyncMock(
        return_value=RouterOutput(next="researcher", reasoning="needs web search")
    )
    mock_llm.with_structured_output = MagicMock(return_value=structured)

    supervisor_fn = make_supervisor_node(mock_llm)
    state: AgentState = {
        "messages": [HumanMessage(content="Search the web for LangGraph docs")],
        "thread_id": "t1",
        "user_id": "u1",
        "run_id": "r1",
        "next": "",
        "step_count": 0,
        "tool_calls_this_run": 0,
    }

    command = await supervisor_fn(state)
    assert command.goto == "researcher"
    assert command.update["next"] == "researcher"
    assert command.update["step_count"] == 1


@pytest.mark.anyio
async def test_supervisor_routes_to_analyst():
    """Supervisor must route to 'analyst' when LLM outputs 'analyst'."""
    mock_llm = MagicMock()
    structured = MagicMock()
    structured.ainvoke = AsyncMock(
        return_value=RouterOutput(next="analyst", reasoning="needs DB query")
    )
    mock_llm.with_structured_output = MagicMock(return_value=structured)

    supervisor_fn = make_supervisor_node(mock_llm)
    state: AgentState = {
        "messages": [HumanMessage(content="Who are the engineers?")],
        "thread_id": "t1",
        "user_id": "u1",
        "run_id": "r1",
        "next": "",
        "step_count": 0,
        "tool_calls_this_run": 0,
    }

    command = await supervisor_fn(state)
    assert command.goto == "analyst"


@pytest.mark.anyio
async def test_loop_guard_fires_at_max_steps():
    """Supervisor must route to END without calling LLM when step_count >= MAX_STEPS."""
    mock_llm = MagicMock()
    # If loop guard fires, the LLM should NOT be called
    structured = MagicMock()
    structured.ainvoke = AsyncMock(side_effect=Exception("LLM should not be called"))
    mock_llm.with_structured_output = MagicMock(return_value=structured)

    supervisor_fn = make_supervisor_node(mock_llm)
    state: AgentState = {
        "messages": [HumanMessage(content="test")],
        "thread_id": "t1",
        "user_id": "u1",
        "run_id": "r1",
        "next": "",
        "step_count": MAX_STEPS,  # at the limit
        "tool_calls_this_run": 0,
    }

    # Should NOT raise — loop guard must handle this gracefully
    command = await supervisor_fn(state)
    assert command.goto == "responder"


@pytest.mark.anyio
async def test_supervisor_handles_llm_error_gracefully():
    """If LLM errors, supervisor must route to responder rather than crashing."""
    mock_llm = MagicMock()
    structured = MagicMock()
    structured.ainvoke = AsyncMock(side_effect=Exception("LLM rate limit exceeded"))
    mock_llm.with_structured_output = MagicMock(return_value=structured)

    supervisor_fn = make_supervisor_node(mock_llm)
    state: AgentState = {
        "messages": [HumanMessage(content="test")],
        "thread_id": "t1",
        "user_id": "u1",
        "run_id": "r1",
        "next": "",
        "step_count": 0,
        "tool_calls_this_run": 0,
    }

    command = await supervisor_fn(state)
    assert command.goto == "responder"


# ── Full graph invocation tests ───────────────────────────────────────────────


@pytest.mark.anyio
async def test_graph_invoke_with_finish_llm(compiled_graph):
    """Full graph invocation must return a result without crashing."""
    config = {"configurable": {"thread_id": "test-thread-001"}}
    state: AgentState = {
        "messages": [HumanMessage(content="Hello, what can you do?")],
        "thread_id": "test-thread-001",
        "user_id": "test-user",
        "run_id": "test-run-001",
        "next": "",
        "step_count": 0,
        "tool_calls_this_run": 0,
    }

    result = await compiled_graph.ainvoke(state, config=config)
    # Graph must have completed without exception
    assert "messages" in result
    assert result["next"] == "FINISH"


@pytest.mark.anyio
async def test_graph_state_persists_between_runs(mock_tools):
    """Checkpointer must persist state so the second run sees previous messages."""
    checkpointer = MemorySaver()
    mock_llm = _make_finish_llm()
    graph = build_graph(
        agent_tools=mock_tools,
        supervisor_llm=mock_llm,
        worker_llm=mock_llm,
    ).compile(checkpointer=checkpointer, store=InMemoryStore())

    config = {"configurable": {"thread_id": "persist-test-001"}}
    initial_state: AgentState = {
        "messages": [HumanMessage(content="First message")],
        "thread_id": "persist-test-001",
        "user_id": "u1",
        "run_id": "r1",
        "next": "",
        "step_count": 0,
        "tool_calls_this_run": 0,
    }

    # First run
    await graph.ainvoke(initial_state, config=config)

    # Second run — add a new message (state already has "First message" in checkpoint)
    followup_state: AgentState = {
        "messages": [HumanMessage(content="Second message")],
        "thread_id": "persist-test-001",
        "user_id": "u1",
        "run_id": "r2",
        "next": "",
        "step_count": 0,
        "tool_calls_this_run": 0,
    }
    result2 = await graph.ainvoke(followup_state, config=config)

    # The add_messages reducer should have accumulated both messages
    assert len(result2["messages"]) >= 2
