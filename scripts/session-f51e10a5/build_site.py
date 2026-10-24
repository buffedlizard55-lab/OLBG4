#!/usr/bin/env python3
"""Board FI dashboard builder.

Reads only committed JSON (desk, predictions, review, sources, verify) and
writes the static site under session-f51e10a5/.  Every fixture row and every
pick card carries the official source link of the bytes its numbers came from.
"""
from __future__ import annotations

import html
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(ROOT, "data", "session-f51e10a5")
SITE = os.path.join(ROOT, "session-f51e10a5")

SPORTS = [
    ("Golf", "golf"), ("Volleyball", "volleyball"), ("Rugby Union", "rugby-union"),
    ("Cricket", "cricket"), ("Snooker", "snooker"), ("Darts", "darts"),
    ("Baseball", "baseball"), ("Gaelic Sports", "gaelic-sports"), ("Greyhounds", "greyhounds"),
    ("Tennis", "tennis"), ("Motor Racing", "motor-racing"), ("Handball", "handball"),
    ("Ice Hockey", "ice-hockey"), ("Basketball", "basketball"), ("Rugby League", "rugby-league"),
]
NAV = [
    ("index.html", "Overview"), ("picks.html", "Picks & predictions"), ("entries.html", "All fixtures"),
    ("markets.html", "Markets"), ("coverage.html", "Coverage"), ("sources.html", "Sources"),
    ("verification.html", "Verification"), ("flagged.html", "Flagged for review"),
    ("methodology.html", "Methodology"),
]


def e(x) -> str:
    return html.escape("" if x is None else str(x), quote=True)


def load(name, default):
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        return default
    with open(path) as fh:
        return json.load(fh)


DESK = load("desk.json", {"rows": []})
PREDS = load("predictions.json", {"predictions": []})
REVIEW = load("review.json", {"findings": []})
SOURCES = load("sources.json", {"records": [], "failures": [], "capture_id": ""})
VERIFY = load("verify.json", {"checks": []})

CAPTURE = DESK.get("capture") or SOURCES.get("capture_id", "")
CUTOFF = DESK.get("generated_utc", "")
TODAY = (CUTOFF or "2026-10-24")[:10]
WINDOW = DESK.get("window", {})
CONF_ORDER = {"High": 0, "Medium": 1, "Low": 2}


def am(v):
    if v is None:
        return "—"
    return ("+" + str(v)) if v > 0 else str(v)


def norm(r):
    if not r.get("home") or not r.get("away"):
        a, b = r.get("side_a", ""), r.get("side_b", "")
        if r.get("sport") in ("Ice Hockey", "Baseball", "Basketball", "Volleyball", "Rugby League"):
            r["home"], r["away"] = b, a
        else:
            r["home"], r["away"] = a, b
    if not r.get("match"):
        if r.get("away"):
            if r.get("sport") in ("Ice Hockey", "Baseball", "Basketball"):
                r["match"] = r["away"] + " @ " + r["home"]
            else:
                r["match"] = r["home"] + " vs " + r["away"]
        else:
            r["match"] = r.get("side_a", "")
    return r


ROWS = [norm(dict(r)) for r in DESK.get("rows", [])]
PREDS_BY_ROW = {p["row_id"]: p for p in PREDS.get("predictions", [])}


def rows_for(sp):
    return [r for r in ROWS if r["sport"] == sp]


def conf_badge(c):
    cls = {"High": "b-high", "Medium": "b-med", "Low": "b-low"}.get(c, "b-none")
    return '<span class="badge ' + cls + '">' + e(c or "Unpriced") + "</span>"


def price(r):
    p = r.get("pick")
    if not p:
        return '<span class="small">—</span>'
    return ('<span class="nowrap"><b>' + e(am(p.get("fair_american"))) + "</b> "
            '<span class="small">(' + e(p.get("fair_decimal")) + ")</span></span>")


def src_cell(r):
    url = r.get("official_url") or ""
    if not url:
        return '<span class="badge b-flag">no source</span>'
    nm = (r.get("official_source_name") or "official source")
    nm = nm[:46] + ("…" if len(nm) > 46 else "")
    return '<a href="' + e(url) + '" rel="noopener">' + e(nm) + "</a>"


def olbg_cell(r):
    o = r.get("olbg") or {}
    url = o.get("event_url") or o.get("url")
    if not url:
        return '<span class="small">not listed on the captured OLBG hubs</span>'
    return '<a href="' + e(url) + '" rel="noopener">OLBG event</a>'


