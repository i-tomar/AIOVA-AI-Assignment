"""The investigation document stored in Postgres and edited in the browser."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


class TrackedStr(BaseModel):
    """A scalar the assistant may fill. `confirmed` means a person accepted the value."""

    value: str = ""
    origin: str = "empty"  # empty | ai | user
    confirmed: bool = False


class TeamMember(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("team"))
    name: str = ""
    role: str = ""
    department: str = ""
    origin: str = "ai"
    confirmed: bool = False


class WhyStep(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("why"))
    question: str = ""
    answer: str = ""
    evidence: str = ""
    grounded: bool = False
    origin: str = "ai"
    confirmed: bool = False


class FishItemRecord(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("fish"))
    category: str = "Method"
    cause: str = ""
    evidence: str = ""
    plausible: bool = True
    grounded: bool = False
    origin: str = "ai"
    confirmed: bool = False


class CauseRecord(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("cause"))
    statement: str = ""
    category: str = "Other"
    evidence: str = ""
    confidence: str = "low"
    evidence_supported: bool = False
    grounded: bool = False
    ai_suggested: bool = True
    confirmed: bool = False
    confirmed_by: str = ""


class GapRecord(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("gap"))
    topic: str = ""
    why_it_matters: str = ""
    suggested_source: str = ""
    origin: str = "ai"
    resolved: bool = False


class CapaRecord(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("capa"))
    capa_type: str = "corrective"
    description: str = ""
    rationale: str = ""
    owner: str = ""
    due_date: str = ""
    effectiveness_check: str = ""
    status: str = "proposed"
    ai_suggested: bool = True
    confirmed: bool = False


class Approval(BaseModel):
    reviewer_name: str = ""
    reviewer_role: str = "Quality Assurance"
    decision: str = ""
    comment: str = ""
    acknowledged_ai_review: bool = False
    signed_at: str = ""


class SourceInfo(BaseModel):
    kind: str = ""
    filename: str = ""
    subject: str = ""
    sender: str = ""
    raw_text: str = ""


class ConversationMessage(BaseModel):
    role: str = "assistant"
    content: str = ""
    at: str = ""


class RCARecord(BaseModel):
    """Full RCA form. JSON keys match the React state so the client stores the API document."""

    model_config = ConfigDict(extra="ignore")

    deviation_number: TrackedStr = Field(default_factory=TrackedStr)
    title: TrackedStr = Field(default_factory=TrackedStr)
    occurred_at: TrackedStr = Field(default_factory=TrackedStr)
    detected_at: TrackedStr = Field(default_factory=TrackedStr)
    site: TrackedStr = Field(default_factory=TrackedStr)
    area: TrackedStr = Field(default_factory=TrackedStr)
    equipment: TrackedStr = Field(default_factory=TrackedStr)
    product_name: TrackedStr = Field(default_factory=TrackedStr)
    batch_lot: TrackedStr = Field(default_factory=TrackedStr)
    process_stage: TrackedStr = Field(default_factory=TrackedStr)
    description: TrackedStr = Field(default_factory=TrackedStr)
    immediate_actions: TrackedStr = Field(default_factory=TrackedStr)
    impact_product_quality: TrackedStr = Field(default_factory=TrackedStr)
    impact_patient_safety: TrackedStr = Field(default_factory=TrackedStr)
    impact_regulatory: TrackedStr = Field(default_factory=TrackedStr)
    batch_disposition: TrackedStr = Field(default_factory=TrackedStr)
    severity: TrackedStr = Field(default_factory=TrackedStr)
    severity_rationale: TrackedStr = Field(default_factory=TrackedStr)
    prepared_by: TrackedStr = Field(default_factory=TrackedStr)
    method: TrackedStr = Field(default_factory=TrackedStr)
    method_notes: TrackedStr = Field(default_factory=TrackedStr)
    problem_statement: TrackedStr = Field(default_factory=TrackedStr)
    team: list[TeamMember] = Field(default_factory=list)
    whys: list[WhyStep] = Field(default_factory=list)
    fishbone: list[FishItemRecord] = Field(default_factory=list)
    root_causes: list[CauseRecord] = Field(default_factory=list)
    contributing_factors: list[CauseRecord] = Field(default_factory=list)
    gaps: list[GapRecord] = Field(default_factory=list)
    capas: list[CapaRecord] = Field(default_factory=list)
    approval: Approval = Field(default_factory=Approval)
    status: str = "draft"
    source: SourceInfo = Field(default_factory=SourceInfo)
    ai_summary: str = ""
    conversation: list[ConversationMessage] = Field(default_factory=list)


class IngestResponse(BaseModel):
    source_text: str
    source_kind: str
    filename: str = ""
    subject: str = ""
    sender: str = ""
    characters: int


class AnalyzeRequest(BaseModel):
    source_text: str
    source_kind: str = "text"
    filename: str = ""
    subject: str = ""
    sender: str = ""


class AnalyzeResponse(BaseModel):
    record: RCARecord
    changed_paths: list[str]
    assistant_message: str


class ChatRequest(BaseModel):
    message: str
    history: list[ConversationMessage] = Field(default_factory=list)
    record: RCARecord


class SaveRequest(BaseModel):
    record: RCARecord
    actor: str = "investigator"


class InvestigationEnvelope(BaseModel):
    id: str
    record: RCARecord
    created_at: str
    updated_at: str


class InvestigationSummary(BaseModel):
    id: str
    deviation_number: str
    title: str
    product_name: str
    batch_lot: str
    severity: str
    status: str
    updated_at: str


class AuditEventOut(BaseModel):
    id: int
    investigation_id: str
    created_at: str
    actor: str
    action: str
    summary: str
    changes: list


class HealthResponse(BaseModel):
    status: str
    database: str
    model: str
    llm_configured: bool


class SampleInfo(BaseModel):
    filename: str
    title: str
    blurb: str
    media_type: str
