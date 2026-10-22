#!/usr/bin/env python3
"""Board AD (session arena/7c581d22-olbg4) — fresh-window desk, 23 Oct-5 Nov 2026.

Every fixture/form value is parsed from a committed official-league payload whose
SHA-256 is re-checked here against the capturing session's manifest (or, where a
small set of values was read live with the agent page-fetch tool on 2026-10-22,
transcribed verbatim below with the exact observed excerpt logged in
live_checks.json). OLBG.com is used only for the sport taxonomy cross-check
(repo data/olbg-structure.json). No bookmaker or OLBG price is read anywhere.
All prices are OUR originated FAIR prices (decimal = 1/p, no margin).

Run: python3 scripts/session-7c581d22/build.py -> data/session-7c581d22/*.json
"""
import gzip, hashlib, json, math, os, sys
from collections import defaultdict

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
OUTDIR = os.path.join(ROOT, "data", "session-7c581d22")
CAPTURE = "2026-10-22"
WIN_LO, WIN_HI = "2026-10-23T00:00:00Z", "2026-11-06T00:00:00Z"  # LoL/MLB UTC bounds; NHL/EL use official local dates

sys.path.insert(0, os.path.dirname(__file__))
try:
    from predictions import PREDICTIONS  # hand-authored, focus picks only
except Exception:
    PREDICTIONS = {}

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def clamp(x, lo, hi): return max(lo, min(hi, x))
def phi(x): return 0.5 * (1 + math.erf(x / math.sqrt(2)))
def dec_odds(p): return round(1.0 / p, 2)
def amer_odds(p):
    d = 1.0 / p
    return int(round(-100 / (d - 1))) if d < 2 else int(round((d - 1) * 100))
def rhalf(x): return math.floor(x * 2 + 0.5) / 2
def price(p):
    p = round(p, 4)  # publish a self-consistent triple: odds derived from the rounded p
    return {"p": p, "decimal": dec_odds(p), "american": amer_odds(p)}
def in_window(am): return -250 <= am <= 10000

def grade(p, cap="High"):
    g = "High" if p >= 0.70 else ("Medium" if p >= 0.58 else "Low")
    order = {"Low": 0, "Medium": 1, "High": 2}
    return g if order[g] <= order[cap] else cap

sources = []
def register_source(name, url, path=None, manifest=None, manifest_key=None, captured="2026-10-22", note=""):
    rec = {"name": name, "url": url, "captured_on": captured, "note": note}
    if path:
        rec["repo_file"] = os.path.relpath(path, ROOT)
        rec["sha256_file"] = sha256(path)
        if path.endswith(".gz"):
            rec["sha256"] = hashlib.sha256(gzip.open(path, "rb").read()).hexdigest()
            rec["hash_basis"] = "decompressed content (matches capturing manifest convention)"
        else:
            rec["sha256"] = rec["sha256_file"]; rec["hash_basis"] = "file bytes"
        if manifest:
            man = json.load(open(manifest))
            want = None
            for t in man.get("targets", man.get("items", [])):
                key = t.get("name") or t.get("id")
                if key == manifest_key:
                    want = t.get("sha256")
            rec["manifest"] = os.path.relpath(manifest, ROOT)
            rec["manifest_key"] = manifest_key
            rec["hash_matches_manifest"] = (want == rec["sha256"])
            assert want == rec["sha256"], f"hash mismatch for {name}: {rec['sha256']} != manifest {want}"
    sources.append(rec)
    return rec

rows = []
def add(**kw): rows.append(kw)

FOCUS = []  # every originated selection with p>=0.70 inside -250..+10000 (sport cap permitting)
def consider_focus(row_id, sport, market, selection_label, p, cap):
    pr = price(p)
    if p >= 0.70 and in_window(pr["american"]) and grade(p, cap) == "High":
        FOCUS.append({"row_id": row_id, "sport": sport, "market": market,
                      "selection": selection_label, **pr, "in_focus_window": True})

# ============================================================ NHL
E5 = os.path.join(ROOT, "data", "session-e5f2dad3", "raw")
E5MAN = os.path.join(ROOT, "data", "session-e5f2dad3", "manifest.json")
NHL_SCHED_URL = "https://api-web.nhle.com/v1/schedule/2026-10-23"
NHL_STAND_URL = "https://api-web.nhle.com/v1/standings/2026-10-22"

stand_path = os.path.join(E5, "nhl_standings_2026-10-22.json")
register_source("NHL standings 2026-10-22 (official NHL API)", NHL_STAND_URL,
                stand_path, E5MAN, "nhl_standings_2026-10-22",
                note="Live re-check 2026-10-22T12:00Z: standingsDateTimeUtc 2026-10-22T12:00:45Z (live_checks L01).")
ST = {}
for t in json.load(open(stand_path))["standings"]:
    ab = t["teamAbbrev"]["default"]
    ST[ab] = {
        "name": t["teamName"]["default"], "gp": t["gamesPlayed"], "w": t["wins"],
        "l": t["losses"], "ot": t["otLosses"], "pts": t["points"],
        "gf": t["goalFor"], "ga": t["goalAgainst"], "ppctg": t["pointPctg"],
        "home": f"{t['homeWins']}-{t['homeLosses']}-{t['homeOtLosses']}",
        "away": f"{t['roadWins']}-{t['roadLosses']}-{t['roadOtLosses']}",
        "l10": f"{t['l10Wins']}-{t['l10Losses']}-{t['l10OtLosses']}",
        "streak": f"{t['streakCode']}{t['streakCount']}",
    }
mu_nhl = sum(v["gf"] for v in ST.values()) / sum(v["gp"] for v in ST.values())
def nhl_rate(v, key):  # shrink early-season rates toward league mean, k=8 games
    return (v[key] + 8 * mu_nhl) / (v["gp"] + 8)

games = {}
for day in ["2026-10-23", "2026-10-24", "2026-10-25", "2026-10-26", "2026-10-27", "2026-10-28",
            "2026-10-29", "2026-10-30", "2026-10-31", "2026-11-01", "2026-11-02"]:
    p = os.path.join(E5, f"nhl_schedule_{day}.json")
    register_source(f"NHL schedule week of {day} (official NHL API)",
                    f"https://api-web.nhle.com/v1/schedule/{day}", p, E5MAN, f"nhl_schedule_{day}")
    for wk in json.load(open(p)).get("gameWeek", []):
        for g in wk.get("games", []):
            g["_local_date"] = wk.get("date", g["startTimeUTC"][:10])
            games[g["id"]] = g

nhl_rows = [g for g in games.values()
            if g.get("gameType") == 2 and "2026-10-23" <= g["_local_date"] <= "2026-11-05"
            and g.get("gameState") == "FUT"]
nhl_rows.sort(key=lambda g: g["startTimeUTC"])
print(f"NHL fixtures in window: {len(nhl_rows)} (league GF/GP mu={mu_nhl:.3f})")

