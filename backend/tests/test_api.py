from app.schemas import RCARecord
from tests.fakes import SOURCE, install


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["database"] == "ok"
    assert body["llm_configured"] is False


def test_analyze_without_a_key_is_503(client):
    response = client.post("/api/ai/analyze", json={"source_text": SOURCE, "source_kind": "text"})
    assert response.status_code == 503
    assert response.json()["code"] == "llm_not_configured"


def test_analyze_with_a_scripted_model(client, monkeypatch):
    install(monkeypatch)
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    from app.config import get_settings

    get_settings.cache_clear()
    response = client.post("/api/ai/analyze", json={"source_text": SOURCE, "source_kind": "text"})
    assert response.status_code == 200
    body = response.json()
    assert body["record"]["deviation_number"]["value"] == "DEV-2026-1184"
    assert any(path.startswith("cause:") for path in body["changed_paths"])


def test_stream_emits_nodes_then_a_record(client, monkeypatch):
    install(monkeypatch)
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    from app.config import get_settings

    get_settings.cache_clear()
    response = client.post("/api/ai/analyze/stream", json={"source_text": SOURCE, "source_kind": "text"})
    assert response.status_code == 200
    text = response.text
    assert "event: phase" in text
    assert "extract_fields" in text
    assert "recommend_capa" in text
    assert "event: result" in text


def test_ingest_shift_note(client):
    note = ( __import__("pathlib").Path(__file__).resolve().parents[2] / "samples" / "shift_note_metformin_lod.txt").read_text(encoding="utf-8")
    response = client.post("/api/ingest", data={"text": note})
    assert response.status_code == 200
    body = response.json()
    assert body["source_kind"] == "text"
    assert "TD-12" in body["source_text"]


def test_save_reload_and_audit(client):
    record = RCARecord().model_dump()
    record["title"] = {"value": "LOD failure on drying", "origin": "user", "confirmed": True}
    record["deviation_number"] = {"value": "DEV-TEST-1", "origin": "user", "confirmed": True}
    record["product_name"] = {"value": "Metformin hydrochloride", "origin": "user", "confirmed": True}
    record["batch_lot"] = {"value": "MFH-26-2033", "origin": "user", "confirmed": True}
    record["severity"] = {"value": "major", "origin": "user", "confirmed": True}
    record["status"] = "under_investigation"
    created = client.post("/api/investigations", json={"record": record, "actor": "A. Iyer"})
    assert created.status_code == 200
    envelope = created.json()
    investigation_id = envelope["id"]
    assert envelope["record"]["batch_lot"]["value"] == "MFH-26-2033"

    record = envelope["record"]
    record["batch_lot"]["value"] = "MFH-26-2033-R"
    updated = client.put(
        f"/api/investigations/{investigation_id}",
        json={"record": record, "actor": "A. Iyer"},
    )
    assert updated.status_code == 200
    assert updated.json()["record"]["batch_lot"]["value"] == "MFH-26-2033-R"

    listing = client.get("/api/investigations")
    assert listing.status_code == 200
    ids = [item["id"] for item in listing.json()["investigations"]]
    assert investigation_id in ids

    audit = client.get(f"/api/investigations/{investigation_id}/audit")
    assert audit.status_code == 200
    events = audit.json()["events"]
    assert [event["action"] for event in events] == ["create", "update"]
    assert events[0]["actor"] == "A. Iyer"
    assert any(change["path"] == "batch_lot.value" for change in events[1]["changes"])

    reloaded = client.get(f"/api/investigations/{investigation_id}")
    assert reloaded.status_code == 200
    assert reloaded.json()["record"]["title"]["value"] == "LOD failure on drying"

    deleted = client.delete(f"/api/investigations/{investigation_id}")
    assert deleted.status_code == 204
    missing = client.get(f"/api/investigations/{investigation_id}")
    assert missing.status_code == 404


def test_approval_requires_acknowledgement(client):
    record = RCARecord().model_dump()
    record["status"] = "approved"
    record["approval"]["reviewer_name"] = "K. Shah"
    response = client.post("/api/investigations", json={"record": record, "actor": "K. Shah"})
    assert response.status_code == 422
    assert response.json()["code"] == "approval_incomplete"


def test_approval_with_signoff_persists(client):
    record = RCARecord().model_dump()
    record["status"] = "approved"
    record["approval"]["reviewer_name"] = "K. Shah"
    record["approval"]["acknowledged_ai_review"] = True
    record["root_causes"] = [
        {
            "id": "cause_ok",
            "statement": "Damper left partly closed.",
            "category": "Machine",
            "evidence": "Damper found at 40% open.",
            "confidence": "medium",
            "evidence_supported": True,
            "grounded": False,
            "ai_suggested": True,
            "confirmed": True,
            "confirmed_by": "K. Shah",
        }
    ]
    response = client.post("/api/investigations", json={"record": record, "actor": "K. Shah"})
    assert response.status_code == 200
    body = response.json()
    assert body["record"]["status"] == "approved"
    assert body["record"]["approval"]["signed_at"]
    assert body["record"]["approval"]["decision"] == "approved"


def test_samples_list(client):
    response = client.get("/api/samples")
    assert response.status_code == 200
    names = [item["filename"] for item in response.json()["samples"]]
    assert "shift_note_metformin_lod.txt" in names
    fetched = client.get("/api/samples/shift_note_metformin_lod.txt")
    assert fetched.status_code == 200
    assert b"MFH-26-2033" in fetched.content
