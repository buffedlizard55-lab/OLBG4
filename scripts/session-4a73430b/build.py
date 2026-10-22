#!/usr/bin/env python3
"""Board 4a73430b builder. Deterministic: reads canonical data/master.json (read-only),
recomputes American odds + focus window, attaches live checks recorded 2026-10-22,
authors 4 replacement predictions from build-verified official facts only, renders site.
No fixture, price or form fact is invented: blank stays blank and is flagged."""
import json, re, html, collections, pathlib, hashlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT_D = ROOT / "data/session-4a73430b"
OUT_S = ROOT / "session-4a73430b"
CUTOFF = "2026-10-22"

EXCLUDED = {"soccer","football","boxing","ufc","mma","american football","hurling","horse racing","cycling","specials"}

def dec_to_am(d):
    d = float(d)
    return int(round(-100/(d-1))) if d < 2 else int(round((d-1)*100))

def pick_moneyline(r):
    """Return (decimal, matched_key) for the pick side only when pick_market is a win/moneyline market."""
    market = (r.get("pick_market") or "").lower()
    if not any(k in market for k in ("winner","moneyline","win match")) and market not in ("moneyline",):
        return None, None
    odds = (r.get("win") or {}).get("odds") or {}
    side = r.get("pick_side")
    team = r.get("home") if side == "home" else r.get("away") if side == "away" else None
    cands = [team, (r.get("pick") or "").split(" to ")[0].strip()]
    for c in cands:
        if not c: continue
        for k, v in odds.items():
            kk = k.split("—")[-1].strip()
            if kk == c or c in kk or kk in c:
                try: return float(v), k
                except Exception: pass
    return None, None

REPLACEMENTS = {
 "M0139": {
  "text": "Gerwyn Price gets the vote to beat Rob Cross in this European Championship first-round tie in Dortmund, and the clear selection is Price to win the match on the moneyline at our originated 1.47. The PDC's official draw, published on 18 October, seeds Price 13th on the one-year European Tour Order of Merit with Cross down in 20th, so on the tour's own current-form ranking the Welshman arrives as the higher-rated player of the two. That seeding gap is exactly what our rating is built from, and it points only one way here: back Gerwyn Price to win.",
  "facts": [
    {"fact": "PDC draw (18 Oct 2026): Gerwyn Price seeded 13, Rob Cross seeded 20 (European Tour rankings)", "source": "https://www.pdc.tv/news/2026/october/18/2026-Machineseeker-European-Championship-field---draw-confirmed"},
    {"fact": "Fixture: European Championship Round 1, 22 Oct 2026, Westfalenhalle, Dortmund (canonical row M0139, build-verified)", "source": "https://www.pdc.tv/news/2026/october/18/2026-Machineseeker-European-Championship-field---draw-confirmed"},
  ]},
 "M0240": {
  "text": "Samoa are the selection to win this World Cup Round 2 match away to Papua New Guinea in Port Moresby, taking the Samoa moneyline at our originated 1.49 as the high-confidence play. Recent match history is emphatic: in Round 1 Samoa hammered France 78-4, a 74-point margin reported by the NRL, while Papua New Guinea's own opening win was a much tighter 42-18 against Lebanon on home soil. Both sides won last weekend, but only one of them produced a rout, and that current form makes Samoa to win the obvious bet.",
  "facts": [
    {"fact": "NRL Round 1 results: Samoa 78-4 France; Papua New Guinea 42-18 Lebanon", "source": "https://www.nrl.com/news/2026/10/20/world-cup-team-lists-mens-round-2/"},
    {"fact": "Fixture, venue and round confirmed on the NRL official Round 2 team-list article (20 Oct 2026); venue Santos National Football Stadium, Port Moresby (row M0240)", "source": "https://www.nrl.com/news/2026/10/20/world-cup-team-lists-mens-round-2/"},
  ]},
 "M0246": {
  "text": "Leinster to win the derby against Munster at the Aviva Stadium is the selection, with the Leinster moneyline at our originated 1.51 the high-confidence bet. Current form from the official URC Round 3 results could hardly contrast more: Leinster beat Cardiff 29-5, a 24-point win built on conceding a single score, whereas Munster could only draw 26-26 with Ulster in the same round. One side is winning comfortably and the other is being held, so recent match history points firmly to the hosts. Back Leinster to win.",
  "facts": [
    {"fact": "URC official Round 3 results: Leinster 29-5 Cardiff; Ulster 26-26 Munster", "source": "https://stats.unitedrugby.com/match-centre/2026-27/4"},
    {"fact": "Fixture listed in URC Round 4 match centre; venue Aviva Stadium, Dublin, Sat 24 Oct 2026 (row M0246)", "source": "https://stats.unitedrugby.com/match-centre/2026-27/4"},
  ]},
 "M0274": {
  "text": "New Zealand to beat the Cook Islands in Christchurch is the high-confidence selection, and the bet is the New Zealand moneyline at our originated 1.55. Judge both teams by their Round 1 World Cup form: New Zealand lost only 24-22 to Australia, pushing the tournament's benchmark side to a two-point game, while the Cook Islands were beaten 40-12 by Fiji in their opener. A narrow defeat against elite opposition is far stronger recent match history than a 28-point loss, so New Zealand to win is the clear pick.",
  "facts": [
    {"fact": "NRL Round 1 results: Australia 24-22 New Zealand; Fiji 40-12 Cook Islands", "source": "https://www.nrl.com/news/2026/10/20/world-cup-team-lists-mens-round-2/"},
    {"fact": "Fixture, venue and round confirmed on the NRL official Round 2 team-list article (20 Oct 2026); venue One NZ Stadium, Christchurch (row M0274)", "source": "https://www.nrl.com/news/2026/10/20/world-cup-team-lists-mens-round-2/"},
  ]},
}