def poisson_matrix(lh, la, n=11):
    def pmf(lam):
        out, tot = [], 0.0
        for k in range(n):
            v = math.exp(-lam) * lam ** k / math.factorial(k)
            out.append(v); tot += v
        out.append(max(0.0, 1 - tot))  # tail lumped at n
        return out
    ph, pa = pmf(lh), pmf(la)
    return [[ph[i] * pa[j] for j in range(n + 1)] for i in range(n + 1)]

for g in nhl_rows:
    ab_a, ab_h = g["awayTeam"]["abbrev"], g["homeTeam"]["abbrev"]
    A, H = ST[ab_a], ST[ab_h]
    lh = mu_nhl * (nhl_rate(H, "gf") / mu_nhl) * (nhl_rate(A, "ga") / mu_nhl) * 1.05
    la = mu_nhl * (nhl_rate(A, "gf") / mu_nhl) * (nhl_rate(H, "ga") / mu_nhl) * 0.95
    M = poisson_matrix(lh, la)
    p_tie = sum(M[i][i] for i in range(12))
    p_home_reg = sum(M[i][j] for i in range(12) for j in range(12) if i > j)
    p_home = p_home_reg + p_tie * lh / (lh + la)
    p_home_by2 = sum(M[i][j] for i in range(12) for j in range(12) if i - j >= 2)
    p_away_by2 = sum(M[i][j] for i in range(12) for j in range(12) if j - i >= 2)
    exp_total = lh + la + p_tie
    tline = rhalf(exp_total - 0.001)  # nearest .5, ties down
    if tline == int(tline): tline += 0.5
    p_over = sum(M[i][j] for i in range(12) for j in range(12) if (i + j + (1 if i == j else 0)) > tline)
    home_fav = p_home >= 0.5
    fav_by2 = p_home_by2 if home_fav else p_away_by2
    rid = f"AD-NHL-{g['id']}"
    pick_home = home_fav
    pick_p = p_home if pick_home else 1 - p_home
    cap = "High" if min(A["gp"], H["gp"]) >= 8 else "Medium"
    r = {
        "id": rid, "sport": "Ice Hockey", "competition": "NHL regular season 2026-27",
        "date": g["_local_date"], "start_utc": g["startTimeUTC"],
        "side_a": A["name"], "side_b": H["name"], "fixture": f"{A['name']} @ {H['name']}",
        "venue": g["venue"]["default"], "source_url": NHL_SCHED_URL,
        "source_name": "NHL official API — schedule + standings (api-web.nhle.com)",
        "status": "priced",
        "inputs": {
            "away": {"team": A["name"], "record": f"{A['w']}-{A['l']}-{A['ot']}", "gp": A["gp"],
                     "pts": A["pts"], "gf": A["gf"], "ga": A["ga"], "road": A["away"],
                     "l10": A["l10"], "streak": A["streak"], "exp_goals": round(la, 2)},
            "home": {"team": H["name"], "record": f"{H['w']}-{H['l']}-{H['ot']}", "gp": H["gp"],
                     "pts": H["pts"], "gf": H["gf"], "ga": H["ga"], "home": H["home"],
                     "l10": H["l10"], "streak": H["streak"], "exp_goals": round(lh, 2)},
            "league_gf_per_game": round(mu_nhl, 3), "standings_date": "2026-10-22",
        },
        "markets": {
            "moneyline": {"label": "Moneyline (incl. OT/shootout)",
                          "a": price(1 - p_home), "b": price(p_home)},
            "puck_line": {"label": "Puck line ±1.5 (favourite -1.5 / underdog +1.5)",
                          "fav_side": "b" if home_fav else "a",
                          "fav_minus": price(fav_by2), "dog_plus": price(1 - fav_by2)},
            "total": {"label": f"Match total {tline} goals (incl. OT winner)",
                      "line": tline, "over": price(p_over), "under": price(1 - p_over)},
        },
        "pick": {"market": "moneyline", "selection": (H["name"] if pick_home else A["name"]) + " (moneyline)",
                 **price(pick_p), "confidence": grade(pick_p, cap),
                 "in_focus_window": in_window(amer_odds(pick_p))},
    }
    add(**r)
    consider_focus(rid, "Ice Hockey", "moneyline", r["pick"]["selection"], pick_p, cap)
    fav_name = H["name"] if home_fav else A["name"]; dog_name = A["name"] if home_fav else H["name"]
    consider_focus(rid, "Ice Hockey", "puck_line", f"{fav_name} -1.5 (puck line)", fav_by2, cap)
    consider_focus(rid, "Ice Hockey", "puck_line", f"{dog_name} +1.5 (puck line)", 1 - fav_by2, cap)
    consider_focus(rid, "Ice Hockey", "total", f"Over {tline} goals", p_over, cap)
    consider_focus(rid, "Ice Hockey", "total", f"Under {tline} goals", 1 - p_over, cap)

# ============================================================ EuroLeague basketball
CAP9359 = os.path.join(ROOT, "data", "session-9359e596", "capture", "20261022T083834Z")
MAN9359 = os.path.join(CAP9359, "manifest.json")
EL_URL = "https://api-live.euroleague.net/v2/competitions/E/seasons/E2026/games"
el_path = os.path.join(CAP9359, "raw", "euroleague_games_E2026.json.gz")
rec = register_source("EuroLeague 2026-27 games feed (official Euroleague Basketball API)",
                      EL_URL, el_path, MAN9359, "euroleague_games_E2026",
                      note="Standings/PPG derived by this build from the 61 played-game scores in the same official feed; no unofficial table used.")
el_games = json.loads(gzip.open(el_path, "rt", encoding="utf-8").read())["data"]
el_st = defaultdict(lambda: {"gp": 0, "w": 0, "l": 0, "pf": 0, "pa": 0, "results": []})
for x in el_games:
    if x.get("played"):
        hn, an = x["local"]["club"]["name"], x["road"]["club"]["name"]
        hs, as_ = x["local"]["score"], x["road"]["score"]
        for nm, pf, pa, w in [(hn, hs, as_, hs > as_), (an, as_, hs, as_ > hs)]:
            s = el_st[nm]; s["gp"] += 1; s["pf"] += pf; s["pa"] += pa
            s["w" if w else "l"] += 1; s["results"].append((x["date"], "W" if w else "L", pf, pa))
for s in el_st.values():
    s["results"].sort()
    s["form"] = "".join(r[1] for r in s["results"][-5:])
    s["last"] = s["results"][-1] if s["results"] else None
mu_el = sum(s["pf"] for s in el_st.values()) / sum(s["gp"] for s in el_st.values())
def el_rate(s, key): return (s[key] + 6 * mu_el) / (s["gp"] + 6)  # shrink k=6 games

el_up = sorted([x for x in el_games if not x.get("played") and "2026-10-23" <= x.get("date", "")[:10] <= "2026-11-05"],
               key=lambda x: x["utcDate"])
