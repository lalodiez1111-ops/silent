"""Shared utility helpers for the solo operator agent system."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover - fallback for environments before dependencies are installed.
    Draft202012Validator = None


def project_root() -> Path:
    """Return the repository root based on the current file location."""
    return Path(__file__).resolve().parent.parent


def load_json(path: str | Path) -> Any:
    """Load and parse a JSON file."""
    with Path(path).expanduser().open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_text(path: str | Path) -> str:
    """Load a UTF-8 text file."""
    return Path(path).expanduser().read_text(encoding="utf-8")


def ensure_dir(path: str | Path) -> Path:
    """Create a directory if it does not already exist."""
    output_path = Path(path)
    output_path.mkdir(parents=True, exist_ok=True)
    return output_path


def timestamp_slug() -> str:
    """Return a sortable UTC timestamp for output filenames."""
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def save_json(path: str | Path, payload: Any) -> None:
    """Save JSON with stable formatting for later review or export."""
    with Path(path).open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=True)
        handle.write("\n")


def save_text(path: str | Path, content: str) -> None:
    """Save Markdown or text output."""
    Path(path).write_text(content.strip() + "\n", encoding="utf-8")


def validate_against_schema(payload: Any, schema_path: str | Path) -> None:
    """Validate payloads against the JSON schema for the agent."""
    if Draft202012Validator is None:
        # Validation is optional during bootstrap, but enabled automatically once dependencies are installed.
        return

    schema = load_json(schema_path)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda item: item.path)
    if errors:
        details = "; ".join(error.message for error in errors)
        raise ValueError(f"Schema validation failed: {details}")


def average_score(score_map: dict[str, int], weights: dict[str, float]) -> float:
    """Compute a weighted average across 1-5 scores."""
    total_weight = sum(weights.values()) or 1.0
    weighted_total = sum(score_map[key] * weights.get(key, 1.0) for key in score_map)
    return round(weighted_total / total_weight, 2)


def first_sentence(text: str) -> str:
    """Return the first sentence-like chunk from a block of text."""
    cleaned = " ".join(text.split())
    if not cleaned:
        return ""
    for separator in [". ", "! ", "? "]:
        if separator in cleaned:
            return cleaned.split(separator)[0].strip(" .!?")
    return cleaned


def compact_lines(items: list[str]) -> list[str]:
    """Normalize and remove empty strings while preserving order."""
    return [item.strip() for item in items if item and item.strip()]


def lane_voice(preferences: dict[str, Any], lane: str) -> list[str]:
    """Return lane-specific voice anchors from preferences."""
    lane_map = preferences.get("lane_preferences", {})
    return lane_map.get(lane, {}).get("voice", [])


def path_from_root(*parts: str) -> Path:
    """Build a path relative to the project root."""
    return project_root().joinpath(*parts)


def default_output_dir() -> Path:
    """Resolve default outputs path at silent-studio/outputs/brand-engine."""
    repo_root = project_root()
    silent_studio_root = repo_root.parent
    return silent_studio_root / "outputs" / repo_root.name


def slugify_filename(value: str) -> str:
    """Create a filesystem-friendly output name."""
    cleaned = "".join(char.lower() if char.isalnum() else "-" for char in value.strip())
    compact = "-".join(part for part in cleaned.split("-") if part)
    return compact or "run"
