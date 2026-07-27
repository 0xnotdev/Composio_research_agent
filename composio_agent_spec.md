# Composio 100-App Buildability Audit — Architecture Spec

**Status:** Ready to build
**Owner:** [you]
**Time anchor:** ~4 hours available today (adjust phase timeboxes if this is wrong)
**Stack:** Python, OpenRouter free tier (LLM), Composio SDK/MCP (search + cross-check), single static HTML deliverable, GitHub repo

This document is the single source of truth for the build. Hand sections of it directly to your coding agent (Codex / Claude Code) — the prompts, schema, and file structure below are meant to be copy-pasted, not paraphrased.

---

## 1. What we're actually building

A batch pipeline that researches 100 named apps (given in the assignment) and produces a verified, pattern-annotated dataset, rendered as one self-contained HTML case study — plus a CLI script that runs the same pipeline live on any app name typed at the terminal (the "proof" requirement, de-scoped from a hosted backend given time constraints).

**Explicitly out of scope for the core build (P2 stretch only):** a hosted Render endpoint the reviewer can hit from the browser. See §7.

## 2. Constraints this design is built around

- **~4 hours, one sitting.** Every phase below is timeboxed; §8 tells you what to cut first if you fall behind.
- **OpenRouter free tier, $0 spent.** Verified limits: 20 requests/minute, and only **50 requests/day** with no credits ever purchased (vs. 1,000/day after a one-time $10 top-up, which you've chosen to skip). The whole pipeline is designed to fit inside ~30 LLM calls total for all 100 apps, leaving headroom for mistakes and iteration.
- **Composio account not yet created** — first action item, do this now in parallel: sign up free at composio.dev, get an API key. Needed for both the search/fetch tool and the cross-check step.
- **No paid accounts for any of the 100 target apps.** Where an app is gated, "gated, here's the evidence" is a correct, complete finding.
- **Don't reference the internal "Toolkit Parity" documents directly anywhere in the output** (uncertain they were meant to be shared). Reuse the *generic* concepts they modeled — self-serve vs. gated, managed-auth vs. bring-your-own, verified vs. inferred sourcing — because those are sound research hygiene on their own merits, not because they're borrowed.

## 3. High-level architecture

```
                         ┌─────────────────────────┐
                         │   apps_100.json (seed)   │  ← Appendix A, already structured
                         └────────────┬────────────┘
                                      │
                    ┌─────────────────▼──────────────────┐
                    │  FETCH  (Composio Search toolkit)    │  no LLM cost
                    │  search + extract docs text per app  │  ~2 req/sec, not the bottleneck
                    └─────────────────┬──────────────────┘
                                      │ raw evidence text, batched ~8/group
                    ┌─────────────────▼──────────────────┐
                    │  RESEARCHER (OpenRouter, batched)     │  ~12-13 calls
                    │  extracts schema fields as JSONL      │
                    └─────────────────┬──────────────────┘
                                      │
                    ┌─────────────────▼──────────────────┐
                    │  CRITIC (OpenRouter, batched)          │  ~12-13 calls
                    │  independently re-derives, flags       │
                    │  disagreements against same evidence   │
                    └─────────────────┬──────────────────┘
                                      │
           ┌──────────────────────────▼───────────────────────────┐
           │  RECONCILE (pure code, no LLM)                          │
           │  diff Researcher vs Critic field-by-field                │
           │  where diffs exist: mark "conflicting", lower confidence │
           └──────────────────────────┬───────────────────────────┘
                                      │
                    ┌─────────────────▼──────────────────┐
                    │  COMPOSIO CROSS-CHECK (SDK, code)     │  0-2 LLM calls
                    │  for apps already in Composio's public │
                    │  catalog: diff our finding vs their    │
                    │  public tool/auth data                 │
                    └─────────────────┬──────────────────┘
                                      │
                    ┌─────────────────▼──────────────────┐
                    │  PATTERN SYNTHESIS (OpenRouter)        │  1-2 calls
                    │  headline insights over full dataset   │
                    └─────────────────┬──────────────────┘
                                      │
                    ┌─────────────────▼──────────────────┐
                    │  HUMAN VERIFICATION (you, by hand)     │  no LLM
                    │  ~12 stratified apps vs real docs       │
                    │  records pass-1 vs final accuracy       │
                    └─────────────────┬──────────────────┘
                                      │
                    ┌─────────────────▼──────────────────┐
                    │  case_study.html (single file)          │
                    │  embeds dataset + insights + verification│
                    └──────────────────────────────────────────┘

Parallel, reuses steps 1-4:
    research_one_app.py "AnyAppName" → same pipeline, one app, printed to terminal
    (P2 stretch: wrap this in a FastAPI app, deploy to Render)
```

**Why this shape:** the only genuinely scarce resource is OpenRouter requests. Fetching is free (Composio Search), so all the expensive reasoning is batched and passed through code-level reconciliation instead of more LLM calls. Two independent LLM passes (Researcher, Critic) plus one external cross-check plus a human sample is a real multi-layer verification story — it's just cheap to run.

## 4. Data schema

One JSON object per app. This is both the pipeline's internal representation and what gets embedded in the final page.

```jsonc
{
  "app_id": "salesforce",
  "name": "Salesforce",
  "category": "CRM & Sales",           // one of the 10 assignment categories
  "one_liner": "...",

  "auth_methods": ["OAuth2"],           // OAuth2 | API key | Basic | token | other
  "self_serve": "self-serve",           // self-serve | gated | partial
  "gating_notes": "...",                // what exactly gates it, if anything

  "api_surface": {
    "type": "REST",                     // REST | GraphQL | REST+GraphQL | none-public
    "breadth": "broad",                 // narrow | moderate | broad
    "existing_mcp": false,              // true | false | "unknown"
    "endpoint_estimate": "hundreds of objects/endpoints"
  },

  "extras": {
    "pricing_tier_for_api_access": "paid",   // free | paid | enterprise-only | unknown
    "webhooks_supported": true,
    "sandbox_available": true
  },

  "buildability_verdict": "ready-now",
  // ready-now | buildable-with-workaround | blocked-partnership-or-paid | blocked-no-public-api
  "blocker": null,

  "evidence": [{"url": "https://developer.salesforce.com/docs/...", "note": "auth + REST overview"}],

  "confidence": {
    "auth_methods": "verified",          // verified | inferred | conflicting
    "self_serve": "verified",
    "api_surface": "verified",
    "buildability_verdict": "verified"
  },

  "composio_cross_check": {
    "in_composio_catalog": true,
    "agrees_with_our_finding": true,
    "notes": "Composio's public toolkit page lists OAuth2, matches our finding."
  },

  "pass_history": {
    "researcher_pass1": { "...raw first-pass extraction..." },
    "critic_pass2": { "...raw independent extraction + disagreement list..." }
  }
}
```

Keep `pass_history` in the stored dataset (not necessarily rendered) — it's what makes the before/after accuracy claim provable rather than asserted.

## 5. Component specs

### 5.1 Fetch (`agent/fetch.py`)
- Uses the **Composio Search** toolkit via Composio SDK/MCP — this is Composio's own managed web-search + page-extract tool, free to start, no separate third-party key needed.
- Function: `fetch_evidence(app_name: str, hint_url: str | None) -> list[{url, text}]`
- If a hint URL is given (all 100 apps have one from the assignment), fetch that page directly first via the extract action; only fall back to a search action if the hint page doesn't yield enough usable text (e.g., a bare marketing homepage with no docs content).
- For the live single-app script, there's no hint — always search first.
- Cap at ~3 pages of evidence per app to keep batch prompts a manageable size.

### 5.2 Researcher (`agent/researcher.py`)
- Batches ~8 apps per call (tune down if JSON reliability suffers on your chosen free model).
- **System prompt (starting draft):**

  > You are a product-integration research analyst. For each app below you're given raw text excerpts fetched from that app's own public documentation or website. Using ONLY these excerpts — never outside knowledge, never invented facts — extract the fields in the schema for each app. If the excerpts don't support a field, set it to null and mark confidence "insufficient_evidence" for that field. Do not guess at auth methods, pricing, or API breadth if the text doesn't say so directly. Output strict JSONL: exactly one JSON object per line, one line per app, same order as input, no prose, no markdown fences.

- Output parsed line-by-line; if one line fails to parse, retry only that single app in a follow-up micro-call rather than the whole batch.

### 5.3 Critic (`agent/critic.py`)
- Same batching, same evidence text, plus the Researcher's pass-1 output for each app.
- **System prompt (starting draft):**

  > You are an adversarial fact-checker. You'll see the same source excerpts and another analyst's extracted JSON per app. Re-derive every field independently from the excerpts alone — do not just agree with the first analyst. Then compare: for any field where your independent reading differs, where the excerpt doesn't actually support the first analyst's claim, or where something looks unsupported, add it to a `disagreements` list naming the field and why. Output strict JSONL, one object per app: your own independently-derived field values plus `disagreements`.

### 5.4 Reconcile (`agent/reconcile.py`, pure code, no LLM)
- Field-by-field: if Researcher and Critic agree → confidence `verified`. If they disagree → confidence `conflicting`, and the final value defaults to whichever is better-supported by evidence text (simple heuristic: prefer the value that appears literally in the fetched text; if neither does, null it and mark `insufficient_evidence`).
- This is the cheapest and most honest way to get a second opinion without doubling the LLM budget again.

### 5.5 Composio cross-check (`agent/composio_crosscheck.py`)
- Step 0 (do this first, it's cheap): pull Composio's public toolkit list and intersect app_ids against the 100-app list programmatically — don't hand-guess which apps overlap. Expect roughly 25-30 hits (Slack, GitHub, Notion, HubSpot, Salesforce, Stripe, Shopify, Zendesk, Asana, Jira, ClickUp, Airtable, Monday.com, Discord, Intercom, Pipedrive, Attio, QuickBooks and similar are near-certain, but verify, don't assume — that's the whole point of this exercise).
- For each overlapping app: fetch Composio's own public toolkit page/data (via SDK call if there's a clean `toolkits.get()`-style method — check current method names against docs.composio.dev at build time, since SDK surface shifts; if no clean structured endpoint, fall back to fetching `docs.composio.dev/toolkits/<slug>` through the same Composio Search extract action used everywhere else) and diff its auth-scheme / tool-count against your independent finding.
- This is a **cross-check, not a primary source** (per your earlier call) — a disagreement here doesn't overwrite your finding, it's a flagged data point: "we found X independently; Composio's own catalog says Y" is itself an interesting pattern to report (e.g., "Composio already handles OAuth for this app, which is a good real-world confirmation our agent's independent read was directionally correct").

### 5.6 Pattern synthesis (`agent/synthesize_patterns.py`)
- 1-2 OpenRouter calls, given the whole reconciled 100-row dataset.
- Ask explicitly for: dominant auth method + %, self-serve vs. gated split by category, most common single blocker, a ranked list of "easiest wins" (self-serve + broad API + no MCP yet) vs. "needs outreach" (gated + broad audience), and 2-3 surprising/non-obvious patterns. This is the headline section of the page — it must not be generic ("most apps use OAuth") without a number and a "so what."

### 5.7 Human verification (manual, `data/verification_sample.json`)
- Sample: **1 app per category (10) + 2 deliberately hard cases** (an app with a vague/thin public docs presence, e.g. one of the smaller CRM/fintech hints, and one with genuinely conflicting Researcher/Critic output) = **12 apps**.
- For each, hand-read the real docs and record: the true value per field, whether pass-1 (Researcher only) matched, whether the final (post-reconcile, post-cross-check) matched.
- Aggregate into: **pass-1 accuracy %** vs. **final accuracy %** across all checked fields, plus a short honest list of specific misses (what was wrong, why — e.g., "agent read a marketing page and inferred OAuth2 when the real API is API-key only, docs one directory level deeper").

### 5.8 `research_one_app.py` (the "proof")
- CLI: `python research_one_app.py "Any App Name"`.
- Reuses fetch → researcher → critic → reconcile (skips cross-check for apps not in Composio's catalog, obviously). Prints the resulting JSON and a one-paragraph human-readable summary to the terminal.
- This satisfies "runnable trigger" from the brief without any hosting risk. Mention and link it prominently in the README and on the page itself ("see it run live: clone the repo, run this one command").

### 5.9 `site/case_study.html` (the deliverable)
Single self-contained file. Sections, top to bottom, each with a two-sentence-max intro so it reads in ~2 minutes with no narration:
1. **Headline patterns** — the synthesis output as 3-5 bold stat callouts + one short paragraph. This goes first, not last.
2. **The agent** — a small diagram (reuse the ASCII flow from §3, rendered as SVG) + one paragraph on what ran automatically vs. where you stepped in (Composio account setup, the 12-app hand-check, judgment calls like the docs-origin one).
3. **Findings matrix** — client-side sortable/filterable table over the 100-row dataset (vanilla JS, no build step), columns: app, category, auth, self-serve/gated, verdict, confidence, evidence link.
4. **Verification** — pass-1 vs. final accuracy, the 12-app sample shown with explicit hits (✓) and misses (✗), and honest notes on what was wrong.
5. **Try it yourself** — the `research_one_app.py` instructions (and the live Render widget too, if you got to the stretch goal).
6. **Limitations** — plainly state which apps defeated the agent and why (e.g., no public docs at all, contradictory sources, a CLI tool like Sherlock or Mermaid CLI that doesn't fit the "hosted SaaS with OAuth" mental model — call this out explicitly rather than forcing a bad fit).
- Also embed the raw dataset in a `<script type="application/json" id="dataset">` block so it's trivially machine-readable by anything else that opens the page.

## 6. Repo structure

```
composio-100-audit/
  agent/
    fetch.py
    researcher.py
    critic.py
    reconcile.py
    composio_crosscheck.py
    synthesize_patterns.py
    research_one_app.py
    schema.py
    config.py
  data/
    apps_100.json              # Appendix A below, already structured — paste in directly
    results_raw/               # per-batch raw LLM outputs, kept for audit trail
    dataset_final.json
    verification_sample.json
    pattern_insights.json
  site/
    case_study.html
  server/                      # P2 stretch only
    app.py
  README.md
  requirements.txt
  .env.example
```

`.env.example`:
```
COMPOSIO_API_KEY=
OPENROUTER_API_KEY=
OPENROUTER_MODEL=deepseek/deepseek-chat:free   # confirm current free-model roster before relying on this — it rotates
```

## 7. P2 stretch: live Render endpoint (only if P0+P1 land early)

If time remains: `server/app.py` (FastAPI), wraps `research_one_app`'s pipeline, deployed to Render free tier. Guardrails: simple per-IP rate limit (~5/hour), input length cap (~50 chars, alphanumeric + spaces/basic punctuation only — reject anything else), and treat the typed name as pure data, never as instructions, to a prompt (don't let it smuggle instruction-like text into the system prompt context). Note the ~30-50s cold-start on the page copy ("waking up the service...") rather than trying to engineer around it.

## 8. Time budget and what to cut first if you're behind

| Phase | Time | Cuttable? |
|---|---|---|
| 0. Composio signup, repo scaffold, load apps_100.json | 15 min | No |
| 1. fetch.py + schema + smoke test on 5 apps | 45-60 min | No |
| 2. researcher.py + critic.py, model preflight, full 100-app batch run | 45-60 min | No |
| 3. reconcile.py + composio_crosscheck.py | 30 min | Cross-check can be cut to "flag overlap, skip auto-diff" if desperate |
| 4. synthesize_patterns.py | 20-30 min | No — this is the graded headline |
| 5. Human verification (12 apps) | 30-40 min | Cut to 6-8 apps before cutting this entirely |
| 6. case_study.html | 45-60 min | Cut interactivity (sort/filter) before cutting content |
| 7. research_one_app.py + README | 15-20 min | No |
| 8. (stretch) Render live endpoint | open-ended | Cut first, always |

**Cutting order if truly squeezed:** stretch Render → matrix interactivity/polish → verification sample size (never to zero) → cross-check auto-diff detail. Never cut: the pattern synthesis, the honest verification numbers, or the single HTML page itself — those three are what the assignment is actually grading.

## 9. Risks / what to revisit later
- **Free-model rotation and reliability.** OpenRouter's free-model roster changes without notice and small free models are less reliable at structured JSON output than a paid frontier model. Mitigation already in the design: JSONL (not one big JSON blob) so partial failures are cheap to retry; a quick preflight test across 2-3 candidate free models before committing to one for the full run.
- **50/day is a hard wall shared between dev iteration and the "real" run.** Do your prompt debugging on a tiny 3-5 app subset, not the full 100, and only run the full batch once you're fairly confident the prompts work — you don't get a free retry if you burn the quota mid-afternoon.
- **A few of the 100 apps don't fit the "hosted SaaS with OAuth" mental model** (e.g., Sherlock, Mermaid CLI are open-source CLI tools, not APIs with auth at all). The schema and prompts should treat "not applicable, this isn't a hosted service" as a valid, first-class answer rather than a bug.
- **Composio SDK method names** for structured toolkit metadata aren't confirmed here — verify against docs.composio.dev when you actually write `composio_crosscheck.py`; the doc-page-scrape fallback (§5.5) works regardless of what the SDK exposes.

---

## Appendix A — seed data (`data/apps_100.json`)

Structured from the assignment's app list. Paste directly; `hint` is the docs/website pointer given in the assignment, used as the first fetch target before falling back to search.

```json
[
  {"app_id":"salesforce","name":"Salesforce","category":"CRM & Sales","hint":"salesforce.com"},
  {"app_id":"hubspot","name":"HubSpot","category":"CRM & Sales","hint":"hubspot.com"},
  {"app_id":"pipedrive","name":"Pipedrive","category":"CRM & Sales","hint":"pipedrive.com"},
  {"app_id":"attio","name":"Attio","category":"CRM & Sales","hint":"attio.com"},
  {"app_id":"twenty","name":"Twenty","category":"CRM & Sales","hint":"twenty.com"},
  {"app_id":"podio","name":"Podio","category":"CRM & Sales","hint":"podio.com"},
  {"app_id":"zoho_crm","name":"Zoho CRM","category":"CRM & Sales","hint":"zoho.com/crm"},
  {"app_id":"close","name":"Close","category":"CRM & Sales","hint":"close.com"},
  {"app_id":"copper","name":"Copper","category":"CRM & Sales","hint":"copper.com"},
  {"app_id":"dealcloud","name":"DealCloud","category":"CRM & Sales","hint":"api.docs.dealcloud.com"},

  {"app_id":"zendesk","name":"Zendesk","category":"Support & Helpdesk","hint":"zendesk.com"},
  {"app_id":"intercom","name":"Intercom","category":"Support & Helpdesk","hint":"intercom.com"},
  {"app_id":"freshdesk","name":"Freshdesk","category":"Support & Helpdesk","hint":"freshdesk.com"},
  {"app_id":"front","name":"Front","category":"Support & Helpdesk","hint":"front.com"},
  {"app_id":"pylon","name":"Pylon","category":"Support & Helpdesk","hint":"usepylon.com"},
  {"app_id":"liveagent","name":"LiveAgent","category":"Support & Helpdesk","hint":"liveagent.com"},
  {"app_id":"plain","name":"Plain","category":"Support & Helpdesk","hint":"plain.com"},
  {"app_id":"help_scout","name":"Help Scout","category":"Support & Helpdesk","hint":"helpscout.com"},
  {"app_id":"gorgias","name":"Gorgias","category":"Support & Helpdesk","hint":"gorgias.com"},
  {"app_id":"gladly","name":"Gladly","category":"Support & Helpdesk","hint":"gladly.com"},

  {"app_id":"slack","name":"Slack","category":"Communications & Messaging","hint":"slack.com"},
  {"app_id":"twilio","name":"Twilio","category":"Communications & Messaging","hint":"twilio.com"},
  {"app_id":"zoho_cliq","name":"Zoho Cliq","category":"Communications & Messaging","hint":"zoho.com/cliq"},
  {"app_id":"lark","name":"Lark (Larksuite)","category":"Communications & Messaging","hint":"open.larksuite.com"},
  {"app_id":"pumble","name":"Pumble","category":"Communications & Messaging","hint":"pumble.com"},
  {"app_id":"discord","name":"Discord","category":"Communications & Messaging","hint":"discord.com"},
  {"app_id":"telegram","name":"Telegram","category":"Communications & Messaging","hint":"core.telegram.org"},
  {"app_id":"whatsapp_business","name":"WhatsApp Business","category":"Communications & Messaging","hint":"developers.facebook.com/docs/whatsapp"},
  {"app_id":"aircall","name":"Aircall","category":"Communications & Messaging","hint":"aircall.io"},
  {"app_id":"vonage","name":"Vonage","category":"Communications & Messaging","hint":"developer.vonage.com"},

  {"app_id":"google_ads","name":"Google Ads","category":"Marketing, Ads, Email & Social","hint":"developers.google.com/google-ads"},
  {"app_id":"meta_ads","name":"Meta Ads","category":"Marketing, Ads, Email & Social","hint":"developers.facebook.com/docs/marketing-apis"},
  {"app_id":"linkedin_ads","name":"LinkedIn Ads","category":"Marketing, Ads, Email & Social","hint":"learn.microsoft.com/linkedin/marketing"},
  {"app_id":"gohighlevel","name":"GoHighLevel","category":"Marketing, Ads, Email & Social","hint":"highlevel.stoplight.io"},
  {"app_id":"mailchimp","name":"Mailchimp","category":"Marketing, Ads, Email & Social","hint":"mailchimp.com/developer"},
  {"app_id":"klaviyo","name":"Klaviyo","category":"Marketing, Ads, Email & Social","hint":"developers.klaviyo.com"},
  {"app_id":"systeme_io","name":"systeme.io","category":"Marketing, Ads, Email & Social","hint":"systeme.io"},
  {"app_id":"pinterest","name":"Pinterest","category":"Marketing, Ads, Email & Social","hint":"developers.pinterest.com"},
  {"app_id":"threads","name":"Threads (Meta)","category":"Marketing, Ads, Email & Social","hint":"developers.facebook.com/docs/threads"},
  {"app_id":"sendgrid","name":"SendGrid","category":"Marketing, Ads, Email & Social","hint":"sendgrid.com"},

  {"app_id":"shopify","name":"Shopify","category":"Ecommerce","hint":"shopify.dev"},
  {"app_id":"woocommerce","name":"WooCommerce","category":"Ecommerce","hint":"woocommerce.com/document/woocommerce-rest-api"},
  {"app_id":"bigcommerce","name":"BigCommerce","category":"Ecommerce","hint":"developer.bigcommerce.com"},
  {"app_id":"sf_commerce_cloud","name":"Salesforce Commerce Cloud","category":"Ecommerce","hint":"developer.salesforce.com/docs/commerce"},
  {"app_id":"magento","name":"Magento (Adobe Commerce)","category":"Ecommerce","hint":"developer.adobe.com/commerce"},
  {"app_id":"squarespace","name":"Squarespace","category":"Ecommerce","hint":"developers.squarespace.com"},
  {"app_id":"ecwid","name":"Ecwid","category":"Ecommerce","hint":"api-docs.ecwid.com"},
  {"app_id":"gumroad","name":"Gumroad","category":"Ecommerce","hint":"gumroad.com/api"},
  {"app_id":"amazon_sp","name":"Amazon Selling Partner","category":"Ecommerce","hint":"developer-docs.amazon.com/sp-api"},
  {"app_id":"fanbasis","name":"fanbasis","category":"Ecommerce","hint":"fanbasis.com"},

  {"app_id":"dataforseo","name":"DataForSEO","category":"Data, SEO & Scraping","hint":"docs.dataforseo.com"},
  {"app_id":"se_ranking","name":"SE Ranking","category":"Data, SEO & Scraping","hint":"seranking.com/api"},
  {"app_id":"ahrefs","name":"Ahrefs","category":"Data, SEO & Scraping","hint":"ahrefs.com/api"},
  {"app_id":"mrscraper","name":"MrScraper","category":"Data, SEO & Scraping","hint":"docs.mrscraper.com"},
  {"app_id":"apify","name":"Apify","category":"Data, SEO & Scraping","hint":"docs.apify.com"},
  {"app_id":"firecrawl","name":"Firecrawl","category":"Data, SEO & Scraping","hint":"firecrawl.dev"},
  {"app_id":"bright_data","name":"Bright Data","category":"Data, SEO & Scraping","hint":"brightdata.com"},
  {"app_id":"sherlock","name":"Sherlock","category":"Data, SEO & Scraping","hint":"github.com/sherlock-project/sherlock"},
  {"app_id":"waterfall_io","name":"Waterfall.io","category":"Data, SEO & Scraping","hint":"waterfall.io"},
  {"app_id":"clay","name":"Clay","category":"Data, SEO & Scraping","hint":"clay.com"},

  {"app_id":"github","name":"GitHub","category":"Developer, Infra & Data Platforms","hint":"docs.github.com/rest"},
  {"app_id":"vercel","name":"Vercel","category":"Developer, Infra & Data Platforms","hint":"vercel.com/docs/rest-api"},
  {"app_id":"netlify","name":"Netlify","category":"Developer, Infra & Data Platforms","hint":"docs.netlify.com/api"},
  {"app_id":"cloudflare","name":"Cloudflare","category":"Developer, Infra & Data Platforms","hint":"developers.cloudflare.com/api"},
  {"app_id":"supabase","name":"Supabase","category":"Developer, Infra & Data Platforms","hint":"supabase.com/docs"},
  {"app_id":"neo4j","name":"Neo4j","category":"Developer, Infra & Data Platforms","hint":"neo4j.com/docs/api"},
  {"app_id":"snowflake","name":"Snowflake","category":"Developer, Infra & Data Platforms","hint":"docs.snowflake.com"},
  {"app_id":"mongodb_atlas","name":"MongoDB Atlas","category":"Developer, Infra & Data Platforms","hint":"mongodb.com/docs/atlas/api"},
  {"app_id":"datadog","name":"Datadog","category":"Developer, Infra & Data Platforms","hint":"docs.datadoghq.com/api"},
  {"app_id":"sentry","name":"Sentry","category":"Developer, Infra & Data Platforms","hint":"docs.sentry.io/api"},

  {"app_id":"notion","name":"Notion","category":"Productivity & Project Management","hint":"developers.notion.com"},
  {"app_id":"airtable","name":"Airtable","category":"Productivity & Project Management","hint":"airtable.com/developers"},
  {"app_id":"linear","name":"Linear","category":"Productivity & Project Management","hint":"developers.linear.app"},
  {"app_id":"jira","name":"Jira","category":"Productivity & Project Management","hint":"developer.atlassian.com"},
  {"app_id":"asana","name":"Asana","category":"Productivity & Project Management","hint":"developers.asana.com"},
  {"app_id":"monday","name":"Monday.com","category":"Productivity & Project Management","hint":"developer.monday.com"},
  {"app_id":"clickup","name":"ClickUp","category":"Productivity & Project Management","hint":"clickup.com/api"},
  {"app_id":"coda","name":"Coda","category":"Productivity & Project Management","hint":"coda.io/developers"},
  {"app_id":"smartsheet","name":"Smartsheet","category":"Productivity & Project Management","hint":"smartsheet.com/developers"},
  {"app_id":"harvest","name":"Harvest","category":"Productivity & Project Management","hint":"help.getharvest.com/api-v2"},

  {"app_id":"stripe","name":"Stripe","category":"Finance & Fintech","hint":"stripe.com/docs/api"},
  {"app_id":"plaid","name":"Plaid","category":"Finance & Fintech","hint":"plaid.com/docs"},
  {"app_id":"binance","name":"Binance","category":"Finance & Fintech","hint":"binance-docs.github.io"},
  {"app_id":"paygent_connect","name":"Paygent Connect","category":"Finance & Fintech","hint":"paygent (NMI-powered)"},
  {"app_id":"ipayx","name":"iPayX","category":"Finance & Fintech","hint":"ipayx.ai/docs"},
  {"app_id":"quickbooks","name":"QuickBooks","category":"Finance & Fintech","hint":"developer.intuit.com"},
  {"app_id":"xero","name":"Xero","category":"Finance & Fintech","hint":"developer.xero.com"},
  {"app_id":"brex","name":"Brex","category":"Finance & Fintech","hint":"developer.brex.com"},
  {"app_id":"ramp","name":"Ramp","category":"Finance & Fintech","hint":"docs.ramp.com"},
  {"app_id":"pitchbook","name":"PitchBook","category":"Finance & Fintech","hint":"pitchbook.com"},

  {"app_id":"notebooklm","name":"NotebookLM","category":"AI, Research & Media-native","hint":"cloud.google.com/gemini"},
  {"app_id":"otter_ai","name":"Otter AI","category":"AI, Research & Media-native","hint":"help.otter.ai"},
  {"app_id":"fathom","name":"Fathom","category":"AI, Research & Media-native","hint":"fathom.video"},
  {"app_id":"consensus","name":"Consensus","category":"AI, Research & Media-native","hint":"consensus.app"},
  {"app_id":"reducto","name":"Reducto","category":"AI, Research & Media-native","hint":"reducto.ai"},
  {"app_id":"devin","name":"Devin","category":"AI, Research & Media-native","hint":"docs.devin.ai"},
  {"app_id":"higgsfield","name":"higgsfield","category":"AI, Research & Media-native","hint":"higgsfield.ai/cli"},
  {"app_id":"mermaid_cli","name":"Mermaid CLI","category":"AI, Research & Media-native","hint":"github.com/mermaid-js/mermaid-cli"},
  {"app_id":"youtube_transcript","name":"YouTube Transcript","category":"AI, Research & Media-native","hint":"transcriptapi.com"},
  {"app_id":"grain","name":"Grain","category":"AI, Research & Media-native","hint":"grain.com"}
]
```

---

**Next step:** confirm this matches what you pictured, then say go and I'll start walking through implementation with you phase by phase, or hand this file straight to Codex/Claude Code with "build this spec" as your first instruction.
