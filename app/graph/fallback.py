"""
app/graph/fallback.py — Automatic fallback wrapper for LLMs with user notification.

Fixes applied:
  - Bug 2: Removed over-broad _should_fallback keywords ("tool", "parse", "json",
    "validation", "invalid") that were causing unnecessary 4-model cascades on
    normal structured-output parse errors.
  - Bug 7: ainvoke() now emits a model_switch custom LangGraph event so the SSE
    layer can surface a user-visible notification when models switch.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

import structlog
from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable

logger = structlog.get_logger(__name__)


class FallbackLLM(Runnable):
    """
    Wraps a primary LLM and fallback LLMs. If the primary fails due to rate limit (429)
    or quota errors, automatically logs and iterates through fallback models sequentially.
    """

    def __init__(
        self,
        primary: Runnable,
        fallback: Runnable,
        primary_name: str = "Groq",
        fallback_name: str = "Google Gemini",
        additional_fallbacks: list[tuple[str, Runnable]] | None = None,
    ):
        self.primary = primary
        self.fallback = fallback
        self.primary_name = primary_name
        self.fallback_name = fallback_name
        self.additional_fallbacks = additional_fallbacks or []
        self.chain = [
            (primary_name, primary),
            (fallback_name, fallback),
        ] + self.additional_fallbacks

    def _should_fallback(self, exc: Exception) -> bool:
        """
        Only fallback for rate limits, quotas, or server downtime.

        Bug 2 fix: Removed over-broad keywords "tool", "parse", "json",
        "validation", "invalid" that were triggering unnecessary fallback
        cascades on normal structured-output parsing errors. These should
        propagate as real errors, not trigger model switching.
        """
        err_str = str(exc).lower()
        trigger_keywords = [
            "429",
            "rate limit",
            "rate_limit_exceeded",
            "503",
            "500",
            "502",
            "504",
            "quota",
            "overloaded",
            "timeout",
            "failed to call",
            "failed_generation",
            "tokens per minute",
            "tokens per day",
        ]
        return any(kw in err_str for kw in trigger_keywords)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.primary, name)

    def bind_tools(self, tools: Any, **kwargs: Any) -> FallbackLLM:
        return FallbackLLM(
            self.primary.bind_tools(tools, **kwargs),
            self.fallback.bind_tools(tools, **kwargs),
            self.primary_name,
            self.fallback_name,
            additional_fallbacks=[
                (name, m.bind_tools(tools, **kwargs)) for name, m in self.additional_fallbacks
            ],
        )

    def with_structured_output(self, schema: Any, **kwargs: Any) -> FallbackLLM:
        return FallbackLLM(
            self.primary.with_structured_output(schema, **kwargs),
            self.fallback.with_structured_output(schema, **kwargs),
            self.primary_name,
            self.fallback_name,
            additional_fallbacks=[
                (name, m.with_structured_output(schema, **kwargs))
                for name, m in self.additional_fallbacks
            ],
        )

    async def ainvoke(self, input: Any, config: Any = None, **kwargs: Any) -> Any:
        """
        Bug 7 fix: Emits a model_switch custom LangGraph event when falling back,
        so the SSE layer can surface a user-visible notification.
        """
        for i, (name, model) in enumerate(self.chain):
            try:
                return await model.ainvoke(input, config=config, **kwargs)
            except Exception as exc:
                if not self._should_fallback(exc) or i == len(self.chain) - 1:
                    raise

                next_name = self.chain[i + 1][0]
                logger.warning(
                    "Primary LLM failed, switching to fallback",
                    primary=name,
                    fallback=next_name,
                    error=str(exc),
                )

                # Bug 7: Emit a LangGraph custom event so agent_router can
                # yield a model_switch SSE event to the frontend.
                try:
                    from langchain_core.callbacks.manager import adispatch_custom_event

                    await adispatch_custom_event(
                        "model_switch",
                        {
                            "event_type": "model_switch",
                            "from_model": name,
                            "to_model": next_name,
                            "reason": "rate_limit"
                            if "429" in str(exc).lower() or "rate" in str(exc).lower()
                            else "error",
                        },
                        config=config,
                    )
                except Exception:
                    pass  # Notification is best-effort; never block the fallback

    def invoke(self, input: Any, config: Any = None, **kwargs: Any) -> Any:
        for i, (name, model) in enumerate(self.chain):
            try:
                return model.invoke(input, config=config, **kwargs)
            except Exception as exc:
                if not self._should_fallback(exc) or i == len(self.chain) - 1:
                    raise

                next_name = self.chain[i + 1][0]
                logger.warning(
                    "Primary LLM failed, switching to fallback",
                    primary=name,
                    fallback=next_name,
                    error=str(exc),
                )

    async def astream(
        self, input: Any, config: Any = None, **kwargs: Any
    ) -> AsyncGenerator[Any, None]:
        for i, (name, model) in enumerate(self.chain):
            try:
                async for chunk in model.astream(input, config=config, **kwargs):
                    yield chunk
                return
            except Exception as exc:
                if not self._should_fallback(exc) or i == len(self.chain) - 1:
                    raise

                next_name = self.chain[i + 1][0]
                logger.warning(
                    "Primary LLM stream failed, switching to fallback",
                    primary=name,
                    fallback=next_name,
                    error=str(exc),
                )
                notice_msg = (
                    AIMessage(
                        content=f"\n\n> ⚡ **Model Switch:** Rate limit on `{name}`. Switched to `{next_name}`.\n\n",
                        name="responder",
                    ),
                    {"langgraph_node": "responder"},
                )
                yield notice_msg
