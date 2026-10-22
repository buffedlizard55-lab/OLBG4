#!/usr/bin/env python3
"""Board Y (session c4fda15e) - reconcile OLBG rows with official records, originate lines, grade.

Inputs (all committed in this repo):
  data/session-c4fda15e/olbg_inventory.json   (parse_olbg.py, from the runner capture)
  data/session-c4fda15e/official.json         (official.py, from runner captures)
  data/session-c4fda15e/official_manual.json  (official pages read with the page reader; URL per block)
Output:
  data/session-c4fda15e/desk.json
Rules: a value not printed by an official source stays None and the row is flagged; lines are
only originated from official numeric inputs; every row carries at least one official URL or is
marked 'unverified'.
"""
from __future__ import annotations

import json
import math
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import model as M  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(ROOT, "data", "session-c4fda15e")
INV = json.load(open(os.path.join(DATA, "olbg_inventory.json"), encoding="utf-8"))
OFF = json.load(open(os.path.join(DATA, "official.json"), encoding="utf-8"))
MAN = {b["id"]: b for b in json.load(open(os.path.join(DATA, "official_manual.json"), encoding="utf-8"))["blocks"]}
CAPTURE_UTC = INV["manifest_generated_utc"]  # OLBG capture time
AS_OF = "2026-10-22T04:10:00Z"               # desk build reference time (rows starting before this are 'started')


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]", "", s.lower().replace("-", " ")).strip()


def surname(n: str) -> str:
    parts = norm(n).split()
    return parts[-1] if parts else ""


def split_event(name: str):
    for sep in (" vs ", " v ", " @ "):
        if sep in name:
            a, b = name.split(sep, 1)
            return a.strip(), b.strip(), sep.strip()
    return name, "", ""


# =============================================================================== official fixture registry
FIX = []  # each: dict(sport, competition, a, b, home(optional), utc, utc_basis, round, venue, url, source_name, capture, extra)


def add(**k):
    k.setdefault("extra", {})
    FIX.append(k)


# ---- tennis ATP (manual transcriptions + ProTennisLive PDFs)
almaty = MAN["atp_almaty_oop_d6"]
for a, b, sa, sb, utc, basis in [
        ("Terence Atmane", "Mattia Bellucci", "", "", "2026-10-22T06:30:00Z", "Starts at 11:30 local (UTC+5)"),
        ("Tomas Machac", "Karen Khachanov", "", "5", "2026-10-22T08:00:00Z", "Not before 13:00 local"),
        ("Daniil Medvedev", "Sho Shimabukuro", "1", "", None, "Followed by (no fixed time), 22 Oct"),
        ("Alexander Bublik", "Fabian Marozsan", "3", "", "2026-10-22T14:30:00Z", "Not before 19:30 local")]:
    add(sport="Tennis", competition="ATP Almaty — R16", a=a, b=b, seed_a=sa, seed_b=sb, utc=utc, utc_basis=basis, date="2026-10-22",
        url=almaty["url"], source_name=almaty["source_name"])
add(sport="Tennis", competition="ATP Almaty — QF", a="Stefanos Tsitsipas", b="James Duckworth", seed_a="7", seed_b="", utc=None,
    utc_basis="Quarter-final; 23 Oct order of play not yet published at capture", date=None,
    url=MAN["atp_almaty_draw"]["url"], source_name=MAN["atp_almaty_draw"]["source_name"], partial=True)
bru = MAN["atp_brussels_oop"]
for a, b, sa, sb, utc, basis in [
        ("Raphael Collignon", "Jiri Lehecka", "", "2", "2026-10-22T11:30:00Z", "Centre Court, starts at 13:30 CEST"),
        ("David Goffin", "Alex Michelsen", "WC", "5", None, "Centre Court, followed by (no fixed time)"),
        ("Damir Dzumhur", "Zizou Bergs", "", "6", "2026-10-22T15:00:00Z", "Centre Court, not before 17:00 CEST")]:
    add(sport="Tennis", competition="ATP Brussels — R16", a=a, b=b, seed_a=sa, seed_b=sb, utc=utc, utc_basis=basis, date="2026-10-22",
        url=bru["url"], source_name=bru["source_name"])
