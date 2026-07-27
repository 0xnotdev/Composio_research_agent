"""Deterministic portfolio statistics and prioritisation."""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable


def get_path(record: dict[str, Any], path: str, default: Any = None) -> Any:
    current: Any = record
    for part in path.split("."):
        if not isinstance(current, dict):
            return default
        current = current.get(part, default)
    return current


def field_value(record: dict[str, Any], path: str) -> Any:
    field = get_path(record, path, {})
    return field.get("value") if isinstance(field, dict) else None


def _normalise(value: Any) -> list[str]:
    if value is None:
        return ["unknown"]
    if isinstance(value, list):
        return [str(item) for item in value] or ["none_reported"]
    return [str(value)]


def distribution(records: Iterable[dict[str, Any]], path: str) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for record in records:
        counter.update(_normalise(field_value(record, path)))
    return dict(sorted(counter.items()))


def coverage(records: Iterable[dict[str, Any]], paths: tuple[str, ...]) -> dict[str, Any]:
    rows = list(records)
    observed = 0
    total = len(rows) * len(paths)
    conflicts = 0
    for record in rows:
        for path in paths:
            field = get_path(record, path, {})
            value = field.get("value") if isinstance(field, dict) else None
            confidence = field.get("confidence") if isinstance(field, dict) else None
            if value is not None and value != "unknown":
                observed += 1
            if confidence == "conflicting":
                conflicts += 1
    return {
        "observed_fields": observed,
        "total_fields": total,
        "coverage_percent": round((observed / total * 100) if total else 0, 1),
        "conflicting_fields": conflicts,
    }


def _record_label(record: dict[str, Any]) -> dict[str, Any]:
    return {"app_id": record["app_id"], "name": record.get("name", record["app_id"]), "category": record.get("category", "Unknown")}


def easy_wins(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for record in records:
        if (
            field_value(record, "credential_path") == "self_serve"
            and field_value(record, "viability.technical") == "ready"
            and field_value(record, "api_surface.breadth") in {"moderate", "broad"}
            and field_value(record, "mcp.official_vendor_mcp") == "no"
        ):
            selected.append(_record_label(record))
    return selected


def outreach_candidates(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for record in records:
        if (
            field_value(record, "credential_path") == "partner_or_sales_gated"
            and field_value(record, "api_surface.breadth") in {"moderate", "broad"}
            and field_value(record, "viability.technical") in {"ready", "workaround_needed"}
        ):
            selected.append(_record_label(record))
    return selected


def calculate_analytics(records: list[dict[str, Any]]) -> dict[str, Any]:
    if len({record["app_id"] for record in records}) != len(records):
        raise ValueError("Analytics requires unique app_id values")
    dimensions = (
        "auth_methods",
        "credential_path",
        "api_surface.protocols",
        "api_surface.breadth",
        "mcp.official_vendor_mcp",
        "viability.technical",
        "viability.combined",
    )
    category_split: dict[str, dict[str, int]] = {}
    for category in sorted({record.get("category", "Unknown") for record in records}):
        category_records = [record for record in records if record.get("category", "Unknown") == category]
        category_split[category] = distribution(category_records, "credential_path")
    blocker_counts: Counter[str] = Counter()
    for record in records:
        blocker_counts.update(_normalise(field_value(record, "viability.blockers")))
    return {
        "record_count": len(records),
        "distributions": {path: distribution(records, path) for path in dimensions},
        "credential_path_by_category": category_split,
        "blockers": dict(sorted(blocker_counts.items())),
        "easy_wins": easy_wins(records),
        "outreach_candidates": outreach_candidates(records),
        "coverage": coverage(records, dimensions),
    }
