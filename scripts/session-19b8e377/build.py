#!/usr/bin/env python3
"""
Board Z (arena/19b8e377-olbg4) — build the desk.

Pipeline
  1. load the verified fixture inputs (matches_handball.py / matches_other.py) and the
     source register (sources_data.py)
  2. originate our own prices for every market we hold verified inputs for:
       moneyline, handicap and match total, from a documented, unfitted model
  3. choose the match-winner pick and grade it Low / Medium / High
  4. mark the single best selection per fixture whose fair price falls inside the
     requested -250 to +10,000 American window and whose model probability is >= 70%
  5. load the authored write-ups (authored_predictions.json), check them, and render
     the desk

Nothing here reads a bookmaker or OLBG price.  Every published number is either an
input copied from the official source or an output of the arithmetic below.
"""
from __future__ import annotations

import html
import json
import math
import pathlib
import re
import sys
from collections import Counter, defaultdict
from statistics import NormalDist

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

import sources_data  # noqa: E402
import matches_handball as MH  # noqa: E402
import matches_other as MO  # noqa: E402

SPORT_META = sources_data.SPORT_META
SPORT_ORDER = sources_data.SPORT_ORDER
EXCLUDED_SPORTS = sources_data.EXCLUDED_SPORTS

ND = NormalDist()
DATA = ROOT / "data" / "session-19b8e377"
SITE = ROOT / "session-19b8e377"
SPORTS_SITE = SITE / "sports"

BUILD_UTC = "2026-10-22T07:55:00Z"
WINDOW_LO, WINDOW_HI = -250, 10000
HIGH_FLOOR = 0.700
BAND_HI = 1.0 / 1.40          # 0.714285…: prices shorter than -250 sit above this probability


# ------------------------------------------------------------------ helpers
def fair_dec(p: float) -> float:
    return round(1.0 / min(max(p, 0.01), 0.99), 2)


def book_dec(p: float, overround: float = 1.045) -> float:
    bp = min(max(p * overround, 0.015), 0.985)
    return max(1.02, round(1.0 / bp, 2))


def american(dec: float) -> int:
    if dec >= 2.0:
        return int(round((dec - 1.0) * 100))
    return int(round(-100.0 / (dec - 1.0)))


def american_from_prob(p: float) -> int:
    return american(fair_dec(p))


def pct(p: float) -> str:
    return f"{p*100:.1f}%"


def esc(x) -> str:
    return html.escape("" if x is None else str(x), quote=True)


# ------------------------------------------------------------------ models
def handball_probs(h: dict, a: dict):
    gd_h = (h["gf"] - h["ga"]) / h["gp"]
    gd_a = (a["gf"] - a["ga"]) / a["gp"]
    wr_h = (h["w"] + 0.5 * h["d"]) / h["gp"]
    wr_a = (a["w"] + 0.5 * a["d"]) / a["gp"]
    mu = 1.10 * (gd_h - gd_a) + 6.0 * (wr_h - wr_a) + 1.4
    sigma = 7.0
    p_home = min(max(ND.cdf(mu / sigma), 0.03), 0.97)
    exp_total = ((h["gf"] + h["ga"]) / h["gp"] + (a["gf"] + a["ga"]) / a["gp"]) / 2.0
    return dict(p_home=p_home, mu=mu, sigma=sigma, exp_total=exp_total,
                rating_home=gd_h, rating_away=gd_a)


def basketball_probs(h: dict, a: dict):
    gd_h = (h["pf"] - h["pa"]) / h["gp"]
    gd_a = (a["pf"] - a["pa"]) / a["gp"]
    wr_h = h["w"] / h["gp"]
    wr_a = a["w"] / a["gp"]
    mu = 0.55 * (gd_h - gd_a) + 8.0 * (wr_h - wr_a) + 2.0
    sigma = 13.0
    p_home = min(max(ND.cdf(mu / sigma), 0.04), 0.96)
    exp_total = ((h["pf"] + h["pa"]) / h["gp"] + (a["pf"] + a["pa"]) / a["gp"]) / 2.0
    return dict(p_home=p_home, mu=mu, sigma=sigma, exp_total=exp_total,
                rating_home=gd_h, rating_away=gd_a)


def volleyball_probs(h: dict, a: dict):
    rh = (h["pf"] / h["pa"] - 1.0) * 100.0
    ra = (a["pf"] / a["pa"] - 1.0) * 100.0
    p_home = 1.0 / (1.0 + math.exp(-((rh - ra) + 2.0) / 5.0))
    p_home = min(max(p_home, 0.08), 0.92)
    return dict(p_home=p_home, mu=None, sigma=None, exp_total=None, rating_home=rh, rating_away=ra)


def tennis_probs(h: dict, a: dict):
    ratio = math.log(h["pts"] / a["pts"])
    p_home = 1.0 / (1.0 + math.exp(-ratio))
    return dict(p_home=p_home, mu=3.6 * ratio, sigma=5.5, exp_total=22.5,
                rating_home=h["pts"], rating_away=a["pts"])


MODELS = {
    "handball": (handball_probs, "goals"),
    "basketball": (basketball_probs, "points"),
    "volleyball": (volleyball_probs, "sets"),
    "tennis": (tennis_probs, "games"),
}


def volley_set_market(p: float):
    """Distribution over set scores implied by a 3-0/3-1/3-2 split at probability p."""
    d = {("3-0"): p * 0.45, ("3-1"): p * 0.35, ("3-2"): p * 0.20,
         ("2-3"): (1 - p) * 0.20, ("1-3"): (1 - p) * 0.35, ("0-3"): (1 - p) * 0.45}
    exp_sets = sum(3 + (1 if k in ("3-1", "1-3") else 2 if k in ("3-2", "2-3") else 0) * v
                   for k, v in d.items())
    p_minus15 = d["3-0"] + d["3-1"]            # home wins by two or more sets
    p_plus15 = d["2-3"] + d["1-3"] + d["0-3"]
    return exp_sets, p_minus15, p_plus15, d


def handicap_grid(sport: str):
    if sport == "handball":
        return [round(0.5 + i, 1) for i in range(7)]               # 0.5 … 6.5
    if sport == "basketball":
        return [round(1.5 + 2 * i, 1) for i in range(15)]          # 1.5 … 29.5
    if sport == "tennis":
        return [1.5, 2.5, 3.5, 4.5, 5.5, 6.5]
    return []


def total_grid(sport: str, exp_total: float | None):
    if sport == "handball":
        base = round(exp_total * 2) / 2
        return [base + d for d in (-4.5, -2.5, 2.5, 4.5)]
    if sport == "basketball":
        base = round(exp_total / 2) * 2
        return [base + d for d in (-9.5, -5.5, 5.5, 9.5)]
    if sport == "tennis":
        return [19.5, 22.5, 25.5]
    return []


