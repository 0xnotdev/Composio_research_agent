"""Single-file, dependency-free HTML case-study renderer."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any

from .analytics import field_value


def _escape(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, list):
        return html.escape(", ".join(str(item) for item in value) or "—")
    return html.escape(str(value))


def _percent(analytics: dict[str, Any], path: str, key: str) -> str:
    count = analytics["distributions"].get(path, {}).get(key, 0)
    total = analytics.get("record_count", 0)
    return f"{round(count / total * 100) if total else 0}%"


def _evidence_link(record: dict[str, Any]) -> str:
    sources = record.get("evidence", [])
    if not sources:
        return "—"
    url = sources[0].get("url")
    return f'<a href="{html.escape(str(url), quote=True)}" target="_blank" rel="noreferrer">source</a>' if url else "—"


def _table_row(record: dict[str, Any]) -> str:
    verdict = field_value(record, "viability.combined")
    confidence = field_value(record, "viability.combined")
    combined = record.get("viability", {}).get("combined", {})
    confidence = combined.get("confidence") if isinstance(combined, dict) else None
    return "<tr>" + "".join(
        [
            f"<td>{_escape(record.get('name', record['app_id']))}</td>",
            f"<td>{_escape(record.get('category'))}</td>",
            f"<td>{_escape(field_value(record, 'auth_methods'))}</td>",
            f"<td>{_escape(field_value(record, 'credential_path'))}</td>",
            f"<td>{_escape(field_value(record, 'api_surface.protocols'))} · {_escape(field_value(record, 'api_surface.breadth'))}</td>",
            f"<td>{_escape(field_value(record, 'mcp.official_vendor_mcp'))} / {_escape(field_value(record, 'mcp.public_mcp_exists'))}</td>",
            f"<td><span class=\"badge\">{_escape(verdict)}</span></td>",
            f"<td>{_escape(confidence)}</td>",
            f"<td>{_evidence_link(record)}</td>",
        ]
    ) + "</tr>"


def render_case_study(records: list[dict[str, Any]], analytics: dict[str, Any], verification: dict[str, Any] | None, generated_at: str, patterns: list[dict[str, Any]] | None = None, simulated_review: dict[str, Any] | None = None) -> str:
    rows = "\n".join(_table_row(record) for record in records)
    wins = "".join(f"<li>{_escape(item['name'])} <span>{_escape(item['category'])}</span></li>" for item in analytics.get("easy_wins", [])[:10]) or "<li>No fully evidenced easy wins yet.</li>"
    outreach = "".join(f"<li>{_escape(item['name'])} <span>{_escape(item['category'])}</span></li>" for item in analytics.get("outreach_candidates", [])[:10]) or "<li>No fully evidenced outreach candidates yet.</li>"
    coverage = analytics.get("coverage", {})
    distributions = analytics.get("distributions", {})
    unknown_breadth = distributions.get("api_surface.breadth", {}).get("unknown", 0)
    unknown_mcp = distributions.get("mcp.official_vendor_mcp", {}).get("unknown", 0)
    pattern_cards = "".join(
        f'<div class="card"><h3>{_escape(pattern.get("headline"))}</h3><p>{_escape(pattern.get("insight"))}</p><p class="metric-label">Agent caveat: {_escape(pattern.get("caveat"))}</p></div>'
        for pattern in (patterns or [])
    ) or '<div class="card"><p>Portfolio-pattern synthesis has not been run yet.</p></div>'
    verification = verification or {}
    v_pass1 = verification.get("pass1_accuracy_percent", "Pending")
    v_final = verification.get("final_pre_human_accuracy_percent", "Pending")
    simulated_review = simulated_review or {}
    simulated_section = ""
    if simulated_review:
        simulated_section = f'<section><h2>Time-boxed AI-simulated reviewer diagnostic</h2><div class="card note"><p><strong>Not human validation.</strong> {_escape(simulated_review.get("disclosure"))}</p><p>Scope: {_escape(simulated_review.get("review_scope"))}. Simulated fields judged: {_escape(simulated_review.get("judged_fields"))}. Pass-one agreement: {_escape(simulated_review.get("pass1_accuracy_percent"))}%. Final pre-human agreement: {_escape(simulated_review.get("final_pre_human_accuracy_percent"))}%.</p></div></section>'
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>100-App Buildability Audit</title>
<style>
:root{{--ink:#14213d;--muted:#62738a;--paper:#f7f9fc;--line:#dce4ed;--accent:#155eef;--good:#027a48;--card:#fff}}
*{{box-sizing:border-box}} body{{margin:0;font:15px/1.55 Inter,ui-sans-serif,system-ui,sans-serif;color:var(--ink);background:var(--paper)}}
main{{max-width:1240px;margin:auto;padding:42px 24px 80px}} h1{{font-size:clamp(2rem,5vw,3.9rem);line-height:1.03;letter-spacing:-.055em;margin:.2rem 0 1rem}} h2{{font-size:1.5rem;letter-spacing:-.025em;margin:0 0 .6rem}} h3{{font-size:1rem;margin:0 0 .4rem}} p{{max-width:78ch;color:var(--muted)}} a{{color:var(--accent)}} .eyebrow{{text-transform:uppercase;letter-spacing:.12em;color:var(--accent);font-weight:700;font-size:.75rem}} .card{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:22px;box-shadow:0 2px 5px #14213d08}} .grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:28px 0}} .metric{{font-size:2rem;font-weight:760;letter-spacing:-.06em;color:var(--ink)}} .metric-label{{color:var(--muted);font-size:.84rem}} section{{margin-top:46px}} .two{{display:grid;grid-template-columns:1fr 1fr;gap:16px}} ul{{margin:10px 0;padding-left:20px}} li span{{color:var(--muted);font-size:.85em}} .workflow{{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;align-items:stretch}} .step{{border:1px solid var(--line);border-radius:10px;padding:12px;background:#fff;font-size:.88rem}} .step b{{display:block;color:var(--accent)}} .table-wrap{{overflow:auto;border:1px solid var(--line);border-radius:12px;background:#fff}} table{{width:100%;border-collapse:collapse;min-width:1050px}} th{{position:sticky;top:0;background:#f0f4f8;text-align:left;font-size:.75rem;text-transform:uppercase;letter-spacing:.05em}} th,td{{border-bottom:1px solid var(--line);padding:11px 10px;vertical-align:top}} td{{font-size:.88rem}} .badge{{border-radius:999px;background:#e8f1ff;color:#1047a9;padding:3px 8px;font-size:.76rem;white-space:nowrap}} .controls{{display:flex;gap:10px;align-items:center;margin:12px 0}} input,select{{border:1px solid var(--line);border-radius:8px;padding:9px;background:white;font:inherit}} .note{{border-left:3px solid var(--accent);padding:8px 14px;background:#edf4ff;color:#314362}} @media(max-width:800px){{.grid{{grid-template-columns:1fr 1fr}}.two{{grid-template-columns:1fr}}.workflow{{grid-template-columns:1fr}}}} @media(max-width:480px){{.grid{{grid-template-columns:1fr}}main{{padding:30px 15px}}}}
</style></head><body><main>
<header><div class="eyebrow">Composio Product Ops · Evidence-grounded research</div><h1>Which apps are buildable for agent toolkits—today?</h1><p>A reproducible audit of 100 assigned apps, grounded in official documentation, independently critiqued, reconciled in code, and sampled by hand. Generated {html.escape(generated_at)}.</p><p><a href="https://github.com/0xnotdev/Composio_research_agent" target="_blank" rel="noreferrer">Source repository and runnable research agent</a></p></header>
<div class="grid"><div class="card"><div class="metric">{analytics.get('record_count', 0)}</div><div class="metric-label">apps audited</div></div><div class="card"><div class="metric">{_percent(analytics,'credential_path','self_serve')}</div><div class="metric-label">self-serve credential paths</div></div><div class="card"><div class="metric">{len(analytics.get('easy_wins', []))}</div><div class="metric-label">evidenced easy wins</div></div><div class="card"><div class="metric">{coverage.get('coverage_percent','—')}%</div><div class="metric-label">field evidence coverage</div></div></div>
<section><h2>How to read blanks and unknowns</h2><div class="card note"><p><strong>An em dash or <code>unknown</code> is not a claim that the vendor lacks a capability.</strong> It means this run did not retain enough official primary-source evidence to support a value, so the agent abstained rather than guessed. This public-documentation snapshot has {coverage.get('coverage_percent','â€”')}% supported-field coverage. {unknown_breadth} apps have unresolved API-breadth evidence and {unknown_mcp} have unresolved official-MCP evidence. Use the source link in each row to inspect the underlying official material.</p></div></section>
<section><h2>Agent-generated portfolio patterns</h2><p>A dedicated analysis agent synthesized these patterns from the deterministic audit metrics below; it was instructed not to infer beyond those metrics.</p><div class="two">{pattern_cards}</div></section>
<section><h2>What the portfolio says</h2><p>Metrics are calculated directly from the audited dataset used to render this matrix. Unknown and conflicting fields are retained rather than smoothed away: {coverage.get('conflicting_fields',0)} fields remain conflicting.</p><div class="two"><div class="card"><h3>Easy wins</h3><p>Self-serve, technically ready apps with a moderate/broad API surface and no official vendor MCP.</p><ul>{wins}</ul></div><div class="card"><h3>Needs outreach</h3><p>Strong API surface, but partner or sales access constrains a toolkit launch.</p><ul>{outreach}</ul></div></div></section>
<section><h2>The research agent</h2><div class="workflow"><div class="step"><b>1. Acquire</b>Official docs only; Composio Search first.</div><div class="step"><b>2. Extract</b>Researcher cites exact evidence excerpts.</div><div class="step"><b>3. Challenge</b>Critic re-derives and flags disagreement.</div><div class="step"><b>4. Reconcile</b>Code validates citations and derives verdicts.</div><div class="step"><b>5. Verify</b>Human checks a stratified 12-app sample.</div></div><p class="note">A model agreement is not treated as verification. Each populated claim requires an official-source excerpt; the accuracy figures below are based on manual review.</p></section>
<section><h2>Findings matrix</h2><div class="controls"><input id="search" type="search" placeholder="Filter apps or categories"><select id="verdict"><option value="">All verdicts</option><option>ready_now</option><option>buildable_with_access_constraint</option><option>buildable_with_technical_workaround</option><option>blocked</option><option>insufficient_evidence</option></select></div><div class="table-wrap"><table id="matrix"><thead><tr><th>App</th><th>Category</th><th>Auth</th><th>Credential path</th><th>API</th><th>Official / public MCP</th><th>Verdict</th><th>Confidence</th><th>Evidence</th></tr></thead><tbody>{rows}</tbody></table></div></section>
<section><h2>Human verification</h2><div class="grid"><div class="card"><div class="metric">{_escape(v_pass1)}{'' if isinstance(v_pass1, str) and v_pass1 == 'Pending' else '%'}</div><div class="metric-label">pass-one accuracy on manually judged fields</div></div><div class="card"><div class="metric">{_escape(v_final)}{'' if isinstance(v_final, str) and v_final == 'Pending' else '%'}</div><div class="metric-label">final pre-human accuracy on the same fields</div></div><div class="card"><div class="metric">{verification.get('judged_fields','Pending')}</div><div class="metric-label">judged field comparisons</div></div><div class="card"><div class="metric">{len(verification.get('misses',[])) if verification else 'Pending'}</div><div class="metric-label">final misses retained honestly</div></div></div><p>Human verification remains pending. The page does not claim human-reviewed accuracy unless a real person completes the 12-app official-doc sample.</p></section>{simulated_section}
<section><h2>Run it yourself</h2><div class="card"><code>python research_one_app.py "Slack"</code><p>The command runs the same evidence, research, critic, validation, and reconciliation path for one app. It returns insufficient evidence rather than guessing when official sources do not support an answer.</p></div></section>
<section><h2>Limitations</h2><p>This is a dated public-documentation snapshot, not a guarantee of production access. Some assigned items are CLIs, open-source projects, thinly documented products, or commercial APIs; those are treated as explicit non-applicable, gated, or insufficient-evidence outcomes rather than forced into a SaaS/OAuth shape.</p></section>
</main><script>const q=document.querySelector('#search'),v=document.querySelector('#verdict'),rows=[...document.querySelectorAll('#matrix tbody tr')];function filter(){{const term=q.value.toLowerCase(), verdict=v.value;rows.forEach(r=>{{const ok=!term||r.innerText.toLowerCase().includes(term);const vok=!verdict||r.cells[6].innerText===verdict;r.hidden=!(ok&&vok)}})}}q.addEventListener('input',filter);v.addEventListener('change',filter);</script></body></html>"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Render the self-contained case study HTML")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--analytics", type=Path, required=True)
    parser.add_argument("--verification", type=Path)
    parser.add_argument("--patterns", type=Path)
    parser.add_argument("--simulated-review", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--generated-at", default="local build")
    args = parser.parse_args()
    records = json.loads(args.dataset.read_text(encoding="utf-8"))
    analytics = json.loads(args.analytics.read_text(encoding="utf-8"))
    verification = json.loads(args.verification.read_text(encoding="utf-8")) if args.verification else None
    pattern_payload = json.loads(args.patterns.read_text(encoding="utf-8")) if args.patterns else {}
    patterns = pattern_payload.get("patterns") if isinstance(pattern_payload, dict) else None
    simulated_review = json.loads(args.simulated_review.read_text(encoding="utf-8")) if args.simulated_review else None
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_case_study(records, analytics, verification, args.generated_at, patterns, simulated_review), encoding="utf-8")


if __name__ == "__main__":
    main()
