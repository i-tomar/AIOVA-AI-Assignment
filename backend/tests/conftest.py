from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    database = tmp_path / "rca.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{database}")
    monkeypatch.setenv("GROQ_API_KEY", "")
    from app.config import get_settings
    from app.db import reset_engine

    get_settings.cache_clear()
    reset_engine()
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
    reset_engine()
    get_settings.cache_clear()