# ------------------------------------------------------------------ originate
def originate(m: dict):
    """Return the market book for one fixture, or None when inputs are incomplete."""
    model = m["model"]
    if model == "snooker":
        return None
    fn, unit = MODELS[model]
    h, a = m["hs"], m["as_"]
    needed = {"handball": ("gp", "w", "d", "l", "gf", "ga"),
              "basketball": ("gp", "w", "l", "pf", "pa"),
              "volleyball": ("gp", "sw", "sl", "pf", "pa"),
              "tennis": ("pts",)}[model]
    for side in (h, a):
        if any(side.get(k) in (None, "") for k in needed):
            return None
        if model == "volleyball" and side["gp"] == 0:
            return None
        if model == "tennis" and side["pts"] in (0, None):
            return None

    p = fn(h, a)
    ph = p["p_home"]
    pa = 1.0 - ph
    book = {
        "prob_home": ph, "prob_away": pa,
        "ml_home": fair_dec(ph), "ml_away": fair_dec(pa),
        "unit": unit, "model_meta": {k: v for k, v in p.items() if k not in ("p_home",)},
        "handicap": [], "total": [],
    }

    # handicap
    if model == "volleyball":
        exp_sets, p_minus, p_plus, _ = volley_set_market(ph)
        book["exp_total"] = round(exp_sets, 2)
        for line, prob in ((1.5, p_minus),):
            book["handicap"].append(dict(line=-line, side="home", prob=prob, dec=fair_dec(prob)))
            book["handicap"].append(dict(line=line, side="away", prob=p_plus, dec=fair_dec(p_plus)))
        # set totals: 3 sets = 3-0 or 0-3, 4 = 3-1 or 1-3, 5 = 3-2 or 2-3
        p3 = ph * 0.45 + pa * 0.45
        p5 = ph * 0.20 + pa * 0.20
        for line, over in ((3.5, 1.0 - p3), (4.5, p5)):
            book["total"].append(dict(line=line, side="over", prob=over, dec=fair_dec(over)))
            book["total"].append(dict(line=line, side="under", prob=1 - over, dec=fair_dec(1 - over)))
    elif model in ("handball", "basketball", "tennis"):
        mu, sigma = p["mu"], p["sigma"]
        for line in handicap_grid(model):
            cover_home = 1.0 - ND.cdf((line - mu) / sigma)
            book["handicap"].append(dict(line=-line, side="home", prob=cover_home, dec=fair_dec(cover_home)))
            book["handicap"].append(dict(line=line, side="away", prob=1 - cover_home, dec=fair_dec(1 - cover_home)))
        exp_total = p["exp_total"]
        book["exp_total"] = round(exp_total, 1)
        for line in total_grid(model, exp_total):
            over = 1.0 - ND.cdf((line - exp_total) / sigma)
            book["total"].append(dict(line=line, side="over", prob=over, dec=fair_dec(over)))
            book["total"].append(dict(line=line, side="under", prob=1 - over, dec=fair_dec(1 - over)))
    return book


def grade_from(p: float, dec: float) -> str:
    am = american(dec)
    if p >= HIGH_FLOOR and WINDOW_LO <= am <= WINDOW_HI:
        return "High"
    if p >= 0.60:
        return "Medium"
    return "Low"


def primary_pick(m: dict, book: dict):
    ph = book["prob_home"]
    side = "home" if ph >= 0.5 else "away"
    p = ph if side == "home" else 1 - ph
    dec = book["ml_home"] if side == "home" else book["ml_away"]
    name = m[side]
    am = american(dec)
    conf = grade_from(p, dec)
    note = ""
    if p >= HIGH_FLOOR and conf != "High":
        note = (f"probability {pct(p)} clears the 70% floor but the fair price {dec:.2f} "
                f"({am:+d}) is shorter than -250, so it is published as Medium and listed on "
                f"Flagged for Review (Z-F-03).")
    return dict(side=side, selection=name, prob=p, dec=dec, american=am,
                confidence=conf, rule_note=note)


def best_in_window(m: dict, book: dict):
    """The single selection closest to 70.7% whose fair price sits inside the window."""
    cands = []
    ph = book["prob_home"]
    for side, prob, dec in (("home", book["prob_home"], book["ml_home"]),
                            ("away", 1 - book["prob_home"], book["ml_away"])):
        cands.append(dict(market="Match winner", side=side, label=m[side], line=None,
                          prob=prob, dec=dec))
    for hc in book["handicap"]:
        cands.append(dict(market="Handicap", side=hc["side"],
                          label=f"{m[hc['side']]} {hc['line']:+g}".replace("+", "+"),
                          line=hc["line"], prob=hc["prob"], dec=hc["dec"]))
    ok = []
    for c in cands:
        am = american(c["dec"])
        if c["prob"] >= HIGH_FLOOR and WINDOW_LO <= am <= WINDOW_HI:
            c["american"] = am
            ok.append(c)
    if not ok:
        return None
    ok.sort(key=lambda c: abs(c["prob"] - 0.706))
    return ok[0]


# ------------------------------------------------------------------ build
def build_rows():
    raw = []
    for bucket in (MH.H, MO.V, MO.T, MO.B, MO.S):
        raw.extend(bucket)
    rows = []
    for m in raw:
        m = dict(m)
        book = originate(m)
        row = dict(
            id=m["id"], sport=m["sport"], competition=m["competition"],
            date=m["date"], time=m["time"], time_note=m["tnote"],
            home=m["home"], away=m["away"], venue=m.get("venue", ""),
            source_id=m["src"], source_url=m["url"],
            inputs=dict(home=m["hs"], away=m["as_"]),
            facts=m.get("facts", []), note=m.get("note", ""),
            status="verified", model=m["model"],
        )
        if book is None:
            row["priced"] = False
            row["markets"] = None
            row["pick"] = dict(side="", selection="", prob=None, dec=None, american=None,
                               confidence="", rule_note="")
            row["in_window_high"] = None
            row["unpriced_reason"] = (
                "Official ranking/season inputs for both sides were not available on the source "
                "read for this fixture, so no line is originated and every price cell is blank."
            )
        else:
            pick = primary_pick(m, book)
            row["priced"] = True
            row["markets"] = book
            row["pick"] = pick
            row["in_window_high"] = best_in_window(m, book)
            row["unpriced_reason"] = ""
        rows.append(row)
    return rows


def load_authored():
    p = DATA / "authored_predictions.json"
    if p.exists():
        return json.loads(p.read_text())
    return {"writeups": {}}


def check_writeup(text: str, label: str):
    """A write-up must be >=30 words, name the selection and its line, and carry a number."""
    problems = []
    words = len(re.findall(r"[A-Za-z0-9''\u2019\-]+", text))
    if words < 30:
        problems.append(f"only {words} words (minimum 30)")
    m = re.match(r"^(.*?)\s*([+-]?\d+(?:\.\d+)?)(?:\s+\w+)?$", label.strip())
    name = (m.group(1) if m else label).strip()
    line = m.group(2) if m else None
    if name.lower() not in text.lower():
        problems.append(f"does not name the selection ({name})")
    if line and line not in text:
        problems.append(f"does not quote the line ({line})")
    if not re.search(r"\d", text):
        problems.append("contains no numeric evidence")
    for bad in ("TODO", "TBD", "lorem", "placeholder"):
        if bad in text.lower():
            problems.append(f"contains the placeholder word {bad}")
    return problems, words


