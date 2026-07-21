"""
app/graph/nodes.py — Supervisor and specialist agent node functions.

Architecture:
  - supervisor_node:   Routes using structured LLM output (RouterOutput).
                       Returns Command(goto=next_node | END).
  - make_specialist_node(name, llm, tools, prompt):
                       Factory that builds a ReAct specialist node.
                       Returns a function that takes AgentState and returns
                       Command(goto="supervisor", update=state_delta).

Infinite loop prevention (Card 10 / §17):
  - supervisor_node checks step_count >= MAX_STEPS before calling the LLM.
  - If the limit is hit, it injects a system message and routes to END.
  - This is the application-level guard. Rate limiting is the infrastructure-level guard.

Bug 1 fix (context window trimming):
  - supervisor_node now passes ONLY the last 6 messages to the router LLM.
  - This prevents stale historical context from dominating routing decisions.

Bug 3 fix (failed specialist tracking):
  - specialist_node marks itself as failed in state when it errors.
  - supervisor_node injects failed_specialists into the prompt so the LLM
    avoids re-routing to broken specialists.

interview_answer: "Walk me through a request that needs researcher + analyst."
  "User asks: 'What's the team working on this month, and who is the lead?'
   Supervisor routes to analyst (query projects, tasks tables). Analyst returns data.
   Supervisor sees 'owner_id' but no name — routes to analyst again for employee lookup.
   Supervisor has full answer, sets FINISH. Final reply synthesized from both results.
   Two round-trips, two DB queries, zero web search needed."
"""

from __future__ import annotations

import warnings

import structlog
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.types import Command
from pydantic import BaseModel

# create_react_agent is deprecated in langgraph-prebuilt 1.x (moved to langchain.agents
# in LangGraph 2.0). Suppress the warning until we upgrade — function still works.
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", message="create_react_agent has been moved")
    from langgraph.prebuilt import create_react_agent  # type: ignore[import]

from typing import Literal

from langchain_core.runnables import RunnableConfig

from app.config import settings
from app.graph.prompts import (
    FACT_EXTRACTION_SYSTEM_PROMPT,
    RESPONDER_SYSTEM_PROMPT,
    SUPERVISOR_SYSTEM_PROMPT,
)
from app.graph.state import MAX_STEPS, AgentState

logger = structlog.get_logger()

# Bug 1 fix: only send last N messages to supervisor to prevent stale history confusion.
SUPERVISOR_CONTEXT_WINDOW = 6


# ── Router output schema ──────────────────────────────────────────────────────

SPECIALIST_NAMES = {"researcher", "analyst", "coder"}


class RouterOutput(BaseModel):
    """
    Structured output from the supervisor LLM.
    Using Pydantic so LangChain's with_structured_output works.
    """

    next: Literal["researcher", "analyst", "coder", "FINISH"]
    reasoning: str


class FactExtractionOutput(BaseModel):
    should_remember: bool
    key: str = ""
    value: str = ""


# ── Supervisor node ───────────────────────────────────────────────────────────