print(f"EuroLeague fixtures in window: {len(el_up)} (league PPG mu={mu_el:.2f})")
SIG_M, SIG_T, HOME_EDGE = 12.0, 19.0, 2.2
for x in el_up:
    hn, an = x["local"]["club"]["name"], x["road"]["club"]["name"]
    H, A = el_st[hn], el_st[an]
    lh = mu_el * (el_rate(H, "pf") / mu_el) * (el_rate(A, "pa") / mu_el)
    la = mu_el * (el_rate(A, "pf") / mu_el) * (el_rate(H, "pa") / mu_el)
    margin = (lh - la) + HOME_EDGE
    p_home = phi(margin / SIG_M)
    spread = -rhalf(margin - 0.001) if abs(margin) >= 0.25 else (-0.5 if margin >= 0 else 0.5)
    if spread == int(spread): spread += -0.5 if margin >= 0 else 0.5
    p_home_cover = phi((margin + spread) / SIG_M)
    tline = rhalf(lh + la - 0.001)
    if tline == int(tline): tline += 0.5
    p_over = 1 - phi((tline - (lh + la)) / SIG_T)
    rid = f"AD-EL-{x['identifier']}"
    pick_home = p_home >= 0.5
    pick_p = p_home if pick_home else 1 - p_home
    cap = "High" if min(H["gp"], A["gp"]) >= 7 else "Medium"
    venue = (x.get("venue") or {}).get("name") or ""
    def last_str(s, nm):
        if not s["last"]: return ""
        d, res, pf, pa = s["last"]; return f"{res} {pf}-{pa} on {d[:10]}"
    r = {
        "id": rid, "sport": "Basketball", "competition": f"Turkish Airlines EuroLeague 2026-27 — {x['roundAlias']}",
        "date": x["date"][:10], "start_utc": x["utcDate"],
        "side_a": an, "side_b": hn, "fixture": f"{an} @ {hn}", "venue": venue,
        "source_url": "https://www.euroleaguebasketball.net/en/euroleague/game-center/",
        "source_name": "Euroleague Basketball official games API (api-live.euroleague.net)",
        "status": "priced",
        "inputs": {
            "away": {"team": an, "record": f"{A['w']}-{A['l']}", "gp": A["gp"], "pf_pg": round(A["pf"]/A["gp"],1),
                     "pa_pg": round(A["pa"]/A["gp"],1), "form_last5": A["form"], "last_result": last_str(A, an),
                     "exp_pts": round(la, 1)},
            "home": {"team": hn, "record": f"{H['w']}-{H['l']}", "gp": H["gp"], "pf_pg": round(H["pf"]/H["gp"],1),
                     "pa_pg": round(H["pa"]/H["gp"],1), "form_last5": H["form"], "last_result": last_str(H, hn),
                     "exp_pts": round(lh, 1)},
            "league_ppg": round(mu_el, 2), "standings_basis": "derived from 61 played scores in official feed, captured 2026-10-22T08:38Z",
        },
        "markets": {
            "moneyline": {"label": "Match winner (incl. OT)", "a": price(1 - p_home), "b": price(p_home)},
            "spread": {"label": f"Point spread — {hn} {spread:+.1f}", "home_line": spread,
                       "b": price(p_home_cover), "a": price(1 - p_home_cover)},
            "total": {"label": f"Match total {tline} points", "line": tline,
                      "over": price(p_over), "under": price(1 - p_over)},
        },
        "pick": {"market": "moneyline", "selection": (hn if pick_home else an) + " (match winner)",
                 **price(pick_p), "confidence": grade(pick_p, cap),
                 "in_focus_window": in_window(amer_odds(pick_p))},
    }
    if hn in ("Maccabi Rapyd Tel Aviv", "Hapoel IBI Tel Aviv"):
        r["notes"] = ("Home fixture staged outside Israel per the venue in the official feed "
                      f"({venue}); the model's standard +2.2 home edge is still applied — see Flagged AD-F07.")
    add(**r)
    consider_focus(rid, "Basketball", "moneyline", r["pick"]["selection"], pick_p, cap)
    consider_focus(rid, "Basketball", "spread", f"{hn} {spread:+.1f} (spread)", p_home_cover, cap)
    consider_focus(rid, "Basketball", "spread", f"{an} {-spread:+.1f} (spread)", 1 - p_home_cover, cap)
    consider_focus(rid, "Basketball", "total", f"Over {tline} points", p_over, cap)
    consider_focus(rid, "Basketball", "total", f"Under {tline} points", 1 - p_over, cap)

# ============================================================ MLB World Series
MLB_SCHED_URL = "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-23&endDate=2026-11-05"
mlb_sched_path = os.path.join(E5, "mlb_schedule.json")
register_source("MLB schedule 22 Oct-5 Nov 2026 (official MLB Stats API)",
                "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-22&endDate=2026-11-05&gameTypes=R,F,D,L,W",
                mlb_sched_path, E5MAN, "mlb_schedule",
                note="Live re-read 2026-10-22 this session returned the same 7 World Series games (live_checks L03).")
mlb_stand_path = os.path.join(E5, "mlb_standings.json")
register_source("MLB 2026 regular-season standings (official MLB Stats API)",
                "https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season=2026&standingsTypes=regularSeason",
                mlb_stand_path, E5MAN, "mlb_standings")
TEAM = {}
lg_rs = lg_g = 0
for rec_ in json.load(open(mlb_stand_path))["records"]:
    for tr in rec_["teamRecords"]:
        nm = {"Rays": "Tampa Bay Rays", "Brewers": "Milwaukee Brewers"}.get(tr["team"]["name"], tr["team"]["name"])
        splits = {s["type"]: s for s in tr["records"]["splitRecords"]}
        TEAM[nm] = {"w": tr["leagueRecord"]["wins"], "l": tr["leagueRecord"]["losses"],
                    "pct": float(tr["leagueRecord"]["pct"]), "rs": tr["runsScored"], "ra": tr["runsAllowed"],
                    "gp": tr["gamesPlayed"], "streak": tr["streak"]["streakCode"],
                    "home_pct": float(splits["home"]["pct"]), "away_pct": float(splits["away"]["pct"]),
                    "home_rec": f"{splits['home']['wins']}-{splits['home']['losses']}",
                    "away_rec": f"{splits['away']['wins']}-{splits['away']['losses']}",
                    "last10": f"{splits['lastTen']['wins']}-{splits['lastTen']['losses']}",
                    "run_diff": tr["runDifferential"]}
        lg_rs += tr["runsScored"]; lg_g += tr["gamesPlayed"]
mu_mlb = lg_rs / lg_g
def log5(pa, pb): return (pa - pa * pb) / (pa + pb - 2 * pa * pb)
SIG_D, SIG_TT = 4.1, 4.6
mlb_games = []
for d in json.load(open(mlb_sched_path))["dates"]:
    for g in d["games"]:
        if WIN_LO <= g["gameDate"] < WIN_HI and g["status"]["abstractGameState"] == "Preview":
            mlb_games.append(g)