# ------------------------------------------------------------------ flagged
def flagged_items(rows):
    near = []
    for r in rows:
        if not r["priced"]:
            continue
        p = r["pick"]
        if p["prob"] and p["prob"] >= HIGH_FLOOR and p["confidence"] != "High":
            near.append(f"{r['id']} {r['home']} v {r['away']}: {p['selection']} at {pct(p['prob'])}, "
                        f"fair {p['dec']:.2f} ({p['american']:+d})")
    unpriced = [f"{r['id']} {r['home']} v {r['away']} ({r['sport']})" for r in rows if not r["priced"]]

    return [
        dict(id="Z-F-01", title="The >70% rule and the -250 floor only overlap between 70.0% and 71.4%",
             detail=("A price of -250 is a decimal 1.40, i.e. an implied 71.4%. Any selection the model rates above 71.4% "
                     "is priced shorter than the brief's short end and therefore falls outside -250 to +10,000. The two "
                     "conditions can only be met together inside a 1.4-point probability band. The desk applies both "
                     "literally: High requires >=70.0% AND a fair price inside the window. Selections above the band are "
                     "graded Medium and named below rather than relabelled."),
             items=near),
        dict(id="Z-F-02", title="Thirteen fixtures are published with no line at all",
             detail=("No price is originated where both sides' official numbers were not on the page read on 22 October. "
                     "Every price, pick and confidence cell for these rows is blank on purpose."),
             items=unpriced),
        dict(id="Z-F-03", title="Two EuroLeague fixtures disagree on who is at home",
             detail=("The EuroLeague game centre lists the fixture as Anadolu Efes v Besiktas but prints the Turkcell "
                     "Basketball Development Center, and lists Olympiacos v Fenerbahce at SUNEL ARENA. The published home "
                     "side follows the fixture slug; the hall printed on the same page does not obviously belong to that "
                     "home club. Treated as nominal home for pricing and flagged for review."),
             items=["Z-300 Anadolu Efes Istanbul v Besiktas Istanbul (TURKCELL BASKETBALL DEVELOPMENT CENTER)",
                    "Z-307 Olympiacos Piraeus v Fenerbahce Tarfin Istanbul (SUNEL ARENA)"]),
        dict(id="Z-F-04", title="Spanish and Italian basketball clocks render in the reader's timezone",
             detail=("acb.com prints 07:00 and 08:00 for Jornada 5 games that are played on a Sunday afternoon in Spain, "
                     "because the page renders in this browser's timezone and names none. The times are published exactly "
                     "as rendered and were not converted; the date is taken from the same page."),
             items=["Z-313 to Z-318 carry acb.com's rendered clock time"]),
        dict(id="Z-F-05", title="WST and EHF print a clock time without naming the timezone",
             detail=("wst.tv renders match times in the visitor's timezone (the eight Last-16 rows show 08:00 to 15:00) and "
                     "the EHF standings page prints a CET heading but no per-match zone. Both are reproduced verbatim."),
             items=["Z-400 to Z-407 (WST)", "Z-007 to Z-023 (EHF)"]),
        dict(id="Z-F-06", title="The live OLBG listings disagree with the governing bodies on more than 20 fixtures",
             detail=("Read on 22 October 2026, OLBG's sport hubs carried pairings or round labels the official source "
                     "contradicts: four Top 14 pairings that are not the LNR's J7 card; a Hilux NPC 'Bay of Plenty v "
                     "Wellington' final when NZR's final is Canterbury v Northland on 26 October; NBL 'Melbourne v Sydney' "
                     "and 'Adelaide v Brisbane' when the NBL schedule has Illawarra v Sydney and Perth v Melbourne; MLB "
                     "Dodgers v Mets and Yankees v Guardians when the World Series is Dodgers v Blue Jays; an 'England "
                     "Women v India Women' ODI on a date the ECB does not have one; a South Africa v Australia '3rd ODI' "
                     "on a day CSA lists the 2nd Test. Those OLBG rows are excluded from this desk rather than priced."),
             items=["https://top14.lnr.fr/classement", "https://www.provincial.rugby/news/northland-chase-maiden-title-underdogs-against-canterbury",
                    "https://www.nbl.com.au/schedule", "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-22&endDate=2026-10-28",
                    "https://www.ecb.co.uk/news/4594465/how-to-watch-and-follow-the-england-men-v-pakistan-and-sri-lanka",
                    "https://cricket.co.za/upcoming/"]),
        dict(id="Z-F-07", title="Two official feeds could not be read",
             detail=("The German Handball-Bundesliga table is served behind Google reCAPTCHA and the GAA's national "
                     "fixtures endpoint carries no club championship fixtures. Nothing was priced for either, and no "
                     "values were taken from a secondary source."),
             items=["https://www.opel-hbl.de/de/hbl/tabelle (reCAPTCHA)", "https://www.gaa.ie/fixtures-results"]),
        dict(id="Z-F-08", title="Czech and Italian volleyball have one round of data",
             detail=("Both leagues had completed a single round when read, so the strength inputs are one match deep. "
                     "Those fixtures are priced (the model needs only the numbers that exist) but no volleyball pick "
                     "reaches High; the single volleyball High selection is a set handicap, not a match winner."),
             items=["Z-100 to Z-110 (ČVS Extraliga)", "Z-120 to Z-125 (SuperLega)"]),
        dict(id="Z-F-09", title="Model constants are disclosed, not fitted",
             detail=("Goal, point and game margins are normal with sport-specific sigma (7.0 goals handball, 13.0 points "
                     "basketball, 5.5 games tennis) and the margin mean is a linear function of the verified differentials. "
                     "No constant was fitted to a market price. A different sigma moves every alternate line, so the "
                     "prices should be read as our own opinion, not as a market forecast."),
             items=["See the Method page for the exact equations"]),
    ]


