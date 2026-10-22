#!/usr/bin/env python3
"""Board X (session arena/e1161e0e-olbg4) — fresh-window desk, 23 Oct-5 Nov 2026.
Every fixture/form value below was read on an official league/tour/federation page
(or, for NBA 2025-26 final records, the Basketball-Reference archive cross-checked
against NBA.com-published figures — disclosed per-row). OLBG.com is used only for
the sport taxonomy cross-check (repo data/sports.json). No bookmaker price is read.
All prices are OUR originated FAIR prices (decimal = 1/p, no margin).
Run: python3 session-e1161e0e/build.py  -> data/session-e1161e0e/board.json
"""
import json, math, os
from datetime import date

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "session-e1161e0e", "board.json")
CAPTURE = "2026-10-22"

def clamp(x, lo, hi): return max(lo, min(hi, x))
def phi(x): return 0.5 * (1 + math.erf(x / math.sqrt(2)))
def inv_phi(p):
    # Acklam approximation, sufficient for spread rounding
    a=[-3.969683028665376e+01,2.209460984245205e+02,-2.759285104469687e+02,1.383577518672690e+02,-3.066479806614716e+01,2.506628277459239e+00]
    b=[-5.447609879822406e+01,1.615858368580409e+02,-1.556989798598866e+02,6.680131188771972e+01,-1.328068155288572e+01]
    c=[-7.784894002430293e-03,-3.223964580411365e-01,-2.400758277161838e+00,-2.549732539343734e+00,4.374664141464968e+00,2.938163982698783e+00]
    d=[7.784695709041462e-03,3.224671290700398e-01,2.445134137142996e+00,3.754408661907416e+00]
    plow, phigh = 0.02425, 1-0.02425
    if p < plow:
        q = math.sqrt(-2*math.log(p)); return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5])/((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > phigh:
        q = math.sqrt(-2*math.log(1-p)); return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5])/((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5; r = q*q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q/(((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)
def dec(p): return round(1.0/p, 2)
def amer(p):
    d = 1.0/p
    return int(round(-100/(d-1))) if d < 2 else int(round((d-1)*100))
def rhalf(x): return math.floor(x*2+0.5)/2

rows = []
def add(**kw): rows.append(kw)

# ============================== NHL =========================================
# Standings read on https://www.nhl.com/standings (current as of Oct 22, 3:24 AM EDT):
# team: GP,W,L,OT,PTS,GF,GA,home,away,L10,streak
NHL_URL = "https://www.nhl.com/standings"; NHL_SCHED = "https://www.nhl.com/schedule"
NHL = {
 "Boston Bruins":(10,7,2,1,15,36,22,"3-1-0","4-1-1","7-2-1","OT1"),
 "Tampa Bay Lightning":(9,7,2,0,14,31,23,"5-0-0","2-2-0","7-2-0","W3"),
 "Ottawa Senators":(10,7,3,0,14,29,24,"4-1-0","3-2-0","7-3-0","W1"),
 "Carolina Hurricanes":(11,8,2,1,17,42,27,"2-1-1","6-1-0","8-2-0","W1"),
 "New York Rangers":(11,7,3,1,15,33,24,"6-0-0","1-3-1","7-2-1","W1"),
 "New York Islanders":(9,5,3,1,11,27,20,"4-1-0","1-2-1","5-3-1","W2"),
 "Florida Panthers":(10,5,3,2,12,31,30,"2-1-0","3-2-2","5-3-2","L1"),
 "Toronto Maple Leafs":(11,5,4,2,12,38,35,"3-3-1","2-1-1","5-3-2","W2"),
 "Washington Capitals":(9,5,4,0,10,30,29,"4-2-0","1-2-0","5-4-0","L1"),
 "New Jersey Devils":(9,5,4,0,10,29,30,"4-2-0","1-2-0","5-4-0","W1"),
 "Montreal Canadiens":(9,4,3,2,10,30,34,"3-2-1","1-1-1","4-3-2","OT1"),
 "Buffalo Sabres":(10,4,4,2,10,28,37,"3-3-0","1-1-2","4-4-2","L1"),
 "Detroit Red Wings":(9,3,3,3,9,23,28,"3-3-1","0-0-2","3-3-3","OT1"),
 "Philadelphia Flyers":(12,3,6,3,9,20,37,"2-2-2","1-4-1","3-5-2","W3"),
 "Pittsburgh Penguins":(10,3,6,1,7,33,38,"2-1-0","1-5-1","3-6-1","L4"),
 "Columbus Blue Jackets":(8,3,5,0,6,20,29,"3-3-0","0-2-0","3-5-0","L2"),
 "Utah Mammoth":(10,7,3,0,14,38,31,"3-1-0","4-2-0","7-3-0","W1"),
 "Minnesota Wild":(10,6,2,2,14,31,25,"4-0-0","2-2-2","6-2-2","OT1"),
 "Dallas Stars":(9,5,3,1,11,23,15,"2-2-0","3-1-1","5-3-1","W3"),
 "Vegas Golden Knights":(11,8,3,0,16,44,30,"5-2-0","3-1-0","7-3-0","L1"),
 "Edmonton Oilers":(9,7,1,1,15,41,27,"2-1-1","5-0-0","7-1-1","W2"),
 "Seattle Kraken":(10,6,3,1,13,39,34,"2-1-0","4-2-1","6-3-1","W1"),
 "Colorado Avalanche":(10,5,4,1,11,41,31,"3-1-1","2-3-0","5-4-1","L2"),
 "San Jose Sharks":(10,5,4,1,11,27,35,"2-2-0","3-2-1","5-4-1","W1"),
 "Winnipeg Jets":(9,4,3,2,10,24,26,"2-2-1","2-1-1","4-3-2","L2"),
 "Nashville Predators":(8,3,2,3,9,23,24,"2-2-1","1-0-2","3-2-3","W1"),
 "St. Louis Blues":(9,4,4,1,9,29,29,"2-0-1","2-4-0","4-4-1","W1"),
 "Anaheim Ducks":(9,4,5,0,8,26,29,"1-3-0","3-2-0","4-5-0","L4"),
 "Chicago Blackhawks":(9,3,6,0,6,21,36,"3-2-0","0-4-0","3-6-0","L1"),
 "Vancouver Canucks":(11,2,8,1,5,33,51,"1-3-0","1-5-1","1-8-1","L2"),
 "Los Angeles Kings":(7,1,4,2,4,17,27,"0-3-0","1-1-2","1-4-2","W1"),
 "Calgary Flames":(8,2,6,0,4,17,37,"1-3-0","1-3-0","2-6-0","W1"),
}
def nhl_rating(t):
    gp,w,l,ot,pts,gf,ga = NHL[t][:7]
    pct = pts/(2*gp)
    return 0.5 + (pct-0.5)*gp/(gp+12) + 0.012*(gf-ga)/gp
def nhl_game(d, away, home, tm, note=""):
    ph = clamp(0.5 + (nhl_rating(home)-nhl_rating(away))*0.80 + 0.035, 0.08, 0.92)
    def gpg(t, col): 
        gp = NHL[t][0]; v = NHL[t][col]
        return (v + 3.05*10)/(gp+10)
    eh = (gpg(home,5)+gpg(away,6))/2; ea = (gpg(away,5)+gpg(home,6))/2
    tmean = clamp(eh+ea, 4.5, 8.5); tline = rhalf(tmean)
    pover = 1-phi((tline-tmean)/1.9)
    p_home_cover = 1-phi((1.5-(eh-ea))/2.0)   # home -1.5
    hf, af = NHL[home], NHL[away]
    add(sport="Ice Hockey", competition="NHL 2026-27 Regular Season", date=d, time_et=tm,
        home=home, away=away, venue="",
        form_home=f"{hf[1]}-{hf[2]}-{hf[3]}, {hf[4]} pts, GF {hf[5]} GA {hf[6]}, home {hf[7]}, L10 {hf[9]}, streak {hf[10]}",
        form_away=f"{af[1]}-{af[2]}-{af[3]}, {af[4]} pts, GF {af[5]} GA {af[6]}, away {af[8]}, L10 {af[9]}, streak {af[10]}",
        p_home=round(ph,3), p_away=round(1-ph,3),
        markets={"Moneyline (incl. OT/SO)": {home: dec(ph), away: dec(1-ph)},
                 f"Puck line {home} -1.5 / {away} +1.5": {home+" -1.5": dec(p_home_cover), away+" +1.5": dec(1-p_home_cover)},
                 f"Total goals {tline}": {"Over": dec(pover), "Under": dec(1-pover)}},
        exp_home=round(eh,2), exp_away=round(ea,2), total_line=tline, p_over=round(pover,3),
        p_puck_home=round(p_home_cover,3),
        sample=f"NHL GP: {home} {hf[0]}, {away} {af[0]} (standings current as of Oct 22 03:24 EDT; Oct 22 evening games not included)",
        source_name="NHL.com standings + schedule (official)", source_url=NHL_URL,
        fixture_url=NHL_SCHED, note=note)
for d,aw,ho,tm,n in [
 ("2026-10-23","Montreal Canadiens","Chicago Blackhawks","8:00 PM ET",""),
 ("2026-10-23","Tampa Bay Lightning","Colorado Avalanche","9:00 PM ET",""),
 ("2026-10-24","Anaheim Ducks","Philadelphia Flyers","1:00 PM ET",""),
 ("2026-10-24","Los Angeles Kings","New Jersey Devils","3:30 PM ET",""),
 ("2026-10-24","Carolina Hurricanes","St. Louis Blues","7:00 PM ET",""),
 ("2026-10-24","Vegas Golden Knights","Columbus Blue Jackets","7:00 PM ET",""),
 ("2026-10-24","Toronto Maple Leafs","Edmonton Oilers","7:00 PM ET",""),
 ("2026-10-24","San Jose Sharks","Boston Bruins","7:00 PM ET",""),
 ("2026-10-24","New York Rangers","Ottawa Senators","7:00 PM ET",""),
 ("2026-10-24","Buffalo Sabres","Washington Capitals","7:00 PM ET",""),
 ("2026-10-24","Nashville Predators","Pittsburgh Penguins","7:00 PM ET",""),
 ("2026-10-24","Tampa Bay Lightning","Utah Mammoth","9:00 PM ET",""),
 ("2026-10-24","Detroit Red Wings","Calgary Flames","10:00 PM ET",""),
 ("2026-10-24","Minnesota Wild","Seattle Kraken","10:00 PM ET",""),
 ("2026-10-25","Florida Panthers","Chicago Blackhawks","3:00 PM ET",""),
 ("2026-10-25","New York Islanders","Dallas Stars","6:00 PM ET",""),
 ("2026-10-25","Montreal Canadiens","Winnipeg Jets","7:00 PM ET","2026 Tim Hortons NHL Heritage Classic, Princess Auto Stadium, Winnipeg (NHL.com schedule release)"),
 ("2026-10-25","Colorado Avalanche","Nashville Predators","8:00 PM ET",""),
 ("2026-10-25","Minnesota Wild","Vancouver Canucks","10:00 PM ET",""),
 ("2026-10-26","Los Angeles Kings","New York Rangers","7:00 PM ET",""),
 ("2026-10-26","Toronto Maple Leafs","Calgary Flames","8:30 PM ET",""),
 ("2026-10-26","Detroit Red Wings","Edmonton Oilers","9:30 PM ET",""),
 ("2026-10-27","Columbus Blue Jackets","Philadelphia Flyers","7:00 PM ET","Oct 27 slate as listed at capture; may be incomplete — flagged"),
 ("2026-10-27","New Jersey Devils","Dallas Stars","8:00 PM ET",""),
 ("2026-10-27","Los Angeles Kings","Chicago Blackhawks","8:00 PM ET",""),
 ("2026-10-27","Montreal Canadiens","St. Louis Blues","8:00 PM ET",""),
]: nhl_game(d,aw,ho,tm,n)

# ============================== NBA =========================================
# Fixtures: NBA.com schedule (Week 1). Records: final 2025-26 W-L (Basketball-Reference
# archive; headline records cross-check with NBA.com-published figures, e.g. OKC 64-18).
NBA_URL="https://www.nba.com/standings"; NBA_SCHED="https://www.nba.com/schedule"
NBA = {"Oklahoma City Thunder":(64,18),"San Antonio Spurs":(62,20),"Detroit Pistons":(60,22),
 "Boston Celtics":(56,26),"Denver Nuggets":(54,28),"Los Angeles Lakers":(53,29),"New York Knicks":(53,29),
 "Cleveland Cavaliers":(52,30),"Houston Rockets":(52,30),"Minnesota Timberwolves":(49,33),
 "Atlanta Hawks":(46,36),"Toronto Raptors":(46,36),"Orlando Magic":(45,37),"Philadelphia 76ers":(45,37),
 "Phoenix Suns":(45,37),"Charlotte Hornets":(44,38),"Miami Heat":(43,39),"Portland Trail Blazers":(42,40),
 "LA Clippers":(42,40),"Golden State Warriors":(37,45),"Milwaukee Bucks":(32,50),"Chicago Bulls":(31,51),
 "Dallas Mavericks":(26,56),"New Orleans Pelicans":(26,56),"Memphis Grizzlies":(25,57),
 "Sacramento Kings":(22,60),"Utah Jazz":(22,60),"Brooklyn Nets":(20,62),"Indiana Pacers":(19,63),
 "Washington Wizards":(17,65)}
def logit(p): return math.log(p/(1-p))
def sig(x): return 1/(1+math.exp(-x))
def nba_str(t):
    w,l = NBA[t]; return 0.5 + (w/(w+l)-0.5)*0.75
def nba_game(d, away, home, tm, venue=""):
    ph = clamp(sig(logit(nba_str(home))-logit(nba_str(away))+0.24), 0.05, 0.95)
    spread = -rhalf(inv_phi(ph)*11.5)
    add(sport="Basketball", competition="NBA 2026-27 Regular Season (Week 1)", date=d, time_et=tm,
        home=home, away=away, venue=venue,
        form_home=f"2025-26 final record {NBA[home][0]}-{NBA[home][1]}",
        form_away=f"2025-26 final record {NBA[away][0]}-{NBA[away][1]}",
        p_home=round(ph,3), p_away=round(1-ph,3),
        markets={"Moneyline": {home: dec(ph), away: dec(1-ph)},
                 f"Spread {home} {spread:+.1f}": {home+f" {spread:+.1f}": dec(0.5), away+f" {-spread:+.1f}": dec(0.5)},
                 "Total points": {"—": "not originated (no official pace/efficiency table captured)"}},
        spread_home=spread,
        sample="82-game 2025-26 records; 2026-27 sample is 0-2 games at capture and is not used",
        source_name="NBA.com schedule (official fixture); 2025-26 records via Basketball-Reference archive cross-checked to NBA.com figures — disclosed",
        source_url=NBA_SCHED, fixture_url=NBA_SCHED, note="")
for d,aw,ho,tm,v in [
 ("2026-10-23","Chicago Bulls","Milwaukee Bucks","8:00 PM ET","Fiserv Forum, Milwaukee"),
 ("2026-10-23","New York Knicks","Boston Celtics","7:00 PM ET","TD Garden, Boston"),
 ("2026-10-23","Atlanta Hawks","Charlotte Hornets","7:00 PM ET","Spectrum Center, Charlotte"),
 ("2026-10-23","Dallas Mavericks","Indiana Pacers","7:00 PM ET","Gainbridge Fieldhouse, Indianapolis"),
 ("2026-10-23","Minnesota Timberwolves","Orlando Magic","7:00 PM ET","Kia Center, Orlando"),
 ("2026-10-23","Toronto Raptors","Washington Wizards","7:00 PM ET","Capital One Arena, Washington"),
 ("2026-10-23","Detroit Pistons","Miami Heat","8:00 PM ET","Kaseya Center, Miami"),
 ("2026-10-23","Houston Rockets","San Antonio Spurs","9:30 PM ET","Moody Center, Austin (NBA.com schedule release)"),
 ("2026-10-23","New Orleans Pelicans","Utah Jazz","9:30 PM ET","Delta Center, Salt Lake City"),
 ("2026-10-23","Memphis Grizzlies","Golden State Warriors","10:00 PM ET","Chase Center, San Francisco"),
 ("2026-10-23","LA Clippers","Los Angeles Lakers","10:00 PM ET","Crypto.com Arena, Los Angeles"),
 ("2026-10-23","Portland Trail Blazers","Sacramento Kings","10:00 PM ET",""),
 ("2026-10-24","Miami Heat","Charlotte Hornets","6:00 PM ET",""),
 ("2026-10-24","Brooklyn Nets","Cleveland Cavaliers","7:30 PM ET",""),
 ("2026-10-24","Milwaukee Bucks","Philadelphia 76ers","7:30 PM ET",""),
 ("2026-10-24","Washington Wizards","Chicago Bulls","8:00 PM ET",""),
 ("2026-10-24","San Antonio Spurs","Dallas Mavericks","8:00 PM ET",""),
 ("2026-10-24","Houston Rockets","Atlanta Hawks","8:30 PM ET",""),
 ("2026-10-24","New Orleans Pelicans","Denver Nuggets","9:00 PM ET",""),
 ("2026-10-24","Golden State Warriors","Phoenix Suns","10:00 PM ET",""),
 ("2026-10-25","Los Angeles Lakers","Utah Jazz","5:00 PM ET",""),
 ("2026-10-25","Indiana Pacers","Brooklyn Nets","6:00 PM ET",""),
 ("2026-10-25","Orlando Magic","New York Knicks","7:00 PM ET",""),
 ("2026-10-25","Toronto Raptors","Minnesota Timberwolves","7:00 PM ET",""),
 ("2026-10-25","LA Clippers","Oklahoma City Thunder","7:00 PM ET",""),
 ("2026-10-25","Detroit Pistons","Philadelphia 76ers","7:30 PM ET",""),
 ("2026-10-25","Memphis Grizzlies","Sacramento Kings","9:00 PM ET",""),
]: nba_game(d,aw,ho,tm,v)

# ============================== MLB =========================================
MLB_URL="https://www.mlb.com/news/2026-mlb-playoff-and-world-series-schedule"
MIL=(103,59); TB=(98,64)
def mlb_pct(wl): w,l=wl; return 0.5+(w/(w+l)-0.5)*162/202
def mlb_game(d, g, home, wl_home, wl_away, venue, ifnec=False):
    ph = clamp(sig(logit(mlb_pct(wl_home))-logit(mlb_pct(wl_away))+0.17),0.10,0.90)
    emargin = (ph-0.5)*6.0
    p_run = 1-phi((1.5-emargin)/3.2)
    away = "Tampa Bay Rays" if home=="Milwaukee Brewers" else "Milwaukee Brewers"
    add(sport="Baseball", competition=f"2026 World Series — Game {g}"+(" (if necessary)" if ifnec else ""),
        date=d, time_et="8:00 PM ET", home=home, away=away, venue=venue,
        form_home=f"2026 regular season {wl_home[0]}-{wl_home[1]}",
        form_away=f"2026 regular season {wl_away[0]}-{wl_away[1]}",
        p_home=round(ph,3), p_away=round(1-ph,3),
        markets={"Moneyline": {home: dec(ph), away: dec(1-ph)},
                 f"Run line {home} -1.5 / {away} +1.5": {home+" -1.5": dec(p_run), away+" +1.5": dec(1-p_run)},
                 "Total runs": {"—": "not originated (official RS/RA splits not captured)"}},
        p_run_home=round(p_run,3),
        sample="162-game 2026 records (MIL 103-59, TB 98-64 — MLB.com); probable pitchers not used",
        source_name="MLB.com 2026 postseason schedule + World Series FAQ (official)", source_url=MLB_URL,
        fixture_url=MLB_URL, note="Series state at capture: 0-0 (Game 1 unplayed)." + (" If-necessary game: played only if series is not decided." if ifnec else ""))
mlb_game("2026-10-23",1,"Milwaukee Brewers",MIL,TB,"American Family Field, Milwaukee")
mlb_game("2026-10-24",2,"Milwaukee Brewers",MIL,TB,"American Family Field, Milwaukee")
mlb_game("2026-10-26",3,"Tampa Bay Rays",TB,MIL,"Tropicana Field, St. Petersburg")
mlb_game("2026-10-27",4,"Tampa Bay Rays",TB,MIL,"Tropicana Field, St. Petersburg")
mlb_game("2026-10-28",5,"Tampa Bay Rays",TB,MIL,"Tropicana Field, St. Petersburg",True)
mlb_game("2026-10-30",6,"Milwaukee Brewers",MIL,TB,"American Family Field, Milwaukee",True)
mlb_game("2026-10-31",7,"Milwaukee Brewers",MIL,TB,"American Family Field, Milwaukee",True)

# ============================== DARTS (PDC) ==================================
PDC_URL="https://www.pdc.tv/news/2026/october/21/2026-machineseeker-european-championship-preview"
from math import comb
def race_p(p, need=6):
    q=1-p; s=0.0
    for k in range(need): s += comb(need-1+k,k)*(p**need)*(q**k)
    return s
def race_by(p, need, minwin_margin):
    q=1-p; s=0.0
    for k in range(need):
        if need-k >= minwin_margin: s += comb(need-1+k,k)*(p**need)*(q**k)
    return s
def exp_legs(p, need=6):
    q=1-p; tot=0.0
    for k in range(need):
        pr = comb(need-1+k,k)*((p**need)*(q**k)+(q**need)*(p**k)); tot += (need+k)*pr
    return tot
DARTS_FRI = [("Ryan Joyce",None,"Jermaine Wattimena",None),("Krzysztof Ratajski",None,"Dave Chisnall",None),
 ("Nathan Aspinall",6,"Cristo Reyes",27),("Jonny Clayton",None,"Niko Springer",None),
 ("Luke Littler",11,"William O'Connor",22),("Wessel Nijman",2,"Martin Schindler",31),
 ("Kevin Doets",14,"Michael van Gerwen",19),("Josh Rock",10,"Chris Dobey",23)]
for a,sa,b,sb in DARTS_FRI:
    if sa is None:
        p_leg=0.5; seed_note="Seed numbers for this tie were not on the official PDC excerpt read at capture; priced as a coin-flip and flagged unverified."
    else:
        p_leg=clamp(0.5+0.005*(sb-sa),0.32,0.68); seed_note="Seeds are the published European Championship draw seeds (1 = top of the 15-event European Tour Order of Merit). Seed is a prize-money proxy, not a player rating, so the per-leg slope is deliberately conservative (0.005 per seed place)."
    pm = race_p(p_leg); el = exp_legs(p_leg); tl = rhalf(el)
    p_over_l = sum(comb(5+k,k)*((p_leg**6)*((1-p_leg)**k)+((1-p_leg)**6)*(p_leg**k)) for k in range(6) if 6+k>tl)
    p_hc_a = race_by(p_leg,6,2)
    fav = a if pm>=0.5 else b
    add(sport="Darts", competition="2026 Machineseeker European Championship — Round One (best of 11 legs)",
        date="2026-10-23", time_et="Session 19:00-23:00 CEST", home=a, away=b,
        venue="Westfalenhallen, Dortmund", neutral=True,
        form_home=(f"Draw seed {sa}" if sa else "Draw seed not confirmed from official excerpt"),
        form_away=(f"Draw seed {sb}" if sb else "Draw seed not confirmed from official excerpt"),
        p_home=round(pm,3), p_away=round(1-pm,3),
        markets={"Match winner": {a: dec(pm), b: dec(1-pm)},
                 f"Leg handicap {a} -1.5": {a+" -1.5 legs": dec(p_hc_a), b+" +1.5 legs": dec(1-p_hc_a)},
                 f"Total legs {tl}": {"Over": dec(p_over_l), "Under": dec(1-p_over_l)}},
        p_leg_home=round(p_leg,3), exp_legs=round(el,2), total_line=tl, p_over=round(p_over_l,3), p_hc_home=round(p_hc_a,3),
        sample="Seed = final position on the 15-event 2026 European Tour Order of Merit (prize-money ranking)",
        source_name="PDC.tv official preview (draw bracket + schedule of play)", source_url=PDC_URL,
        fixture_url=PDC_URL, note=seed_note)

# ============================== RUGBY UNION (URC) ============================
URC_URL="https://stats.unitedrugby.com/match-centre/table/2026-27"; URC_FIX="https://www.unitedrugby.com/"
# team: PL,W,D,L,PF,PA,PD,PTS,form  (official URC Match Centre table after Round 3)
URC={"Edinburgh":(3,3,0,0,80,54,26,14,"W W W"),"Glasgow Warriors":(3,2,1,0,95,72,23,13,"W D W"),
 "Vodacom Bulls":(3,2,0,1,126,54,72,11,"W L W"),"DHL Stormers":(3,2,0,1,81,54,27,11,"W L W"),
 "Hollywoodbets Sharks":(3,2,0,1,89,83,6,10,"W W L"),"Cardiff Rugby":(3,2,0,1,66,71,-5,9,"W W L"),
 "10bet Lions":(3,2,0,1,77,102,-25,9,"W W L"),"Dragons RFC":(3,1,1,1,88,83,5,9,"D W L"),
 "Munster":(3,1,1,1,72,74,-2,9,"L W D"),"Leinster":(3,1,0,2,75,58,17,8,"L L W"),
 "Ulster":(3,0,2,1,88,93,-5,8,"L D D"),"Scarlets":(3,1,0,2,68,85,-17,7,"L L W"),
 "Ospreys":(3,1,0,2,81,107,-26,6,"L L W"),"Connacht":(3,1,0,2,56,84,-28,5,"L W L"),
 "Benetton":(3,0,1,2,64,68,-4,5,"D L L"),"Zebre Parma":(3,0,0,3,52,116,-64,1,"L L L")}
def urc_game(d, home, away, tm, venue):
    h,a = URC[home], URC[away]
    pdpg_h, pdpg_a = h[6]/h[0], a[6]/a[0]
    em = (pdpg_h-pdpg_a)*0.9 + 3.0
    p_draw = phi((0.5-em)/13)-phi((-0.5-em)/13)
    p_home = 1-phi((0.5-em)/13); p_away = phi((-0.5-em)/13)
    hcap = -rhalf(em)
    eh = (h[4]/h[0]+a[5]/a[0])/2; ea=(a[4]/a[0]+h[5]/h[0])/2
    tl = rhalf(eh+ea); po = 1-phi((tl-(eh+ea))/11)
    add(sport="Rugby Union", competition="BKT United Rugby Championship 2026-27 — Round 5", date=d, time_et=tm,
        home=home, away=away, venue=venue,
        form_home=f"{h[7]} pts, {h[1]}W-{h[2]}D-{h[3]}L, PF {h[4]} PA {h[5]} (PD {h[6]:+d}), form {h[8]}",
        form_away=f"{a[7]} pts, {a[1]}W-{a[2]}D-{a[3]}L, PF {a[4]} PA {a[5]} (PD {a[6]:+d}), form {a[8]}",
        p_home=round(p_home,3), p_draw=round(p_draw,3), p_away=round(p_away,3),
        markets={"Match result (1X2)": {home: dec(p_home), "Draw": dec(p_draw), away: dec(p_away)},
                 f"Handicap {home} {hcap:+.1f}": {home+f" {hcap:+.1f}": dec(0.5), away+f" {-hcap:+.1f}": dec(0.5)},
                 f"Total points {tl}": {"Over": dec(po), "Under": dec(1-po)}},
        exp_margin_home=round(em,1), total_line=tl, p_over=round(po,3), handicap_home=hcap,
        sample="3 rounds played at capture (table after Round 3); Round 4 (23-25 Oct) intervenes before these Round 5 fixtures — prices will move, flagged",
        source_name="URC Match Centre official table + unitedrugby.com fixture list", source_url=URC_URL,
        fixture_url=URC_FIX, note="Kick-off times UK/IRE as published by URC.")
for d,ho,aw,tm,v in [
 ("2026-10-30","Connacht","Leinster","19:45","Dexcom Stadium, Galway"),
 ("2026-10-30","Glasgow Warriors","10bet Lions","19:45","Scotstoun Stadium, Glasgow"),
 ("2026-10-31","DHL Stormers","Ulster","12:45","DHL Stadium, Cape Town"),
 ("2026-10-31","Vodacom Bulls","Scarlets","15:00","Loftus Versfeld, Pretoria"),
 ("2026-10-31","Benetton","Edinburgh","15:00","Stadio Monigo, Treviso"),
 ("2026-10-31","Munster","Hollywoodbets Sharks","17:30","Thomond Park, Limerick"),
 ("2026-10-31","Dragons RFC","Zebre Parma","17:30","Rodney Parade, Newport"),
 ("2026-10-31","Ospreys","Cardiff Rugby","19:45","St Helen's, Swansea"),
]: urc_game(d,ho,aw,tm,v)

# ============================== RUGBY LEAGUE (RLWC) ==========================
NRL_M="https://www.nrl.com/news/2026/10/20/world-cup-team-lists-mens-round-2/"
NRL_W="https://www.nrl.com/news/2026/10/20/world-cup-team-lists-womens-round-2/"
# Round-1 margins (points): men AUS +2 (24-22 NZ), SAM +74 (78-4 FRA), PNG +24 (42-18 LEB),
# TON +18 (30-12 ENG), FJI +28 (40-12 COOK). Women AUS +40 (40-0 SAM), PNG +54 (58-4 FRA),
# ENG +64 (70-6 WAL), NZ +6 (18-12 FJI).
RL_M={"Australia":(24,22),"New Zealand":(22,24),"Samoa":(78,4),"France":(4,78),"Papua New Guinea":(42,18),
 "Lebanon":(18,42),"Tonga":(30,12),"England":(12,30),"Fiji":(40,12),"Cook Islands":(12,40)}
RL_W={"Australia":(40,0),"Samoa":(0,40),"Papua New Guinea":(58,4),"France":(4,58),"England":(70,6),
 "Wales":(6,70),"New Zealand":(18,12),"Fiji":(12,18)}
def rl_game(comp, d, home, away, tm, venue, table, url, host_home=False, rd="Round 2"):
    hf,ha = table[home]; af,aa = table[away]
    em = ((hf-ha)-(af-aa))*0.35 + (4.0 if host_home else 0.0)
    p_home = clamp(1-phi((0-em)/16),0.03,0.97)
    hcap = -rhalf(em)
    et = (hf+aa)/2 + (af+ha)/2; tl=rhalf(clamp(et,30,70)); po=1-phi((tl-et)/13)
    add(sport="Rugby League", competition=comp, date=d, time_et=tm, home=home, away=away, venue=venue,
        neutral=not host_home,
        form_home=f"Round 1: scored {hf}, conceded {ha} (margin {hf-ha:+d})",
        form_away=f"Round 1: scored {af}, conceded {aa} (margin {af-aa:+d})",
        p_home=round(p_home,3), p_away=round(1-p_home,3),
        markets={"Match winner": {home: dec(p_home), away: dec(1-p_home)},
                 f"Handicap {home} {hcap:+.1f}": {home+f" {hcap:+.1f}": dec(0.5), away+f" {-hcap:+.1f}": dec(0.5)},
                 f"Total points {tl}": {"Over": dec(po), "Under": dec(1-po)}},
        exp_margin_home=round(em,1), total_line=tl, p_over=round(po,3), handicap_home=hcap,
        sample="ONE Round-1 game per team at capture — minimum sample; ratings shrunk 65% toward zero; confidence capped at Medium"+(" (Round 2 result not yet known at capture)" if rd=="Round 3" else ""),
        source_name="NRL.com official World Cup team lists / draw", source_url=url, fixture_url=url,
        note="Kick-off AEDT as published by NRL.com.")
rl_game("Rugby League World Cup 2026 — Men, Round 2","2026-10-23","Tonga","Lebanon","8:05 PM AEDT","CommBank Stadium, Sydney",RL_M,NRL_M)
rl_game("Rugby League World Cup 2026 — Men, Round 2","2026-10-24","Papua New Guinea","Samoa","3:25 PM AEDT","Santos National Football Stadium, Port Moresby",RL_M,NRL_M,True)
rl_game("Rugby League World Cup 2026 — Men, Round 2","2026-10-24","England","France","5:35 PM AEDT","HBF Park, Perth",RL_M,NRL_M)
rl_game("Rugby League World Cup 2026 — Men, Round 2","2026-10-25","New Zealand","Cook Islands","4:05 PM AEDT","One NZ Stadium, Christchurch",RL_M,NRL_M,True)
rl_game("Rugby League World Cup 2026 — Men, Round 2","2026-10-25","Australia","Fiji","8:05 PM AEDT","Suncorp Stadium, Brisbane",RL_M,NRL_M,True)
rl_game("Rugby League World Cup 2026 — Men, Round 3","2026-10-30","England","Papua New Guinea","8:05 PM AEDT","WIN Stadium, Wollongong",RL_M,NRL_M,False,"Round 3")
rl_game("Rugby League World Cup 2026 — Men, Round 3","2026-10-31","New Zealand","Fiji","","Cbus Super Stadium, Gold Coast",RL_M,NRL_M,False,"Round 3")
rl_game("Rugby League World Cup 2026 — Men, Round 3","2026-10-31","Australia","Cook Islands","8:05 PM AEDT","Queensland Country Bank Stadium, Townsville",RL_M,NRL_M,True,"Round 3")
rl_game("Rugby League World Cup 2026 — Men, Round 3","2026-11-01","Lebanon","France","5:50 PM AEDT","CommBank Stadium, Sydney",RL_M,NRL_M,False,"Round 3")
rl_game("Rugby League World Cup 2026 — Men, Round 3","2026-11-01","Tonga","Samoa","8:05 PM AEDT","CommBank Stadium, Sydney",RL_M,NRL_M,False,"Round 3")
rl_game("Rugby League World Cup 2026 — Women, Round 2","2026-10-23","Samoa","Wales","5:45 PM AEDT","CommBank Stadium, Sydney",RL_W,NRL_W)
rl_game("Rugby League World Cup 2026 — Women, Round 2","2026-10-24","Fiji","Papua New Guinea","1:15 PM AEDT","Santos National Football Stadium, Port Moresby",RL_W,NRL_W)
rl_game("Rugby League World Cup 2026 — Women, Round 2","2026-10-24","Australia","England","8:05 PM AEDT","HBF Park, Perth",RL_W,NRL_W,True)
rl_game("Rugby League World Cup 2026 — Women, Round 2","2026-10-25","New Zealand","France","2:00 PM AEDT","One NZ Stadium, Christchurch",RL_W,NRL_W,True)
rl_game("Rugby League World Cup 2026 — Women, Round 3","2026-10-31","New Zealand","Papua New Guinea","","Cbus Super Stadium, Gold Coast",RL_W,NRL_W,False,"Round 3")
rl_game("Rugby League World Cup 2026 — Women, Round 3","2026-10-31","Fiji","France","","Cbus Super Stadium, Gold Coast",RL_W,NRL_W,False,"Round 3")
rl_game("Rugby League World Cup 2026 — Women, Round 3","2026-11-01","Australia","Wales","","CommBank Stadium, Sydney",RL_W,NRL_W,True,"Round 3")

# ============================== CRICKET =====================================
ICC_FIX="https://www.icc-cricket.com/news/new-zealand-announce-schedule-for-action-packed-home-summer"
ICC_RANK="https://www.icc-cricket.com/rankings/team-rankings/mens/t20i"
# ICC men's T20I ratings, rank date 21 Oct 2026: India 267 (71 matches), New Zealand 247 (50).
diff = (247+6) - 267  # NZ rating + 6 home points, minus India rating
p_nz = 1/(1+10**(-diff/60))
for d,n,v in [("2026-10-24","2nd T20I","Hagley Oval, Christchurch"),("2026-10-27","3rd T20I","Wellington"),
              ("2026-10-30","4th T20I","Eden Park, Auckland"),("2026-11-01","5th T20I","Seddon Park, Hamilton")]:
    add(sport="Cricket", competition=f"India tour of New Zealand 2026 — {n}", date=d, time_et="",
        home="New Zealand", away="India", venue=v,
        form_home="ICC T20I rating 247 (4th, 50 rated matches, 21 Oct 2026)",
        form_away="ICC T20I rating 267 (2nd, 71 rated matches, 21 Oct 2026)",
        p_home=round(p_nz,3), p_away=round(1-p_nz,3),
        markets={"Match winner": {"New Zealand": dec(p_nz), "India": dec(1-p_nz)},
                 "Handicap / runs lines": {"—": "not originated (no venue scoring history captured)"},
                 "Total runs": {"—": "not originated (no venue scoring history captured)"}},
        sample="ICC official T20I team ratings (50-71 rated matches). 1st T20I (22 Oct) result not known at capture — series score blank, flagged.",
        source_name="ICC.com official tour schedule + ICC T20I team rankings", source_url=ICC_RANK, fixture_url=ICC_FIX, note="")
add(sport="Cricket", competition="India tour of New Zealand 2026 — 1st ODI", date="2026-11-04", time_et="",
    home="New Zealand", away="India", venue="Eden Park, Auckland",
    form_home="", form_away="", p_home=None, p_away=None,
    markets={"Match winner": {"—": "not originated (ICC ODI ratings not captured in this session)"}},
    sample="Fixture confirmed on ICC.com; ODI ratings not read — price left blank and flagged, never inferred.",
    source_name="ICC.com official tour schedule", source_url=ICC_FIX, fixture_url=ICC_FIX, note="")

# ============================== picks / confidence ==========================
WRITTEN = {}
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("preds", os.path.join(os.path.dirname(__file__),"predictions.py"))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); WRITTEN = mod.WRITTEN
except FileNotFoundError:
    WRITTEN = {}

SAMPLE_CAP = {"Rugby League":"Medium", "Rugby Union":"Medium"}  # 1-3 game samples
for i,r in enumerate(rows,1):
    r["id"]=f"X{i:03d}"
    if r.get("p_home") is None:
        r.update(pick="", pick_market="", pick_p=None, pick_dec=None, pick_amer=None,
                 confidence="", in_window=False, focus_play="", prediction="",
                 status="UNPRICED — inputs not captured (flagged)")
        continue
    ph = r["p_home"]; home_pick = ph >= 0.5
    p_pick = ph if home_pick else r["p_away"]
    pick = r["home"] if home_pick else r["away"]
    am = amer(p_pick)
    conf = "High" if p_pick>=0.70 else ("Medium" if p_pick>=0.58 else "Low")
    cap = SAMPLE_CAP.get(r["sport"])
    if cap=="Medium" and conf=="High": conf="Medium"
    r.update(pick=pick, pick_market="Match winner", pick_p=p_pick, pick_dec=dec(p_pick),
             pick_amer=am, confidence=conf, in_window=(-250 <= am <= 10000))
    # focus play: any market selection with p in [0.70, 0.7143] not sample-capped
    fp=[]
    def scan(label,p):
        if p is not None and 0.70 <= p <= 0.7143 and cap is None: fp.append((label,p))
    scan(f"{pick} (match winner)", p_pick)
    if r["sport"]=="Ice Hockey":
        scan(f"{r['home']} -1.5 puck line", r.get("p_puck_home")); scan(f"{r['away']} +1.5 puck line", 1-r.get("p_puck_home",0) if r.get("p_puck_home") else None)
        scan(f"Over {r.get('total_line')} goals", r.get("p_over")); scan(f"Under {r.get('total_line')} goals", 1-r["p_over"] if r.get("p_over") else None)
    if r["sport"]=="Baseball":
        scan(f"{r['home']} -1.5 run line", r.get("p_run_home")); scan(f"{r['away']} +1.5 run line", 1-r["p_run_home"] if r.get("p_run_home") else None)
    if r["sport"]=="Darts":
        scan(f"{r['home']} -1.5 legs", r.get("p_hc_home")); scan(f"{r['away']} +1.5 legs", 1-r["p_hc_home"] if r.get("p_hc_home") else None)
        scan(f"Over {r.get('total_line')} legs", r.get("p_over")); scan(f"Under {r.get('total_line')} legs", 1-r["p_over"] if r.get("p_over") else None)
    r["focus_play"] = "; ".join(f"{l} (p={p:.3f}, {amer(p):+d})" for l,p in fp)
    key = f"{r['date']}|{r['away']}|{r['home']}"
    r["prediction"] = WRITTEN.get(key,"")
    r["status"]="priced"

out = {"schema":"olbg4/board-x/v1","session":"arena/e1161e0e-olbg4","captured_on":CAPTURE,
 "window":"2026-10-23..2026-11-04",
 "method":"Originated FAIR prices (decimal=1/p, no margin) from official-source inputs only; see methodology.html. No bookmaker/OLBG price read.",
 "focus_rule":"Focus = pick model probability >= 0.70 AND fair American price inside -250..+10000 (p <= 0.7143), with an adequate sample (rugby league 1 game and URC 3 rounds are capped at Medium).",
 "rows":rows}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(out, open(OUT,"w"), indent=1, ensure_ascii=False)
priced=[r for r in rows if r["status"]=="priced"]
print(f"rows={len(rows)} priced={len(priced)}")
for c in ("High","Medium","Low"):
    sel=[r for r in priced if r["confidence"]==c]; print(c, len(sel))
print("\nHIGH / FOCUS rows needing written predictions:")
for r in priced:
    if r["confidence"]=="High" or r["focus_play"]:
        print(r["id"], r["date"], r["sport"], f"{r['away']} @ {r['home']}", "pick:", r["pick"],
              "p=",r["pick_p"], "amer=",r["pick_amer"], "conf=",r["confidence"], "in_window=",r["in_window"],
              "| focus:", r["focus_play"] or "-", "| written:", bool(r["prediction"]))
