from __future__ import annotations

from fastapi import APIRouter, File, Form, UploadFile

from app.services.text_extract import ingest_source

router = APIRouter(tags=["ingest"])


@router.post("/ingest")
async def ingest(
    file: UploadFile | None = File(default=None),
    text: str = Form(default=""),
    kind: str = Form(default=""),
) -> dict:
    data = await file.read() if file is not None else b""
    filename = file.filename if file is not None else ""
    result = ingest_source(data, filename or "", text, kind)
    return {
        "source_text": result.source_text,
        "source_kind": result.source_kind,
        "filename": result.filename,
        "subject": result.subject,
        "sender": result.sender,
        "characters": result.characters,
    }