def page(title, active, body, prefix=""):
    act = " class='active'"
    nav = "".join('<a href="' + prefix + h + '"' + (act if h == active else "") + ">" + l + "</a>" for h, l in NAV)
    head = (
        '<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>" + e(title) + " · OLBG 15-sport predictions (Board FI)</title>"
        '<link rel="stylesheet" href="' + prefix + 'assets/style.css"></head><body>'
        '<header class="site"><div class="wrap">'
        '<div class="brand">OLBG<span>15</span> · Board FI predictions desk</div>'
        '<nav class="top">' + nav + "</nav></div></header>"
        '<main><div class="wrap">'
    )
    foot = (
        "</div></main>"
        '<footer class="site"><div class="wrap">Dated snapshot · capture <code>' + e(CAPTURE)
        + "</code> · desk generated " + e(CUTOFF)
        + " · every price here is our own originated line (1 ÷ our probability, no margin), never a bookmaker or OLBG quote"
        + " · OLBG links appear only where OLBG lists the event.</div></footer></body></html>"
    )
    return head + body + foot


def pred_card(p):
    r = next((x for x in ROWS if x["id"] == p["row_id"]), None)
    conf = p.get("confidence") or "Low"
    cls = {"High": "", "Medium": "med", "Low": "low"}.get(conf, "low")
    facts = []
    if r:
        for k, v in (r.get("form") or {}).items():
            facts.append("<div class='fact'><b>Official form · " + e(k) + "</b>" + e(v) + "</div>")
        for k, v in list((r.get("evidence") or {}).items())[:5]:
            if isinstance(v, (dict, list)) or v in (None, ""):
                continue
            facts.append("<div class='fact'><b>" + e(k) + "</b>" + e(v) + "</div>")
    facts.append("<div class='fact'><b>Injuries / availability</b> "
                 "<span class='badge b-flag'>unverified</span> no injury or availability statement is published "
                 "on the captured official page for this fixture, so none is claimed.</div>")
    if p.get("in_window"):
        win = "<span class='badge b-ok'>inside −250…+10,000</span>"
    else:
        win = "<span class='badge b-none'>outside the −250…+10,000 window</span>"
    if p.get("olbg_url"):
        olbg_html = " · <a href='" + e(p["olbg_url"]) + "' rel='noopener'>OLBG event page</a>"
    else:
        olbg_html = " · <span class='small'>OLBG event page not in this capture</span>"
    prob = round((p.get("prob") or 0) * 100, 1)
    return (
        "<div class='card pick " + cls + "' id='" + e(p["prediction_id"]) + "'>"
        "<div class='small'>" + e(p["sport"]) + " · " + e(p["competition"]) + " · starts " + e(p["start_utc"]) + "</div>"
        "<div class='selection'>" + e(p["match"]) + "</div>"
        "<div><b>Selection:</b> " + e(p["selection"]) + " <span class='small'>· " + e(p["market"]) + "</span> "
        "<span class='price'>" + e(am(p.get("american"))) + "</span> "
        "<span class='small'>(" + e(p.get("decimal")) + " fair · " + e(prob) + "%)</span> "
        + conf_badge(conf) + " " + win + "</div>"
        "<p class='pred'>" + e(p["text"]) + "</p>"
        "<div class='small'>" + e(p.get("word_count")) + " words"
        + (" · " + e(p["venue"]) if p.get("venue") else "") + "</div>"
        "<div class='facts'>" + "".join(facts) + "</div>"
        "<div class='src' style='margin-top:10px'>Official source: "
        "<a href='" + e(p.get("source_url", "")) + "' rel='noopener'>" + e(p.get("source_name", "")) + "</a>"
        + olbg_html + "</div></div>"
    )


def coverage_counts():
    out = {}
    for sp, slug in SPORTS:
        rs = rows_for(sp)
        ps = [p for p in PREDS.get("predictions", []) if p["sport"] == sp]
        out[sp] = {
            "rows": len(rs), "priced": sum(1 for r in rs if r.get("pick")), "written": len(ps),
            "high": sum(1 for p in ps if p.get("confidence") == "High"),
            "high_win": sum(1 for p in ps if p.get("confidence") == "High" and p.get("in_window")),
            "win": sum(1 for p in ps if p.get("in_window")),
        }
    return out


