#!/usr/bin/env python3
"""Render the 2026-10-22 freshness and source-traceability review.

This is intentionally a read-only review of the committed OLBG4 datasets.  It does
not invent a fixture, re-price a market, or promote an old selection.  The output
keeps official links only where the canonical master dataset itself classifies the
source as official; everything else is held and published on the Flagged page.

Usage:
    python3 session-4e9d03cf/build_review.py
"""
from __future__ import annotations

import html
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "session-4e9d03cf" / "review.json"
SITE = ROOT / "session-4e9d03cf"
REVIEW_DATE = "2026-10-22"
REVIEW_LABEL = "22 October 2026 (UTC date boundary)"
REPO_URL = "https://github.com/buffedlizard55-lab/OLBG4"
PIPELINE_RUN_URL = f"{REPO_URL}/actions/runs/39680482203"


def load(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def compact(value: Any) -> str:
    """Make an existing market field readable without changing its value."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        return "; ".join(compact(item) for item in value if compact(item))
    if isinstance(value, dict):
        odds = value.get("odds")
        if isinstance(odds, dict):
            bits = [f"{key}: {compact(val)}" for key, val in odds.items()]
            return "; ".join(bits)
        bits = [f"{key}: {compact(val)}" for key, val in value.items() if compact(val)]
        return "; ".join(bits)
    return str(value)


def market_summary(row: dict[str, Any]) -> dict[str, str]:
    return {
        "winner": compact(row.get("win")),
        "handicap": compact(row.get("handicap")),
        "total": compact(row.get("total")),
    }


def source_status(row: dict[str, Any]) -> tuple[str, str, str]:
    """Return (status, official-url-or-blank, disclosure)."""
    url = str(row.get("source_url") or "").strip()
    tier = row.get("source_tier") or "none"
    if tier == "official" and url:
        if row.get("verified"):
            return (
                "official-source / original-build-verified",
                url,
                "The master record labels this source official and records original-build verification. "
                "S1 did not re-open the external page.",
            )
        return (
            "official-source / not-original-build-verified",
            url,
            "An official-domain URL is recorded, but the canonical record is not marked verified. "
            "It is held rather than treated as confirmed.",
        )
    if not url:
        return (
            "no official source recorded",
            "",
            "No source value is shown as an official source. The row is held and must remain unverified.",
        )
    return (
        f"{tier} source — not eligible as official evidence",
        "",
        "A non-official or unclassified prior URL exists in the canonical record. It is not shown "
        "as an official source in this review and the row is held.",
    )


def review_status(row: dict[str, Any], official_url: str) -> tuple[str, str]:
    """Classify rows conservatively for a 22 October current/upcoming desk."""
    if not row.get("in_scope"):
        return "excluded", "Excluded from the requested sports scope; retained only for audit visibility."
    if row.get("row_type") != "fixture":
        return "not-a-fixture", "Market note or incomplete record; it is not a head-to-head match entry."
    if str(row.get("date") or "") < REVIEW_DATE:
        return "historical", "Dated before the review boundary; preserved as history, not an active match."
    if not official_url:
        return "held-source", "No eligible official-source link is available for this row. Leave values unverified."
    if not row.get("verified"):
        return "held-verification", "Official URL is recorded, but the canonical row was not marked originally verified."
    if row.get("confidence") == "High" and (
        row.get("prediction_style") != "written" or count_words(str(row.get("prediction") or "")) < 30
    ):
        return (
            "held-copy",
            "High-confidence copy is templated or shorter than 30 words rather than a compliant unique written "
            "prediction; do not publish it as a high-confidence write-up.",
        )
    return (
        "carried-current",
        "Current/future fixture carried from an original-build-verified official-source record. "
        "No S1 re-pricing or external re-check was performed.",
    )


def american_in_focus(value: Any) -> bool:
    try:
        price = int(str(value).strip())
    except (TypeError, ValueError):
        return False
    return -250 <= price <= 10000


def count_words(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9'’\-]+", text or ""))


def make_rows(master_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for row in master_rows:
        src_state, official_url, src_note = source_status(row)
        state, reason = review_status(row, official_url)
        prediction = str(row.get("prediction") or "")
        results.append(
            {
                "id": row.get("id", ""),
                "date": row.get("date", ""),
                "time": row.get("time", ""),
                "sport": row.get("sport", ""),
                "competition": row.get("competition", ""),
                "home": row.get("home", ""),
                "away": row.get("away", ""),
                "row_type": row.get("row_type", ""),
                "in_scope": bool(row.get("in_scope")),
                "build": row.get("build", ""),
                "selection": row.get("pick", ""),
                "selection_market": row.get("pick_market", ""),
                "confidence": row.get("confidence", "") or "—",
                "markets": market_summary(row),
                "official_source_url": official_url,
                "source_domain": row.get("source_domain", ""),
                "source_status": src_state,
                "source_note": src_note,
                "original_build_verified": bool(row.get("verified")),
                "review_status": state,
                "review_reason": reason,
                "prediction_style": row.get("prediction_style", "") or "none",
                "prediction_words": count_words(prediction),
                "prediction_present": bool(prediction),
                "flags": row.get("flags", []),
            }
        )
    return results


def make_findings(
    master: dict[str, Any], rows: list[dict[str, Any]], snapshot: dict[str, Any], predictions: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    source_held = [r for r in rows if r["review_status"] in {"held-source", "held-verification"}]
    copy_held = [r for r in rows if r["review_status"] == "held-copy"]
    high_templates = [
        r for r in rows
        if r["confidence"] == "High" and r["prediction_style"] != "written"
    ]
    current_high = [p for p in predictions if str(p.get("start_utc", ""))[:10] >= REVIEW_DATE]
    focused = [
        p for p in current_high
        if float(p.get("prob_pct") or 0) >= 70 and american_in_focus(p.get("american"))
    ]
    outside = [
        p for p in current_high
        if not american_in_focus(p.get("american"))
    ]
    master_counts = master.get("counts", {})
    master_in_scope = master_counts.get("rows_in_scope", 0)
    master_sports = len(master_counts.get("sports_in_scope", []))
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    stale_readme = ("308 in-scope rows across 18 sports" in readme or
                    "312 rows total, 308 in scope, 18 sports" in readme)

    return [
        {
            "id": "S1-F01",
            "severity": "needs review",
            "title": "Canonical master metadata is not dated 22 October",
            "detail": (
                f"`data/master.json` says it was generated on {master.get('generated_on')}. "
                f"This S1 review uses {REVIEW_LABEL}; it therefore does not relabel the master "
                "fixtures, lines, or predictions as freshly verified today."
            ),
            "action": "Refresh/re-verify before treating any carried row as a current official confirmation.",
            "evidence": [
                {"label": "Canonical master metadata", "url": "../data/master.json"},
                {"label": "Master methodology", "url": "../board/methodology.html"},
            ],
        },
        {
            "id": "S1-F02",
            "severity": "needs review",
            "title": "Automated fresh-feed coverage is limited to three sports",
            "detail": (
                "The most recent committed automated snapshot names NBA, NHL, and MLB only. "
                "It cannot by itself establish a current all-sport fixture list for the other "
                f"{max(master_sports - 3, 0)} in-scope sports in the master inventory."
            ),
            "action": "Add an official-feed refresh path per in-scope sport; leave unsupported fields blank until then.",
            "evidence": [
                {"label": "Automated snapshot", "url": "../session-4afef1af/data/snapshot.json"},
                {"label": "Successful scheduled run", "url": PIPELINE_RUN_URL},
            ],
        },
        {
            "id": "S1-F03",
            "severity": "held",
            "title": f"{len(source_held)} current/upcoming fixture rows are not publishable as strict official confirmations",
            "detail": (
                "These rows either have no eligible official source link or have an official-domain link "
                "without the canonical build-verified flag. This review preserves the values but does not "
                "present them as confirmed."
            ),
            "action": "Leave the affected fields unverified/blank in a strict current desk until a governing-body page is re-read.",
            "evidence": [
                {"label": "Review rows (filter held-source / held-verification)", "url": "index.html#review-table"},
                {"label": "Canonical master data", "url": "../data/master.json"},
            ],
        },
        {
            "id": "S1-F04",
            "severity": "held",
            "title": f"{len(high_templates)} high-confidence records use templated, not unique, prediction copy",
            "detail": (
                "The canonical data identifies these high-confidence predictions as `templated`. "
                "They do not meet the brief's unique human-written prediction requirement and are held "
                "from S1's strict current view."
            ),
            "action": "Replace only after re-checking each cited official source and writing a distinct 30+ word prediction.",
            "evidence": [
                {"label": "Canonical master data", "url": "../data/master.json"},
                {"label": "Master flagged register", "url": "../board/flagged.html"},
            ],
            "rows": [
                {
                    "id": r["id"], "match": f"{r['home']} vs {r['away']}", "date": r["date"],
                    "source_url": r["official_source_url"], "words": r["prediction_words"],
                }
                for r in high_templates
            ],
        },
        {
            "id": "S1-F05",
            "severity": "info",
            "title": "No current pipeline selection meets both requested focus filters",
            "detail": (
                f"The automated pipeline has {len(current_high)} high-confidence prediction records on/after "
                f"{REVIEW_DATE}, but {len(focused)} have both a model probability of at least 70% and an "
                "originated American price between -250 and +10000. "
                f"{len(outside)} are outside the requested price focus range. No extra pick was invented to fill the gap."
            ),
            "action": "Do not force a focus-list prediction; wait for a qualifying, source-linked model output.",
            "evidence": [
                {"label": "Automated predictions", "url": "../session-4afef1af/data/predictions.json"},
                {"label": "Automated picks page", "url": "../session-4afef1af/picks.html"},
            ],
        },
        {
            "id": "S1-F06",
            "severity": "needs review" if stale_readme else "info",
            "title": "Repository README count claims do not match the current canonical master metadata",
            "detail": (
                f"The current master reports {len(rows)} total rows, {master_in_scope} in scope and "
                f"{master_sports} in-scope sports. The README retains older headline wording "
                "('308 in-scope rows across 18 sports' / '312 rows total, 308 in scope, 18 sports')."
                if stale_readme else
                "The README no longer contains the older count wording checked by this review."
            ),
            "action": "Final integration should regenerate or correct root documentation from the canonical metadata.",
            "evidence": [
                {"label": "Repository README", "url": f"{REPO_URL}/blob/main/README.md"},
                {"label": "Canonical master metadata", "url": "../data/master.json"},
            ],
        },
        {
            "id": "S1-F07",
            "severity": "information boundary",
            "title": "S1 performed structural verification, not a new live external-source read",
            "detail": (
                "This execution environment cannot make arbitrary outbound requests to sports-provider domains. "
                "S1 checked the committed source classification, row state, prediction state, deterministic "
                "build gate, and GitHub Actions evidence; it did not claim a fresh external page read."
            ),
            "action": "Treat the per-row official links as manual-review links; re-open them from an approved network before updating values.",
            "evidence": [
                {"label": "Session review methodology", "url": "index.html#method"},
                {"label": "Scheduled run evidence", "url": PIPELINE_RUN_URL},
            ],
        },
    ]


def html_page(title: str, body: str, active: str) -> str:
    nav = [
        ("index.html", "Review desk", "review"),
        ("flagged.html", "Flagged for review", "flagged"),
        ("../board/index.html", "Canonical board", "board"),
        ("../session-4afef1af/index.html", "Automated desk", "pipeline"),
    ]
    nav_html = "".join(
        f'<a href="{href}" class="{"active" if key == active else ""}">{label}</a>'
        for href, label, key in nav
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex">
  <title>{html.escape(title)} · OLBG4 review</title>
  <meta name="description" content="A conservative freshness and official-source traceability review of the committed OLBG4 data.">
  <link rel="stylesheet" href="assets/review.css">
</head>
<body>
<header class="topbar">
  <div class="shell navwrap"><a class="brand" href="index.html"><span class="brand-mark">O4</span><span>OLBG4 <small>freshness review</small></span></a><nav>{nav_html}</nav></div>
</header>
<main class="shell">{body}</main>
<footer class="shell footer"><p>Prepared from committed repository data only. This is not betting advice. Values without eligible official evidence are held rather than inferred.</p></footer>
<script src="assets/review.js"></script>
</body>
</html>
"""


def build_index(data: dict[str, Any]) -> str:
    counts = data["summary"]
    sports = "".join(
        f'<option value="{html.escape(s)}">{html.escape(s)}</option>'
        for s in data["sports"]
    )
    body = f"""
<section class="hero">
  <p class="eyebrow">Independent session S1 · {REVIEW_LABEL}</p>
  <h1>Current-match freshness review</h1>
  <p class="lede">A conservative, source-first overlay for the committed OLBG4 inventory. It does not make new fixture claims, odds, or predictions. A row is carried into the strict current view only when it is in scope, a head-to-head fixture, dated today or later, and the canonical record has an official-source URL plus its original build-verified flag. High-confidence rows also need a unique written prediction.</p>
  <div class="callout"><strong>Important:</strong> the canonical master is dated <code>{html.escape(data['master_generated_on'])}</code>, not 22 October. “Carried current” means a prior build recorded official evidence; it does <em>not</em> mean S1 re-opened that external page today. Use the official link in each row for manual review.</div>
</section>

<section class="cards" aria-label="Review summary">
  <article><span>Canonical rows</span><strong>{counts['total_rows']}</strong><small>all retained audit rows</small></article>
  <article><span>Current/upcoming fixtures</span><strong>{counts['current_fixture_rows']}</strong><small>in-scope · {REVIEW_DATE} onward</small></article>
  <article><span>Strict carried rows</span><strong>{counts['carried_current']}</strong><small>official URL + original verification</small></article>
  <article class="warn-card"><span>Held current rows</span><strong>{counts['held_current']}</strong><small>source, verification, or copy gap</small></article>
  <article><span>Written high write-ups</span><strong>{counts['high_written']}</strong><small>canonical written predictions</small></article>
</section>

<section class="panel" id="method">
  <div class="section-heading"><div><p class="eyebrow">How this review works</p><h2>Rules that prevent silent promotion</h2></div></div>
  <ol class="rules">
    <li><b>Official source link:</b> shown only if the canonical master classifies the source as official. A blank means blank; S1 does not substitute a guess.</li>
    <li><b>Current view:</b> only in-scope head-to-head fixtures dated {REVIEW_DATE} or later are candidates. Historical, market-note, incomplete and excluded rows remain visible in the full audit table.</li>
    <li><b>High confidence:</b> templated high-confidence copy is held. The original official link remains available on the Flagged page, but the prediction is not treated as compliant unique writing.</li>
    <li><b>Focus range:</b> the pipeline’s 70%+ / −250 to +10000 American-odds subset is reported exactly as supplied; no artificial pick is added if it is empty.</li>
  </ol>
</section>

<section class="panel" id="review-table">
  <div class="section-heading">
    <div><p class="eyebrow">Line-by-line audit</p><h2>All canonical entries</h2><p class="muted">Filtering changes visibility only; the downloaded review data retains all {counts['total_rows']} rows. “Markets” are carried values from the canonical record, not S1-originated lines.</p></div>
    <a class="button secondary" href="../data/session-4e9d03cf/review.json">Download review JSON</a>
  </div>
  <div class="filters" aria-label="Table filters">
    <label>View <select id="f-view"><option value="all">All rows ({counts['total_rows']})</option><option value="current">Current/upcoming fixtures ({counts['current_fixture_rows']})</option><option value="strict">Strict carried current ({counts['carried_current']})</option><option value="held">Held / flagged rows</option></select></label>
    <label>Sport <select id="f-sport"><option value="">All sports</option>{sports}</select></label>
    <label>Search <input id="f-query" type="search" placeholder="team, event, selection"></label>
    <p id="shown" aria-live="polite"></p>
  </div>
  <div class="table-scroll"><table id="rows"><thead><tr><th>Date</th><th>Sport</th><th>Match / competition</th><th>Carried selection</th><th>Markets</th><th>Official source</th><th>Review state</th></tr></thead><tbody><tr><td colspan="7">Loading committed review data…</td></tr></tbody></table></div>
</section>

<section class="split-grid">
  <article class="panel"><p class="eyebrow">What can be used today</p><h2>Strict view</h2><p><strong>{counts['carried_current']}</strong> current/upcoming fixture rows pass the review’s structural gate. Their selection and market text are still historical model output; use each official link to validate live changes before publication.</p><a class="text-link" href="#review-table" data-set-view="strict">Open strict rows →</a></article>
  <article class="panel"><p class="eyebrow">What is intentionally held</p><h2>No source? No promotion.</h2><p><strong>{counts['held_current']}</strong> current/upcoming rows are held for missing/insufficient source verification or templated high-confidence text. They are not erased, so the evidence gap remains reviewable.</p><a class="text-link" href="flagged.html">See flagged findings →</a></article>
  <article class="panel"><p class="eyebrow">Fresh automated feed</p><h2>NBA · NHL · MLB only</h2><p>The latest committed pipeline snapshot is from <code>{html.escape(data['pipeline_generated_utc'])}</code>. It has its own source-linked market and prediction pages; it does not refresh every in-scope sport.</p><a class="text-link" href="../session-4afef1af/index.html">Open automated desk →</a></article>
</section>
"""
    return html_page("Freshness review", body, "review")


def link_list(evidence: list[dict[str, str]]) -> str:
    return " · ".join(
        f'<a href="{html.escape(item["url"], quote=True)}" target="_blank" rel="noopener noreferrer">{html.escape(item["label"])} ↗</a>'
        for item in evidence
    )


def build_flagged(data: dict[str, Any]) -> str:
    finding_rows = []
    for finding in data["findings"]:
        details = ""
        if finding.get("rows"):
            nested = "<ul class=\"nested\">" + "".join(
                (
                    f'<li><code>{html.escape(row["id"])}</code> — {html.escape(row["date"])} — '
                    f'{html.escape(row["match"])} — {row["words"]} words — '
                    + (f'<a href="{html.escape(row["source_url"], quote=True)}" target="_blank" rel="noopener noreferrer">official source ↗</a>' if row["source_url"] else "no eligible official source")
                    + "</li>"
                )
                for row in finding["rows"]
            ) + "</ul>"
        finding_rows.append(
            "<tr>"
            f"<td><code>{html.escape(finding['id'])}</code><br><span class=\"state {html.escape(finding['severity'].replace(' ', '-'))}\">{html.escape(finding['severity'])}</span></td>"
            f"<td><strong>{html.escape(finding['title'])}</strong><p>{html.escape(finding['detail'])}</p>{details}</td>"
            f"<td>{html.escape(finding['action'])}</td>"
            f"<td>{link_list(finding['evidence'])}</td>"
            "</tr>"
        )
    body = f"""
<section class="hero compact">
  <p class="eyebrow">Independent session S1 · {REVIEW_LABEL}</p>
  <h1>Flagged for review</h1>
  <p class="lede">These are explicit publication boundaries found while auditing the committed datasets. They do not block access to the original evidence; they prevent S1 from presenting an unsupported value as a fresh, verified fact.</p>
  <div class="callout"><strong>Resolution rule:</strong> only a re-read of the linked official source can fill a held value. S1 has not inferred replacements.</div>
</section>
<section class="panel">
  <div class="section-heading"><div><p class="eyebrow">Irregularity register</p><h2>{len(data['findings'])} review findings</h2></div><a class="button secondary" href="index.html">Back to all rows</a></div>
  <div class="table-scroll"><table class="findings"><thead><tr><th>ID / severity</th><th>Finding</th><th>Required action</th><th>Evidence</th></tr></thead><tbody>{''.join(finding_rows)}</tbody></table></div>
</section>
<section class="panel">
  <p class="eyebrow">Manual review links</p><h2>Where the underlying data remains available</h2>
  <ul class="link-list">
    <li><a href="../board/index.html">Canonical master board</a> — all retained source-linked records.</li>
    <li><a href="../board/flagged.html">Canonical master flagged page</a> — prior cross-build conflicts and source gaps.</li>
    <li><a href="../session-4afef1af/picks.html">Automated pipeline picks</a> — its source-linked, three-sport outputs.</li>
    <li><a href="../data/session-4e9d03cf/review.json">S1 machine-readable review</a> — generated entirely from committed inputs.</li>
  </ul>
</section>
"""
    return html_page("Flagged for review", body, "flagged")


def main() -> None:
    master = load(ROOT / "data" / "master.json")
    snapshot = load(ROOT / "session-4afef1af" / "data" / "snapshot.json")
    predictions = load(ROOT / "session-4afef1af" / "data" / "predictions.json")
    rows = make_rows(master["rows"])
    status_counts = Counter(row["review_status"] for row in rows)
    current = [
        row for row in rows
        if row["in_scope"] and row["row_type"] == "fixture" and row["date"] >= REVIEW_DATE
    ]
    held_current = [
        row for row in current
        if row["review_status"] in {"held-source", "held-verification", "held-copy"}
    ]
    high_written = [
        row for row in rows
        if row["confidence"] == "High" and row["prediction_style"] == "written"
    ]
    review = {
        "schema": "olbg4.s1-freshness-review/1",
        "review_date": REVIEW_DATE,
        "review_label": REVIEW_LABEL,
        "scope": (
            "Read-only structural review of data/master.json and the committed automated pipeline snapshot. "
            "No live external sports-provider request was made by S1."
        ),
        "master_generated_on": master.get("generated_on", ""),
        "pipeline_generated_utc": snapshot.get("generated_utc", ""),
        "pipeline_run_url": PIPELINE_RUN_URL,
        "summary": {
            "total_rows": len(rows),
            "in_scope_rows": sum(row["in_scope"] for row in rows),
            "current_fixture_rows": len(current),
            "carried_current": status_counts["carried-current"],
            "held_current": len(held_current),
            "high_written": len(high_written),
            "high_templated": sum(
                row["confidence"] == "High" and row["prediction_style"] != "written" for row in rows
            ),
            "review_statuses": dict(sorted(status_counts.items())),
            "source_states": dict(sorted(Counter(row["source_status"] for row in rows).items())),
        },
        "sports": sorted({row["sport"] for row in rows}),
        "rows": rows,
    }
    review["findings"] = make_findings(master, rows, snapshot, predictions)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(review, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (SITE / "index.html").write_text(build_index(review), encoding="utf-8")
    (SITE / "flagged.html").write_text(build_flagged(review), encoding="utf-8")
    print(
        f"review built: {len(rows)} rows · {len(current)} current fixtures · "
        f"{status_counts['carried-current']} strict carried · {len(held_current)} held current"
    )


if __name__ == "__main__":
    main()
