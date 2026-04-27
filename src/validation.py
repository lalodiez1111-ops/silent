"""Validation helpers for Brand Content Engine v2 outputs."""

from __future__ import annotations

import re
from typing import Any


def validate_generated_content(generated_content: dict[str, Any], risky_words: list[str] | dict[str, Any]) -> dict[str, Any]:
    """Check generated content for risky terms and return structured findings."""
    normalized_rules = _normalize_risky_words(risky_words)
    joined = _flatten_content(generated_content)
    findings = _build_findings(joined, normalized_rules)
    flagged_terms = [item["term"] for item in findings]
    overall_status = "review_required" if findings else "approved"

    return {
        "overall_status": overall_status,
        "findings": findings,
        # Compatibility aliases for older callers.
        "status": overall_status,
        "flagged_terms": flagged_terms,
        "risk_level": _overall_risk_level(findings),
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


def _risk_level_for_count(flagged_count: int) -> str:
    """Map number of flagged risky terms to a simple risk level."""
    if flagged_count == 0:
        return "low"
    if flagged_count <= 2:
        return "medium"
    return "high"


def _normalize_risky_words(risky_words: list[str] | dict[str, Any]) -> list[dict[str, str]]:
    """Normalize risky words into rule dictionaries with guidance."""
    if isinstance(risky_words, dict):
        raw_rules = risky_words.get("risky_words", [])
    else:
        raw_rules = risky_words

    normalized: list[dict[str, Any]] = []
    for item in raw_rules:
        if isinstance(item, str):
            normalized.append(
                {
                    "term": item.strip(),
                    "risk_level": "medium",
                    "reason": "Absolute or high-certainty language can create legal or trust risk.",
                    "alternatives": [_default_alternative(item.strip())],
                }
            )
            continue

        if isinstance(item, dict):
            term = str(item.get("term", "")).strip()
            if not term:
                continue
            normalized.append(
                {
                    "term": term,
                    "risk_level": str(item.get("risk_level", "medium")).strip().lower(),
                    "reason": str(
                        item.get(
                            "reason",
                            "Absolute or high-certainty language can create legal or trust risk.",
                        )
                    ).strip(),
                    "alternatives": _normalize_alternatives(item.get("alternatives"), term),
                }
            )
    return normalized


def _normalize_alternatives(value: Any, term: str) -> list[str]:
    """Normalize alternatives into a non-empty list."""
    if isinstance(value, list):
        cleaned = [str(item).strip() for item in value if str(item).strip()]
        if cleaned:
            return cleaned
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return [_default_alternative(term)]


def _build_findings(content: str, rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build detailed findings with occurrence counts for matched risky terms."""
    findings: list[dict[str, Any]] = []
    lowered = content.lower()
    for rule in rules:
        term = rule["term"]
        occurrences = len(re.findall(re.escape(term.lower()), lowered))
        if occurrences <= 0:
            continue
        findings.append(
            {
                "term": term,
                "risk_level": str(rule.get("risk_level", "medium")).lower(),
                "reason": rule.get("reason", ""),
                "alternatives": rule.get("alternatives", []),
                "occurrences": occurrences,
            }
        )
    return findings


def _overall_risk_level(findings: list[dict[str, Any]]) -> str:
    """Return overall risk based on highest finding risk."""
    if not findings:
        return "low"
    rank = {"low": 1, "medium": 2, "high": 3}
    highest = max(findings, key=lambda item: rank.get(str(item.get("risk_level", "low")).lower(), 1))
    return str(highest.get("risk_level", "low")).lower()


def _default_alternative(term: str) -> str:
    """Return safer language alternatives for common risky terms."""
    alternatives = {
        "guarantee": "designed to improve",
        "best": "strong",
        "no risk": "lower risk",
        "risk-free": "lower-risk",
        "never fails": "reliably supports",
        "instant results": "faster results",
    }
    return alternatives.get(term.lower(), "results can vary")
