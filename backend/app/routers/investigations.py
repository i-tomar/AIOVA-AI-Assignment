from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import SaveRequest
from app.services import repository

router = APIRouter(prefix="/investigations", tags=["investigations"])


def _envelope(row) -> dict:
    return {
        "id": row.id,
        "record": repository.to_record(row),
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }


def _summary(row) -> dict:
    return {
        "id": row.id,
        "deviation_number": row.deviation_number,
        "title": row.title,
        "product_name": row.product_name,
        "batch_lot": row.batch_lot,
        "severity": row.severity,
        "status": row.status,
        "updated_at": row.updated_at.isoformat(),
    }


@router.get("")
def list_investigations(db: Session = Depends(get_db)) -> dict:
    return {"investigations": [_summary(row) for row in repository.list_investigations(db)]}


@router.post("")
def create_investigation(body: SaveRequest, db: Session = Depends(get_db)) -> dict:
    row = repository.create_investigation(db, body.record, body.actor)
    return _envelope(row)


@router.get("/{investigation_id}")
def get_investigation(investigation_id: str, db: Session = Depends(get_db)) -> dict:
    return _envelope(repository.get_investigation(db, investigation_id))


@router.put("/{investigation_id}")
def update_investigation(
    investigation_id: str, body: SaveRequest, db: Session = Depends(get_db)
) -> dict:
    row = repository.update_investigation(db, investigation_id, body.record, body.actor)
    return _envelope(row)


@router.delete("/{investigation_id}", status_code=204)
def delete_investigation(investigation_id: str, db: Session = Depends(get_db)) -> None:
    repository.delete_investigation(db, investigation_id)


@router.get("/{investigation_id}/audit")
def investigation_audit(investigation_id: str, db: Session = Depends(get_db)) -> dict:
    events = repository.list_audit(db, investigation_id)
    return {
        "events": [
            {
                "id": event.id,
                "investigation_id": event.investigation_id,
                "created_at": event.created_at.isoformat(),
                "actor": event.actor,
                "action": event.action,
                "summary": event.summary,
                "changes": event.changes,
            }
            for event in events
        ]
    }
