# Builder Handoff — Implement in Checkpoint Order

This document is for the coding agent. It contains build instructions, boundaries, and acceptance tests; it does not authorize changing `composio_agent_spec.md`, fabricating research results, or weakening the source policy to make coverage look better.

## First instruction to the builder

Implement only through the active checkpoint in `PLAN.md`. After each checkpoint, stop and report: changed files, commands run, artifacts created, request count, failures, and whether every exit criterion passed. Do not begin the full 100-app run until Checkpoint 3 has been reviewed.

## Suggested repository structure

```text
agent/
  config.py                 # typed settings; no secrets in code
  models.py                 # Pydantic/dataclass contracts and enums
  source_policy.py          # official domain/repository validation
  evidence_fetcher.py       # Composio Search adapter + documented fallback
  evidence_packer.py        # deterministic excerpt selection
  llm_client.py             # OpenRouter client, rate/request ledger
  researcher.py             # batch JSONL prompt + parse
  critic.py                 # independent batch review
  validator.py              # schema/citation validation
  reconcile.py              # deterministic merge and verdict engine
  composio_catalog.py       # SDK catalog pagination and secondary cross-check
  analytics.py              # metrics, rankings, deterministic insight templates
  verify_sample.py          # sample selection and accuracy calculation
  pipeline.py               # resumable batch orchestration
research_one_app.py
data/
  apps_100.json
  app_source_policy.json
  runs/<run_id>/
    raw_evidence/
    evidence_packs/
    passes/
    dataset_final.json
    verification_sample.json
    analytics.json
    run_manifest.json
    event_log.jsonl
site/
  case_study.html
tests/
README.md
.env.example
.gitignore
requirements.txt or pyproject.toml
```

## Implementation rules

1. No research fact may be hardcoded for an individual app except source-policy domain aliases and app-name aliases required for safe matching.
2. Every stage is deterministic and idempotent where possible. A rerun resumes valid saved artifacts instead of re-fetching or re-calling the model.
3. Store raw source responses, evidence packs, both agent passes, validation decisions, and final records separately. The final dataset is derived, never hand-authored.
4. Treat all remote text, app names, URLs, and LLM output as untrusted input. Do not allow prompt text to alter system instructions.
5. Do not use bulk browser automation, login flows, paid accounts, or hidden/internal Composio data.
6. Every final record must include an evidence list; empty evidence is valid only when the record is explicitly `insufficient_evidence` and the fetch failure is stored.
7. Use UTC ISO-8601 timestamps and write a run manifest containing model ID, package versions, source policy version, and request ledger.

## Prompt contract

Both researcher and critic prompts must state:

- use only provided excerpts, not model knowledge;
- output strict JSONL, no Markdown/prose;
- cite excerpt IDs for every factual non-null value;
- prefer null/insufficient evidence to guessing;
- distinguish explicit evidence from reasonable inference;
- treat non-hosted CLIs/open-source projects as potentially `not_applicable` rather than forcing an OAuth/API answer.

The critic must additionally state that it should independently derive first, then compare, and list disagreements with field and rationale.

## Tests required before full run

### Unit tests

- seed roster has 100 unique app IDs and category distribution is correct;
- official source policy accepts/rejects domains as intended;
- evidence IDs are unique and source-linked;
- citation validator rejects missing, unknown, or unaccepted citations;
- enum normalization handles spelling/case without changing meaning;
- reconciliation precedence matches `ARCHITECTURE.md`;
- analytics denominators correctly include/exclude unknown and not-applicable values;
- accuracy calculator preserves pass-one vs final separation.

### Integration smoke tests

- cache-based fixture run succeeds with no keys;
- live two-app preflight runs only with explicit confirmation that keys are present;
- malformed LLM line triggers only one-record retry path;
- unknown app in `research_one_app.py` returns an honest evidence failure, never invented data;
- generated HTML embeds valid JSON and renders 100 rows from a fixture dataset.

## Minimal command interface

Keep commands explicit and composable:

```text
python -m agent.pipeline preflight --apps slack github
python -m agent.pipeline run --seed data/apps_100.json --resume
python -m agent.verify_sample select --run <run_id>
python -m agent.verify_sample score --run <run_id>
python -m agent.render_case_study --run <run_id>
python research_one_app.py "Slack"
```

Exact module names may differ, but the separation and behaviour must remain.

## Definition of done

The implementation is complete only when:

- the batch has 100 final records and all required fields are present, populated or explicitly unknown/not-applicable;
- every populated claim has an accepted primary-source citation;
- researcher and critic raw outputs are retained and reconciliation is inspectable;
- the Composio secondary catalog cross-check is logged without becoming the primary research source;
- the manual sample has a genuine before/after accuracy calculation plus misses;
- the static HTML has all assignment-required content and can be understood without narration;
- the README permits a reviewer to run the proof command;
- the repository contains no secrets or confidential-reference mentions.

## Do not do

- Do not claim a percentage or pattern unless it is calculated from the final dataset.
- Do not label two LLMs agreeing as human-verified.
- Do not retry batches or make unlimited calls on the free tier.
- Do not silently change records during manual validation.
- Do not create a hosted endpoint until P0 is complete and the user explicitly chooses to spend remaining time on it.