lyo = MAN["atp_lyon_oop"]
for a, b, sa, sb, utc, basis in [
        ("Valentin Vacherot", "Luca Van Assche", "3", "", "2026-10-22T12:00:00Z", "Court Central, not before 14:00 CEST"),
        ("Pierre-Hugues Herbert", "Taylor Fritz", "Q", "2", None, "Court Central, followed by (no fixed time)"),
        ("Flavio Cobolli", "Stan Wawrinka", "1", "WC", "2026-10-22T17:00:00Z", "Court Central, not before 19:00 CEST"),
        ("Kyrian Jacquet", "Brandon Nakashima", "Q", "5", None, "Court Central, followed by (no fixed time)"),
        ("Borna Gojo", "Daniel Altmaier", "Q", "", None, "Court 1, third match (followed by)")]:
    add(sport="Tennis", competition="ATP Lyon — R16", a=a, b=b, seed_a=sa, seed_b=sb, utc=utc, utc_basis=basis, date="2026-10-22",
        url=lyo["url"], source_name=lyo["source_name"])

# ---- tennis WTA (official match feeds)
for key, label in (("wta_osaka", "WTA Osaka"), ("wta_ningbo", "WTA Ningbo")):
    T = OFF[key]
    for m in T["matches"]:
        t = m["time"] or ""
        fixed = None
        basis = ""
        if m["state"] == "U":
            if "T23:59" in t:
                basis = "Scheduled 22 Oct, no fixed time on the official feed"
            else:
                dt = datetime.fromisoformat(t)
                fixed = dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                basis = f"Official feed start {t}"
        elif m["state"] in ("P", "M"):
            basis = f"In progress on the official feed at capture (state {m['state']})"
        elif m["state"] == "F":
            basis = f"Completed: {m['result']}"
        rnd = " — Round of 16 (official order of play, Day 4)" if m["state"] in ("U", "P", "M") else ""
        add(sport="Tennis", competition=f"{label}{rnd}", a=m["a"], b=m["b"], seed_a=m["seed_a"], seed_b=m["seed_b"],
            utc=fixed, utc_basis=basis, date=(t[:10] if t else None), state=m["state"], result=m["result"],
            url=(T["page_url"].replace("/scores", "/order-of-play") if m["state"] in ("U", "P", "M") else T["page_url"]),
            source_name=(f"{label} official order of play + match feed" if m["state"] in ("U", "P", "M") else f"{label} official match feed (api.wtatennis.com)"),
            capture=T["source"]["capture"])

osk = MAN["wta_osaka_oop_d4"]
add(sport="Tennis", competition="WTA Osaka — QF", a="Talia Gibson", b="Ashlyn Krueger", seed_a="4", seed_b="", utc=None,
    utc_basis="Both players won their round-of-16 matches on 21 Oct (official WTA match feed); QF order of play not yet published at capture",
    date=None, url="https://www.wtatennis.com/tournaments/405/osaka/2026/scores", source_name="WTA Osaka official match feed (api.wtatennis.com)", partial=True)

# ---- darts (PDC article)
pdc = MAN["pdc_ec2026_schedule"]
for sess in pdc["sessions"]:
    for i, m in enumerate(sess["order"], 1):
        a, b = m.split(" v ")
        add(sport="Darts", competition="PDC European Championship — Round One", a=a.strip(), b=b.strip(), utc=None,
            utc_basis=f"{sess['date']} session {sess['window_utc']} ({sess['window_local']}), match {i} of 8 in order",
            date=sess["date"], url=pdc["url"], source_name=pdc["source_name"], extra={"order": i, "window_utc": sess["window_utc"]})

# ---- NBA (NBA.com schedule page)
nba = MAN["nba_schedule_wk1"]
for g in nba["games"]:
    add(sport="Basketball", competition="NBA", a=g["away"], b=g["home"], home=g["home"], utc=g["utc"], utc_basis=g["time_et"],
        date=g["utc"][:10], venue=g["venue"], url=g["game_url"], source_name="NBA.com schedule / game page",
        extra={"schedule_url": nba["url"]})

# ---- EuroLeague (official API)
EL = OFF["euroleague_2026"]
for g in EL["games"]:
    if "2026-10-21" <= g["utc"][:10] <= "2026-10-24" and not g["played"]:
        add(sport="Basketball", competition=f"EuroLeague — Round {g['round']}", a=g["home"], b=g["away"], home=g["home"], utc=g["utc"],
            utc_basis="official utcDate", date=g["utc"][:10], venue=g["venue"],
            url="https://www.euroleaguebasketball.net/en/euroleague/game-center/", source_name="EuroLeague official API (api-live.euroleague.net)",
            capture=EL["source"]["capture"], extra={"game_code": g["code"], "api_url": EL["source"]["url"]})

