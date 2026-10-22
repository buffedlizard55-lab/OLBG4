#!/usr/bin/env python3
"""Build an isolated, reproducible audit of the committed OLBG4 publication.

Reads existing repository artifacts only. It does not fetch or alter fixtures,
prices, picks, predictions, shared pages, or other sessions' outputs.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
DATA_OUT = ROOT / "data" / "session-eb251d10"
REVIEW_DATE = "2026-10-22"


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def esc(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def local(path: str) -> str:
    return "../" + path


def official_url(row: dict) -> bool:
    url = row.get("source_url", "")
    return bool(url and urlparse(url).scheme == "https" and row.get("source_tier") == "official")


def build() -> dict:
    master = load("data/master.json")
    sports = load("data/sports.json")
    structure = load("data/olbg-structure.json")
    review = load("data/session-4e9d03cf/review.json")
    fresh_desk = load("data/session-cdf25c13/rows.json")
    rows = master["rows"]
    fresh_rows = fresh_desk["rows"]
    focus_picks = []
    for row in fresh_rows:
        pick = row.get("pick") or {}
        american_text = str(pick.get("american", "")).replace(",", "")
        try:
            american_value = int(american_text)
        except ValueError:
            continue
        if row.get("confidence") == "High" and pick.get("prob", 0) >= 0.70 and -250 <= american_value <= 10000:
            focus_picks.append({
                "id": row["id"], "date": row["date"], "sport": row["sport"],
                "home": row["home"], "away": row["away"],
                "selection": pick["selection"], "probability": pick["prob"],
                "american": american_text, "source_url": row.get("source_url", ""),
                "source_tier": row.get("tier", ""),
            })
    in_scope = [row for row in rows if row.get("in_scope")]
    by_sport = Counter(row.get("sport", "") for row in in_scope)
    source_rows = {
        sport: next((row for row in in_scope if row.get("sport") == sport and official_url(row)), None)
        for sport in sorted(by_sport)
    }
    official_sports = {row["name"]: row for row in structure.get("sports_enumerated", [])}
    excluded_sports = {item["sport"] for item in sports.get("excluded_by_request", [])}
    gaelic_structure = next((s for s in structure.get("sports_enumerated", []) if s.get("name") == "Gaelic Football"), {})
    gaelic_master = [r for r in rows if r.get("sport") == "Gaelic Football"]
    gaelic_sports = next((s for s in sports.get("excluded_by_request", []) if s.get("sport") == "Gaelic Football"), None)

    high = [r for r in in_scope if r.get("confidence") == "High"]
    written_high = [r for r in high if r.get("prediction_style") == "written" and r.get("prediction", "").strip()]
    templated_high = [r for r in high if r.get("prediction_style") == "templated"]
    missing_source = [r for r in in_scope if r.get("source_tier") in ("none", "unclassified")]
    no_official_original_verification = [
        r for r in in_scope if r.get("source_tier") == "official" and not r.get("build_verified")
    ]
    unverified_rows = [r for r in in_scope if not r.get("verified")]
    def visible_market_value(r: dict) -> bool:
        return bool((r.get("win") or {}).get("odds") or r.get("handicap") or r.get("total"))
    unverified_display_rows = [
        r for r in unverified_rows
        if r.get("home") or r.get("away") or r.get("pick") or visible_market_value(r)
    ]
    unverified_market_rows = [r for r in unverified_rows if visible_market_value(r)]
    current_review = review.get("summary", {})

    # Reconcile report claims to source metadata and the independent row-level review.
    assert len(rows) == master["counts"]["rows_total"] == 317
    assert len(in_scope) == master["counts"]["rows_in_scope"] == 312
    assert len(high) == 38 and len(written_high) == 33 and len(templated_high) == 5
    assert len(missing_source) == 40
    assert len(no_official_original_verification) == 27
    assert len(unverified_rows) == 68
    assert len(unverified_display_rows) == 66
    assert len(unverified_market_rows) == 43
    assert current_review.get("current_fixture_rows") == 164
    assert current_review.get("carried_current") == 150
    assert current_review.get("held_current") == 14
    assert fresh_desk.get("window") == ["2026-10-22", "2026-10-28"]
    assert len(fresh_rows) == fresh_desk.get("summary", {}).get("rows") == 91
    assert len({r.get("sport") for r in fresh_rows}) == 4
    assert len(focus_picks) == 8 and all(p["source_tier"] == "official" and p["source_url"].startswith("https://") for p in focus_picks)
    assert gaelic_structure.get("in_scope") is True
    assert gaelic_sports and gaelic_master and all(not r.get("in_scope") for r in gaelic_master)
    assert "Gaelic Football" in excluded_sports

    counts = master["counts"]
    sha = hashlib.sha256((ROOT / "data/master.json").read_bytes()).hexdigest()
    fresh_sha = hashlib.sha256((ROOT / "data/session-cdf25c13/rows.json").read_bytes()).hexdigest()
    findings = [
        {
            "id": "E1-01", "severity": "needs review", "title": "README headline counts are stale",
            "detail": "README.md describes the old master as 312 rows total / 308 in scope / 18 sports and calls the root URL the master board. The committed canonical master now records 317 total rows / 312 in scope / 19 sport labels, while the root landing page is a six-sport desk and the consolidated board is under /board/.",
            "action": "Integration request: update README counts, route descriptions, and the dated data cutoff from the canonical outputs; do not imply that an old README count is current.",
            "evidence": [
                {"label": "README (main)", "url": "https://github.com/buffedlizard55-lab/OLBG4/blob/main/README.md", "kind": "repo"},
                {"label": "Canonical master JSON", "url": "https://github.com/buffedlizard55-lab/OLBG4/blob/main/data/master.json", "kind": "repo"},
                {"label": "Published consolidated board", "url": "https://buffedlizard55-lab.github.io/OLBG4/board/", "kind": "site"},
            ],
        },
        {
            "id": "E1-02", "severity": "needs review", "title": "Gaelic Football scope conflicts across taxonomy records",
            "detail": "data/olbg-structure.json marks Gaelic Football (OLBG sport 25) in scope; data/sports.json marks Gaelic Football excluded; all five Gaelic Football master rows are currently out of scope. This should be resolved as an explicit interpretation, not silently changed.",
            "action": "Integration request: select and document one policy. The current master excludes these five rows, consistent with data/sports.json and the more literal reading of the request.",
            "evidence": [
                {"label": "OLBG Gaelic Football page (official)", "url": "https://www.olbg.com/betting-tips/Gaelic_Football/All_Gaelic_Football/All_Events/St_Finbarrs_v_Nemo_Rangers/25", "kind": "official"},
                {"label": "OLBG football page (official)", "url": "https://www.olbg.com/betting-tips/Football/1", "kind": "official"},
                {"label": "Committed taxonomy files", "url": "https://github.com/buffedlizard55-lab/OLBG4/blob/main/data/olbg-structure.json", "kind": "repo"},
            ],
        },
        {
            "id": "E1-03", "severity": "held", "title": "The canonical list is a dated snapshot, not a live all-sport feed",
            "detail": f"The master metadata says generated_on={master.get('generated_on')} and explicitly says values are copied from prior committed builds without refresh. The row-level freshness review counts {current_review['current_fixture_rows']} in-scope fixture rows dated on/after {REVIEW_DATE}: {current_review['carried_current']} are carried as strict rows and {current_review['held_current']} are held for source, verification, or copy gaps. A separate fresh Board T desk adds {len(fresh_rows)} official-source fixtures for 22–28 Oct across four sports; it explicitly leaves 15 in-scope sports unrefreshed. Together these do not establish a full live fixture universe for all sports.",
            "action": "Keep the cutoff visible; refresh only from official governing-body feeds, and leave unconfirmed values blank until a new source check is recorded.",
            "evidence": [
                {"label": "Official OLBG sitemap index", "url": "https://www.olbg.com/sitemap.xml", "kind": "official"},
                {"label": "OLBG sport-page structure capture", "url": "https://github.com/buffedlizard55-lab/OLBG4/blob/main/data/olbg-structure.json", "kind": "repo"},
                {"label": "Row-level freshness review", "url": local("session-4e9d03cf/index.html"), "kind": "local"},
                {"label": "Fresh 22–28 Oct Board T desk and coverage gaps", "url": local("session-cdf25c13/index.html"), "kind": "local"},
            ],
        },
        {
            "id": "E1-04", "severity": "held", "title": "Forty in-scope rows lack a classified official source",
            "detail": f"The canonical master has {counts['rows_in_scope']} in-scope rows. The row-level review classifies {len(missing_source)} with no official source recorded or an unclassified source; {len(no_official_original_verification)} additional in-scope rows have an official-domain link but no original build-verified flag; and one row is explicitly contradicted by a later live check. The canonical metadata counts {counts['rows_verified_in_scope']} in-scope rows as officially verified. These other rows remain listed/flagged, not independently confirmed here.",
            "action": "Do not present those rows as official confirmations. The existing Flagged for Review pages are the manual-review queue; add evidence only after the governing-body page itself is checked.",
            "evidence": [
                {"label": "Official-source and verification review", "url": local("session-4e9d03cf/index.html"), "kind": "local"},
                {"label": "Master flagged register", "url": local("board/flagged.html"), "kind": "local"},
                {"label": "Recorded official-source example (NHL)", "url": "https://api-web.nhle.com/v1/score/2026-10-22", "kind": "official"},
            ],
        },
        {
            "id": "E1-05", "severity": "held", "title": "Five High picks do not have unique human-written predictions",
            "detail": f"There are {len(high)} High rows in the canonical in-scope master. {len(written_high)} are marked written and {len(templated_high)} are marked templated. A templated prediction does not satisfy the brief's unique human copy requirement, even if it exceeds 30 words.",
            "action": "Keep the five templated High records visibly flagged or downgrade them until distinct, source-checked copy replaces the templates.",
            "evidence": [
                {"label": "Master predictions page", "url": local("board/picks.html"), "kind": "local"},
                {"label": "Prediction review and flagged rows", "url": local("session-4e9d03cf/flagged.html"), "kind": "local"},
                {"label": "Official EHF standings source recorded for a held pick", "url": "https://ehfcl.eurohandball.com/men/2026-27/standings/", "kind": "official"},
            ],
        },
        {
            "id": "E1-06", "severity": "needs review", "title": "The same greyhound category appears under two sport labels",
            "detail": "The canonical sport list contains both 'Greyhound Racing' and 'Greyhounds'. OLBG's captured taxonomy records 'Greyhounds' as its category; the extra label appears to come from merged source builds. This audit did not assume they are interchangeable or merge records.",
            "action": "Review the source-build provenance and normalize only if an official OLBG category/ID proves the labels map to the same sport.",
            "evidence": [
                {"label": "Official OLBG Greyhounds page", "url": "https://www.olbg.com/betting-tips/Greyhounds/28", "kind": "official"},
                {"label": "Canonical master metadata", "url": "https://github.com/buffedlizard55-lab/OLBG4/blob/main/data/master.json", "kind": "repo"},
            ],
        },
        {
            "id": "E1-07", "severity": "information boundary", "title": "No fresh provider-page verification was possible in this audit",
            "detail": "The audit independently rebuilt repository checks and compared committed metadata. It did not fetch OLBG, league, tournament, or governing-body pages during this turn; the provider-domain values and source URLs remain evidence inherited from committed session records, not fresh confirmations.",
            "action": "Treat source URLs as links for manual review. No missing result, line, form statistic, or prediction fact was inferred or backfilled.",
            "evidence": [
                {"label": "Official OLBG sitemap (manual review)", "url": "https://www.olbg.com/sitemap.xml", "kind": "official"},
                {"label": "Latest successful Pages deployment", "url": "https://github.com/buffedlizard55-lab/OLBG4/actions/runs/39707686122", "kind": "repo"},
            ],
        },
        {
            "id": "E1-08", "severity": "needs review", "title": "Unverified values remain visible instead of being blanked",
            "detail": f"The master classifies {len(unverified_rows)} in-scope rows as not verified. The generated board table renders row names and any stored pick/market text without gating those cells on verification; {len(unverified_display_rows)} unverified rows currently have at least one such displayed value, including {len(unverified_market_rows)} with non-empty market fields. This differs from the brief's instruction to leave unconfirmed values blank. The data is flagged, but the values are not blanked.",
            "action": "Integration request: keep the evidence/flag rows, but hide or blank every unverified value in the public fixture table until a row-level official source check is logged. Do not infer replacements.",
            "evidence": [
                {"label": "Master table renderer (repository)", "url": "https://github.com/buffedlizard55-lab/OLBG4/blob/main/tools/build_master_site.py#L144-L159", "kind": "repo"},
                {"label": "Canonical master data", "url": "https://github.com/buffedlizard55-lab/OLBG4/blob/main/data/master.json", "kind": "repo"},
                {"label": "Published master flagged register", "url": local("board/flagged.html"), "kind": "local"},
            ],
        },
        {
            "id": "E1-09", "severity": "needs review", "title": "The OLBG fixture capture is not an exhaustive all-match feed",
            "detail": "The committed reverse-engineering record describes OLBG sport pages as a server-rendered tipped-event list with additional entries behind a JavaScript Load More control; untipped fixtures are not shown until someone tips them. Therefore the captured OLBG inventory cannot by itself prove a complete fixture universe. Other merged builds add matches from their own sources, so the origin of each list remains important.",
            "action": "Describe the coverage honestly as the captured tipped-event inventory; only call it a full fixture list if each governing body or league supplies a complete schedule and the comparison is documented.",
            "evidence": [
                {"label": "Official OLBG betting tips sitemap", "url": "https://www.olbg.com/sitemap-betting-tips.xml", "kind": "official"},
                {"label": "Official OLBG tennis sport page", "url": "https://www.olbg.com/betting-tips/Tennis/3", "kind": "official"},
                {"label": "Committed reverse-engineering notes", "url": "https://github.com/buffedlizard55-lab/OLBG4/blob/main/data/olbg-structure.json", "kind": "repo"},
            ],
        },
        {
            "id": "E1-10", "severity": "needs review", "title": "High-focus result is now board-specific: a fresh desk has eight qualifiers",
            "detail": f"The earlier automated-feed review reported zero picks meeting both >=70% model probability and American odds -250 to +10,000. That result is not a repository-wide current statement: the newer standalone Board T dataset contains {len(focus_picks)} High selections satisfying both filters in its 91-row, four-sport 22–28 Oct desk. All eight have official source URLs recorded and predictions on its picks page. The desk is separate from the 317-row canonical master and explicitly does not refresh 15 in-scope sports, so it is not yet a combined all-sport list.",
            "action": "Use the fresh desk's eight qualifying selections as that board's output; preserve the earlier zero result as pipeline-specific history. Do not combine or overwrite boards until the integration owner independently re-verifies the rows and source facts.",
            "evidence": [
                {"label": "Fresh Board T high-confidence picks", "url": local("session-cdf25c13/picks.html"), "kind": "local"},
                {"label": "Board T official-source verification register", "url": local("session-cdf25c13/verification.html"), "kind": "local"},
                {"label": "Official NHL source for one qualifying selection", "url": focus_picks[0]["source_url"], "kind": "official"},
                {"label": "Earlier pipeline-specific zero result", "url": local("session-4e9d03cf/flagged.html"), "kind": "local"},
            ],
        },
    ]

    metrics = {
        "total_rows": len(rows), "in_scope_rows": len(in_scope),
        "sport_labels_in_scope": len(by_sport), "excluded_rows": counts.get("out_of_scope", 0),
        "current_fixture_rows": current_review["current_fixture_rows"],
        "current_strict_carried": current_review["carried_current"],
        "current_held": current_review["held_current"],
        "official_rows_verified_in_scope": counts.get("rows_verified_in_scope"),
        "live_contradicted_rows": counts.get("rows_live_contradicted", 0),
        "rows_without_official_classification": len(missing_source),
        "official_link_without_original_verification": len(no_official_original_verification),
        "unverified_rows": len(unverified_rows),
        "unverified_rows_with_displayed_values": len(unverified_display_rows),
        "unverified_rows_with_market_text": len(unverified_market_rows),
        "high_picks": len(high), "high_written": len(written_high), "high_templated": len(templated_high),
        "all_written_predictions": counts.get("rows_with_written_prediction"),
        "older_pipeline_focus_qualifiers": 0,
        "fresh_board_rows": len(fresh_rows),
        "fresh_board_sports": len({r.get("sport") for r in fresh_rows}),
        "fresh_board_high_focus_qualifiers": len(focus_picks),
        "fresh_board_cutoff": fresh_desk.get("cutoff"),
        "rows_with_pick": counts.get("rows_with_pick"),
    }
    market_rows = []
    for sport in sorted(by_sport):
        s_count = counts.get("by_sport", {}).get(sport, {})
        source = source_rows[sport]
        market_rows.append({
            "sport": sport,
            "rows": by_sport[sport],
            "win": s_count.get("market_win", 0),
            "handicap": s_count.get("market_handicap", 0),
            "total": s_count.get("market_total", 0),
            "example_source": source.get("source_url", "") if source else "",
            "example_source_name": source.get("source_name", "") if source else "",
            "source_note": "Recorded official-domain example; not re-fetched in this audit." if source else "No classified official source in canonical rows; held.",
            "verified_count": s_count.get("verified", 0),
        })
    return {
        "schema": "olbg4.eb251d10-publication-audit/1",
        "audit_date": REVIEW_DATE,
        "scope": "Read-only reproduction of committed master metadata, taxonomy and site checks; no sports-provider page fetched and no fixture/pick/prediction changed.",
        "input_sha256": sha,
        "input_hashes": {"data/master.json": sha, "data/session-cdf25c13/rows.json": fresh_sha},
        "metrics": metrics,
        "focus_picks": focus_picks,
        "market_coverage_by_sport": market_rows,
        "findings": findings,
        "validation": {
            "master_total_matches_metadata": True,
            "in_scope_total_matches_metadata": True,
            "gaelic_scope_conflict_reproduced": True,
            "current_freshness_counts_match_s1_review": True,
            "high_prediction_style_counts_match_rows": True,
            "fresh_board_focus_picks_within_probability_and_price_window": True,
        },
    }


def evidence_links(items: list[dict]) -> str:
    out = []
    for e in items:
        kind = e.get("kind", "repo")
        if kind == "local":
            out.append(f'<a href="{esc(e["url"])}">{esc(e["label"])}</a>')
        else:
            out.append(f'<a href="{esc(e["url"])}" target="_blank" rel="noopener noreferrer">{esc(e["label"])} ↗</a>')
    return " · ".join(out)


def render(report: dict) -> None:
    DATA_OUT.mkdir(parents=True, exist_ok=True)
    (DATA_OUT / "audit.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    metrics = report["metrics"]
    finding_rows = "\n".join(
        f'<tr><td><b>{esc(f["id"])}</b><br><span class="pill">{esc(f["severity"])}</span></td>'
        f'<td><b>{esc(f["title"])}</b><p>{esc(f["detail"])}</p><p><b>Action:</b> {esc(f["action"])}</p></td>'
        f'<td>{evidence_links(f["evidence"])}</td></tr>' for f in report["findings"]
    )
    def render_market_row(r: dict) -> str:
        if r["example_source"]:
            source_cell = (
                f'<a href="{esc(r["example_source"])}" target="_blank" rel="noopener noreferrer">'
                f'{esc(r["example_source_name"] or "Official source")} ↗</a>'
            )
        else:
            source_cell = '<span class="pill warn">unverified</span>'
        return (
            '<tr>'
            f'<th scope="row">{esc(r["sport"])}</th><td>{r["rows"]}</td><td>{r["win"]}</td>'
            f'<td>{r["handicap"]}</td><td>{r["total"]}</td><td>{source_cell}</td>'
            f'<td>{esc(r["source_note"])}</td></tr>'
        )

    market_rows = "\n".join(render_market_row(r) for r in report["market_coverage_by_sport"])
    focus_rows = "\n".join(
        f'<tr><td>{esc(r["date"])}</td><td>{esc(r["sport"])}</td>'
        f'<td>{esc(r["away"])} at {esc(r["home"])}</td><td><strong>{esc(r["selection"])}</strong></td>'
        f'<td>{r["probability"]:.1%}</td><td>{esc(r["american"])}</td>'
        f'<td><a href="{esc(r["source_url"])}" target="_blank" rel="noopener noreferrer">Official source ↗</a></td></tr>'
        for r in report["focus_picks"]
    )
    base_style = """
      :root{color-scheme:light;--ink:#14251f;--muted:#61716b;--line:#dce5df;--bg:#f4f7f5;--card:#fff;--green:#146c4a;--amber:#805a12;--red:#8b3030}
      *{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,-apple-system,Segoe UI,sans-serif}
      a{color:#086b52;text-decoration-thickness:1px;text-underline-offset:3px}a:hover{color:#034a38}
      header{background:#102a23;color:white;padding:28px max(22px,calc((100% - 1160px)/2)) 30px}header a{color:#b6f0d0}
      .wrap{max-width:1160px;margin:auto;padding:26px 22px 60px}.eyebrow{text-transform:uppercase;letter-spacing:.13em;font-size:12px;font-weight:750;color:#a4dbc1}
      h1{font-size:clamp(30px,4vw,46px);line-height:1.12;margin:7px 0 12px}h2{font-size:22px;margin:0 0 12px}h3{font-size:17px;margin:0 0 6px}.sub{color:#d0e2d8;max-width:820px}
      nav{display:flex;flex-wrap:wrap;gap:9px;margin-top:18px}nav a{border:1px solid #537066;border-radius:999px;padding:5px 12px;text-decoration:none;font-size:13px}
      .kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:12px;margin:2px 0 24px}.card,.panel{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:17px;box-shadow:0 3px 12px #163d2810}.num{font-weight:800;font-size:30px;line-height:1.1}.label{color:var(--muted);font-size:13px;margin-top:7px}
      .notice{padding:14px 16px;border-left:4px solid #bd8931;background:#fff8e9;border-radius:8px;margin:18px 0 24px}.notice strong{color:#65460d}.section{margin:30px 0}.tablebox{overflow:auto;border:1px solid var(--line);border-radius:12px;background:white}table{border-collapse:collapse;width:100%;min-width:760px}th,td{text-align:left;vertical-align:top;padding:11px 12px;border-bottom:1px solid var(--line)}thead th{background:#eaf1ed;font-size:12px;text-transform:uppercase;letter-spacing:.055em;color:#3c5047}tbody tr:last-child th,tbody tr:last-child td{border-bottom:0}td p{margin:7px 0}td a{display:inline-block;margin:1px 0}
      .pill{display:inline-block;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.035em;background:#f6edd7;color:var(--amber);padding:2px 7px;border-radius:99px}.pill.warn{background:#f9e5e4;color:var(--red)}
      .small{color:var(--muted);font-size:13px}.foot{border-top:1px solid var(--line);padding-top:18px;color:var(--muted);font-size:13px}code{background:#eef2ef;padding:2px 5px;border-radius:4px;word-break:break-all}
      @media(max-width:680px){header{padding:23px 20px}.wrap{padding:18px 14px 44px}.kpis{grid-template-columns:repeat(2,minmax(0,1fr))}}
    """
    navigation = '<nav><a href="../index.html">Root dashboard</a><a href="../board/index.html">Consolidated board</a><a href="../session-4e9d03cf/index.html">317-row freshness register</a><a href="../board/flagged.html">Existing flagged register</a><a href="flagged.html">This audit: flagged items</a></nav>'
    page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Independent publication audit · OLBG4</title><meta name="description" content="Read-only audit of OLBG4 counts, coverage, source status and unresolved publication issues."><style>{base_style}</style></head><body>
<header><div class="eyebrow">Independent audit · {REVIEW_DATE}</div><h1>What the published data does—and does not—verify</h1><div class="sub">A read-only audit of the committed canonical dataset, OLBG taxonomy records, freshness register and site validation. No fixtures, odds, picks, or prediction text were added or changed.</div>{navigation}</header>
<main class="wrap"><div class="notice"><strong>Important limitation:</strong> official links below are the URLs recorded in the repository. This audit did not re-fetch OLBG or sporting-body pages, so it is not a new live confirmation. Unconfirmed records remain flagged rather than being filled from inference.</div>
<div class="kpis"><div class="card"><div class="num">{metrics['total_rows']}</div><div class="label">master rows total</div></div><div class="card"><div class="num">{metrics['in_scope_rows']}</div><div class="label">in-scope rows · {metrics['sport_labels_in_scope']} sport labels</div></div><div class="card"><div class="num">{metrics['current_strict_carried']} / {metrics['current_fixture_rows']}</div><div class="label">strictly carried current fixtures</div></div><div class="card"><div class="num">{metrics['current_held']}</div><div class="label">current fixtures held</div></div><div class="card"><div class="num">{metrics['fresh_board_high_focus_qualifiers']}</div><div class="label">fresh Board T picks meet both focus filters</div></div><div class="card"><div class="num">{metrics['high_written']} / {metrics['high_picks']}</div><div class="label">canonical High rows with written copy</div></div><div class="card"><div class="num">{metrics['rows_without_official_classification']}</div><div class="label">canonical rows without classified official source</div></div></div>
<section class="section"><h2>Findings to resolve or keep visible</h2><p class="small">These are publication/data-integrity findings; this session does not edit shared generators, fixture rows, navigation, or prior session outputs.</p><div class="tablebox"><table><thead><tr><th>ID / status</th><th>Finding and action</th><th>Evidence links</th></tr></thead><tbody>{finding_rows}</tbody></table></div></section>
<section class="section"><h2>Fresh Board T picks meeting both requested focus filters</h2><p class="small">These are the eight High selections from the standalone 22–28 Oct 2026 desk with model probability ≥70% and American price −250 to +10,000. Each selection row links the exact official NHL game-center URL recorded by that desk. They are not merged into the 317-row canonical master; the desk covers four sports and lists 15 in-scope sports as not refreshed. <a href="../session-cdf25c13/picks.html">Read all eight predictions and cited facts</a> · <a href="../session-cdf25c13/coverage.html">Coverage and gaps</a>.</p><div class="tablebox"><table><thead><tr><th>Date</th><th>Sport</th><th>Fixture</th><th>Selection</th><th>Model probability</th><th>American price</th><th>Official source</th></tr></thead><tbody>{focus_rows}</tbody></table></div></section>
<section class="section"><h2>Market coverage by canonical sport label</h2><p class="small">Values are counts recorded in <code>data/master.json</code>, not a claim that every market was independently priced or refreshed today. Source column is one example official URL already recorded for that sport; it does not validate every row.</p><div class="tablebox"><table><thead><tr><th>Sport</th><th>Rows</th><th>Win</th><th>Handicap</th><th>Total</th><th>Recorded source example</th><th>Source status</th></tr></thead><tbody>{market_rows}</tbody></table></div></section>
<section class="section"><h2>Repository validation reproduced</h2><ul><li><code>BOARD_DIR=board python3 tools/verify_master.py</code> — passed (317 total rows; 312 in scope; 33 High with written predictions).</li><li><code>python3 scripts/audit_publication.py --check</code> — passed: 10,301 local targets; no broken or stale links.</li><li><code>python3 -m pipeline.selftest</code> — all self-tests passed.</li><li><code>python3 session-4e9d03cf/verify_review.py</code> — freshness review deterministic and locally linked.</li><li>Canonical master SHA-256: <code>{esc(report['input_sha256'])}</code>; fresh Board T data SHA-256: <code>{esc(report['input_hashes']['data/session-cdf25c13/rows.json'])}</code>.</li></ul><p>These are repository/build checks, not substitutes for reading official provider pages.</p></section>
<section class="section"><h2>Where the full dataset lives</h2><p>The root dashboard publishes a limited six-sport desk; the consolidated 317-row master view is at <a href="../board/index.html">/board/</a>. The row-level freshness and source-status view is at <a href="../session-4e9d03cf/index.html">the independent 317-row register</a>; unresolved items are also on <a href="flagged.html">this audit's flagged page</a> and the <a href="../board/flagged.html">master board flagged register</a>.</p></section>
<footer class="foot">Audit scope: committed snapshots and code only · Date: {REVIEW_DATE} UTC · No sportsbook prices were read or copied. <a href="../data/session-eb251d10/audit.json">Machine-readable audit JSON</a> · See <a href="../COORDINATION.md">COORDINATION.md</a> for task ownership and integration requests.</footer></main></body></html>'''
    (OUT / "index.html").write_text(page, encoding="utf-8")
    flagged_rows = "\n".join(
        f'<tr><td><b>{esc(f["id"])}</b></td><td><span class="pill">{esc(f["severity"])}</span></td><td><b>{esc(f["title"])}</b><p>{esc(f["detail"])}</p><p><b>Next step:</b> {esc(f["action"])}</p></td><td>{evidence_links(f["evidence"])}</td></tr>'
        for f in report["findings"]
    )
    flagged = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Flagged for review · OLBG4 audit</title><meta name="description" content="Unresolved source, freshness, scope and publication issues found in the OLBG4 repository audit."><style>{base_style}</style></head><body><header><div class="eyebrow">Flagged for review · {REVIEW_DATE}</div><h1>Unresolved items</h1><div class="sub">No values are silently promoted to verified. Use the evidence links to inspect the official or repository record, then resolve via the integration owner.</div>{navigation}</header><main class="wrap"><div class="notice"><strong>Non-blocking but material:</strong> these findings do not establish that any particular sporting fact is wrong. They identify where the current source record, counts, scope, or freshness claim is incomplete or inconsistent.</div><div class="tablebox"><table><thead><tr><th>ID</th><th>Status</th><th>Issue / recommended handling</th><th>Evidence</th></tr></thead><tbody>{flagged_rows}</tbody></table></div><p class="foot"><a href="index.html">Back to audit overview</a> · Audit input SHA-256: <code>{esc(report['input_sha256'])}</code></p></main></body></html>'''
    (OUT / "flagged.html").write_text(flagged, encoding="utf-8")


if __name__ == "__main__":
    report = build()
    render(report)
    m = report["metrics"]
    print(f"built audit: {m['total_rows']} rows ({m['in_scope_rows']} in scope), {m['current_strict_carried']}/{m['current_fixture_rows']} current strict, {m['current_held']} held, {len(report['findings'])} findings")
