#!/usr/bin/env python3
"""Render the isolated QF acceptance dashboard from its generated audit JSON."""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "session-51fff5fb" / "audit.json"
SITE = ROOT / "session-51fff5fb"

CSS = r"""
:root{--ink:#172033;--muted:#5d6b82;--paper:#f4f7fb;--panel:#fff;--line:#dce4ef;--navy:#132238;--blue:#165dcc;--teal:#087f72;--red:#a92c3b;--amber:#8a5a00;--green:#08714c;--shadow:0 12px 30px rgba(24,42,69,.08)}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.55 Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif}a{color:var(--blue);text-decoration:none}a:hover{text-decoration:underline}.wrap{max-width:1240px;margin:auto;padding:0 22px}
header{background:var(--navy);color:#fff;border-bottom:1px solid #263c59;position:sticky;top:0;z-index:10}.nav{display:flex;align-items:center;gap:14px;flex-wrap:wrap;padding:12px 0}.brand{color:#fff;font-weight:800;letter-spacing:.02em;display:flex;align-items:center;gap:9px;margin-right:10px}.mark{display:grid;place-items:center;width:32px;height:32px;border-radius:9px;background:#55d3b0;color:#0b2631;font-size:12px}.nav a.item{color:#c6d2e3;font-size:14px;font-weight:650;padding:7px 4px;border-bottom:2px solid transparent}.nav a.item.active,.nav a.item:hover{color:#fff;border-bottom-color:#55d3b0;text-decoration:none}.nav .spacer{flex:1}.stamp{font-size:12px;color:#b6c4d8}
main{padding:28px 0 64px}h1{font-size:clamp(28px,4vw,44px);line-height:1.12;letter-spacing:-.035em;margin:0 0 12px}h2{font-size:23px;letter-spacing:-.02em;margin:34px 0 12px}h3{font-size:17px;margin:0 0 8px}.lede{font-size:18px;color:var(--muted);max-width:82ch;margin:0 0 18px}.eyebrow{font-size:11px;font-weight:850;text-transform:uppercase;letter-spacing:.11em;color:var(--teal)}
.hero{background:linear-gradient(125deg,#fff,#e7f6f2);border:1px solid #d2e9e3;border-radius:20px;padding:25px 26px;box-shadow:var(--shadow)}.hero p:last-child{margin-bottom:0}.callout{padding:14px 16px;border-radius:12px;background:#fff8e9;border:1px solid #f0d99b;border-left:4px solid #d89921;color:#5d4615;margin:16px 0}.callout.critical{background:#fff0f1;border-color:#f1c7cb;border-left-color:var(--red);color:#6c222d}.callout.good{background:#edfbf5;border-color:#c7e9d8;border-left-color:var(--green);color:#20583f}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:12px;margin:18px 0}.kpi{background:var(--panel);border:1px solid var(--line);border-radius:15px;padding:15px 16px;box-shadow:var(--shadow)}.kpi .n{font-size:27px;font-weight:850;letter-spacing:-.04em}.kpi .l{font-size:11px;color:var(--muted);text-transform:uppercase;font-weight:800;letter-spacing:.08em}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:15px}.card{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:18px;box-shadow:var(--shadow)}.card.green{border-top:4px solid var(--green)}.card.red{border-top:4px solid var(--red)}.card.amber{border-top:4px solid #d89921}.card .sport{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.09em;font-weight:800}.match{font-size:19px;font-weight:850;line-height:1.25;margin:5px 0}.meta{color:var(--muted);font-size:13px}.selection{background:#f0f5fc;border:1px solid #dce7f6;border-radius:11px;padding:11px 13px;margin:12px 0}.selection .label{display:block;font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.1em;font-weight:850}.selection strong{font-size:17px}.price{font-size:15px;font-weight:800;margin-top:5px}.prediction{color:#34425a;font-size:14px;border-left:3px solid #bdd2ed;padding-left:12px;margin:12px 0}.sources{display:flex;gap:9px;flex-wrap:wrap;margin-top:12px;font-size:13px}.sources a,.button{display:inline-flex;align-items:center;gap:5px;background:#edf4ff;border:1px solid #d0def2;border-radius:999px;padding:6px 11px;font-weight:750}.button.primary{background:var(--navy);border-color:var(--navy);color:#fff}.button.green{background:#e7f8f0;border-color:#bde5d0;color:#15583c}.buttonrow{display:flex;gap:9px;flex-wrap:wrap;margin:14px 0}.badge{display:inline-block;border-radius:999px;padding:3px 8px;font-size:10px;font-weight:900;letter-spacing:.08em;text-transform:uppercase}.badge.high{color:#095f41;background:#def7eb;border:1px solid #b8e9d1}.badge.medium{color:#785100;background:#fff4d9;border:1px solid #f0dca3}.badge.low{color:#58657a;background:#edf0f5;border:1px solid #dce1e8}.badge.flag{color:#8e2632;background:#ffeaec;border:1px solid #efc4c9}.badge.neutral{color:#304762;background:#edf4fc;border:1px solid #d8e3f1}
.tablewrap{overflow:auto;border:1px solid var(--line);border-radius:14px;background:#fff;box-shadow:var(--shadow)}table{border-collapse:collapse;width:100%;min-width:800px;font-size:13px}th,td{text-align:left;vertical-align:top;padding:10px 11px;border-bottom:1px solid var(--line)}th{background:#f0f4f9;color:#4f6078;font-size:10px;text-transform:uppercase;letter-spacing:.08em;position:sticky;top:58px;z-index:1}tbody tr:last-child td{border-bottom:0}tbody tr:hover{background:#f8fbff}.mono{font-variant-numeric:tabular-nums;white-space:nowrap}.muted{color:var(--muted)}.small{font-size:12px}.nowrap{white-space:nowrap}.missing{color:#7b8595;font-style:italic}.detail{margin:15px 0;border:1px solid var(--line);border-radius:13px;background:#fff;box-shadow:var(--shadow)}.detail summary{cursor:pointer;padding:14px 16px;font-weight:800}.detail .inside{padding:0 16px 16px}.metricline{display:flex;gap:10px;flex-wrap:wrap;margin:11px 0}.metricline span{background:#f0f4f9;border-radius:8px;padding:5px 8px;font-size:12px}.gaplist{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}.gap{background:#fff;border:1px solid var(--line);border-radius:13px;padding:14px}.gap p{margin:6px 0;font-size:13px;color:#4e5c70}.progress{height:7px;background:#e8edf4;border-radius:999px;overflow:hidden;margin-top:8px}.progress span{display:block;height:100%;background:var(--teal)}footer{border-top:1px solid var(--line);padding:25px 0 42px;color:var(--muted);font-size:12px}.right{float:right}
@media(max-width:680px){.wrap{padding:0 14px}.nav{gap:8px}.nav .spacer{display:none}.stamp{width:100%}main{padding-top:18px}.hero{padding:19px}.kpi .n{font-size:23px}th{position:static}.right{float:none;display:block;margin-top:6px}}
"""


