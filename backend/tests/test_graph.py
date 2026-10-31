from app.services.graph.analyze import run_analysis
from app.services.graph.chat import run_chat
from tests.fakes import SOURCE, install


def test_analysis_marks_suggestions_and_grounds_evidence(monkeypatch):
    install(monkeypatch)
    result = run_analysis(SOURCE, "text", "note.txt", "", "")
    record = result["record"]
    assert record["batch_lot"]["value"] == "ATV-CA-26-0142"
    assert record["batch_lot"]["origin"] == "ai"
    assert record["batch_lot"]["confirmed"] is False
    assert record["status"] == "under_investigation"
    assert record["whys"]
    assert record["whys"][0]["grounded"] is True
    assert record["fishbone"][0]["category"] == "Machine"
    grounded = [cause for cause in record["root_causes"] if cause["grounded"]]
    ungrounded = [cause for cause in record["root_causes"] if not cause["grounded"]]
    assert grounded and ungrounded
    assert all(cause["ai_suggested"] and not cause["confirmed"] for cause in record["root_causes"])
    assert all(cause["confidence"] == "low" for cause in ungrounded)
    assert record["capas"]
    assert {item["capa_type"] for item in record["capas"]} >= {"corrective", "preventive"}
    assert "AI suggested" in result["assistant_message"] or "hypothesis" in result["assistant_message"]
    assert result["changed_paths"]


def test_extraction_retries_once_when_the_first_pass_is_empty(monkeypatch):
    calls = install(monkeypatch, fail_extract_once=True)
    result = run_analysis(SOURCE, "text", "", "", "")
    assert calls["extract_fields"] == 2
    assert result["record"]["product_name"]["value"] == "Atorvastatin calcium"


def test_chat_applies_a_field_edit(monkeypatch):
    install(monkeypatch)
    from app.schemas import RCARecord

    record = RCARecord().model_dump()
    record["source"]["raw_text"] = SOURCE
    result = run_chat("Set the batch number to ATV-CA-26-0999.", [], record)
    assert result["record"]["batch_lot"]["value"] == "ATV-CA-26-0999"
    assert result["record"]["batch_lot"]["origin"] == "user"
    assert "batch_lot" in result["changed_paths"]
    assert "ATV-CA-26-0999" in result["assistant_message"] or "batch" in result["assistant_message"].lower()
