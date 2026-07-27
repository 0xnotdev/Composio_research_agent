"""Runnable one-app proof using the same live pipeline as the batch audit."""

from __future__ import annotations

import argparse
import json

from agent.config import PROJECT_ROOT, Settings
from agent.pipeline import build_live_pipeline
from agent.seed import load_seeds


def main() -> None:
    parser = argparse.ArgumentParser(description="Research one assigned app with the audit pipeline")
    parser.add_argument("app_name", help="Assigned app name or app_id, for example Slack")
    parser.add_argument("--run-id", default="single-app")
    args = parser.parse_args()
    needle = args.app_name.strip().casefold()
    matches = [seed for seed in load_seeds(PROJECT_ROOT / "data/apps_100.json") if seed.app_id.casefold() == needle or seed.name.casefold() == needle]
    if not matches:
        raise SystemExit("App is not in the assigned research set. Refusing to guess an official source domain.")
    pipeline = build_live_pipeline(args.run_id, Settings.from_environment())
    record = pipeline.run(matches)[0]
    print(json.dumps(record, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