def e(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def read_audit() -> dict:
    with DATA.open(encoding="utf-8") as f:
        return json.load(f)


def pct(value, digits: int = 1) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value) * 100:.{digits}f}%"
    except (TypeError, ValueError):
        return "—"


def odds(value) -> str:
    if value is None or value == "":
        return "—"
    try:
        value = int(value)
    except (TypeError, ValueError):
        return "—"
    return f"+{value:,}" if value > 0 else f"{value:,}"


def link(url: str, label: str, cls: str = "") -> str:
    if not url:
        return '<span class="missing">not supplied</span>'
    class_attr = f' class="{e(cls)}"' if cls else ""
    return f'<a{class_attr} href="{e(url)}" target="_blank" rel="noopener noreferrer">{e(label)}</a>'


def source_links(item: dict) -> str:
    parts = []
    official_url = item.get("official_source_url") or item.get("source_url") or ""
    official_name = item.get("official_source_name") or item.get("source_name") or "Official source"
    if official_url:
        parts.append(link(official_url, official_name))
    else:
        parts.append('<span class="missing">official source not supplied</span>')
    event_url = item.get("olbg_event_url") or ""
    if event_url:
        parts.append(link(event_url, "OLBG event"))
    else:
        parts.append('<span class="missing">OLBG event not cross-referenced</span>')
    return '<div class="sources">' + "".join(parts) + "</div>"


def primary_source_cell(item: dict) -> str:
    url = item.get("official_source_url") or item.get("source_url") or ""
    name = item.get("official_source_name") or item.get("source_name") or "Official source"
    if not url:
        return '<span class="missing">not captured — flagged</span>'
    return link(url, name)


