"""Round-trip against a real Postgres if one is listening. Skips otherwise."""

from __future__ import annotations

import uuid

import pytest

URL = "postgresql+psycopg://rca:rca@127.0.0.1:5432/rca_test"


def _reachable() -> bool:
    try:
        import psycopg

        with psycopg.connect(URL.replace("postgresql+psycopg://", "postgresql://"), connect_timeout=3) as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _reachable(), reason="Postgres rca_test is not available")


@pytest.fixture()
def pg_client(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", URL)
    monkeypatch.setenv("GROQ_API_KEY", "")
    from app.config import get_settings
    from app.db import reset_engine

    get_settings.cache_clear()
    reset_engine()
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
    reset_engine()
    get_settings.cache_clear()


def test_postgres_save_and_reload(pg_client):
    from app.schemas import RCARecord

    marker = f"DEV-PG-{uuid.uuid4().hex[:8]}"
    record = RCARecord().model_dump()
    record["deviation_number"] = {"value": marker, "origin": "user", "confirmed": True}
    record["title"] = {"value": "Postgres round trip", "origin": "user", "confirmed": True}
    record["root_causes"] = [
        {
            "id": "cause_pg",
            "statement": "Hypothesis only.",
            "category": "Method",
            "evidence": "",
            "confidence": "low",
            "evidence_supported": False,
            "grounded": False,
            "ai_suggested": True,
            "confirmed": False,
            "confirmed_by": "",
        }
    ]
    created = pg_client.post("/api/investigations", json={"record": record, "actor": "qa"})
    assert created.status_code == 200
    investigation_id = created.json()["id"]
    try:
        loaded = pg_client.get(f"/api/investigations/{investigation_id}")
        assert loaded.status_code == 200
        cause = loaded.json()["record"]["root_causes"][0]
        assert cause["ai_suggested"] is True
        assert cause["confirmed"] is False
        assert loaded.json()["record"]["deviation_number"]["value"] == marker
    finally:
        pg_client.delete(f"/api/investigations/{investigation_id}")
