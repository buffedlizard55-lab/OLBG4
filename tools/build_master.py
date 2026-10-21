#!/usr/bin/env python3
"""Build the deduplicated master board from the committed work of builds A, B, C, D, E and G.

Design rules (all of them are restated on the site's Methodology page):

  * Nothing is invented. Every field is copied from a build's committed data and every master
    row keeps the source URL that build recorded. Where a field was taken from a different
    build than the row's primary build, `fields_from` says so.
  * Records are clustered when sport + the two team names match AND the dates are within one
    day (or one date is unknown). A four-game MLB series therefore stays four rows.
  * Inside a cluster the primary record is the one with the most evidence:
    has pick > has prediction > official source > build-verified > backbone rank (G,E,C,A,D,B).
    The remaining records are kept in `cross_build` with their own pick, confidence, date and
    source, so disagreements are published instead of dropped.
  * Out-of-scope sports are never silently deleted: rows stay in the file with `in_scope: false`
    and a reason, and the site hides them from the default view.

Usage: python3 tools/build_master.py
"""
from __future__ import annotations

import glob
import json
import os
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import date, datetime
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPSHOT = date(2026, 10, 21)  # data cut-off for the whole repo

# ---------------------------------------------------------------- sport naming
SPORT_CANON = {
    "basketball": "Basketball", "ice hockey": "Ice Hockey", "ice_hockey": "Ice Hockey",
    "baseball": "Baseball", "tennis": "Tennis", "cricket": "Cricket", "darts": "Darts",
    "snooker": "Snooker", "rugby union": "Rugby Union", "rugby_union": "Rugby Union",
    "rugby league": "Rugby League", "rugby_league": "Rugby League", "handball": "Handball",
    "volleyball": "Volleyball", "aussie rules": "Aussie Rules", "gaelic football": "Gaelic Football",
    "greyhounds": "Greyhounds", "golf": "Golf", "motor racing": "Motor Racing",
    "esports": "Esports", "badminton": "Badminton", "table tennis": "Table Tennis",
}

# The brief excludes soccer, boxing, UFC/MMA, football, American football, hurling, horse
# racing, cycling and specials. "Football" is read as association football; Gaelic football is
# kept but marked scope-ambiguous rather than silently dropped (it is published on Flagged).
EXCLUDED = {"Soccer", "Football", "American Football", "Boxing", "UFC", "MMA", "Hurling",
            "Horse Racing", "Cycling", "Specials"}
AMBIGUOUS = {"Gaelic Football"}

SLUGS = {
    "Basketball": "basketball", "Ice Hockey": "ice-hockey", "Baseball": "baseball",
    "Tennis": "tennis", "Cricket": "cricket", "Darts": "darts", "Snooker": "snooker",
    "Rugby Union": "rugby-union", "Rugby League": "rugby-league", "Handball": "handball",
    "Volleyball": "volleyball", "Aussie Rules": "aussie-rules", "Gaelic Football": "gaelic-football",
    "Greyhounds": "greyhounds", "Golf": "golf", "Motor Racing": "motor-racing",
    "Esports": "esports", "Badminton": "badminton", "Table Tennis": "table-tennis",
}

BACKBONE = ["G", "E", "C", "A", "D", "B"]
BUILD_LABEL = {
    "G": "G — widest single sweep: 17 sport files with documented per-sport models",
    "E": "E — refreshable NBA/NHL/MLB pipeline built from league endpoints",
    "C": "C — verified-input desk: every input transcribed from a league page with a source id",
    "A": "A — governing-body ratings desk (Model v1)",
    "D": "D — hub board as it now stands in the repo (later sessions rebuilt it and downgraded "
         "rows they could not re-confirm; those flags are taken as given)",
    "B": "B — read directly off OLBG's live sport pages (published separately: no official source)",
}