def build_index():
    cov = coverage_counts()
    plist = PREDS.get("predictions", [])
    hi = [p for p in plist if p.get("confidence") == "High"]
    win = [p for p in plist if p.get("in_window")]
    win_hi = [p for p in win if p.get("confidence") == "High"]
    today = [p for p in plist if p["start_utc"][:10] == TODAY]
    top = sorted(plist, key=lambda p: (CONF_ORDER.get(p.get("confidence"), 3), -p.get("prob", 0)))
    top_today = [p for p in top if p["start_utc"][:10] == TODAY][:10] or top[:10]
    trs = []
    for p in top_today:
        trs.append(
            "<tr><td>" + e(p["sport"]) + "</td><td><b>" + e(p["match"]) + "</b><div class='small'>"
            + e(p["competition"]) + "</div></td><td><b>" + e(p["selection"]) + "</b><div class='small'>"
            + e(p["market"]) + "</div></td><td class='num'>" + e(am(p.get("american"))) + "</td><td>"
            + conf_badge(p.get("confidence")) + "</td><td class='num'>"
            + e(p["start_utc"][:16].replace("T", " ")) + "</td><td><a href='picks.html#"
            + e(p["prediction_id"]) + "'>write-up</a></td></tr>")
    cov_rows = []
    for sp, slug in SPORTS:
        c = cov[sp]
        if c["written"] >= 5:
            target = "<span class='badge b-ok'>5 written</span>"
        else:
            target = "<span class='badge b-low'>" + str(c["written"]) + " of 5</span>"
        cov_rows.append(
            "<tr><td><a href='sports/" + slug + ".html'>" + e(sp) + "</a></td><td class='num'>" + str(c["rows"])
            + "</td><td class='num'>" + str(c["priced"]) + "</td><td class='num'>" + str(c["written"])
            + "</td><td class='num'>" + str(c["high"]) + "</td><td class='num'>" + str(c["high_win"])
            + "</td><td>" + target + "</td></tr>")
    body = (
        "<h1>Fifteen sports, our own lines, and a written case for every pick</h1>"
        "<p class='lead'>Every fixture below was read on the governing body's own page or official API in capture "
        "<code>" + e(CAPTURE) + "</code> (finished " + e(CUTOFF) + "), priced by this desk, and written up with the form "
        "and statistics behind the selection.</p>"
        "<div class='grid k4' style='margin-top:18px'>"
        "<div class='card'><div class='small'>Fixtures captured</div><div class='kpi'>" + str(len(ROWS)) + "</div>"
        "<div class='small'>" + str(sum(1 for r in ROWS if r.get("pick"))) + " priced with our own line; the rest are "
        "published without a price and flagged</div></div>"
        "<div class='card'><div class='small'>Written predictions</div><div class='kpi blue'>" + str(len(plist)) + "</div>"
        "<div class='small'>30+ words each, unique, every one naming its selection</div></div>"
        "<div class='card'><div class='small'>High-confidence picks</div><div class='kpi'>" + str(len(hi)) + "</div>"
        "<div class='small'>" + str(len(hi)) + " of " + str(len(plist)) + " written picks carry the High label</div></div>"
        "<div class='card'><div class='small'>Inside −250…+10,000</div><div class='kpi warn'>" + str(len(win)) + "</div>"
        "<div class='small'>" + str(len(win_hi)) + " of those are also High confidence</div></div></div>"
        "<h2 id='today'>Executive summary — highest-confidence picks, " + e(TODAY) + " (UTC)</h2>"
        "<div class='tablewrap'><table><thead><tr><th>Sport</th><th>Match</th><th>Selection</th><th>Our price</th>"
        "<th>Confidence</th><th>Start (UTC)</th><th></th></tr></thead><tbody>" + "".join(trs)
        + "</tbody></table></div>"
        "<p class='small'>The <a href='picks.html'>Picks &amp; predictions</a> page carries the full write-up for each, with "
        "the official form lines, statistics and source link under every card.</p>"
        "<h2>Where the picks are</h2><div class='grid k3'>"
        "<div class='card'><h3><a href='picks.html'>Picks &amp; predictions</a></h3><p class='small'>Every written "
        "prediction grouped by sport, each with its selection, our price, confidence label, reasoning and source.</p></div>"
        "<div class='card'><h3><a href='entries.html'>All fixtures</a></h3><p class='small'>Every fixture in the window with "
        "the markets originated, the pick, price, confidence and both official and OLBG links.</p></div>"
        "<div class='card'><h3><a href='markets.html'>Markets</a></h3><p class='small'>Which markets were investigated per "
        "sport, the full ladder of our prices, and what was withheld and why.</p></div>"
        "<div class='card'><h3><a href='coverage.html'>Coverage</a></h3><p class='small'>The 15-sport checklist with the "
        "exact shortfall where five written picks were not available.</p></div>"
        "<div class='card'><h3><a href='sources.html'>Sources</a></h3><p class='small'>The capture manifest: every URL "
        "fetched, its status, byte count and SHA-256, plus every failure.</p></div>"
        "<div class='card'><h3><a href='flagged.html'>Flagged for review</a></h3><p class='small'>Every unconfirmed value, "
        "gap and irregularity, with the link needed to check it by hand.</p></div></div>"
        "<h2>Coverage by sport</h2><div class='tablewrap'><table><thead><tr><th>Sport</th><th>Fixtures</th><th>Priced</th>"
        "<th>Written picks</th><th>High</th><th>High in window</th><th>Target</th></tr></thead><tbody>"
        + "".join(cov_rows) + "</tbody></table></div>"
        "<div class='notice'><b>How to read a price.</b> Every price is ours: the inverse of our own probability with no "
        "margin. A pick at −200 means we make it a 66.7% chance; it is not a quote from a bookmaker and not copied from "
        "OLBG. OLBG is used to establish which events its site lists, and to give an event link on each row. See "
        "<a href='methodology.html'>Methodology</a>.</div>"
    )
    open(os.path.join(SITE, "index.html"), "w").write(page("Overview", "index.html", body))


