# Build Progress Ledger

This is the verified checkpoint record for the take-home implementation. The original `composio_agent_spec.md` is unchanged.

| Checkpoint | Status | Verified result |
| --- | --- | --- |
| 0 - Access and contracts | Complete | Local-only keys work; Composio search/fetch schemas were inspected; a free OpenRouter JSON-capable model was preflighted. |
| 1 - Data and source policy | Complete | The roster contains 100 unique apps across 10 categories; official-domain policy, bounded evidence packs, redaction, and atomic artifacts are implemented. |
| 2 - Evidence acquisition | Complete | `audit-2` retained raw acquisition artifacts and evidence packs for all 100 apps. Failed or empty retrieval is retained as an explicit outcome. |
| 3 - Dual-pass agent | Complete | Researcher and critic passes are citation-validated, deterministic reconciliation preserves conflicts, and malformed model batches are split and recovered safely. |
| 4 - Full audit | Complete | `data/runs/audit-2/dataset_final.json` contains exactly 100 distinct reconciled records. It has no invalid citation references and no boolean MCP values outside the contract. |
| 5 - Analysis and verification | Complete, pending human judgement | Analytics and a stratified 12-app worksheet exist. The deterministic scorer is implemented; human correctness decisions have not been invented. |
| 6 - Case study and proof | Complete, pending hosted visual QA | `site/index.html` has 100 table rows, filters, official evidence links, and the single-app proof command. |
| 7 - Submit readiness | Awaiting bounded manual gate | GitHub Pages workflow is present; reviewer must complete the 12-app sample and enable Pages if a public link is required. |

## Current audit snapshot

- Records: **100**; categories: **10**; manual-verification apps: **12**.
- Supported-field coverage: **64.7%**; unresolved uncertainty is preserved, not filled with assumptions.
- Buildability: **68 ready now**, **10 access constrained**, **22 insufficient evidence**.
- Credential paths: **70 self-serve**, **9 paid/admin gated**, **3 partner/sales gated**, **17 unknown**, **1 not applicable**.
- The static page shows verification as pending until the worksheet is manually judged; it makes no unearned accuracy claim.

## Automated verification performed

- `python -m unittest discover -s tests -q`: **33 passing tests**.
- Full-run integrity: 100 unique IDs; zero invalid citations in either raw agent pass; 100 rendered table rows.
- Secret safety: `.env` and all run artifacts are ignored by Git. Only the self-contained static page is prepared for publication.

## Exact remaining human work

1. Open `data/runs/audit-2/verification_sample.json`, judge its 12 x 6 fields against official docs, and save it.
2. Run `python -m agent.verify_sample --sample data/runs/audit-2/verification_sample.json --output data/runs/audit-2/verification_results.json`.
3. Re-render `site/index.html` with `--verification data/runs/audit-2/verification_results.json`.
4. In GitHub repository settings, set Pages source to **GitHub Actions**, then open the published page and sample evidence links.
