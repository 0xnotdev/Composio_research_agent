"""Resumable orchestration for evidence → dual pass → reconciliation → artifacts."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from itertools import islice
from pathlib import Path
from typing import Any, Iterable

from .analytics import calculate_analytics
from .config import PROJECT_ROOT, Settings
from .composio_catalog import ComposioCatalogClient, cross_check
from .critic import critique_batch
from .evidence_fetcher import ComposioSearchFetcher, HttpFetcher, ResilientFetcher, acquire_official_evidence, acquisition_to_dict
from .evidence_packer import build_evidence_pack
from .llm_client import OpenRouterClient, RequestLedger
from .models import AppSeed, EvidenceSource
from .reconcile import reconcile_passes
from .researcher import research_batch
from .seed import load_seeds
from .source_policy import SourcePolicy
from .storage import RunStore, utc_now
from .validator import validate_pass_record
from .verification import select_verification_sample


def chunks(items: list[AppSeed], size: int = 6) -> Iterable[list[AppSeed]]:
    iterator = iter(items)
    while batch := list(islice(iterator, size)):
        yield batch


class ResearchPipeline:
    def __init__(self, store: RunStore, policy: SourcePolicy, fetcher: Any, client: Any, request_limit: int, catalog_client: Any | None = None) -> None:
        self.store, self.policy, self.fetcher, self.client, self.request_limit, self.catalog_client = store, policy, fetcher, client, request_limit, catalog_client

    def run(self, seeds: list[AppSeed]) -> list[dict[str, Any]]:
        if (self.store.path / "dataset_final.json").exists():
            return self.store.read_json("dataset_final.json")
        self.store.write_json("run_manifest.json", {"started_at": utc_now(), "seed_count": len(seeds), "source_policy_version": self.policy.version, "request_limit": self.request_limit})
        source_sets: dict[str, dict[str, EvidenceSource]] = {}
        packs = {}
        for seed in seeds:
            acquisitions = acquire_official_evidence(seed, self.fetcher, self.policy)
            self.store.write_json(f"raw_evidence/{seed.app_id}.json", [acquisition_to_dict(acquisition) for acquisition in acquisitions])
            sources = {acquisition.source.source_id: acquisition.source for acquisition in acquisitions if acquisition.source}
            source_sets[seed.app_id] = sources
            packs[seed.app_id] = build_evidence_pack(sources.values())
            self.store.write_json(f"evidence_packs/{seed.app_id}.json", {"excerpts": [asdict(excerpt) for excerpt in packs[seed.app_id].excerpts], "omitted_characters": packs[seed.app_id].omitted_characters})
            failures = [acquisition.failure for acquisition in acquisitions if acquisition.failure]
            transports = sorted({acquisition.transport for acquisition in acquisitions})
            self.store.append_event("evidence", "ok" if sources else "failed", app_id=seed.app_id, transport=",".join(transports), failure=" | ".join(failures) if failures else None)

        final_records: list[dict[str, Any]] = []
        for batch_index, batch in enumerate(chunks(seeds)):
            first_raw = research_batch(self.client, batch, packs, source_sets)
            critic_raw = critique_batch(self.client, batch, packs, source_sets, first_raw)
            self.store.write_json(f"passes/researcher_{batch_index:02d}.json", first_raw)
            self.store.write_json(f"passes/critic_{batch_index:02d}.json", critic_raw)
            for seed, first, critic in zip(batch, first_raw, critic_raw, strict=True):
                evidence_ids = {excerpt.excerpt_id for excerpt in packs[seed.app_id].excerpts}
                first_checked = validate_pass_record(first, seed.app_id, evidence_ids)
                critic_checked = validate_pass_record(critic, seed.app_id, evidence_ids)
                evidence = [
                    {"id": excerpt.excerpt_id, "url": source_sets[seed.app_id][excerpt.source_id].url, "title": source_sets[seed.app_id][excerpt.source_id].title, "excerpt": excerpt.text}
                    for excerpt in packs[seed.app_id].excerpts
                ]
                final = reconcile_passes(first_checked.record, critic_checked.record, evidence)
                final.update({"name": seed.name, "category": seed.category, "hint": seed.hint, "composio_cross_check": {"match_status": "not_run", "notes": "catalog cross-check pending"}})
                final["audit"]["validation_errors"] = {"researcher": list(first_checked.errors), "critic": list(critic_checked.errors)}
                final_records.append(final)
                self.store.append_event("reconcile", "ok", app_id=seed.app_id, researcher_errors=len(first_checked.errors), critic_errors=len(critic_checked.errors))
        if self.catalog_client is not None:
            try:
                cross_check(final_records, self.catalog_client.list_all())
                self.store.append_event("composio_cross_check", "ok")
            except RuntimeError as error:
                self.store.append_event("composio_cross_check", "failed", error=str(error))
        self.store.write_json("dataset_final.json", final_records)
        self.store.write_json("analytics.json", calculate_analytics(final_records))
        self.store.write_json("verification_sample.json", select_verification_sample(final_records))
        return final_records


def build_live_pipeline(run_id: str, settings: Settings) -> ResearchPipeline:
    if not settings.composio_api_key or not settings.openrouter_api_key or not settings.openrouter_model:
        raise RuntimeError("Live execution requires COMPOSIO_API_KEY, OPENROUTER_API_KEY, and OPENROUTER_MODEL in .env")
    store = RunStore(PROJECT_ROOT / "data/runs", run_id)
    primary = ComposioSearchFetcher(settings.composio_api_key, settings.composio_api_base)
    fetcher = ResilientFetcher(primary, HttpFetcher())
    client = OpenRouterClient(settings.openrouter_api_key, settings.openrouter_model, RequestLedger(settings.request_limit))
    catalog_client = ComposioCatalogClient(settings.composio_api_key, settings.composio_api_base)
    return ResearchPipeline(store, SourcePolicy.load(PROJECT_ROOT / "data/app_source_policy.json"), fetcher, client, settings.request_limit, catalog_client)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Composio 100-app buildability audit")
    parser.add_argument("command", choices=("preflight", "run"))
    parser.add_argument("--run-id", default="audit-20260727")
    parser.add_argument("--apps", nargs="*", help="app IDs for a small preflight; default is Slack and GitHub")
    args = parser.parse_args()
    seeds = load_seeds(PROJECT_ROOT / "data/apps_100.json")
    if args.command == "preflight":
        wanted = args.apps or ["slack", "github"]
        seeds = [seed for seed in seeds if seed.app_id in set(wanted)]
        if len(seeds) != len(wanted):
            raise SystemExit("Unknown app ID in --apps")
    pipeline = build_live_pipeline(args.run_id, Settings.from_environment())
    records = pipeline.run(seeds)
    print(json.dumps({"run_id": args.run_id, "records": len(records), "output": str(pipeline.store.path)}, indent=2))


if __name__ == "__main__":
    main()
