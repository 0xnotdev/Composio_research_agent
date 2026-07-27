"""Run-scoped, append-only artifact storage with atomic JSON writes."""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .redaction import redact


RUN_ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}$")


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def json_default(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    return str(value)


class RunStore:
    def __init__(self, root: str | Path, run_id: str) -> None:
        if not RUN_ID_PATTERN.fullmatch(run_id):
            raise ValueError("run_id may contain only letters, numbers, underscores, and hyphens")
        self.root = Path(root)
        self.run_id = run_id
        self.path = self.root / run_id
        self.path.mkdir(parents=True, exist_ok=True)
        for directory in ("raw_evidence", "evidence_packs", "passes", "logs"):
            (self.path / directory).mkdir(exist_ok=True)

    def relative_path(self, relative: str | Path) -> Path:
        candidate = (self.path / relative).resolve()
        if self.path.resolve() not in candidate.parents and candidate != self.path.resolve():
            raise ValueError("artifact path escapes run directory")
        return candidate

    def write_json(self, relative: str | Path, payload: Any) -> Path:
        target = self.relative_path(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(f"{target.suffix}.tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=json_default), encoding="utf-8")
        os.replace(temporary, target)
        return target

    def read_json(self, relative: str | Path) -> Any:
        return json.loads(self.relative_path(relative).read_text(encoding="utf-8"))

    def append_event(self, stage: str, status: str, **details: Any) -> None:
        safe_details = {key: redact(value) if isinstance(value, str) and ("error" in key or "failure" in key) else value for key, value in details.items()}
        event = {"at": utc_now(), "stage": stage, "status": status, **safe_details}
        path = self.relative_path("logs/event_log.jsonl")
        with path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(event, ensure_ascii=False, default=json_default) + "\n")
