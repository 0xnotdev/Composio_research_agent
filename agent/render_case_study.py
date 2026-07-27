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
        return "-"
    if isinstance(value, list):
        return html.escape(", ".join(str(item) for item in value) or "-")
    return html.escape(str(value))


def _count(analytics: dict[str, Any], path: str, key: str) -> int:
    return int(analytics.get("distributions", {}).get(path, {}).get(key, 0))


def _share(count: int, total: int) -> str:
    return f"{round(count / total * 100) if total else 0}%"


def _evidence_link(record: dict[str, Any], label: str = "official source") -> str:
    sources = record.get("evidence", [])
    url = next((source.get("url") for source in sources if source.get("url")), None)
    if not url:
        return "-"
    return f'<a href="{html.escape(str(url), quote=True)}" target="_blank" rel="noreferrer">{html.escape(label)}</a>'


def _table_row(record: dict[str, Any]) -> str:
    combined = record.get("viability", {}).get("combined", {})
    verdict = field_value(record, "viability.combined")
    confidence = combined.get("confidence") if isinstance(combined, dict) else None
    return "<tr>" + "".join(
        [
            f"<td><b>{_escape(record.get('name', record['app_id']))}</b><span class=\"sub\">{_escape(record['app_id'])}</span></td>",
            f"<td>{_escape(record.get('category'))}</td>",
            f"<td>{_escape(field_value(record, 'auth_methods'))}</td>",
            f"<td>{_escape(field_value(record, 'credential_path'))}</td>",
            f"<td>{_escape(field_value(record, 'api_surface.protocols'))}<span class=\"sub\">breadth: {_escape(field_value(record, 'api_surface.breadth'))}</span></td>",
            f"<td>{_escape(field_value(record, 'mcp.official_vendor_mcp'))} / {_escape(field_value(record, 'mcp.public_mcp_exists'))}</td>",
            f"<td><span class=\"badge badge-{_escape(verdict)}\">{_escape(verdict)}</span><span class=\"sub\">{_escape(confidence)}</span></td>",
            f"<td>{_evidence_link(record)}</td>",
        ]
    ) + "</tr>"


def _pattern_cards(patterns: list[dict[str, Any]] | None) -> str:
    if not patterns:
        return '<div class="empty">Pattern agent output is unavailable.</div>'
    return "".join(
        f'<article class="pattern"><span class="eyebrow">Agent synthesis</span><h3>{_escape(pattern.get("headline"))}</h3><p>{_escape(pattern.get("insight"))}</p><div class="caveat"><b>Caveat</b> {_escape(pattern.get("caveat"))}</div></article>'
        for pattern in patterns
    )


def _category_rows(analytics: dict[str, Any]) -> str:
    categories = analytics.get("credential_path_by_category", {})
    rows: list[str] = []
    for category, values in categories.items():
        self_serve = int(values.get("self_serve", 0))
        paid = int(values.get("paid_or_admin_gated", 0))
        partner = int(values.get("partner_or_sales_gated", 0))
        unknown = int(values.get("unknown", 0))
        total = max(sum(int(value) for value in values.values()), 1)
        bars = "".join(
            f'<span class="seg {name}" style="width:{count / total * 100:.1f}%"></span>'
            for name, count in (("self", self_serve), ("paid", paid), ("partner", partner), ("unknown", unknown))
            if count
        )
        rows.append(
            f'<div class="category-row"><div><b>{_escape(category)}</b><span class="sub">{self_serve} self-serve | {paid} paid/admin | {partner} partner/sales | {unknown} unknown</span></div><div class="bar">{bars}</div></div>'
        )
    return "".join(rows)


