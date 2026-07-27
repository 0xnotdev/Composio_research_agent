"""Schema-adjacent validation and safe sanitisation of model output."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

from .models import Confidence


FIELD_PATHS = (
    "one_liner",
    "auth_methods",
    "credential_path",
    "gating_reasons",
    "api_surface.protocols",
    "api_surface.breadth",
    "api_surface.documented",
    "mcp.official_vendor_mcp",
    "mcp.public_mcp_exists",
    "extras.webhooks",
    "extras.sandbox",
    "extras.api_access_tier",
    "viability.technical",
    "viability.blockers",
)


@dataclass(frozen=True, slots=True)
class ValidationResult:
    record: dict[str, Any]
    errors: tuple[str, ...]

    @property
    def is_clean(self) -> bool:
        return not self.errors


def _get_path(record: dict[str, Any], path: str) -> Any:
    current: Any = record
    for item in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(item)
    return current


def _set_path(record: dict[str, Any], path: str, value: Any) -> None:
    current = record
    parts = path.split(".")
    for item in parts[:-1]:
        child = current.get(item)
        if not isinstance(child, dict):
            child = {}
            current[item] = child
        current = child
    current[parts[-1]] = value


def insufficient(note: str) -> dict[str, Any]:
    return {"value": None, "citations": [], "confidence": Confidence.INSUFFICIENT_EVIDENCE, "note": note}


def _requires_citation(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str) and value == "unknown":
        return False
    return True


def validate_pass_record(record: dict[str, Any], expected_app_id: str, evidence_ids: set[str]) -> ValidationResult:
    """Return a safe record; ungrounded fields are nulled instead of published."""
    clean = copy.deepcopy(record)
    errors: list[str] = []
    if clean.get("app_id") != expected_app_id:
        errors.append(f"app_id must equal {expected_app_id!r}")
        clean["app_id"] = expected_app_id

    for path in FIELD_PATHS:
        field = _get_path(clean, path)
        if not isinstance(field, dict) or "value" not in field:
            errors.append(f"{path} must be a field wrapper with value")
            _set_path(clean, path, insufficient("missing or malformed field wrapper"))
            continue
        citations = field.get("citations", [])
        if not isinstance(citations, list) or not all(isinstance(item, str) for item in citations):
            errors.append(f"{path} citations must be a string list")
            _set_path(clean, path, insufficient("malformed citations"))
            continue
        unknown = sorted(set(citations) - evidence_ids)
        if unknown:
            errors.append(f"{path} cites unknown evidence IDs: {', '.join(unknown)}")
            _set_path(clean, path, insufficient("unknown citation"))
            continue
        if _requires_citation(field["value"]) and not citations:
            errors.append(f"{path} populated value lacks primary-evidence citation")
            _set_path(clean, path, insufficient("uncited claim"))
            continue
        field.setdefault("confidence", Confidence.SUPPORTED_PRIMARY if citations else Confidence.INSUFFICIENT_EVIDENCE)
        field.setdefault("note", None)
    return ValidationResult(clean, tuple(errors))