def shell(title: str, active: str, content: str, audit: dict) -> str:
    pages = [
        ("index.html", "Executive QA"),
        ("picks.html", "Pick shortlist"),
        ("coverage.html", "Sports"),
        ("flagged.html", "Flagged for review"),
        ("sources.html", "Sources"),
    ]
    nav = "".join(
        f'<a class="item{" active" if href == active else ""}" href="{href}">{e(label)}</a>'
        for href, label in pages
    )
    stamp = audit.get("capture", {}).get("captured_utc", "")
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} · OLBG4 research desk</title>
<meta name="description" content="Independent acceptance audit of the OLBG4 multi-sport picks and source coverage.">
<link rel="stylesheet" href="style.css"></head><body>
<header><div class="wrap nav"><a class="brand" href="index.html"><span class="mark">QF</span>Research check</a>{nav}<span class="spacer"></span><span class="stamp">Capture: {e(stamp)} · snapshot, not live</span></div></header>
<main><div class="wrap">{content}</div></main>
<footer><div class="wrap">Independent review of committed source captures. No live refresh is implied. <span class="right"><a href="../index.html">Main OLBG4 dashboard</a></span></div></footer>
</body></html>'''


def kpi(number, label):
    return f'<div class="kpi"><div class="n">{e(number)}</div><div class="l">{e(label)}</div></div>'


def finding_cards(audit: dict) -> str:
    out = []
    for item in audit.get("findings", []):
        sev = item.get("severity", "medium")
        title_id = f'<span class="badge {"flag" if sev == "high" else "medium"}">{e(item.get("id"))} · {e(sev)}</span>'
        out.append(f'<article class="card {"red" if sev == "high" else "amber"}">{title_id}<h3 style="margin-top:9px">{e(item.get("title"))}</h3><p class="small">{e(item.get("summary"))}</p></article>')
    return '<div class="cards">' + "".join(out) + "</div>"


def pick_card(item: dict, research_incomplete: bool = True) -> str:
    has_text = bool(item.get("prediction_text"))
    badge = '<span class="badge high">High</span>'
    note = ""
    if research_incomplete:
        gaps = []
        if not item.get("injury_input_present"):
            gaps.append("injury / availability status not captured")
        if not item.get("match_by_match_history_present"):
            gaps.append("recent match-by-match results not captured")
        if item.get("prediction_statistic_wording_issue"):
            gaps.append("league scoring-rate wording needs correction (see QF-F11)")
        if not item.get("venue"):
            gaps.append("venue not supplied")
        if not item.get("has_olbg_event"):
            gaps.append("OLBG event not cross-referenced")
        if gaps:
            note = '<div class="callout">Research gaps: ' + e("; ".join(gaps)) + '. Blank means unknown, not a negative report.</div>'
    if not has_text:
        note = '<div class="callout critical">No written prediction is present. This row is not promoted as a complete pick.</div>'
    prediction = f'<p class="prediction">{e(item.get("prediction_text"))}</p>' if has_text else ""
    return f'''<article class="card green">
<div class="sport">{e(item.get("sport"))} · {e(item.get("competition"))}</div>
<div class="match">{e(item.get("match"))}</div>
<div class="meta">{e(item.get("start_utc"))} UTC {badge}</div>
<div class="selection"><span class="label">Selection · {e(item.get("market"))}</span><strong>{e(item.get("selection"))}</strong>
<div class="price">Fair price {e(odds(item.get("fair_american")))} American / {e(item.get("fair_decimal"))} decimal · {e(pct(item.get("fair_probability"), 2))}</div></div>
{prediction}{note}{source_links(item)}
</article>'''


def high_row_table(rows: list[dict], empty_message: str = "No rows.") -> str:
    if not rows:
        return f'<p class="muted">{e(empty_message)}</p>'
    body = []
    for r in rows:
        source = primary_source_cell(r)
        olbg = link(r.get("olbg_event_url", ""), "Event") if r.get("olbg_event_url") else '<span class="missing">not linked</span>'
        pred_badge = '<span class="badge high">write-up</span>' if r.get("has_written_prediction") else '<span class="badge flag">missing</span>'
        window_badge = '<span class="badge high">in range</span>' if r.get("inside_american_price_focus") else '<span class="badge flag">out of range</span>'
        body.append(f'''<tr>
