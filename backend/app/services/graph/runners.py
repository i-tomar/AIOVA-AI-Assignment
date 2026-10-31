"""LLM calls used by the graph nodes. Chat can re-enter the same functions to redraft one section."""

from __future__ import annotations

import json

from app.ai_schemas import (
    CapaListOut,
    CausesOut,
    EditPlan,
    ExtractedDeviation,
    GapsOut,
    InvestigationOut,
)
from app.services import llm as llm_service
from app.services.graph import prompts

_SOURCE_LIMIT = 18000


def _source_block(source: str, kind: str = "", filename: str = "") -> str:
    header = f"Source kind: {kind or 'text'}."
    if filename:
        header += f" Filename: {filename}."
    body = source if len(source) <= _SOURCE_LIMIT else source[:_SOURCE_LIMIT] + "\n\n[Source truncated.]"
    return f"{header}\n\n{body}"


def _context(payload: dict, limit: int = 12000) -> str:
    text = json.dumps(payload, ensure_ascii=False)
    if len(text) > limit:
        return text[:limit] + "…[truncated]"
    return text


def run_extract(source: str, attempt: int, kind: str = "", filename: str = "") -> ExtractedDeviation:
    extra = ""
    if attempt > 1:
        extra = (
            "\n\nThe previous extraction was empty. Look again for the product, the batch, "
            "and what happened. Quote only the source."
        )
    return llm_service.complete_structured(
        ExtractedDeviation,
        prompts.EXTRACT,
        _source_block(source, kind, filename) + extra,
        node="extract_fields",
        temperature=0.0,
    )


def run_investigation(source: str, extraction: dict, instruction: str = "") -> InvestigationOut:
    human = (
        f"{_source_block(source)}\n\nFacts already extracted:\n{_context(extraction)}\n\n"
        "Draft the 5 Whys and the fishbone from these facts and the source."
    )
    if instruction:
        human += f"\n\nAdditional instruction from the investigator: {instruction}"
    return llm_service.complete_structured(
        InvestigationOut,
        prompts.INVESTIGATE,
        human,
        node="investigate",
        temperature=0.2,
    )


def run_causes(
    source: str,
    extraction: dict,
    investigation: dict,
    instruction: str = "",
) -> CausesOut:
    human = (
        f"{_source_block(source)}\n\nExtracted facts:\n{_context(extraction)}\n\n"
        f"Investigation draft:\n{_context(investigation)}\n\n"
        "Propose root causes and contributing factors. Cite the source in each evidence field."
    )
    if instruction:
        human += f"\n\nAdditional instruction from the investigator: {instruction}"
    return llm_service.complete_structured(
        CausesOut,
        prompts.CAUSES,
        human,
        node="identify_causes",
        temperature=0.2,
        reject=_no_causes,
    )


def _no_causes(result: CausesOut) -> str | None:
    if result.root_causes or result.contributing_factors:
        return None
    return (
        "root_causes and contributing_factors were both empty. "
        "Return at least one item that the source supports."
    )


def run_gaps(source: str, context: dict, instruction: str = "") -> GapsOut:
    human = (
        f"{_source_block(source)}\n\nInvestigation so far:\n{_context(context)}\n\n"
        "List the evidence that is still missing."
    )
    if instruction:
        human += f"\n\nAdditional instruction from the investigator: {instruction}"
    return llm_service.complete_structured(
        GapsOut,
        prompts.GAPS,
        human,
        node="evidence_gaps",
        temperature=0.2,
    )


def run_capa(source: str, context: dict, instruction: str = "") -> CapaListOut:
    human = (
        f"{_source_block(source)}\n\nInvestigation so far:\n{_context(context)}\n\n"
        "Recommend corrective and preventive actions."
    )
    if instruction:
        human += f"\n\nAdditional instruction from the investigator: {instruction}"
    return llm_service.complete_structured(
        CapaListOut,
        prompts.CAPA,
        human,
        node="recommend_capa",
        temperature=0.2,
    )


def run_plan(message: str, history: list[dict], record: dict, source: str) -> EditPlan:
    compact = json.loads(json.dumps(record))
    source_info = compact.get("source") or {}
    if isinstance(source_info, dict):
        source_info["raw_text"] = ""
    compact["conversation"] = []
    turns = []
    for item in history[-6:]:
        role = "Investigator" if item.get("role") == "user" else "Assistant"
        content = str(item.get("content") or "")[:1500]
        turns.append(f"{role}: {content}")
    history_text = "\n".join(turns) if turns else "(no earlier turns)"
    excerpt = source[:12000]
    human = (
        f"Source excerpt:\n{excerpt or '(no source stored)'}\n\n"
        f"Current record JSON:\n{_context(compact, 14000)}\n\n"
        f"Conversation so far:\n{history_text}\n\n"
        f"Investigator message:\n{message}"
    )
    return llm_service.complete_structured(
        EditPlan,
        prompts.PLAN,
        human,
        node="plan_edit",
        temperature=0.1,
    )
