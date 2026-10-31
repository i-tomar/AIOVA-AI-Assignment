from pathlib import Path

from app.services.text_extract import ingest_source

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "samples"


def test_shift_note_is_text():
    note = (SAMPLES / "shift_note_metformin_lod.txt").read_text(encoding="utf-8")
    result = ingest_source(b"", "", note, "")
    assert result.source_kind == "text"
    assert "MFH-26-2033" in result.source_text
    assert "0.42%" in result.source_text


def test_sample_email():
    data = (SAMPLES / "email_omeprazole_near_miss.eml").read_bytes()
    result = ingest_source(data, "email_omeprazole_near_miss.eml", "", "")
    assert result.source_kind == "email"
    assert "Priya Raman" in result.sender
    assert "OMP-INT-26-077" in result.source_text
    assert "MD-4418" in result.source_text
    assert "wrong solvent" in result.subject.lower()


def test_sample_pdf_text():
    data = (SAMPLES / "DEV-2026-1184_atorvastatin_impurity.pdf").read_bytes()
    result = ingest_source(data, "DEV-2026-1184_atorvastatin_impurity.pdf", "", "")
    assert result.source_kind == "pdf"
    assert "DEV-2026-1184" in result.source_text
    assert "ATV-CA-26-0142" in result.source_text
    assert "0.18" in result.source_text
    assert "V-17" in result.source_text


def test_empty_upload_is_rejected():
    from app.errors import AppError

    try:
        ingest_source(b"", "", "   ", "")
    except AppError as exc:
        assert exc.code == "empty_source"
    else:
        raise AssertionError("expected AppError")


def test_msg_is_rejected():
    from app.errors import AppError

    try:
        ingest_source(b"not an outlook file", "note.msg", "", "")
    except AppError as exc:
        assert exc.code == "unsupported_type"
    else:
        raise AssertionError("expected AppError")
