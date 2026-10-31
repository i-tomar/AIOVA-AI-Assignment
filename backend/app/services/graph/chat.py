"""Chat graph: plan edits, optionally redraft one section, then apply the edits in Python.

The model never writes the stored document directly. `apply_edits` runs the allow-listed
operations and rejects confirms that have no evidence note.
"""

from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.schemas import RCARecord
from app.services.graph import runners
from app.services.operations import apply_operations
from app.services.recordkit import due_date, new_id, refresh_grounding, tracked


class ChatState(TypedDict, total=False):
    message: str
    history: list
    record: dict
    plan: dict
    regen_paths: list
    regen_notes: list
    changed_paths: list
    assistant_message: str


def plan_edit(state: ChatState) -> dict:
    record = state.get("record") or {}
    source = ((record.get("source") or {}).get("raw_text")) or ""
    history = state.get("history") or record.get("conversation") or []
    history_dump = [item if isinstance(item, dict) else item for item in history]
    plan = runners.run_plan(state.get("message") or "", history_dump, record, source)
    return {"plan": plan.model_dump()}


def route_plan(state: ChatState) -> str:
    operations = (state.get("plan") or {}).get("operations") or []
    if any((op.get("op") or "") == "regenerate" for op in operations):
        return "regenerate"
    return "apply_edits"


def regenerate(state: ChatState) -> dict:
    record = dict(state.get("record") or {})
    # Nested lists must be copies so we do not mutate the caller's dict via shared lists.
    record = RCARecord.model_validate(record).model_dump()
    source = ((record.get("source") or {}).get("raw_text")) or ""
    paths: list[str] = []
    notes: list[str] = []
    if len(source.strip()) < 40:
        notes.append("The original source is not on this record, so I could not redraft a section from it.")
        return {"record": record, "regen_paths": paths, "regen_notes": notes}

    extraction = _facts_from_record(record)
    for operation in (state.get("plan") or {}).get("operations") or []:
        if (operation.get("op") or "") != "regenerate":
            continue
        section = (operation.get("section") or "").strip().lower()
        instruction = operation.get("instruction") or ""
        if section == "whys":
            drafted = runners.run_investigation(source, extraction, instruction)
            paths.extend(_replace_whys(record, drafted))
            notes.append("I redrafted the 5 Whys from the source.")
        elif section == "fishbone":
            drafted = runners.run_investigation(source, extraction, instruction or "Focus on the fishbone.")
            paths.extend(_replace_fishbone(record, drafted))
            notes.append("I redrafted the fishbone from the source.")
        elif section == "causes":
            drafted = runners.run_causes(
                source,
                extraction,
                {"whys": record.get("whys"), "fishbone": record.get("fishbone")},
                instruction,
            )
            paths.extend(_replace_causes(record, drafted))
            notes.append("I redrafted the root causes and contributing factors. They remain suggestions.")
        elif section == "gaps":
            drafted = runners.run_gaps(source, _compact_context(record), instruction)
            paths.extend(_replace_gaps(record, drafted))
            notes.append("I redrafted the evidence gaps.")
        elif section == "capa":
            drafted = runners.run_capa(source, _compact_context(record), instruction)
            paths.extend(_replace_capa(record, drafted))
            notes.append("I redrafted the CAPA proposals. They remain suggestions.")
        else:
            notes.append("I can redraft whys, fishbone, causes, gaps, or capa.")
    refresh_grounding(record)
    return {"record": record, "regen_paths": paths, "regen_notes": notes}


def apply_edits(state: ChatState) -> dict:
    record = RCARecord.model_validate(state.get("record") or {}).model_dump()
    plan = state.get("plan") or {}
    structural = [op for op in plan.get("operations") or [] if (op.get("op") or "") != "regenerate"]
    applied = apply_operations(record, structural)
    refresh_grounding(applied.record)
    cleaned = RCARecord.model_validate(applied.record).model_dump()
    paths = list(state.get("regen_paths") or []) + applied.changed_paths
    notes = list(state.get("regen_notes") or []) + applied.notes
    message = (plan.get("assistant_message") or "").strip() or "Done."
    if notes:
        message = message.rstrip() + "\n\n" + " ".join(notes)
    return {"record": cleaned, "changed_paths": paths, "assistant_message": message}


def _facts_from_record(record: dict) -> dict:
    keys = (
        "deviation_number",
        "title",
        "product_name",
        "batch_lot",
        "description",
        "immediate_actions",
        "equipment",
        "process_stage",
    )
    return {key: (record.get(key) or {}).get("value", "") for key in keys}


