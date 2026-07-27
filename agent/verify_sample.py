"""Score the manually completed verification worksheet without model involvement."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .verification import score_verification_sample


def main() -> None:
    parser = argparse.ArgumentParser(description="Score a completed 12-app verification sample")
    parser.add_argument("--sample", type=Path, required=True, help="Edited verification_sample.json")
    parser.add_argument("--output", type=Path, required=True, help="verification_results.json")
    args = parser.parse_args()
    sample = json.loads(args.sample.read_text(encoding="utf-8"))
    if not isinstance(sample, list):
        raise SystemExit("Verification sample must be a JSON array")
    result = score_verification_sample(sample)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "judged_fields": result["judged_fields"]}, indent=2))


if __name__ == "__main__":
    main()
