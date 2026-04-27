"""Validation helpers for Brand Content Engine v2 outputs."""

from __future__ import annotations

from typing import Any


def validate_generated_content(generated_content: dict[str, Any], risky_words: list[str]) -> dict[str, Any]:
    """Check generated content for risky terms and return review status."""
    joined = _flatten_content(generated_content).lower()
    flagged_terms = sorted({word for word in risky_words if word.lower() in joined})
    status = "review_required" if flagged_terms else "approved"
    return {
        "status": status,
        "flagged_terms": flagged_terms,
    }


def _flatten_content(value: Any) -> str:
    """Flatten nested generated content into one string for term scanning."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(_flatten_content(item) for item in value)
    if isinstance(value, dict):
        return " ".join(_flatten_content(item) for item in value.values())
    return str(value)