def _compact_context(record: dict) -> dict:
    return {
        "facts": _facts_from_record(record),
        "whys": record.get("whys") or [],
        "fishbone": record.get("fishbone") or [],
        "root_causes": record.get("root_causes") or [],
        "contributing_factors": record.get("contributing_factors") or [],
        "gaps": record.get("gaps") or [],
    }


def _replace_whys(record: dict, drafted) -> list[str]:
    items = []
    paths = []
    for why in drafted.whys:
        item = {
            "id": new_id("why"),
            "question": why.question,
            "answer": why.answer,
            "evidence": why.evidence,
            "grounded": False,
            "origin": "ai",
            "confirmed": False,
        }
        items.append(item)
        paths.append(f"why:{item['id']}")
    record["whys"] = items
    if drafted.problem_statement:
        record["problem_statement"] = tracked(drafted.problem_statement)
        paths.append("problem_statement")
    return paths


def _replace_fishbone(record: dict, drafted) -> list[str]:
    items = []
    paths = []
    for bone in drafted.fishbone:
        item = {
            "id": new_id("fish"),
            "category": bone.category,
            "cause": bone.cause,
            "evidence": bone.evidence,
            "plausible": bone.plausible,
            "grounded": False,
            "origin": "ai",
            "confirmed": False,
        }
        items.append(item)
        paths.append(f"fish:{item['id']}")
    record["fishbone"] = items
    return paths


def _replace_causes(record: dict, drafted) -> list[str]:
    paths = []
    roots = []
    for cause in drafted.root_causes:
        item = _cause_item(cause, "cause")
        roots.append(item)
        paths.append(f"cause:{item['id']}")
    factors = []
    for cause in drafted.contributing_factors:
        item = _cause_item(cause, "factor")
        factors.append(item)
        paths.append(f"factor:{item['id']}")
    record["root_causes"] = roots
    record["contributing_factors"] = factors
    return paths


def _cause_item(cause, prefix: str) -> dict:
    return {
        "id": new_id(prefix),
        "statement": cause.statement,
        "category": cause.category,
        "evidence": cause.evidence,
        "confidence": cause.confidence,
        "evidence_supported": False,
        "grounded": False,
        "ai_suggested": True,
        "confirmed": False,
        "confirmed_by": "",
    }


def _replace_gaps(record: dict, drafted) -> list[str]:
    items = []
    paths = []
    for gap in drafted.gaps:
        item = {
            "id": new_id("gap"),
            "topic": gap.topic,
            "why_it_matters": gap.why_it_matters,
            "suggested_source": gap.suggested_source,
            "origin": "ai",
            "resolved": False,
        }
        items.append(item)
        paths.append(f"gap:{item['id']}")
    record["gaps"] = items
    return paths


def _replace_capa(record: dict, drafted) -> list[str]:
    items = []
    paths = []
    for capa in drafted.capas:
        item = {
            "id": new_id("capa"),
            "capa_type": capa.capa_type,
            "description": capa.description,
            "rationale": capa.rationale,
            "owner": capa.owner_role,
            "due_date": due_date(capa.due_in_days),
            "effectiveness_check": capa.effectiveness_check,
            "status": "proposed",
            "ai_suggested": True,
            "confirmed": False,
        }
        items.append(item)
        paths.append(f"capa:{item['id']}")
    record["capas"] = items
    return paths


def build_chat_graph():
    builder = StateGraph(ChatState)
    builder.add_node("plan_edit", plan_edit)
    builder.add_node("regenerate", regenerate)
    builder.add_node("apply_edits", apply_edits)
    builder.add_edge(START, "plan_edit")
    builder.add_conditional_edges(
        "plan_edit",
        route_plan,
        {"regenerate": "regenerate", "apply_edits": "apply_edits"},
    )
    builder.add_edge("regenerate", "apply_edits")
    builder.add_edge("apply_edits", END)
    return builder.compile()


_graph = None


def get_chat_graph():
    global _graph
    if _graph is None:
        _graph = build_chat_graph()
    return _graph


def run_chat(message: str, history: list[dict], record: dict) -> dict:
    final = get_chat_graph().invoke(
        {"message": message, "history": history, "record": record},
        config={"recursion_limit": 12},
    )
    return {
        "record": final["record"],
        "changed_paths": final.get("changed_paths") or [],
        "assistant_message": final.get("assistant_message") or "",
    }