mlb_games.sort(key=lambda g: g["gameDate"])
print(f"MLB games in window: {len(mlb_games)} (league RS/G={mu_mlb:.3f})")
for g in mlb_games:
    an = g["teams"]["away"]["team"]["name"]; hn = g["teams"]["home"]["team"]["name"]
    A, H = TEAM[an], TEAM[hn]
    p_home = log5(H["home_pct"], A["away_pct"])
    r_h = mu_mlb * ((H["rs"] / H["gp"]) / mu_mlb) * ((A["ra"] / A["gp"]) / mu_mlb)
    r_a = mu_mlb * ((A["rs"] / A["gp"]) / mu_mlb) * ((H["ra"] / H["gp"]) / mu_mlb)
    mdiff = r_h - r_a
    home_fav = p_home >= 0.5
    p_fav_by2 = 1 - phi((1.5 - mdiff) / SIG_D) if home_fav else phi((-1.5 - mdiff) / SIG_D)
    tline = rhalf(r_h + r_a - 0.001)
    if tline == int(tline): tline += 0.5
    p_over = 1 - phi((tline - (r_h + r_a)) / SIG_TT)
    rid = f"AD-MLB-{g['gamePk']}"
    pick_p = p_home if home_fav else 1 - p_home
    r = {
        "id": rid, "sport": "Baseball", "competition": f"MLB World Series 2026 — {g['description']}",
        "date": g["officialDate"], "start_utc": g["gameDate"],
        "side_a": an, "side_b": hn, "fixture": f"{an} @ {hn}", "venue": g["venue"]["name"],
        "source_url": MLB_SCHED_URL, "source_name": "MLB official Stats API — schedule + standings (statsapi.mlb.com)",
        "status": "priced",
        "inputs": {
            "away": {"team": an, "record": f"{A['w']}-{A['l']}", "rs": A["rs"], "ra": A["ra"],
                     "run_diff": A["run_diff"], "away_rec": A["away_rec"], "last10": A["last10"],
                     "streak": A["streak"], "exp_runs": round(r_a, 2)},
            "home": {"team": hn, "record": f"{H['w']}-{H['l']}", "rs": H["rs"], "ra": H["ra"],
                     "run_diff": H["run_diff"], "home_rec": H["home_rec"], "last10": H["last10"],
                     "streak": H["streak"], "exp_runs": round(r_h, 2)},
            "league_rs_per_game": round(mu_mlb, 3), "if_necessary": g["ifNecessary"],
        },
        "markets": {
            "moneyline": {"label": "Moneyline", "a": price(1 - p_home), "b": price(p_home)},
            "run_line": {"label": "Run line ±1.5 (favourite -1.5 / underdog +1.5)",
                         "fav_side": "b" if home_fav else "a",
                         "fav_minus": price(p_fav_by2), "dog_plus": price(1 - p_fav_by2)},
            "total": {"label": f"Match total {tline} runs", "line": tline,
                      "over": price(p_over), "under": price(1 - p_over)},
        },
        "pick": {"market": "moneyline", "selection": (hn if home_fav else an) + " (moneyline)",
                 **price(pick_p), "confidence": grade(pick_p),
                 "in_focus_window": in_window(amer_odds(pick_p))},
    }
    if g["ifNecessary"] == "Y":
        r["notes"] = "If-necessary game: only played if the series requires it (official schedule flag)."
    add(**r)
    consider_focus(rid, "Baseball", "moneyline", r["pick"]["selection"], pick_p, "High")
    fav_name = hn if home_fav else an; dog_name = an if home_fav else hn
    consider_focus(rid, "Baseball", "run_line", f"{dog_name} +1.5 (run line)", 1 - p_fav_by2, "High")
    consider_focus(rid, "Baseball", "total", f"Over {tline} runs", p_over, "High")
    consider_focus(rid, "Baseball", "total", f"Under {tline} runs", 1 - p_over, "High")

# ============================================================ PDC darts (live-read transcriptions, see live_checks L05)
PDC_SCHED = "https://www.pdc.tv/news/2026/october/19/2026-machineseeker-european-championship-schedule-confirmed/"
PDC_DRAW = "https://www.pdc.tv/news/2026/october/18/2026-Machineseeker-European-Championship-field---draw-confirmed"
register_source("PDC 2026 European Championship schedule of play (pdc.tv)", PDC_SCHED,
                note="Read live 2026-10-22 via search excerpt of the official page; direct fetch returned a consent wall in this environment — see live_checks L05 and Flagged AD-F03.")
register_source("PDC 2026 European Championship field & draw, seeds = European Tour Order of Merit (pdc.tv)", PDC_DRAW,
                note="Seeded bracket transcribed 2026-10-22 from the official draw as republished verbatim; cross-checked against the pdc.tv search excerpt — see live_checks L05.")
# Friday 23 Oct round-one ties (best of 11 legs), (player, Euro Tour OOM seed)
PDC_FRI = [
    ("Ryan Joyce", 15, "Jermaine Wattimena", 18),
    ("Krzysztof Ratajski", 3, "Dave Chisnall", 30),
    ("Nathan Aspinall", 6, "Cristo Reyes", 27),
    ("Jonny Clayton", 7, "Niko Springer", 26),
    ("Luke Littler", 11, "William O'Connor", 22),
    ("Wessel Nijman", 2, "Martin Schindler", 31),
    ("Kevin Doets", 14, "Michael van Gerwen", 19),
    ("Josh Rock", 10, "Chris Dobey", 23),
]
for i, (pa, sa, pb, sb) in enumerate(PDC_FRI, 1):
    p_a = 1 / (1 + math.exp(-0.035 * (sb - sa)))
    pick_a = p_a >= 0.5
    pick_p = p_a if pick_a else 1 - p_a
    rid = f"AD-PDC-{i:02d}"
    add(**{
        "id": rid, "sport": "Darts",
        "competition": "PDC Machineseeker European Championship 2026 — Round One (best of 11 legs)",
        "date": "2026-10-23", "start_utc": "2026-10-23T17:00:00Z (session 1900-2300 CEST per pdc.tv)",
        "side_a": pa, "side_b": pb, "fixture": f"{pa} v {pb}",
        "venue": "Westfalenhallen, Dortmund", "source_url": PDC_SCHED,
        "source_name": "PDC official site (pdc.tv) — schedule confirmed 19 Oct; seeded draw 18 Oct",
        "status": "priced",
        "inputs": {"a": {"player": pa, "euro_tour_oom_seed": sa},
                   "b": {"player": pb, "euro_tour_oom_seed": sb},
                   "basis": "European Tour Order of Merit seeding only; no leg/average data read this session"},
        "markets": {"moneyline": {"label": "Match winner", "a": price(p_a), "b": price(1 - p_a)}},
        "pick": {"market": "moneyline", "selection": (pa if pick_a else pb) + " (match winner)",
                 **price(pick_p), "confidence": grade(pick_p, "Medium"),
                 "in_focus_window": in_window(amer_odds(pick_p))},
        "notes": ("Seeded by the European Tour Order of Merit, which is NOT the PDC world ranking "
                  "(e.g. Luke Littler, world number one per pdc.tv, is seeded 11 here); confidence "
                  "therefore capped at Medium — see Flagged AD-F04. Leg handicap / totals not "
                  "originated: no verified leg-level data read."),
    })
