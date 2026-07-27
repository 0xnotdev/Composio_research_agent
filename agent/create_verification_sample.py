"""Create a fresh, coverage-first human verification worksheet from an audit dataset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .verification import select_verification_sample


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the stratified manual-verification worksheet")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    records = json.loads(args.dataset.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise SystemExit("Dataset must be a JSON array")
    sample = select_verification_sample(records)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(sample, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "apps": len(sample)}, indent=2))


if __name__ == "__main__":
    main()
