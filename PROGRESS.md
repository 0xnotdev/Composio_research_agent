# Build Progress Ledger

This file is the authoritative checkpoint ledger. It records verified outcomes, not intentions.

| Checkpoint | Status | Commit(s) | Evidence / notes |
| --- | --- | --- | --- |
| 0 — Access and reality check | Blocked on user credentials | — | Composio account/project key and OpenRouter key are not yet available. No live API calls will be attempted until provided locally in `.env`. |
| 1 — Contracts before code | Complete | Pending commit | 100-app seed is validated, source-policy contract exists, model-output JSONL parser/validator is implemented, and deterministic reconciliation is covered by 14 offline tests. |
| 2 — Evidence pipeline | Complete (offline) | Pending commit | Composio-first and HTTPS fallback transports, official redirect rejection, bounded response handling, deterministic evidence packs, and atomic run-scoped artifacts are covered by 18 offline tests. Live Composio schema confirmation remains a Checkpoint-0 task. |
| 3 — Dual-pass research | In progress (offline) | — | Researcher and critic prompts, strict ordered JSONL parsing, request ledger, citation validation, and reconciliation exist. Live two-app preflight remains blocked on credentials. |
| 4 — Full 100-app run | Not started | — | Blocked until Checkpoint 3 and API credentials. |
| 5 — Analysis and human verification | Complete (offline) | Pending commit | Deterministic distributions, prioritisation, stratified sample selection, and before/after accuracy scoring are implemented. Human judgement remains required after the live run. |
| 6 — Case study and proof | In progress | — | A single-file HTML renderer is tested with fixture data. Batch orchestration and the executable single-app path remain. |
| 7 — Submit readiness | Not started | — | Static deployment is P0; hosted service is P2. |

## Git history

- `c0fbaa6` — `docs: add architecture and checkpoint plan`

## Current blockers

1. Create a Composio account/project and add `COMPOSIO_API_KEY` to a local `.env` file.
2. Add `OPENROUTER_API_KEY` and a preflighted free `OPENROUTER_MODEL` to that file.
3. Do not send keys through chat or commit them.