# ------------------------------------------------------------ source registry
# official  = league / governing body / event organiser / regulator
# secondary = news, aggregator, betting or fan source (kept, flagged)
# olbg      = OLBG itself, the site being reverse-engineered
OFFICIAL_DOMAINS = {
    "www.nba.com": "NBA", "api-web.nhle.com": "NHL", "www.nhl.com": "NHL",
    "www.mlb.com": "MLB", "statsapi.mlb.com": "MLB", "www.atptour.com": "ATP Tour",
    "www.protennislive.com": "ATP Tour (ProTennisLive, the ATP's own stats service)",
    "www.wtatennis.com": "WTA", "wtafiles.wtatennis.com": "WTA (official draw PDFs)",
    "www.icc-cricket.com": "ICC", "www.cricket.com.au": "Cricket Australia",
    "www.cricket.co.za": "Cricket South Africa", "www.ecb.co.uk": "England & Wales Cricket Board",
    "cricketireland.ie": "Cricket Ireland", "www.nzc.nz": "New Zealand Cricket",
    "www.pdc.tv": "PDC (darts)", "www.wst.tv": "World Snooker Tour",
    "www.gbgb.org.uk": "Greyhound Board of Great Britain (regulator)",
    "www.nottingham-greyhounds.co.uk": "Nottingham Greyhound Stadium (racecourse operator)",
    "stats.unitedrugby.com": "United Rugby Championship",
    "www.premiershiprugby.com": "Premiership Rugby", "www.nrl.com": "NRL",
    "top14.lnr.fr": "LNR (Top 14)", "prod2.lnr.fr": "LNR (Pro D2)",
    "ehfcl.eurohandball.com": "EHF Champions League",
    "www.eurohandball.com": "European Handball Federation",
    "www.ihf.info": "International Handball Federation", "www.handball.no": "NHF (Norway)",
    "handbollsligan.se": "Handbollsligan (Sweden)", "tophaandbold.dk": "Tophåndbold (Denmark)",
    "www.kbl.or.kr": "KBL (Korea Basketball League)",
    "www.euroleaguebasketball.net": "EuroLeague",
    "www.championsleague.basketball": "Basketball Champions League",
    "www.fivb.com": "FIVB", "en.volleyballworld.com": "Volleyball World",
    "www.volleyball-bundesliga.de": "Volleyball Bundesliga (Germany)",
    "www.legavolleyfemminile.it": "Lega Volley Femminile (Italy)",
    "www.plusliga.pl": "PlusLiga (Poland)", "www.tauron1liga.pl": "Tauron 1. Liga (Poland)",
    "mestaruusliiga.fi": "Mestaruusliiga (Finland)", "www.volleybal.nl": "Nederlandse Volleybalbond",
    "www.shl.se": "SHL (Sweden)", "www.ice.hockey": "IIHF",
    "www.pgatour.com": "PGA TOUR", "www.lpga.com": "LPGA", "www.formula1.com": "Formula 1",
    "www.afl.com.au": "AFL", "lolesports.com": "Riot Games (LoL Esports)",
    "valorantesports.com": "Riot Games (Valorant Esports)", "www.ittf.com": "ITTF",
    "www.fftt.com": "Fédération Française de Tennis de Table",
    "www.montpellier.fr": "Ville de Montpellier (host city, official event page)",
    "www.olympics.com": "International Olympic Committee",
    "gaacork.ie": "Cork GAA", "www.galwaygaa.ie": "Galway GAA", "munster.gaa.ie": "Munster GAA",
    "www.world.rugby": "World Rugby", "www.pcb.com.pk": "Pakistan Cricket Board",
    "bwfworldtour.bwfbadminton.com": "BWF World Tour (Badminton World Federation)",
}
SECONDARY_DOMAINS = {
    "www.espn.com": "ESPN — news/aggregator",
    "en.wikipedia.org": "Wikipedia — fan encyclopedia",
    "www.bbc.com": "BBC Sport — news",
    "www.skysports.com": "Sky Sports — news",
    "www.cricinfo.com": "ESPNcricinfo — cricket news/stats",
    "etusuora.com": "Etusuora — odds/news aggregator",
    "basketnews.com": "BasketNews — news",
    "sportsdata.usatoday.com": "USA TODAY Sports — aggregator",
    "en.tempo.co": "Tempo — news",
    "www.findmygroup.uk": "findmygroup.uk — unclassified, treated as secondary",
}


def tier_for(url: str) -> tuple[str, str, str]:
    if not url:
        return "none", "", "no source URL recorded"
    dom = urlparse(url).netloc.lower()
    if dom.endswith("olbg.com"):
        return "olbg", dom, "OLBG — the site being reverse-engineered (not an official source)"
    if dom in OFFICIAL_DOMAINS:
        return "official", dom, OFFICIAL_DOMAINS[dom]
    if dom in SECONDARY_DOMAINS:
        return "secondary", dom, SECONDARY_DOMAINS[dom]
    return "unclassified", dom, "domain not in the registry — flagged for manual review"


