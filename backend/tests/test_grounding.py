from app.services.grounding import evidence_grounded

SOURCE = (
    "Valve V-17 was hunting. The jacket temperature rose from 8°C to 17°C for 46 minutes. "
    "Batch ATV-CA-26-0142 was quarantined."
)


def test_exact_quote_is_grounded():
    assert evidence_grounded("Valve V-17 was hunting.", SOURCE)


def test_paraphrase_with_source_numbers_can_be_grounded():
    quote = "jacket temperature rose from 8°C to 17°C for 46 minutes"
    assert evidence_grounded(quote, SOURCE)


def test_number_not_in_the_source_is_rejected():
    quote = "The impurity reached 99.9% because of an unwritten rule in the bay."
    assert not evidence_grounded(quote, SOURCE)


def test_empty_evidence_is_not_grounded():
    assert not evidence_grounded("", SOURCE)
    assert not evidence_grounded("too short", SOURCE)
