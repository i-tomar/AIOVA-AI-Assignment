"""Merge the five model outputs into one RCA record and mark every fill as AI-suggested."""

from __future__ import annotations

from app.ai_schemas import (
    CapaListOut,
    CausesOut,
    ExtractedDeviation,
    GapsOut,
    InvestigationOut,
)
from app.services.recordkit import due_date, new_id, refresh_grounding, tracked
from app.vocab import norm_severity

_TRACKED_FROM_EXTRACT = (
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
)


def assemble_record(state: dict) -> tuple[dict, list[str], str]:
    extraction = ExtractedDeviation.model_validate(state.get("extraction") or {})
    investigation = InvestigationOut.model_validate(state.get("investigation") or {})
    causes = CausesOut.model_validate(state.get("causes") or {})
    gaps = GapsOut.model_validate(state.get("gaps") or {})
    capa = CapaListOut.model_validate(state.get("capa") or {})
    source_text = state.get("source_text") or ""

    record = {
        "deviation_number": tracked(""),
        "title": tracked(""),
        "occurred_at": tracked(""),
        "detected_at": tracked(""),
        "site": tracked(""),
        "area": tracked(""),
        "equipment": tracked(""),
        "product_name": tracked(""),
        "batch_lot": tracked(""),
        "process_stage": tracked(""),
        "description": tracked(""),
        "immediate_actions": tracked(""),
        "impact_product_quality": tracked(""),
        "impact_patient_safety": tracked(""),
        "impact_regulatory": tracked(""),
        "batch_disposition": tracked(""),
        "severity": tracked(""),
        "severity_rationale": tracked(""),
        "prepared_by": tracked(""),
        "method": tracked("5 Whys and Ishikawa fishbone (6M)"),
        "method_notes": tracked(investigation.method_summary or extraction.method_notes),
        "problem_statement": tracked(investigation.problem_statement),
        "team": [],
        "whys": [],
        "fishbone": [],
        "root_causes": [],
        "contributing_factors": [],
        "gaps": [],
        "capas": [],
        "approval": {
            "reviewer_name": "",
            "reviewer_role": "Quality Assurance",
            "decision": "",
            "comment": "",
            "acknowledged_ai_review": False,
            "signed_at": "",
        },
        "status": "under_investigation",
        "source": {
            "kind": state.get("source_kind") or "",
            "filename": state.get("filename") or "",
            "subject": state.get("subject") or "",
            "sender": state.get("sender") or "",
            "raw_text": source_text,
        },
        "ai_summary": "",
        "conversation": [],
    }

    for key in _TRACKED_FROM_EXTRACT:
        record[key] = tracked(getattr(extraction, key))

    severity = norm_severity(extraction.severity)
    record["severity"] = tracked(severity)
    record["severity_rationale"] = tracked(extraction.severity_rationale)

    for member in extraction.investigation_team:
        record["team"].append(
            {
                "id": new_id("team"),
                "name": member.name,
                "role": member.role,
                "department": member.department,
                "origin": "ai",
                "confirmed": False,
            }
        )

    for why in investigation.whys:
        record["whys"].append(
            {
                "id": new_id("why"),
                "question": why.question,
                "answer": why.answer,
                "evidence": why.evidence,
                "grounded": False,
                "origin": "ai",
                "confirmed": False,
            }
        )

    for bone in investigation.fishbone:
        record["fishbone"].append(
            {
                "id": new_id("fish"),
                "category": bone.category,
                "cause": bone.cause,
                "evidence": bone.evidence,
                "plausible": bone.plausible,
                "grounded": False,
                "origin": "ai",
                "confirmed": False,
            }
        )

    for cause in causes.root_causes:
        record["root_causes"].append(_cause_dict(cause, "cause"))
    for factor in causes.contributing_factors:
        record["contributing_factors"].append(_cause_dict(factor, "factor"))

    for gap in gaps.gaps:
        record["gaps"].append(_gap_dict(gap.topic, gap.why_it_matters, gap.suggested_source))

    _ensure_gap(
        record,
        not extraction.deviation_number,
        "Deviation number not assigned",
        "The quality system needs a controlled deviation number before this record can be filed.",
        "QA deviation log",
    )
    _ensure_gap(
        record,
        not extraction.batch_lot,
        "Batch or lot number missing",
        "Disposition and the batch record cannot be tied to this event without the lot identity.",
        "Batch manufacturing record",
    )
    _ensure_gap(
        record,
        not extraction.product_name,
        "Product identity missing",
        "The investigation has to name the API before impact and CAPA can be scoped.",
        "Batch record or production schedule",
    )
    _ensure_gap(
        record,
        not extraction.occurred_at and not extraction.detected_at,
        "Timing of the event is incomplete",
        "Occurrence and detection times decide the investigation window and who was on shift.",
        "Shift log and equipment historian",
    )
    if state.get("truncation_note"):
        _ensure_gap(
            record,
            True,
            "Source text was truncated",
            state["truncation_note"],
            "The original file, read in full by the investigator",
        )

    for item in capa.capas:
        record["capas"].append(
            {
                "id": new_id("capa"),
                "capa_type": item.capa_type,
                "description": item.description,
                "rationale": item.rationale,
                "owner": item.owner_role,
                "due_date": due_date(item.due_in_days),
                "effectiveness_check": item.effectiveness_check,
                "status": "proposed",
                "ai_suggested": True,
                "confirmed": False,
            }
        )

    refresh_grounding(record)
    message = _summary(record, capa.summary)
    record["ai_summary"] = message
    return record, _changed_paths(record), message