<td class="mono">{e(r.get("start_utc"))}</td><td><strong>{e(r.get("sport"))}</strong><br>{e(r.get("match"))}</td>
<td><strong>{e(r.get("selection"))}</strong><br><span class="muted">{e(r.get("market"))}</span></td>
<td class="mono">{e(pct(r.get("fair_probability"),2))}<br>{e(odds(r.get("fair_american")))}</td>
<td>{window_badge}</td><td>{pred_badge}</td><td>{olbg}</td><td>{source}</td></tr>''')
    return '<div class="tablewrap"><table><thead><tr><th>Start UTC</th><th>Sport / match</th><th>Selection / market</th><th>Probability / fair price</th><th>−250…+10,000</th><th>Written copy</th><th>OLBG event</th><th>Official source</th></tr></thead><tbody>' + "".join(body) + '</tbody></table></div>'


def general_rows_table(rows: list[dict], columns: list[tuple[str, str]]) -> str:
    if not rows:
        return '<p class="muted">No records in this category.</p>'
    head = ''.join(f'<th>{e(label)}</th>' for _, label in columns)
    body = []
    for r in rows:
        cells = []
        for key, label in columns:
            if key == "official_source":
                cells.append(f'<td>{primary_source_cell(r)}</td>')
            elif key == "olbg_event":
                event_cell = link(r.get("olbg_event_url", ""), "OLBG event") if r.get("olbg_event_url") else '<span class="missing">not cross-referenced</span>'
                cells.append(f'<td>{event_cell}</td>')
            elif key == "price":
                cells.append(f'<td class="mono">{e(odds(r.get("fair_american")))}</td>')
            elif key == "probability":
                cells.append(f'<td class="mono">{e(pct(r.get("fair_probability"),2))}</td>')
            elif key == "flags":
                value = '; '.join(r.get("flags", []))
                content = e(value) if value else '<span class="missing">none listed</span>'
                cells.append(f'<td class="small">{content}</td>')
            elif key == "started":
                cells.append(f'<td class="mono">{e(r.get("start_utc"))}</td>')
            else:
                value = r.get(key, "")
                content = e(value) if value not in (None, "") else '<span class="missing">not supplied</span>'
                cells.append(f'<td>{content}</td>')
        body.append('<tr>' + ''.join(cells) + '</tr>')
    return f'<div class="tablewrap"><table><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'


def page_index(a: dict) -> str:
    s = a["summary"]
    candidates = a.get("numeric_high_candidates", [])
    promoted = [x for x in candidates if x.get("has_written_prediction") and x.get("olbg_event_url") and x.get("starts_after_capture")]
    incomplete_candidates = [x for x in candidates if x not in promoted]
    full_count = sum(bool(x.get("injury_input_present")) and bool(x.get("match_by_match_history_present")) and not bool(x.get("prediction_statistic_wording_issue")) and bool(x.get("has_written_prediction")) and bool(x.get("olbg_event_url")) and bool(x.get("starts_after_capture")) for x in candidates)
    stamp = a["capture"].get("captured_utc", "")
    cards = ''.join(pick_card(x) for x in promoted)
    if not cards:
        cards = '<div class="callout critical">No complete, source-linked pick meets the stated filters in this snapshot.</div>'
    incomplete = ''
    if incomplete_candidates:
        incomplete += '<h3>Other numeric matches needing review</h3>'
        incomplete += high_row_table(incomplete_candidates, "No other numeric matches.")
    root = a.get("root_summary_check", {})
    root_note = ""
    if root.get("available") and not root.get("first_card_is_earliest_written_prediction"):
        first = root.get("first_displayed_card", {})
        earliest = root.get("earliest_future_written_prediction", {})
        root_note = f'''<div class="callout"><strong>Navigation clarity flag.</strong> The root page's “Next up” first card is {e(first.get("match"))} ({e(first.get("date_label"))}), while the earliest written fixture in the same snapshot is {e(earliest.get("match"))} ({e(earliest.get("start_utc"))}). The cards appear confidence-ranked. Consider labeling the sort or showing a separate chronological next-match row. {link(first.get("official_source_url", ""), "First card official source")} {link(earliest.get("official_source_url", ""), "Earliest match official source")}</div>'''
    content = f'''
<section class="hero"><div class="eyebrow">Independent snapshot acceptance audit</div><h1>Executive summary: what is a pick, and what still needs review?</h1>
<p class="lede">This page checks the merged 15-sport desk against the brief's price focus, full-write-up, source, OLBG cross-reference and freshness requirements. The data is a dated capture, not a live odds feed.</p>
<p><strong>Capture read:</strong> <span class="mono">{e(stamp)}</span> · <strong>window cutoff:</strong> <span class="mono">{e(a["capture"].get("desk_cutoff_utc"))}</span> · <strong>captured payload hashes:</strong> {e(s.get("capture_payload_hashes_passed"))}/{e(s.get("capture_payload_hashes_checked"))} pass.</p>
<div class="callout critical"><strong>Bottom line.</strong> {e(len(promoted))} written selection clears the 70% probability / −250…+10,000 fair-price screen, has an OLBG event URL, and was upcoming at capture. It still lacks a captured injury/availability feed and a match-by-match recent-result log, so <strong>{e(full_count)} picks meet every requested research detail.</strong> Do not treat a blank as “no injury.”</div>
<div class="buttonrow"><a class="button primary" href="picks.html">Open pick shortlist →</a><a class="button" href="../desk/picks.html">All authored picks →</a><a class="button" href="../desk/matches.html">Full matches table →</a><a class="button" href="flagged.html">Flagged for review →</a></div></section>
<div class="kpis">{kpi(s['fixture_rows'],'fixture rows')}{kpi(f"{s['sports_with_fixture_rows']}/15",'sports with rows')}{kpi(s['priced_rows'],'own-line priced')}{kpi(f"{s['high_label_rows']} / {s['high_rows_inside_numeric_focus']}",'High labels / in price focus')}{kpi(f"{s['written_predictions']} / 75",'written / five-per-sport target')}{kpi(s['rows_started_at_or_before_capture'],'starts not future at capture')}</div>
<h2>Only item clearing the numeric, write-up and OLBG link filters</h2>
<div class="cards">{cards}</div>{incomplete}
<h2>How to read the −250…+10,000 focus</h2>
<div class="card"><p>A fair probability of 70% corresponds to approximately <strong>−233</strong> American odds. A −250 price corresponds to roughly <strong>71.4%</strong>. The intersection is narrow: about 70.0%–71.4%. A −526 selection may be a high-probability own line, but it is outside this price-focused shortlist.</p><p class="muted small">The quoted prices above are the desk's own fair prices. The captured rows do not contain an actual OLBG/bookmaker quote, so this audit does not claim the displayed price is currently offered.</p><div class="buttonrow"><a class="button" href="coverage.html">See all 15 sports →</a><a class="button" href="sources.html">Inspect capture sources →</a></div></div>
{root_note}
<h2>Published-data checks</h2><div class="cards">
<article class="card green"><span class="badge high">Pass</span><h3>Capture integrity</h3><p>{e(s['capture_payload_hashes_passed'])}/{e(s['capture_payload_hashes_checked'])} successful captured payloads match their SHA-256 manifest entries; {e(s['capture_failure_count'])} targets failed and remain listed for review.</p><a href="sources.html">Capture manifest and failures →</a></article>
<article class="card green"><span class="badge high">Pass</span><h3>Write-up length and uniqueness</h3><p>{e(s['written_predictions'])} texts; {e(s['prediction_words_min'])}–{e(s['prediction_words_max'])} words; maximum pairwise 3-gram Jaccard {e(s['prediction_similarity_max_3gram_jaccard'])}. The prediction-rule check found {e(s['prediction_rule_failure_count'])} structural errors.</p><a href="../desk/picks.html">Read the full picks →</a></article>
<article class="card red"><span class="badge flag">Review</span><h3>OLBG event traceability</h3><p>{e(s['priced_rows_with_olbg_event'])}/{e(s['priced_rows'])} priced rows have an OLBG event URL; {e(s['predictions_without_olbg_event'])}/{e(s['written_predictions'])} written predictions do not.</p><a href="flagged.html">See affected rows →</a></article>
</div>
'''
    return shell("Executive summary", "index.html", content, a)


