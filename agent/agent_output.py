"""Strict JSONL parsing shared by the researcher and critic stages."""

from __future__ import annotations

import json
from typing import Any


class AgentOutputError(ValueError):
    pass


def parse_ordered_jsonl(raw: str, expected_app_ids: list[str]) -> list[dict[str, Any]]:
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    if len(lines) != len(expected_app_ids):
        raise AgentOutputError(f"Expected {len(expected_app_ids)} JSONL rows, received {len(lines)}")
    records: list[dict[str, Any]] = []
    for index, line in enumerate(lines):
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise AgentOutputError(f"Invalid JSON on line {index + 1}: {error.msg}") from error
        if not isinstance(record, dict):
            raise AgentOutputError(f"Line {index + 1} must be a JSON object")
        if record.get("app_id") != expected_app_ids[index]:
            raise AgentOutputError(
                f"Line {index + 1} app_id must be {expected_app_ids[index]!r}, got {record.get('app_id')!r}"
            )
        records.append(record)
    return records