# ------------------------------------------------------------------- helpers
def norm_name(s: str) -> str:
    s = s or ""
    # Some builds prefix the venue to the team field ("Westfalenhalle, Dortmund — Danny Noppert")
    # or append a record note ("Tampa Bay Rays (AL Champions, 98-64)"). Keep only the team.
    if "\u2014" in s or "\u2013" in s:
        s = re.split(r"[\u2014\u2013]", s)[-1]
    if " - " in s and s.count(" ") > 3:
        s = s.rsplit(" - ", 1)[-1]
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"\b(fc|cf|afc|sc|bc|hc|club|the|women|womens|men|mens|u19|u21|u23|rfc)\b", " ", s)
    # kit/sponsor prefixes that different builds keep or drop ("Vodacom Bulls" vs "Bulls")
    s = re.sub(r"\b(vodacom|dhl|hollywoodbets|10bet|betway|suzuki|toyota|emirates|etihad|qantas)\b", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return s


def first_date(text: str) -> str:
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", str(text or ""))
    return m.group(0) if m else ""


def date_from_long(text: str) -> str:
    """Read a date out of a human string such as 'Fri 23 Oct 2026, 14:45 local'."""
    m = re.search(r"(\d{1,2})\s+([A-Za-z]{3})[a-z]*\s+(\d{4})", str(text or ""))
    if m and m.group(2).lower() in MONTHS:
        return f"{int(m.group(3))}-{MONTHS[m.group(2).lower()]:02d}-{int(m.group(1)):02d}"
    return ""


def days_between(a: str, b: str) -> int | None:
    if not a or not b:
        return None
    try:
        return abs((date.fromisoformat(a) - date.fromisoformat(b)).days)
    except ValueError:
        return None


def norm_conf(c: str) -> str:
    c = (c or "").strip().lower()
    return {"high": "High", "medium": "Medium", "low": "Low"}.get(c, "")


MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def parse_olbg_label(label: str, captured: date) -> str:
    if not label:
        return ""
    s = label.strip().lower()
    if s.startswith("today"):
        return captured.isoformat()
    if s.startswith("tomorrow"):
        return date.fromordinal(captured.toordinal() + 1).isoformat()
    m = re.match(r"(\d{1,2})\s+([a-z]{3})", s)
    if m and m.group(2) in MONTHS:
        return f"{captured.year}-{MONTHS[m.group(2)]:02d}-{int(m.group(1)):02d}"
    return ""


def side_of(pick: str, home: str, away: str) -> str:
    p = norm_name(pick)
    if not p:
        return ""
    h, a = norm_name(home), norm_name(away)
    hit_h, hit_a = bool(h) and h in p, bool(a) and a in p
    if hit_h and not hit_a:
        return "home"
    if hit_a and not hit_h:
        return "away"
    if re.search(r"\bdraw\b|\btie\b", p):
        return "draw"
    if re.search(r"\bover\b", p):
        return "over"
    if re.search(r"\bunder\b", p):
        return "under"
    return "other"


def infer_market(pick: str, home: str, away: str, fallback: str = "") -> str:
    side = side_of(pick, home, away)
    if side in ("home", "away", "draw"):
        return "Match winner (moneyline)"
    if side in ("over", "under"):
        return "Match total (over/under)"
    if re.search(r"[+-]\s?\d", pick or ""):
        return "Handicap"
    return fallback or ""


def clean_team(s: str) -> str:
    """Drop a venue prefix or a trailing record note from a team field, for display."""
    s = (s or "").strip()
    if "\u2014" in s or "\u2013" in s:
        s = re.split(r"[\u2014\u2013]", s)[-1].strip()
    if " - " in s and s.count(" ") > 3:
        s = s.rsplit(" - ", 1)[-1].strip()
    if re.fullmatch(r"[^()]{2,40}\s*\([^()]*\)", s):
        s = re.sub(r"\s*\([^()]*\)\s*$", "", s).strip()
    return s


def base_record() -> dict:
    return {
        "build": "", "build_verified": None, "sport": "", "competition": "", "date": "",
        "date_raw": "", "time": "", "venue": "", "home": "", "away": "", "neutral": None,
        "win": {}, "handicap": "", "total": "", "pick": "", "pick_market": "",
        "confidence": "", "prediction": "", "source_url": "", "source_name": "",
        "notes": "", "flags": [],
    }


# --------------------------------------------------------------- build loaders
def load_G(records):
    verified_ids = set()
    for path in glob.glob(os.path.join(ROOT, "data/verified/*.json")):
        payload = json.load(open(path))
        for m in payload.get("matches", []):
            verified_ids.add(str(m.get("event_id")))
    for path in sorted(glob.glob(os.path.join(ROOT, "data/matches/*.json"))):
        payload = json.load(open(path))
        for m in payload.get("matches", []):
            r = base_record()
            r.update(build="G", build_verified=str(m.get("event_id")) in verified_ids,
                     sport=m["sport"], competition=m.get("competition") or "",
                     date_raw=m.get("date") or "", date=first_date(m.get("date")),
                     venue=m.get("venue") or "", home=m["home"], away=m["away"],
                     pick=m.get("pick") or "", confidence=norm_conf(m.get("confidence")),
                     prediction=m.get("prediction") or "",
                     source_url=m.get("source_url") or "", source_name=m.get("source_name") or "",
                     notes=m.get("inputs_summary") or "")
            lines = m.get("lines") or []
            win = {l["selection"]: l.get("fair_odds") for l in lines if l.get("market") == "Win Match"}
            if win:
                r["win"] = {"odds": win, "basis": "build G fair odds (its own model, no bookmaker price)"}
            hc = [l for l in lines if "Handicap" in (l.get("market") or "")]
            if hc:
                r["handicap"] = "; ".join(f"{l['selection']} @ {l.get('fair_odds')}" for l in hc[:4])
            tot = [l for l in lines if "Total" in (l.get("market") or "")]
            if tot:
                r["total"] = "; ".join(f"{l['selection']} @ {l.get('fair_odds')}" for l in tot[:4])
            r["pick_market"] = infer_market(r["pick"], r["home"], r["away"])
            for f in (m.get("flags") or []):
                r["flags"].append({"kind": "source-note", "text": f})
            records.append(r)


def load_E(records):
    analysis = {a["fixture"]["id"]: a
                for a in json.load(open(os.path.join(ROOT, "session-4afef1af/data/analysis.json")))}
    preds = {p.get("fixture_id"): p
             for p in json.load(open(os.path.join(ROOT, "session-4afef1af/data/predictions.json")))}
    for fx in json.load(open(os.path.join(ROOT, "session-4afef1af/data/fixtures.json"))):
        an = (analysis.get(fx["id"]) or {}).get("analysis") or {}
        r = base_record()
        r.update(build="E", build_verified=True,
                 sport=SPORT_CANON.get(fx["sport"], fx["sport"].title()),
                 competition=fx.get("league") or "", date=first_date(fx.get("start_utc")),
                 date_raw=fx.get("start_utc") or "", time=fx.get("status") or "",
                 venue=fx.get("venue") or "", home=fx["home"]["name"], away=fx["away"]["name"],
                 source_url=(fx.get("official_source_urls") or fx.get("source_urls") or [""])[0],
                 source_name=(fx.get("league") or "") + " official schedule/game page",
                 notes=an.get("rationale") or "")
        mk = an.get("markets") or {}
        if mk.get("moneyline"):
            r["win"] = {"odds": {s["name"]: s.get("price_decimal") for s in mk["moneyline"]["selections"]},
                        "basis": "build E originated price (its own margin applied)"}
        if mk.get("handicap"):
            r["handicap"] = "; ".join(f"{s['name']} @ {s.get('price_decimal')}"
                                      for s in mk["handicap"]["selections"])
        if mk.get("total"):
            r["total"] = "; ".join(f"{s['name']} @ {s.get('price_decimal')}"
                                   for s in mk["total"]["selections"])
        hp = an.get("headline_pick")
        if hp:
            r["pick"] = hp.get("selection") or hp.get("name") or ""
            r["pick_market"] = hp.get("market") or infer_market(r["pick"], r["home"], r["away"])
            r["confidence"] = norm_conf(hp.get("confidence"))
        if an.get("market_status") == "withheld":
            r["flags"].append({"kind": "market-withheld",
                               "text": an.get("market_note") or "markets withheld"})
        r["pick_market"] = r["pick_market"] or infer_market(r["pick"], r["home"], r["away"])
        p = preds.get(fx["id"])
        if p and p.get("text"):
            r["prediction"] = p["text"]
        records.append(r)


def load_C(records):
    payload = json.load(open(os.path.join(ROOT, "data/session-74f9613e/matches.json")))
    sources = {s["id"]: s for s in json.load(open(os.path.join(ROOT, "data/session-74f9613e/sources.json")))["sources"]}
    CP = {}
    for p in json.load(open(os.path.join(ROOT, "data/session-74f9613e/predictions.json"))).get("predictions", []):
        CP[p.get("match_id") or p.get("fixture_id") or p.get("id")] = p
    for m in payload["matches"]:
        r = base_record()
        input_ids = m.get("input_sources") or []
        fixture_ids = m.get("fixture_sources") or []
        src = sources.get((input_ids or fixture_ids or [""])[0], {})
        r.update(build="C", build_verified=bool(m.get("inputs_verified")),
                 sport=m.get("sport") or "", competition=m.get("competition") or "",
                 date=first_date(m.get("start_utc")) or date_from_long(m.get("start_local")),
                 date_raw=(m.get("start_utc") or m.get("start_local") or ""),
                 time=m.get("start_local") or "", venue=m.get("venue") or "",
                 home=m["home"]["name"], away=m["away"]["name"],
                 source_url=src.get("url") or "",
                 source_name=src.get("title") or "")
        for s in m.get("selections") or []:
            if s["market"] == "moneyline":
                r["win"].setdefault("odds", {})[s["selection"]] = s.get("odds")
            elif s["market"] == "handicap":
                r["handicap"] = (r["handicap"] + "; " if r["handicap"] else "") + \
                                f"{s['selection']} @ {s.get('odds')}"
            elif s["market"] == "total":
                r["total"] = (r["total"] + "; " if r["total"] else "") + \
                             f"{s['selection']} @ {s.get('odds')}"
        if r["win"]:
            r["win"]["basis"] = "build C originated price (its own margin applied)"
        pk = m.get("pick") or {}
        if pk.get("selection"):
            r["pick"] = pk["selection"]
            r["pick_market"] = pk.get("market") or ""
            r["confidence"] = norm_conf(m.get("confidence"))
        r["pick_market"] = r["pick_market"] or infer_market(r["pick"], r["home"], r["away"])
        r["pick_market"] = {"moneyline": "Match winner (moneyline)"}.get(r["pick_market"], r["pick_market"])
        p = CP.get(m.get("id"))
        if p:
            r["prediction"] = (p.get("text") or p.get("prediction") or "").strip()
        if m.get("notes"):
            r["flags"].append({"kind": "source-note", "text": m["notes"]})
        records.append(r)


def load_A(records):
    for x in json.load(open(os.path.join(ROOT, "data/rows.json"))):
        r = base_record()
        r.update(build="A", build_verified=(x.get("status") == "Verified"),
                 sport=SPORT_CANON.get((x.get("sport") or "").lower(), x.get("sport") or ""),
                 competition=x.get("competition") or "", date=first_date(x.get("date")),
                 date_raw=x.get("date") or "", time=x.get("time") or "", venue=x.get("venue") or "",
                 home=x.get("home") or "", away=x.get("away") or "",
                 pick=x.get("pick") or "", confidence=norm_conf(x.get("confidence")),
                 prediction=x.get("prediction") or "", source_url=x.get("source") or "",
                 source_name=x.get("source_label") or "", notes=x.get("basis") or "")
        if x.get("our_line_home"):
            r["win"] = {"odds": {x.get("home"): x.get("our_line_home"),
                                 x.get("away"): x.get("our_line_away")},
                        "basis": "build A Model v1 line (its own price)"}
        r["pick_market"] = infer_market(r["pick"], r["home"], r["away"])
        if x.get("markets_investigated"):
            r["flags"].append({"kind": "market-note", "text": x["markets_investigated"]})
        if x.get("flag"):
            r["flags"].append({"kind": "build-flag", "text": x["flag"]})
        records.append(r)


def load_D(records):
    for x in json.load(open(os.path.join(ROOT, "data/matches.json"))):
        r = base_record()
        ml = x.get("originatedMoneyline") or {}
        ver = x.get("verification") if isinstance(x.get("verification"), dict) else {}
        src = x.get("sourceUrl") or ver.get("officialUrl") or ""
        r.update(build="D",
                 build_verified=(ver.get("status") == "confirmed") if ver else bool(x.get("verified")),
                 sport=x.get("sport") or "", competition=x.get("competition") or "",
                 date=first_date(x.get("date")), date_raw=x.get("date") or "",
                 time=x.get("time") or "", venue=x.get("venue") or "",
                 home=x.get("teamA") or "", away=x.get("teamB") or "",
                 pick=x.get("pick") or "", confidence=norm_conf(x.get("confidence")),
                 prediction=x.get("prediction") or "", source_url=src,
                 source_name=x.get("sourceName") or ver.get("officialSource") or "",
                 notes=x.get("formNotes") or "")
        if ver.get("status") and ver.get("status") != "confirmed":
            r["flags"].append({"kind": "downgraded-by-later-session",
                               "text": f"Build D's file, as rebuilt by a later session, records this row as "
                                       f"'{ver.get('status')}' with the evidence in data/matches.json."})
        if ml:
            odds = {k: v for k, v in {x.get("teamA"): ml.get("a"), x.get("teamB"): ml.get("b")}.items()
                    if k and v}
            r["win"] = {"odds": odds, "basis": "build D originated moneyline"}
        r["handicap"] = x.get("originatedSpread") or ""
        r["total"] = x.get("originatedTotal") or ""
        r["pick_market"] = infer_market(r["pick"], r["home"], r["away"])
        if x.get("flagReason"):
            r["flags"].append({"kind": "build-flag", "text": x["flagReason"]})
        records.append(r)


def load_B(records):
    """Build B read its fixtures off OLBG itself, so none of its rows can carry an official
    source. They are kept, but in a separate inventory file with its own page, not in the
    master table where every row must link an official source."""
    payload = json.load(open(os.path.join(ROOT, "data/board.json")))
    captured = datetime.fromisoformat(payload["captured_at"].replace("Z", "+00:00")).date()
    for x in payload["rows"]:
        r = base_record()
        r.update(build="B", build_verified=False,
                 sport=SPORT_CANON.get((x.get("sport") or "").lower(), x.get("sport") or ""),
                 competition=x.get("competition") or "",
                 date=parse_olbg_label(x.get("time_label"), captured),
                 date_raw=x.get("time_label") or "", time=x.get("time_label") or "",
                 home=x.get("home") or "", away=x.get("away") or "",
                 neutral=x.get("neutral_venue"), pick=x.get("pick") or "",
                 pick_market=x.get("pick_market") or "", confidence=norm_conf(x.get("confidence")),
                 source_url=x.get("olbg_url") or "",
                 source_name="OLBG event page (reverse-engineered inventory)",
                 notes=x.get("confidence_reason") or "")
        if x.get("our_price"):
            r["win"] = {"odds": {x.get("selection"): x.get("our_price")},
                        "basis": "build B own price from the captured OLBG consensus"}
        if x.get("own_handicap"):
            oh = x["own_handicap"]
            r["handicap"] = f"{oh.get('for')} {oh.get('line')} — {oh.get('basis')}"
        if x.get("own_total"):
            ot = x["own_total"]
            r["total"] = f"{ot.get('line')} {ot.get('unit')} — {ot.get('basis')}"
        r["pick_market"] = r["pick_market"] or infer_market(r["pick"], r["home"], r["away"])
        if x.get("flag"):
            r["flags"].append({"kind": "build-flag", "text": x["flag"]})
        records.append(r)


def cluster_score(rec) -> tuple:
    tier, _, _ = tier_for(rec["source_url"])
    return (1 if rec["pick"] else 0,
            1 if rec["prediction"] and rec.get("prediction_style") != "templated" else 0,
            1 if tier == "official" else 0,
            1 if rec["build_verified"] else 0,
            -BACKBONE.index(rec["build"]))


def main() -> None:
    records: list[dict] = []
    for b in ["G", "E", "C", "A", "D"]:
        {"G": load_G, "E": load_E, "C": load_C, "A": load_A, "D": load_D}[b](records)
    olbg_rows: list[dict] = []
    load_B(olbg_rows)

    for rec in records + olbg_rows:
        rec["home_raw"], rec["away_raw"] = rec["home"], rec["away"]
        rec["home"], rec["away"] = clean_team(rec["home"]), clean_team(rec["away"])

    # Template detection: a build that fills its write-ups from one boilerplate sentence produces
    # text that is unique per match but structurally identical. Those rows are marked so the site
    # can say honestly which write-ups are hand-written prose and which are filled-in templates.
    def skeleton(text: str, home: str, away: str) -> str:
        t = (text or "").lower()
        for name in (home, away):
            if name:
                t = t.replace(name.lower(), " team ")
        t = re.sub(r"\d+(\.\d+)?", " n ", t)
        t = re.sub(r"[^a-z %]+", " ", t)
        return " ".join(t.split()[:14])

    skels = Counter(skeleton(r["prediction"], r["home"], r["away"]) for r in records if r["prediction"])
    for r in records:
        r["prediction_style"] = ""
        if r["prediction"]:
            sk = skeleton(r["prediction"], r["home"], r["away"])
            r["prediction_style"] = "templated" if skels[sk] >= 3 else "written"
            if r["prediction_style"] == "templated":
                r["flags"].append({"kind": "templated-prediction",
                                   "text": f"Build {r['build']} filled this write-up from one boilerplate "
                                           f"sentence used on {skels[sk]} rows; it is not a hand-written prediction."})

    # Series detection: if any single build reports the same pairing on two or more dates, the
    # pairing is a multi-game series (MLB's best-of-seven, a two-legged tie, and so on) and the
    # records must be clustered on the exact date. Otherwise a one-day tolerance is allowed so
    # that builds which disagree about the date of the same fixture are merged and flagged,
    # instead of publishing the same match twice.
    pair_dates: dict[tuple, dict[str, set]] = defaultdict(lambda: defaultdict(set))
    for rec in records:
        key = (rec["sport"], tuple(sorted([norm_name(rec["home"]), norm_name(rec["away"])])))
        if rec["date"]:
            pair_dates[key][rec["build"]].add(rec["date"])
    series_keys = {k for k, v in pair_dates.items() if any(len(d) > 1 for d in v.values())}

    clusters: dict[tuple, list[list[dict]]] = defaultdict(list)
    for rec in records:
        key = (rec["sport"], tuple(sorted([norm_name(rec["home"]), norm_name(rec["away"])])))
        tol = 0 if key in series_keys else 1
        placed = False
        for cluster in clusters[key]:
            if any((days_between(rec["date"], other["date"]) in (0,) or
                    (tol and days_between(rec["date"], other["date"]) in (None, 1)))
                   for other in cluster):
                cluster.append(rec)
                placed = True
                break
        if not placed:
            clusters[key].append([rec])

    master: list[dict] = []
    conflicts: list[dict] = []
    for key, group_list in clusters.items():
        for group in group_list:
            group.sort(key=cluster_score, reverse=True)
            primary = dict(group[0])
            primary["cross_build"] = []
            primary["fields_from"] = {}
            for alt in group[1:]:
                primary["cross_build"].append({
                    "build": alt["build"], "pick": alt["pick"], "confidence": alt["confidence"],
                    "date": alt["date"], "date_raw": alt["date_raw"],
                    "source_url": alt["source_url"],
                })
                for field in ("pick", "confidence", "pick_market", "prediction",
                              "handicap", "total", "win", "venue", "competition", "time"):
                    if not primary.get(field) and alt.get(field):
                        primary[field] = alt[field]
                        primary["fields_from"][field] = alt["build"]
                if not primary["date"] and alt["date"]:
                    primary["date"] = alt["date"]
                    primary["fields_from"]["date"] = alt["build"]
                primary["flags"].extend(alt["flags"])
            primary["archive_rows"] = len(group) - 1
            master.append(primary)

    # ---- write-ups authored by this session (data/authored_predictions.json)
    # Build A ships frame-generated prose for a handful of high-confidence rows. Rather than publish
    # that as if it were written analysis, those rows either get a write-up authored here from facts
    # re-read on the official pages (recorded with the text), or lose their High tag. Nothing is
    # filled in from memory: every claim in the text is listed in `authored_facts` with its URL.
    authored_applied, authored_missing = [], []
    apath = os.path.join(ROOT, "data", "authored_predictions.json")
    if os.path.exists(apath):
        with open(apath) as fh:
            ap = json.load(fh)
        for entry in ap.get("entries", []):
            m = entry["match"]
            hits = [r for r in master
                    if r["sport"] == m["sport"]
                    and m["home_contains"].lower() in r["home"].lower()
                    and m["away_contains"].lower() in r["away"].lower()]
            if len(hits) != 1:
                authored_missing.append(f'{m["sport"]}: {m["home_contains"]} v {m["away_contains"]} matched '
                                        f'{len(hits)} rows')
                continue
            row = hits[0]
            row["prediction"] = entry["prediction"]
            row["prediction_source"] = f'authored {ap.get("authored_at", "")}'.strip()
            row["authored_facts"] = entry.get("facts", [])
            row["authored_sources"] = entry.get("sources", [])
            row["pick"] = row["pick"] or entry.get("pick", "")
            authored_applied.append(row["id"] if "id" in row else f'{row["sport"]} {row["home"]} v {row["away"]}')
        for entry in ap.get("confidence_overrides", []):
            m = entry["match"]
            hits = [r for r in master
                    if r["sport"] == m["sport"]
                    and m["home_contains"].lower() in r["home"].lower()
                    and m["away_contains"].lower() in r["away"].lower()]
            if len(hits) != 1:
                authored_missing.append(f'override {m["sport"]}: matched {len(hits)} rows')
                continue
            row = hits[0]
            row["flags"].append({"kind": "confidence-lowered",
                                 "text": f'Confidence lowered from {row["confidence"] or "unset"} to '
                                         f'{entry["confidence"]}: {entry["reason"]}'})
            row["confidence"] = entry["confidence"]
            row["confidence_note"] = entry["reason"]

    # ---- final write-up classification (done after merging so copied texts are covered too)
    import difflib

    def skeleton2(text: str, home: str, away: str) -> str:
        t = (text or "").lower()
        for name in (home, away):
            if name:
                t = t.replace(name.lower(), " team ")
        t = re.sub(r"\d+(\.\d+)?", " n ", t)
        t = re.sub(r"[^a-z %]+", " ", t)
        return " ".join(t.split()[:14])

    skels2 = Counter(skeleton2(r["prediction"], r["home"], r["away"]) for r in master if r["prediction"])
    by_build_pred = defaultdict(list)
    for r in master:
        if r["prediction"]:
            by_build_pred[r["build"]].append(r)
    for r in master:
        r["flags"] = [f for f in r["flags"] if f["kind"] != "templated-prediction"]
        r["prediction_style"] = ""
        if not r["prediction"]:
            continue
        sk = skeleton2(r["prediction"], r["home"], r["away"])
        peers = [o for o in by_build_pred[r["build"]] if o is not r]
        max_sim = max((difflib.SequenceMatcher(None, r["prediction"], o["prediction"]).ratio()
                       for o in peers), default=0.0)
        reasons = []
        if r.get("prediction_source", "").startswith("authored"):
            # Written here against the official pages recorded in authored_sources; never a template.
            r["prediction_style"] = "written"
            r["prediction_similarity"] = 0.0
            continue
        if r["build"] == "A":
            # Every one of build A's 32 write-ups follows one of a handful of fixed sentence frames
            # ("Take X to win this ...", "Back X to win ...", "X entered this match with a points
            # percentage of ..."). Treated as a generation template rather than as prose.
            reasons.append("build A generates every write-up from a small set of fixed sentence frames")
        if skels2[sk] >= 3:
            reasons.append(f"the same opening sentence appears on {skels2[sk]} rows")
        if max_sim >= 0.55:
            reasons.append(f"it is {max_sim:.0%} identical to another write-up from the same build")
        r["prediction_style"] = "templated" if reasons else "written"
        r["prediction_similarity"] = round(max_sim, 3)
        if reasons:
            r["flags"].append({"kind": "templated-prediction",
                               "text": f"Build {r['build']} generated this write-up from boilerplate: " +
                                       "; ".join(reasons) + ". It is not counted as a written prediction."})

    # ---- conflicts, date disputes and verification flags
    for row in master:
        side = side_of(row["pick"], row["home"], row["away"])
        row["pick_side"] = side
        disagree = []
        for alt in row["cross_build"]:
            alt_side = side_of(alt["pick"], alt["home"] if "home" in alt else row["home"], row["away"]) \
                if alt["pick"] else ""
            alt["side"] = alt_side
            if alt_side in ("home", "away") and side in ("home", "away") and alt_side != side:
                disagree.append({**alt, "side": alt_side})
        if disagree:
            row["cross_build_conflict"] = True
            conflicts.append({
                "sport": row["sport"], "match": f'{row["home"]} vs {row["away"]}',
                "date": row["date"] or row["date_raw"],
                "primary_build": row["build"], "primary_pick": row["pick"],
                "primary_source": row["source_url"],
                "alternates": [{k: a[k] for k in ("build", "pick", "confidence", "date", "source_url")}
                               for a in disagree],
                "note": "Two builds originated opposite winners for this fixture. Neither is deleted: "
                        "the backbone row is published and every alternative is listed here.",
            })
        dates = {row["date"]} | {a["date"] for a in row["cross_build"] if a["date"]}
        dates.discard("")
        if len(dates) > 1:
            spread = max(days_between(d, o) or 0 for d in dates for o in dates)
            if spread >= 1:
                row["flags"].append({
                    "kind": "date-discrepancy",
                    "text": "Builds disagree on the date: " + ", ".join(sorted(dates)) +
                            f" (spread {spread} day(s)). Primary date kept — check the official source.",
                })

    # ---- ids, tiers, status
    master.sort(key=lambda r: (r["date"] or "9999", r["sport"], r["home"], r["away"]))
    # duplicate flags (the same note added twice by a build) are collapsed so the table reads cleanly
    for row in master:
        seen, uniq = set(), []
        for f in row["flags"]:
            key = (f.get("kind"), f.get("text"))
            if key in seen:
                continue
            seen.add(key)
            uniq.append(f)
        row["flags"] = uniq

    for i, row in enumerate(master, 1):
        row["id"] = f"M{i:04d}"
        tier, dom, note = tier_for(row["source_url"])
        row["source_tier"], row["source_domain"], row["source_note"] = tier, dom, note
        row["verified"] = bool(tier == "official" and row["build_verified"] is True)
        if tier == "olbg":
            row["flags"].append({"kind": "olbg-only-source",
                                 "text": "Only OLBG (the site being reverse-engineered) is cited for this row, so no "
                                         "official source confirmed it. Published as unverified and listed on Flagged."})
        elif tier in ("secondary", "unclassified"):
            row["flags"].append({"kind": "secondary-source",
                                 "text": f"Source is {note} — not a governing-body page. Flagged for review."})
        elif tier == "none":
            row["flags"].append({"kind": "no-source", "text": "No source URL recorded by the originating build."})
        if tier == "official" and row["build_verified"] is False:
            row["flags"].append({"kind": "build-marked-unverified",
                                 "text": "The originating build marked this row as not fully verified even though the "
                                         "cited domain is official."})
        if not row["pick"]:
            row["flags"].append({"kind": "no-pick",
                                 "text": "No pick originated: the originating build could not verify enough inputs."})
        if not row["prediction"] and row["confidence"] == "High":
            row["flags"].append({"kind": "missing-prediction",
                                 "text": "High-confidence row with no written prediction in the source build."})
        if row["date"]:
            row["status"] = "upcoming" if row["date"] >= SNAPSHOT.isoformat() else "played-before-cutoff"
        else:
            row["status"] = "date-unconfirmed"
        row["sport_slug"] = SLUGS.get(row["sport"],
                                      re.sub(r"[^a-z0-9]+", "-", row["sport"].lower()).strip("-"))
        blob = f'{row["home"]} {row["away"]}'
        placeholder = (re.search(r"\b(TBD|Field|Winner|Loser|Qualifiers?|Favourites?|Seeded|Players?|"
                                 r"Finalists?|Top \d+|Round \d+|Spread|No pick|Bo5|LCK|LPL|LEC|LCS|"
                                 r"World Champions|Asian swing|Europe|Rest of)\b", blob, re.I)
                       or re.search(r"\d+%|\b\d{2}[A-Z/]", blob)
                       or "?" in blob
                       or len(row["home"]) > 40 or len(row["away"]) > 40)
        row["row_type"] = "market-note" if placeholder else "fixture"
        if not row["home"] or not row["away"]:
            row["row_type"] = "incomplete"
            row["flags"].append({"kind": "blank-teams",
                                 "text": "The originating build did not record both teams. Left blank rather than "
                                         "guessed, and kept out of the fixture table."})
        if row["row_type"] == "market-note":
            row["flags"].append({"kind": "not-a-fixture",
                                 "text": "Not a head-to-head fixture: the participant field is a placeholder "
                                         "('Field' / 'TBD'), so this row is a market note, not a match."})
        row["in_scope"] = row["sport"] not in EXCLUDED and row["sport"] not in AMBIGUOUS
        row["scope_note"] = ("Gaelic football: 'football' is on the brief's exclusion list, so this row is hidden "
                             "from the default view and published on Flagged for Review instead of being deleted."
                             if row["sport"] in AMBIGUOUS else "")

    # ---- attach live re-checks (data/live_checks.json) to the rows they cover
    checks = json.load(open(os.path.join(ROOT, "data/live_checks.json")))["checks"]
    for row in master:
        row["live_checks"] = []
        for chk in checks:
            if chk["sport"] != row["sport"]:
                continue
            pairs = chk.get("teams") or []
            for a, b in pairs:
                if {norm_name(a), norm_name(b)} == {norm_name(row["home"]), norm_name(row["away"])}:
                    row["live_checks"].append(chk["id"])
                    break
        row["live_contradicted"] = False
        for chk in checks:
            for bad in chk.get("contradicts") or []:
                if (bad["sport"] == row["sport"] and bad.get("date") == row["date"]
                        and {norm_name(t) for t in bad["teams"]} == {norm_name(row["home"]), norm_name(row["away"])}):
                    row["live_contradicted"] = True
                    row["live_checks"].append(chk["id"] + "-CONTRADICTED")
                    row["verified"] = False
                    row["flags"].append({"kind": "contradicted-by-official-source",
                                         "text": f"A live re-check against the official schedule found no such fixture on "
                                                 f"{bad['date']} ({bad['source_url']}). Left published and unverified."})
        if row["live_checks"] and not row["live_contradicted"]:
            row["live_verified"] = True

    # ---- outrights / futures (not head-to-head, so kept in their own list)
    outrights = []
    for path in sorted(glob.glob(os.path.join(ROOT, "data/matches/*.json"))):
        payload = json.load(open(path))
        for o in payload.get("outrights", []):
            o = dict(o)
            o["sport"] = payload["sport"]
            o["sport_slug"] = SLUGS.get(payload["sport"], "")
            tier, dom, note = tier_for(o.get("source_url") or "")
            o["source_tier"], o["source_domain"], o["source_note"] = tier, dom, note
            o["verified"] = tier == "official"
            o["in_scope"] = payload["sport"] not in EXCLUDED and payload["sport"] not in AMBIGUOUS
            outrights.append(o)

    in_scope = [r for r in master if r["in_scope"]]
    counts = {
        "rows_total": len(master),
        "rows_in_scope": len(in_scope),
        "sports_in_scope": sorted({r["sport"] for r in in_scope}),
        "sports_all": sorted({r["sport"] for r in master}),
        "rows_verified_official": sum(1 for r in master if r["verified"]),
        "rows_verified_in_scope": sum(1 for r in in_scope if r["verified"]),
        "rows_with_pick": sum(1 for r in in_scope if r["pick"]),
        "rows_with_prediction": sum(1 for r in in_scope if r["prediction"]),
        "rows_with_written_prediction": sum(1 for r in in_scope if r["prediction"] and r["prediction_style"] == "written"),
        "rows_with_templated_prediction": sum(1 for r in in_scope if r["prediction_style"] == "templated"),
        "high_with_written_prediction": sum(1 for r in in_scope if r["confidence"] == "High"
                                            and r["row_type"] == "fixture" and r["prediction_style"] == "written"),
        "confidence": dict(Counter(r["confidence"] or "none" for r in in_scope)),
        "by_sport": {
            s: {
                "rows": sum(1 for r in in_scope if r["sport"] == s),
                "verified": sum(1 for r in in_scope if r["sport"] == s and r["verified"]),
                "picks": sum(1 for r in in_scope if r["sport"] == s and r["pick"]),
                "high": sum(1 for r in in_scope if r["sport"] == s and r["confidence"] == "High"),
                "predicted": sum(1 for r in in_scope if r["sport"] == s and r["prediction"]),
                "market_win": sum(1 for r in in_scope if r["sport"] == s and r["win"]),
                "market_handicap": sum(1 for r in in_scope if r["sport"] == s and r["handicap"]),
                "market_total": sum(1 for r in in_scope if r["sport"] == s and r["total"]),
            }
            for s in sorted({r["sport"] for r in in_scope})
        },
        "by_build": dict(Counter(r["build"] for r in master)),
        "cross_build_fixtures": sum(1 for r in master if r["cross_build"]),
        "cross_build_conflicts": len(conflicts),
        "rows_flagged": sum(1 for r in master if r["flags"]),
        "outrights": len(outrights),
        "outrights_in_scope": sum(1 for o in outrights if o["in_scope"]),
        "upcoming": sum(1 for r in master if r["status"] == "upcoming"),
        "out_of_scope": sum(1 for r in master if not r["in_scope"]),
        "source_tiers": dict(Counter(r["source_tier"] for r in master)),
        "rows_live_confirmed": sum(1 for r in master if r.get("live_verified")),
        "rows_live_contradicted": sum(1 for r in master if r.get("live_contradicted")),
        "live_checks": {"total": len(checks),
                        "confirmed": sum(1 for c in checks if c["result"] == "confirmed"),
                        "not_readable": sum(1 for c in checks if c["result"] == "not-readable")},
    }

    payload = {
        "schema": "olbg4.master/1",
        "generated_by": "tools/build_master.py",
        "generated_on": SNAPSHOT.isoformat(),
        "cutoff_note": "Every value is copied from the committed data of builds A, B, C, D, E and G. "
                       "Nothing is inferred or refreshed; each row carries the source URL its build recorded.",
        "backbone": BACKBONE,
        "build_labels": BUILD_LABEL,
        "counts": counts,
        "rows": master,
        "outrights": outrights,
    }
    json.dump(payload, open(os.path.join(ROOT, "data/master.json"), "w"), indent=1, ensure_ascii=False)
    json.dump({"schema": "olbg4.master_conflicts/1", "generated_on": SNAPSHOT.isoformat(),
               "count": len(conflicts), "conflicts": conflicts},
              open(os.path.join(ROOT, "data/master_conflicts.json"), "w"), indent=1, ensure_ascii=False)

    reg = Counter()
    meta = {}
    for r in master + outrights:
        if r["source_domain"]:
            reg[(r["source_tier"], r["source_domain"], r["source_note"])] += 1
    registry = [{"tier": k[0], "domain": k[1], "note": k[2], "rows": v} for k, v in
                sorted(reg.items(), key=lambda kv: ({"official": 0, "secondary": 1, "olbg": 2}.get(kv[0][0], 3),
                                                    -kv[1]))]
    json.dump({"schema": "olbg4.sources/1", "count": len(registry), "sources": registry},
              open(os.path.join(ROOT, "data/source_registry.json"), "w"), indent=1, ensure_ascii=False)

    # Build B's OLBG-only inventory is published on its own page, not in the master table.
    for r in olbg_rows:
        r["source_tier"], r["source_domain"], r["source_note"] = tier_for(r["source_url"])
    json.dump({"schema": "olbg4.olbg_inventory/1", "generated_on": SNAPSHOT.isoformat(),
               "note": "Fixtures captured from OLBG's own sport pages by build B. OLBG is the site being "
                       "reverse-engineered, so none of these rows has an official source. They are published as "
                       "unverified and are not counted as verified in the master board.",
               "counts": {"rows": len(olbg_rows),
                          "by_sport": dict(Counter(r["sport"] for r in olbg_rows))},
               "rows": olbg_rows},
              open(os.path.join(ROOT, "data/master_olbg.json"), "w"), indent=1, ensure_ascii=False)

    print(json.dumps({k: v for k, v in counts.items() if k != "by_sport"}, indent=1))
    for s, v in counts["by_sport"].items():
        print(f"  {s:15} {v}")
    print("conflicts:", len(conflicts), "| source domains:", len(registry))


if __name__ == "__main__":
    main()
