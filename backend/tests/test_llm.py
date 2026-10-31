import httpx
import pytest
from groq import RateLimitError

from app.ai_schemas import CausesOut
from app.config import get_settings
from app.errors import LLMFailed
from app.services.graph import runners

CAUSE = {
    "statement": "Valve V-17 hunting let the jacket reach 17 C for 46 minutes.",
    "category": "Machine",
    "evidence": "Jacket at 17 C for 46 minutes; V-17 hunting.",
    "confidence": "high",
}


def _rate_limit(seconds: str) -> RateLimitError:
    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    response = httpx.Response(429, headers={"retry-after": seconds}, request=request)
    return RateLimitError("rate limited", response=response, body=None)


@pytest.fixture()
def scripted(monkeypatch):
    """Replace ChatGroq with a model that replays `script`, one reply per call."""
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    get_settings.cache_clear()
    calls: list[tuple[str, list]] = []
    sleeps: list[float] = []
    script: list = []

    class FakeChat:
        def __init__(self, **kwargs):
            pass

        def with_structured_output(self, schema, method):
            return FakeRunnable(method)

    class FakeRunnable:
        def __init__(self, method):
            self.method = method

        def invoke(self, prompt):
            calls.append((self.method, prompt))
            reply = script.pop(0)
            if isinstance(reply, Exception):
                raise reply
            return reply

    monkeypatch.setattr("app.services.llm.ChatGroq", FakeChat)
    monkeypatch.setattr("app.services.llm.time.sleep", sleeps.append)
    yield script, calls, sleeps
    get_settings.cache_clear()


def test_rate_limit_waits_and_keeps_the_same_method(scripted):
    script, calls, sleeps = scripted
    script += [_rate_limit("3"), CausesOut(root_causes=[CAUSE])]
    result = runners.run_causes("source", {}, {})
    assert len(result.root_causes) == 1
    assert sleeps == [3.0]
    assert [method for method, _ in calls] == ["function_calling", "function_calling"]


def test_empty_causes_are_retried_and_json_mode_gets_the_schema(scripted):
    script, calls, _ = scripted
    script += [CausesOut(), CausesOut(), {"root_causes": [CAUSE]}]
    result = runners.run_causes("source", {}, {})
    assert result.root_causes[0].statement.startswith("Valve V-17")
    assert [method for method, _ in calls] == ["function_calling", "json_schema", "json_mode"]
    retry_note = calls[1][1][-1].content
    assert "both empty" in retry_note
    schema_note = calls[2][1][-1].content
    assert "root_causes" in schema_note and "contributing_factors" in schema_note


def test_empty_causes_fail_instead_of_returning_an_empty_record(scripted):
    script, _, _ = scripted
    script += [CausesOut(), CausesOut(), CausesOut()]
    with pytest.raises(LLMFailed):
        runners.run_causes("source", {}, {})


def test_rate_limit_gives_up_after_a_bounded_wait(scripted):
    script, _, sleeps = scripted
    script += [_rate_limit("90") for _ in range(5)]
    with pytest.raises(LLMFailed, match="rate limit"):
        runners.run_causes("source", {}, {})
    assert sleeps == [60.0] * 4
