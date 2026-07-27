"""Resumable orchestration for evidence → dual pass → reconciliation → artifacts."""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
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


def chunks(items: list[AppSeed], size: int = 8) -> Iterable[list[AppSeed]]:
    iterator = iter(items)
    while batch := list(islice(iterator, size)):
        yield batch


def is_valid_pass_batch(records: Any, batch: list[AppSeed]) -> bool:
    """Only reuse a completed model batch when it exactly matches its seeds."""
    return (
        isinstance(records, list)
        and len(records) == len(batch)
        and all(isinstance(record, dict) and record.get("app_id") == seed.app_id for record, seed in zip(records, batch, strict=True))
    )


class ResearchPipeline:
    def __init__(self, store: RunStore, policy: SourcePolicy, fetcher: Any, client: Any, request_limit: int, catalog_client: Any | None = None) -> None:
        self.store, self.policy, self.fetcher, self.client, self.request_limit, self.catalog_client = store, policy, fetcher, client, request_limit, catalog_client

    def run(self, seeds: list[AppSeed]) -> list[dict[str, Any]]:
        if (self.store.path / "dataset_final.json").exists():
            return self.store.read_json("dataset_final.json")
        self.store.write_json("run_manifest.json", {"started_at": utc_now(), "seed_count": len(seeds), "source_policy_version": self.policy.version, "request_limit": self.request_limit})
        source_sets: dict[str, dict[str, EvidenceSource]] = {}
        packs = {}
        pending_evidence: dict[str, tuple[AppSeed, str]] = {}
        for seed in seeds:
            raw_path = f"raw_evidence/{seed.app_id}.json"
            if self.store.relative_path(raw_path).exists():
                cached = self.store.read_json(raw_path)
                cached_items = cached if isinstance(cached, list) else [cached]
                sources = {
                    item["source"]["source_id"]: EvidenceSource(**item["source"])
                    for item in cached_items
                    if isinstance(item, dict) and isinstance(item.get("source"), dict)
                }
                weak_cache = not sources or any(len(source.text.strip()) < 350 or source.text.strip().casefold().startswith('{"ok":false') for source in sources.values())
                if weak_cache:
                    pending_evidence[seed.app_id] = (seed, "refreshed")
                else:
                    self.store.append_event("evidence", "resumed", app_id=seed.app_id, source_count=len(sources))
            else:
                pending_evidence[seed.app_id] = (seed, "new")
                sources = {}
            source_sets[seed.app_id] = sources

        acquired: dict[str, tuple[list[Any], str]] = {}
        if pending_evidence:
            # Network calls are independent. Keep writes on the main thread so the
            # append-only audit log stays uncorrupted.
            with ThreadPoolExecutor(max_workers=5, thread_name_prefix="evidence") as pool:
                futures = {
                    pool.submit(acquire_official_evidence, seed, self.fetcher, self.policy): (app_id, state)
                    for app_id, (seed, state) in pending_evidence.items()
                }
                for future in as_completed(futures):
                    app_id, state = futures[future]
                    try:
                        acquired[app_id] = (future.result(), state)
                    except Exception as error:
                        acquired[app_id] = ([], state)
                        self.store.append_event("evidence", "failed", app_id=app_id, error=f"unexpected acquisition failure: {type(error).__name__}")
        for seed in seeds:
            outcome = acquired.get(seed.app_id)
            if outcome is not None:
                acquisitions, state = outcome
                raw_path = f"raw_evidence/{seed.app_id}.json"
                self.store.write_json(raw_path, [acquisition_to_dict(acquisition) for acquisition in acquisitions])
                source_sets[seed.app_id] = {acquisition.source.source_id: acquisition.source for acquisition in acquisitions if acquisition.source}
                failures = [acquisition.failure for acquisition in acquisitions if acquisition.failure]
                transports = sorted({acquisition.transport for acquisition in acquisitions})
                status = state if state == "refreshed" else ("ok" if source_sets[seed.app_id] else "failed")
                self.store.append_event("evidence", status, app_id=seed.app_id, source_count=len(source_sets[seed.app_id]), transport=",".join(transports), failure=" | ".join(failures) if failures else None)
            packs[seed.app_id] = build_evidence_pack(source_sets[seed.app_id].values())
            self.store.write_json(f"evidence_packs/{seed.app_id}.json", {"excerpts": [asdict(excerpt) for excerpt in packs[seed.app_id].excerpts], "omitted_characters": packs[seed.app_id].omitted_characters})

        final_records: list[dict[str, Any]] = []
        for batch_index, batch in enumerate(chunks(seeds)):
            researcher_path = f"passes/researcher_{batch_index:02d}.json"
            critic_path = f"passes/critic_{batch_index:02d}.json"
            first_raw = self.store.read_json(researcher_path) if self.store.relative_path(researcher_path).exists() else None
            if not is_valid_pass_batch(first_raw, batch):
                first_raw = research_batch(self.client, batch, packs, source_sets)
                self.store.write_json(researcher_path, first_raw)
            else:
                self.store.append_event("researcher", "resumed", batch=batch_index, record_count=len(first_raw))
            critic_raw = self.store.read_json(critic_path) if self.store.relative_path(critic_path).exists() else None
            if not is_valid_pass_batch(critic_raw, batch):
                critic_raw = critique_batch(self.client, batch, packs, source_sets, first_raw)
                self.store.write_json(critic_path, critic_raw)
            else:
                self.store.append_event("critic", "resumed", batch=batch_index, record_count=len(critic_raw))
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