def make_supervisor_node(llm):
    """
    Factory: build the supervisor node with the given LLM.
    """
    router_chain = llm.with_structured_output(RouterOutput)

    async def supervisor_node(state: AgentState, config: RunnableConfig | None = None) -> Command:
        config = config or {}
        step = state.get("step_count", 0)
        recorder = config.get("configurable", {}).get("step_recorder")
        # Bug 3: Retrieve set of specialists that errored this run.
        failed_specialists = state.get("failed_specialists") or []

        # ── Loop guard ─────────────────────────────────────────────────────
        if step >= MAX_STEPS:
            logger.warning(
                "supervisor_loop_guard",
                step_count=step,
                max=MAX_STEPS,
                thread_id=state.get("thread_id"),
            )
            stop_msg = SystemMessage(
                content=(
                    f"[SYSTEM] Maximum step limit ({MAX_STEPS}) reached. "
                    "Synthesize the best answer from the information gathered so far."
                )
            )
            messages = list(state["messages"]) + [stop_msg]
            return Command(
                goto="responder",
                update={"messages": messages, "next": "FINISH"},
            )

        # ── Normal routing ─────────────────────────────────────────────────
        # Bug 1 fix: trim to last SUPERVISOR_CONTEXT_WINDOW messages only.
        # This prevents old messages from prior runs/topics dominating routing.
        recent_messages = list(state["messages"])[-SUPERVISOR_CONTEXT_WINDOW:]

        # ── Auto-FINISH detection (prevents coder/researcher loop) ─────────
        # If the most recent message is a completed specialist AI response
        # (not requesting tool calls), route directly to FINISH without
        # wasting another LLM call on the weakened fallback model.
        if recent_messages:
            last_msg = recent_messages[-1]
            is_ai_msg = (
                hasattr(last_msg, "content") and hasattr(last_msg, "type") and last_msg.type == "ai"
            )
            has_no_tool_calls = not (hasattr(last_msg, "tool_calls") and last_msg.tool_calls)
            # If the last message is a completed AI response with no pending tool calls,
            # and a specialist has already been called this run (step > 0), go to FINISH.
            if is_ai_msg and has_no_tool_calls and step > 0:
                logger.info(
                    "supervisor_auto_finish",
                    step=step,
                    reason="specialist_completed_auto_finish",
                    thread_id=state.get("thread_id"),
                )
                return Command(
                    goto="responder",
                    update={"next": "FINISH", "step_count": step + 1},
                )
        # Bug 3 fix: inject failed specialists into the system prompt so the
        # LLM knows to avoid them.
        system_content = SUPERVISOR_SYSTEM_PROMPT
        if failed_specialists:
            failed_list = ", ".join(failed_specialists)
            system_content += (
                f"\n\nFAILED SPECIALISTS (do NOT route to these): {failed_list}\n"
                "Route to an alternative specialist or set next=FINISH."
            )

        messages = [SystemMessage(content=system_content)] + recent_messages

        async def _invoke():
            try:
                return await router_chain.ainvoke(messages, config=config)
            except Exception as exc:
                logger.error("supervisor_llm_error", exc=str(exc))
                return RouterOutput(next="FINISH", reasoning=f"Error: {exc}")

        if recorder:
            async with recorder.timed("supervisor", "node_exec"):
                result = await _invoke()
        else:
            result = await _invoke()

        logger.info(
            "supervisor_routing",
            next=result.next,
            reasoning=result.reasoning,
            step=step,
            thread_id=state.get("thread_id"),
            failed_specialists=failed_specialists,
        )

        # Bug 3 fix: if the LLM tries to route to a failed specialist, redirect to FINISH.
        if result.next in failed_specialists:
            logger.warning(
                "supervisor_blocked_failed_specialist",
                attempted=result.next,
                thread_id=state.get("thread_id"),
            )
            result = RouterOutput(
                next="FINISH", reasoning="Redirected — specialist previously errored."
            )

        goto = result.next if result.next in SPECIALIST_NAMES else "responder"

        return Command(
            goto=goto,
            update={
                "next": result.next,
                "step_count": step + 1,
            },
        )

    return supervisor_node


# ── Specialist node factory ───────────────────────────────────────────────────