def build_picks():
    out = ["<h1>Picks &amp; predictions</h1>",
           "<p class='lead'>Every prediction below is written in full, is at least 30 words, names the selection and its "
           "price, and shows the official form and statistics behind it. Where the captured official page says nothing "
           "about injuries or availability, the card says so rather than guessing.</p>"]
    counts = coverage_counts()
    out.append("<div class='sportnav'>" + "".join(
        "<a href='#" + slug + "'>" + e(sp) + " (" + str(counts[sp]["written"]) + ")</a>" for sp, slug in SPORTS) + "</div>")
    for sp, slug in SPORTS:
        ps = [p for p in PREDS.get("predictions", []) if p["sport"] == sp]
        out.append("<h2 id='" + slug + "'>" + e(sp) + " <span class='small'>· " + str(len(ps))
                   + " written pick(s)</span></h2>")
        if not ps:
            out.append("<div class='notice bad'>No written pick for this sport in this snapshot: the capture holds no "
                       "official strength input for its in-window fixtures, so no line was invented. The exact missing "
                       "feed is on the <a href='flagged.html'>Flagged for review</a> page and the shortfall is stated on "
                       "<a href='coverage.html'>Coverage</a>.</div>")
            continue
        for p in ps:
            out.append(pred_card(p) + "<div style='height:12px'></div>")
    open(os.path.join(SITE, "picks.html"), "w").write(page("Picks and predictions", "picks.html", "\n".join(out)))


def build_entries():
    body = ["<h1>All fixtures</h1>",
            "<p class='lead'>Every row the desk holds: the fixture, the markets we originated, our pick, the price and "
            "confidence, the analysis link, the official source each number came from, and the OLBG event page where OLBG "
            "lists the match.</p>",
            "<div class='sportnav'>" + "".join(
                "<a href='#" + slug + "'>" + e(sp) + " (" + str(len(rows_for(sp))) + ")</a>" for sp, slug in SPORTS) + "</div>"]
    for sp, slug in SPORTS:
        rs = sorted(rows_for(sp), key=lambda r: (r.get("start_utc") or "9999", r.get("match", "")))
        body.append("<h2 id='" + slug + "'>" + e(sp) + " <span class='small'>· " + str(len(rs))
                    + " fixture(s) · <a href='sports/" + slug + ".html'>sport page</a></span></h2>")
        if not rs:
            body.append("<div class='notice bad'>No fixture captured for this sport in the window. Flagged, not filled in."
                        "</div>")
            continue
        trs = []
        for r in rs:
            pk = r.get("pick") or {}
            mk = ", ".join(m.get("market_name", k) for k, m in (r.get("markets") or {}).items()) or "—"
            pred = PREDS_BY_ROW.get(r["id"])
            writeup = ("<a href='picks.html#" + e(pred["prediction_id"]) + "'>write-up</a>") if pred else "<span class='small'>—</span>"
            trs.append(
                "<tr><td class='nowrap'>" + e((r.get("start_utc") or "—")[:16].replace("T", " ")) + "</td>"
                + "<td><b>" + e(r.get("match")) + "</b><div class='small'>" + e(r.get("competition")) + "</div>"
                + ("<div class='small'>" + e(r.get("venue")) + "</div>" if r.get("venue") else "") + "</td>"
                + "<td class='small'>" + e(mk) + "</td>"
                + "<td>" + e(pk.get("selection") or "") + ("<div class='small'>" + e(pk.get("market", "")) + "</div>" if pk else "") + "</td>"
                + "<td class='num'>" + price(r) + "</td><td>" + conf_badge(pk.get("confidence")) + "</td>"
                + "<td>" + writeup + "</td><td>" + src_cell(r) + "</td><td>" + olbg_cell(r) + "</td>"
                + "<td class='small'>" + e("; ".join(r.get("flags", [])))[:150] + "</td></tr>")
        body.append("<div class='tablewrap'><table><thead><tr><th>Start (UTC)</th><th>Fixture</th><th>Markets originated</th>"
                    "<th>Pick</th><th>Our price</th><th>Conf.</th><th>Analysis</th><th>Official source</th><th>OLBG</th>"
                    "<th>Flags</th></tr></thead><tbody>" + "".join(trs) + "</tbody></table></div>")
    open(os.path.join(SITE, "entries.html"), "w").write(page("All fixtures", "entries.html", "\n".join(body)))


