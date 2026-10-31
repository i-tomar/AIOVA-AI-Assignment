"""Save and reload investigations. The JSON document is the record; columns feed the library list."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.errors import AppError
from app.models import AuditEvent, Investigation
from app.schemas import RCARecord
from app.services.audit import diff_documents
from app.services.recordkit import refresh_grounding


def create_investigation(db: Session, record: RCARecord, actor: str) -> Investigation:
    stored = _prepare(record)
    now = _now()
    row = Investigation(
        id=str(uuid.uuid4()),
        document=stored,
        created_at=now,
        updated_at=now,
        **_columns(stored),
    )
    db.add(row)
    db.flush()
    db.add(_event(row.id, actor, "create", "Investigation created", [], now))
    db.commit()
    db.refresh(row)
    return row


def update_investigation(db: Session, investigation_id: str, record: RCARecord, actor: str) -> Investigation:
    row = get_investigation(db, investigation_id)
    stored = _prepare(record)
    changes = diff_documents(row.document, stored)
    status_changed = row.status != stored["status"]
    summary = "Investigation updated"
    if status_changed:
        summary = f"Status set to {stored['status']}"
    row.document = stored
    row.updated_at = _now()
    for key, value in _columns(stored).items():
        setattr(row, key, value)
    db.add(
        _event(
            row.id,
            actor,
            "status" if status_changed else "update",
            summary,
            changes,
            row.updated_at,
        )
    )
    db.commit()
    db.refresh(row)
    return row


def list_investigations(db: Session, limit: int = 100) -> list[Investigation]:
    return list(
        db.scalars(select(Investigation).order_by(Investigation.updated_at.desc()).limit(limit)).all()
    )


def get_investigation(db: Session, investigation_id: str) -> Investigation:
    row = db.get(Investigation, investigation_id)
    if row is None:
        raise AppError("Investigation not found.", "not_found", 404)
    return row


def delete_investigation(db: Session, investigation_id: str) -> None:
    row = get_investigation(db, investigation_id)
    db.execute(delete(AuditEvent).where(AuditEvent.investigation_id == row.id))
    db.delete(row)
    db.commit()


def list_audit(db: Session, investigation_id: str) -> list[AuditEvent]:
    get_investigation(db, investigation_id)
    return list(
        db.scalars(
            select(AuditEvent)
            .where(AuditEvent.investigation_id == investigation_id)
            .order_by(AuditEvent.id.asc())
        ).all()
    )


def to_record(row: Investigation) -> dict:
    return RCARecord.model_validate(row.document).model_dump()


def _prepare(record: RCARecord) -> dict:
    document = record.model_dump()
    refresh_grounding(document)
    _enforce_approval(document)
    return RCARecord.model_validate(document).model_dump()


def _enforce_approval(document: dict) -> None:
    if document.get("status") != "approved":
        return
    approval = document.get("approval") or {}
    if not str(approval.get("reviewer_name") or "").strip():
        raise AppError(
            "A reviewer name is required before the investigation can be approved.",
            "approval_incomplete",
            422,
        )
    if not approval.get("acknowledged_ai_review"):
        raise AppError(
            "QA must acknowledge review of the AI suggestions before approval.",
            "approval_incomplete",
            422,
        )
    for label, collection in (("root cause", "root_causes"), ("contributing factor", "contributing_factors")):
        for index, cause in enumerate(document.get(collection) or [], start=1):
            if cause.get("confirmed") and not str(cause.get("evidence") or "").strip():
                raise AppError(
                    f"Confirmed {label} {index} needs an evidence note before approval.",
                    "cause_evidence",
                    422,
                )
    approval["decision"] = "approved"
    if not str(approval.get("signed_at") or "").strip():
        approval["signed_at"] = _now().isoformat()
    document["approval"] = approval


def _columns(document: dict) -> dict:
    def value(key: str, limit: int) -> str:
        field = document.get(key) or {}
        text = field.get("value") if isinstance(field, dict) else ""
        return str(text or "")[:limit]

    return {
        "deviation_number": value("deviation_number", 80),
        "title": value("title", 400),
        "product_name": value("product_name", 240),
        "batch_lot": value("batch_lot", 120),
        "severity": value("severity", 20) or "unknown",
        "status": str(document.get("status") or "draft")[:40],
    }


def _event(investigation_id: str, actor: str, action: str, summary: str, changes: list, when: datetime) -> AuditEvent:
    return AuditEvent(
        investigation_id=investigation_id,
        created_at=when,
        actor=(actor or "investigator")[:160],
        action=action,
        summary=summary,
        changes=changes,
    )


def _now() -> datetime:
    return datetime.now(UTC)
