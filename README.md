# Composio 100-App Buildability Audit

An evidence-grounded research pipeline for the Composio Product Ops take-home. It audits the assigned 100 apps from official public documentation, runs independent researcher and critic passes, validates citations in code, preserves conflicts, calculates prioritisation, and renders a self-contained HTML case study.

## Safety and research rules

- The pipeline accepts only official vendor docs, official product/developer pages, or path-scoped official repositories.
- A populated field without a retained excerpt citation is nulled rather than published.
- Researcher/critic agreement is `corroborated_primary`, not human verification.
- The final accuracy claim comes only from the manually judged 12-app sample.
- Real keys belong only in `.env`, which is ignored by Git.

## Setup

1. Create a Composio project and obtain its project API key.
2. Obtain an OpenRouter key and choose a currently available free model after preflight.
3. Copy `.env.example` to `.env` and fill `COMPOSIO_API_KEY`, `OPENROUTER_API_KEY`, and `OPENROUTER_MODEL`.
4. Run the offline test suite:

```powershell
python -m unittest discover -s tests -v
```

If `python` is unavailable on PATH in Codex Desktop, use its bundled runtime documented by the desktop environment.

## Run order

First inspect the live Composio search-tool schema and run only two representative apps:

```powershell
python -m agent.pipeline preflight --apps slack github --run-id preflight-1
```

Inspect raw evidence, citations, validator errors, and Composio transport behavior under `data/runs/preflight-1/`. Only then run all 100:

```powershell
python -m agent.pipeline run --run-id audit-1
```

Render the static page after completing human verification:

```powershell
python -m agent.render_case_study --dataset data/runs/audit-1/dataset_final.json --analytics data/runs/audit-1/analytics.json --verification data/runs/audit-1/verification_results.json --output site/index.html --generated-at 2026-07-27
```

Complete the generated `verification_sample.json` using the linked official documentation. For each reviewed field, enter the grounded value, mark whether pass one and the reconciled pre-human value are correct, and retain the source URL. Then calculate the displayed accuracy figures deterministically:

```powershell
python -m agent.verify_sample --sample data/runs/audit-1/verification_sample.json --output data/runs/audit-1/verification_results.json
```

To regenerate an untouched worksheet using the highest-coverage app in each category plus two difficult cases, run:

```powershell
python -m agent.create_verification_sample --dataset data/runs/audit-1/dataset_final.json --output data/runs/audit-1/verification_sample.json
```

The one-app proof reuses the exact pipeline:

```powershell
python research_one_app.py "Slack" --run-id proof-slack
```

It intentionally accepts only an app from the assigned set: arbitrary names would make an “official source” claim unsafe without an approved domain policy.

## Artifacts

- `data/runs/<run-id>/raw_evidence/` — source text and fetch outcomes.
- `evidence_packs/` — bounded excerpts sent to the models.
- `passes/` — raw researcher and critic outputs.
- `dataset_final.json` — reconciled records with audit history.
- `analytics.json` — all displayed numbers and prioritisation.
- `verification_sample.json` — 12-app manual review worksheet.
- `logs/event_log.jsonl` — append-only execution events.

See `ARCHITECTURE.md`, `PLAN.md`, `BUILD_HANDOFF.md`, and `PROGRESS.md` for the full implementation contract and current checkpoint status.

## Static deployment

`site/index.html` is self-contained and can be opened directly. The included GitHub Actions workflow deploys `site/` after GitHub Pages is set to **GitHub Actions** in repository settings. The expected public address is `https://0xnotdev.github.io/Composio_research_agent/`.