def make_specialist_node(name: str, llm, tools: list[BaseTool], system_prompt: str):
    """
    Factory: build a ReAct specialist node.

    Args:
        name:          Node name ("researcher" | "analyst" | "coder").
        llm:           ChatModel instance (WORKER_LLM_MODEL / Haiku).
        tools:         List of LangChain BaseTool objects for this specialist.
        system_prompt: System message injected at the start of every invocation.

    Returns:
        An async function suitable for graph.add_node(name, ...).

    The specialist uses create_react_agent from langgraph.prebuilt.
    It runs until all tool calls are satisfied, then returns to the supervisor.

    Bug 3 fix: On exception, marks the specialist as failed in state so the
    supervisor won't re-route here in the same run.
    """
    # Create the internal ReAct sub-graph
    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=system_prompt,
    )

    async def specialist_node(state: AgentState, config: RunnableConfig | None = None) -> Command:
        config = config or {}
        tool_count = state.get("tool_calls_this_run", 0)
        recorder = config.get("configurable", {}).get("step_recorder")
        failed_specialists = list(state.get("failed_specialists") or [])

        # ── Per-run tool call cap (Card 10) ────────────────────────────────
        if tool_count >= settings.TOOL_CALLS_PER_RUN:
            logger.warning(
                "tool_call_limit_reached",
                specialist=name,
                count=tool_count,
                limit=settings.TOOL_CALLS_PER_RUN,
            )
            cap_msg = AIMessage(
                content=(
                    f"[{name.upper()}] Tool call limit reached ({settings.TOOL_CALLS_PER_RUN}). "
                    "Returning partial results."
                )
            )
            return Command(
                goto="supervisor",
                update={"messages": [cap_msg], "tool_calls_this_run": tool_count},
            )

        # ── ReAct invocation ───────────────────────────────────────────────
        # Trim state messages to prevent react agent from processing 30+
        # historical messages and making redundant tool calls in a loop.
        SPECIALIST_CONTEXT = 10
        trimmed_state = dict(state)
        all_msgs = list(state.get("messages", []))
        # Always include the original HumanMessage + last N messages
        from langchain_core.messages import HumanMessage as _HM

        human_msgs = [m for m in all_msgs if isinstance(m, _HM)]
        recent_msgs = all_msgs[-SPECIALIST_CONTEXT:]
        # Merge: first HumanMessage + recent, deduplicated preserving order
        seen_ids = set()
        merged = []
        for m in human_msgs[-1:] + recent_msgs:
            msg_id = id(m)
            if msg_id not in seen_ids:
                seen_ids.add(msg_id)
                merged.append(m)
        trimmed_state["messages"] = merged

        async def _invoke():
            try:
                return await agent.ainvoke(trimmed_state, config=config)
            except Exception as exc:
                logger.error("specialist_error", specialist=name, exc=str(exc))
                error_msg = AIMessage(
                    content=f"[{name.upper()}] Error: {exc}. Please try a different approach."
                )
                return {"messages": [error_msg], "_errored": True}

        if recorder:
            async with recorder.timed(name, "node_exec"):
                result = await _invoke()
            for m in result.get("messages", []):
                if hasattr(m, "usage_metadata") and m.usage_metadata:
                    recorder.record_usage(
                        m.usage_metadata.get("input_tokens", 0),
                        m.usage_metadata.get("output_tokens", 0),
                    )
        else:
            result = await _invoke()

        # Bug 3 fix: if this invocation errored, add this specialist to the
        # failed list so the supervisor won't re-route here.
        errored = result.pop("_errored", False) if isinstance(result, dict) else False
        if errored:
            if name not in failed_specialists:
                failed_specialists = failed_specialists + [name]
            logger.warning(
                "specialist_marked_failed",
                specialist=name,
                failed_list=failed_specialists,
            )

        # Count tool calls made in this invocation
        new_tool_calls = sum(
            1 for m in result.get("messages", []) if hasattr(m, "tool_calls") and m.tool_calls
        )

        logger.info(
            "specialist_done",
            specialist=name,
            new_messages=len(result.get("messages", [])),
            new_tool_calls=new_tool_calls,
        )

        return Command(
            goto="supervisor",
            update={
                "messages": result.get("messages", []),
                "tool_calls_this_run": tool_count + new_tool_calls,
                "failed_specialists": failed_specialists,  # Bug 3 fix
            },
        )

    specialist_node.__name__ = f"{name}_node"
    return specialist_node