# Live checks actually read on 2026-10-22 via official endpoints (see live_checks.json).
LIVE_CHECKS = [
 {"id":"XLC-01","source":"NHL official API schedule","url":"https://api-web.nhle.com/v1/schedule/2026-10-22","read":"2026-10-22",
  "confirmed":[{"match":"Nashville Predators at Boston Bruins","date":"2026-10-22","start_utc":"2026-10-22T23:00:00Z","venue":"TD Garden","canonical_id":"M0156"},
               {"match":"New York Rangers at Toronto Maple Leafs","date":"2026-10-22","start_utc":"2026-10-22T23:00:00Z","venue":"Scotiabank Arena","canonical_id":"M0162"},
               {"match":"San Jose Sharks at Ottawa Senators","date":"2026-10-22","start_utc":"2026-10-22T23:00:00Z","venue":"Canadian Tire Centre","canonical_id":"M0159"},
               {"match":"Anaheim Ducks at New Jersey Devils","date":"2026-10-22","start_utc":"2026-10-22T23:00:00Z","venue":"Prudential Center","canonical_id":"M0157"}]},
 {"id":"XLC-02","source":"NHL official standings (standingsDateTimeUtc 2026-10-22T07:22:15Z; date 2026-10-21)","url":"https://api-web.nhle.com/v1/standings/now","read":"2026-10-22",
  "confirmed":[{"match":"Boston Bruins record 7-2-1, 15 pts, GF 36 GA 22, L10 7-2-1 (form context for M0156)","canonical_id":"M0156"},
               {"match":"Edmonton Oilers 7-1-1, 15 pts, GF 41 GA 27 (form context for Edmonton rows)","canonical_id":"M0230"},
               {"match":"Carolina Hurricanes leagueSequence 1: 8-2-1, 17 pts, GF 42 GA 27","canonical_id":""}]},
 {"id":"XLC-03","source":"MLB Stats API schedule (official)","url":"https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-22&endDate=2026-10-30","read":"2026-10-22",
  "confirmed":[{"match":"World Series Game 1: Tampa Bay Rays at Milwaukee Brewers, officialDate 2026-10-23, American Family Field","canonical_id":"M0164"},
               {"match":"World Series Game 2: Tampa Bay Rays at Milwaukee Brewers, officialDate 2026-10-24, American Family Field","canonical_id":"M0210"},
               {"match":"World Series Game 3: Milwaukee Brewers at Tampa Bay Rays, officialDate 2026-10-26, Tropicana Field","canonical_id":"M0282"},
               {"match":"World Series Game 4: Milwaukee Brewers at Tampa Bay Rays, officialDate 2026-10-27, Tropicana Field","canonical_id":"M0293"},
               {"match":"World Series Game 5 (if necessary): 2026-10-28, Tropicana Field; Game 6: 2026-10-30 at Milwaukee","canonical_id":""}]},
 {"id":"XLC-04","source":"OLBG.com live pages (structure only, not a fact source)","url":"https://www.olbg.com/betting-tips","read":"2026-10-22",
  "confirmed":[{"match":"OLBG today feed lists in-scope events incl. Gerwyn Price vs Rob Cross (Darts, Win Match 2-way, 16/20 Win Tips 80%) and TB Rays @ MIL Brewers (Baseball Money Line)","canonical_id":"M0139"},
               {"match":"OLBG Ice Hockey page (sport id 13) markets observed live: Money Line, Puck Line (e.g. +1.50), with x/y Win Tips % and expert counts","canonical_id":""}]},
]