def build_markets():
    stats = {}
    for r in ROWS:
        st = stats.setdefault(r["sport"], {"rows": 0, "mk": {}, "withheld": {}})
        st["rows"] += 1
        for k, m in (r.get("markets") or {}).items():
            nm = m.get("market_name", k)
            st["mk"][nm] = st["mk"].get(nm, 0) + 1
        for f in r.get("flags", []):
            st["withheld"][f] = st["withheld"].get(f, 0) + 1
    trs = []
    for sp, slug in SPORTS:
        st = stats.get(sp, {"rows": 0, "mk": {}, "withheld": {}})
        mk = ", ".join(e(k) + " (" + str(v) + ")" for k, v in sorted(st["mk"].items())) or "—"
        wh = "; ".join(e(k) for k in list(st["withheld"])[:3]) or "—"
        trs.append("<tr><td><a href='sports/" + slug + ".html'>" + e(sp) + "</a></td><td class='num'>"
                   + str(st["rows"]) + "</td><td class='small'>" + mk + "</td><td class='small'>" + wh + "</td></tr>")
    body = ["<h1>Markets investigated</h1>",
            "<p class='lead'>A market is only originated when the capture holds the inputs it needs. Everything else is "
            "recorded as withheld with the reason, so a blank price is never mistaken for a missing effort.</p>",
            "<div class='tablewrap'><table><thead><tr><th>Sport</th><th>Fixtures</th><th>Originated markets (rows)</th>"
            "<th>Withheld / flagged</th></tr></thead><tbody>" + "".join(trs) + "</tbody></table></div>",
            "<h2>The ladder behind every pick</h2>"
            "<p class='lead'>Every originated outcome with our probability and the fair price it implies. Both legs of a "
            "two-way market sum to 1.0000 before rounding.</p>"]
    for sp, slug in SPORTS:
        rs = [r for r in rows_for(sp) if r.get("markets")]
        body.append("<h2 id='m-" + slug + "'>" + e(sp) + " <span class='small'>· " + str(len(rs)) + " priced</span></h2>")
        if not rs:
            body.append("<div class='notice bad'>No market originated for this sport. See the Flagged page and Coverage.</div>")
            continue
        trs = []
        for r in rs[:40]:
            for k, m in (r.get("markets") or {}).items():
                outs = " · ".join(o["label"] + " " + format(o["fair_prob"] * 100, ".1f") + "% (" + am(o["fair_american"]) + ")"
                                  for o in m.get("selections", []))
                trs.append("<tr><td>" + e(r.get("match")) + "</td><td>" + e(m.get("market_name"))
                           + "<div class='small'>" + e(m.get("note", "")) + "</div></td><td class='small'>" + e(outs)
                           + "</td><td class='src'><a href='" + e(r.get("official_url", "")) + "' rel='noopener'>official</a></td></tr>")
        body.append("<div class='tablewrap'><table><thead><tr><th>Fixture</th><th>Market</th>"
                    "<th>Our outcomes (probability, fair American)</th><th>Source</th></tr></thead><tbody>"
                    + "".join(trs) + "</tbody></table></div>")
    open(os.path.join(SITE, "markets.html"), "w").write(page("Markets", "markets.html", "\n".join(body)))


