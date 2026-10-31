from app.schemas import RCARecord
from app.services.operations import apply_operations


def _record() -> dict:
    record = RCARecord().model_dump()
    record["root_causes"] = [
        {
            "id": "cause_1",
            "statement": "Valve hunting",
            "category": "Machine",
            "evidence": "",
            "confidence": "low",
            "evidence_supported": False,
            "grounded": False,
            "ai_suggested": True,
            "confirmed": False,
            "confirmed_by": "",
        }
    ]
    return record


def test_set_batch_marks_the_field_as_a_user_edit():
    result = apply_operations(_record(), [{"op": "set", "path": "batch_lot", "value": "ATV-CA-26-0999"}])
    field = result.record["batch_lot"]
    assert field["value"] == "ATV-CA-26-0999"
    assert field["origin"] == "user"
    assert field["confirmed"] is True
    assert "batch_lot" in result.changed_paths


def test_unknown_path_is_rejected():
    result = apply_operations(_record(), [{"op": "set", "path": "password", "value": "nope"}])
    assert result.changed_paths == []
    assert result.notes


def test_confirm_without_evidence_is_rejected():
    result = apply_operations(
        _record(),
        [{"op": "confirm", "collection": "root_causes", "index": 0, "confirmed": True}],
    )
    assert result.record["root_causes"][0]["confirmed"] is False
    assert "evidence" in result.notes[0].lower()


def test_confirm_with_evidence_sticks():
    record = _record()
    record["root_causes"][0]["evidence"] = "Valve V-17 was hunting."
    result = apply_operations(
        record,
        [{"op": "confirm", "collection": "root_causes", "index": 0, "confirmed": True}],
    )
    cause = result.record["root_causes"][0]
    assert cause["confirmed"] is True
    assert cause["evidence_supported"] is True


def test_chat_cannot_approve():
    result = apply_operations(_record(), [{"op": "set", "path": "status", "value": "approved"}])
    assert result.record["status"] == "draft"
    assert result.notes


def test_append_why_stays_unconfirmed():
    result = apply_operations(
        _record(),
        [{"op": "append_why", "question": "Why?", "answer": "Because the valve hunted.", "evidence": "V-17"}],
    )
    why = result.record["whys"][0]
    assert why["origin"] == "ai"
    assert why["confirmed"] is False
    assert result.changed_paths[0].startswith("why:")
