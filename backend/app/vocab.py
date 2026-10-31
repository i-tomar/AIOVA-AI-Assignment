"""Shared classifications for the RCA record.

The frontend mirrors these strings in `src/format.ts`. Keep the two in step.
"""

from __future__ import annotations

CATEGORIES = (
    "Man",
    "Machine",
    "Method",
    "Material",
    "Measurement",
    "Environment",
    "Other",
)
FISH_CATEGORIES = CATEGORIES[:-1]
SEVERITIES = ("critical", "major", "minor", "unknown")
STATUSES = ("draft", "under_investigation", "pending_qa", "approved", "closed")
CHAT_STATUSES = ("draft", "under_investigation", "pending_qa", "closed")
CAPA_TYPES = ("corrective", "preventive")
CAPA_STATUSES = ("proposed", "accepted", "in_progress", "completed", "verified")
CONFIDENCE = ("low", "medium", "high")

_CATEGORY_ALIASES = {
    "man": "Man",
    "people": "Man",
    "personnel": "Man",
    "manpower": "Man",
    "operator": "Man",
    "machine": "Machine",
    "equipment": "Machine",
    "method": "Method",
    "process": "Method",
    "procedure": "Method",
    "material": "Material",
    "materials": "Material",
    "measurement": "Measurement",
    "measure": "Measurement",
    "mother nature": "Environment",
    "environment": "Environment",
    "env": "Environment",
    "milieu": "Environment",
    "other": "Other",
}


def norm_category(value: str) -> str:
    key = " ".join((value or "").strip().lower().split())
    if key in _CATEGORY_ALIASES:
        return _CATEGORY_ALIASES[key]
    for name in CATEGORIES:
        if name.lower() == key:
            return name
    return "Other"


def norm_fish_category(value: str) -> str:
    category = norm_category(value)
    if category == "Other":
        return "Method"
    return category


def norm_severity(value: str) -> str:
    key = (value or "").strip().lower()
    aliases = {
        "crit": "critical",
        "catastrophic": "critical",
        "moderate": "major",
        "medium": "major",
        "low": "minor",
        "n/a": "unknown",
        "na": "unknown",
        "unclassified": "unknown",
        "": "unknown",
    }
    key = aliases.get(key, key)
    if key in SEVERITIES:
        return key
    return "unknown"


def norm_confidence(value: str) -> str:
    key = (value or "").strip().lower()
    if key in CONFIDENCE:
        return key
    return "low"


def norm_capa_type(value: str) -> str:
    key = (value or "").strip().lower()
    if key.startswith("prev"):
        return "preventive"
    return "corrective"


def norm_capa_status(value: str) -> str:
    key = (value or "").strip().lower().replace(" ", "_").replace("-", "_")
    if key in CAPA_STATUSES:
        return key
    return "proposed"


def norm_status(value: str) -> str:
    key = (value or "").strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "open": "under_investigation",
        "investigation": "under_investigation",
        "pending": "pending_qa",
        "qa": "pending_qa",
        "qa_review": "pending_qa",
        "signed": "approved",
    }
    key = aliases.get(key, key)
    if key in STATUSES:
        return key
    return "draft"