FLAGGED_STATIC = [
 {"id":"X-F01","kind":"contradicted-date","row":"M0252","text":"Canonical row M0252 lists Milwaukee Brewers vs Tampa Bay Rays on 2026-10-25 at American Family Field. The official MLB Stats API schedule read 2026-10-22 has no game on 2026-10-25 (Game 2 is 2026-10-24 at Milwaukee; Game 3 is 2026-10-26 at Tampa Bay). Row held as contradicted; pick not promoted.","source":"https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-22&endDate=2026-10-30"},
 {"id":"X-F02","kind":"home-away-swap","row":"M0164/M0210","text":"Canonical M0164/M0210 record Tampa Bay/Milwaukee home-away designation opposite to the MLB API (official: Tampa Bay Rays at Milwaukee Brewers for Games 1-2). Venues and dates agree; designation flagged for the owning build to correct — not edited here (read-only canonical).","source":"https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-22&endDate=2026-10-30"},
 {"id":"X-F03","kind":"odds-window-tension","row":"all High","text":"A >70% fair probability implies American odds shorter than -233, and -250 equals 71.4% implied: the brief's >70% guide and -250..+10000 window intersect only in the narrow -250..-233 band. This desk therefore defines Focus High transparently (canonical High + published pick price inside the window) and prints each pick's raw implied %; it never claims >70% where the published price implies less.","source":""},
 {"id":"X-F04","kind":"held-high-no-price","row":"M0129,M0163,M0197,M0203,M0205,M0206,M0248 + totals/handicap picks","text":"Canonical High rows whose pick has no matching published moneyline price (empty win.odds, or pick is a total/handicap without a parseable matching price) are held from the Focus list and listed on Flagged with the reason. No price was invented to fill them.","source":""},
 {"id":"X-F05","kind":"live-coverage-limit","row":"all","text":"Live re-reading on 2026-10-22 reached NHL (schedule+standings APIs), MLB Stats API and OLBG pages. The PDC draw URL returned a consent wall to the fetcher, so darts facts are carried from the build-verified canonical notes citing that same official URL, disclosed as not live re-read today. All other sports are carried-current from build-verified canonical data, not claimed as live re-checked today.","source":"https://www.pdc.tv/news/2026/october/18/2026-Machineseeker-European-Championship-field---draw-confirmed"},
 {"id":"X-F06","kind":"markets-blank","row":"see desk.json","text":"Where the originating build published no handicap or total (official inputs missing at pricing time), the cell is left blank on this desk and counted on the Markets page. Markets investigated per sport are listed; blank never means zero — it means not originated.","source":""},
]

