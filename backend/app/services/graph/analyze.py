"""Analysis graph.

    prepare_source -> extract_fields -> (retry once if the facts are empty) ->
    investigate -> identify_causes -> evidence_gaps -> recommend_capa -> assemble

`prepare_source` and `assemble` are plain Python. The five middle steps each make
one structured model call. `extract_fields` is the only node with a graph-level retry:
if product, batch, title, and description are all empty, it runs a second time.
"""

from __future__ import annotations

import re
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.services.assemble import assemble_record
from app.services.graph import runners


class AnalyzeState(TypedDict, total=False):
    source_text: str
    source_kind: str
    filename: str
    subject: str
    sender: str
    truncation_note: str
    extract_attempts: int
    extraction_valid: bool
    extraction: dict
    investigation: dict
    causes: dict
    gaps: dict
    capa: dict
    record: dict
    changed_paths: list
    assistant_message: str


def prepare_source(state: AnalyzeState) -> dict:
    text = (state.get("source_text") or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    note = ""
    if len(text) > 18000:
        text = text[:18000]
        note = "The source was longer than 18,000 characters and was truncated before analysis."
    return {"source_text": text, "truncation_note": note}


def extract_fields(state: AnalyzeState) -> dict:
    attempts = int(state.get("extract_attempts") or 0) + 1
    extraction = runners.run_extract(
        state.get("source_text") or "",
        attempts,
        state.get("source_kind") or "",
        state.get("filename") or "",
    )
    valid = bool(
        extraction.description or extraction.product_name or extraction.batch_lot or extraction.title
    )
    return {
        "extraction": extraction.model_dump(),
        "extract_attempts": attempts,
        "extraction_valid": valid,
    }


def route_after_extract(state: AnalyzeState) -> str:
    if state.get("extraction_valid"):
        return "investigate"
    if int(state.get("extract_attempts") or 0) >= 2:
        return "investigate"
    return "extract_fields"


def investigate(state: AnalyzeState) -> dict:
    result = runners.run_investigation(state.get("source_text") or "", state.get("extraction") or {})
    return {"investigation": result.model_dump()}


def identify_causes(state: AnalyzeState) -> dict:
    result = runners.run_causes(
        state.get("source_text") or "",
        state.get("extraction") or {},
        state.get("investigation") or {},
    )
    return {"causes": result.model_dump()}


def evidence_gaps(state: AnalyzeState) -> dict:
    context = {
        "extraction": state.get("extraction") or {},
        "investigation": state.get("investigation") or {},
        "causes": state.get("causes") or {},
    }
    result = runners.run_gaps(state.get("source_text") or "", context)
    return {"gaps": result.model_dump()}


def recommend_capa(state: AnalyzeState) -> dict:
    context = {
        "extraction": state.get("extraction") or {},
        "investigation": state.get("investigation") or {},
        "causes": state.get("causes") or {},
        "gaps": state.get("gaps") or {},
    }
    result = runners.run_capa(state.get("source_text") or "", context)
    return {"capa": result.model_dump()}


def assemble(state: AnalyzeState) -> dict:
    record, paths, message = assemble_record(dict(state))
    return {"record": record, "changed_paths": paths, "assistant_message": message}


def build_analyze_graph():
    builder = StateGraph(AnalyzeState)
    builder.add_node("prepare_source", prepare_source)
    builder.add_node("extract_fields", extract_fields)
    builder.add_node("investigate", investigate)
    builder.add_node("identify_causes", identify_causes)
    builder.add_node("evidence_gaps", evidence_gaps)
    builder.add_node("recommend_capa", recommend_capa)
    builder.add_node("assemble", assemble)
    builder.add_edge(START, "prepare_source")
    builder.add_edge("prepare_source", "extract_fields")
    builder.add_conditional_edges(
        "extract_fields",
        route_after_extract,
        {"extract_fields": "extract_fields", "investigate": "investigate"},
    )
    builder.add_edge("investigate", "identify_causes")
    builder.add_edge("identify_causes", "evidence_gaps")
    builder.add_edge("evidence_gaps", "recommend_capa")
    builder.add_edge("recommend_capa", "assemble")
    builder.add_edge("assemble", END)
    return builder.compile()


_graph = None


def get_analyze_graph():
    global _graph
    if _graph is None:
        _graph = build_analyze_graph()
    return _graph


def initial_state(source_text: str, source_kind: str, filename: str, subject: str, sender: str) -> AnalyzeState:
    return {
        "source_text": source_text,
        "source_kind": source_kind,
        "filename": filename,
        "subject": subject,
        "sender": sender,
        "extract_attempts": 0,
    }


def run_analysis(source_text: str, source_kind: str, filename: str, subject: str, sender: str) -> dict:
    final = get_analyze_graph().invoke(
        initial_state(source_text, source_kind, filename, subject, sender),
        config={"recursion_limit": 20},
    )
    return {
        "record": final["record"],
        "changed_paths": final["changed_paths"],
        "assistant_message": final["assistant_message"],
    }


def stream_analysis(source_text: str, source_kind: str, filename: str, subject: str, sender: str):
    """Yield (event, payload) pairs. `phase` events name the node that just finished."""
    graph = get_analyze_graph()
    accumulated: dict = dict(initial_state(source_text, source_kind, filename, subject, sender))
    for chunk in graph.stream(accumulated, stream_mode="updates", config={"recursion_limit": 20}):
        for node, update in chunk.items():
            accumulated.update(update)
            yield "phase", {"node": node}
    yield "result", {
        "record": accumulated["record"],
        "changed_paths": accumulated["changed_paths"],
        "assistant_message": accumulated["assistant_message"],
    }
