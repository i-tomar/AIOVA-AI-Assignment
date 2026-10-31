"""Decide whether an evidence note is actually supported by the uploaded source.

The model sets a confidence. This check can lower it. A qualified person may still
confirm a cause with evidence that was never in the file; `grounded` only means
the quote matches the source we were given.
"""

from __future__ import annotations

import re

_TOKEN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_NUMBER = re.compile(r"\d+(?:\.\d+)?")
_STOP = {
    "that",
    "this",
    "with",
    "from",
    "were",
    "was",
    "have",
    "been",
    "into",
    "than",
    "then",
    "when",
    "where",
    "which",
    "their",
    "there",
    "about",
    "after",
    "before",
    "during",
    "because",
    "would",
    "could",
    "should",
    "other",
    "only",
    "also",
    "over",
    "under",
    "between",
    "within",
    "using",
    "used",
    "such",
    "batch",
    "result",
    "results",
}


def evidence_grounded(evidence: str, source: str) -> bool:
    quote = " ".join((evidence or "").split())
    if len(quote) < 12 or not (source or "").strip():
        return False
    source_folded = source.lower()
    if quote.lower() in source_folded:
        return True
    numbers = _NUMBER.findall(quote)
    if any(number not in source_folded for number in numbers):
        return False
    tokens = [
        token
        for token in _TOKEN.findall(quote.lower())
        if len(token) >= 4 and token not in _STOP
    ]
    if len(tokens) < 3:
        return False
    source_tokens = set(_TOKEN.findall(source_folded))
    overlap = sum(1 for token in tokens if token in source_tokens)
    return overlap >= 3 and overlap / len(tokens) >= 0.45
