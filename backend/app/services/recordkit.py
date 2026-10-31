"""Small constructors shared by the analysis assembler and the chat editor."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

from app.schemas import RCARecord
from app.services.grounding import evidence_grounded


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def tracked(value: str, origin: str = "ai") -> dict:
    text = " ".join((value or "").split())
    if not text:
        return {"value": "", "origin": "empty", "confirmed": False}
    return {"value": text, "origin": origin, "confirmed": False}


def empty_record() -> dict:
    return RCARecord().model_dump()


def due_date(days: int) -> str:
    safe = max(7, min(int(days or 30), 90))
    return (date.today() + timedelta(days=safe)).isoformat()


def coerce_due_date(value: str, fallback_days: int) -> str:
    text = (value or "").strip()
    if len(text) >= 10 and text[4:5] == "-" and text[7:8] == "-":
        return text[:10]
    return due_date(fallback_days)


def refresh_grounding(record: dict) -> None:
    """Re-check evidence notes against the stored source.

    Unconfirmed items that are not grounded are kept as low-confidence hypotheses.
    A confirmed item is left alone: the reviewer may have supplied evidence that
    was not in the original file.
    """
    source = ((record.get("source") or {}).get("raw_text")) or ""
    for why in record.get("whys") or []:
        why["grounded"] = evidence_grounded(why.get("evidence") or "", source)
    for bone in record.get("fishbone") or []:
        bone["grounded"] = evidence_grounded(bone.get("evidence") or "", source)
    for cause in list(record.get("root_causes") or []) + list(record.get("contributing_factors") or []):
        grounded = evidence_grounded(cause.get("evidence") or "", source)
        cause["grounded"] = grounded
        if grounded:
            cause["evidence_supported"] = True
        elif not cause.get("confirmed"):
            cause["evidence_supported"] = False
            cause["confidence"] = "low"
