"""Analysis and chat. Both call a LangGraph workflow and return the updated record."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.errors import AppError
from app.schemas import AnalyzeRequest, ChatRequest
from app.services.graph.analyze import run_analysis, stream_analysis
from app.services.graph.chat import run_chat

log = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["ai"])


def _require_source(text: str) -> str:
    cleaned = (text or "").strip()
    if len(cleaned) < 40:
        raise AppError(
            "Provide a longer incident narrative before analysis (at least a short paragraph).",
            "source_too_short",
            422,
        )
    return cleaned


@router.post("/analyze")
def analyze(body: AnalyzeRequest) -> dict:
    source = _require_source(body.source_text)
    try:
        return run_analysis(source, body.source_kind, body.filename, body.subject, body.sender)
    except AppError:
        raise
    except Exception as exc:
        log.exception("analyze failed")
        raise AppError("Analysis failed before the record could be filled.", "analyze_failed", 500) from exc


@router.post("/analyze/stream")
def analyze_stream(body: AnalyzeRequest) -> StreamingResponse:
    source = _require_source(body.source_text)

    def events():
        try:
            for event, payload in stream_analysis(
                source, body.source_kind, body.filename, body.subject, body.sender
            ):
                yield _sse(event, payload)
        except AppError as exc:
            yield _sse("error", {"detail": exc.message, "code": exc.code})
        except Exception:
            log.exception("analyze stream failed")
            yield _sse(
                "error",
                {
                    "detail": "Analysis failed before the record could be filled.",
                    "code": "analyze_failed",
                },
            )

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/chat")
def chat(body: ChatRequest) -> dict:
    message = (body.message or "").strip()
    if not message:
        raise AppError("Enter a message for the assistant.", "empty_message", 422)
    if len(message) > 4000:
        raise AppError("Messages are limited to 4,000 characters.", "message_too_long", 422)
    history = [item.model_dump() for item in body.history]
    record = body.record.model_dump()
    try:
        return run_chat(message, history, record)
    except AppError:
        raise
    except Exception as exc:
        log.exception("chat failed")
        raise AppError("The assistant could not apply that request.", "chat_failed", 500) from exc


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