def main():
    master = json.load(open(ROOT/"data/master.json"))
    rows = [r for r in master["rows"] if r.get("in_scope") and (r.get("date") or "") >= CUTOFF and r.get("row_type") == "fixture"]
    rows.sort(key=lambda r: (r["date"], r["sport"], r["home"]))
    live_ids = {}
    for lc in LIVE_CHECKS:
        for c in lc["confirmed"]:
            if c.get("canonical_id"): live_ids.setdefault(c["canonical_id"], []).append(lc["id"])
    desk, preds, flagged = [], [], list(FLAGGED_STATIC)
    for r in rows:
        assert r["sport"].lower() not in EXCLUDED, r
        price, key = pick_moneyline(r)
        am = dec_to_am(price) if price else None
        implied = round(100/price, 1) if price else None
        in_window = (am is not None and -250 <= am <= 10000)
        pred = r.get("prediction") or ""
        style = r.get("prediction_style") or ""
        replacement = None
        if r["id"] in REPLACEMENTS:
            replacement = REPLACEMENTS[r["id"]]["text"]
        eff_pred = replacement or (pred if style == "written" else "")
        focus = bool(r.get("confidence") == "High" and in_window and r.get("verified") and eff_pred and len(eff_pred.split()) >= 30)
        held = ""
        if r.get("confidence") == "High" and not focus:
            if price is None: held = "High held: no published matching moneyline price for the pick"
            elif not in_window: held = f"High held: pick price {am:+d} outside -250..+10000"
            elif not r.get("verified"): held = "High held: not build-verified against an official source"
            else: held = "High held: no written prediction >=30 words"
            flagged.append({"id": f"X-H-{r['id']}", "kind": "held-high", "row": r["id"],
                            "text": held + f" ({r['home']} vs {r['away']}, {r['date']}).", "source": r.get("source_url") or ""})
        if r["id"] == "M0252":
            focus = False
            held = "Contradicted by MLB official schedule read 2026-10-22 (no game 2026-10-25) — see X-F01"
        d = {
            "id": r["id"], "sport": r["sport"], "sport_slug": r["sport_slug"], "competition": r.get("competition") or "",
            "date": r["date"], "time": r.get("time") or "", "venue": r.get("venue") or "",
            "home": r["home"], "away": r["away"],
            "win_odds": (r.get("win") or {}).get("odds") or {}, "win_basis": (r.get("win") or {}).get("basis") or "",
            "handicap": r.get("handicap") or "", "total": r.get("total") or "",
            "pick": r.get("pick") or "", "pick_market": r.get("pick_market") or "", "confidence": r.get("confidence") or "",
            "pick_price_dec": price, "pick_price_us": am, "pick_implied_pct": implied, "in_focus_window": in_window,
            "focus_high": focus, "held_reason": held,
            "prediction": eff_pred, "prediction_style": ("replacement-4a73430b" if replacement else style),
            "prediction_words": len(eff_pred.split()),
            "source_url": r.get("source_url") or "", "source_name": r.get("source_name") or "",
            "verified_official": bool(r.get("verified")), "build": r.get("build") or "",
            "live_checks_2026_10_22": live_ids.get(r["id"], []),
            "flags": [f.get("text","") for f in (r.get("flags") or [])],
        }
        if not d["source_url"]:
            flagged.append({"id": f"X-S-{r['id']}", "kind": "no-source", "row": r["id"],
                            "text": f"No source URL recorded by originating build ({r['home']} vs {r['away']}); row shown unverified with blank source.", "source": ""})
        desk.append(d)
        if focus:
            facts = REPLACEMENTS[r["id"]]["facts"] if r["id"] in REPLACEMENTS else [{"fact": "Written prediction carried from build-verified canonical row; facts and inputs in canonical notes for this row.", "source": r.get("source_url") or ""}]
            preds.append({"id": r["id"], "sport": r["sport"], "fixture": f"{r['home']} vs {r['away']}", "date": r["date"],
                          "pick": r.get("pick"), "market": r.get("pick_market"), "price_dec": price, "price_us": am,
                          "implied_pct": implied, "text": eff_pred, "words": len(eff_pred.split()), "facts": facts,
                          "source_url": r.get("source_url") or "", "live_checks": live_ids.get(r["id"], [])})
    counts = {
        "fixtures": len(desk),
        "sports": dict(collections.Counter(d["sport"] for d in desk)),
        "confidence": dict(collections.Counter(d["confidence"] or "none" for d in desk)),
        "verified_official": sum(1 for d in desk if d["verified_official"]),
        "no_source": sum(1 for d in desk if not d["source_url"]),
        "with_moneyline": sum(1 for d in desk if d["win_odds"]),
        "with_handicap": sum(1 for d in desk if d["handicap"]),
        "with_total": sum(1 for d in desk if d["total"]),
        "high_total": sum(1 for d in desk if d["confidence"] == "High"),
        "focus_high": sum(1 for d in desk if d["focus_high"]),
        "live_checked_rows": sum(1 for d in desk if d["live_checks_2026_10_22"]),
        "flagged_items": len(flagged),
    }
    OUT_D.mkdir(parents=True, exist_ok=True)
    json.dump({"schema":"olbg4.session-4a73430b.desk/1","generated_on":"2026-10-22","session":"arena/4a73430b-olbg4",
               "cutoff":CUTOFF,"rule":"Focus High = canonical High + verified official + published moneyline pick price with American odds in [-250,+10000] + written prediction >=30 words. Raw implied % printed per pick; >70% never claimed where price implies less.",
               "counts":counts,"rows":desk}, open(OUT_D/"desk.json","w"), indent=1, ensure_ascii=False)
    json.dump({"schema":"olbg4.session-4a73430b.predictions/1","generated_on":"2026-10-22","predictions":preds}, open(OUT_D/"predictions.json","w"), indent=1, ensure_ascii=False)
    json.dump({"schema":"olbg4.session-4a73430b.flagged/1","generated_on":"2026-10-22","flagged":flagged}, open(OUT_D/"flagged.json","w"), indent=1, ensure_ascii=False)
    json.dump({"schema":"olbg4.session-4a73430b.live_checks/1","read_on":"2026-10-22","checks":LIVE_CHECKS}, open(OUT_D/"live_checks.json","w"), indent=1, ensure_ascii=False)
    # OLBG structure: prior enumeration (data/olbg-structure.json, 2026-10-21) + live evidence 2026-10-22
    struct = json.load(open(ROOT/"data/olbg-structure.json"))
    struct["session_4a73430b_live_evidence"] = {
        "read_on":"2026-10-22","pages_read":["https://www.olbg.com/betting-tips","https://www.olbg.com/betting-tips/Ice_Hockey/13"],
        "observed":["Event cards carry: event link with trailing sport ID + ?event_id=, selection name, market label (e.g. 'Win Match 2-way', 'Money Line', 'Puck Line'), x/y Win Tips with %, comment and expert counts, local start time, venue where OLBG holds it.",
                    "Excluded per brief even though prominent on OLBG today feed: Horse Racing (id 2), Football (id 1), American Football/NFL (id 11).",
                    "In-scope examples read live 2026-10-22: Gerwyn Price vs Rob Cross (Darts id 15, Win Match 2-way), England vs Sri Lanka ODI (Cricket id 7, Win Match), TB Rays @ MIL Brewers (Baseball id 12, Money Line), SHL/Liiga/NHL ice hockey (id 13, Money Line / Puck Line)."]}
    json.dump(struct, open(OUT_D/"olbg_structure.json","w"), indent=1, ensure_ascii=False)
    render(desk, preds, flagged, counts, struct)
    print(json.dumps(counts, indent=1))

