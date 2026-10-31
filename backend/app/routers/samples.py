"""Serve the three demo incidents from the repository `samples/` directory."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import ROOT

router = APIRouter(prefix="/samples", tags=["samples"])

CATALOG = [
    {
        "filename": "DEV-2026-1184_atorvastatin_impurity.pdf",
        "title": "Deviation PDF",
        "blurb": "Atorvastatin calcium batch ATV-CA-26-0142 fails RS-3 and assay after a crystallization temperature excursion.",
        "media_type": "application/pdf",
    },
    {
        "filename": "shift_note_metformin_lod.txt",
        "title": "Shift note",
        "blurb": "A supervisor's note: metformin hydrochloride batch MFH-26-2033 left the tray dryer above the LOD limit.",
        "media_type": "text/plain; charset=utf-8",
    },
    {
        "filename": "email_omeprazole_near_miss.eml",
        "title": "QA email",
        "blurb": "Near miss: methanol was staged for an omeprazole intermediate and caught before the solvent charge.",
        "media_type": "message/rfc822",
    },
]

_BY_NAME = {item["filename"]: item for item in CATALOG}
_DIR = ROOT / "samples"


@router.get("")
def list_samples() -> dict:
    return {"samples": CATALOG}


@router.get("/{filename}")
def get_sample(filename: str) -> FileResponse:
    item = _BY_NAME.get(filename)
    path = _DIR / filename
    if item is None or not path.is_file():
        raise HTTPException(status_code=404, detail="Sample not found.")
    return FileResponse(Path(path), media_type=item["media_type"].split(";")[0], filename=filename)
