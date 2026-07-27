# Build Progress Ledger

This file is the authoritative checkpoint ledger. It records verified outcomes, not intentions.

| Checkpoint | Status | Commit(s) | Evidence / notes |
| --- | --- | --- | --- |
| 0 — Access and reality check | Complete | Pending commit | Replacement keys are local-only. Free model selected by live JSON test. Composio fetch/search schemas were inspected and adapter contracts corrected. |
| 1 — Contracts before code | Complete | Pending commit | 100-app seed is validated, source-policy contract exists, model-output JSONL parser/validator is implemented, and deterministic reconciliation is covered by 14 offline tests. |
| 2 — Evidence pipeline | Complete (offline) | Pending commit | Composio-first and HTTPS fallback transports, official redirect rejection, bounded response handling, deterministic evidence packs, and atomic run-scoped artifacts are covered by 18 offline tests. Live Composio schema confirmation remains a Checkpoint-0 task. |
| 3 — Dual-pass research | Complete | Pending commit | 26 offline tests pass. Slack and GitHub live preflights passed after source-discovery refinement; no parser or citation-validation errors. |
| 4 — Full 100-app run | Not started | — | Blocked until Checkpoint 3 and API credentials. |
| 5 — Analysis and human verification | Complete (offline) | Pending commit | Deterministic distributions, prioritisation, stratified sample selection, and before/after accuracy scoring are implemented. Human judgement remains required after the live run. |
| 6 — Case study and proof | Complete (offline) | Pending commit | Static renderer, runnable `research_one_app.py`, batch orchestration, README, catalog cross-check module, and a fixture end-to-end run exist. Live API proof is blocked on credentials. |
| 7 — Submit readiness | Not started | — | Static deployment is P0; hosted service is P2. |

## Git history

- `c0fbaa6` — `docs: add architecture and checkpoint plan`
- `124781b` — `feat: establish evidence and validation core`
- `a0171e4` — `feat: add resilient evidence acquisition artifacts`
- `b55e81d` — `feat: add analysis verification and case study renderer`
- `5a045c6` — `feat: add runnable audit orchestration`

## Latest verification

- Offline suite: **25 passing tests** (`python -m unittest discover -s tests -v`).
- Offline fixture: a complete one-app evidence → researcher → critic → citation validation → reconciliation → artifacts run passed.
- Python compilation: `python -m compileall -q agent research_one_app.py` passed.
- GitHub: commits through `5a045c6` were pushed to `origin/master` on 2026-07-27.

## Current blockers

1. Create a Composio account/project and add `COMPOSIO_API_KEY` to a local `.env` file.
2. Add `OPENROUTER_API_KEY` and a preflighted free `OPENROUTER_MODEL` to that file.
3. Do not send keys through chat or commit them.