CSS = """body{font-family:system-ui,Arial,sans-serif;margin:0;background:#f6f7f9;color:#17202a}header{background:#0b2a4a;color:#fff;padding:22px}header a{color:#9fd0ff}nav{background:#123a63;padding:10px 22px}nav a{color:#fff;margin-right:14px;text-decoration:none}main{max-width:1180px;margin:auto;padding:22px}.kpis{display:flex;gap:12px;flex-wrap:wrap}.kpi{background:#fff;border:1px solid #ddd;border-radius:8px;padding:14px;min-width:140px}.kpi b{font-size:26px;display:block}table{border-collapse:collapse;width:100%;background:#fff;font-size:13px}th,td{border:1px solid #e2e5ea;padding:6px 8px;text-align:left;vertical-align:top}th{background:#eaf1f8}.high{background:#ffe9a8;font-weight:700}.focus{background:#d7f5d0}.card{background:#fff;border:1px solid #ddd;border-radius:8px;padding:16px;margin:14px 0}.muted{color:#5b6b7c}input,select{padding:7px;margin:4px}a{color:#0b5cad}footer{padding:22px;color:#5b6b7c;font-size:12px}"""

def esc(x): return html.escape(str(x if x is not None else ""))
def src_link(d):
    return f'<a href="{esc(d["source_url"])}">official source</a>' if d["source_url"] else '<span class="muted">— unverified (no source)</span>'

def page(title, body, depth=0):
    p = "../"*depth
    return f"""<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>{esc(title)} · OLBG4 Board 4a73430b</title><style>{CSS}</style>
<header><h1 style="margin:0">OLBG4 — Board 4a73430b fresh desk (22 Oct 2026)</h1><p style="margin:6px 0 0">Reverse-engineered from OLBG.com · our own originated lines · every row linked to its official source · unverified stays blank and flagged. <a href="{p}../index.html">Repo home</a></p></header>
<nav><a href="{p}index.html">Dashboard</a><a href="{p}picks.html">★ Focus High picks</a><a href="{p}markets.html">Markets</a><a href="{p}olbg.html">OLBG structure</a><a href="{p}methodology.html">Methodology</a><a href="{p}flagged.html">Flagged for Review</a></nav>
<main>{body}</main><footer>Session arena/4a73430b-olbg4 · Data: <a href="{p}../data/session-4a73430b/desk.json">desk.json</a> · Predictions: <a href="{p}../data/session-4a73430b/predictions.json">predictions.json</a> · This is analysis of published fixtures, not betting advice.</footer>"""