# ---- rugby LNR
for key, comp in (("prod2_calendar", "Pro D2"), ("top14_calendar", "Top 14")):
    C = OFF[key]
    for f in C["fixtures"]:
        add(sport="Rugby Union", competition=f"{comp} — Journée {C['round']}", a=f["home"], b=f["away"], home=f["home"], utc=f["utc"],
            utc_basis=f"{f['local_time']} Paris time", date=f["date"], url=C["source"]["url"], source_name=f"LNR official {comp} calendar",
            capture=C["source"]["capture"], extra={"home_pos": f["home_pos"], "away_pos": f["away_pos"]})
urc = MAN["urc_fixtures_article"]
for f in urc["fixtures"]:
    add(sport="Rugby Union", competition="United Rugby Championship", a=f["home"], b=f["away"], home=f["home"], utc=f["utc"],
        utc_basis=f"KO {f['ko']}", date=f["date"], venue=f["venue"], url=urc["url"], source_name=urc["source_name"])

# ---- MLB
for g in OFF["mlb"]["postseason"]:
    if g["type"] == "W" and g["game_no"] == 1:
        add(sport="Baseball", competition="MLB World Series — Game 1", a=g["away"], b=g["home"], home=g["home"], utc=g["utc"],
            utc_basis="official gameDate", date=g["utc"][:10], venue=g["venue"],
            url=f"https://www.mlb.com/gameday/{g['pk']}", source_name="MLB Stats API schedule (statsapi.mlb.com)",
            capture=OFF["mlb"]["schedule_source"]["capture"], extra={"pk": g["pk"], "home_pp": g["home_pp"], "away_pp": g["away_pp"]})

# ---- Liiga
for g in OFF["liiga"]["games"]:
    if g["utc"].startswith("2026-10-22"):
        add(sport="Ice Hockey", competition="Liiga (Finland)", a=g["home"], b=g["away"], home=g["home"], utc=g["utc"], utc_basis="official start",
            date=g["utc"][:10], url="https://liiga.fi/fi/ohjelma", source_name="Liiga official API (liiga.fi/api/v2/games)",
            capture=OFF["liiga"]["games_source"]["capture"], extra={"game_id": g["id"]})

# =============================================================================== matching
ALIASES = {  # OLBG label token -> official token (only spelling/branding differences; checked by hand)
    "okc thunder": "oklahoma city thunder", "phi 76ers": "philadelphia 76ers", "cle cavaliers": "cleveland cavaliers",
    "den nuggets": "denver nuggets", "ny knicks": "new york knicks", "bos celtics": "boston celtics", "hou rockets": "houston rockets",
    "sa spurs": "san antonio spurs", "tb rays": "tampa bay rays", "mil brewers": "milwaukee brewers",
    "maccabi tel aviv": "maccabi rapyd tel aviv", "panathinaikos": "panathinaikos aktor athens", "baskonia": "kosner baskonia vitoria gasteiz",
    "anadolu efes": "anadolu efes istanbul", "besiktas": "besiktas istanbul", "bayern munich": "fc bayern munich", "bc dubai": "dubai basketball",
    "zalgiris": "zalgiris kaunas", "asvel lyon villeurbanne": "ldlc asvel villeurbanne",
    "montauban": "us montauban", "oyonnax": "oyonnax rugby", "narbonne": "rc narbonnais", "brive": "ca brive", "aurillac": "stade aurillacois",
    "nevers": "uson nevers", "agen": "su agen", "nissa": "nissa rugby", "soyaux angouleme": "soyaux angouleme xv", "dax": "us dax",
    "valence romans": "valence romans", "colomiers": "colomiers rugby", "grenoble": "fc grenoble rugby", "biarritz": "biarritz olympique pb",
    "provence": "provence rugby", "beziers": "as beziers herault", "toulouse": "stade toulousain", "perpignan": "usa perpignan",
    "bayonne": "aviron bayonnais", "lyon": "lou rugby", "la rochelle": "stade rochelais", "bordeaux": "union bordeaux begles",
    "connacht": "connacht", "zebre parma": "zebre parma", "bulls": "vodacom bulls", "ulster": "ulster", "stormers": "dhl stormers", "scarlets": "scarlets",
    "jyp": "jyp", "hpk": "hpk",
}


def canon(x: str) -> str:
    n = norm(x)
    return ALIASES.get(n, n)


def match_fixture(row):
    a, b, sep = split_event(row["event_name"])
    sp = row["sport"]
    cands = [f for f in FIX if f["sport"] == sp]
    if sp in ("Tennis", "Darts"):
        sa, sb = surname(a), surname(b)
        for f in cands:
            fa, fb = surname(f["a"]), surname(f["b"])
            if {sa, sb} == {fa, fb}:
                return f, (sa == fa)
        return None, None
    ca, cb = canon(a), canon(b)
    for f in cands:
        fa, fb = norm(f["a"]), norm(f["b"])
        if {ca, cb} == {fa, fb}:
            return f, (ca == fa)
    return None, None


