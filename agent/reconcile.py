"""Deterministic field-level reconciliation and buildability derivation."""

from __future__ import annotations

import copy
import json
from typing import Any

from .models import CombinedBuildability, Confidence
from .validator import FIELD_PATHS, insufficient


def _get_path(record: dict[str, Any], path: str) -> dict[str, Any]:
    current: Any = record
    for item in path.split("."):
        current = current[item]
    return current


def _set_path(record: dict[str, Any], path: str, value: dict[str, Any]) -> None:
    current = record
    parts = path.split(".")
    for item in parts[:-1]:
        current = current.setdefault(item, {})
    current[parts[-1]] = value


def _field_key(field: dict[str, Any]) -> str:
    return json.dumps(field.get("value"), sort_keys=True, separators=(",", ":"))


def _supported(field: dict[str, Any]) -> bool:
    return field.get("value") is not None and bool(field.get("citations"))


def reconcile_field(first: dict[str, Any], second: dict[str, Any]) -> dict[str, Any]:
    first_supported, second_supported = _supported(first), _supported(second)
    if first_supported and second_supported and _field_key(first) == _field_key(second):
        result = copy.deepcopy(first)
        result["citations"] = sorted(set(first["citations"]) | set(second["citations"]))
        result["confidence"] = Confidence.CORROBORATED_PRIMARY
        return result
    if first_supported and not second_supported:
        result = copy.deepcopy(first)
        result["confidence"] = Confidence.SUPPORTED_PRIMARY
        return result
    if second_supported and not first_supported:
        result = copy.deepcopy(second)
        result["confidence"] = Confidence.SUPPORTED_PRIMARY
        return result
    if first_supported and second_supported:
        citations = sorted(set(first["citations"]) | set(second["citations"]))
        return {"value": None, "citations": citations, "confidence": Confidence.CONFLICTING, "note": "researcher and critic disagree"}
    return insufficient("no primary-evidence-supported value after reconciliation")


def _derive_combined(technical: dict[str, Any], credential_path: dict[str, Any]) -> dict[str, Any]:
    citations = sorted(set(technical.get("citations", [])) | set(credential_path.get("citations", [])))
    values = (technical.get("value"), credential_path.get("value"))
    if technical.get("confidence") == Confidence.CONFLICTING or credential_path.get("confidence") == Confidence.CONFLICTING:
        return {"value": CombinedBuildability.INSUFFICIENT_EVIDENCE, "citations": citations, "confidence": Confidence.CONFLICTING, "note": "upstream field conflict"}
    if values[0] == "not_applicable":
        return {"value": CombinedBuildability.NOT_APPLICABLE, "citations": citations, "confidence": Confidence.SUPPORTED_PRIMARY, "note": None}
    if values[0] == "no_public_api":
        return {"value": CombinedBuildability.BLOCKED, "citations": citations, "confidence": Confidence.SUPPORTED_PRIMARY, "note": "no documented public API"}
    if values[0] == "ready" and values[1] == "self_serve":
        return {"value": CombinedBuildability.READY_NOW, "citations": citations, "confidence": Confidence.SUPPORTED_PRIMARY, "note": None}
    if values[0] == "ready" and values[1] in {"paid_or_admin_gated", "partner_or_sales_gated"}:
        return {"value": CombinedBuildability.BUILDABLE_WITH_ACCESS_CONSTRAINT, "citations": citations, "confidence": Confidence.SUPPORTED_PRIMARY, "note": None}
    if values[0] == "workaround_needed" and values[1] == "self_serve":
        return {"value": CombinedBuildability.BUILDABLE_WITH_TECHNICAL_WORKAROUND, "citations": citations, "confidence": Confidence.SUPPORTED_PRIMARY, "note": None}
    return {"value": CombinedBuildability.INSUFFICIENT_EVIDENCE, "citations": citations, "confidence": Confidence.INSUFFICIENT_EVIDENCE, "note": "cannot derive buildability from available evidence"}


def reconcile_passes(researcher: dict[str, Any], critic: dict[str, Any], evidence: list[dict[str, Any]]) -> dict[str, Any]:
    if researcher["app_id"] != critic["app_id"]:
        raise ValueError("Cannot reconcile records for different apps")
    final: dict[str, Any] = {"app_id": researcher["app_id"]}
    disagreements: list[str] = []
    for path in FIELD_PATHS:
        result = reconcile_field(_get_path(researcher, path), _get_path(critic, path))
        _set_path(final, path, result)
        if result["confidence"] == Confidence.CONFLICTING:
            disagreements.append(path)
    _set_path(final, "viability.combined", _derive_combined(_get_path(final, "viability.technical"), _get_path(final, "credential_path")))
    final["evidence"] = evidence
    final["audit"] = {
        "researcher_pass1": researcher,
        "critic_pass2": critic,
        "disagreement_fields": disagreements,
    }
    return final