def table(desk, show_pred=False):
    rows = []
    for d in desk:
        odds = ", ".join(f"{esc(k)} {esc(v)}" for k, v in d["win_odds"].items()) or "—"
        us = f"{d['pick_price_us']:+d} ({d['pick_implied_pct']}%)" if d["pick_price_us"] is not None else "—"
        cls = "focus" if d["focus_high"] else ""
        conf = f'<span class="high">High ★FOCUS</span>' if d["focus_high"] else esc(d["confidence"] or "—")
        live = " ✓live 22Oct" if d["live_checks_2026_10_22"] else ""
        pred = f'<br><em>{esc(d["prediction"])}</em>' if show_pred and d["prediction"] else ""
        rows.append(f'<tr class="{cls}" data-sport="{esc(d["sport"])}" data-conf="{esc(d["confidence"])}"><td>{esc(d["date"])} {esc(d["time"])}</td><td>{esc(d["sport"])}<br><span class=muted>{esc(d["competition"])}</span></td><td><b>{esc(d["home"])} vs {esc(d["away"])}</b><br><span class=muted>{esc(d["venue"])}</span>{pred}</td><td>{odds}</td><td>{esc(d["handicap"] or "—")}</td><td>{esc(d["total"] or "—")}</td><td><b>{esc(d["pick"] or "—")}</b><br>{esc(d["pick_market"])}<br>{us}</td><td>{conf}{live}</td><td>{src_link(d)}<br><span class=muted>{esc(d["id"])} build {esc(d["build"])}</span></td></tr>')
    return "<table id=t><thead><tr><th>Date</th><th>Sport</th><th>Match</th><th>Our moneyline</th><th>Our handicap</th><th>Our total</th><th>Pick (US odds, raw implied)</th><th>Confidence</th><th>Source</th></tr></thead><tbody>" + "\n".join(rows) + "</tbody></table>"

FILTER = """<p><input id=q placeholder="Filter text…" oninput="f()"><select id=s onchange="f()"><option value="">All sports</option></select><select id=c onchange="f()"><option value="">All confidence</option><option>High</option><option>Medium</option><option>Low</option></select></p>
<script>let ss=new Set();document.querySelectorAll('#t tbody tr').forEach(r=>ss.add(r.dataset.sport));ss.forEach(x=>{let o=document.createElement('option');o.textContent=x;s.appendChild(o)});function f(){let q=document.getElementById('q').value.toLowerCase(),sv=s.value,cv=c.value;document.querySelectorAll('#t tbody tr').forEach(r=>{r.style.display=(!q||r.textContent.toLowerCase().includes(q))&&(!sv||r.dataset.sport==sv)&&(!cv||r.dataset.conf==cv)?'':'none'})}</script>"""