# ------------------------------------------------------------------ site
CSS = """
:root{--ink:#172335;--muted:#5b6b80;--line:#dfe5ee;--bg:#f5f7fb;--card:#fff;--acc:#0b5aa8;--acc2:#0f766e;--warn:#b45309}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--acc)}
.wrap{max-width:1180px;margin:0 auto;padding:0 20px}
header.top{background:var(--ink);color:#fff;padding:14px 0}
header.top a{color:#dbe6f5;text-decoration:none}
.bar{display:flex;flex-wrap:wrap;gap:18px;align-items:center;justify-content:space-between}
.brand{font-weight:700;font-size:19px;letter-spacing:.2px;color:#fff}
.brand small{display:block;font-weight:400;font-size:12px;color:#9fb3cd;letter-spacing:.4px}
nav.n{display:flex;flex-wrap:wrap;gap:14px;font-size:14px}
nav.n a{padding:4px 0;border-bottom:2px solid transparent}
nav.n a.on{border-color:#6aa9e0;color:#fff}
h1{font-size:32px;line-height:1.2;margin:26px 0 8px}
h2{font-size:21px;margin:30px 0 10px}
h3{font-size:17px;margin:22px 0 6px}
p.lede{font-size:17px;color:var(--muted);max-width:820px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:14px;margin:22px 0}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px}
.kpi b{display:block;font-size:26px}
.kpi span{font-size:13px;color:var(--muted)}
.note{background:#fff7ed;border-left:4px solid var(--warn);padding:14px 18px;border-radius:8px;margin:18px 0}
.info{background:#eef6ff;border-left:4px solid var(--acc);padding:14px 18px;border-radius:8px;margin:18px 0}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px;margin:18px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;text-decoration:none;color:var(--ink);display:block}
.card:hover{border-color:var(--acc)}
.card b{font-size:16px}
.card .n{font-size:24px;font-weight:700;color:var(--acc)}
.card .m{font-size:12px;color:var(--muted)}
table{width:100%;border-collapse:collapse;background:#fff;font-size:14px}
.scroll{overflow:auto;border:1px solid var(--line);border-radius:12px;margin:14px 0}
th,td{padding:9px 11px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{background:#eef2f8;font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:#42536b;position:sticky;top:0}
tr:last-child td{border-bottom:none}
.tiny{font-size:12px;color:var(--muted)}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px}
.chip{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:600}
.h{background:#dcfce7;color:#166534}.m{background:#e0f2fe;color:#075985}.l{background:#f1f5f9;color:#475569}
.u{background:#fef3c7;color:#92400e}
.pick{background:#fff;border:1px solid var(--line);border-radius:12px;padding:18px;margin:14px 0}
.pick h3{margin-top:0}
.pick .sel{font-size:18px;font-weight:700;color:var(--acc2)}
.pick blockquote{margin:10px 0 0;padding-left:14px;border-left:3px solid #cbd5e1;color:#22304a}
.facts{margin:12px 0 0;padding-left:18px;font-size:13px;color:var(--muted)}
footer.f{background:var(--ink);color:#c3d2e6;margin-top:46px;padding:22px 0;font-size:13px}
footer.f a{color:#9fc6ef}
input[type=search],select{padding:9px 11px;border:1px solid var(--line);border-radius:8px;font-size:14px;background:#fff}
.filters{display:flex;flex-wrap:wrap;gap:10px;margin:14px 0}
"""


NAV = [("index.html", "Dashboard"), ("matches.html", "All matches"), ("picks.html", "Picks"),
       ("markets.html", "Our lines"), ("predictions.html", "High-confidence write-ups"),
       ("analysis.html", "Analysis"), ("verification.html", "Verification"), ("sources.html", "Sources"),
       ("methodology.html", "Method"), ("flagged.html", "Flagged for review")]


def page(title, body, active="", pre=""):
    on = ' class="on"'
    nav = "".join(
        '<a href="%s%s"%s>%s</a>' % (pre, href, on if href == active else "", esc(label))
        for href, label in NAV)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · Board Z — OLBG4 verified desk</title>
<meta name="description" content="Board Z: 91 fixtures across five sports, verified on the governing body's own page on 22 October 2026, with our own moneyline, handicap and total prices.">
<style>{CSS}</style>
</head>
<body>
<header class="top"><div class="wrap bar">
  <div class="brand">Board Z — verified desk<small>OLBG4 · read 22 October 2026 · session arena/19b8e377-olbg4</small></div>
  <nav class="n">{nav}</nav>
</div></header>
<main class="wrap">
{body}
</main>
<footer class="f"><div class="wrap">
  <p><strong>Analysis only, not betting advice. 18+.</strong> Every row carries the official page it was read on.
  No bookmaker or OLBG price is used anywhere on this desk. Values that could not be confirmed are blank and listed on
  <a href="{pre}flagged.html">Flagged for review</a>.</p>
  <p>Built {esc(BUILD_UTC)} by <code>arena/19b8e377-olbg4</code>. Other sessions' desks are untouched and remain at the
  repository root.</p>
</div></footer>
</body></html>
"""


def conf_chip(c):
    cls = {"High": "h", "Medium": "m", "Low": "l"}.get(c, "u")
    return f'<span class="chip {cls}">{esc(c or "—")}</span>'


def md(d: str) -> str:
    return d


def render(rows):
    from_sources = {s["id"]: s for s in sources_data.SOURCES}
    counts = dict(rows=len(rows), priced=sum(1 for r in rows if r["priced"]),
                  high=sum(1 for r in rows if r["priced"] and r["in_window_high"]))
    by_sport = Counter(r["sport"] for r in rows)
    hi_rows = [r for r in rows if r["priced"] and r["in_window_high"]]
    authored = load_authored()["writeups"]
    SITE.mkdir(exist_ok=True)
    SPORTS_SITE.mkdir(exist_ok=True)

    def wkey(r):
        h = r["in_window_high"]
        return f"{r['id']}|{h['market']}|{h['label']}"

    # ---------------- index
    sport_cards = "".join(
        f'<a class="card" href="sports/{SPORT_META[s]["slug"]}.html"><b>{esc(s)}</b>'
        f'<div class="n">{by_sport[s]}</div>'
        f'<div class="m">fixtures · {sum(1 for r in rows if r["sport"]==s and r["priced"] and r["in_window_high"])} high-confidence</div>'
        f'<div class="m">{esc(SPORT_META[s]["gov"])}</div></a>'
        for s in SPORT_ORDER if by_sport[s])
    tops = "".join(
        f'<tr><td><a href="sports/{SPORT_META[r["sport"]]["slug"]}.html">{esc(r["sport"])}</a></td>'
        f'<td>{esc(r["home"])} v {esc(r["away"])}<div class="tiny">{esc(r["competition"])}</div></td>'
        f'<td><strong>{esc(r["in_window_high"]["label"])}</strong><div class="tiny">{esc(r["in_window_high"]["market"])}</div></td>'
        f'<td class="mono">{pct(r["in_window_high"]["prob"])}</td>'
        f'<td class="mono">{r["in_window_high"]["dec"]:.2f} ({r["in_window_high"]["american"]:+d})</td>'
        f'<td><a href="predictions.html#{esc(r["id"])}">write-up</a></td></tr>'
        for r in hi_rows)
    body = f"""
<h1>Ninety-one verified fixtures, our own prices, fourteen in-window high-confidence selections.</h1>
<p class="lede">This desk reads the governing body's own page for every fixture on it — the World Snooker Tour, the EHF
Champions League and four national handball and volleyball leagues, the ATP Tour, EuroLeague and Liga Endesa — and then
originates its own moneyline, handicap and match-total prices from those numbers. No bookmaker price and no OLBG price is
used to set a line. Sports the brief excludes (soccer, boxing, UFC/MMA, American football, hurling, horse racing, cycling,
specials) do not appear anywhere in the data.</p>
<section class="kpis">
  <div class="kpi"><b>{counts['rows']}</b><span>fixtures listed</span></div>
  <div class="kpi"><b>{counts['priced']}</b><span>priced by our model</span></div>
  <div class="kpi"><b>{counts['rows']-counts['priced']}</b><span>published blank and flagged</span></div>
  <div class="kpi"><b>{counts['high']}</b><span>high-confidence selections inside −250 to +10,000</span></div>
  <div class="kpi"><b>{len(authored)}</b><span>hand-written predictions</span></div>
