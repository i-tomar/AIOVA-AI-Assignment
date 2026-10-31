"""FastAPI entrypoint for the Northline RCA module."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.db import init_db
from app.errors import AppError
from app.routers import ai, health, ingest, investigations, samples

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    init_db()
    log.info(
        "RCA API ready model=%s llm_configured=%s",
        settings.groq_model,
        settings.llm_configured,
    )
    yield


app = FastAPI(
    title="Northline RCA",
    summary="AI-assisted root cause analysis for API manufacturing deviations.",
    version="1.0.0",
    lifespan=lifespan,
)

_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
def handle_app_error(_request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status, content={"detail": exc.message, "code": exc.code})


app.include_router(health.router, prefix="/api")
app.include_router(ingest.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(investigations.router, prefix="/api")
app.include_router(samples.router, prefix="/api")