# =============================================================================== models
def tennis_line(f, row):
    tour = "WTA" if f["competition"].startswith("WTA") else "ATP"
    R = OFF["wta_rankings" if tour == "WTA" else "atp_rankings"]["players"]
    ra, rb = R.get(f["a"]), R.get(f["b"])
    if not ra or not rb:
        return None
    p = M.power_ratio(ra["points"], rb["points"], 0.9)
    s = M.solve_unit(p, 2)
    sets = M.race_markets(p, 2, handicaps=(1.5,), totals=(2.5,))
    reliable = max(ra["rank"], rb["rank"]) <= 200
    return {"model": "ranking-points power model (alpha 0.9) on official rankings of 19 Oct 2026; set markets from an i.i.d. set model",
            "p_a": round(p, 4), "p_b": round(1 - p, 4), "inputs": {f["a"]: ra, f["b"]: rb},
            "markets": {"first_set_a": round(s, 4), "set_betting": sets["correct_score"], "set_handicap": sets["handicap"],
                        "total_sets": sets["total_units"]},
            "data_complete": True, "reliability_note": "" if reliable else "one player ranked outside the top 200 (wildcard/qualifier/returning): ranking points understate or overstate current level",
            "reliable": reliable, "inputs_url": OFF["wta_rankings"]["sources"][0]["url"] if tour == "WTA" else OFF["atp_rankings"]["source"]["url"]}


def darts_line(f, row):
    P = OFF["pdc"]["players"]
    def look(n):
        if n in P:
            return P[n]
        nn = norm(n)
        for k, v in P.items():
            if norm(k) == nn:
                return v
        return None
    pa, pb = look(f["a"]), look(f["b"])
    if not pa or not pb or not pa.get("oom_rank") or not pb.get("oom_rank"):
        return None
    p = M.power_ratio(1.0 / pa["oom_rank"], 1.0 / pb["oom_rank"], 0.5)
    legs = M.race_markets(p, 6, handicaps=(1.5, 2.5, 3.5), totals=(8.5, 9.5))
    return {"model": "PDC Order of Merit rank power model, P(A) = rB^0.5/(rA^0.5+rB^0.5); leg markets assume best-of-11 (format not printed on the captured PDC page)",
            "p_a": round(p, 4), "p_b": round(1 - p, 4),
            "inputs": {f["a"]: {"oom_rank": pa["oom_rank"]}, f["b"]: {"oom_rank": pb["oom_rank"]}},
            "markets": {"leg_handicap": legs["handicap"], "total_legs": legs["total_units"], "expected_legs": legs["expected_units"]},
            "data_complete": True, "reliable": True, "reliability_note": "", "inputs_url": OFF["pdc"]["sources"][0]["url"]}


def logit(p):
    return math.log(p / (1 - p))


def nba_line(f, row):
    S = MAN["nba_standings_2025_26"]["teams"]
    h, a = S.get(f["home"]), S.get(f["a"] if f["a"] != f["home"] else f["b"])
    away = f["a"] if f["a"] != f["home"] else f["b"]
    if not h or not a:
        return None
    def reg(t):
        wp = t["w"] / (t["w"] + t["l"])
        return 0.5 + 0.65 * (wp - 0.5)  # 35% regression toward .500 for off-season change
    hca = 0.28
    note = ""
    if "Austin" in (f.get("venue") or ""):
        hca = 0.14
        note = "Spurs home game staged at Moody Center, Austin: home edge halved"
    x = logit(reg(h)) - logit(reg(a)) + hca
    p_home = 1 / (1 + math.exp(-x))
    # convert to an equivalent spread with a normal margin model (sd 12)
    lo, hi = -30.0, 30.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if 1 - M.norm_cdf(-mid / 12.0) < p_home:
            lo = mid
        else:
            hi = mid
    mk = M.margin_markets((lo + hi) / 2, 12.0)
    return {"model": "2025-26 official win% (35% regressed) log5 + home edge; spread from a normal margin model (sd 12); no total (points data not captured)",
            "p_home": round(p_home, 4), "p_away": round(1 - p_home, 4), "home": f["home"], "away": away,
            "inputs": {f["home"]: h, away: a}, "markets": {"spread_home": mk["spread_home"], "p_home_cover": mk["p_home_cover"]},
            "data_complete": True, "reliable": True, "reliability_note": note, "inputs_url": "https://www.nba.com/standings?Season=2025-26"}


