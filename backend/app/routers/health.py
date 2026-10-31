from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.db import ping_database

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> JSONResponse:
    settings = get_settings()
    database_ok = ping_database()
    body = {
        "status": "ok" if database_ok else "degraded",
        "database": "ok" if database_ok else "unavailable",
        "model": settings.groq_model,
        "llm_configured": settings.llm_configured,
    }
    return JSONResponse(status_code=200 if database_ok else 503, content=body)