def build_coverage():
    cov = coverage_counts()
    trs = []
    for sp, slug in SPORTS:
        c = cov[sp]
        if c["written"] >= 5:
            badge = "<span class='badge b-ok'>5 written</span>"
            note = ""
        else:
            badge = "<span class='badge b-low'>" + str(c["written"]) + " of 5</span>"
            if c["priced"] == 0:
                note = "no in-window fixture could be priced: the capture holds no official strength input for this sport"
            elif c["priced"] < 5:
                note = ("only " + str(c["priced"]) + " priceable fixture(s) in the capture window, and each row carries "
                        "one pick")
            else:
                note = "fewer than five fixtures inside the window"
        trs.append("<tr><td><a href='sports/" + slug + ".html'>" + e(sp) + "</a></td><td class='num'>" + str(c["rows"])
                   + "</td><td class='num'>" + str(c["priced"]) + "</td><td class='num'>" + str(c["written"])
                   + "</td><td class='num'>" + str(c["high"]) + "</td><td class='num'>" + str(c["win"])
                   + "</td><td>" + badge + "</td><td class='small'>" + e(note) + "</td></tr>")
    body = ["<h1>Coverage — the fifteen sports in the brief</h1>",
            "<p class='lead'>One row per requested sport: fixtures captured, fixtures priced with our own line, written "
            "predictions, High-confidence picks and picks inside the requested price window. Where the five-pick target is "
            "not met the exact shortfall is stated.</p>",
            "<div class='tablewrap'><table><thead><tr><th>Sport</th><th>Fixtures</th><th>Priced</th><th>Written</th>"
            "<th>High</th><th>In window</th><th>Target</th><th>Shortfall / note</th></tr></thead><tbody>"
            + "".join(trs) + "</tbody></table></div>",
            build_listings_section(),
            "<p class='small'>Window " + e(WINDOW.get("start", "")) + " → " + e(WINDOW.get("end", "")) + ". Cut-off "
            + e(CUTOFF) + ". Counts come from <code>data/session-f51e10a5/desk.json</code> and <code>predictions.json</code>."
            "</p>"]
    open(os.path.join(SITE, "coverage.html"), "w").write(page("Coverage", "coverage.html", "\n".join(body)))


def build_listings_section():
    """Events OLBG lists that no official fixture in this capture matches."""
    listings = DESK.get("olbg_listings", [])
    if not listings:
        return ""
    by = {}
    for x in listings:
        by.setdefault(x["sport"], []).append(x)
    rows = []
    for sp, slug in SPORTS:
        items = sorted(by.get(sp, []), key=lambda x: x.get("start_utc") or "")
        if not items:
            continue
        ex = " · ".join("<a href='" + e(i["event_url"]) + "' rel='noopener'>" + e(i["event"][:42]) + "</a>"
                        for i in items[:3])
        rows.append("<tr><td>" + e(sp) + "</td><td class='num'>" + str(len(items)) + "</td><td class='small'>"
                    + ex + (" …" if len(items) > 3 else "") + "</td></tr>")
    if not rows:
        return ""
    return ("<h2>OLBG-listed events with no official fixture located</h2>"
            "<p class='lead'>These events appear on the OLBG sport hubs inside the window, but no official fixture or value "
            "for them exists in this capture. They are recorded here rather than published as rows: a row without an "
            "official source would breach the desk's own rule. " + str(len(listings)) + " event(s) in total.</p>"
            "<div class='tablewrap'><table><thead><tr><th>Sport</th><th>Events</th><th>Examples</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>")


def build_sources():
    recs = SOURCES.get("records", [])
    fails = SOURCES.get("failures", [])
    body = ["<h1>Sources</h1>",
            "<p class='lead'>Capture <code>" + e(SOURCES.get("capture_id")) + "</code>, fetched from an Actions runner with "
            "open egress. " + str(len(recs)) + " responses were stored byte-for-byte with a SHA-256 each; " + str(len(fails))
            + " requests failed and are listed too. Every row and pick on this site links to one of the successful responses "
            "below.</p>"]
    groups = [("Official league, tour, federation and API sources", [r for r in recs if "olbg.com" not in r["url"]]),
              ("OLBG pages — event taxonomy and event links only", [r for r in recs if "olbg.com" in r["url"]])]
    for title, group in groups:
        body.append("<h2>" + title + " <span class='small'>· " + str(len(group)) + "</span></h2>")
        trs = "".join("<tr><td>" + e(r["id"]) + "</td><td class='src'><a href='" + e(r["url"]) + "' rel='noopener'>"
                      + e(r["url"]) + "</a></td><td class='num'>" + format(r.get("bytes", 0), ",")
                      + "</td><td class='src'><code>" + e((r.get("sha256") or "")[:16]) + "…</code></td></tr>"
                      for r in sorted(group, key=lambda x: x["id"]))
        body.append("<div class='tablewrap'><table><thead><tr><th>Capture id</th><th>URL</th><th>Bytes</th>"
                    "<th>SHA-256</th></tr></thead><tbody>" + trs + "</tbody></table></div>")
    if fails:
        body.append("<h2>Failed requests <span class='small'>· " + str(len(fails)) + "</span></h2>")
        trs = "".join("<tr><td>" + e(f["id"]) + "</td><td class='src'><a href='" + e(f["url"]) + "'>" + e(f["url"])
                      + "</a></td><td class='small'>" + e(f.get("error")) + "</td></tr>" for f in fails)
        body.append("<div class='tablewrap'><table><thead><tr><th>Capture id</th><th>URL</th><th>Error</th></tr></thead>"
                    "<tbody>" + trs + "</tbody></table></div>")
    open(os.path.join(SITE, "sources.html"), "w").write(page("Sources", "sources.html", "\n".join(body)))


