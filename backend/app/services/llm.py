"""One helper for structured Groq calls, with a short retry on schema failures."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable

from groq import RateLimitError
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from pydantic import BaseModel

from app.config import get_settings
from app.errors import LLMFailed, LLMNotConfigured

log = logging.getLogger(__name__)

_METHODS = ("function_calling", "json_schema", "json_mode")
_RATE_LIMIT_WAITS = 4
_MAX_RATE_LIMIT_WAIT = 60.0


def complete_structured[T: BaseModel](
    schema: type[T],
    system: str,
    human: str,
    *,
    node: str,
    temperature: float = 0.1,
    reject: Callable[[T], str | None] | None = None,
) -> T:
    """`reject` returns a reason when a schema-valid result is still unusable; the call is then retried."""
    settings = get_settings()
    if not settings.llm_configured:
        raise LLMNotConfigured()

    messages = [SystemMessage(content=system), HumanMessage(content=human)]
    last_error = "The model returned no usable object."
    attempt = 0
    waits = 0
    while attempt < len(_METHODS):
        method = _METHODS[attempt]
        prompt = list(messages)
        if method == "json_mode":
            prompt.append(HumanMessage(content=_json_instruction(schema)))
        try:
            model = ChatGroq(
                model_name=settings.groq_model,
                groq_api_key=settings.groq_api_key,
                temperature=temperature,
                max_tokens=4096,
                max_retries=0,
                request_timeout=90,
            )
            runnable = model.with_structured_output(schema, method=method)
            result = _coerce(schema, runnable.invoke(prompt))
            problem = reject(result) if reject else None
            if problem:
                raise ValueError(problem)
            return result
        except LLMNotConfigured:
            raise
        except RateLimitError as exc:
            if waits >= _RATE_LIMIT_WAITS:
                raise LLMFailed(node, "Groq rate limit reached. Wait a minute and try again.") from exc
            waits += 1
            delay = _retry_after(exc)
            log.warning("rate limited node=%s wait=%.0fs", node, delay)
            time.sleep(delay)
        except Exception as exc:
            last_error = _redact(exc, settings.groq_api_key)
            log.warning("structured output failed node=%s attempt=%s method=%s", node, attempt + 1, method)
            attempt += 1
            messages = [
                SystemMessage(content=system),
                HumanMessage(content=human),
                HumanMessage(
                    content=(
                        "The previous response failed validation "
                        f"({last_error[:700]}). "
                        "Return only data that matches the schema. Use empty strings instead of null. "
                        "Do not invent facts that are not in the source."
                    )
                ),
            ]
    raise LLMFailed(node, last_error[:500])


def _json_instruction(schema: type[BaseModel]) -> str:
    return "Return a single JSON object that matches this JSON schema:\n" + json.dumps(
        schema.model_json_schema(), ensure_ascii=False
    )


def _retry_after(exc: RateLimitError) -> float:
    try:
        seconds = float(exc.response.headers.get("retry-after", ""))
    except (TypeError, ValueError):
        seconds = 10.0
    return min(max(seconds, 1.0), _MAX_RATE_LIMIT_WAIT)


def _coerce[T: BaseModel](schema: type[T], raw: object) -> T:
    if isinstance(raw, schema):
        return raw
    if isinstance(raw, BaseModel):
        return schema.model_validate(raw.model_dump())
    if isinstance(raw, dict):
        return schema.model_validate(raw)
    raise TypeError(f"Expected {schema.__name__}, got {type(raw).__name__}")


def _redact(exc: Exception, secret: str) -> str:
    text = f"{type(exc).__name__}: {exc}"
    if secret:
        text = text.replace(secret, "[redacted]")
    return text