def page_picks(a: dict) -> str:
    candidates = a.get("numeric_high_candidates", [])
    promoted = [x for x in candidates if x.get("has_written_prediction") and x.get("olbg_event_url") and x.get("starts_after_capture")]
    content = f'''<div class="eyebrow">Picks · selection first</div><h1>Price-focused High picks</h1>
<p class="lede">A row appears in the candidate cards only when its own fair probability is at least 70% and its American fair price is between −250 and +10,000. Every pick is shown with the market, exact selection, written reasoning and source links.</p>
<div class="callout critical"><strong>Important.</strong> This snapshot contains {e(len(candidates))} numeric High candidates; {e(len(promoted))} also have a full text and an OLBG event link. None carries captured injury / availability details or a match-by-match result log. Treat the surviving card as a research candidate, not a fully cleared betting instruction.</div>
<div class="cards">{''.join(pick_card(x) for x in promoted) if promoted else '<div class="card">No candidates meet all filters in this snapshot.</div>'}</div>
<h2>Numeric High candidates not ready to publish as complete picks</h2>
<p class="muted">The rows below clear the probability and price conditions, but have at least one missing requirement. The official fixture source is linked on each row.</p>
{high_row_table([x for x in candidates if x not in promoted], "No additional numeric High candidates.")}
<h2>All rows currently labelled High</h2>
<p class="muted">“High” in the source desk is a probability label. The additional price-focus column is separate; out-of-range rows are not promoted here as price-focused candidates.</p>
{high_row_table(a.get('high_rows', []))}
<div class="buttonrow"><a class="button primary" href="../desk/picks.html">Open the complete prediction ledger →</a><a class="button" href="../desk/matches.html">All matches →</a><a class="button" href="flagged.html">Why other rows are excluded →</a></div>
'''
    return shell("Pick shortlist", "picks.html", content, a)