print(f"PDC ties priced: {len(PDC_FRI)}")

# ============================================================ WTA Osaka QFs — verified fixtures, unpriced (live_checks L04/L09)
WTA_API = "https://api.wtatennis.com/tennis/tournaments/405/2026/matches"
wta_path = os.path.join(CAP9359, "raw", "wta_405_matches.json.gz")
register_source("WTA Osaka (Kinoshita Group Japan Open) matches feed (api.wtatennis.com)",
                WTA_API, wta_path, MAN9359, "wta_405_matches",
                note="Live re-read 2026-10-22 (feed lastUpdated 2026-10-22T09:46:03Z) resolved the fourth QF pairing — live_checks L04.")
wta = json.loads(gzip.open(wta_path, "rt", encoding="utf-8").read())
def wta_last_result(pid):
    res = []
    for m in wta["matches"]:
        if m.get("MatchState") == "F" and m.get("DrawMatchType") == "S" and pid in (m.get("PlayerIDA"), m.get("PlayerIDB")):
            res.append(m.get("ResultString") or "")
    return res[-1] if res else ""
# QF pairings as read live from WTA_API on 2026-10-22 (MatchIDs LS004-LS007, all 2026-10-23, Osaka):
WTA_QF = [
    ("LS004", "Ann Li", "326096", "1", "Lilli Tagger", "332150", "", "2026-10-23T11:30+09:00"),
    ("LS005", "Talia Gibson", "329393", "4", "Ashlyn Krueger", "329409", "", "2026-10-23 (order of play: followed by, per feed)"),
    ("LS006", "Katie Boulter", "319125", "8", "Antonia Ruzic", "329505", "", "2026-10-23 (order of play: followed by, per feed)"),
    ("LS007", "Mary Stoiana", "330265", "", "Katerina Siniakova", "320301", "", "2026-10-23 (order of play: followed by, per feed)"),
]
for mid, pa, ida, sa, pb, idb, sb, when in WTA_QF:
    add(**{
        "id": f"AD-WTA-{mid}", "sport": "Tennis",
        "competition": "WTA 250 Kinoshita Group Japan Open, Osaka — singles quarter-final",
        "date": "2026-10-23", "start_utc": when,
        "side_a": pa, "side_b": pb, "fixture": f"{pa} v {pb}", "venue": "Osaka, JPN (hard, outdoor — per WTA feed)",
        "source_url": "https://www.wtatennis.com/tournaments/405/osaka/2026/scores",
        "source_name": "WTA official matches feed (api.wtatennis.com), live re-read 2026-10-22",
        "status": "unpriced",
        "unpriced_reason": ("WTA singles rankings/points could not be read from an official page in this "
                            "environment (rankings page returned no table; player API carries no ranking "
                            "field — live_checks L09). Seeds alone are not a sufficient strength input, "
                            "so prices are left blank rather than inferred."),
        "inputs": {"a": {"player": pa, "seed": sa or "unseeded", "last_result_this_event": wta_last_result(ida)},
                   "b": {"player": pb, "seed": sb or "unseeded", "last_result_this_event": wta_last_result(idb)}},
        "markets": {}, "pick": None,
    })
print(f"WTA QFs listed unpriced: {len(WTA_QF)}")

# ============================================================ LoL Worlds Swiss R1 — verified fixtures, unpriced
LOL_URL = "https://esports-api.lolesports.com/persisted/gw/getSchedule?hl=en-US"
lol_path = os.path.join(E5, "lolesports_schedule.json")
register_source("LoL Esports schedule feed (official Riot lolesports API)", LOL_URL,
                lol_path, E5MAN, "lolesports_schedule")
lol = json.load(open(lol_path))
lol_rows = [e for e in lol["data"]["schedule"]["events"]
            if e["state"] == "unstarted" and WIN_LO <= e["startTime"] < WIN_HI
            and e.get("match", {}).get("teams")
            and all(t.get("name") not in (None, "TBD") for t in e["match"]["teams"])]
lol_rows.sort(key=lambda e: e["startTime"])
for e in lol_rows:
    t1, t2 = e["match"]["teams"][0]["name"], e["match"]["teams"][1]["name"]
    add(**{
        "id": f"AD-LOL-{e['match']['id']}", "sport": "eSports",
        "competition": f"League of Legends World Championship 2026 — {e['league']['name']} {e.get('blockName','')}".strip(),
        "date": e["startTime"][:10], "start_utc": e["startTime"],
        "side_a": t1, "side_b": t2, "fixture": f"{t1} v {t2}",
        "venue": "", "source_url": "https://lolesports.com/en-US/leagues/worlds",
        "source_name": "Riot Games official LoL Esports schedule API (esports-api.lolesports.com)",
        "status": "unpriced",
        "unpriced_reason": ("The official schedule feed returns a 0-0 record for every team in these "
                            "Swiss-stage openers and no other verified strength input was read this "
                            "session; prices left blank rather than inferred from reputation."),
        "inputs": {"a": {"team": t1, "record_in_feed": "0-0"}, "b": {"team": t2, "record_in_feed": "0-0"}},
        "markets": {}, "pick": None,
    })
print(f"LoL matches listed unpriced: {len(lol_rows)}")