def build_flagged():
    fs = REVIEW.get("findings", [])
    body = ["<h1>Flagged for review</h1>",
            "<p class='lead'>Every gap, every unconfirmed number and every irregularity found while building and checking "
            "this desk. Each item names the affected rows or files and links the page needed to check it by hand.</p>",
            "<div class='notice'><b>" + str(len(fs)) + " open item(s).</b></div>"]
    for f in fs:
        sev = (f.get("severity") or "review").lower()
        badge = "b-flag" if sev == "high" else ("b-low" if sev == "medium" else "b-med")
        srcs = "".join(" · <a href='" + e(u) + "' rel='noopener'>source</a>" for u in f.get("sources", []) if u)
        body.append("<div class='card' style='margin-bottom:12px'><div class='small'>" + e(f.get("id")) + " · "
                    + e(f.get("area")) + " · <span class='badge " + badge + "'>" + e(sev) + "</span></div><h3>"
                    + e(f.get("title")) + "</h3><p>" + e(f.get("detail")) + "</p><div class='src'>Affects: <code>"
                    + e(f.get("where", "")) + "</code>" + srcs + "</div></div>")
    open(os.path.join(SITE, "flagged.html"), "w").write(page("Flagged for review", "flagged.html", "\n".join(body)))


def build_verification():
    checks = VERIFY.get("checks", [])
    ok = sum(1 for c in checks if c.get("ok"))
    body = ["<h1>Verification</h1><p class='lead'>The deterministic gate that runs before publication: <b>" + str(ok) + "/"
            + str(len(checks)) + "</b> checks passed at " + e(VERIFY.get("run_utc", "")) + ".</p>"]
    if checks:
        trs = "".join("<tr><td>" + e(c.get("name")) + "</td><td>"
                      + ("<span class='badge b-ok'>PASS</span>" if c.get("ok") else "<span class='badge b-flag'>FAIL</span>")
                      + "</td><td class='small'>" + e(c.get("detail", "")) + "</td></tr>" for c in checks)
        body.append("<div class='tablewrap'><table><thead><tr><th>Check</th><th>Result</th><th>Detail</th></tr></thead>"
                    "<tbody>" + trs + "</tbody></table></div>")
    body.append("<h2>What the gate covers</h2><ul class='tight'>"
                "<li>Every dated row starts inside the declared window and carries an https official source.</li>"
                "<li>Every market's probabilities sum to 1.0000 and every fair price re-derives from its own probability.</li>"
                "<li>Every pick is a real leg of its own market and its confidence follows the stated rule.</li>"
                "<li>Every written prediction is 30+ words, unique, names its selection, avoids internal vocabulary and "
                "carries a source link.</li>"
                "<li>Every internal link resolves and every rendered fixture row contains an official https link.</li>"
                "<li>The site rebuild is byte-identical, so the published pages match the committed data.</li></ul>")
    open(os.path.join(SITE, "verification.html"), "w").write(page("Verification", "verification.html", "\n".join(body)))


