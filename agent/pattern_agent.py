"""Evidence-constrained portfolio-pattern synthesis over deterministic audit metrics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .config import Settings
from .llm_client import OpenRouterClient, RequestLedger


PATTERN_SYSTEM_PROMPT = """You are the portfolio-analysis agent in an evidence-grounded app research audit.
You receive only deterministic aggregate metrics calculated from a 100-app dataset. Produce exactly four concise portfolio patterns.
Do not invent facts, source URLs, apps, counts, percentages, causes, or recommendations beyond the supplied metrics.
Every pattern must identify the metric keys that support it and must state an uncertainty caveat where the supplied data is incomplete.
Return a strict JSON object only: {\"patterns\":[{\"headline\":string,\"insight\":string,\"metric_refs\":[string],\"caveat\":string}]}."""


def pattern_packet(analytics: dict[str, Any]) -> dict[str, Any]:
    """Expose only computed, presentation-relevant values to the synthesis agent."""
    return {
        "record_count": analytics.get("record_count"),
        "coverage": analytics.get("coverage"),
        "auth_distribution": analytics.get("distributions", {}).get("auth_methods", {}),
        "credential_distribution": analytics.get("distributions", {}).get("credential_path", {}),
        "api_protocol_distribution": analytics.get("distributions", {}).get("api_surface.protocols", {}),
        "api_breadth_distribution": analytics.get("distributions", {}).get("api_surface.breadth", {}),
        "official_mcp_distribution": analytics.get("distributions", {}).get("mcp.official_vendor_mcp", {}),
        "buildability_distribution": analytics.get("distributions", {}).get("viability.combined", {}),
        "credential_path_by_category": analytics.get("credential_path_by_category", {}),
        "easy_wins": analytics.get("easy_wins", []),
        "outreach_candidates": analytics.get("outreach_candidates", []),
    }


def parse_patterns(raw: str) -> list[dict[str, Any]]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError("Pattern agent returned invalid JSON") from error
    patterns = payload.get("patterns") if isinstance(payload, dict) else None
    if not isinstance(patterns, list) or len(patterns) != 4:
        raise ValueError("Pattern agent must return exactly four patterns")
    clean: list[dict[str, Any]] = []
    for pattern in patterns:
        if not isinstance(pattern, dict):
            raise ValueError("Each pattern must be an object")
        headline, insight, caveat, refs = (pattern.get("headline"), pattern.get("insight"), pattern.get("caveat"), pattern.get("metric_refs"))
        if not all(isinstance(item, str) and item.strip() for item in (headline, insight, caveat)):
            raise ValueError("Each pattern needs non-empty headline, insight, and caveat")
        if not isinstance(refs, list) or not refs or not all(isinstance(item, str) for item in refs):
            raise ValueError("Each pattern needs metric references")
        clean.append({"headline": headline.strip(), "insight": insight.strip(), "metric_refs": refs, "caveat": caveat.strip()})
    return clean


def synthesize_patterns(client: Any, analytics: dict[str, Any]) -> list[dict[str, Any]]:
    raw = client.complete(
        system=PATTERN_SYSTEM_PROMPT,
        user=json.dumps({"metrics": pattern_packet(analytics)}, ensure_ascii=False, separators=(",", ":")),
        purpose="portfolio_pattern_synthesis",
    )
    return parse_patterns(raw)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask the portfolio-analysis agent to synthesize four grounded patterns")
    parser.add_argument("--analytics", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    settings = Settings.from_environment()
    if not settings.openrouter_api_key or not settings.openrouter_model:
        raise SystemExit("OPENROUTER_API_KEY and OPENROUTER_MODEL are required")
    analytics = json.loads(args.analytics.read_text(encoding="utf-8"))
    client = OpenRouterClient(settings.openrouter_api_key, settings.openrouter_model, RequestLedger(1))
    patterns = synthesize_patterns(client, analytics)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"patterns": patterns}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "patterns": len(patterns)}, indent=2))


if __name__ == "__main__":
    main()