# ============================================================ coverage (every OLBG in-scope sport)
olbg = json.load(open(os.path.join(ROOT, "data", "olbg-structure.json")))
IN_SCOPE = [s for s in olbg["sports_enumerated"] if s["in_scope"]]
STATUS = {
 "Tennis": ("listed-unpriced", "4 WTA Osaka singles QFs on 23 Oct listed unpriced (rankings unreadable, L09). ATP Almaty/Brussels/Lyon QF pairings for 23 Oct were not final at capture — R16 still live on atptour.com (L08); next week's Paris draw unpublished at capture."),
 "Basketball": ("priced (EuroLeague) / blocked (NBA)", "29 EuroLeague fixtures priced from the official games feed. NBA pairings could not be read officially: nba.com pages render no fixtures in this environment, cdn.nba.com scoreboard returned HTTP 500, stats.nba.com fetch failed (L06) — NBA game counts per day only (e.g. 12 games 23 Oct per nba.com calendar)."),
 "Golf": ("coverage-only", "No official field/tee-time numeric input read this session; PGA/LPGA schedules captured in repo manifest (e5f2dad3) carry no priceable pairings for the window."),
 "Cricket": ("coverage-only", "ICC fixtures page captured in repo manifest returned content without a verified priceable numeric input read this session; no XI/rankings data originated from."),
 "Snooker": ("coverage-only", "BetVictor Northern Ireland Open quarter-finals (23 Oct) pairings did not exist at capture: wst.tv listed Round 3 for today 22 Oct only (L07)."),
 "Rugby Union": ("coverage-only", "URC/Premiership official pages in repo captures are JS shells/404s (unitedrugby.com fixtures 404 in e5f2dad3 manifest); no verified table read live this session."),
 "Rugby League": ("coverage-only", "RLWC 2026 pool pages captured in repo (rlwc2026.com 200) but no verified form table read live this session to originate lines from."),
 "Baseball": ("priced", "MLB World Series, 7 games (5-7 if necessary), priced from official MLB Stats API schedule + 2026 standings."),
 "Ice Hockey": ("priced", f"{len(nhl_rows)} NHL games 23 Oct-5 Nov priced from official NHL API schedule + standings (official endpoints also re-read live, L01/L02)."),
 "Motor Racing": ("coverage-only", "No head-to-head match market with a verified numeric input in window read this session (F1 calendar is event/outright format)."),
 "Darts": ("priced (capped)", "8 PDC European Championship round-one ties on 23 Oct priced from official European Tour OOM seeding; confidence capped at Medium (seed is not world ranking, AD-F04). Round-two pairings (24 Oct) are winner-v-winner TBD."),
 "Handball": ("coverage-only", "EHF official match pages returned 404 in repo captures (e5f2dad3 manifest); domestic-league tables were priced by Board Z (session-19b8e377) — not re-read live this session."),
 "Volleyball": ("coverage-only", "Volleyball World calendar captured in repo; league tables priced by Board Z (session-19b8e377) — not re-read live this session."),
 "Aussie Rules": ("coverage-only", "AFL official API returned 401 in repo captures; AFL men's season final was in September per the AFL fixture capture — no in-window men's fixture found."),
 "eSports": ("listed-unpriced", f"{len(lol_rows)} LoL Worlds Swiss round-one series on 23 Oct listed unpriced (feed records 0-0); later Swiss rounds are TBD-v-TBD in the official feed until each draw."),
 "Gaelic Football": ("coverage-only", "Distinct GAA sport (OLBG id 25), in scope per repo taxonomy note; county club fixtures are not published with a priceable official numeric input read this session — scope call flagged AD-F12."),
 "Greyhounds": ("coverage-only", "GBGB official racecards unreachable in repo captures (status 0); no official card read live this session."),
 "Badminton": ("coverage-only", "BWF calendar captured in repo (French Open in progress this week per 9359e596 capture); daily draws not read live this session."),
 "Table Tennis": ("coverage-only", "WTT events page captured in repo returned no priceable draw read this session."),
}
coverage = []
for s in IN_SCOPE:
    st, note = STATUS.get(s["name"], ("coverage-only", "No verified official numeric input read this session."))
    coverage.append({"olbg_id": s["id"], "sport": s["name"],
                     "olbg_url": f"https://www.olbg.com/betting-tips/{s['slug']}/{s['id']}",
                     "board_ad_status": st, "note": note})
extra_names = [c["sport"] for c in coverage]
for nm in ["Badminton", "Table Tennis"]:
    if nm not in extra_names:
        st, note = STATUS[nm]
        coverage.append({"olbg_id": None, "sport": nm, "olbg_url": "https://www.olbg.com/betting-tips",
                         "board_ad_status": st, "note": note + " (Not a standalone OLBG sport ID in data/olbg-structure.json; listed for completeness.)"})

# ============================================================ focus picks + predictions
row_by_id = {r["id"]: r for r in rows}
focus_out = []
for f in sorted(FOCUS, key=lambda x: -x["p"]):
    r = row_by_id[f["row_id"]]
    key = f"{f['row_id']}|{f['market']}|{f['selection']}"
    focus_out.append({**f, "fixture": r["fixture"], "date": r["date"],
                      "competition": r["competition"], "source_url": r["source_url"],
                      "inputs": r["inputs"], "prediction_key": key,
                      "prediction": PREDICTIONS.get(key, "")})
high_outside = []
for r in rows:
    if r["status"] == "priced" and r["pick"] and r["pick"]["confidence"] == "High" and not r["pick"]["in_focus_window"]:
        high_outside.append({"row_id": r["id"], "sport": r["sport"], "fixture": r["fixture"],
                             "date": r["date"], "selection": r["pick"]["selection"],
                             "p": r["pick"]["p"], "american": r["pick"]["american"],
                             "source_url": r["source_url"]})
high_outside.sort(key=lambda x: -x["p"])