def el_ratings():
    out = {}
    for key, w in (("euroleague_2025", "prev"), ("euroleague_2026", "cur")):
        for g in OFF[key]["games"]:
            if not g["played"] or g["phase"] != "RS":
                continue
            for t, pf, pa, won in ((g["home"], g["hs"], g["as"], g["hs"] > g["as"]), (g["away"], g["as"], g["hs"], g["as"] > g["hs"])):
                d = out.setdefault(t, {"prev": [0, 0, 0, 0, 0], "cur": [0, 0, 0, 0, 0], "cur_seq": []})
                d[w][0] += 1; d[w][1] += pf; d[w][2] += pa; d[w][3] += won; d[w][4] += (not won)
                if w == "cur":
                    d["cur_seq"].append((g["utc"], "W" if won else "L", g["home"] if t != g["home"] else g["away"], pf, pa, t == g["home"]))
    return out


ELR = el_ratings()


def el_line(f, row):
    h, a = f["home"], (f["b"] if f["a"] == f["home"] else f["a"])
    if h not in ELR or a not in ELR:
        return None
    def blend(t):
        d = ELR[t]
        pv, cu = d["prev"], d["cur"]
        net_p = (pv[1] - pv[2]) / pv[0] if pv[0] else None
        net_c = (cu[1] - cu[2]) / cu[0] if cu[0] else 0.0
        pf_p = pv[1] / pv[0] if pv[0] else None
        pa_p = pv[2] / pv[0] if pv[0] else None
        pf_c = cu[1] / cu[0] if cu[0] else None
        pa_c = cu[2] / cu[0] if cu[0] else None
        wc = cu[0] / (cu[0] + 8.0)  # current season weight grows with games played
        net = (net_c * wc + (net_p if net_p is not None else 0.0) * (1 - wc)) if net_p is not None else net_c * wc
        pf = (pf_c * wc + pf_p * (1 - wc)) if pf_p is not None else pf_c
        pa = (pa_c * wc + pa_p * (1 - wc)) if pa_p is not None else pa_c
        return net, pf, pa, (net_p is not None)
    nh, pfh, pah, okh = blend(h)
    na, pfa, paa, oka = blend(a)
    exp_margin = (nh - na) / 2 + 3.0
    exp_total = (pfh + paa + pfa + pah) / 2
    mk = M.margin_markets(exp_margin, 11.5, exp_total, 15.0)
    inputs = {}
    for t in (h, a):
        d = ELR[t]
        inputs[t] = {"2025_26_rs": {"gp": d["prev"][0], "w": d["prev"][3], "l": d["prev"][4], "pf": d["prev"][1], "pa": d["prev"][2]},
                     "2026_27": {"gp": d["cur"][0], "w": d["cur"][3], "l": d["cur"][4], "pf": d["cur"][1], "pa": d["cur"][2],
                                 "seq": "".join(x[1] for x in sorted(d["cur_seq"]))}}
    return {"model": "EuroLeague net-points rating: 2026-27 per-game net blended with 2025-26 regular season (weight on current = gp/(gp+8)); home +3.0; margin sd 11.5, total sd 15",
            "p_home": mk["p_home"], "p_away": mk["p_away"], "home": h, "away": a, "inputs": inputs,
            "markets": {"spread_home": mk["spread_home"], "p_home_cover": mk["p_home_cover"], "total_line": mk.get("total_line"),
                        "p_over": mk.get("p_over"), "exp_total": mk.get("exp_total"), "exp_margin_home": mk["exp_margin_home"]},
            "data_complete": okh and oka, "reliable": True,
            "reliability_note": "" if (okh and oka) else "one club has no 2025-26 EuroLeague data (current season only)",
            "inputs_url": EL["source"]["url"]}


def lnr_line(f, row):
    comp = "prod2_table" if f["competition"].startswith("Pro D2") else "top14_table"
    T = OFF[comp]["table"]
    h, a = f["home"], (f["b"] if f["a"] == f["home"] else f["a"])
    th, ta = T.get(h), T.get(a)
    if not th or not ta:
        return None
    nh = (th["pf"] - th["pa"]) / th["played"]
    na = (ta["pf"] - ta["pa"]) / ta["played"]
    exp_margin = (nh - na) / 2 + 7.0
    exp_total = (th["pf"] / th["played"] + ta["pa"] / ta["played"] + ta["pf"] / ta["played"] + th["pa"] / th["played"]) / 2
    mk = M.margin_markets(exp_margin, 13.0, exp_total, 14.0, draw_band=0.5)
    return {"model": "LNR table points-difference rating (per game), home +7 pts, margin sd 13, total sd 14; three-way (draw = margin within half a point)",
            "p_home": mk["p_home"], "p_away": mk["p_away"], "p_draw": mk["p_draw"], "home": h, "away": a, "inputs": {h: th, a: ta},
            "markets": {"spread_home": mk["spread_home"], "p_home_cover": mk["p_home_cover"], "total_line": mk.get("total_line"),
                        "p_over": mk.get("p_over"), "exp_total": mk.get("exp_total"), "exp_margin_home": mk["exp_margin_home"]},
            "data_complete": True, "reliable": True, "reliability_note": "", "inputs_url": OFF[comp]["source"]["url"]}


