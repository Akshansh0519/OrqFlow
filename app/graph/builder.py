"""
app/graph/builder.py — LangGraph supervisor graph construction.

Graph topology:
  START → supervisor
  supervisor → researcher | analyst | coder | END
  researcher → supervisor
  analyst    → supervisor
  coder      → supervisor

The graph is built once (build_graph) and compiled in app/main.py lifespan
with the real checkpointer and store injected at compile time.

Why compile in lifespan, not here?
  build_graph() returns an uncompiled StateGraph so tests can compile it
  with a MemorySaver and InMemoryStore without needing Redis or Postgres.
  The lifespan then compiles the production graph with the real backends.

interview_answer: "How does the supervisor know which node to go to?"
  "supervisor_node returns a Command(goto=next_node). LangGraph reads the
  goto field and transitions to that node. The graph has conditional edges
  declared in build_graph(), but the routing is fully data-driven — the LLM
  decides, the Command carries the decision, and LangGraph executes it."
"""

from __future__ import annotations

from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph

from app.config import settings
from app.graph.fallback import FallbackLLM
from app.graph.nodes import (
    make_fact_extraction_node,
    make_responder_node,
    make_specialist_node,
    make_supervisor_node,
)
from app.graph.prompts import (
    ANALYST_SYSTEM_PROMPT,
    CODER_SYSTEM_PROMPT,
    RESEARCHER_SYSTEM_PROMPT,
)
from app.graph.state import AgentState


def build_graph(
    agent_tools: dict[str, list],
    supervisor_llm=None,
    worker_llm=None,
) -> StateGraph:
    """
    Build and return an uncompiled LangGraph StateGraph.

    Args:
        agent_tools:    dict with keys "researcher", "analyst", "coder",
                        each a list of LangChain BaseTool objects.
                        Provided by app/graph/tools.py::load_agent_tools().
        supervisor_llm: Optional override for the router LLM (for testing).
                        Defaults to ChatGroq(ROUTER_LLM_MODEL).
        worker_llm:     Optional override for specialist LLMs (for testing).
                        Defaults to ChatGroq(WORKER_LLM_MODEL).

    Returns:
        An uncompiled StateGraph. Caller must call .compile(checkpointer=..., store=...)
        before using it. See app/main.py lifespan for the production compile.
    """
    # ── LLMs ─────────────────────────────────────────────────────────────────
    if supervisor_llm is None:
        groq_router = ChatGroq(
            model=settings.ROUTER_LLM_MODEL,
            api_key=settings.GROQ_API_KEY,
            temperature=0,
        )
        groq_router_fast = ChatGroq(
            model="llama-3.1-8b-instant",
            api_key=settings.GROQ_API_KEY,
            temperature=0,
        )
        gemini_router = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            api_key=settings.GOOGLE_API_KEY,
            temperature=0,
        )
        gemini_router_15 = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            api_key=settings.GOOGLE_API_KEY,
            temperature=0,
        )
        supervisor_llm = FallbackLLM(
            primary=groq_router,
            fallback=groq_router_fast,
            primary_name="Groq (llama-3.3-70b)",
            fallback_name="Groq (llama-3.1-8b)",
            additional_fallbacks=[
                ("Google Gemini (gemini-2.5-flash)", gemini_router),
                ("Google Gemini (gemini-1.5-flash)", gemini_router_15),
            ],
        )

    if worker_llm is None:
        groq_worker = ChatGroq(
            model=settings.WORKER_LLM_MODEL,
            api_key=settings.GROQ_API_KEY,
            temperature=0,
        )
        groq_worker_fast = ChatGroq(
            model="llama-3.1-8b-instant",
            api_key=settings.GROQ_API_KEY,
            temperature=0,
        )
        gemini_worker = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            api_key=settings.GOOGLE_API_KEY,
            temperature=0,
        )
        gemini_worker_15 = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            api_key=settings.GOOGLE_API_KEY,
            temperature=0,
        )
        worker_llm = FallbackLLM(
            primary=groq_worker,
            fallback=groq_worker_fast,
            primary_name="Groq (llama-3.3-70b)",
            fallback_name="Groq (llama-3.1-8b)",
            additional_fallbacks=[
                ("Google Gemini (gemini-2.5-flash)", gemini_worker),
                ("Google Gemini (gemini-1.5-flash)", gemini_worker_15),
            ],
        )

    # ── Node functions ────────────────────────────────────────────────────────
    supervisor_fn = make_supervisor_node(supervisor_llm)
    researcher_fn = make_specialist_node(
        "researcher",
        worker_llm,
        agent_tools.get("researcher", []),
        RESEARCHER_SYSTEM_PROMPT,
    )
    analyst_fn = make_specialist_node(
        "analyst",
        worker_llm,
        agent_tools.get("analyst", []),
        ANALYST_SYSTEM_PROMPT,
    )
    coder_fn = make_specialist_node(
        "coder",
        worker_llm,
        agent_tools.get("coder", []),
        CODER_SYSTEM_PROMPT,
    )
    responder_fn = make_responder_node(worker_llm)
    extractor_fn = make_fact_extraction_node(worker_llm)

    # ── Graph construction ────────────────────────────────────────────────────
    graph = StateGraph(AgentState)

    graph.add_node("supervisor", supervisor_fn)
    graph.add_node("researcher", researcher_fn)
    graph.add_node("analyst", analyst_fn)
    graph.add_node("coder", coder_fn)
    graph.add_node("responder", responder_fn)
    graph.add_node("fact_extraction", extractor_fn)

    # START → supervisor (every run begins here)
    graph.add_edge(START, "supervisor")

    # Specialist → supervisor (loop back after each specialist completes)
    graph.add_edge("researcher", "supervisor")
    graph.add_edge("analyst", "supervisor")
    graph.add_edge("coder", "supervisor")

    # responder → fact_extraction → END
    graph.add_edge("responder", "fact_extraction")
    graph.add_edge("fact_extraction", END)

    return graph