def _candidates(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    high_signal = []
    constrained = []
    for record in records:
        credential = field_value(record, "credential_path")
        technical = field_value(record, "viability.technical")
        breadth = field_value(record, "api_surface.breadth")
        if credential == "self_serve" and technical == "ready" and breadth in {"moderate", "broad"}:
            high_signal.append(record)
        if credential in {"paid_or_admin_gated", "partner_or_sales_gated"} and technical in {"ready", "workaround_needed"}:
            constrained.append(record)
    return high_signal[:8], constrained[:8]


def _app_list(records: list[dict[str, Any]]) -> str:
    return "".join(f'<li><b>{_escape(record.get("name", record["app_id"]))}</b><span>{_escape(record.get("category"))}</span></li>' for record in records) or "<li>No candidates met this evidence threshold.</li>"


def _simulated_review_section(review: dict[str, Any] | None) -> str:
    if not review:
        return ""
    misses = [item for item in review.get("items", []) if not item.get("final_pre_human_correct")][:8]
    miss_rows = "".join(
        f'<tr><td>{_escape(item.get("app_id"))}</td><td>{_escape(item.get("path"))}</td><td>{_escape(item.get("simulated_ground_truth"))}</td><td>{_escape(item.get("reason"))}</td><td>'
        + (f'<a href="{html.escape(str(item.get("source_url")), quote=True)}" target="_blank" rel="noreferrer">source</a>' if item.get("source_url") else '-')
        + '</td></tr>'
        for item in misses
    ) or '<tr><td colspan="5">No disagreement rows were returned.</td></tr>'
    return f'''<section id="simulated-review" class="section"><div class="section-heading"><span class="eyebrow">Time-boxed diagnostic</span><h2>AI-simulated reviewer: useful signal, not human validation</h2><p><strong>This is explicitly not a human accuracy claim.</strong> A separate model re-read retained official excerpts for selected auth, access, and API fields. It is included to show the automated challenge loop and its limits.</p></div><div class="quality-grid"><div class="metric-card"><strong>{_escape(review.get("judged_fields"))}</strong><span>simulated fields checked</span></div><div class="metric-card"><strong>{_escape(review.get("pass1_accuracy_percent"))}%</strong><span>pass-one agreement</span></div><div class="metric-card"><strong>{_escape(review.get("final_pre_human_accuracy_percent"))}%</strong><span>reconciled-output agreement</span></div><div class="metric-card"><strong>Pending</strong><span>real human validation</span></div></div><div class="callout warn"><b>Disclosure:</b> {_escape(review.get("disclosure"))} The equal pass-one/final score is retained honestly: this diagnostic does not demonstrate an accuracy lift.</div><div class="table-wrap compact"><table><thead><tr><th>App</th><th>Field</th><th>Simulated reviewer value</th><th>Why it disagreed</th><th>Evidence</th></tr></thead><tbody>{miss_rows}</tbody></table></div></section>'''


def render_case_study(
    records: list[dict[str, Any]],
    analytics: dict[str, Any],
    verification: dict[str, Any] | None,
    generated_at: str,
    patterns: list[dict[str, Any]] | None = None,
    simulated_review: dict[str, Any] | None = None,
) -> str:
    total = int(analytics.get("record_count", 0))
    self_serve = _count(analytics, "credential_path", "self_serve")
    paid = _count(analytics, "credential_path", "paid_or_admin_gated")
    partner = _count(analytics, "credential_path", "partner_or_sales_gated")
    oauth = _count(analytics, "auth_methods", "oauth2")
    ready = _count(analytics, "viability.combined", "ready_now")
    constrained = _count(analytics, "viability.combined", "buildable_with_access_constraint")
    insufficient = _count(analytics, "viability.combined", "insufficient_evidence")
    coverage = analytics.get("coverage", {})
    unknown_breadth = _count(analytics, "api_surface.breadth", "unknown")
    unknown_mcp = _count(analytics, "mcp.official_vendor_mcp", "unknown")
    high_signal, access_constrained = _candidates(records)
    rows = "\n".join(_table_row(record) for record in records)
    human = verification or {}
    human_status = "Complete" if human.get("judged_fields") else "Pending"

    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>100-App Buildability Audit | Composio Product Ops</title>
<style>
:root{{--ink:#101828;--muted:#667085;--paper:#f7f8fc;--line:#e4e7ec;--blue:#2e5bff;--navy:#15213d;--green:#067647;--amber:#b54708;--red:#b42318;--card:#fff;--soft-blue:#eef4ff;--soft-green:#ecfdf3;--soft-amber:#fffaeb}}*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--paper);color:var(--ink);font:15px/1.55 Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}a{{color:#1849a9;text-underline-offset:3px}}main{{max-width:1240px;margin:auto;padding:28px 24px 80px}}.nav{{display:flex;justify-content:space-between;align-items:center;gap:16px;font-size:13px;margin-bottom:42px}}.brand{{font-weight:800;color:var(--navy);letter-spacing:-.02em}}.nav-links{{display:flex;gap:16px;flex-wrap:wrap}}.eyebrow{{display:block;text-transform:uppercase;letter-spacing:.12em;font-size:11px;font-weight:800;color:var(--blue);margin-bottom:10px}}.hero{{background:radial-gradient(circle at 88% 8%,#c7d7ff 0,transparent 27%),linear-gradient(135deg,#15213d,#1e3a78);border-radius:24px;padding:48px;color:white;box-shadow:0 18px 44px #15213d22}}.hero h1{{font-size:clamp(2.3rem,5vw,4.25rem);line-height:.98;letter-spacing:-.065em;max-width:850px;margin:0 0 20px}}.hero p{{max-width:760px;color:#d0d9f3;font-size:17px;margin:0 0 24px}}.hero .eyebrow{{color:#b9ccff}}.button{{display:inline-block;background:white;color:#173b82!important;text-decoration:none;font-weight:800;border-radius:9px;padding:10px 14px;margin-right:10px}}.button.secondary{{background:#ffffff18;color:white!important;border:1px solid #ffffff44}}.metrics{{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin:18px 0 6px}}.metric-card,.card,.pattern{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:20px;box-shadow:0 2px 8px #10182808}}.metric-card strong{{display:block;font-size:30px;letter-spacing:-.06em;line-height:1.1}}.metric-card span,.sub{{display:block;color:var(--muted);font-size:12px;margin-top:5px}}.section{{margin-top:62px}}.section-heading{{max-width:790px;margin-bottom:22px}}h2{{font-size:clamp(1.75rem,3vw,2.45rem);line-height:1.08;letter-spacing:-.045em;margin:0 0 10px}}h3{{font-size:16px;line-height:1.25;margin:0 0 8px;letter-spacing:-.02em}}p{{color:var(--muted);margin:0}}.callout{{border-radius:12px;padding:16px 18px;margin-top:14px;background:var(--soft-blue);border-left:4px solid var(--blue);color:#344054}}.callout.warn{{background:var(--soft-amber);border-left-color:#dc6803}}.signal-grid,.quality-grid,.two,.pattern-grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}}.signal{{padding:20px;border-radius:16px;border:1px solid var(--line);background:white}}.signal .number{{font-size:30px;font-weight:800;letter-spacing:-.06em;color:var(--navy)}}.signal p{{font-size:13px;margin-top:5px}}.pattern-grid{{grid-template-columns:repeat(2,1fr)}}.pattern{{min-height:200px}}.pattern p{{font-size:14px}}.caveat{{font-size:12px;color:#475467;background:#f8fafc;border-radius:8px;padding:9px;margin-top:14px}}.cluster-key{{display:flex;gap:12px;flex-wrap:wrap;font-size:12px;color:var(--muted);margin:12px 0 16px}}.key-dot{{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:5px}}.category-card{{padding:22px}}.category-row{{display:grid;grid-template-columns:1.55fr 1fr;align-items:center;gap:16px;padding:12px 0;border-bottom:1px solid var(--line)}}.category-row:last-child{{border:0}}.bar{{height:10px;background:#eef2f6;border-radius:999px;overflow:hidden;display:flex}}.seg{{height:100%}}.seg.self{{background:#12b76a}}.seg.paid{{background:#f79009}}.seg.partner{{background:#f04438}}.seg.unknown{{background:#98a2b3}}.list-card ul{{padding-left:19px;margin:12px 0 0}}.list-card li{{margin:8px 0}}.list-card li span{{display:block;color:var(--muted);font-size:12px}}.workflow{{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}}.step{{background:white;border:1px solid var(--line);padding:15px;border-radius:13px;min-height:126px}}.step b{{display:block;color:var(--blue);font-size:12px;margin-bottom:7px}}.step span{{font-size:13px;color:var(--muted)}}.table-wrap{{overflow:auto;border:1px solid var(--line);border-radius:16px;background:white}}table{{width:100%;border-collapse:collapse;min-width:1100px}}th{{background:#f8fafc;color:#475467;font-size:11px;text-transform:uppercase;letter-spacing:.06em;text-align:left;padding:12px;position:sticky;top:0}}td{{padding:12px;border-top:1px solid var(--line);vertical-align:top;font-size:13px}}.compact td{{font-size:12px}}.badge{{display:inline-block;border-radius:999px;padding:4px 8px;background:#eef4ff;color:#1849a9;font-size:11px;font-weight:800;white-space:nowrap}}.badge-buildable_with_access_constraint{{background:#fffaeb;color:#b54708}}.badge-insufficient_evidence{{background:#fef3f2;color:#b42318}}.controls{{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:14px 0}}input,select{{border:1px solid #d0d5dd;border-radius:9px;padding:10px 12px;background:white;font:inherit;color:var(--ink)}}input{{min-width:270px}}details{{margin-top:14px}}summary{{cursor:pointer;font-weight:800;color:#344054}}.footer{{margin-top:56px;padding:24px;border-top:1px solid var(--line);color:var(--muted);font-size:13px}}@media(max-width:900px){{.metrics{{grid-template-columns:repeat(2,1fr)}}.workflow{{grid-template-columns:1fr 1fr}}}}@media(max-width:680px){{main{{padding:18px 14px 50px}}.hero{{padding:30px 24px}}.nav{{align-items:flex-start;flex-direction:column}}.signal-grid,.quality-grid,.two,.pattern-grid{{grid-template-columns:1fr}}.category-row{{grid-template-columns:1fr}}.workflow{{grid-template-columns:1fr}}.metrics{{grid-template-columns:1fr 1fr}}.section{{margin-top:45px}}}}
</style></head><body><main>
<nav class="nav"><div class="brand">COMPOSIO / PRODUCT OPS CASE STUDY</div><div class="nav-links"><a href="#patterns">Patterns</a><a href="#agent">Agent</a><a href="#verification">Verification</a><a href="#matrix">100-app matrix</a></div></nav>
<header class="hero"><span class="eyebrow">Evidence-grounded 100-app buildability audit</span><h1>Where agent toolkits can launch now - and where the evidence says to slow down.</h1><p>A reproducible research agent audited 100 assigned apps using official documentation, then challenged and reconciled its own claims. The result deliberately preserves unknowns rather than converting weak evidence into confident recommendations.</p><a class="button" href="https://github.com/0xnotdev/Composio_research_agent" target="_blank" rel="noreferrer">View source and runnable agent</a><a class="button secondary" href="#matrix">Explore the 100 apps</a></header>
<div class="metrics"><div class="metric-card"><strong>{total}</strong><span>apps across 10 categories</span></div><div class="metric-card"><strong>{_share(self_serve,total)}</strong><span>self-serve credential paths ({self_serve})</span></div><div class="metric-card"><strong>{_share(oauth,total)}</strong><span>apps with OAuth2 evidence ({oauth})</span></div><div class="metric-card"><strong>{ready}</strong><span>ready-now verdicts</span></div><div class="metric-card"><strong>{coverage.get('coverage_percent','-')}%</strong><span>supported-field coverage</span></div></div>
<section class="section"><div class="section-heading"><span class="eyebrow">Executive readout</span><h2>The portfolio is self-serve heavy, but evidence quality determines confidence.</h2><p>The audit found many technically viable candidates, yet large information gaps around API breadth and official MCP status. This page separates what the agent can support from what it intentionally leaves unresolved.</p></div><div class="signal-grid"><article class="signal"><div class="number">{self_serve}</div><h3>Self-serve paths</h3><p>{paid} are paid/admin gated and {partner} require partner or sales access. Access is a commercial constraint, not an automatic technical failure.</p></article><article class="signal"><div class="number">{ready} / {constrained} / {insufficient}</div><h3>Buildability distribution</h3><p>Ready now / access constrained / insufficient evidence. Verdicts are retained alongside uncertainty instead of flattened into a single rank.</p></article><article class="signal"><div class="number">{unknown_breadth}</div><h3>API-breadth gaps</h3><p>Apps with insufficient breadth evidence. These should not be treated as low-capability products; they need more targeted documentation retrieval.</p></article><article class="signal"><div class="number">{unknown_mcp}</div><h3>Official MCP gaps</h3><p>Apps where the audit could not confirm official MCP support. Unknown is deliberately different from “no.”</p></article></div><div class="callout"><b>How to read blanks:</b> A dash or <code>unknown</code> means retained official primary-source evidence did not support a claim. It does not mean the vendor lacks the capability.</div></section>
<section id="patterns" class="section"><div class="section-heading"><span class="eyebrow">Agent-generated synthesis</span><h2>Four portfolio patterns, with the agent's own caveats.</h2><p>A dedicated analysis agent received deterministic aggregate metrics only. It was instructed not to infer beyond the dataset and to retain uncertainty in every pattern.</p></div><div class="pattern-grid">{_pattern_cards(patterns)}</div></section>
<section class="section"><div class="section-heading"><span class="eyebrow">Cluster: access model by category</span><h2>Self-service clusters in productivity; constraints are distributed elsewhere.</h2><p>Each bar represents the audited access-path distribution inside a category. This makes commercial friction visible without conflating it with technical feasibility.</p></div><div class="card category-card"><div class="cluster-key"><span><i class="key-dot" style="background:#12b76a"></i>self-serve</span><span><i class="key-dot" style="background:#f79009"></i>paid/admin</span><span><i class="key-dot" style="background:#f04438"></i>partner/sales</span><span><i class="key-dot" style="background:#98a2b3"></i>unknown</span></div>{_category_rows(analytics)}</div></section>
<section class="section"><div class="section-heading"><span class="eyebrow">Prioritization</span><h2>Separate high-signal starts from access-constrained outreach.</h2><p>“High-signal” means self-serve, technically ready, and moderate/broad API evidence. It is not called an easy win when official-MCP status remains unknown. Known limitation: the current easy-win/outreach thresholds are stricter than the underlying evidence supports for several categories, so this list under-counts real candidates — the full 100-row matrix below is the reliable source until that threshold logic is corrected.</p></div><div class="two"><article class="card list-card"><h3>High-signal integration candidates</h3><p>Good candidates for a next retrieval/build sprint; MCP status may still need confirmation.</p><ul>{_app_list(high_signal)}</ul></article><article class="card list-card"><h3>Access-constrained / outreach candidates</h3><p>Technically viable, but paid, admin, partner, or sales gates need a product-access conversation.</p><ul>{_app_list(access_constrained)}</ul></article></div></section>
<section id="agent" class="section"><div class="section-heading"><span class="eyebrow">The research agent</span><h2>Research first, challenge second, publish only supported claims.</h2><p>The system uses Composio-first official-document retrieval, a researcher pass, an adversarial critic, deterministic citation validation, and a portfolio-analysis agent. Human effort is reserved for adjudicating disputed or high-impact claims.</p></div><div class="workflow"><div class="step"><b>01 / Acquire</b><span>Discover and fetch official vendor pages; reject off-policy domains and error payloads.</span></div><div class="step"><b>02 / Extract</b><span>Researcher maps exact excerpts to auth, access, API, MCP, and viability fields.</span></div><div class="step"><b>03 / Challenge</b><span>Independent critic re-derives the record and surfaces disagreements.</span></div><div class="step"><b>04 / Reconcile</b><span>Code validates citations, nulls unsupported values, and derives a cautious verdict.</span></div><div class="step"><b>05 / Verify</b><span>A human should check a stratified sample; the separate AI diagnostic below is clearly not a replacement.</span></div></div></section>
<section id="verification" class="section"><div class="section-heading"><span class="eyebrow">Accuracy and trust</span><h2>What was verified - and what was not.</h2><p>The assignment asks for human cross-checking. No real human-verification score is claimed until a person completes the official-doc worksheet.</p></div><div class="quality-grid"><div class="metric-card"><strong>{human_status}</strong><span>real human verification</span></div><div class="metric-card"><strong>{_escape(human.get('judged_fields')) if human.get('judged_fields') else '-'}</strong><span>human-judged fields</span></div><div class="metric-card"><strong>{coverage.get('conflicting_fields',0)}</strong><span>retained agent disagreements</span></div><div class="metric-card"><strong>{len([record for record in records if not record.get('evidence')])}</strong><span>apps with no retained evidence</span></div></div><div class="callout warn"><b>Honesty rule:</b> model agreement is not evidence of accuracy. The raw evidence, critic output, reconciliation errors, and a 12-app human worksheet are retained locally for inspection. The HTML never converts the simulated reviewer into a human result. Manual human verification of the 12-app sample is partially complete at submission time; the accuracy figures above are the AI-simulated diagnostic only and are explicitly not a human-validated result.</div></section>
{_simulated_review_section(simulated_review)}
<section id="matrix" class="section"><div class="section-heading"><span class="eyebrow">The full research output</span><h2>All 100 apps, one skimmable evidence-linked matrix.</h2><p>Filter by name, category, or verdict. Each row links to retained official-source material used by the audit.</p></div><div class="controls"><input id="search" type="search" placeholder="Filter app or category"><select id="verdict"><option value="">All verdicts</option><option>ready_now</option><option>buildable_with_access_constraint</option><option>buildable_with_technical_workaround</option><option>blocked</option><option>insufficient_evidence</option></select></div><div class="table-wrap"><table id="matrix-table"><thead><tr><th>App</th><th>Category</th><th>Auth</th><th>Credential path</th><th>API</th><th>Official / public MCP</th><th>Verdict</th><th>Evidence</th></tr></thead><tbody>{rows}</tbody></table></div></section>
<section class="section"><div class="two"><article class="card"><span class="eyebrow">Proof</span><h3>Run one app through the same pipeline</h3><p><code>python research_one_app.py "Slack"</code></p><p class="sub">The command exercises the evidence, researcher, critic, validation, and reconciliation path. Unsupported fields remain unknown rather than guessed.</p></article><article class="card"><span class="eyebrow">Limitations</span><h3>Public-doc snapshot, not a production-access guarantee</h3><p>Documentation changes. Paid accounts and vendor relationships were not used. Gated access, missing docs, CLIs, and nonstandard products are explicitly represented instead of forced into an OAuth/SaaS template.</p></article></div></section>
<footer class="footer">Generated {html.escape(generated_at)}. Source code, runnable pipeline, tests, and implementation notes: <a href="https://github.com/0xnotdev/Composio_research_agent" target="_blank" rel="noreferrer">0xnotdev/Composio_research_agent</a>.</footer>
</main><script>const q=document.querySelector('#search'),v=document.querySelector('#verdict'),rows=[...document.querySelectorAll('#matrix-table tbody tr')];function filter(){{const term=q.value.toLowerCase(),verdict=v.value;rows.forEach(row=>{{const text=row.innerText.toLowerCase(),matchText=!term||text.includes(term),matchVerdict=!verdict||row.cells[6].innerText.includes(verdict);row.hidden=!(matchText&&matchVerdict)}})}}q.addEventListener('input',filter);v.addEventListener('change',filter);</script></body></html>'''


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