def mlb_line(f, row):
    S = OFF["mlb"]["standings"]
    h, a = f["home"], (f["b"] if f["a"] == f["home"] else f["a"])
    th, ta = S.get(h), S.get(a)
    if not th or not ta:
        return None
    def pyth(t):
        return t["rs"] ** 1.83 / (t["rs"] ** 1.83 + t["ra"] ** 1.83)
    ph, pa = pyth(th), pyth(ta)
    x = logit(ph) - logit(pa) + logit(0.54)
    p_home = 1 / (1 + math.exp(-x))
    g_h, g_a = th["w"] + th["l"], ta["w"] + ta["l"]
    exp_total = (th["rs"] / g_h + ta["ra"] / g_a + ta["rs"] / g_a + th["ra"] / g_h) / 2
    lo, hi = -10.0, 10.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if 1 - M.norm_cdf(-mid / 4.3) < p_home:
            lo = mid
        else:
            hi = mid
    mk = M.margin_markets((lo + hi) / 2, 4.3, exp_total, 4.4)
    rl = 1 - M.norm_cdf((1.5 - (lo + hi) / 2) / 4.3)
    return {"model": "Pythagorean win% (exp 1.83) from official 2026 runs scored/allowed, log5 + home field 54%; margin/total normal models (sd 4.3/4.4)",
            "p_home": round(p_home, 4), "p_away": round(1 - p_home, 4), "home": h, "away": a, "inputs": {h: th, a: ta},
            "markets": {"run_line_home_-1.5": round(rl, 4), "total_line": mk.get("total_line"), "p_over": mk.get("p_over"), "exp_total": mk.get("exp_total")},
            "data_complete": True, "reliable": True, "reliability_note": "Rays starting pitcher not announced on the official feed at capture",
            "inputs_url": OFF["mlb"]["standings_source"]["url"]}


def liiga_line(f, row):
    T = OFF["liiga"]["table"]
    h, a = f["home"], (f["b"] if f["a"] == f["home"] else f["a"])
    th, ta = T.get(h), T.get(a)
    if not th or not ta:
        return None
    lam_h = (th["goals"] / th["games"] + ta["goalsAgainst"] / ta["games"]) / 2 * 1.07
    lam_a = (ta["goals"] / ta["games"] + th["goalsAgainst"] / th["games"]) / 2 * 0.95
    mk = M.poisson_markets(lam_h, lam_a, total_lines=(4.5, 5.5, 6.5))
    return {"model": "Independent Poisson on official Liiga goals for/against per game (home x1.07, away x0.95); 2-way splits regulation draws 50/50",
            "p_home": mk["p_home"], "p_away": mk["p_away"], "home": h, "away": a, "inputs": {h: th, a: ta},
            "markets": {"reg_3way": [mk["reg_home"], mk["reg_draw"], mk["reg_away"]], "puck_line": mk["puck_line"], "totals": mk["totals"], "exp_total": mk["exp_total"]},
            "data_complete": True, "reliable": True, "reliability_note": "", "inputs_url": OFF["liiga"]["table_source"]["url"]}


def line_for(f, row):
    sp, comp = f["sport"], f["competition"]
    if sp == "Tennis":
        return tennis_line(f, row)
    if sp == "Darts":
        return darts_line(f, row)
    if comp == "NBA":
        return nba_line(f, row)
    if comp.startswith("EuroLeague"):
        return el_line(f, row)
    if comp.startswith(("Pro D2", "Top 14")):
        return lnr_line(f, row)
    if sp == "Baseball":
        return mlb_line(f, row)
    if comp.startswith("Liiga"):
        return liiga_line(f, row)
    return None


