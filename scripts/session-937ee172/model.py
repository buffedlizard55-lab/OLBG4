"""Own-line origination for NHL games from the official NHL standings only.

Method (documented on the methodology page):
  L      = league goals per team-game = sum(GF)/sum(GP) over all 32 clubs
  Shrinkage: per-game rates are pulled toward league average with K = 10 prior games
    att_T = (GF_T + K*L) / (GP_T + K);  def_T = (GA_T + K*L) / (GP_T + K)
  lam_H  = att_H * def_A / L          expected home goals
  lam_A  = att_A * def_H / L          expected away goals
  Goals ~ independent Poisson(lam). Joint distribution summed to 15 goals each.
  Match winner = P(H>A) + 0.5*P(H=A)  (overtime / shootout treated as a coin toss; no home edge added).
  Puck line  = P(home margin >= 2) for home -1.5 (OT wins counted as one-goal margin).
  Match total = P(H+A >= line+0.5) for 5.5 and 6.5.
No bookmaker or OLBG price is an input to the probability. Bookmaker prices are shown only as a reference
for comparison and never change a probability or a confidence label.
"""
import json, math, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "data/session-937ee172/official/nhl_2026-10-24.json"
OUT = ROOT / "data/session-937ee172/desk.json"

K = 10          # prior weight in games, shrinks small samples toward league average
MIN_GP_HIGH = 10  # High confidence requires both clubs to have at least this many games

def pois(lam, kmax=16):
    p = [math.exp(-lam)]
    for k in range(1, kmax):
        p.append(p[-1] * lam / k)
    return p

def american(p):
    if p <= 0 or p >= 1:
        return None
    if p >= 0.5:
        return round(-100 * p / (1 - p))
    return round(100 * (1 - p) / p)

def dec_to_prob_american(a):
    a = int(a)
    return 100 / (a + 100) if a > 0 else -a / (-a + 100)

def run():
    d = json.loads(SRC.read_text())
    T = {t["abbrev"]: t for t in d["teams"]}
    L = sum(t["gf"] for t in T.values()) / sum(t["gp"] for t in T.values())
    rows = []
    for g in d["games_2026_10_24"]:
        H, A = T[g["home"]], T[g["away"]]
        att = lambda t: (t["gf"] + K * L) / (t["gp"] + K)
        dfn = lambda t: (t["ga"] + K * L) / (t["gp"] + K)
        lamH = att(H) * dfn(A) / L
        lamA = att(A) * dfn(H) / L
        pH, pA = pois(lamH), pois(lamA)
        pHwin = pAwin = pTie = pHmargin2 = 0.0
        tot = {5: 0.0, 6: 0.0}
        for h in range(len(pH)):
            for a in range(len(pA)):
                p = pH[h] * pA[a]
                if h > a: pHwin += p
                elif h < a: pAwin += p
                else: pTie += p
                if h - a >= 2: pHmargin2 += p
                s = h + a
                if s >= 6: tot[5] += p     # over 5.5
                if s >= 7: tot[6] += p     # over 6.5
        pHml = pHwin + 0.5 * pTie
        pAml = pAwin + 0.5 * pTie
        pick_side = g["home"] if pHml >= pAml else g["away"]
        p_pick = max(pHml, pAml)
        dk = g["dk_ml"]
        dk_side_price = dk[pick_side]
        implied = dec_to_prob_american(dk_side_price)
        _px = int(dk_side_price)
        ref_ok = -250 <= _px <= 10000
        sample_ok = min(H["gp"], A["gp"]) >= MIN_GP_HIGH
        if p_pick >= 0.70 and ref_ok and sample_ok:
            conf = "High"
        elif p_pick >= 0.60:
            conf = "Medium"
        else:
            conf = "Low"
        rows.append({
            "id": g["id"], "away": g["away"], "home": g["home"], "start_utc": g["start_utc"], "venue": g["venue"],
            "away_record": f'{A["w"]}-{A["l"]}-{A["otl"]}', "home_record": f'{H["w"]}-{H["l"]}-{H["otl"]}',
            "away_gf_pg": round(A["gf"]/A["gp"],2), "away_ga_pg": round(A["ga"]/A["gp"],2),
            "home_gf_pg": round(H["gf"]/H["gp"],2), "home_ga_pg": round(H["ga"]/H["gp"],2),
            "away_streak": A["streak"], "home_streak": H["streak"],
            "lam_home": round(lamH,3), "lam_away": round(lamA,3),
            "p_home_ml": round(pHml,4), "p_away_ml": round(pAml,4),
            "fair_home_ml": american(pHml), "fair_away_ml": american(pAml),
            "p_home_minus_1_5": round(pHmargin2,4), "p_away_plus_1_5": round(1-pHmargin2,4),
            "p_over_5_5": round(tot[5],4), "p_under_5_5": round(1-tot[5],4),
            "p_over_6_5": round(tot[6],4), "p_under_6_5": round(1-tot[6],4),
            "pick_side": pick_side, "pick_p": round(p_pick,4), "pick_fair_american": american(p_pick),
            "confidence": conf,
            "min_gp": min(H["gp"], A["gp"]), "ref_price_in_window": ref_ok,
            "dk_reference_ml_pick_side": dk_side_price,
            "dk_reference_implied_p": round(implied,4),
            "edge_vs_reference": round(p_pick - implied,4),
            "olbg_seen": g["olbg_seen"], "dk_ml": dk,
        })
    league = {"L_goals_per_team_game": round(L,4), "teams": len(T), "gp_sum": sum(t["gp"] for t in T.values())}
    out = {"generated_from": str(SRC.relative_to(ROOT)), "league": league, "games": rows,
           "sources": d["sources"], "as_of_utc": d["as_of_utc"]}
    OUT.write_text(json.dumps(out, indent=2))
    return out

if __name__ == "__main__":
    o = run()
    print("L=", o["league"])
    for r in o["games"]:
        print(f'{r["away"]}@{r["home"]} lam {r["lam_away"]}-{r["lam_home"]} pH {r["p_home_ml"]} pA {r["p_away_ml"]} pick {r["pick_side"]} {r["pick_p"]} fair {r["pick_fair_american"]} DK {r["dk_reference_ml_pick_side"]} edge {r["edge_vs_reference"]} conf {r["confidence"]} O5.5 {r["p_over_5_5"]} O6.5 {r["p_over_6_5"]} H-1.5 {r["p_home_minus_1_5"]}')