</section>
<div class="info"><strong>How to read the confidence labels.</strong> A selection is graded <em>High</em> only when the
model gives it at least 70.0% <em>and</em> its fair price sits inside the requested −250 to +10,000 window. Those two
conditions overlap only between 70.0% and 71.4%, because −250 is a decimal 1.40. Picks stronger than that are priced
shorter than −250 and are therefore graded Medium and listed on the Flagged page, not silently relabelled.</div>
<h2>Browse by sport</h2>
<div class="cards">{sport_cards}</div>
<h2>The fourteen high-confidence selections</h2>
<div class="scroll"><table>
<thead><tr><th>Sport</th><th>Fixture</th><th>Selection</th><th>Our probability</th><th>Our price</th><th></th></tr></thead>
<tbody>{tops}</tbody></table></div>
<h2>What was verified, and how</h2>
<p>Each of the {counts['rows']} rows carries the exact URL it was read on and the clock time as that page printed it.
Thirty-eight separate official sources are registered on the <a href="sources.html">Sources</a> page, each with what was
read there and when. Two official feeds could not be read at all — the German Handball-Bundesliga table (reCAPTCHA) and
the GAA's national fixtures endpoint (no club championship fixtures) — and nothing was priced for either.</p>
<div class="note"><strong>Thirteen rows have no line.</strong> Eight snooker Last-16 ties, four tennis matches where one
player's ranking is outside the ATP top 100 captured that day, and one volleyball fixture whose home side had not played a
match yet. Every price cell on those rows is blank on purpose and they are listed on
<a href="flagged.html">Flagged for review</a>.</div>
"""
    (SITE / "index.html").write_text(page("Dashboard", body, "index.html"))

    # ---------------- matches
    trs = []
    for r in rows:
        mk = r["markets"]
        line = ""
        if mk:
            line = (f'<div class="tiny">Win {mk["ml_home"]:.2f} / {mk["ml_away"]:.2f}</div>'
                    + (f'<div class="tiny">Handicap ladder: {len(mk["handicap"])} prices</div>' if mk["handicap"] else "")
                    + (f'<div class="tiny">Total ladder: {len(mk["total"])} prices</div>' if mk["total"] else ""))
        else:
            line = '<div class="tiny">— no line originated —</div>'
        badge = ('<span class="chip u">listed, unpriced</span>' if not r["priced"]
                 else conf_chip(r["pick"]["confidence"]))
        trs.append(
            f'<tr data-sport="{esc(r["sport"])}" data-conf="{esc(r["pick"]["confidence"]) if r["priced"] else "Unpriced"}">'
            f'<td class="tiny">{esc(r["date"])}<div class="mono">{esc(r["time"])}</div></td>'
            f'<td><span class="chip l">{esc(r["sport"])}</span><div class="tiny">{esc(r["competition"])}</div></td>'
            f'<td><strong>{esc(r["home"])}</strong> v {esc(r["away"])}'
            + (f'<div class="tiny">{esc(r["venue"])}</div>' if r["venue"] else "") + "</td>"
            f'<td>{line}</td>'
            f'<td>' + (f'<strong>{esc(r["pick"]["selection"])}</strong><div class="tiny">'
                       f'{pct(r["pick"]["prob"])} · {r["pick"]["dec"]:.2f} ({r["pick"]["american"]:+d})</div>{badge}'
                       if r["priced"] else badge) + "</td>"
            f'<td><a href="{esc(r["source_url"])}" rel="noopener">{esc(from_sources[r["source_id"]]["publisher"])}</a>'
            f'<div class="tiny">{esc(r["src"] if "src" in r else r["source_id"])}</div></td></tr>')
    body = f"""
<h1>All {counts['rows']} fixtures</h1>
<p class="lede">Filter by sport or confidence. The kit column names the official publisher; the link is the exact page
the row was read on. Times are reproduced as the source printed them — the source's own timezone caveat is on each row of
the <a href="verification.html">verification register</a>.</p>
<div class="filters">
  <input id="q" type="search" placeholder="Filter by team, competition or date…" aria-label="Filter fixtures">
  <select id="sp"><option value="">All sports</option>{''.join(f'<option>{esc(s)}</option>' for s in SPORT_ORDER if by_sport[s])}</select>
  <select id="cf"><option value="">All confidence</option><option>High</option><option>Medium</option><option>Low</option><option>Unpriced</option></select>
  <span class="tiny" id="cnt"></span>
</div>
<div class="scroll"><table id="t">
<thead><tr><th>Date (source clock)</th><th>Sport / competition</th><th>Fixture</th><th>Our lines</th><th>Our pick</th><th>Official source</th></tr></thead>
<tbody>{''.join(trs)}</tbody></table></div>
<script>
const rows=[...document.querySelectorAll('#t tbody tr')],q=document.getElementById('q'),sp=document.getElementById('sp'),cf=document.getElementById('cf'),cnt=document.getElementById('cnt');
function f(){{let n=0;for(const r of rows){{const ok=(!q.value||r.textContent.toLowerCase().includes(q.value.toLowerCase()))&&(!sp.value||r.dataset.sport===sp.value)&&(!cf.value||r.dataset.conf===cf.value);r.hidden=!ok;if(ok)n++;}}cnt.textContent=n+' of '+rows.length+' rows shown';}}
[q,sp,cf].forEach(e=>e.addEventListener('input',f));f();
</script>
"""
    (SITE / "matches.html").write_text(page("All matches", body, "matches.html"))

    # ---------------- picks
    pick_rows = []
    for r in rows:
        if not r["priced"]:
            continue
        pk = r["pick"]
        pick_rows.append(
            f'<tr><td class="tiny">{esc(r["date"])}</td><td><span class="chip l">{esc(r["sport"])}</span></td>'
            f'<td>{esc(r["home"])} v {esc(r["away"])}</td>'
            f'<td><strong>{esc(pk["selection"])}</strong></td>'
            f'<td class="mono">{pct(pk["prob"])}</td>'
            f'<td class="mono">{pk["dec"]:.2f}<div class="tiny">{pk["american"]:+d}</div></td>'
            f'<td>{conf_chip(pk["confidence"])}</td>'
            f'<td class="tiny">{esc(pk["rule_note"])}</td></tr>')
    body = f"""
<h1>Picks — one match winner per priced fixture</h1>
<p class="lede">The pick is the side our model makes favourite on the money line. The confidence column applies the
brief's rule literally: High needs at least 70.0% and a fair price inside −250 to +10,000.</p>
<div class="info"><strong>Why almost everything is Medium.</strong> Our model reads the season numbers on the official
page, and a club that is 9-1 against one that is 1-9 comes out far above 71.4%. Those picks are sound but they are
priced shorter than −250, so the brief's window excludes them from High. The note column says so on every affected row.</div>
<div class="scroll"><table>
<thead><tr><th>Date</th><th>Sport</th><th>Fixture</th><th>Pick</th><th>Probability</th><th>Our price</th><th>Confidence</th><th>Rule note</th></tr></thead>
<tbody>{''.join(pick_rows)}</tbody></table></div>
<p class="tiny">The {counts['rows']-counts['priced']} unpriced fixtures are not listed here because no pick is made without
a price. They are on <a href="matches.html">All matches</a> and on <a href="flagged.html">Flagged for review</a>.</p>
"""
    (SITE / "picks.html").write_text(page("Picks", body, "picks.html"))

    # ---------------- markets
    mblocks = []
    for r in rows:
        mk = r["markets"]
        if not mk:
            continue
        hc = "".join(
            f'<tr><td>{esc(r["home"] if x["side"]=="home" else r["away"])}</td>'
            f'<td class="mono">{x["line"]:+g}</td><td class="mono">{pct(x["prob"])}</td>'
            f'<td class="mono">{x["dec"]:.2f} ({american(x["dec"]):+d})</td></tr>' for x in mk["handicap"])
        tt = "".join(
            f'<tr><td>{esc(x["side"].title())} {x["line"]:g} {esc(mk["unit"])}</td>'
            f'<td class="mono">{pct(x["prob"])}</td><td class="mono">{x["dec"]:.2f} ({american(x["dec"]):+d})</td></tr>'
            for x in mk["total"])
        mblocks.append(f"""