flagged = [
 {"id": "AD-F01", "title": "70% rule vs -250 window arithmetic",
  "detail": "At fair odds, a selection with p>=0.70 prices at -233 or shorter; it sits inside the brief's -250..+10,000 focus window only while p<=0.7143 (fair -250). Genuine high-confidence selections stronger than that are therefore published separately as 'High — shorter than -250' instead of being relabelled or dropped.",
  "source_url": "https://buffedlizard55-lab.github.io/OLBG4/session-7c581d22/methodology.html"},
 {"id": "AD-F02", "title": "NHL standings are through 21 Oct games",
  "detail": "The official standings payload (standingsDateTimeUtc 2026-10-22T12:00:45Z, standings date 2026-10-21) does not include the 22 Oct slate, which had not been played at capture. Form inputs lag one matchday for teams playing on 22 Oct.",
  "source_url": NHL_STAND_URL},
 {"id": "AD-F03", "title": "pdc.tv direct fetch blocked by consent wall in this environment",
  "detail": "Fetching the official PDC schedule article returned only cookie-consent text. The Friday 23 Oct schedule was read from the search-index excerpt of that same pdc.tv page and the seeded bracket cross-checked against two verbatim republications of the official draw; every PDC row links the official pdc.tv article for manual review. Ties should be re-confirmed on pdc.tv before use.",
  "source_url": PDC_SCHED},
 {"id": "AD-F04", "title": "Darts prices use European Tour OOM seeding, not world ranking",
  "detail": "Seeding reflects 2026 European Tour earnings only. pdc.tv itself notes world number one Luke Littler is seeded 11 and Luke Humphries (world number two, seeded 12) withdrew on 22 Oct through illness (gastroenteritis). Darts confidence is capped at Medium; no leg handicap/total originated.",
  "source_url": "https://www.pdc.tv/news/2026/october/22/humphries-withdraws-from-machineseeker-european-championship"},
 {"id": "AD-F05", "title": "WTA Osaka quarter-finals unpriced — rankings not officially readable here",
  "detail": "wtatennis.com/rankings/singles returned no ranking table in this environment and the WTA player API object for Ann Li (326096) carries no ranking field. The four verified QFs are listed with seeds and last results only; prices blank.",
  "source_url": "https://www.wtatennis.com/rankings/singles"},
 {"id": "AD-F06", "title": "LoL Worlds Swiss openers unpriced — feed records are 0-0",
  "detail": "Riot's official schedule feed lists every Swiss round-one team at 0 wins / 0 losses and later Swiss slots as TBD v TBD. No strength input was invented; the eight named series are listed unpriced.",
  "source_url": "https://lolesports.com/en-US/leagues/worlds"},
 {"id": "AD-F07", "title": "EuroLeague: derived standings + Israeli home games staged abroad",
  "detail": "Records/PPG were computed by this build from the 61 played scores inside the official games feed (not copied from an official table). Per the feed's venue fields, Maccabi Rapyd Tel Aviv's listed home venue is Aleksandar Nikolic Hall and Hapoel IBI Tel Aviv's are in Botevgrad/Sofia — outside Israel; the flat +2.2 home edge is still applied and may overstate their edge.",
  "source_url": "https://www.euroleaguebasketball.net/en/euroleague/game-center/"},
 {"id": "AD-F08", "title": "NBA fixtures not officially readable in this environment",
  "detail": "Attempts 2026-10-22: nba.com/schedule and nba.com/games returned shells/calendar-counts only (23 Oct = 12 games per the calendar), cdn.nba.com todaysScoreboard returned HTTP 500, stats.nba.com fetch failed; committed captures show scheduleLeagueV2 at HTTP 403. No NBA pairing is published rather than risk an unverified one.",
  "source_url": "https://www.nba.com/schedule"},
 {"id": "AD-F09", "title": "Tennis (ATP) and snooker pairings for 23 Oct did not exist at capture",
  "detail": "atptour.com showed Almaty/Brussels/Lyon round-of-16 matches still live on 22 Oct, so Friday quarter-final pairings were incomplete; wst.tv listed Northern Ireland Open Round 3 on 22 Oct with quarter-finals to follow. Neither sport's 23 Oct pairings are guessed.",
  "source_url": "https://www.atptour.com/en/scores/current"},
 {"id": "AD-F10", "title": "MLB Games 5-7 are if-necessary; run line uses a Normal approximation",
  "detail": "The official schedule flags World Series Games 5, 6 and 7 as if-necessary. Moneylines use log5 on verified 2026 home/away win percentages; run-line and total prices use a disclosed Normal run-differential approximation (sigma 4.1 / 4.6) rather than a full run-distribution model. Probable pitchers were not read and are not reflected.",
  "source_url": MLB_SCHED_URL},
 {"id": "AD-F11", "title": "Markets not originated",
  "detail": "Period/quarter lines, player props, correct score, outrights, 180s/most-180s (darts), set betting (tennis), map handicaps (LoL) and team totals were investigated, but no verified official input for them was read this session, so they are absent rather than invented. Originated: moneyline/match winner everywhere priced, plus puck/run lines, spreads and match totals where the model supports them.",
  "source_url": "https://buffedlizard55-lab.github.io/OLBG4/session-7c581d22/markets.html"},
 {"id": "AD-F12", "title": "Gaelic Football scope interpretation",
  "detail": "The brief excludes 'football' and hurling. Following the repo taxonomy (data/olbg-structure.json), OLBG 'Football' (id 1) is soccer and is excluded; Gaelic Football (id 25) is a distinct GAA sport and is carried as in-scope coverage-only. Flagged for the owner's confirmation; no row depends on this call.",
  "source_url": "https://www.olbg.com/betting-tips/Gaelic_Football/25"},
 {"id": "AD-F13", "title": "What was not checked on any row",
  "detail": "Injuries, line-ups/starting goaltenders and pitchers, rest/travel beyond the published schedule, weather, referees, head-to-head history beyond the form fields printed per row, and any market/line movement. Confidence grades reflect the documented model + sample size only.",
  "source_url": "https://buffedlizard55-lab.github.io/OLBG4/session-7c581d22/methodology.html"},
 {"id": "AD-F14", "title": "Integration request (not applied by Board AD)",
  "detail": "Root README.md / index.html are another claim's files while PR #102 (Board AC) is open. Request: when a future integration owner next claims the root, add a Board AD pointer (session-7c581d22/) alongside Boards X/W/Z/AC.",
  "source_url": "https://github.com/buffedlizard55-lab/OLBG4/pull/102"},
]

