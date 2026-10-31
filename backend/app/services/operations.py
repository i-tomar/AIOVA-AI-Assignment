"""Apply a chat plan to the RCA document.

The model proposes operations. This module is the only thing that mutates the record,
so a bad path or a confirm-without-evidence is rejected in plain language.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from app.services.recordkit import coerce_due_date, new_id
from app.vocab import (
    CHAT_STATUSES,
    norm_capa_status,
    norm_capa_type,
    norm_category,
    norm_confidence,
    norm_fish_category,
    norm_severity,
    norm_status,
)

TRACKED_PATHS = {
    "deviation_number",
    "title",
    "occurred_at",
    "detected_at",
    "site",
    "area",
    "equipment",
    "product_name",
    "batch_lot",
    "process_stage",
    "description",
    "immediate_actions",
    "impact_product_quality",
    "impact_patient_safety",
    "impact_regulatory",
    "batch_disposition",
    "severity",
    "severity_rationale",
    "prepared_by",
    "method",
    "method_notes",
    "problem_statement",
}

COLLECTIONS = {
    "whys",
    "fishbone",
    "root_causes",
    "contributing_factors",
    "gaps",
    "capas",
    "team",
}

ITEM_FIELDS = {
    "whys": {"question", "answer", "evidence"},
    "fishbone": {"cause", "evidence", "category"},
    "root_causes": {"statement", "evidence", "category", "confidence"},
    "contributing_factors": {"statement", "evidence", "category", "confidence"},
    "gaps": {"topic", "why_it_matters", "suggested_source"},
    "capas": {
        "description",
        "rationale",
        "owner",
        "due_date",
        "effectiveness_check",
        "capa_type",
        "status",
    },
    "team": {"name", "role", "department"},
}

CONFIRMABLE = {"whys", "fishbone", "root_causes", "contributing_factors", "capas"}


@dataclass
class ApplyResult:
    record: dict
    changed_paths: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def apply_operations(record: dict, operations: list[dict]) -> ApplyResult:
    result = ApplyResult(record=record)
    for operation in operations[:8]:
        op = (operation.get("op") or "").strip()
        handler = _HANDLERS.get(op)
        if handler is None:
            if op and op != "regenerate":
                result.notes.append(f"I skipped an unknown edit '{op}'.")
            continue
        handler(result, operation)
    return result


def _set_field(result: ApplyResult, operation: dict) -> None:
    path = (operation.get("path") or "").strip()
    value = str(operation.get("value") or "").strip()[:4000]
    record = result.record
    if path == "status":
        status = norm_status(value)
        if status == "approved" or status not in CHAT_STATUSES:
            result.notes.append(
                "Approval is signed in the review section by a named reviewer, so I did not set the status to approved."
            )
            return
        record["status"] = status
        result.changed_paths.append("status")
        return
    if path.startswith("approval."):
        key = path.split(".", 1)[1]
        approval = record.setdefault("approval", {})
        if key == "acknowledged_ai_review":
            approval[key] = value.lower() in {"true", "yes", "1"}
        elif key in {"reviewer_name", "reviewer_role", "comment", "decision"}:
            approval[key] = value[:1000]
        else:
            result.notes.append(f"I cannot set '{path}'.")
            return
        result.changed_paths.append(path)
        return
    if path not in TRACKED_PATHS:
        result.notes.append(f"I cannot set '{path or 'that field'}' from chat.")
        return
    if path == "severity":
        value = norm_severity(value)
    current = record.get(path)
    if not isinstance(current, dict):
        result.notes.append(f"I cannot set '{path}'.")
        return
    current["value"] = value
    current["origin"] = "user"
    current["confirmed"] = True
    result.changed_paths.append(path)


def _append_why(result: ApplyResult, operation: dict) -> None:
    question = str(operation.get("question") or "").strip()
    answer = str(operation.get("answer") or "").strip()
    if not question and not answer:
        result.notes.append("I did not add a why because the question and answer were empty.")
        return
    item = {
        "id": new_id("why"),
        "question": question or "Why?",
        "answer": answer,
        "evidence": str(operation.get("evidence") or "").strip(),
        "grounded": False,
        "origin": "ai",
        "confirmed": False,
    }
    result.record.setdefault("whys", []).append(item)
    result.changed_paths.append(f"why:{item['id']}")


def _add_fishbone(result: ApplyResult, operation: dict) -> None:
    cause = str(operation.get("statement") or operation.get("answer") or "").strip()
    if not cause:
        result.notes.append("I did not add a fishbone cause because the text was empty.")
        return
    item = {
        "id": new_id("fish"),
        "category": norm_fish_category(str(operation.get("category") or "")),
        "cause": cause,
        "evidence": str(operation.get("evidence") or "").strip(),
        "plausible": True,
        "grounded": False,
        "origin": "ai",
        "confirmed": False,
    }
    result.record.setdefault("fishbone", []).append(item)
    result.changed_paths.append(f"fish:{item['id']}")


def _add_cause(result: ApplyResult, operation: dict, collection: str, prefix: str) -> None:
    statement = str(operation.get("statement") or "").strip()
    if not statement:
        result.notes.append("I did not add a cause because the statement was empty.")
        return
    evidence = str(operation.get("evidence") or "").strip()
    item = {
        "id": new_id(prefix),
        "statement": statement,
        "category": norm_category(str(operation.get("category") or "")),
        "evidence": evidence,
        "confidence": norm_confidence(str(operation.get("confidence") or "low")) if evidence else "low",
        "evidence_supported": False,
        "grounded": False,
        "ai_suggested": True,
        "confirmed": False,
        "confirmed_by": "",
    }
    result.record.setdefault(collection, []).append(item)
    kind = "cause" if collection == "root_causes" else "factor"
    result.changed_paths.append(f"{kind}:{item['id']}")


def _add_root(result: ApplyResult, operation: dict) -> None:
    _add_cause(result, operation, "root_causes", "cause")


def _add_factor(result: ApplyResult, operation: dict) -> None:
    _add_cause(result, operation, "contributing_factors", "factor")


def _add_gap(result: ApplyResult, operation: dict) -> None:
    topic = str(operation.get("topic") or "").strip()
    if not topic:
        result.notes.append("I did not add a gap because the topic was empty.")
        return
    item = {
        "id": new_id("gap"),
        "topic": topic,
        "why_it_matters": str(operation.get("why_it_matters") or "").strip(),
        "suggested_source": str(operation.get("suggested_source") or "").strip(),
        "origin": "ai",
        "resolved": False,
    }
    result.record.setdefault("gaps", []).append(item)
    result.changed_paths.append(f"gap:{item['id']}")


def _add_capa(result: ApplyResult, operation: dict) -> None:
    description = str(operation.get("description") or "").strip()
    if not description:
        result.notes.append("I did not add a CAPA because the description was empty.")
        return
    capa_type = norm_capa_type(str(operation.get("capa_type") or "corrective"))
    fallback = 30 if capa_type == "preventive" else 14
    item = {
        "id": new_id("capa"),
        "capa_type": capa_type,
        "description": description,
        "rationale": str(operation.get("rationale") or "").strip(),
        "owner": str(operation.get("owner") or "").strip(),
        "due_date": coerce_due_date(str(operation.get("due_date") or ""), fallback),
        "effectiveness_check": str(operation.get("effectiveness_check") or "").strip(),
        "status": "proposed",
        "ai_suggested": True,
        "confirmed": False,
    }
    result.record.setdefault("capas", []).append(item)
    result.changed_paths.append(f"capa:{item['id']}")


def _add_team(result: ApplyResult, operation: dict) -> None:
    name = str(operation.get("name") or operation.get("statement") or "").strip()
    if not name:
        result.notes.append("I did not add a team member because the name was empty.")
        return
    item = {
        "id": new_id("team"),
        "name": name,
        "role": str(operation.get("role") or operation.get("category") or "").strip(),
        "department": str(operation.get("department") or operation.get("owner") or "").strip(),
        "origin": "ai",
        "confirmed": False,
    }
    result.record.setdefault("team", []).append(item)
    result.changed_paths.append("team")


def _remove(result: ApplyResult, operation: dict) -> None:
    collection = (operation.get("collection") or "").strip()
    index = operation.get("index")
    items = result.record.get(collection)
    if collection not in COLLECTIONS or not isinstance(items, list):
        result.notes.append(f"I cannot remove from '{collection or 'that list'}'.")
        return
    if not isinstance(index, int) or index < 0 or index >= len(items):
        result.notes.append(f"There is no item {index} in {collection}.")
        return
    items.pop(index)
    result.changed_paths.append(collection)


def _confirm(result: ApplyResult, operation: dict) -> None:
    collection = (operation.get("collection") or "").strip()
    index = operation.get("index")
    items = result.record.get(collection)
    if collection not in CONFIRMABLE or not isinstance(items, list):
        result.notes.append(f"I cannot confirm an item in '{collection or 'that list'}'.")
        return
    if not isinstance(index, int) or index < 0 or index >= len(items):
        result.notes.append(f"There is no item {index} in {collection}.")
        return
    item = items[index]
    confirmed = bool(operation.get("confirmed", True))
    evidence = str(item.get("evidence") or item.get("rationale") or "").strip()
    if confirmed and collection in {"root_causes", "contributing_factors", "whys", "fishbone"} and not evidence:
        result.notes.append(
            f"I did not confirm {collection.replace('_', ' ')} {index + 1} because it has no evidence note."
        )
        return
    item["confirmed"] = confirmed
    if "confirmed_by" in item:
        reviewer = ((result.record.get("prepared_by") or {}).get("value")) or "qualified reviewer"
        item["confirmed_by"] = reviewer if confirmed else ""
    if confirmed and "evidence_supported" in item and evidence:
        item["evidence_supported"] = True
    prefix = {
        "whys": "why",
        "fishbone": "fish",
        "root_causes": "cause",
        "contributing_factors": "factor",
        "capas": "capa",
    }[collection]
    result.changed_paths.append(f"{prefix}:{item.get('id', index)}")


def _update_item(result: ApplyResult, operation: dict) -> None:
    collection = (operation.get("collection") or "").strip()
    index = operation.get("index")
    items = result.record.get(collection)
    allowed = ITEM_FIELDS.get(collection)
    if not allowed or not isinstance(items, list):
        result.notes.append(f"I cannot update '{collection or 'that list'}'.")
        return
    if not isinstance(index, int) or index < 0 or index >= len(items):
        result.notes.append(f"There is no item {index} in {collection}.")
        return
    raw = operation.get("fields_json") or ""
    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        result.notes.append("I could not read the field update (it was not JSON).")
        return
    if not isinstance(payload, dict) or not payload:
        result.notes.append("The field update was empty.")
        return
    item = items[index]
    wrote = False
    for key, value in payload.items():
        if key not in allowed:
            continue
        text = str(value).strip()[:4000]
        if key == "category":
            text = norm_fish_category(text) if collection == "fishbone" else norm_category(text)
        elif key == "confidence":
            text = norm_confidence(text)
        elif key == "capa_type":
            text = norm_capa_type(text)
        elif key == "status":
            text = norm_capa_status(text)
        elif key == "due_date":
            text = coerce_due_date(text, 30)
        item[key] = text
        wrote = True
    if not wrote:
        result.notes.append("None of the requested fields can be edited on that item.")
        return
    if item.get("origin") == "ai" and collection in {"whys", "fishbone", "team"}:
        item["origin"] = "user"
    if "confirmed" in item and "statement" in payload:
        item["confirmed"] = False
    result.changed_paths.append(collection)


def _noop_regenerate(result: ApplyResult, operation: dict) -> None:
    """Regenerate is handled by the chat graph before this function runs."""
    section = operation.get("section") or "that section"
    result.notes.append(f"Redraft of {section} was requested.")


_HANDLERS = {
    "set": _set_field,
    "append_why": _append_why,
    "add_fishbone": _add_fishbone,
    "add_root_cause": _add_root,
    "add_factor": _add_factor,
    "add_gap": _add_gap,
    "add_capa": _add_capa,
    "add_team": _add_team,
    "remove": _remove,
    "confirm": _confirm,
    "update_item": _update_item,
    "regenerate": _noop_regenerate,
}