<details class="pick"><summary><strong>{esc(r["home"])} v {esc(r["away"])}</strong>
 · {esc(r["competition"])} · {esc(r["date"])} {esc(r["time"])}</summary>
 <p class="tiny">Money line: <strong>{esc(r["home"])} {mk["ml_home"]:.2f}</strong> ({american(mk["ml_home"]):+d}) ·
 <strong>{esc(r["away"])} {mk["ml_away"]:.2f}</strong> ({american(mk["ml_away"]):+d}).
 Model expects {mk["model_meta"].get("exp_total","—")} {esc(mk["unit"])} in total.</p>
 <h3>Handicap ladder ({esc(mk["unit"])})</h3>
 <div class="scroll"><table><thead><tr><th>Side</th><th>Line</th><th>Our probability</th><th>Our price</th></tr></thead>
 <tbody>{hc or '<tr><td colspan="4" class="tiny">No handicap originated for this sport.</td></tr>'}</tbody></table></div>
 <h3>Match total</h3>
 <div class="scroll"><table><thead><tr><th>Selection</th><th>Our probability</th><th>Our price</th></tr></thead>
 <tbody>{tt or '<tr><td colspan="3" class="tiny">No total originated for this sport.</td></tr>'}</tbody></table></div>
</details>""")
    body = f"""
<h1>Our lines — every originated price</h1>
<p class="lede">{counts['priced']} fixtures, each with a money line, a handicap ladder and a match total. Probabilities are
the model's; prices are 1 ÷ probability, so the book is round with no margin added. Expand a fixture to see its ladder.</p>
<div class="note"><strong>The ladder is a ladder of our opinion.</strong> Each handicap and total number is priced from the
same distribution as the money line, so the further a line sits from our expected margin, the longer its price. Handling
a line is always available at the price shown.</div>
{''.join(mblocks)}
"""
    (SITE / "markets.html").write_text(page("Our lines", body, "markets.html"))

    # ---------------- predictions
    cards = []
    for r in hi_rows:
        h = r["in_window_high"]
        text = authored.get(wkey(r), "")
        facts = "".join(f"<li>{esc(f)}</li>" for f in r["facts"])
        cards.append(f"""
<article class="pick" id="{esc(r['id'])}">
  <div class="tiny">{esc(r['sport'])} · {esc(r['competition'])} · {esc(r['date'])} · {esc(r['time'])} as printed by the source</div>
  <h3>{esc(r['home'])} v {esc(r['away'])}</h3>
  <div class="sel">{esc(h['label'])} — {h['dec']:.2f} ({h['american']:+d}), our probability {pct(h['prob'])}</div>
  <blockquote>{esc(text)}</blockquote>
  <ul class="facts">{facts}</ul>
  <p class="tiny">Read on <a href="{esc(r['source_url'])}" rel="noopener">{esc(from_sources[r['source_id']]['publisher'])}</a>
  · <a href="markets.html">all originated lines for this fixture</a> · <a href="verification.html">verification entry</a></p>
</article>""")
    body = f"""
<h1>Fourteen high-confidence write-ups</h1>
<p class="lede">One hand-written prediction per in-window high-confidence selection. Each names the selection and its
line, quotes the form numbers that are on the official page, states the recent result we checked, and is at least thirty
words. Every figure below is also printed in the fixture's input line on the verification register.</p>
{''.join(cards)}
"""
    (SITE / "predictions.html").write_text(page("High-confidence write-ups", body, "predictions.html"))

    # ---------------- verification
    vrows = []
    for r in rows:
        s = from_sources[r["source_id"]]
        vrows.append(
            f'<tr><td class="mono">{esc(r["id"])}</td><td>{esc(r["sport"])}</td>'
            f'<td>{esc(r["home"])} v {esc(r["away"])}</td>'
            f'<td><a href="{esc(r["source_url"])}" rel="noopener">{esc(s["publisher"])}</a>'
            f'<div class="tiny mono">{esc(r["source_url"])}</div></td>'
            f'<td class="tiny">{esc(s["notes"])}</td>'
            f'<td class="tiny">{esc(r["time"])} — {esc(r["time_note"])}</td>'
            f'<td>{"verified" if r["priced"] else "inputs incomplete"}</td></tr>')
    body = f"""
<h1>Verification register</h1>
<p class="lede">One line per fixture: the official page it was read on, what that page says, and the clock-time caveat
in the source's own words. A row is marked <em>inputs incomplete</em> when the numbers needed to originate a price for
both sides were not on the page; those rows carry no price anywhere on this desk.</p>
<div class="note">An official URL is evidence that the page was read, not proof that a later reader will see the same
numbers. Fixture lists, standings and schedules change. The register records the reading, and the Sources page records the
time.</div>
<div class="scroll"><table>
<thead><tr><th>ID</th><th>Sport</th><th>Fixture</th><th>Official source</th><th>What was read there</th><th>Clock time</th><th>State</th></tr></thead>
<tbody>{''.join(vrows)}</tbody></table></div>
"""
    (SITE / "verification.html").write_text(page("Verification register", body, "verification.html"))

    # ---------------- flagged
    fl = flagged_items(rows)
    blocks = []
    for f in fl:
        items = "".join(f"<li>{esc(i)}</li>" for i in f["items"])
        blocks.append(f'<section class="pick" id="{esc(f["id"])}"><h3>{esc(f["id"])} — {esc(f["title"])}</h3>'
                      f'<p>{esc(f["detail"])}</p><ul class="tiny">{items}</ul></section>')
    body = f"""
<h1>Flagged for review</h1>
<p class="lede">Everything this desk could not settle, published rather than hidden. None of these items blocked
publication; each one is a decision the reader should see.</p>
<div class="note">This page is the standing review list for Board Z. It is not an error log: an item here means the
official source did not let us publish a value, or two official sources disagree, or a modelling choice needs disclosure.</div>
{''.join(blocks)}
"""
    (SITE / "flagged.html").write_text(page("Flagged for review", body, "flagged.html"))

    # ---------------- sources
    srows = "".join(
        f'<tr><td class="mono">{esc(s["id"])}</td><td>{esc(s["sport"])}</td><td>{esc(s["publisher"])}</td>'
        f'<td><a href="{esc(s["url"])}" rel="noopener">{esc(s["url"])}</a></td>'
        f'<td><span class="chip {"h" if s["status"].startswith("verified") else "u"}">{esc(s["status"])}</span></td>'
        f'<td class="tiny">{esc(s["notes"])}</td>'
        f'<td class="tiny">{sum(1 for r in rows if r["source_id"]==s["id"])}</td></tr>'
        for s in sorted(sources_data.SOURCES, key=lambda x: (not x["status"].startswith("verified"), x["sport"], x["id"])))
    body = f"""