def build_methodology():
    body = (
        "<h1>Methodology</h1><p class='lead'>The rules this desk is built to, stated so every number on the site can be "
        "checked.</p>"
        "<h2>1. Scope and window</h2><p>Only the fifteen sports in the brief. A fixture is included only if it appears on an "
        "official schedule, fixture feed or ranking payload captured in this snapshot, or — where the governing body "
        "publishes no machine-readable fixture list — if OLBG lists the event and the governing body's own table or ranking "
        "supplies the strength inputs. Fixtures start at or after <code>" + e(WINDOW.get("start", ""))
        + "</code> and no later than <code>" + e(WINDOW.get("end", "")) + "</code>.</p>"
        "<h2>2. Reading OLBG</h2><p>The sport hubs are read directly. Each tip object carries <code>event_name_alias</code>, "
        "<code>market_alias</code>, <code>odds</code>, <code>american_odds</code>, an event URL and a start timestamp. That "
        "gives the event list, the market taxonomy per sport and the event link printed on each row. No OLBG price ever "
        "enters a line.</p>"
        "<h2>3. Our own lines</h2><p>Every price is ours: <code>fair_decimal = 1 / our probability</code>, no margin, and the "
        "American equivalent is derived from the same number. Independent Poisson scoring models drive the goal and run "
        "sports; exact best-of-N scoreline distributions drive the frame, leg and set sports; Elo built from official results "
        "drives the sports whose feed publishes completed matches but no ranking table; normal margin models drive the "
        "points sports.</p>"
        "<h2>4. Confidence</h2><p><span class='badge b-high'>High</span> needs an official input read in this capture, an "
        "adequate sample, our probability at 70% or better and the resulting own price inside −250…+10,000. "
        "<span class='badge b-med'>Medium</span> is a verified pick at 55–70%, or one carrying a documented cap. "
        "<span class='badge b-low'>Low</span> is everything else, including models capped for a result-only or thin sample. "
        "The cap used is printed on every pick.</p>"
        "<h2>5. Written predictions</h2><p>Each pick names the teams or players, the competition, the date and the venue "
        "where the official page gives one, quotes the official form for both sides and at least one match-specific number, "
        "and states the selection and its price. Every prediction is at least 30 words, contains no internal vocabulary and "
        "is checked against every other prediction for duplication. Injuries and availability are stated only when the "
        "captured official page states them; otherwise the card says none was found and the item is flagged.</p>"
        "<h2>6. What is never done</h2><ul class='tight'><li>No bookmaker odds are read, quoted or copied into a line.</li>"
        "<li>No value is inferred, interpolated or filled from memory. A missing input means an unpriced fixture, published "
        "with a flag.</li><li>No row is published without an official source link.</li>"
        "<li>The desk is a dated snapshot and says so in the footer of every page.</li></ul>"
    )
    open(os.path.join(SITE, "methodology.html"), "w").write(page("Methodology", "methodology.html", body))


def build_sport_pages():
    os.makedirs(os.path.join(SITE, "sports"), exist_ok=True)
    for sp, slug in SPORTS:
        rs = sorted(rows_for(sp), key=lambda r: (r.get("start_utc") or "9999", r.get("match", "")))
        ps = [p for p in PREDS.get("predictions", []) if p["sport"] == sp]
        body = ["<p class='small'><a href='../index.html'>Overview</a> › " + e(sp) + "</p><h1>" + e(sp) + "</h1>",
                "<p class='lead'>" + str(len(rs)) + " fixture(s) captured, " + str(sum(1 for r in rs if r.get("pick")))
                + " priced with our own line, " + str(len(ps)) + " written pick(s), "
                + str(sum(1 for p in ps if p.get("confidence") == "High")) + " of them High confidence.</p>",
                "<h2>Written picks</h2>"]
        if not ps:
            body.append("<div class='notice bad'>No written pick for this sport in this snapshot: no official strength "
                        "input exists in the capture for its in-window fixtures, so nothing was invented. See "
                        "<a href='../flagged.html'>Flagged for review</a>.</div>")
        else:
            body.extend("<div style='margin-bottom:12px'>" + pred_card(p).replace("href='picks.html", "href='../picks.html")
                        + "</div>" for p in ps)
        body.append("<h2>All fixtures</h2>")
        if rs:
            trs = "".join(
                "<tr><td class='nowrap'>" + e((r.get("start_utc") or "—")[:16].replace("T", " ")) + "</td><td><b>"
                + e(r.get("match")) + "</b><div class='small'>" + e(r.get("competition")) + "</div></td><td>"
                + e((r.get("pick") or {}).get("selection") or "") + "</td><td class='num'>" + price(r) + "</td><td>"
                + conf_badge((r.get("pick") or {}).get("confidence")) + "</td><td>" + src_cell(r) + "</td><td>"
                + olbg_cell(r) + "</td></tr>" for r in rs)
            body.append("<div class='tablewrap'><table><thead><tr><th>Start (UTC)</th><th>Fixture</th><th>Pick</th>"
                        "<th>Our price</th><th>Conf.</th><th>Official source</th><th>OLBG</th></tr></thead><tbody>"
                        + trs + "</tbody></table></div>")
        else:
            body.append("<div class='notice bad'>No fixture captured for this sport in the window.</div>")
        open(os.path.join(SITE, "sports", slug + ".html"), "w").write(page(sp, "", "\n".join(body), "../"))


def main():
    os.makedirs(SITE, exist_ok=True)
    build_index()
    build_picks()
    build_entries()
    build_markets()
    build_coverage()
    build_sources()
    build_flagged()
    build_methodology()
    build_verification()
    build_sport_pages()
    print("site built:", SITE)


if __name__ == "__main__":
    main()