def _cause_dict(cause, prefix: str) -> dict:
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


def _gap_dict(topic: str, why: str, suggested: str) -> dict:
    return {
        "id": new_id("gap"),
        "topic": topic,
        "why_it_matters": why,
        "suggested_source": suggested,
        "origin": "ai",
        "resolved": False,
    }


def _ensure_gap(record: dict, needed: bool, topic: str, why: str, suggested: str) -> None:
    if not needed:
        return
    folded = topic.lower()
    for gap in record["gaps"]:
        if folded in gap["topic"].lower() or gap["topic"].lower() in folded:
            return
    record["gaps"].insert(0, _gap_dict(topic, why, suggested))


def _changed_paths(record: dict) -> list[str]:
    paths: list[str] = []
    for key, value in record.items():
        if isinstance(value, dict) and value.get("origin") == "ai" and value.get("value"):
            paths.append(key)
    if record["team"]:
        paths.append("team")
    for why in record["whys"]:
        paths.append(f"why:{why['id']}")
    for bone in record["fishbone"]:
        paths.append(f"fish:{bone['id']}")
    for cause in record["root_causes"]:
        paths.append(f"cause:{cause['id']}")
    for factor in record["contributing_factors"]:
        paths.append(f"factor:{factor['id']}")
    for gap in record["gaps"]:
        paths.append(f"gap:{gap['id']}")
    for item in record["capas"]:
        paths.append(f"capa:{item['id']}")
    return paths


def _count(count: int, singular: str, plural: str | None = None) -> str:
    word = singular if count == 1 else (plural or f"{singular}s")
    return f"{count} {word}"


def _summary(record: dict, capa_summary: str) -> str:
    product = record["product_name"]["value"] or "the material in the source"
    batch = record["batch_lot"]["value"]
    batch_bit = f", batch {batch}" if batch else ""
    kind = record["source"]["kind"] or "source"
    severity = record["severity"]["value"] or "unknown"
    causes = record["root_causes"]
    supported = sum(1 for cause in causes if cause.get("grounded"))
    lines = [
        f"I read the {kind} and drafted the deviation record for {product}{batch_bit}.",
        f"Suggested classification: {severity}.",
        (
            f"The draft has {_count(len(record['whys']), 'why-step')}, "
            f"{_count(len(record['fishbone']), 'fishbone item')}, "
            f"{_count(len(causes), 'root-cause hypothesis', 'root-cause hypotheses')} "
            f"({supported} citing evidence found in the source), "
            f"{_count(len(record['contributing_factors']), 'contributing factor')}, "
            f"{_count(len(record['gaps']), 'evidence gap')}, and "
            f"{_count(len(record['capas']), 'CAPA proposal')}."
        ),
        "Anything marked AI suggested stays a hypothesis until a qualified person confirms it.",
    ]
    if capa_summary:
        lines.append(capa_summary)
    return " ".join(lines)