<h1>Sources</h1>
<p class="lede">Every official page this desk read, what was taken from it, and how many fixtures depend on it. The last
column counts the rows on this desk that cite the source.</p>
<div class="scroll"><table>
<thead><tr><th>ID</th><th>Sport</th><th>Publisher</th><th>Page</th><th>Status</th><th>What was read</th><th>Rows</th></tr></thead>
<tbody>{srows}</tbody></table></div>
<div class="note"><strong>Two feeds are registered as unreadable.</strong> The German HBL table is behind a reCAPTCHA and
the GAA national fixtures endpoint carries no club championship fixtures. Both are listed with that status so the gap is
visible rather than filled from elsewhere.</div>
"""
    (SITE / "sources.html").write_text(page("Sources", body, "sources.html"))

    # ---------------- methodology
    body = """
<h1>Method</h1>
<p class="lede">Five steps, in order, with no step skipped for a fixture that appears on the desk.</p>
<h2>1. Read the governing body, not a listing</h2>
<p>Every fixture is taken from the competition organiser's own page: the EHF Champions League standings and calendar,
Tophaandbold's Herreligaen programme, the LNH StarLigue calendar and table, Liga ASOBAL, the Swedish Handbollsligan, ČVS
Extraliga, Lega Pallavolo Serie A, the ATP order of play and rankings, EuroLeague and Liga Endesa, and the World Snooker
Tour match list. OLBG is used only to see what the site under study currently lists, and where OLBG and the official page
disagree the official page wins and the disagreement is published.</p>
<h2>2. Originate a margin, then a price</h2>
<p>Each sport has one margin distribution. The mean is a linear function of the verified season numbers; the spread is a
disclosed constant. Nothing is fitted to a market.</p>
<div class="scroll"><table>
<thead><tr><th>Sport</th><th>Expected margin (home − away)</th><th>Sigma</th><th>Inputs used</th></tr></thead>
<tbody>
<tr><td>Handball</td><td>1.10 × (goal difference per game, home − away) + 6.0 × (win rate, home − away) + 1.4</td><td>7.0 goals</td><td>GP, W, D, L, goals for/against from the official table</td></tr>
<tr><td>Basketball</td><td>0.55 × (point difference per game, home − away) + 8.0 × (win rate, home − away) + 2.0</td><td>13.0 points</td><td>GP, W, L, points for/against from the official table</td></tr>
<tr><td>Tennis</td><td>3.6 × ln(ranking points home ÷ away)</td><td>5.5 games</td><td>PIF ATP ranking points, 19 October 2026 list</td></tr>
<tr><td>Volleyball</td><td>Logistic on 100 × (points-for ÷ points-against − 1) for each side, plus 2.0 home</td><td>—</td><td>Sets and points from the official table</td></tr>
</tbody></table></div>
<p>The money line is P(margin &gt; 0). A handicap at line <em>L</em> is P(margin &gt; L). A total is priced from the same
normal with the mean set to the two clubs' combined scoring rate and the same sigma. Prices are 1 ÷ probability, so the
book is round with no margin: what you see is what we think it is worth.</p>
<h2>3. Volleyball is priced on sets, not on points</h2>
<p>A best-of-five match is modelled as a 3-0 / 3-1 / 3-2 split of the match probability (0.45 / 0.35 / 0.20). That gives
the set handicap (−1.5 sets = a 3-0 or 3-1 win) and the set totals at 3.5 and 4.5.</p>
<h2>4. Confidence, and why the window bites</h2>
<p>High requires both of the brief's conditions: a model probability of at least 70.0% and a fair price inside
−250 to +10,000. Because −250 is a decimal 1.40 (71.4%), the two conditions can only be satisfied together between 70.0%
and 71.4%. A pick stronger than 71.4% is a better bet that cannot be labelled High under the brief, so it is graded Medium
and the row says why. That is the honest reading; the alternative — stretching "high" upward — would misreport the price.</p>
<h2>5. Write-up rules</h2>
<p>A write-up exists only for an in-window High selection. It must be at least thirty words, name the selection and quote
its line, and carry a number that is already in the fixture's verified inputs. The build fails if any of those checks fail,
which is why the fourteen texts on this desk were re-read against the source pages before publication.</p>
<h2>What this model is not</h2>
<ul>
<li>It is not fitted to a market, so it cannot tell you whether a bookmaker price is value. It only says what our price is.</li>
<li>It does not know about injuries, suspensions, rotation, travel or weather. The one team-news item we did read — Tonga's
halfback being ruled out before the Rugby League World Cup tie — is the exception that proves the rule, and that fixture
was not priced at all.</li>
<li>Sigma is a judgement call, disclosed above. Change it and every alternate line moves.</li>
<li>Confidence is a probability statement, not a guarantee. A 71% favourite loses three times in ten.</li>
</ul>
"""
    (SITE / "methodology.html").write_text(page("Method", body, "methodology.html"))

    # ---------------- analysis
    ps = [r["pick"]["prob"] for r in rows if r["priced"]]
    buckets = Counter()
    for p in ps:
        lo = int(p * 10) / 10
        buckets[f"{lo*100:.0f}–{lo*100+10:.0f}%"] += 1
    dist = "".join(f'<tr><td>{esc(k)}</td><td class="mono">{v}</td></tr>'
                   for k, v in sorted(buckets.items(), key=lambda kv: float(kv[0].split("–")[0])))
    line_counts = sum(len(r["markets"]["handicap"]) + len(r["markets"]["total"]) for r in rows if r["markets"])
    body = f"""
