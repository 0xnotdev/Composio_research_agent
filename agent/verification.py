"""Stratified human-verification templates and honest accuracy calculations."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .analytics import field_value, get_path


JUDGED_PATHS = (
    "auth_methods",
    "credential_path",
    "api_surface.protocols",
    "api_surface.breadth",
    "mcp.official_vendor_mcp",
    "viability.technical",
)


def _uncertainty(record: dict[str, Any]) -> int:
    score = 0
    for path in JUDGED_PATHS:
        field = get_path(record, path, {})
        value = field.get("value") if isinstance(field, dict) else None
        if not isinstance(field, dict) or value is None or value == "unknown":
            score += 2
        if isinstance(field, dict) and field.get("confidence") == "conflicting":
            score += 3
    return score


def select_verification_sample(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One record per category plus two highest-uncertainty non-duplicates."""
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_category[record.get("category", "Unknown")].append(record)
    sample: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    for category in sorted(by_category):
        candidate = max(by_category[category], key=lambda record: (_uncertainty(record), record["app_id"]))
        selected_ids.add(candidate["app_id"])
        sample.append(_template(candidate, f"category representative: {category}"))
    for record in sorted(records, key=lambda item: (-_uncertainty(item), item["app_id"])):
        if len(sample) >= 12:
            break
        if record["app_id"] not in selected_ids:
            selected_ids.add(record["app_id"])
            sample.append(_template(record, "highest remaining uncertainty / hard case"))
    return sample


def _template(record: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "app_id": record["app_id"],
        "name": record.get("name", record["app_id"]),
        "category": record.get("category", "Unknown"),
        "selection_reason": reason,
        "judgements": [
            {
                "path": path,
                "ground_truth": None,
                "pass1_value": field_value(get_path(record, "audit.researcher_pass1", {}), path),
                "final_pre_human_value": field_value(record, path),
                "pass1_correct": None,
                "final_pre_human_correct": None,
                "official_source_url": None,
                "notes": None,
            }
            for path in JUDGED_PATHS
        ],
    }


def score_verification_sample(sample: list[dict[str, Any]]) -> dict[str, Any]:
    pass1_correct = final_correct = judged = abstentions = 0
    misses: list[dict[str, Any]] = []
    for app in sample:
        for judgement in app.get("judgements", []):
            if judgement.get("ground_truth") is None:
                abstentions += 1
                continue
            if judgement.get("pass1_correct") is None or judgement.get("final_pre_human_correct") is None:
                raise ValueError(f"Missing correctness decision for {app['app_id']} {judgement['path']}")
            judged += 1
            pass1_correct += int(bool(judgement["pass1_correct"]))
            final_correct += int(bool(judgement["final_pre_human_correct"]))
            if not judgement["final_pre_human_correct"]:
                misses.append({"app_id": app["app_id"], "path": judgement["path"], "notes": judgement.get("notes")})
    return {
        "judged_fields": judged,
        "unjudged_fields": abstentions,
        "pass1_correct": pass1_correct,
        "final_pre_human_correct": final_correct,
        "pass1_accuracy_percent": round(pass1_correct / judged * 100, 1) if judged else None,
        "final_pre_human_accuracy_percent": round(final_correct / judged * 100, 1) if judged else None,
        "misses": misses,
    }
