"""CSV import and normalization helpers for the Lead Sourcing Agent."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


HEADER_ALIASES = {
    "company_name": ["company", "company_name", "account", "account_name", "organization", "business_name"],
    "website": ["website", "url", "domain", "company_website", "site"],
    "source": ["source", "origin", "list_source", "lead_source"],
    "signal_detected": ["signal", "trigger", "reason", "signal_detected", "lead_signal"],
    "notes": ["notes", "comments", "observation", "observations", "comment"],
    "decision_maker_guess": [
        "decision_maker_guess",
        "decision_maker",
        "contact_role",
        "buyer",
        "stakeholder",
    ],
    "geography": ["geography", "region", "location", "country", "market"],
    "industry": ["industry", "sector", "category", "vertical"],
    "hiring_signal": ["hiring_signal", "hiring", "job_signal", "open_roles"],
    "funding_signal": ["funding_signal", "funding", "recent_funding", "investment_signal"],
    "brand_observation": ["brand_observation", "brand_note", "brand_issue", "design_observation"],
}


def normalize_header(value: str) -> str:
    """Normalize raw CSV headers for flexible matching."""
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def map_headers(fieldnames: list[str] | None) -> dict[str, str]:
    """Return canonical field names mapped to actual CSV headers when present."""
    if not fieldnames:
        return {}

    normalized_to_actual = {normalize_header(name): name for name in fieldnames if name}
    mapped: dict[str, str] = {}

    for canonical, aliases in HEADER_ALIASES.items():
        for alias in aliases:
            normalized = normalize_header(alias)
            if normalized in normalized_to_actual:
                mapped[canonical] = normalized_to_actual[normalized]
                break
    return mapped


def _clean_value(value: str | None) -> str:
    """Return a trimmed CSV cell value."""
    return (value or "").strip()


def _get_value(row: dict[str, str], header_map: dict[str, str], canonical_field: str) -> str:
    """Safely return the mapped CSV value for one canonical field."""
    actual_header = header_map.get(canonical_field)
    if not actual_header:
        return ""
    return _clean_value(row.get(actual_header))


def _append_signal(signals: list[str], value: str) -> None:
    """Append a non-empty signal while preserving order."""
    cleaned = _clean_value(value)
    if cleaned:
        signals.append(cleaned)


def normalize_lead_row(row: dict[str, str], header_map: dict[str, str]) -> dict[str, Any]:
    """Normalize a CSV row into the same lead seed structure used by the scorer."""
    company_name = _get_value(row, header_map, "company_name") or "Unknown company"
    website = _get_value(row, header_map, "website")
    source = _get_value(row, header_map, "source") or "csv_import"
    signal_detected = _get_value(row, header_map, "signal_detected")
    notes = _get_value(row, header_map, "notes")
    decision_maker_guess = _get_value(row, header_map, "decision_maker_guess")
    geography = _get_value(row, header_map, "geography")
    industry = _get_value(row, header_map, "industry")
    hiring_signal = _get_value(row, header_map, "hiring_signal")
    funding_signal = _get_value(row, header_map, "funding_signal")
    brand_observation = _get_value(row, header_map, "brand_observation")

    signals: list[str] = []
    _append_signal(signals, signal_detected)
    _append_signal(signals, hiring_signal)
    _append_signal(signals, funding_signal)
    _append_signal(signals, brand_observation)

    note_parts = [notes]
    if geography:
        note_parts.append(f"Geography: {geography}")
    if industry:
        note_parts.append(f"Industry: {industry}")
    normalized_notes = " | ".join(part for part in note_parts if part)

    return {
        "company_name": company_name,
        "website": website,
        "source": source,
        "signals": signals,
        "notes": normalized_notes,
        "decision_maker_guess": decision_maker_guess,
        "geography": geography,
        "industry": industry,
        "hiring_signal": hiring_signal,
        "funding_signal": funding_signal,
        "brand_observation": brand_observation,
    }


def load_lead_csv(csv_path: str | Path, limit: int | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Load a lead CSV file and normalize it into lead seeds plus import metadata."""
    csv_file = Path(csv_path)
    if not csv_file.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_file}")
    if csv_file.suffix.lower() != ".csv":
        raise ValueError(f"Expected a .csv file, got: {csv_file.name}")

    with csv_file.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("CSV file is missing a header row.")

        header_map = map_headers(reader.fieldnames)
        if "company_name" not in header_map and "website" not in header_map:
            raise ValueError(
                "CSV could not be mapped. Include at least one company-identifying column like "
                "'company', 'company_name', 'account', 'website', 'url', or 'domain'."
            )

        seeds: list[dict[str, Any]] = []
        for index, row in enumerate(reader, start=1):
            if limit is not None and len(seeds) >= limit:
                break

            normalized = normalize_lead_row(row, header_map)
            if normalized["company_name"] == "Unknown company" and not normalized["website"]:
                continue
            normalized["source"] = normalized["source"] or f"csv_import:{csv_file.name}"
            seeds.append(normalized)

    metadata = {
        "csv_path": str(csv_file),
        "row_count": len(seeds),
        "mapped_headers": header_map,
    }
    return seeds, metadata