def make_responder_node(llm):
    """Factory: build the final responder node."""

    async def responder_node(
        state: AgentState, config: RunnableConfig | None = None, *, store=None
    ) -> Command:
        config = config or {}
        recorder = config.get("configurable", {}).get("step_recorder")
        user_id = config.get("configurable", {}).get("user_id", "anonymous")

        facts_text = ""
        if store and user_id != "anonymous":
            try:
                if hasattr(store, "asearch"):
                    items = await store.asearch((str(user_id), "facts"))
                    if items:
                        facts_text = "\n".join(
                            f"- {i.key}: {i.value.get('value', '')}" for i in items
                        )
                elif hasattr(store, "search"):
                    items = store.search((str(user_id), "facts"))
                    if items:
                        facts_text = "\n".join(
                            f"- {i.key}: {i.value.get('value', '')}" for i in items
                        )
            except Exception as exc:
                logger.warning("responder_fetch_facts_failed", exc=str(exc))

        system_msg = RESPONDER_SYSTEM_PROMPT
        if facts_text:
            system_msg += f"\n\nKnown user facts:\n{facts_text}"

        messages = [SystemMessage(content=system_msg)] + list(state["messages"])
        if messages and isinstance(messages[-1], AIMessage):
            messages.append(
                HumanMessage(
                    content="Please synthesize all actions and results from the specialists above into the final markdown response for the user."
                )
            )

        async def _invoke():
            try:
                return await llm.ainvoke(messages, config=config)
            except Exception as exc:
                logger.error("responder_llm_error", exc=str(exc))
                # Check if it's a rate limit error for better UX messaging
                err_str = str(exc).lower()
                is_rate_limit = "429" in err_str or "rate limit" in err_str or "quota" in err_str
                if is_rate_limit:
                    return AIMessage(
                        content=(
                            "⚠️ **Rate Limit Reached** — All AI models are temporarily at capacity. "
                            "This typically resets within 1 minute (per-minute limit) or up to "
                            "40 minutes (daily quota). Please try again shortly."
                        )
                    )
                return AIMessage(
                    content=f"❌ **Error** — The AI encountered an issue: `{exc}`. Please try again."
                )

        if recorder:
            async with recorder.timed("responder", "node_exec"):
                response = await _invoke()
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                recorder.record_usage(
                    response.usage_metadata.get("input_tokens", 0),
                    response.usage_metadata.get("output_tokens", 0),
                )
        else:
            response = await _invoke()

        return {"messages": [response]}

    responder_node.__name__ = "responder_node"
    return responder_node


def make_fact_extraction_node(llm):
    """Factory: build the fact extraction node."""
    extractor = llm.with_structured_output(FactExtractionOutput)

    async def fact_extraction_node(
        state: AgentState, config: RunnableConfig | None = None, *, store=None
    ) -> dict:
        config = config or {}
        recorder = config.get("configurable", {}).get("step_recorder")
        user_id = config.get("configurable", {}).get("user_id", "anonymous")

        messages = [SystemMessage(content=FACT_EXTRACTION_SYSTEM_PROMPT)] + list(
            state["messages"][-6:]
        )

        async def _invoke():
            try:
                return await extractor.ainvoke(messages, config=config)
            except Exception:
                return FactExtractionOutput(should_remember=False)

        if recorder:
            async with recorder.timed("fact_extraction", "node_exec"):
                result = await _invoke()
        else:
            result = await _invoke()

        if (
            isinstance(result, FactExtractionOutput)
            and result.should_remember
            and result.key
            and result.value
            and store
            and user_id != "anonymous"
        ):
            try:
                if hasattr(store, "aput"):
                    await store.aput((str(user_id), "facts"), result.key, {"value": result.value})
                elif hasattr(store, "put"):
                    store.put((str(user_id), "facts"), result.key, {"value": result.value})
                logger.info("fact_extracted", user_id=user_id, key=result.key, value=result.value)
            except Exception as exc:
                logger.warning("fact_save_failed", exc=str(exc))

        return {}

    fact_extraction_node.__name__ = "fact_extraction_node"
    return fact_extraction_node