live_checks = [
 {"id": "L01", "url": "https://api-web.nhle.com/v1/standings/now", "fetched": "2026-10-22 (this session)",
  "observed": "\"standingsDateTimeUtc\":\"2026-10-22T12:00:45Z\"; first team Carolina Hurricanes GP11 W8 L2 OT1 PTS17 GF42 GA27 streak W1.",
  "compared_with": "data/session-e5f2dad3/raw/nhl_standings_2026-10-22.json — identical Carolina line (11, 8-2-1, 17, 42, 27).", "result": "match"},
 {"id": "L02", "url": "https://api-web.nhle.com/v1/schedule/2026-10-24", "fetched": "2026-10-22 (this session)",
  "observed": "2026-10-24: 12 games; id 2026020168 Anaheim Ducks @ Philadelphia Flyers 17:00Z Xfinity Mobile Arena; 2026020169 LAK@NJD Prudential Center; 2026020170 SJS@BOS TD Garden; 2026020171 NYR@OTT Canadian Tire Centre.",
  "compared_with": "Committed nhl_schedule_2026-10-24.json parse — verify.py asserts these four game IDs/teams/venues.", "result": "match"},
 {"id": "L03", "url": MLB_SCHED_URL, "fetched": "2026-10-22 (this session)",
  "observed": "totalGames 7, all World Series: G1 2026-10-23 Tampa Bay Rays @ Milwaukee Brewers, American Family Field, gamePk 849805; G5/G6/G7 ifNecessary Y (gamePks 849799/849801/849800).",
  "compared_with": "data/session-e5f2dad3/raw/mlb_schedule.json — same 7 gamePks, venues, if-necessary flags.", "result": "match"},
 {"id": "L04", "url": WTA_API, "fetched": "2026-10-22 (this session)",
  "observed": "Feed lastUpdated 2026-10-22T09:46:03Z. QFs 2026-10-23: LS004 Ann Li (seed 1) v Lilli Tagger 11:30+09:00; LS005 Talia Gibson (4) v Ashlyn Krueger; LS006 Katie Boulter (8) v Antonia Ruzic; LS007 Mary Stoiana v Katerina Siniakova. R2 today: Li d Sonmez 6-3 6-1; Siniakova d Linette 6-4 6-1; Stoiana d Uchijima 6-2 2-6 6-3; Ruzic d Day 6-4 ret.",
  "compared_with": "Committed wta_405_matches.json.gz (08:37Z) had LS007 opponent TBD; live feed resolves it to Siniakova — live value used, difference disclosed.", "result": "newer than capture; live value used"},
 {"id": "L05", "url": PDC_SCHED, "fetched": "2026-10-22 (this session)",
  "observed": "Direct fetch returned cookie-consent text only (7 chunks, no article body). Search excerpt of the same pdc.tv URL lists Friday 23 Oct R1 x8: Joyce v Wattimena, Ratajski v Chisnall, Aspinall v Reyes, Clayton v Springer, Littler v O'Connor, Nijman v Schindler, Doets v Van Gerwen, Rock v Dobey (1900-2300 CEST). Seeded bracket read from verbatim republications of the official pdc.tv draw (seeds printed per tie). pdc.tv 22 Oct: Humphries withdrawn (gastroenteritis) — affects Thursday's tie only.",
  "compared_with": "pdc.tv draw article excerpt (18 Oct) and schedule article excerpt (19 Oct) agree on all eight Friday pairings.", "result": "match (via excerpt; AD-F03)"},
 {"id": "L06", "url": "https://www.nba.com/games?date=2026-10-24", "fetched": "2026-10-22 (this session)",
  "observed": "Calendar counts only (23 Oct: 12 GAMES, 24 Oct: 8 GAMES) then 'Sorry, something went wrong.' nba.com/schedule returned filter UI only; cdn.nba.com todaysScoreboard_00.json HTTP 500; stats.nba.com scoreboardv3 fetch failed.",
  "compared_with": "Committed manifest: scheduleLeagueV2.json HTTP 403, stats.nba.com status 0.", "result": "no official pairing readable — NBA coverage-only (AD-F08)"},
 {"id": "L07", "url": "https://www.wst.tv/matches", "fetched": "2026-10-22 (this session)",
  "observed": "BetVictor Northern Ireland Open: Round 3 scheduled Thu 22 Oct (Matthew Selt v Sam Craigie, Kyren Wilson v Pang Junxu, Anthony McGill v Mateusz Baranowski, Elliot Slessor v Ricky Walden, Mark Williams v Martin O'Donnell, David Gilbert v Ka Wai Cheung, Jordan Brown v Scott Donaldson, Jak Jones v Daniel Wells). No 23 Oct quarter-final pairings listed.",
  "compared_with": "—", "result": "QF pairings do not exist yet; snooker coverage-only (AD-F09)"},
 {"id": "L08", "url": "https://www.atptour.com/en/scores/current", "fetched": "2026-10-22 (this session)",
  "observed": "Round of 16 live today: Almaty Machac v Khachanov (5); Brussels Collignon v Lehecka (2); Lyon Vacherot (3) v Van Assche, Gojo v Altmaier.",
  "compared_with": "—", "result": "Friday ATP QF pairings incomplete at capture (AD-F09)"},
 {"id": "L09", "url": "https://www.wtatennis.com/rankings/singles", "fetched": "2026-10-22 (this session)",
  "observed": "Page returned site chrome/notifications only — no ranking rows. https://api.wtatennis.com/tennis/players/326096 returned {\"id\":326096,\"fullName\":\"Ann Li\",...} with no ranking field.",
  "compared_with": "—", "result": "rankings unreadable — WTA listed unpriced (AD-F05)"},
 {"id": "L10", "url": "https://github.com/buffedlizard55-lab/OLBG4/blob/main/data/session-e5f2dad3/manifest.json", "fetched": "2026-10-22 (this session)",
  "observed": "build.py re-hashed every payload it parsed and asserted equality with data/session-e5f2dad3/manifest.json and data/session-9359e596/capture/20261022T083834Z/manifest.json before use (see sources.json).",
  "compared_with": "Manifest SHA-256 values recorded at capture on 2026-10-22.", "result": "match (asserted in code)"},
]

board = {
    "schema": "olbg4.board-ad/1", "session": "arena/7c581d22-olbg4", "board": "AD",
    "captured_on": CAPTURE, "window": {"from": "2026-10-23", "to": "2026-11-05",
                                        "basis": "official local fixture date (NHL gameWeek date, EuroLeague local date, MLB officialDate, WTA/PDC published date); LoL uses the feed UTC start date"},
    "method": {
        "prices": "Our own originated fair prices: decimal = 1/p, no margin. No bookmaker or OLBG price is read.",
        "confidence": "High: model p>=0.70 (plus sample-size caps); Medium: 0.58<=p<0.70; Low: p<0.58.",
        "focus_rule": "Focus predictions are written for originated selections graded High whose fair American price sits inside -250..+10,000.",
        "nhl": "Poisson goals from shrinkage-adjusted GF/GA rates (k=8 games toward league mean), home x1.05 / away x0.95; moneyline includes OT (tie split by expected-goals share); puck line from the same score matrix; total line = nearest .5 to expected final total incl. the OT goal. A High grade additionally requires both teams to have >=8 games in the standings snapshot (one row is capped by this: Los Angeles, 7 GP).",
        "euroleague": "Expected points from shrinkage-adjusted PF/PA per game (k=6), derived from the 61 played scores in the official feed; Normal margin sigma 12.0 / total sigma 19.0; flat +2.2 home edge. High capped unless both teams have >=7 games in the derived sample.",
        "mlb": "Moneyline: log5 on 2026 home/away split win percentages. Run line/total: expected runs from RS/RA rates with a disclosed Normal approximation (diff sigma 4.1, total sigma 4.6). Probable pitchers not read.",
        "pdc": "Logistic on European Tour Order of Merit seed difference (k=0.035 per seed place), best-of-11 legs; confidence capped at Medium because seeding is not world ranking.",
        "unpriced": "Fixtures verified on an official source but lacking a verified strength input are published with blank prices and a stated reason. Unverified values are never inferred.",
    },
    "rows": rows, "focus_picks": focus_out, "high_shorter_than_minus250": high_outside,
    "coverage": coverage, "flagged": flagged, "live_checks": live_checks,
}
os.makedirs(OUTDIR, exist_ok=True)
json.dump(board, open(os.path.join(OUTDIR, "board.json"), "w"), indent=1, ensure_ascii=False)
json.dump({"schema": "olbg4.board-ad.sources/1", "session": "arena/7c581d22-olbg4", "sources": sources},
          open(os.path.join(OUTDIR, "sources.json"), "w"), indent=1, ensure_ascii=False)
json.dump(flagged, open(os.path.join(OUTDIR, "flagged.json"), "w"), indent=1, ensure_ascii=False)
json.dump(live_checks, open(os.path.join(OUTDIR, "live_checks.json"), "w"), indent=1, ensure_ascii=False)

from collections import Counter
print("\nRows by sport:", dict(Counter(r["sport"] for r in rows)))
print("Priced:", sum(r["status"] == "priced" for r in rows), "| Unpriced:", sum(r["status"] == "unpriced" for r in rows))
print("Confidence (match picks):", dict(Counter(r["pick"]["confidence"] for r in rows if r["pick"])))
print(f"\nFOCUS PICKS (High, in -250..+10000): {len(focus_out)}")
for f in focus_out:
    print(f"  {f['prediction_key']}  p={f['p']} amer={f['american']}  pred={'OK' if f['prediction'] else 'MISSING'}")
print(f"\nHigh moneyline picks shorter than -250: {len(high_outside)}")
for h in high_outside: print(f"  {h['row_id']} {h['selection']} p={h['p']} amer={h['american']}")
print("\nSources registered:", len(sources), "| all hashes matched manifests where applicable")