def page_coverage(a: dict) -> str:
    sport_rows = a.get("sports", [])
    rows = []
    for r in sport_rows:
        progress = round(100 * r.get("written_predictions", 0) / 5)
        gap = r.get("coverage_gap") or "No source gap recorded in this snapshot."
        rows.append(f'''<tr><td><strong><a href="{e(r.get('category_page'))}">{e(r.get('sport'))}</a></strong></td>
<td class="mono">{e(r.get('fixture_rows'))}</td><td class="mono">{e(r.get('priced_rows'))}</td><td class="mono">{e(r.get('high_labels'))}</td><td class="mono">{e(r.get('numeric_high_candidates'))}</td>
<td class="mono">{e(r.get('written_predictions'))}/5<div class="progress"><span style="width:{progress}%"></span></div></td>
<td class="small">{e(gap)}</td><td>{primary_source_cell(r)}<br><a href="{e(r.get('category_page'))}">Sport page</a></td></tr>''')
    content = f'''<div class="eyebrow">Coverage · one row per requested sport</div><h1>Fifteen-sport coverage</h1>
<p class="lede">This matrix distinguishes listed fixtures, rows with an originated fair line, High labels, numeric price-focus candidates and authored predictions. A blank or zero is not filled by inference.</p>
<div class="callout">The target is five unique written predictions per sport. This snapshot has {e(a['summary']['written_predictions'])} in total; the shortfall by sport is shown below. Official source links lead to the captured competition/federation page or, where only a listing was available, the recorded coverage-gap page.</div>
<div class="tablewrap"><table><thead><tr><th>Sport / category page</th><th>Rows</th><th>Priced</th><th>High labels</th><th>In price focus</th><th>Write-ups / target</th><th>Coverage note</th><th>Source</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<h2>Direct sport pages</h2><div class="cards">{''.join(f'<article class="card"><h3><a href="{e(r["category_page"])}">{e(r["sport"])} →</a></h3><p class="small">{e(r["fixture_rows"])} rows · {e(r["priced_rows"])} priced · {e(r["written_predictions"])} written</p>{primary_source_cell(r)}</article>' for r in sport_rows)}</div>
<div class="buttonrow"><a class="button" href="../desk/coverage.html">Main desk coverage page →</a><a class="button" href="flagged.html">Flagged gaps →</a></div>
'''
    return shell("Sports coverage", "coverage.html", content, a)


