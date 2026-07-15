"""
app/graph/state.py — AgentState TypedDict for the LangGraph supervisor.

Design decisions:
  - messages uses add_messages reducer so every node appends rather than replaces.
  - next is the routing decision made by the supervisor ("researcher" | "analyst" |
    "coder" | "FINISH"). It's stored in state so Phase 4 streaming can emit it.
  - step_count prevents infinite loops: if it exceeds MAX_STEPS, the graph force-
    finishes. This is the app-layer guard against infinite agent loops (Card 10).
  - tool_calls_this_run is incremented by tool execution hooks and checked against
    settings.TOOL_CALLS_PER_RUN (also Card 10).
  - failed_specialists tracks which specialists errored this run so the supervisor
    avoids re-routing to broken agents (Bug 3 fix).

interview_answer: "How do you prevent agent loops?"
  "Two guards: step_count caps graph traversals, tool_calls_this_run caps individual
  tool invocations. If either is exceeded the supervisor node receives a forced FINISH
  message and the graph terminates gracefully instead of running forever.
  A third guard (failed_specialists) prevents the supervisor from re-routing to a
  specialist that already errored in this run."
"""

from __future__ import annotations

from typing import Annotated

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

# Maximum supervisor→specialist round-trips per run.
# Configurable via settings; hard limit here for safety.
MAX_STEPS = 10


class AgentState(TypedDict):
    """
    Shared state threaded through every node in the graph.

    Fields:
        messages:           Full conversation including human, AI, and tool messages.
                            add_messages reducer: nodes append, never replace.
        thread_id:          LangGraph thread_id — maps to Thread.id in our DB.
        user_id:            The authenticated user who started this run.
        run_id:             The AgentRun.id for the current invocation.
        next:               Routing target chosen by the supervisor node.
        step_count:         Number of supervisor→specialist round-trips so far.
        tool_calls_this_run: Total tool calls across all specialists in this run.
        failed_specialists: Set of specialist names that returned errors this run.
                            Prevents supervisor from re-routing to broken specialists.
                            (Bug 3 fix)
    """
    messages: Annotated[list[AnyMessage], add_messages]
    thread_id: str
    user_id: str
    run_id: str
    next: str                    # set by supervisor, read by builder for routing
    step_count: int              # incremented in supervisor node
    tool_calls_this_run: int     # incremented by tool execution hooks
    failed_specialists: list[str]  # Bug 3: tracks errored specialists this run
