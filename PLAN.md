# Execution Plan — 100-App Buildability Audit

This is the operational plan for a six-to-seven-hour, agent-assisted build. It is intentionally checkpoint-based: do not start the next stage until the current stage’s exit criteria pass. The original `composio_agent_spec.md` remains untouched.

## Operating principle

Work from the submission backward. The page is the graded artifact, but it may only contain claims backed by the persisted dataset and validation log. Build the smallest reliable system that can generate all of it.

## Checkpoint map

| Checkpoint | Outcome | Time box | Approval needed | Exit criteria |
| --- | --- | ---: | --- | --- |
| 0 — Access and reality check | Keys, dependencies, and actual Composio tool schemas known | 25 min | Yes, major gate | Composio account/key works, OpenRouter model responds, one official page fetch works, no secret is committed. |
| 1 — Contracts before code | Schema, source policy, fixtures, and audit model locked | 25 min | No | JSON Schema validates a sample record; 100-app seed validates; field enums and confidence meanings are frozen. |
| 2 — Evidence pipeline | Official-source collection and evidence packs work for difficult + ordinary apps | 50 min | No | Five-app smoke test archives raw sources, rejects non-official URLs, and produces citation IDs. |
| 3 — Dual-pass research | Researcher, critic, validator, and reconciliation work end-to-end | 60 min | Yes, major gate | Two-app preflight produces valid citations, disagreement handling, and no ungrounded populated fields. |
| 4 — Full 100-app run | Complete, resumable, 100-record final dataset exists | 75 min | No | 100/100 final records, all failures explicit, event log and request count persisted. |
| 5 — Analysis and manual verification | Exact portfolio metrics plus audited accuracy delta | 45 min | No | 12-app sample spans all categories; pass-one and final comparisons are recorded before edits. |
| 6 — Case study and proof | Reviewer can understand, inspect, and run the work | 65 min | Yes, pre-submission gate | Single HTML opens locally, has all mandated sections, table has 100 rows, and CLI proof runs. |
| 7 — Submit readiness | Repo and public static deployment are presentable | 20 min | Yes, final go/no-go | README works from clean clone, page deployed, links and evidence sampled, secrets absent. |

Total planned time: approximately 6 hours 5 minutes. The remaining time is contingency for rate limits, failed pages, deployment, and visual fixes.

## Checkpoint 0 — Access and reality check

### Actions

1. Create a Composio project and store its project API key only in local `.env`.
2. Create/confirm an OpenRouter key. Select one free model with sufficient context and reliable JSON output; record its exact model ID in the run manifest.
3. Install the current Python dependencies in an isolated virtual environment.
4. Inspect the actual schemas for `COMPOSIO_SEARCH_WEB` and `COMPOSIO_SEARCH_FETCH_URL_CONTENT` rather than coding from a remembered interface.
5. Make one benign fetch against an official documentation URL and make one OpenRouter structured-output test.
6. Create `.env.example`, `.gitignore`, and a redaction scan command before any data run.

### Stop conditions

- If a Composio account cannot be created or its search tool cannot execute, record the exact limitation. Use the planned public-HTTP fallback for retrieval and retain Composio catalog cross-check as soon as the project key works.
- If a chosen free model cannot return valid JSON for the two-app preflight, change models now—never halfway through the 100-app run.

## Checkpoint 1 — Contracts before code

The builder must create contracts before integrations:

- `AppSeed`, `EvidenceSource`, `EvidenceExcerpt`, `ResearchPass`, `FinalRecord`, `VerificationJudgement`, and `RunManifest` models;
- versioned JSON Schema for final records;
- enum lists for auth, credential path, API protocol/breadth, MCP state, viability, blockers, and confidence;
- append-only JSONL event log with time, stage, app id/batch id, status, request count, and error category;
- deterministic file layout for run-specific artifacts.

**Key correctness rule:** every non-null factual final field needs one or more source excerpts. A source URL alone is insufficient because it cannot prove which statement the agent used.

## Checkpoint 2 — Evidence pipeline

### Smoke-test apps

Use a deliberately varied five-app test set: Salesforce or HubSpot, Slack or Telegram, Shopify, GitHub, and Mermaid CLI or Sherlock. This exercises OAuth, API key/token, commercial gating, structured REST docs, and non-hosted/CLI handling.

### Assertions

- official URL policy accepts vendor docs and official GitHub repositories;
- a search result from a third-party domain is rejected as evidence;
- failed pages are logged with HTTP/transport reason;
- every accepted excerpt has URL, title, retrieval timestamp, source type, text, and a stable `E##` ID;
- evidence packet size stays under its configured limit;
- raw evidence can be re-rendered for a human without using the LLM again.

### Human decision only if needed

If a vendor uses multiple legitimate domains, add the domain to the policy with a short rationale. Do not add broad wildcards that can accept unaffiliated content.

## Checkpoint 3 — Dual-pass research

### Researcher input/output

