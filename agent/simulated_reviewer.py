"""Time-boxed AI reviewer diagnostic, explicitly separate from human verification."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .config import Settings
from .llm_client import OpenRouterClient, RequestLedger


REVIEW_PATHS = {"auth_methods", "credential_path", "api_surface.protocols"}
SYSTEM = """You are an AI simulating a reviewer for a product-research audit. This is not human validation.
Use only the supplied official-source excerpts. Do not use outside knowledge. Return canonical values only:
- auth_methods: a JSON array using only oauth2, api_key, basic, token, other, none, unknown.
- credential_path: exactly self_serve, paid_or_admin_gated, partner_or_sales_gated, unknown, or not_applicable.
- api_surface.protocols: exactly rest, graphql, rest_and_graphql, other, none_public, unknown, or not_applicable.
If an excerpt does not directly support a field, return "unknown" (or ["unknown"] for auth_methods). Never return prose in ground_truth.
Return exactly {"reviews":[{"app_id":string,"judgements":[{"path":string,"ground_truth":string-or-array,"reason":string}]}]} with requested apps and fields only."""

ALLOWED = {
    "auth_methods": {"oauth2", "api_key", "basic", "token", "other", "none", "unknown"},
    "credential_path": {"self_serve", "paid_or_admin_gated", "partner_or_sales_gated", "unknown", "not_applicable"},
    "api_surface.protocols": {"rest", "graphql", "rest_and_graphql", "other", "none_public", "unknown", "not_applicable"},
}


def _review_requests(sample: list[dict[str, Any]]) -> list[dict[str, Any]]:
    requests = []
    for app in sample:
        fields = [j["path"] for j in app.get("judgements", []) if j.get("path") in REVIEW_PATHS and j.get("final_pre_human_value") is not None and j.get("final_pre_human_value") != "unknown"]
        if fields:
            requests.append({"app_id": app["app_id"], "paths": fields})
    return requests


def _payload(requests: list[dict[str, Any]], records: dict[str, dict[str, Any]]) -> dict[str, Any]:
    apps = []
    for request in requests:
        record = records[request["app_id"]]
        sources = [
            {"url": item.get("url"), "title": item.get("title"), "excerpt": str(item.get("excerpt", ""))[:1200]}
            for item in record.get("evidence", [])[:6]
        ]
        apps.append({"app_id": request["app_id"], "requested_paths": request["paths"], "official_evidence": sources})
    return {"apps": apps}


def _normalise(value: Any) -> Any:
    values = value if isinstance(value, list) else [value]
    return tuple(sorted(str(item) for item in values))


def simulate(client: Any, sample: list[dict[str, Any]], records: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {record["app_id"]: record for record in records}
    requests = _review_requests(sample)
    raw = client.complete(system=SYSTEM, user=json.dumps(_payload(requests, by_id), ensure_ascii=False), purpose="simulated_reviewer")
    payload = json.loads(raw)
    reviews = payload.get("reviews") if isinstance(payload, dict) else None
    if not isinstance(reviews, list):
        raise ValueError("Simulated reviewer returned no reviews array")
    returned = {item.get("app_id"): item for item in reviews if isinstance(item, dict)}
    judged = pass1_correct = final_correct = 0
    items: list[dict[str, Any]] = []
    sample_by_id = {app["app_id"]: app for app in sample}
    for request in requests:
        review = returned.get(request["app_id"], {})
        findings = {item.get("path"): item for item in review.get("judgements", []) if isinstance(item, dict)}
        source_url = next((item.get("url") for item in by_id[request["app_id"]].get("evidence", []) if item.get("url")), None)
        for path in request["paths"]:
            finding = findings.get(path)
            if not finding or not isinstance(finding.get("ground_truth"), (str, list)):
                continue
            original = next(item for item in sample_by_id[request["app_id"]]["judgements"] if item["path"] == path)
            truth = finding["ground_truth"]
            truth_values = truth if isinstance(truth, list) else [truth]
            if not truth_values or not all(isinstance(value, str) and value in ALLOWED[path] for value in truth_values):
                raise ValueError(f"Simulated reviewer returned a non-canonical value for {request['app_id']} {path}")
            p1 = _normalise(original.get("pass1_value")) == _normalise(truth)
            final = _normalise(original.get("final_pre_human_value")) == _normalise(truth)
            judged += 1
            pass1_correct += int(p1)
            final_correct += int(final)
            items.append({"app_id": request["app_id"], "path": path, "simulated_ground_truth": truth, "pass1_correct": p1, "final_pre_human_correct": final, "source_url": source_url, "reason": str(finding.get("reason", ""))})
    return {
        "mode": "ai_simulated_reviewer_not_human_validation",
        "disclosure": "Time-constrained AI-simulated review using retained official-source excerpts. This is a diagnostic, not a human accuracy claim or substitute for manual validation.",
        "review_scope": sorted(REVIEW_PATHS),
        "judged_fields": judged,
        "pass1_accuracy_percent": round(pass1_correct / judged * 100, 1) if judged else None,
        "final_pre_human_accuracy_percent": round(final_correct / judged * 100, 1) if judged else None,
        "items": items,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the clearly disclosed AI-simulated reviewer diagnostic")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--sample", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    settings = Settings.from_environment()
    if not settings.openrouter_api_key or not settings.openrouter_model:
        raise SystemExit("OPENROUTER_API_KEY and OPENROUTER_MODEL are required")
    records = json.loads(args.dataset.read_text(encoding="utf-8"))
    sample = json.loads(args.sample.read_text(encoding="utf-8"))
    result = simulate(OpenRouterClient(settings.openrouter_api_key, settings.openrouter_model, RequestLedger(1)), sample, records)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "judged_fields": result["judged_fields"]}, indent=2))


if __name__ == "__main__":
    main()