# =============================================================================== recent form (only where official results exist)
def recent_form(f, team):
    comp = f["competition"]
    if comp.startswith("Liiga"):
        gs = sorted([g for g in OFF["liiga"]["games"] if g["ended"] and team in (g["home"], g["away"])], key=lambda g: g["utc"])[-5:]
        w = sum(1 for g in gs if (g["hg"] > g["ag"]) == (g["home"] == team))
        return w, len(gs), "last five Liiga results (official API)"
    if comp.startswith(("Pro D2", "Top 14")):
        T = OFF["prod2_table" if comp.startswith("Pro D2") else "top14_table"]["table"]
        fm = (T.get(team) or {}).get("form_last5_as_printed", "")
        return fm.count("V"), len(fm), "LNR 'Etat de forme' (last five)"
    if comp.startswith("MLB"):
        l10 = (OFF["mlb"]["standings"].get(team) or {}).get("last10") or ""
        if "-" in l10:
            w, l = [int(x) for x in l10.split("-")]
            return w, w + l, "regular-season last ten (official standings)"
    if comp.startswith("EuroLeague") and team in ELR:
        seq = "".join(x[1] for x in sorted(ELR[team]["cur_seq"]))[-5:]
        return seq.count("W"), len(seq), "last five EuroLeague games 2026-27 (official API)"
    return None


# =============================================================================== assemble
def fmt_side(L, f):
    """Return (pick_name, p_pick, opp_name) from a line dict."""
    if "p_a" in L:
        if L["p_a"] >= L["p_b"]:
            return f["a"], L["p_a"], f["b"]
        return f["b"], L["p_b"], f["a"]
    if L["p_home"] >= L["p_away"]:
        return L["home"], L["p_home"], L["away"]
    return L["away"], L["p_away"], L["home"]


def same_entity(x: str, y: str) -> bool:
    if not x or not y:
        return False
    nx, ny = canon(x), canon(y)
    return nx == ny or surname(x) == surname(y) or nx in ny or ny in nx


rows = []
used = set()
for r in INV["events"]:
    if r["row_kind"] != "match":
        continue
    f, aligned = match_fixture(r)
    rec = dict(r)
    rec["flags"] = []
    started = (r["expired_flag"] == "1") or (r["start_utc"] and r["start_utc"] < AS_OF)
    rec["started_before_desk"] = bool(started)
    if f is None:
        rec["verification"] = "unverified"
        rec["official"] = None
        rec["flags"].append("No official fixture page captured for this competition in this run; date/time/participants not confirmed — left blank")
        rows.append(rec)
        continue
    used.add(id(f))
    status = "verified"
    if f.get("partial"):
        status = "partially verified"
    off_utc = f.get("utc")
    if off_utc and r["start_utc"]:
        dmin = (datetime.fromisoformat(r["start_utc"].replace("Z", "+00:00")) - datetime.fromisoformat(off_utc.replace("Z", "+00:00"))).total_seconds() / 60
        if abs(dmin) >= 1:
            rec["flags"].append(f"OLBG start differs from official by {int(dmin):+d} min (OLBG {r['start_utc'][11:16]}Z vs official {off_utc[11:16]}Z)")
            if abs(dmin) > 60:
                status = "mismatch"
    elif not off_utc:
        if f.get("date") and r["start_utc"] and f["date"] != r["start_utc"][:10] and f["sport"] != "Darts":
            rec["flags"].append(f"OLBG date {r['start_utc'][:10]} vs official date {f['date']}")
        rec["flags"].append(f"Official schedule gives no fixed start ({f.get('utc_basis')}); OLBG time is an estimate")
    if f["sport"] == "Darts" and f.get("date") and r["start_utc"][:10] != f["date"]:
        status = "mismatch"
        rec["flags"].append("OLBG date differs from the official session date")
    if f.get("venue") and "Austin" in f["venue"]:
        rec["flags"].append("Venue irregularity: Spurs home game staged at Moody Center, Austin TX (official)")
    rec["verification"] = status
    rec["official"] = {k: f.get(k) for k in ("competition", "a", "b", "home", "utc", "utc_basis", "date", "venue", "url", "source_name", "capture", "seed_a", "seed_b", "state", "result")}
    rec["official"]["extra"] = f.get("extra", {})
    L = None if started else line_for(f, r)
    rec["line"] = L
    if L:
        pick, p_pick, opp = fmt_side(L, f)
        fair = M.american(p_pick)
        mkt = None
        mkt_note = ""
        opp_price = None
        if r["market_label"] in ("Win Match", "Money Line", "Win Match 2-way", "To Win") and r["featured_price_american"]:
            try:
                fp = int(float(r["featured_price_american"]))
            except ValueError:
                fp = None
            if fp is not None:
                if same_entity(r["featured_selection"], pick):
                    mkt = fp
                    mkt_note = f"market price shown on OLBG for {pick}: {fp:+d}"
                elif same_entity(r["featured_selection"], opp):
                    opp_price = fp
                    mkt_note = f"OLBG shows the opponent ({opp}) at {fp:+d}; price for our side not displayed"
                    if fp < 0:
                        mkt_note += " — our side is the market underdog"
        grade, why = M.grade(p_pick, L["data_complete"], fair, mkt)
        if grade == "High":
            if mkt is not None and mkt > 0:
                grade, why = "Medium", f"capped: model-market disagreement (market has {pick} as underdog at {mkt:+d})"
            elif mkt is None and opp_price is not None and opp_price < 0:
                grade, why = "Medium", f"capped: model-market disagreement (market favours {opp} at {opp_price:+d})"
            elif mkt is None and opp_price is not None and opp_price >= 250:
                grade, why = "Medium", f"capped: opponent displayed at {opp_price:+d}, so our side is priced shorter than the -250 window can be shown to allow"
            elif mkt is None and opp_price is None and fair < -200:
                grade, why = "Medium", "capped: no market moneyline displayed; High without a market check needs a fair price no shorter than -200"
        if grade == "High":
            fp_, fo_ = recent_form(f, pick), recent_form(f, opp)
            if fp_ and fo_ and fp_[1] and fo_[1] and fp_[0] / fp_[1] < fo_[0] / fo_[1]:
                grade, why = "Medium", f"capped: recent form favours {opp} ({fo_[0]}/{fo_[1]} v {fp_[0]}/{fp_[1]}, {fp_[2]})"
        if not L.get("reliable", True) and grade in ("High", "Medium"):
            grade, why = "Low", "capped: " + L["reliability_note"]
        if status != "verified" and grade == "High":
            grade, why = "Medium", "capped: fixture not fully verified"
        rec["pick"] = {"selection": pick, "opponent": opp, "p": round(p_pick, 4), "fair_american": fair, "fair_decimal": M.decimal(p_pick),
                       "confidence": grade, "confidence_reason": why, "market_reference": mkt, "market_note": mkt_note,
                       "in_window_fair": M.in_window(fair), "in_window_market": (M.in_window(mkt) if mkt is not None else None)}
    else:
        rec["pick"] = None
        if not started:
            rec["flags"].append("No line originated: official numeric inputs for this competition were not captured")
    rows.append(rec)

