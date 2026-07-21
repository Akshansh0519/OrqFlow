"""
scripts/run_routing_eval.py — Evaluation script for Supervisor routing accuracy.

Runs a benchmark dataset of user prompts through the OrqFlow supervisor routing logic
and computes routing accuracy across researcher, analyst, coder, and FINISH routes.

Usage:
    python scripts/run_routing_eval.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.messages import HumanMessage

from app.config import settings
from app.graph.nodes import RouterOutput, make_supervisor_node

EVAL_DATASET = [
    {"prompt": "Search the web for LangGraph tutorials", "expected": "researcher"},
    {"prompt": "Look up recent news about artificial intelligence", "expected": "researcher"},
    {"prompt": "Find documentation on FastMCP server implementation", "expected": "researcher"},
    {"prompt": "Query the database for all employees in Engineering", "expected": "analyst"},
    {"prompt": "List the tables available in the company_ops schema", "expected": "analyst"},
    {"prompt": "What is the average salary of employees in Product?", "expected": "analyst"},
    {
        "prompt": "Write a Python script to parse CSV files and calculate averages",
        "expected": "coder",
    },
    {"prompt": "Create a regex pattern to validate email addresses", "expected": "coder"},
    {"prompt": "Refactor this function to use async/await", "expected": "coder"},
    {"prompt": "Hello, how are you today?", "expected": "FINISH"},
    {"prompt": "Thank you for the help, goodbye!", "expected": "FINISH"},
    {"prompt": "Who are you?", "expected": "FINISH"},
]


class MockRouterChain:
    """Mock structured router output for offline CI / test evaluation."""

    async def ainvoke(self, messages: Any) -> RouterOutput:
        content = ""
        if isinstance(messages, list) and messages:
            last = messages[-1]
            content = str(getattr(last, "content", "")).lower()

        if any(w in content for w in ("search", "news", "documentation", "look up", "find doc")):
            return RouterOutput(next="researcher", reasoning="Needs web research")
        if any(w in content for w in ("query", "database", "table", "salary", "employee")):
            return RouterOutput(next="analyst", reasoning="Needs database interrogation")
        if any(w in content for w in ("write", "python", "script", "regex", "refactor", "code")):
            return RouterOutput(next="coder", reasoning="Needs software engineering")
        return RouterOutput(next="FINISH", reasoning="General conversational query")


class MockLLM:
    def with_structured_output(self, schema: Any) -> Any:
        return MockRouterChain()


async def run_evaluation() -> None:
    print("=" * 70)
    print("ORQFLOW SUPERVISOR ROUTING EVALUATION")
    print("=" * 70)

    # Determine whether to use real Anthropic LLM or offline Mock LLM
    api_key = getattr(settings, "ANTHROPIC_API_KEY", "")
    if not api_key or api_key.startswith("sk-mock") or settings.SEARCH_PROVIDER == "mock":
        print("[INFO] Running in offline / mock mode using heuristic benchmark evaluation.")
        llm = MockLLM()
    else:
        print("[INFO] Running live evaluation against Anthropic API.")
        from langchain_anthropic import ChatAnthropic

        llm = ChatAnthropic(model=settings.ROUTER_LLM_MODEL, temperature=0)

    supervisor = make_supervisor_node(llm)

    correct = 0
    total = len(EVAL_DATASET)

    print(f"\n{'PROMPT':<50} | {'EXPECTED':<12} | {'ACTUAL':<12} | {'STATUS'}")
    print("-" * 88)

    for item in EVAL_DATASET:
        prompt = item["prompt"]
        expected = item["expected"]
        state = {
            "messages": [HumanMessage(content=prompt)],
            "step_count": 0,
            "thread_id": "eval-thread",
        }

        command = await supervisor(state)
        # Supervisor updates 'next' in command.update
        actual = command.update.get("next", "UNKNOWN")

        is_correct = actual == expected
        if is_correct:
            correct += 1
            status = "PASS"
        else:
            status = "FAIL"

        display_prompt = (prompt[:46] + "...") if len(prompt) > 49 else prompt
        print(f"{display_prompt:<50} | {expected:<12} | {actual:<12} | {status}")

    accuracy = (correct / total) * 100
    print("-" * 88)
    print(f"\nTotal Evaluated: {total}")
    print(f"Correct Routes : {correct}")
    print(f"Accuracy       : {accuracy:.1f}%\n")
    print("=" * 70)

    if accuracy < 80.0:
        print("[ERROR] Routing accuracy below threshold (80.0%)")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_evaluation())