def render(desk, preds, flagged, counts, struct):
    OUT_S.mkdir(parents=True, exist_ok=True); (OUT_S/"sports").mkdir(exist_ok=True)
    kpis = "".join(f'<div class=kpi><b>{v}</b>{k.replace("_"," ")}</div>' for k, v in
                   [("fixtures ≥22 Oct", counts["fixtures"]), ("verified official", counts["verified_official"]), ("★ Focus High (−250…+10000)", counts["focus_high"]),
                    ("High total", counts["high_total"]), ("live-checked rows 22 Oct", counts["live_checked_rows"]), ("flagged items", counts["flagged_items"])])
    sport_links = " · ".join(f'<a href="sports/{slug}.html">{esc(sport)} ({n})</a>' for (sport, n), slug in
                              zip(sorted(counts["sports"].items()), [next(d["sport_slug"] for d in desk if d["sport"]==sp) for sp in sorted(counts["sports"])]))
    body = f"""<h2>Dashboard — full updated match list (in scope)</h2><div class=kpis>{kpis}</div>
<p>Excluded per brief: soccer/football, boxing, UFC/MMA, American football, hurling, horse racing, cycling, specials. Universe = every canonical in-scope fixture dated ≥ 2026-10-22 (builds A/C/D/E/G, official-sourced), with American odds recomputed this session. <b>Focus High rule:</b> canonical High + verified on an official source + published moneyline pick price inside −250…+10,000 + written prediction ≥30 words. Raw implied % is printed for every pick — where it is below 70% we do not claim a &gt;70% chance (see <a href="flagged.html">X-F03</a>).</p>
<p>{sport_links}</p>{FILTER}{table(desk)}"""
    (OUT_S/"index.html").write_text(page("Dashboard", body))
    # picks
    cards = ""
    for p in preds:
        facts = "".join(f'<li>{esc(f["fact"])} — <a href="{esc(f["source"])}">source</a></li>' for f in p["facts"] if f.get("source"))
        live = " · live-checked 22 Oct (" + ", ".join(p["live_checks"]) + ")" if p["live_checks"] else " · carried from build-verified canonical data (not live re-read 22 Oct)"
        cards += f'<div class=card><h3>{esc(p["fixture"])} — {esc(p["date"])}</h3><p><b>Selection: {esc(p["pick"])}</b> · {esc(p["market"])} · our {esc(p["price_dec"])} = {p["price_us"]:+d} US (raw implied {p["implied_pct"]}%){live}</p><p>{esc(p["text"])}</p><p class=muted>{p["words"]} words · {esc(p["id"])} · <a href="{esc(p["source_url"])}">official source</a></p><ul>{facts}</ul></div>'
    (OUT_S/"picks.html").write_text(page("Focus High picks", f"<h2>★ Focus High-confidence picks ({len(preds)}) — all inside −250…+10,000</h2><p>Each prediction is unique, ≥30 words, names the team/player, current form and recent match history, and states the selection plainly. Facts are listed under every card with their official URL. Four texts (M0139, M0240, M0246, M0274) were newly written this session to replace templated canonical copy, using only facts in the build-verified canonical notes.</p>{cards}"))
    # sports
    for slug in sorted(set(d["sport_slug"] for d in desk)):
        sd = [d for d in desk if d["sport_slug"] == slug]; name = sd[0]["sport"]
        (OUT_S/"sports"/f"{slug}.html").write_text(page(name, f"<h2>{esc(name)} ({len(sd)} fixtures)</h2>{FILTER}{table(sd, show_pred=True)}", depth=1))
    # markets
    mrows = ""
    for sport in sorted(counts["sports"]):
        sd = [d for d in desk if d["sport"] == sport]
        mrows += f'<tr><td>{esc(sport)}</td><td>{len(sd)}</td><td>{sum(1 for d in sd if d["win_odds"])}</td><td>{sum(1 for d in sd if d["handicap"])}</td><td>{sum(1 for d in sd if d["total"])}</td><td>Match winner investigated for every fixture; handicap/spread and match total originated only where the originating build had official inputs — blank cells in the tables mean “not originated”, never zero.</td></tr>'
    (OUT_S/"markets.html").write_text(page("Markets", f"<h2>Markets investigated & originated coverage</h2><table><tr><th>Sport</th><th>Fixtures</th><th>Moneyline originated</th><th>Handicap originated</th><th>Total originated</th><th>Notes</th></tr>{mrows}</table><p>Totals: moneyline {counts['with_moneyline']}/{counts['fixtures']}, handicap {counts['with_handicap']}/{counts['fixtures']}, total {counts['with_total']}/{counts['fixtures']}.</p>"))
    # flagged
    frows = "".join(f'<tr><td>{esc(f["id"])}</td><td>{esc(f["kind"])}</td><td>{esc(f["row"])}</td><td>{esc(f["text"])}</td><td>{("<a href="+esc(f["source"])+">source</a>") if f.get("source") else "—"}</td></tr>' for f in flagged)
    (OUT_S/"flagged.html").write_text(page("Flagged for Review", f"<h2>Flagged for Review ({len(flagged)}) — needs review, non-blocking</h2><p>Every irregularity, held High pick and unverified row found line by line, with its source link for manual review. Nothing here was silently filled in.</p><table><tr><th>ID</th><th>Kind</th><th>Row</th><th>Finding</th><th>Source</th></tr>{frows}</table>"))
    # olbg structure
    srows = "".join(f'<tr><td>{esc(s.get("id"))}</td><td>{esc(s.get("name"))}</td><td>{"IN" if s.get("in_scope") else "OUT — "+esc(s.get("reason",""))}</td><td><a href="https://www.olbg.com/betting-tips/{esc(s.get("slug"))}/{esc(s.get("id"))}">OLBG page</a></td></tr>' for s in struct.get("sports_enumerated", []))
    ev = "".join(f"<li>{esc(x)}</li>" for x in struct["session_4a73430b_live_evidence"]["observed"])
    (OUT_S/"olbg.html").write_text(page("OLBG structure", f"""<h2>OLBG.com reverse-engineered</h2>
<p><b>URL patterns</b> (enumerated 2026-10-21, re-read live 2026-10-22): sport landing <code>olbg.com/betting-tips/&lt;Sport&gt;/&lt;sport_id&gt;</code>; event <code>…/&lt;Category&gt;/&lt;Competition&gt;/&lt;Event&gt;/&lt;sport_id&gt;?event_id=…</code>. The trailing number is the OLBG sport ID. Cards show selection, market label, x/y Win Tips %, expert/comment counts and local start time; untipped fixtures are not publicly enumerable on OLBG, which is why the fixture universe is verified on official league sources, with OLBG used for structure/markets only.</p><ul>{ev}</ul>
<table><tr><th>OLBG sport ID</th><th>Sport</th><th>Scope</th><th>Link</th></tr>{srows}</table>
<p>Machine-readable: <a href="../data/session-4a73430b/olbg_structure.json">olbg_structure.json</a> · Live checks: <a href="../data/session-4a73430b/live_checks.json">live_checks.json</a></p>"""))
    # methodology
    (OUT_S/"methodology.html").write_text(page("Methodology", """<h2>Methodology & verification</h2>
<h3>How the list was built</h3><p>Universe: canonical <code>data/master.json</code> rows that are in scope, are fixtures, and are dated ≥2026-10-22. Excluded sports (soccer/football, boxing, UFC/MMA, American football, hurling, horse racing, cycling, specials) were asserted absent in code. Each row keeps the originating build's official source URL; rows with no source are published unverified with a blank source cell and a flagged entry.</p>
<h3>Our own lines</h3><p>Moneyline / handicap / total are the repository builds' originated lines (basis shown in desk.json per row: governing-body ratings, league-endpoint pipelines, verified-input and per-sport models documented in the repo METHODOLOGY). No bookmaker or OLBG price is used as a line. This session recomputed American odds (decimal &lt;2 → −100/(d−1); otherwise +(d−1)×100) and raw implied % (100/d) for every pick; it did not re-price fixtures whose official inputs were not re-read today — those cells stay exactly as originated or blank.</p>
<h3>Confidence & the −250…+10,000 window</h3><p>Low/Medium/High are the canonical grades. <b>Focus High</b> additionally requires: verified on an official source, a published moneyline price for the pick whose American odds sit in [−250, +10,000], and a unique written prediction of ≥30 words. Because −250 equals 71.4% implied, a &gt;70% fair chance and the window overlap only between −250 and −233; this desk prints raw implied % everywhere and never asserts &gt;70% where the price implies less (finding X-F03).</p>
<h3>Live verification on 2026-10-22</h3><p>Read today: NHL official schedule API (22 Oct slate: Nashville@Boston, NY Rangers@Toronto, San Jose@Ottawa, Anaheim@New Jersey — venues/times confirmed), NHL standings API (dated 2026-10-21), MLB Stats API World Series schedule (Games 1–6), and OLBG today/ice-hockey pages (structure and markets only). The PDC article returned a consent wall to the fetcher and is disclosed as not live re-read today. Everything else is carried-current build-verified data, labelled as such. Line-by-line findings, including one contradicted date (M0252), are on the Flagged page.</p>
<h3>Predictions</h3><p>Focus cards carry the canonical written prediction, except four templated rows (M0139 Price, M0240 Samoa, M0246 Leinster, M0274 New Zealand) given new texts this session built only from facts in the canonical notes (PDC seedings; NRL Round 1 scores; URC Round 3 scores), each fact linked to its official URL on the card.</p>
<h3>Gates</h3><p><code>python3 scripts/session-4a73430b/build.py</code> then <code>python3 scripts/session-4a73430b/verify.py</code> (window maths, ≥30-word unique predictions with obvious selection, official-source presence or flagged blank, local links, scope). Plus repo gates: verify_master, publication audit, pipeline selftest.</p>"""))

if __name__ == "__main__":
    main()