def page_flagged(a: dict) -> str:
    integ = a["source_integrity"]
    failures = integ.get("capture_failures", [])
    failure_rows = []
    for f in failures:
        failure_rows.append(f'''<tr><td>{e(f.get('id'))}</td><td class="mono">{e(f.get('status'))}</td><td class="small">{e(f.get('error'))}</td><td>{link(f.get('url',''), 'Official source / attempted target')}</td></tr>''')
    sports = a.get("sports_short_of_five", [])
    shortfall_rows = []
    for s in sports:
        gap_content = e(s.get("coverage_gap")) if s.get("coverage_gap") else '<span class="missing">No capture gap recorded</span>'
        shortfall_rows.append(f'''<tr><td><a href="{e(s.get('category_page'))}">{e(s.get('sport'))}</a></td><td class="mono">{e(s.get('written_predictions'))}/5</td><td class="mono">{e(s.get('shortfall'))}</td><td>{gap_content}</td><td>{primary_source_cell(s)}</td></tr>''')
    handball = a.get("handball_copy_audit", {})
    handball_rows = ""
    if handball.get("issue"):
        handball_rows = f'''<div class="tablewrap"><table><thead><tr><th>Prediction</th><th>Text currently says</th><th>Per-team rate</th><th>Table-derived match total</th><th>Sources</th></tr></thead><tbody><tr><td>Ringsted v GOG · {e(handball.get('row_id'))}</td><td>31.66 goals a match</td><td class="mono">{e(handball.get('mean_goals_per_team_game'))} goals / team-game</td><td class="mono">{e(handball.get('mean_total_goals_per_match'))} goals / match</td><td>{link(handball.get('official_source_url',''), 'Official Danish standings')} {link(handball.get('official_fixture_url',''), 'OLBG event')}</td></tr></tbody></table></div>'''
    else:
        handball_rows = '<p class="muted">No mismatch found in the captured handball prediction.</p>'
    content = f'''<div class="eyebrow">Flagged for review · no inferred replacements</div><h1>Flagged for Review</h1>
<p class="lede">These are concrete limitations in the committed snapshot. Each affected fixture points to its official source URL and, when captured, its OLBG event. Unsupported values stay blank.</p>
{finding_cards(a)}
<h2>High rows outside the requested price range</h2>
<p class="muted">These remain High by the source desk's probability rule, but are excluded from the −250…+10,000 price-focused shortlist.</p>
{high_row_table(a.get('high_outside_price_focus', []), 'No High rows are outside the price band.')}
<h2>High rows without a written prediction</h2>
{general_rows_table(a.get('high_missing_prediction', []), [('start_utc','Start UTC'),('sport','Sport'),('match','Match'),('selection','Selection'),('probability','Probability'),('price','Fair price'),('official_source','Official source'),('olbg_event','OLBG event')])}
<h2>Rows that are not upcoming at capture time</h2>
<p class="muted">Capture read time: <span class="mono">{e(a['capture'].get('captured_utc'))}</span>. Starts at or before that instant are not future fixtures for this snapshot.</p>
{general_rows_table(a.get('not_future_at_capture', []), [('start_utc','Start UTC'),('sport','Sport'),('match','Match'),('selection','Selection'),('flags','Existing flags'),('official_source','Official source'),('olbg_event','OLBG event')])}
<h2>Priced rows without an OLBG event URL</h2>
<p class="muted">{e(a['summary']['priced_rows_without_olbg_event'])} rows have an official source and an originated fair line, but no event URL in the captured OLBG cross-reference. Do not assume the market is currently listed on OLBG.</p>
{general_rows_table(a.get('priced_without_olbg_event', []), [('start_utc','Start UTC'),('sport','Sport'),('match','Match'),('selection','Selection'),('probability','Probability'),('price','Fair price'),('official_source','Official source'),('olbg_event','OLBG event')])}
<h2>Five-prediction target shortfalls</h2>
{general_rows_table(sports, [('sport','Sport'),('fixture_rows','Fixture rows'),('written_predictions','Written / 5'),('shortfall','Shortfall'),('coverage_gap','Coverage note'),('official_source','Official source')])}
<h2>Prediction statistic wording to correct</h2>
<p class="muted">The relevant official standings are recalculated from the committed capture; the text is not silently changed here.</p>
{handball_rows}
<h2>Capture targets that failed</h2>
<p class="muted">{e(integ.get('http_200_records'))}/{e(integ.get('manifest_targets'))} targets returned HTTP 200. The 17 failures are preserved below with their source URL and returned status/error.</p>
<div class="tablewrap"><table><thead><tr><th>Target ID</th><th>Status</th><th>Capture result</th><th>Source URL</th></tr></thead><tbody>{''.join(failure_rows) if failure_rows else '<tr><td colspan="4">No capture failures.</td></tr>'}</tbody></table></div>
<div class="buttonrow"><a class="button" href="sources.html">All source gaps and manifest →</a><a class="button" href="../desk/flagged.html">Main desk flagged register →</a></div>
'''
    return shell("Flagged for Review", "flagged.html", content, a)