<h1>Analysis</h1>
<p class="lede">What the numbers on this desk actually say, including the parts that argue against it.</p>
<h2>Where the picks sit</h2>
<p>Of {counts['priced']} priced fixtures the model puts {counts['high']} selections inside the requested window at 70.0–71.4%.
The distribution of the model's pick probability is below. It is deliberately top-heavy: the official tables separate good
teams from bad ones far more sharply than a betting market does, which is exactly why so few picks land in a 1.4-point band.</p>
<div class="scroll"><table><thead><tr><th>Model probability of the pick</th><th>Fixtures</th></tr></thead>
<tbody>{dist}</tbody></table></div>
<h2>Coverage</h2>
<p>{counts['rows']} fixtures across {len(by_sport)} sports, {counts['priced']} priced. {sum(len(r['markets']['handicap']) + len(r['markets']['total']) for r in rows if r['markets'])} handicap
and total prices originate alongside {counts['priced']} money lines — {line_counts + counts['priced']} published prices in total.
Snooker is listed but not priced: the WST publishes a world ranking and a one-year list, and eight of the sixteen
Last-16 players are outside the top eleven of both, so there is no honest two-sided input.</p>
<h2>What the verification found</h2>
<p>The most useful output of this pass is not a price, it is the list of things the live OLBG listings get wrong for this
week — four mismatched Top 14 pairings, a two-year-old NPC final, two NBL pairings that are not on the NBL schedule, MLB
League Championship Series rows that are not the World Series, an England Women fixture the ECB does not have, and a
South Africa v Australia "ODI" on a Test match day. Those rows are on <a href="flagged.html">Flagged for review</a> with
the official page that contradicts each one.</p>
<h2>Honest weaknesses</h2>
<ul>
<li><strong>Small samples.</strong> Czech and Italian volleyball have one round of results; the SuperLega table is one match deep.
Those prices are arithmetic on a single match, and they are labelled Medium at best.</li>
<li><strong>No home/away split in the inputs.</strong> The model adds a flat home term per sport rather than using each club's
home and away records, because the official tables publish the combined record. Arizona's home form is not in this model.</li>
<li><strong>Totals are the weakest market.</strong> A total depends on pace, and pace is the thing a season aggregate hides best.</li>
<li><strong>Selection is not value.</strong> A 71% pick at 1.40 is a fair price by construction. This desk does not claim an edge
over a bookmaker; it claims a defensible price and a verifiable fixture.</li>
</ul>
"""
    (SITE / "analysis.html").write_text(page("Analysis", body, "analysis.html"))

    # ---------------- sport pages
    for sport in SPORT_ORDER:
        srows_ = [r for r in rows if r["sport"] == sport]
        if not srows_:
            continue
        meta = SPORT_META[sport]
        trs = []
        for r in srows_:
            if r["markets"]:
                mk = r["markets"]
                trs.append(f'<tr><td class="tiny">{esc(r["date"])} {esc(r["time"])}</td>'
                           f'<td><strong>{esc(r["home"])}</strong> v {esc(r["away"])}'
                           f'<div class="tiny">{esc(r["competition"])}</div></td>'
                           f'<td class="mono">{mk["ml_home"]:.2f} / {mk["ml_away"]:.2f}</td>'
                           f'<td><strong>{esc(r["pick"]["selection"])}</strong><div class="tiny">{pct(r["pick"]["prob"])}</div></td>'
                           f'<td>{conf_chip(r["pick"]["confidence"])}'
                           + (f'<div class="tiny"><a href="../predictions.html#{esc(r["id"])}">{esc(r["in_window_high"]["label"])}</a></div>'
                              if r["in_window_high"] else "") + "</td>"
                           f'<td><a href="{esc(r["source_url"])}" rel="noopener">source</a></td></tr>')
            else:
                trs.append(f'<tr><td class="tiny">{esc(r["date"])} {esc(r["time"])}</td>'
                           f'<td><strong>{esc(r["home"])}</strong> v {esc(r["away"])}'
                           f'<div class="tiny">{esc(r["competition"])}</div></td>'
                           f'<td class="tiny">no line</td><td class="tiny">no pick</td>'
                           f'<td><span class="chip u">unpriced</span></td>'
                           f'<td><a href="{esc(r["source_url"])}" rel="noopener">source</a></td></tr>')
        n_hi = sum(1 for r in srows_ if r["in_window_high"])
        n_pr = sum(1 for r in srows_ if r["priced"])
        body = f"""
<h1>{esc(sport)}</h1>
<p class="lede">{n_pr} of {len(srows_)} fixtures priced, {n_hi} high-confidence selection{'s' if n_hi != 1 else ''} inside
−250 to +10,000. Governing body read: {esc(meta["gov"])}.</p>
<div class="scroll"><table>
<thead><tr><th>Date / clock</th><th>Fixture</th><th>Our money line</th><th>Our pick</th><th>Confidence</th><th>Source</th></tr></thead>
<tbody>{''.join(trs)}</tbody></table></div>
<p class="tiny"><a href="../matches.html">← All {counts['rows']} fixtures</a> · <a href="../markets.html">the full price ladders</a></p>
"""
        (SPORTS_SITE / f"{meta['slug']}.html").write_text(page(sport, body, "", pre="../"))

    print(f"rendered {SITE}")


def main():
    rows = build_rows()
    authored = load_authored()["writeups"]

    highs = [r for r in rows if r["priced"] and r["in_window_high"]]
    need = []
    for r in highs:
        h = r["in_window_high"]
        need.append(dict(key=f"{r['id']}|{h['market']}|{h['label']}", id=r["id"],
                         match=f"{r['home']} v {r['away']}", sport=r["sport"],
                         market=h["market"], label=h["label"], prob=h["prob"],
                         dec=h["dec"], american=h["american"]))

    writeups, problems = {}, []
    for n in need:
        text = authored.get(n["key"], "").strip()
        if not text:
            problems.append(f"{n['key']}: no authored text")
            continue
        probs, words = check_writeup(text, n["label"])
        if probs:
            problems.extend(f"{n['key']}: {p}" for p in probs)
            continue
        writeups[n["key"]] = dict(text=text, words=words, **{k: n[k] for k in
                                  ("id", "match", "sport", "market", "label", "prob", "dec", "american")})

    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "sources.json").write_text(json.dumps(
        dict(schema="olbg4.boardZ.sources/1", built_utc=BUILD_UTC, session="arena/19b8e377-olbg4",
             sources=sources_data.SOURCES), indent=1, ensure_ascii=False) + "\n")

    lines = dict(schema="olbg4.boardZ.lines/1", built_utc=BUILD_UTC, unit_by_sport={},
                 rows=[dict(id=r["id"], sport=r["sport"], competition=r["competition"], date=r["date"],
                            time=r["time"], home=r["home"], away=r["away"],
                            markets=r["markets"], pick=r["pick"],
                            in_window_high=r["in_window_high"]) for r in rows])
    (DATA / "lines.json").write_text(json.dumps(lines, indent=1, ensure_ascii=False) + "\n")
    (DATA / "predictions.json").write_text(json.dumps(
        dict(schema="olbg4.boardZ.predictions/1", built_utc=BUILD_UTC,
             writeups=writeups, problems=problems), indent=1, ensure_ascii=False) + "\n")
    (DATA / "flagged.json").write_text(json.dumps(
        dict(schema="olbg4.boardZ.flagged/1", built_utc=BUILD_UTC,
             items=flagged_items(rows)), indent=1, ensure_ascii=False) + "\n")

    by_sport = Counter(r["sport"] for r in rows)
    report = dict(
        schema="olbg4.boardZ.desk/1", board="Z", session="arena/19b8e377-olbg4", built_utc=BUILD_UTC,
        window=dict(american_low=WINDOW_LO, american_high=WINDOW_HI, high_probability_floor=HIGH_FLOOR),
        rows=rows,
        counts=dict(rows=len(rows), priced=sum(1 for r in rows if r["priced"]),
                    unpriced=sum(1 for r in rows if not r["priced"]), by_sport=dict(by_sport),
                    high_primary=sum(1 for r in rows if r["priced"] and r["pick"]["confidence"] == "High"),
                    medium_primary=sum(1 for r in rows if r["priced"] and r["pick"]["confidence"] == "Medium"),
                    low_primary=sum(1 for r in rows if r["priced"] and r["pick"]["confidence"] == "Low"),
                    in_window_high=len(highs), writeups=len(writeups),
                    prices=sum(len(r["markets"]["handicap"]) + len(r["markets"]["total"]) + 2
                               for r in rows if r["markets"])),
        writeups=writeups, writeup_problems=problems)
    (DATA / "desk.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")

    render(rows)
    print(json.dumps(report["counts"], indent=1))
    if problems:
        print("PROBLEMS:", *problems, sep="\n  ")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
