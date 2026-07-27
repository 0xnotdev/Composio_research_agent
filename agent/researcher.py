"""Grounded first-pass extraction prompt and batch execution."""

from __future__ import annotations

import json
from typing import Any

from .agent_output import parse_ordered_jsonl
from .evidence_packer import EvidencePack
from .llm_client import OpenRouterClient
from .models import AppSeed, EvidenceSource


RESEARCHER_SYSTEM_PROMPT = """You are a product-integration research analyst.
Use only the supplied official-source excerpts. Never use outside knowledge, memory,
or assumptions. Produce strict JSONL only: exactly one JSON object per requested app,
in supplied order, with no markdown and no prose.

Every non-null factual field must include citations containing one or more supplied E##
excerpt IDs. If evidence does not directly support a field, return null with an empty
citation list and confidence 'insufficient_evidence'. Do not infer OAuth, pricing,
API breadth, or MCP support. A CLI/open-source project can be not_applicable rather
than forced into a hosted-SaaS answer.

Field wrapper format: {"value": <value-or-null>, "citations": ["E01"], "confidence": <string>, "note": <optional-string>}.
Return these fields: app_id, one_liner, auth_methods, credential_path, gating_reasons,
api_surface.protocols, api_surface.breadth, api_surface.documented,
mcp.official_vendor_mcp, mcp.public_mcp_exists, extras.webhooks, extras.sandbox,
extras.api_access_tier, viability.technical, viability.blockers.
Use canonical values: auth_methods oauth2/api_key/basic/token/other/none/unknown;
credential_path self_serve/paid_or_admin_gated/partner_or_sales_gated/unknown/not_applicable;
protocols rest/graphql/rest_and_graphql/other/none_public/unknown/not_applicable;
breadth narrow/moderate/broad/unknown/not_applicable; yes/no/unknown for boolean-like
fields; technical viability ready/workaround_needed/no_public_api/not_applicable/unknown.
"""


def build_researcher_user_prompt(
    apps: list[AppSeed], packs: dict[str, EvidencePack], sources: dict[str, EvidenceSource]
) -> str:
    payload: list[dict[str, Any]] = []
    for app in apps:
        payload.append(
            {
                "app_id": app.app_id,
                "name": app.name,
                "category": app.category,
                "evidence": packs[app.app_id].as_prompt_payload(sources),
            }
        )
    return json.dumps({"apps": payload}, ensure_ascii=False, separators=(",", ":"))


def research_batch(
    client: OpenRouterClient,
    apps: list[AppSeed],
    packs: dict[str, EvidencePack],
    sources: dict[str, EvidenceSource],
) -> list[dict[str, Any]]:
    raw = client.complete(
        system=RESEARCHER_SYSTEM_PROMPT,
        user=build_researcher_user_prompt(apps, packs, sources),
        purpose="researcher_batch",
    )
    return parse_ordered_jsonl(raw, [app.app_id for app in apps])
