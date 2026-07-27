"""Independent adversarial extraction prompt and batch execution."""

from __future__ import annotations

import json
from typing import Any

from .agent_output import parse_ordered_jsonl
from .evidence_packer import EvidencePack
from .llm_client import OpenRouterClient
from .models import AppSeed, EvidenceSource
from .researcher import RESEARCHER_SYSTEM_PROMPT


CRITIC_SYSTEM_PROMPT = RESEARCHER_SYSTEM_PROMPT + """
You are now the adversarial critic, not a reviewer who rubber-stamps another analyst.
Independently derive each answer from the excerpts before looking at the researcher
record. Then emit your own record in the exact same schema plus a disagreements list.
Each disagreement item must contain field, reason, and cited excerpt IDs. Flag claims
that are unsupported even if you would otherwise agree. Do not copy unsupported values.
"""


def build_critic_user_prompt(
    apps: list[AppSeed],
    packs: dict[str, EvidencePack],
    sources: dict[str, EvidenceSource],
    researcher_records: list[dict[str, Any]],
) -> str:
    first_pass = {record["app_id"]: record for record in researcher_records}
    payload: list[dict[str, Any]] = []
    for app in apps:
        payload.append(
            {
                "app_id": app.app_id,
                "name": app.name,
                "category": app.category,
                "evidence": packs[app.app_id].as_prompt_payload(sources),
                "researcher_record": first_pass[app.app_id],
            }
        )
    return json.dumps({"apps": payload}, ensure_ascii=False, separators=(",", ":"))


def critique_batch(
    client: OpenRouterClient,
    apps: list[AppSeed],
    packs: dict[str, EvidencePack],
    sources: dict[str, EvidenceSource],
    researcher_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    raw = client.complete(
        system=CRITIC_SYSTEM_PROMPT,
        user=build_critic_user_prompt(apps, packs, sources, researcher_records),
        purpose="critic_batch",
    )
    return parse_ordered_jsonl(raw, [app.app_id for app in apps])
