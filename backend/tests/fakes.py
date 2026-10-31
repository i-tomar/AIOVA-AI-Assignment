"""Scripted model responses for the analysis graph. No network."""

from __future__ import annotations

from app.ai_schemas import (
    CapaItemOut,
    CapaListOut,
    CauseOut,
    CausesOut,
    EditOperation,
    EditPlan,
    ExtractedDeviation,
    FishItem,
    GapOut,
    GapsOut,
    InvestigationOut,
    TeamExtract,
    WhyItem,
)

SOURCE = (
    "Deviation DEV-2026-1184. Product atorvastatin calcium batch ATV-CA-26-0142. "
    "Related substance RS-3 was 0.18% against NMT 0.15%. Assay was 98.2%. "
    "The jacket temperature rose from 8°C to 17°C for 46 minutes. Valve V-17 was hunting. "
    "The batch was quarantined and has not been shipped."
)


def responses(node: str, calls: dict[str, int]):
    calls[node] = calls.get(node, 0) + 1
    if node == "extract_fields":
        if calls[node] == 1 and calls.get("fail_extract_once"):
            return ExtractedDeviation()
        return ExtractedDeviation(
            deviation_number="DEV-2026-1184",
            title="RS-3 and assay OOS after a crystallization excursion",
            occurred_at="12 March 2026, 14:40 IST",
            detected_at="14 March 2026, 09:15 IST",
            site="Northline API Works, Hyderabad",
            area="Crystallization bay 2",
            equipment="Crystallizer CR-300, valve V-17",
            product_name="Atorvastatin calcium",
            batch_lot="ATV-CA-26-0142",
            process_stage="Final crystallization",
            description=(
                "RS-3 was 0.18% against NMT 0.15% and assay was 98.2% on batch ATV-CA-26-0142. "
                "The batch was quarantined and has not been shipped."
            ),
            immediate_actions="Batch quarantined. Crystallizer tagged out of service.",
            impact_product_quality="Two release tests are out of specification.",
            impact_patient_safety="No patient exposure is identified in the source.",
            impact_regulatory="The batch was planned for EU CEP supply.",
            batch_disposition="Quarantine",
            severity="major",
            severity_rationale="Specification failure on a batch that remains under quarantine.",
            investigation_team=[TeamExtract(name="R. Menon", role="Operator", department="Production")],
        )
    if node == "investigate":
        return InvestigationOut(
            method_summary="5 Whys follows the temperature excursion; the fishbone checks the other categories.",
            problem_statement="Batch ATV-CA-26-0142 failed the RS-3 specification.",
            whys=[
                WhyItem(
                    question="Why was RS-3 above the limit?",
                    answer="The crystallizer jacket rose from 8°C to 17°C for 46 minutes.",
                    evidence="jacket temperature rose from 8°C to 17°C for 46 minutes",
                )
            ],
            fishbone=[
                FishItem(
                    category="Machine",
                    cause="Cooling-water valve V-17 was hunting",
                    evidence="Valve V-17 was hunting",
                    plausible=True,
                )
            ],
        )
    if node == "identify_causes":
        return CausesOut(
            root_causes=[
                CauseOut(
                    statement="Loss of crystallization temperature control while valve V-17 was hunting.",
                    category="Machine",
                    evidence="Valve V-17 was hunting and the jacket rose to 17°C for 46 minutes",
                    confidence="high",
                ),
                CauseOut(
                    statement="An unstated night-shift policy caused the impurity.",
                    category="Method",
                    evidence="The impurity reached 99.9% because of an unwritten rule.",
                    confidence="high",
                ),
            ],
            contributing_factors=[
                CauseOut(
                    statement="The batch remained in the crystallizer during the excursion.",
                    category="Method",
                    evidence="The batch was quarantined and has not been shipped.",
                    confidence="low",
                )
            ],
        )
    if node == "evidence_gaps":
        return GapsOut(
            gaps=[
                GapOut(
                    topic="DCS audit trail for the alarm",
                    why_it_matters="The record does not say who suppressed the alarm.",
                    suggested_source="DCS audit trail",
                )
            ]
        )
    if node == "recommend_capa":
        return CapaListOut(
            summary="Repair the cooling loop and stop unapproved alarm suppression.",
            capas=[
                CapaItemOut(
                    capa_type="corrective",
                    description="Repair valve V-17 and return CR-300 to service only after an engineering check.",
                    rationale="The excursion is tied to V-17 hunting.",
                    owner_role="Engineering — utilities",
                    due_in_days=14,
                    effectiveness_check="Jacket temperature stays within 3°C of setpoint on the next two batches.",
                ),
                CapaItemOut(
                    capa_type="preventive",
                    description="Require QA approval and a time limit before a differential-pressure alarm can be suppressed.",
                    rationale="The alarm was left suppressed across a batch.",
                    owner_role="QA operations",
                    due_in_days=30,
                    effectiveness_check="Alarm-suppression log shows no open suppression older than the approved window.",
                ),
            ],
        )
    if node == "plan_edit":
        return EditPlan(
            assistant_message="I set the batch number to the value you gave.",
            operations=[EditOperation(op="set", path="batch_lot", value="ATV-CA-26-0999")],
        )
    raise AssertionError(f"unexpected node {node}")


def install(monkeypatch, *, fail_extract_once: bool = False):
    calls: dict[str, int] = {}
    if fail_extract_once:
        calls["fail_extract_once"] = 1

    def fake(schema, system, human, *, node, temperature=0.1, reject=None):  # noqa: ARG001
        return responses(node, calls)

    monkeypatch.setattr("app.services.llm.complete_structured", fake)
    return calls
