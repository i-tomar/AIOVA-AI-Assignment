"""Structured outputs for each LangGraph node.

These are what the model must return. `app.schemas.RCARecord` is what we store.
A node maps one into the other; it does not ask the model to fill the whole record at once.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.vocab import (
    norm_capa_type,
    norm_category,
    norm_confidence,
    norm_fish_category,
    norm_severity,
)


class TextModel(BaseModel):
    @field_validator("*", mode="before")
    @classmethod
    def _strip_strings(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value


class TeamExtract(TextModel):
    name: str = ""
    role: str = ""
    department: str = ""


class ExtractedDeviation(TextModel):
    """Facts stated in the source. Empty string means the source did not say."""

    deviation_number: str = Field(default="", max_length=80)
    title: str = Field(default="", max_length=300)
    occurred_at: str = Field(default="", max_length=120)
    detected_at: str = Field(default="", max_length=120)
    site: str = Field(default="", max_length=200)
    area: str = Field(default="", max_length=200)
    equipment: str = Field(default="", max_length=400)
    product_name: str = Field(default="", max_length=200)
    batch_lot: str = Field(default="", max_length=120)
    process_stage: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=2500)
    immediate_actions: str = Field(default="", max_length=2000)
    impact_product_quality: str = Field(default="", max_length=800)
    impact_patient_safety: str = Field(default="", max_length=800)
    impact_regulatory: str = Field(default="", max_length=800)
    batch_disposition: str = Field(default="", max_length=200)
    severity: str = "unknown"
    severity_rationale: str = Field(default="", max_length=800)
    investigation_team: list[TeamExtract] = Field(default_factory=list)
    method_notes: str = Field(default="", max_length=800)

    @field_validator("severity", mode="before")
    @classmethod
    def _severity(cls, value: str) -> str:
        return norm_severity(str(value or ""))

    @field_validator("investigation_team")
    @classmethod
    def _team_cap(cls, value: list[TeamExtract]) -> list[TeamExtract]:
        return [member for member in value if member.name][:8]


class WhyItem(TextModel):
    question: str = Field(default="", max_length=300)
    answer: str = Field(default="", max_length=800)
    evidence: str = Field(default="", max_length=500)


class FishItem(TextModel):
    category: str = "Method"
    cause: str = Field(default="", max_length=400)
    evidence: str = Field(default="", max_length=500)
    plausible: bool = True

    @field_validator("category", mode="before")
    @classmethod
    def _category(cls, value: str) -> str:
        return norm_fish_category(str(value or ""))


class InvestigationOut(TextModel):
    method_summary: str = Field(default="", max_length=800)
    problem_statement: str = Field(default="", max_length=400)
    whys: list[WhyItem] = Field(default_factory=list)
    fishbone: list[FishItem] = Field(default_factory=list)

    @field_validator("whys")
    @classmethod
    def _whys(cls, value: list[WhyItem]) -> list[WhyItem]:
        return [item for item in value if item.question or item.answer][:6]

    @field_validator("fishbone")
    @classmethod
    def _bones(cls, value: list[FishItem]) -> list[FishItem]:
        return [item for item in value if item.cause][:12]


class CauseOut(TextModel):
    statement: str = Field(default="", max_length=600)
    category: str = "Other"
    evidence: str = Field(default="", max_length=500)
    confidence: str = "low"
    rationale: str = Field(default="", max_length=400)

    @field_validator("category", mode="before")
    @classmethod
    def _category(cls, value: str) -> str:
        return norm_category(str(value or ""))

    @field_validator("confidence", mode="before")
    @classmethod
    def _confidence(cls, value: str) -> str:
        return norm_confidence(str(value or ""))


class CausesOut(TextModel):
    root_causes: list[CauseOut] = Field(default_factory=list)
    contributing_factors: list[CauseOut] = Field(default_factory=list)

    @field_validator("root_causes")
    @classmethod
    def _roots(cls, value: list[CauseOut]) -> list[CauseOut]:
        return [item for item in value if item.statement][:3]

    @field_validator("contributing_factors")
    @classmethod
    def _factors(cls, value: list[CauseOut]) -> list[CauseOut]:
        return [item for item in value if item.statement][:4]


class GapOut(TextModel):
    topic: str = Field(default="", max_length=200)
    why_it_matters: str = Field(default="", max_length=500)
    suggested_source: str = Field(default="", max_length=300)


class GapsOut(TextModel):
    gaps: list[GapOut] = Field(default_factory=list)

    @field_validator("gaps")
    @classmethod
    def _gaps(cls, value: list[GapOut]) -> list[GapOut]:
        return [item for item in value if item.topic][:6]


class CapaItemOut(TextModel):
    capa_type: str = "corrective"
    description: str = Field(default="", max_length=800)
    rationale: str = Field(default="", max_length=500)
    owner_role: str = Field(default="", max_length=160)
    due_in_days: int = 30
    effectiveness_check: str = Field(default="", max_length=500)

    @field_validator("capa_type", mode="before")
    @classmethod
    def _type(cls, value: str) -> str:
        return norm_capa_type(str(value or ""))

    @field_validator("due_in_days", mode="before")
    @classmethod
    def _days(cls, value) -> int:
        try:
            days = int(value)
        except (TypeError, ValueError):
            return 30
        return max(7, min(days, 90))


class CapaListOut(TextModel):
    summary: str = Field(default="", max_length=600)
    capas: list[CapaItemOut] = Field(default_factory=list)

    @field_validator("capas")
    @classmethod
    def _capas(cls, value: list[CapaItemOut]) -> list[CapaItemOut]:
        return [item for item in value if item.description][:5]


class EditOperation(TextModel):
    """One edit the chat model wants applied. Unused fields stay empty."""

    op: str = ""
    path: str = ""
    value: str = ""
    collection: str = ""
    index: int = -1
    confirmed: bool = True
    category: str = ""
    question: str = ""
    answer: str = ""
    evidence: str = ""
    statement: str = ""
    confidence: str = "medium"
    topic: str = ""
    why_it_matters: str = ""
    suggested_source: str = ""
    capa_type: str = "corrective"
    description: str = ""
    rationale: str = ""
    owner: str = ""
    due_date: str = ""
    effectiveness_check: str = ""
    section: str = ""
    instruction: str = ""
    fields_json: str = ""
    name: str = ""
    role: str = ""
    department: str = ""

    @field_validator("index", mode="before")
    @classmethod
    def _index(cls, value) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return -1

    @field_validator("confirmed", mode="before")
    @classmethod
    def _confirmed(cls, value) -> bool:
        if isinstance(value, str):
            return value.strip().lower() in {"true", "yes", "1"}
        return bool(value)


class EditPlan(TextModel):
    assistant_message: str = Field(default="", max_length=2000)
    operations: list[EditOperation] = Field(default_factory=list)

    @field_validator("operations")
    @classmethod
    def _ops(cls, value: list[EditOperation]) -> list[EditOperation]:
        return value[:8]