Input contains: seed metadata, exact evidence snippets, allowed value enums, and an explicit citation requirement. Output is strict JSONL, one object per input app, in the same order.

### Critic input/output

Input contains the same evidence plus researcher JSON. It must independently populate its own proposed fields, cite excerpts, and enumerate field-specific disagreements. It must not merely approve/rewrite the first pass.

### Preflight review

Run only two apps. Inspect all populated fields manually:

- Does every claim have an excerpt that actually supports it?
- Are unavailable facts null rather than inferred?
- Does the critic flag a deliberately injected bad claim?
- Does reconciliation preserve the conflict and refuse unsupported values?
- Are the final record and all raw passes persisted?

Do not proceed to the full batch unless all answers are yes.

## Checkpoint 4 — Full batch execution

### Run order

1. Validate seed roster and create `run_manifest.json`.
2. Fetch and package evidence. Persist per-app success/failure, then resume safely on rerun.
3. Research in batches of six.
4. Critique in batches of six.
5. Validate and reconcile each app independently.
6. Fetch/cross-check the Composio catalog only after independent research is frozen.
7. Write `dataset_final.json`, `dataset_final.jsonl`, `coverage_report.json`, and `request_ledger.json`.

### Completion definition

The batch is complete only when every assigned app has one final record. Completion does not mean every field is known: insufficient evidence, conflicts, non-applicable cases, and fetch failures are legitimate documented outcomes.

### Budget safety

- Hard-stop at 48 OpenRouter requests.
- No whole-batch retry.
- Max eight single-app repairs, selected first by required-field coverage and evidence availability.
- No final prose-generation call; all quantitative insights come from code.

## Checkpoint 5 — Analysis and human verification

### Portfolio analysis

Generate statistics from final records only. Include denominators, exclude `not_applicable` only when explicitly explained, and show unknown/conflict counts next to headline metrics.

### Verification sample selection

Select exactly twelve before inspecting their final records in detail:

- one app per each of the ten assignment categories;
- highest-conflict or lowest-coverage app;
- one nonstandard app type, severe access gate, or thin-documentation app.

For each sample app, judge these field groups against the archived official sources: auth, credential path, API surface, official MCP, and viability. Record pass-one and final correctness separately, plus comments.

### Avoiding a misleading accuracy claim

The sample must be captured as an immutable first draft. If you correct a final record after checking it, keep both `final_pre_human` and `final_post_human` and state that the page’s accuracy metric refers to the pre-human version. Never retroactively improve the agent’s score by changing the answer key.

## Checkpoint 6 — Case study and runnable proof

### Required page sections

1. **Headline:** clear claim, coverage, retrieval date, and 3–5 computed insights.
2. **Prioritization:** easy wins, access-constrained prospects, and uncertainty caveat.
3. **Agent:** compact pipeline diagram, roles, input/output, source policy, and human role.
4. **Findings:** filterable 100-row table with app, category, auth, credential path, API, official/public MCP, verdict, confidence, and evidence links.
5. **Verification:** methodology, sample, pass-one vs final accuracy, true hits/misses, and limitations.
6. **Proof:** exact one-command local invocation and expected output.
7. **Limitations:** data freshness, official-source restriction, missing docs, constraints of a static sample, and exclusions/non-applicable tools.

### Definition of good enough visual quality

Clean typography, strong hierarchy, responsive overflow for the matrix, accessible colors, no external runtime dependency, and readable evidence links. No animation, framework, dashboard library, or custom illustration is required.

### CLI proof acceptance

From a clean terminal with documented setup, this must work:

`python research_one_app.py "Slack"`

It must print the final structured record, a concise evidence-backed summary, source URLs, and an explicit failure result for an unknown/non-evidenced app rather than guessing.

## Checkpoint 7 — Submit readiness

### Repository checklist

- README has prerequisites, local setup, environment variables, full-run command, single-app command, outputs, verification method, and limitations.
- `.env`, raw tokens, and account identifiers are absent from Git history and rendered HTML.
- Raw evidence may be omitted from the deployed page if size is large, but final citations and the reproducibility path remain present in the repository.
- `case_study.html` works by opening it directly, without a local server or build tool.

### Deployment checklist

Deploy the static page to any straightforward public static host supported by the chosen repository workflow. GitHub Pages is a reasonable default, but deployment method is not a requirement of the assignment. Open the deployed URL in an incognito/private session, test table filters, sample several evidence links, and verify the page still tells the complete story without narration.

## Scope cuts, in order

If time becomes tight, cut only in this order:

1. live FastAPI/Render endpoint;
2. table sorting/filter bells and whistles (retain readable 100-row table);
3. decorative charts (retain computed numbers/tables);
4. catalog metadata depth beyond matched/not-matched and basic signal;
5. optional extras such as sandbox/webhook fields.

Never cut: all 100 records, source citations, human sample, the before/after accuracy calculation, the headline pattern analysis, the self-contained HTML, or the runnable CLI.
