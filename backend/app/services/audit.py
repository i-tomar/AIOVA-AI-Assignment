"""Diff two investigation documents for the audit trail.

The source text and the chat thread are recorded as a single line so the trail stays readable.
"""

from __future__ import annotations

_OPAQUE = {"raw_text", "conversation"}
_LIMIT = 240


def diff_documents(before: dict | None, after: dict | None) -> list[dict]:
    changes = _walk(before, after, "")
    if len(changes) > 80:
        extra = len(changes) - 80
        changes = changes[:80]
        changes.append({"path": "…", "before": "", "after": f"{extra} further changes"})
    return changes


def _walk(before, after, prefix: str) -> list[dict]:
    if before == after:
        return []
    if isinstance(before, dict) and isinstance(after, dict):
        changes: list[dict] = []
        for key in sorted(set(before) | set(after)):
            if key in _OPAQUE:
                if before.get(key) != after.get(key):
                    changes.append(
                        {
                            "path": f"{prefix}{key}",
                            "before": _size(before.get(key)),
                            "after": _size(after.get(key)),
                        }
                    )
                continue
            changes.extend(_walk(before.get(key), after.get(key), f"{prefix}{key}."))
        return changes
    if isinstance(before, list) and isinstance(after, list):
        return [{"path": prefix.rstrip("."), "before": _clip(before), "after": _clip(after)}]
    return [{"path": prefix.rstrip("."), "before": _clip(before), "after": _clip(after)}]


def _size(value) -> str:
    if isinstance(value, str):
        return f"<{len(value)} characters>"
    if isinstance(value, list):
        return f"<{len(value)} messages>"
    return _clip(value)


def _clip(value) -> str:
    if value is None:
        return ""
    text = value if isinstance(value, str) else str(value)
    text = " ".join(text.split())
    if len(text) > _LIMIT:
        return text[: _LIMIT - 1] + "…"
    return text
