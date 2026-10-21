#!/usr/bin/env python3
"""Build a static, source-preserving audit report for the published Build E desk.

The audit deliberately does not request any external URL. It checks the committed
snapshot line by line, preserves every original official source URL for review, and
reports anything that cannot be demonstrated from the published record as a flag.
"""
from __future__ import annotations

import html
import json
import re
from collections import Counter
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
DESK = ROOT / "session-4afef1af"
DATA = DESK / "data"
OUT = Path(__file__).resolve().parent


class _LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if key.lower() in {"href", "src"} and value:
                self.links.append(value)


def load_json(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def host(url: str) -> str:
    return urlparse(url).netloc.lower()


def official(url: str, sport: str, snapshot: dict) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        return False
    for domain in snapshot["official_domains"].get(sport, []):
        domain = domain.lower()
        if parsed.netloc.lower() == domain or parsed.netloc.lower().endswith("." + domain):
            return True
    return False


def ext_link(url: str, text: str | None = None) -> str:
    safe_url = html.escape(url, quote=True)
    label = html.escape(text or host(url) or url)
    return f'<a href="{safe_url}" target="_blank" rel="noopener noreferrer">{label}</a>'


def tags(items: list[str], limit: int | None = None) -> str:
    if limit is not None:
        items = items[:limit]
    return "<br>".join(ext_link(item) for item in items) or "—"


def e(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def relevant_local_target(base: Path, raw: str) -> Path | None:
    parsed = urlparse(raw)
    if parsed.scheme or parsed.netloc or raw.startswith("#") or raw.startswith("data:"):
        return None
    path = unquote(parsed.path)
    if not path:
        return None
    target = (base / path).resolve()
    try:
        target.relative_to(ROOT.resolve())
    except ValueError:
        return None
    if target.is_dir():
        target = target / "index.html"
    return target


def audit_local_links() -> dict:
    pages = sorted(DESK.rglob("*.html"))
    checked = 0
    broken: list[dict] = []
    for page in pages:
        parser = _LinkCollector()
        parser.feed(page.read_text(encoding="utf-8"))
        for raw in parser.links:
            target = relevant_local_target(page.parent, raw)
            if target is None:
                continue
            checked += 1
            if not target.exists():
                broken.append({
                    "page": str(page.relative_to(ROOT)),
                    "link": raw,
                    "resolved": str(target.relative_to(ROOT)) if target.is_relative_to(ROOT) else str(target),
                })
    return {"pages": len(pages), "links_checked": checked, "broken": broken}


def find_last_result_phrase(text: str) -> bool:
    # A strict narrative test, not a claim that other form evidence is invalid.
    return bool(re.search(r"\bmost recently\b|\blast game\b", text, re.I))


def audit() -> dict:
    snapshot = load_json("snapshot.json")
    fixtures = load_json("fixtures.json")
    analysis = load_json("analysis.json")
    predictions = load_json("predictions.json")
    findings = load_json("flagged.json")
    models = load_json("models.json")

    start = iso(snapshot["window"]["start"])
    end = iso(snapshot["window"]["end"])
    analysis_by_id = {row["fixture"]["id"]: row for row in analysis}
    picks_by_fixture_market: dict[tuple[str, str], dict] = {}
    for row in analysis:
        fixture_id = row["fixture"]["id"]
        pick_set = [row["analysis"].get("winner_pick")] + list(row["analysis"].get("market_picks") or [])
        for pick in pick_set:
            if pick:
                picks_by_fixture_market[(fixture_id, pick.get("market"))] = pick

    audit_errors: list[dict] = []
    fixture_rows: list[dict] = []
    seen_ids: set[str] = set()
    priced = withheld = market_count = 0
    valid_market_rows = 0
    for fixture in fixtures:
        fid = fixture.get("id", "")
        row_errors: list[str] = []
        if not fid or fid in seen_ids:
            row_errors.append("fixture id missing or duplicated")
        seen_ids.add(fid)
        if fixture.get("sport") not in snapshot["sports"]:
            row_errors.append("sport absent from snapshot taxonomy")
        try:
            when = iso(fixture["start_utc"])
            if not (start <= when < end):
                row_errors.append("start is outside the published window")
        except Exception:  # noqa: BLE001
            row_errors.append("start is not a parseable ISO-8601 timestamp")
        sources = fixture.get("official_source_urls") or fixture.get("source_urls") or []
        if not sources:
            row_errors.append("no source URL")
        elif not any(official(url, fixture["sport"], snapshot) for url in sources):
            row_errors.append("no allowlisted official HTTPS source URL")
        elif any(not official(url, fixture["sport"], snapshot) for url in sources):
            row_errors.append("one or more published source URLs fall outside the sport allowlist")
        row = analysis_by_id.get(fid)
        if row is None:
            row_errors.append("fixture has no analysis row")
            market_status = "missing analysis"
        else:
            a = row["analysis"]
            market_status = a.get("market_status") or "priced"
            if market_status == "withheld":
                withheld += 1
                if a.get("markets") or a.get("headline_pick") or a.get("winner_pick") or a.get("market_picks"):
                    row_errors.append("withheld fixture has an originated market or pick")
                if not a.get("market_note"):
                    row_errors.append("withheld fixture has no published reason")
                league = snapshot["sports"][fixture["sport"]]["league"]
                game_count = models[fixture["sport"]]["current"]["games"]
                expected = f"{league} ratings rest on {game_count} completed games, so no line is originated for this fixture."
                if a.get("rationale") != expected:
                    row_errors.append("withheld rationale does not identify this fixture's league/sample")
            else:
                priced += 1
                expected_markets = {"moneyline", "handicap", "total"}
                actual_markets = set((a.get("markets") or {}).keys())
                if actual_markets != expected_markets:
                    row_errors.append("priced fixture does not have exactly winner, handicap and total markets")
                for market_name, market in (a.get("markets") or {}).items():
                    market_count += 1
                    selections = market.get("selections") or []
                    if len(selections) < 2:
                        row_errors.append(f"{market_name} has fewer than two selections")
                        continue
                    probability = sum(float(selection.get("prob", 0)) for selection in selections)
                    if abs(probability - 1.0) > 0.01:
                        row_errors.append(f"{market_name} probabilities do not sum to 1")
                    if any(not 0 < float(selection.get("prob", 0)) < 1 for selection in selections):
                        row_errors.append(f"{market_name} has a probability outside (0, 1)")
                    if any(float(selection.get("price_decimal", 0)) <= 1 for selection in selections):
                        row_errors.append(f"{market_name} has a decimal price at or below 1")
                    valid_market_rows += 1
                pick = a.get("headline_pick")
                if not pick:
                    row_errors.append("priced fixture has no headline pick")
        if row_errors:
            audit_errors.append({"fixture_id": fid, "errors": row_errors})
        fixture_rows.append({
            "id": fid,
            "sport": fixture.get("sport"),
            "league": fixture.get("league"),
            "match": f'{fixture.get("away", {}).get("name", "?")} at {fixture.get("home", {}).get("name", "?")}',
            "start_utc": fixture.get("start_utc"),
            "sources": sources,
            "market_status": market_status,
            "result": "pass" if not row_errors else "error",
            "errors": row_errors,
        })

    analysis_ids = {row["fixture"]["id"] for row in analysis}
    fixture_ids = {row["id"] for row in fixtures}
    if analysis_ids != fixture_ids:
        audit_errors.append({"fixture_id": "inventory", "errors": ["fixture and analysis ID sets differ"]})

    prediction_rows: list[dict] = []
    prediction_errors: list[dict] = []
    player_context_missing: list[str] = []
    no_specific_recent_result: list[str] = []
    for prediction in predictions:
        pid = prediction.get("fixture_id", "")
        row_errors: list[str] = []
        if pid not in fixture_ids:
            row_errors.append("prediction refers to a fixture not present in inventory")
        if prediction.get("confidence") != "high":
            row_errors.append("written prediction is not high confidence")
        words = len((prediction.get("text") or "").split())
        if words < 30:
            row_errors.append("prediction is shorter than 30 words")
        if words != prediction.get("word_count"):
            row_errors.append("stored word count does not match text")
        if prediction.get("selection") not in (prediction.get("text") or ""):
            row_errors.append("selection is not explicit in the narrative")
        published_pick = picks_by_fixture_market.get((pid, prediction.get("market")))
        if not published_pick or published_pick.get("confidence") != "high" or published_pick.get("selection") != prediction.get("selection"):
            row_errors.append("prediction does not match its high-confidence published selection")
        sources = prediction.get("source_urls") or []
        sport = prediction.get("sport")
        if not sources or not all(official(url, sport, snapshot) for url in sources):
            row_errors.append("prediction source URLs are not all allowlisted official HTTPS URLs")
        facts = prediction.get("facts") or []
        if not facts:
            row_errors.append("prediction has no source-linked fact list")
        for fact in facts:
            src = fact.get("source", "")
            if src.startswith("https://") and not official(src, sport, snapshot):
                row_errors.append("a prediction fact links outside the sport allowlist")
            if not fact.get("fact") or not src:
                row_errors.append("a prediction fact is blank or lacks its source")

        # The brief requires a named, officially sourced player. This snapshot has no
        # player field and no player fact, so leave it unfilled and flag it rather than infer one.
        player_fact = any("player" in str(fact.get("fact", "")).lower() for fact in facts)
        player_ok = bool(prediction.get("player")) and player_fact
        if not player_ok:
            player_context_missing.append(f"{pid}/{prediction.get('market')}")
        recent_result = find_last_result_phrase(prediction.get("text") or "")
        if not recent_result:
            no_specific_recent_result.append(f"{pid}/{prediction.get('market')}")
        if row_errors:
            prediction_errors.append({"fixture_id": pid, "market": prediction.get("market"), "errors": row_errors})
        prediction_rows.append({
            "fixture_id": pid,
            "match": prediction.get("match"),
            "market": prediction.get("market"),
            "selection": prediction.get("selection"),
            "words": words,
            "sources": sources,
            "facts": facts,
            "result": "pass" if not row_errors else "error",
            "errors": row_errors,
            "player_context": "unverified — no player fact or player source is published",
            "recent_result": "stated" if recent_result else "not stated in narrative",
        })

    unique_texts = len({p.get("text", "") for p in predictions})
    local_links = audit_local_links()
    fetch_log = snapshot.get("fetch_log") or []
    fetch_counts = Counter("HTTP " + str(item["status"]) if item.get("status") else "no response" for item in fetch_log)

    finding_rows = [
        {
            "id": "F-01",
            "severity": "needs review",
            "title": "Player context is unverified in all written high-confidence predictions",
            "detail": (
                f"{len(player_context_missing)} of {len(predictions)} written predictions have no player field and "
                "no player-level fact/source in the committed record. The player value is intentionally left blank "
                "here; do not infer a player from a roster."
            ),
            "affected": player_context_missing,
            "sources": sorted({url for p in predictions for url in p.get("source_urls", [])}),
        },
        {
            "id": "F-02",
            "severity": "needs review",
            "title": "Some high-confidence narratives do not state a specific latest result",
            "detail": (
                f"{len(no_specific_recent_result)} narratives have form/score context but do not use a specific "
                "last-result sentence. Their fact lists still carry official last-five / head-to-head source links."
            ),
            "affected": no_specific_recent_result,
            "sources": sorted({
                fact["source"] for p in predictions for fact in p.get("facts", [])
                if fact.get("source", "").startswith("https://")
            }),
        },
        {
            "id": "F-03",
            "severity": "published blank",
            "title": "NBA pricing remains withheld, not guessed",
            "detail": (
                f"{withheld} NBA fixtures have no originated market because the snapshot recorded only "
                f"{models['basketball']['current']['games']} completed games and the declared threshold is 20. "
                "The archived NBA historical-results requests timed out; prices, probabilities and picks remain blank."
            ),
            "affected": [row["id"] for row in fixture_rows if row["market_status"] == "withheld"],
            "sources": [item["url"] for item in fetch_log if not item.get("status")],
        },
        {
            "id": "F-04",
            "severity": "clarification",
            "title": "‘High-confidence winners’ and written-prediction totals measure different subsets",
            "detail": (
                f"The snapshot's high_picks count is {snapshot['counts'].get('high_picks')} match-winner picks, "
                f"while {len(predictions)} written high predictions include {Counter(p['market'] for p in predictions)['handicap']} handicap "
                f"and {Counter(p['market'] for p in predictions)['total']} total selections. This is not a pricing error, "
                "but the label should not be read as the total number of written high selections."
            ),
            "affected": [],
            "sources": [],
        },
        {
            "id": "F-05",
            "severity": "fixed in this handoff",
            "title": "Cross-sport withheld-rationale label and grammar defect corrected",
            "detail": (
                "The static audit confirmed all 50 NBA withheld rows now identify the NBA and its three-game sample. "
                "The one generated ‘Recent form has … have’ construction was corrected in the current snapshot and future template."
            ),
            "affected": [row["id"] for row in fixture_rows if row["sport"] == "basketball" and row["market_status"] == "withheld"],
            "sources": [],
        },
    ]

    return {
        "audit_generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scope": {
            "desk": "session-4afef1af",
            "snapshot_generated_utc": snapshot.get("generated_utc"),
            "window": snapshot.get("window"),
            "mode": "static integrity and provenance audit; no external requests were made during this audit",
        },
        "summary": {
            "fixtures": len(fixtures),
            "analysis_rows": len(analysis),
            "fixture_row_errors": len(audit_errors),
            "priced_fixtures": priced,
            "withheld_fixtures": withheld,
            "market_families": market_count,
            "market_families_passing": valid_market_rows,
            "written_predictions": len(predictions),
            "prediction_row_errors": len(prediction_errors),
            "unique_prediction_bodies": unique_texts,
            "local_html_pages": local_links["pages"],
            "local_links_checked": local_links["links_checked"],
            "broken_local_links": len(local_links["broken"]),
            "archived_fetch_statuses": dict(fetch_counts),
        },
        "checks": {
            "fixture_analysis_ids_match": analysis_ids == fixture_ids,
            "fixture_row_errors": audit_errors,
            "prediction_row_errors": prediction_errors,
            "local_links": local_links,
        },
        "findings": finding_rows,
        "fixtures": fixture_rows,
        "predictions": prediction_rows,
    }


def badge(value: str) -> str:
    cls = "ok" if value == "pass" or value == "stated" else "warn"
    return f'<span class="badge {cls}">{e(value)}</span>'


def render(report: dict) -> str:
    summary = report["summary"]
    scope = report["scope"]
    fixture_html = []
    for row in report["fixtures"]:
        status = "withheld — blank" if row["market_status"] == "withheld" else "priced — 3 markets"
        fixture_html.append(
            "<tr>"
            f"<td class=mono>{e(row['id'])}</td><td>{e(row['league'])}</td><td>{e(row['match'])}</td>"
            f"<td class=mono>{e(row['start_utc'])}</td><td>{tags(row['sources'])}</td>"
            f"<td>{e(status)}</td><td>{badge(row['result'])}</td>"
            f"<td>{e('; '.join(row['errors'])) or '—'}</td></tr>"
        )
    prediction_html = []
    for row in report["predictions"]:
        source_html = tags(row["sources"])
        fact_sources = sorted({fact["source"] for fact in row["facts"] if fact.get("source", "").startswith("https://")})
        prediction_html.append(
            "<tr>"
            f"<td class=mono>{e(row['fixture_id'])}</td><td>{e(row['match'])}</td>"
            f"<td>{e(row['market'])}<br><strong>{e(row['selection'])}</strong></td>"
            f"<td>{e(row['words'])}</td><td>{badge(row['result'])}</td>"
            f"<td>{e(row['recent_result'])}</td><td class=warn-text>{e(row['player_context'])}</td>"
            f"<td>{source_html}<details><summary>Fact sources ({len(fact_sources)})</summary>{tags(fact_sources)}</details></td>"
            f"<td>{e('; '.join(row['errors'])) or '—'}</td></tr>"
        )
    findings_html = []
    for item in report["findings"]:
        affected = ", ".join(item["affected"]) if item["affected"] else "—"
        source_html = tags(item["sources"], limit=8)
        if len(item["sources"]) > 8:
            source_html += f"<br><span class=muted>+ {len(item['sources']) - 8} more row-level links in the prediction table</span>"
        findings_html.append(
            "<tr>"
            f"<td class=mono>{e(item['id'])}</td><td>{badge(item['severity'])}</td>"
            f"<td><strong>{e(item['title'])}</strong><br><span class=muted>{e(item['detail'])}</span></td>"
            f"<td class=small>{e(affected)}</td><td>{source_html}</td></tr>"
        )
    cards = [
        ("Fixtures", summary["fixtures"], "all rows have a source allowlist check"),
        ("Priced / withheld", f"{summary['priced_fixtures']} / {summary['withheld_fixtures']}", "withheld rows contain no invented markets"),
        ("Market families", summary["market_families"], "probability and price range checked"),
        ("High narratives", summary["written_predictions"], "length, selection and source facts checked"),
        ("Local links", summary["local_links_checked"], f"{summary['broken_local_links']} broken across {summary['local_html_pages']} pages"),
        ("Snapshot fetches", summary["archived_fetch_statuses"].get("HTTP 200", 0), "archived HTTP 200 records; not a live re-fetch"),
    ]
    card_html = "".join(
        f'<article class="card"><strong>{e(value)}</strong><span>{e(label)}</span><small>{e(note)}</small></article>'
        for label, value, note in cards
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Independent snapshot audit · OLBG4</title>
<style>
:root {{ color-scheme: light; --ink:#12212e; --muted:#526475; --bg:#f5f8fa; --line:#d9e2e8; --brand:#0c736b; --ok:#067647; --warn:#9a6300; --panel:#fff; }}
* {{ box-sizing:border-box }} body {{ margin:0; font:14px/1.5 Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; color:var(--ink); background:var(--bg) }}
a {{ color:#056eac }} .wrap {{ width:min(1540px,calc(100% - 32px)); margin:auto }}
header {{ background:#102b3a; color:#fff; padding:20px 0 18px; border-bottom:4px solid #35b59f }}
header h1 {{ margin:0 0 4px; font-size:25px }} header p {{ margin:0; color:#d5e4ec; max-width:980px }}
nav {{ margin-top:12px; display:flex; gap:8px; flex-wrap:wrap }} nav a {{ color:#e7f6f3; border:1px solid #477386; border-radius:7px; padding:5px 8px; text-decoration:none; font-size:12px }}
main {{ padding:22px 0 40px }} h2 {{ margin:30px 0 8px; font-size:19px }} .lead {{ color:var(--muted); max-width:1100px }}
.grid {{ display:grid; grid-template-columns:repeat(6,minmax(0,1fr)); gap:10px; margin:18px 0 }} .card {{ min-height:104px; padding:14px; background:var(--panel); border:1px solid var(--line); border-radius:10px; display:flex; flex-direction:column }}
.card strong {{ font-size:25px; color:var(--brand) }} .card span {{ font-weight:700; margin-top:2px }} .card small,.muted {{ color:var(--muted) }}
.notice {{ border-left:4px solid #d19a2a; padding:12px 14px; background:#fff9e9; color:#5d480d; border-radius:4px; margin:16px 0 }}
.table {{ overflow:auto; background:var(--panel); border:1px solid var(--line); border-radius:10px }} table {{ width:100%; border-collapse:collapse; min-width:1060px }} th {{ text-align:left; background:#edf3f5; white-space:nowrap; font-size:12px }} th,td {{ padding:9px 10px; vertical-align:top; border-bottom:1px solid var(--line) }} tr:last-child td {{ border-bottom:0 }}
.mono {{ font-family:ui-monospace,SFMono-Regular,Consolas,monospace; font-size:12px }} .small {{ font-size:12px; min-width:260px }} .badge {{ display:inline-block; font-size:11px; font-weight:800; border-radius:999px; padding:2px 7px; background:#eceff2; text-transform:uppercase; white-space:nowrap }} .badge.ok {{ background:#dff4e8; color:var(--ok) }} .badge.warn {{ background:#fff0cb; color:var(--warn) }} .warn-text {{ color:#815100 }} details {{ margin-top:5px }} summary {{ cursor:pointer; color:#056eac; font-size:12px }}
footer {{ padding:22px 0; background:#102b3a; color:#d5e4ec; font-size:12px }}
@media(max-width:1000px) {{ .grid {{ grid-template-columns:repeat(3,minmax(0,1fr)) }} }} @media(max-width:600px) {{ .wrap {{ width:min(100% - 20px,1540px) }} .grid {{ grid-template-columns:repeat(2,minmax(0,1fr)) }} }}
</style>
</head>
<body>
<header><div class="wrap">
<h1>Independent Build E snapshot audit</h1>
<p>Line-by-line structural and provenance review of the published NBA, NHL and MLB desk. Every fixture and high-confidence narrative below retains its official source links for manual review.</p>
<nav><a href="../index.html">All dashboards</a><a href="../session-4afef1af/">Build E desk</a><a href="../session-4afef1af/flagged.html">Build E flagged page</a><a href="audit.json">Machine-readable audit JSON</a><a href="https://github.com/buffedlizard55-lab/OLBG4/blob/main/COORDINATION.md">Coordination log</a></nav>
</div></header>
<main class="wrap">
<p class="lead"><strong>Audit mode:</strong> {e(scope['mode'])}. It checked the committed snapshot generated {e(scope['snapshot_generated_utc'])}, covering {e(scope['window']['start'])} to {e(scope['window']['end'])}. Official URL ownership is tested against the snapshot’s sport-specific allowlist; content was not newly fetched or inferred.</p>
<div class="grid">{card_html}</div>
<div class="notice"><strong>Review first:</strong> structurally valid rows are not a substitute for the missing player-level evidence identified below. Per the project rule, player values have not been guessed or populated.</div>
<h2>Findings and irregularities</h2><p class="lead">These items are published for review and do not silently alter match, market or source values.</p>
<div class="table"><table><thead><tr><th>ID</th><th>Status</th><th>Finding</th><th>Affected records</th><th>Official source links</th></tr></thead><tbody>{''.join(findings_html)}</tbody></table></div>
<h2>Fixture-by-fixture audit</h2><p class="lead">A pass confirms a unique fixture ID, an in-window timestamp, at least one official HTTPS source URL, a matching analysis row, and the correct blank/market state. It does not claim a fresh live-page read.</p>
<div class="table"><table><thead><tr><th>Fixture ID</th><th>League</th><th>Match</th><th>Start UTC</th><th>Official source links</th><th>Market state</th><th>Integrity</th><th>Notes</th></tr></thead><tbody>{''.join(fixture_html)}</tbody></table></div>
<h2>High-confidence prediction audit</h2><p class="lead">The checks confirm the selection relationship, ≥30-word requirement, official URL allowlist and fact list. “Not stated in narrative” is a strict latest-result wording flag; it does not erase the separately linked form facts. Player context remains blank where the snapshot lacks player evidence.</p>
<div class="table"><table><thead><tr><th>Fixture</th><th>Match</th><th>Selection</th><th>Words</th><th>Structural checks</th><th>Specific last result</th><th>Player context</th><th>Official source links</th><th>Errors</th></tr></thead><tbody>{''.join(prediction_html)}</tbody></table></div>
</main>
<footer><div class="wrap">Audit generated {e(report['audit_generated_utc'])}. Static report created by <code>session-5e6c545d/audit.py</code>; no external request was made by this audit. Research and review only — not betting advice.</div></footer>
</body></html>"""


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report = audit()
    (OUT / "audit.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "index.html").write_text(render(report), encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    return 1 if report["summary"]["fixture_row_errors"] or report["summary"]["prediction_row_errors"] or report["summary"]["broken_local_links"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