def page_sources(a: dict) -> str:
    c = a["capture"]
    integrity = a["source_integrity"]
    failures = integrity.get("capture_failures", [])
    failure_rows = ''.join(f'''<tr><td>{e(f.get('id'))}</td><td class="mono">{e(f.get('status'))}</td><td class="small">{e(f.get('error'))}</td><td>{link(f.get('url',''), 'Open source URL')}</td></tr>''' for f in failures)
    gap_cards = []
    for g in a.get("coverage_gaps", []):
        gap_cards.append(f'''<article class="gap"><h3>{e(g.get('sport'))}</h3><p>{e(g.get('reason'))}</p>{link(g.get('source_url',''), 'Official source / coverage gap')}</article>''')
    mapped = a.get("source_map_counts", {})
    content = f'''<div class="eyebrow">Sources · timestamped primary capture</div><h1>Source register and capture integrity</h1>
<p class="lede">The audit runs on the committed snapshot and does not re-fetch external websites from this environment. The external source links below are for manual review; the stored capture bytes are checked against their recorded SHA-256 values.</p>
<div class="kpis">{kpi(c.get('captured_utc'),'capture finished UTC')}{kpi(f"{c.get('successful_targets')}/{c.get('manifest_targets')}",'HTTP 200 targets')}{kpi(f"{a['summary'].get('capture_payload_hashes_passed')}/{a['summary'].get('capture_payload_hashes_checked')}",'payload hashes pass')}{kpi(c.get('failed_targets'),'failed targets')}</div>
<div class="card"><h3>Capture manifest</h3><p>Capture ID <code>{e(c.get('id'))}</code>; desk cutoff <code>{e(c.get('desk_cutoff_utc'))}</code>; desk generated <code>{e(c.get('desk_generated_utc'))}</code>.</p><p>Manifest SHA-256: <code>{e(c.get('manifest_file_sha256'))}</code></p><p><a class="button" href="../{e(a['source_paths']['capture_manifest'])}">Open committed capture manifest</a> <a class="button" href="../desk/sources.html">Main desk source register</a></p></div>
<h2>How row sources map to the capture</h2><div class="metricline"><span>{e(mapped.get('source_url_matches_successful_capture',0))} row source URLs match a successful manifest URL</span><span>{e(mapped.get('capture_id_matches_successful_capture',0))} match a successful capture ID</span><span>{e(mapped.get('source_link_not_matched_to_successful_manifest_record',0))} unmatched source URLs</span></div>
<p class="small muted">The capture-ID group includes OLBG listing rows whose fixture detail is a market listing; it does not mean that the governing body independently confirmed every listed team/time. Those items remain flagged as listing-only.</p>
<h2>Official coverage gaps</h2><div class="gaplist">{''.join(gap_cards) if gap_cards else '<p>No gap records.</p>'}</div>
<h2>Failed source requests</h2><div class="tablewrap"><table><thead><tr><th>Target ID</th><th>Status</th><th>Capture response</th><th>Source URL</th></tr></thead><tbody>{failure_rows if failure_rows else '<tr><td colspan="4">No failed targets.</td></tr>'}</tbody></table></div>
<div class="callout">The failure status reflects this capture attempt only. A 403, 404, JavaScript shell or DNS error is not used to infer missing fixtures or prices; the corresponding values remain blank and are flagged.</div>
'''
    return shell("Sources", "sources.html", content, a)


def main() -> int:
    audit = read_audit()
    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / "style.css").write_text(CSS.strip() + "\n", encoding="utf-8")
    pages = {
        "index.html": page_index(audit),
        "picks.html": page_picks(audit),
        "coverage.html": page_coverage(audit),
        "flagged.html": page_flagged(audit),
        "sources.html": page_sources(audit),
    }
    for name, content in pages.items():
        (SITE / name).write_text(content, encoding="utf-8")
    print(f"Built {len(pages)} QF pages in {SITE.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