# official-only fixtures in captured competitions (not listed by OLBG at capture)
extra_rows = []
for f in FIX:
    if id(f) in used or f["sport"] not in ("Basketball", "Rugby Union") or not f.get("utc") or f["utc"] < AS_OF:
        continue
    if not (f["competition"].startswith("EuroLeague") or f["competition"].startswith("Top 14")):
        continue
    L = line_for(f, None)
    rec = {"sport": f["sport"], "event_name": f"{f['a']} v {f['b']}", "olbg_url": None, "event_id": None, "start_utc": f["utc"],
           "verification": "verified (official only)", "official": {k: f.get(k) for k in ("competition", "a", "b", "home", "utc", "utc_basis", "date", "venue", "url", "source_name", "capture")},
           "flags": ["Not listed on OLBG at capture (OLBG lists only events that already carry tips)"], "line": L, "row_kind": "official_only"}
    if L:
        pick, p_pick, opp = fmt_side(L, f)
        fair = M.american(p_pick)
        grade, why = M.grade(p_pick, L["data_complete"], fair, None)
        if grade == "High":
            grade, why = "Medium", "capped: official-only fixture (not on OLBG), so no market reference for the -250...+10000 check"
        rec["pick"] = {"selection": pick, "opponent": opp, "p": round(p_pick, 4), "fair_american": fair, "fair_decimal": M.decimal(p_pick),
                       "confidence": grade, "confidence_reason": why, "market_reference": None, "market_note": "", "in_window_fair": M.in_window(fair), "in_window_market": None}
    extra_rows.append(rec)

desk = {"built_utc": AS_OF, "olbg_capture_utc": CAPTURE_UTC, "rows": rows, "official_only": extra_rows,
        "outrights": [r for r in INV["events"] if r["row_kind"] == "outright"], "hubs": INV["hubs"]}
json.dump(desk, open(os.path.join(DATA, "desk.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)

from collections import Counter
print("match rows", len(rows), Counter(r["verification"] for r in rows))
print("lines", sum(1 for r in rows if r.get("pick")), "conf", Counter(r["pick"]["confidence"] for r in rows if r.get("pick")))
print("official-only", len(extra_rows))
