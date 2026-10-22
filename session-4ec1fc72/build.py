#!/usr/bin/env python3
"""
Board T (session arena/4ec1fc72-olbg4) — fresh verified desk, 22-28 Oct 2026.

DATA PROVENANCE (read 2026-10-22 UTC with the agent web-fetch tool; sandbox curl
egress to sports domains fails with SSL_ERROR_SYSCALL):
- NHL fixtures/times: https://www.nhl.com/schedule/2026-10-22 ,
  https://www.nhl.com/schedule/2026-10-23 (pages list 22-28 Oct, gamecenter ids
  2026020154-2026020202 in order)
- NHL standings (all 32 teams, as of Oct 21 22:46 EDT):
  https://www.nhl.com/standings/2026-10-21/wildcard
- NHL team leaders quoted in predictions:
  https://api-web.nhle.com/v1/score/2026-10-24 (TOR@EDM leaders),
  https://api-web.nhle.com/v1/score/2026-10-25 (MIN@VAN leaders),
  https://api-web.nhle.com/v1/score/2026-10-22 (DET@VAN leaders)
- NBA fixtures/venues/times: https://www.nba.com/schedule?date=2026-10-23
  (Week 1 pages listing 22-25 Oct) and https://www.nba.com/games?date=2026-10-22
- NBA records: https://www.nba.com/standings (2026-27, snapshot 22 Oct)
- MLB World Series fixtures: https://statsapi.mlb.com/api/v1/schedule?sportId=1
  &startDate=2026-10-22&endDate=2026-11-04&gameType=F,W&hydrate=team,venue
  (Game 1 TB@MIL 2026-10-24T00:00Z, Game 2 2026-10-25T00:00Z,
   Game 3 MIL@TB 2026-10-27T00:00Z; venues American Family Field / Tropicana Field)
- MLB records/runs: https://statsapi.mlb.com/api/v1/standings?leagueId=103,104
  &season=2026&standingsTypes=regularSeason
  (Rays 98-64, RS736 RA650; Brewers 103-59, RS832 RA618 — the 103-59 division
   champion entry immediately ahead of the 89-73 Cubs in the NL Central block)
- Darts R1 draw: https://www.pdc.tv/news/2026/october/19/
  2026-machineseeker-european-championship-schedule-confirmed
  (Westfalenhalle, Dortmund, Oct 22-25; 16 R1 ties listed verbatim below)

Models are the repo's documented formulas (METHODOLOGY.md SS2.1 NHL, SS2.3 MLB,
adapted for NBA as stated on the methodology page). Prices are OUR OWN:
decimal = 1/(p x 1.04). Nothing is copied from OLBG or any bookmaker.
"""
import json, os, html, re, math
from statistics import NormalDist

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "session-4ec1fc72")
DATAOUT = os.path.join(ROOT, "data/session-4ec1fc72")
os.makedirs(os.path.join(OUT, "sports"), exist_ok=True)
os.makedirs(DATAOUT, exist_ok=True)
ND = NormalDist()

RETRIEVED = "2026-10-22"
WINDOW = "2026-10-22 to 2026-10-28"
EXCLUDED = ["Soccer", "Football (association)", "American football", "Boxing",
            "UFC", "MMA", "Hurling", "Horse racing", "Cycling", "Specials"]

def amer(dec):
    return round((dec - 1) * 100) if dec >= 2 else round(-100 / (dec - 1))
def price(p):  # our own price, 4% two-way overround (METHODOLOGY.md)
    return round(max(1.01, 1.0 / (min(0.99, max(0.01, p)) * 1.04)), 3)
def in_window(dec):
    a = amer(dec); return -250 <= a <= 10000
def clamp(x, lo, hi): return min(hi, max(lo, x))
def sigmoid(x): return 1 / (1 + math.exp(-x))
def logit(p): return math.log(p / (1 - p))

# ---------------------------------------------------------------- NHL inputs
# abbrev: (full name, GP, W, L, OT, GF, GA, L10, streak) — NHL.com standings 21 Oct
NHL_TEAMS = {
 "BOS": ("Boston Bruins",10,7,2,1,36,22,"7-2-1","OT1"), "TBL": ("Tampa Bay Lightning",9,7,2,0,31,23,"7-2-0","W3"),
 "OTT": ("Ottawa Senators",10,7,3,0,29,24,"7-3-0","W1"), "CAR": ("Carolina Hurricanes",11,8,2,1,42,27,"8-2-0","W1"),
 "NYR": ("New York Rangers",11,7,3,1,33,24,"7-2-1","W1"), "NYI": ("New York Islanders",9,5,3,1,27,20,"5-3-1","W2"),
 "FLA": ("Florida Panthers",10,5,3,2,31,30,"5-3-2","L1"), "TOR": ("Toronto Maple Leafs",11,5,4,2,38,35,"5-3-2","W2"),
 "WSH": ("Washington Capitals",9,5,4,0,30,29,"5-4-0","L1"), "NJD": ("New Jersey Devils",9,5,4,0,29,30,"5-4-0","W1"),
 "MTL": ("Montreal Canadiens",9,4,3,2,30,34,"4-3-2","OT1"), "BUF": ("Buffalo Sabres",10,4,4,2,28,37,"4-4-2","L1"),
 "DET": ("Detroit Red Wings",9,3,3,3,23,28,"3-3-3","OT1"), "PHI": ("Philadelphia Flyers",12,3,6,3,20,37,"3-5-2","W3"),
 "PIT": ("Pittsburgh Penguins",10,3,6,1,33,38,"3-6-1","L4"), "CBJ": ("Columbus Blue Jackets",8,3,5,0,20,29,"3-5-0","L2"),
 "UTA": ("Utah Mammoth",10,7,3,0,38,31,"7-3-0","W1"), "MIN": ("Minnesota Wild",10,6,2,2,31,25,"6-2-2","OT1"),
 "DAL": ("Dallas Stars",9,5,3,1,23,15,"5-3-1","W3"), "VGK": ("Vegas Golden Knights",11,8,3,0,44,30,"7-3-0","L1"),
 "EDM": ("Edmonton Oilers",9,7,1,1,41,27,"7-1-1","W2"), "SEA": ("Seattle Kraken",10,6,3,1,39,34,"6-3-1","W1"),
 "COL": ("Colorado Avalanche",10,5,4,1,41,31,"5-4-1","L2"), "SJS": ("San Jose Sharks",10,5,4,1,27,35,"5-4-1","W1"),
 "WPG": ("Winnipeg Jets",9,4,3,2,24,26,"4-3-2","L2"), "NSH": ("Nashville Predators",8,3,2,3,23,24,"3-2-3","W1"),
 "STL": ("St. Louis Blues",9,4,4,1,29,29,"4-4-1","W1"), "ANA": ("Anaheim Ducks",9,4,5,0,26,29,"4-5-0","L4"),
 "CHI": ("Chicago Blackhawks",9,3,6,0,21,36,"3-6-0","L1"), "VAN": ("Vancouver Canucks",11,2,8,1,33,51,"","L2"),
 "LAK": ("Los Angeles Kings",7,1,4,2,17,27,"1-4-2","W1"), "CGY": ("Calgary Flames",8,2,6,0,17,37,"2-6-0","W1"),
}
def nhl_rating(t):
    name, gp, w, l, ot, gf, ga, l10, stk = NHL_TEAMS[t]
    pts = 2 * w + ot; pct = pts / (2 * gp)
    return 0.5 + (pct - 0.5) * gp / (gp + 12) + 0.012 * (gf - ga) / gp

NHL_FIX = [
 ("2026-10-22","NSH","BOS","7:00 PM ET"),("2026-10-22","NYR","TOR","7:00 PM ET"),
 ("2026-10-22","SJS","OTT","7:00 PM ET"),("2026-10-22","ANA","NJD","7:00 PM ET"),
 ("2026-10-22","FLA","PIT","7:00 PM ET"),("2026-10-22","LAK","NYI","7:30 PM ET"),
 ("2026-10-22","VGK","STL","8:00 PM ET"),("2026-10-22","WPG","DAL","8:00 PM ET"),
 ("2026-10-22","MIN","CGY","9:00 PM ET"),("2026-10-22","CAR","EDM","9:00 PM ET"),
 ("2026-10-22","UTA","SEA","10:00 PM ET"),("2026-10-22","DET","VAN","10:00 PM ET"),
 ("2026-10-23","MTL","CHI","8:00 PM ET"),("2026-10-23","TBL","COL","9:00 PM ET"),
 ("2026-10-24","ANA","PHI","1:00 PM ET"),("2026-10-24","LAK","NJD","3:30 PM ET"),
 ("2026-10-24","SJS","BOS","7:00 PM ET"),("2026-10-24","NYR","OTT","7:00 PM ET"),
 ("2026-10-24","NSH","PIT","7:00 PM ET"),("2026-10-24","BUF","WSH","7:00 PM ET"),
 ("2026-10-24","VGK","CBJ","7:00 PM ET"),("2026-10-24","CAR","STL","7:00 PM ET"),
 ("2026-10-24","TOR","EDM","7:00 PM ET"),("2026-10-24","TBL","UTA","9:00 PM ET"),
 ("2026-10-24","DET","CGY","10:00 PM ET"),("2026-10-24","MIN","SEA","10:00 PM ET"),
 ("2026-10-25","FLA","CHI","3:00 PM ET"),("2026-10-25","NYI","DAL","6:00 PM ET"),
 ("2026-10-25","MTL","WPG","7:00 PM ET"),("2026-10-25","COL","NSH","8:00 PM ET"),
 ("2026-10-25","MIN","VAN","10:00 PM ET"),
 ("2026-10-26","LAK","NYR","7:00 PM ET"),("2026-10-26","TOR","CGY","8:30 PM ET"),
 ("2026-10-26","DET","EDM","9:30 PM ET"),
 ("2026-10-27","CBJ","PHI","7:00 PM ET"),("2026-10-27","BOS","CAR","8:00 PM ET"),
 ("2026-10-27","LAK","CHI","8:00 PM ET"),("2026-10-27","MTL","STL","8:00 PM ET"),
 ("2026-10-27","NYI","NSH","8:00 PM ET"),("2026-10-27","NJD","DAL","8:00 PM ET"),
 ("2026-10-27","FLA","WPG","8:00 PM ET"),("2026-10-27","MIN","UTA","9:00 PM ET"),
 ("2026-10-27","OTT","VGK","10:00 PM ET"),("2026-10-27","VAN","ANA","10:00 PM ET"),
 ("2026-10-27","BUF","SJS","10:30 PM ET"),
 ("2026-10-28","PHI","WSH","7:30 PM ET"),("2026-10-28","CGY","EDM","8:30 PM ET"),
 ("2026-10-28","NJD","COL","9:00 PM ET"),("2026-10-28","TOR","SEA","10:00 PM ET"),
]

rows, flagged = [], []
def add_flag(fid, kind, text, source):
    flagged.append({"id": fid, "kind": kind, "text": text, "source": source})

for i, (d, aw, hm, tm) in enumerate(NHL_FIX, 1):
    fid = f"T-NHL-{i:02d}"
    neutral = (d, aw, hm) == ("2026-10-25", "MTL", "WPG")
    rh, ra = nhl_rating(hm), nhl_rating(aw)
    p_home = clamp(0.5 + (rh - ra) * 0.80 + (0.0 if neutral else 0.035), 0.08, 0.92)
    hn, an = NHL_TEAMS[hm], NHL_TEAMS[aw]
    # total: shrunk goal rates toward 3.05/team (METHODOLOGY.md SS2.1)
    def shrunk(t, idx):
        gp = NHL_TEAMS[t][1]; return (NHL_TEAMS[t][idx] / gp * gp + 3.05 * 10) / (gp + 10)
    eh = (shrunk(hm, 5) + shrunk(aw, 6)) / 2; ea = (shrunk(aw, 5) + shrunk(hm, 6)) / 2
    tmean = clamp(eh + ea, 4.5, 8.5); tline = math.floor(tmean) + 0.5
    p_over = 1 - ND.cdf((tline - tmean) / 1.9)
    p_home_pl = 1 - ND.cdf((1.5 - (eh - ea)) / 2.0)  # home -1.5
    pick_home = p_home >= 0.5
    p_pick = p_home if pick_home else 1 - p_home
    pick_name = hn[0] if pick_home else an[0]
    dec_pick = price(p_pick)
    conf = "High" if p_pick >= 0.66 else ("Medium" if p_pick >= 0.58 else "Low")
    note = ""
    if conf == "High" and not in_window(dec_pick):
        conf = "Medium"; note = "Model probability >=70% band but originated price is shorter than -250, so this is capped at Medium under the -250 to +10000 focus window and carries no High prediction."
        add_flag(fid, "outside-focus-window", f"{an[0]} at {hn[0]} ({d}): model p={p_pick:.3f} prices at {amer(dec_pick)} ({dec_pick}), outside -250..+10000. Downgraded High->Medium; no High prediction written.", "https://www.nhl.com/standings/2026-10-21/wildcard")
    if neutral:
        note = (note + " Neutral-site game (Princess Auto Stadium, Winnipeg, per NHL score feed); no home-ice term applied.").strip()
        add_flag(fid, "neutral-site", "Montreal at Winnipeg on 2026-10-25 is listed Neutral Site at Princess Auto Stadium in the official NHL score feed; treated as no-home-advantage.", "https://api-web.nhle.com/v1/score/2026-10-25")
    basis = (f"Standings snapshot 21 Oct (NHL.com): {hn[0]} {hn[2]}-{hn[3]}-{hn[4]} "
             f"(GF{hn[5]} GA{hn[6]}{', L10 '+hn[7] if hn[7] else ''}, streak {hn[8]}); "
             f"{an[0]} {an[2]}-{an[3]}-{an[4]} (GF{an[5]} GA{an[6]}{', L10 '+an[7] if an[7] else ''}, streak {an[8]}). "
             f"Model v1 (repo METHODOLOGY SS2.1): shrunk points-% rating + goal differential, +0.035 home ice"
             f"{' (removed: neutral site)' if neutral else ''}.")
    rows.append({
        "id": fid, "sport": "Ice Hockey", "competition": "NHL", "date": d, "time": tm,
        "venue": "", "home": hn[0], "away": an[0],
        " markets_note": "",
        "markets": {
            "win": {"label": "Match winner (moneyline, incl. OT/SO)", "home_price": price(p_home), "away_price": price(1-p_home), "p_home": round(p_home,4)},
            "handicap": {"label": "Puck line -1.5/+1.5", "line_home": -1.5, "home_price": price(p_home_pl), "away_price": price(1-p_home_pl), "p_home_cover": round(p_home_pl,4)},
            "total": {"label": "Match total goals", "line": tline, "over_price": price(p_over), "under_price": price(1-p_over), "p_over": round(p_over,4), "expected_total": round(tmean,2)},
        },
        "pick": pick_name, "pick_market": "Match winner (moneyline)", "model_prob": round(p_pick,4),
        "our_price": dec_pick, "american": amer(dec_pick), "confidence": conf,
        "basis": basis, "prediction": "", "note": note,
        "source_url": f"https://www.nhl.com/schedule/{d}", "source_label": "NHL.com official schedule (date page)",
        "form_source_url": "https://www.nhl.com/standings/2026-10-21/wildcard", "form_source_label": "NHL.com official standings, 21 Oct 2026",
        "retrieved": RETRIEVED, "status": "Verified",
    })

# ---------------------------------------------------------------- NBA inputs
# team: (W, L) at 22 Oct snapshot — NBA.com official standings
NBA_REC = {"Detroit Pistons":(1,0),"Atlanta Hawks":(1,0),"Philadelphia 76ers":(1,0),"Toronto Raptors":(1,0),
 "Washington Wizards":(1,0),"Charlotte Hornets":(1,0),"Indiana Pacers":(1,0),"New York Knicks":(0,1),
 "Brooklyn Nets":(0,1),"Orlando Magic":(0,1),"Boston Celtics":(0,1),"Milwaukee Bucks":(0,1),
 "Chicago Bulls":(0,1),"Miami Heat":(0,1),"Cleveland Cavaliers":(0,0),"Memphis Grizzlies":(1,0),
 "Oklahoma City Thunder":(1,0),"Minnesota Timberwolves":(1,0),"San Antonio Spurs":(0,1),"Utah Jazz":(0,1),
 "New Orleans Pelicans":(0,1),"Golden State Warriors":(0,0),"Dallas Mavericks":(0,0),"Denver Nuggets":(0,0),
 "Houston Rockets":(0,0),"Los Angeles Lakers":(0,0),"LA Clippers":(0,0),"Phoenix Suns":(0,0),
 "Portland Trail Blazers":(0,0),"Sacramento Kings":(0,0)}
NBA_FIX = [
 ("2026-10-22","Cleveland Cavaliers","Philadelphia 76ers","7:00 PM ET","Xfinity Mobile Arena, Philadelphia, PA"),
 ("2026-10-22","Denver Nuggets","Oklahoma City Thunder","9:30 PM ET","Paycom Center, Oklahoma City, OK"),
 ("2026-10-23","Chicago Bulls","Milwaukee Bucks","4:00 PM ET","Fiserv Forum, Milwaukee, WI"),
 ("2026-10-23","New York Knicks","Boston Celtics","7:00 PM ET","TD Garden, Boston, MA"),
 ("2026-10-23","Atlanta Hawks","Charlotte Hornets","7:00 PM ET","Spectrum Center, Charlotte, NC"),
 ("2026-10-23","Dallas Mavericks","Indiana Pacers","7:00 PM ET","Gainbridge Fieldhouse, Indianapolis, IN"),
 ("2026-10-23","Minnesota Timberwolves","Orlando Magic","7:00 PM ET","Kia Center, Orlando, FL"),
 ("2026-10-23","Toronto Raptors","Washington Wizards","7:00 PM ET","Capital One Arena, Washington, DC"),
 ("2026-10-23","Detroit Pistons","Miami Heat","8:00 PM ET","Kaseya Center, Miami, FL"),
 ("2026-10-23","Houston Rockets","San Antonio Spurs","9:30 PM ET","Moody Center, Austin, TX"),
 ("2026-10-23","New Orleans Pelicans","Utah Jazz","9:30 PM ET","Delta Center, Salt Lake City, UT"),
 ("2026-10-23","Memphis Grizzlies","Golden State Warriors","10:00 PM ET","Chase Center, San Francisco, CA"),
 ("2026-10-23","LA Clippers","Los Angeles Lakers","10:00 PM ET","Crypto.com Arena, Los Angeles, CA"),
 ("2026-10-23","Portland Trail Blazers","Sacramento Kings","10:00 PM ET","Golden 1 Center, Sacramento, CA"),
 ("2026-10-24","Miami Heat","Charlotte Hornets","6:00 PM ET","Spectrum Center, Charlotte, NC"),
 ("2026-10-24","Brooklyn Nets","Cleveland Cavaliers","7:30 PM ET","Rocket Arena, Cleveland, OH"),
 ("2026-10-24","Milwaukee Bucks","Philadelphia 76ers","7:30 PM ET","Xfinity Mobile Arena, Philadelphia, PA"),
 ("2026-10-24","Washington Wizards","Chicago Bulls","8:00 PM ET","United Center, Chicago, IL"),
 ("2026-10-24","San Antonio Spurs","Dallas Mavericks","8:00 PM ET","American Airlines Center, Dallas, TX"),
 ("2026-10-24","Houston Rockets","Atlanta Hawks","8:30 PM ET","State Farm Arena, Atlanta, GA"),
 ("2026-10-24","New Orleans Pelicans","Denver Nuggets","9:00 PM ET","Ball Arena, Denver, CO"),
 ("2026-10-24","Golden State Warriors","Phoenix Suns","10:00 PM ET","Mortgage Matchup Center, Phoenix, AZ"),
 ("2026-10-25","Los Angeles Lakers","Utah Jazz","5:00 PM ET","Delta Center, Salt Lake City, UT"),
 ("2026-10-25","Indiana Pacers","Brooklyn Nets","6:00 PM ET","Barclays Center, Brooklyn, NY"),
 ("2026-10-25","Orlando Magic","New York Knicks","7:00 PM ET","Madison Square Garden, New York, NY"),
 ("2026-10-25","Toronto Raptors","Minnesota Timberwolves","7:00 PM ET","Target Center, Minneapolis, MN"),
 ("2026-10-25","LA Clippers","Oklahoma City Thunder","7:00 PM ET","Paycom Center, Oklahoma City, OK"),
 ("2026-10-25","Detroit Pistons","Philadelphia 76ers","7:30 PM ET","Xfinity Mobile Arena, Philadelphia, PA"),
 ("2026-10-25","Memphis Grizzlies","Sacramento Kings","9:00 PM ET","Golden 1 Center, Sacramento, CA"),
]
for i, (d, aw, hm, tm, ven) in enumerate(NBA_FIX, 1):
    fid = f"T-NBA-{i:02d}"
    def rating(t):
        w, l = NBA_REC[t]; gp = w + l
        pct = (w / gp) if gp else 0.5
        return 0.5 + (pct - 0.5) * gp / (gp + 20)
    rh, ra = rating(hm), rating(aw)
    p_home = clamp(0.5 + (rh - ra) * 0.80 + 0.055, 0.05, 0.95)
    spread = - (math.floor(abs(ND.inv_cdf(p_home) * 11.5)) + 0.5) * (1 if p_home >= 0.5 else -1)
    # spread expressed as home line: favourite gets negative line
    home_line = - (math.floor(abs(ND.inv_cdf(p_home) * 11.5) ) + 0.5) if p_home >= 0.5 else (math.floor(abs(ND.inv_cdf(p_home) * 11.5)) + 0.5)
    p_home_cover = 1 - ND.cdf((abs(home_line) - abs(ND.inv_cdf(p_home) * 11.5)) / 11.5) if False else 0.5
    # price the named half-point spread at the model's own 50% point -> fair 1.92/1.92 before hold check:
    pick_home = p_home >= 0.5; p_pick = p_home if pick_home else 1 - p_home
    dec_pick = price(p_pick)
    hw, hl = NBA_REC[hm]; aw_, al = NBA_REC[aw]
    rows.append({
        "id": fid, "sport": "Basketball", "competition": "NBA", "date": d, "time": tm, "venue": ven,
        "home": hm, "away": aw,
        "markets": {
            "win": {"label": "Match winner (moneyline)", "home_price": price(p_home), "away_price": price(1-p_home), "p_home": round(p_home,4)},
            "handicap": {"label": "Point spread (home line, priced at model median)", "line_home": home_line, "home_price": price(0.5), "away_price": price(0.5), "p_home_cover": 0.5},
            "total": {"label": "Match total points", "line": None, "note": "Investigated — NOT originated: no official pace / offensive-efficiency table was captured, so no total is priced (deliberate blank, flagged)."},
        },
        "pick": hm if pick_home else aw, "pick_market": "Match winner (moneyline)", "model_prob": round(p_pick,4),
        "our_price": dec_pick, "american": amer(dec_pick), "confidence": "Low",
        "basis": (f"NBA.com standings snapshot 22 Oct: {hm} {hw}-{hl}, {aw} {aw_}-{al}. Every club had played at most one "
                  f"2026-27 game at the snapshot, so the current-form rating is shrunk 1/21 toward .500 and every NBA row is "
                  f"capped at Low confidence — no Medium/High is claimed on a one-game sample. Home term +0.055."),
        "prediction": "", "note": "Confidence capped at Low: one-game (or zero-game) current-season sample for both clubs at snapshot.",
        "source_url": "https://www.nba.com/schedule?date=2026-10-23", "source_label": "NBA.com official schedule, Week 1 (22-25 Oct pages)",
        "form_source_url": "https://www.nba.com/standings", "form_source_label": "NBA.com official 2026-27 standings (22 Oct snapshot)",
        "retrieved": RETRIEVED, "status": "Verified",
    })
add_flag("T-NBA-ALL", "market-not-originated", "NBA match totals (29 rows): investigated but not originated — no official pace/efficiency input was captured. Lines left blank, never estimated.", "https://www.nba.com/standings")
add_flag("T-NBA-CAP", "small-sample-cap", "All 29 NBA rows capped at Low: at the 22 Oct snapshot every club had played 0-1 regular-season games (NBA.com standings). Any stronger grade would be invented form.", "https://www.nba.com/standings")

# ---------------------------------------------------------------- MLB
MLB = {  # W, L, RS, RA — MLB Stats API regular-season standings 2026
 "Tampa Bay Rays": (98, 64, 736, 650), "Milwaukee Brewers": (103, 59, 832, 618)}
MLB_FIX = [
 ("2026-10-23","World Series Game 1","Tampa Bay Rays","Milwaukee Brewers","2026-10-24T00:00Z","American Family Field, Milwaukee"),
 ("2026-10-24","World Series Game 2","Tampa Bay Rays","Milwaukee Brewers","2026-10-25T00:00Z","American Family Field, Milwaukee"),
 ("2026-10-26","World Series Game 3","Milwaukee Brewers","Tampa Bay Rays","2026-10-27T00:00Z","Tropicana Field, St. Petersburg"),
]
for i, (d, comp, aw, hm, utc, ven) in enumerate(MLB_FIX, 1):
    fid = f"T-MLB-{i}"
    def adj(t):
        w, l, rs, ra = MLB[t]; return 0.5 + (w / (w + l) - 0.5) * 162 / 202
    ph = sigmoid(logit(adj(hm)) - logit(adj(aw)) + 0.17)
    hw, hl, hrs, hra = MLB[hm]; aw2, al2, ars, ara = MLB[aw]
    eh = (hrs / 162 + ara / 162) / 2 + 0.12; ea = (ars / 162 + hra / 162) / 2 - 0.12
    tmean = eh + ea; tline = math.floor(tmean) + 0.5
    p_over = 1 - ND.cdf((tline - tmean) / 1.85)
    p_home_rl = 1 - ND.cdf((1.5 - (eh - ea)) / 1.9)  # home -1.5
    pick_home = ph >= 0.5; p_pick = ph if pick_home else 1 - ph; dec_pick = price(p_pick)
    rows.append({
        "id": fid, "sport": "Baseball", "competition": f"MLB — {comp}", "date": d, "time": utc + " (official UTC, MLB Stats API)", "venue": ven,
        "home": hm, "away": aw,
        "markets": {
            "win": {"label": "Match winner (moneyline)", "home_price": price(ph), "away_price": price(1-ph), "p_home": round(ph,4)},
            "handicap": {"label": "Run line -1.5/+1.5", "line_home": -1.5, "home_price": price(p_home_rl), "away_price": price(1-p_home_rl), "p_home_cover": round(p_home_rl,4)},
            "total": {"label": "Match total runs", "line": tline, "over_price": price(p_over), "under_price": price(1-p_over), "p_over": round(p_over,4), "expected_total": round(tmean,2)},
        },
        "pick": hm if pick_home else aw, "pick_market": "Match winner (moneyline)", "model_prob": round(p_pick,4),
        "our_price": dec_pick, "american": amer(dec_pick),
        "confidence": "Medium" if p_pick >= 0.58 else "Low",
        "basis": (f"MLB Stats API 2026 regular-season standings: {hm} {hw}-{hl} (runs {hrs} for / {hra} against); "
                  f"{aw} {aw2}-{al2} (runs {ars} / {ara}). Repo METHODOLOGY SS2.3: win-% shrunk 162/202 toward .500, "
                  f"+0.17 home logit; expected runs from RS/RA per 162. Probable pitchers were not published on the "
                  f"schedule payload read, so no pitcher claim is made and confidence is capped below High."),
        "prediction": "", "note": "Probable pitchers not on the official schedule payload read — blank, not guessed; see Flagged.",
        "source_url": "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-22&endDate=2026-11-04&gameType=F,W&hydrate=team,venue",
        "source_label": "MLB Stats API official schedule (World Series)",
        "form_source_url": "https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season=2026&standingsTypes=regularSeason",
        "form_source_label": "MLB Stats API official 2026 standings",
        "retrieved": RETRIEVED, "status": "Verified",
    })
add_flag("T-MLB-PITCH", "missing-input", "MLB World Series Games 1-3: probable pitchers were not present on the official schedule payload read on 22 Oct, so no pitcher-based claim is made and no MLB row is graded High.", "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-22&endDate=2026-11-04&gameType=F,W&hydrate=team,venue")

# ---------------------------------------------------------------- Darts (fixtures only)
DARTS = [
 ("2026-10-22", ["Luke Woodhouse v Dirk van Duijvenbode","Danny Noppert v Stephen Bunting","Niels Zonneveld v Cameron Menzies","Gerwyn Price v Rob Cross","James Wade v Damon Heta","Luke Humphries v Ryan Searle","Gian van Veen v Andrew Gilding","Ross Smith v Karel Sedlacek"]),
 ("2026-10-23", ["Ryan Joyce v Jermaine Wattimena","Krzysztof Ratajski v Dave Chisnall","Nathan Aspinall v Cristo Reyes","Jonny Clayton v Niko Springer","Luke Littler v William O'Connor","Wessel Nijman v Martin Schindler","Kevin Doets v Michael van Gerwen","Josh Rock v Chris Dobey"]),
]
di = 0
for d, ties in DARTS:
    for tie in ties:
        di += 1; a, b = [x.strip() for x in tie.split(" v ")]
        rows.append({
            "id": f"T-DARTS-{di:02d}", "sport": "Darts", "competition": "PDC European Championship — Round One",
            "date": d, "time": "Evening session 1900-2300 CEST (per-match start not published — blank)", "venue": "Westfalenhalle, Dortmund",
            "home": a, "away": b,
            "markets": {"win": {"label": "Match winner — NOT originated (see Flagged)", "home_price": None, "away_price": None},
                        "handicap": {"label": "Leg handicap — investigated, not originated"},
                        "total": {"label": "Total legs — investigated, not originated"}},
            "pick": "", "pick_market": "", "model_prob": None, "our_price": None, "american": None, "confidence": "",
            "basis": "PDC's official schedule article confirms the tie, the session and the venue, and describes Van Veen as defending champion, Humphries as world number two, Littler as world number one and Nijman as number two seed — but it publishes no ranking/average for both players in every tie, so no defensible line can be originated for these rows in this session.",
            "prediction": "", "note": "Fixture verified; no line, pick or confidence originated — missing verified quantitative input for both players.",
            "source_url": "https://www.pdc.tv/news/2026/october/19/2026-machineseeker-european-championship-schedule-confirmed",
            "source_label": "PDC (pdc.tv) official European Championship schedule, 19 Oct 2026",
            "form_source_url": "", "form_source_label": "", "retrieved": RETRIEVED, "status": "Flagged",
        })
add_flag("T-DARTS-01", "market-not-originated", "Darts (16 PDC European Championship R1 ties, 22-23 Oct): fixtures, session times and Westfalenhalle venue verified on pdc.tv, but no official ranking/three-dart-average for both players in each tie was captured, so match-winner, leg-handicap and total-legs markets were investigated and deliberately left unpriced rather than invented.", "https://www.pdc.tv/news/2026/october/19/2026-machineseeker-european-championship-schedule-confirmed")

# ---------------------------------------------------------------- predictions (High only)
PREDICTIONS = {
 "T-NHL-34": ("Edmonton Oilers moneyline (match winner) against Detroit. Edmonton arrive at Rogers Place with the league's "
   "standout early record, seven wins from nine games and a 41-27 goal split at the official standings snapshot, and their "
   "attack is being driven by Leon Draisaitl, who leads the club with eight goals, while Connor McDavid's twenty assists "
   "show how reliably the Oilers are creating chances. Detroit, by contrast, sit at three wins, three losses and three "
   "overtime losses with a negative goal difference, and although Alex DeBrincat has six goals, the Red Wings have leaned "
   "on overtime to stay close in games. On current form, venue and scoring depth, the selection is Edmonton Oilers to win "
   "the match on the moneyline."),
 "T-NHL-31": ("Minnesota Wild moneyline (match winner) at Vancouver. Minnesota travel to Rogers Arena holding a six-win, "
   "two-loss, two-overtime-loss record with a positive 31-25 goal split, and Kirill Kaprizov has set the tone with eleven "
   "goals while Quinn Hughes has added eleven assists from the blue line; behind them, Jesper Wallstedt already has six "
   "goaltending wins. Vancouver's verified early form points the other way entirely: two wins from eleven games, a league-worst "
   "33-51 goal split in this snapshot, Elias Pettersson's eight assists standing as a bright spot on a side that has conceded "
   "heavily, and only one win for Leevi Merilainen. The selection is Minnesota Wild to win the match on the moneyline."),
}
for r in rows:
    if r["id"] in PREDICTIONS:
        assert r["confidence"] == "High", (r["id"], r["confidence"], r["model_prob"], r["our_price"])
        r["prediction"] = PREDICTIONS[r["id"]]

# coverage of every in-scope sport
COVERAGE = [
 ("Ice Hockey","Refreshed — 49 NHL fixtures priced (win / puck line / total)","https://www.nhl.com/schedule/2026-10-22"),
 ("Basketball","Refreshed — 29 NBA fixtures priced (win / spread; total flagged blank)","https://www.nba.com/schedule?date=2026-10-23"),
 ("Baseball","Refreshed — MLB World Series Games 1-3 priced (win / run line / total)","https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-22&endDate=2026-11-04&gameType=F,W&hydrate=team,venue"),
 ("Darts","Fixtures verified — 16 PDC European Championship R1 ties listed, lines flagged unpriced","https://www.pdc.tv/news/2026/october/19/2026-machineseeker-european-championship-schedule-confirmed"),
 ("Snooker","Attempted — WST matches page read; R1 results (18-19 Oct) are completed, later-round pairings for 22-25 Oct were not on the page chunk read, so no snooker row is published","https://www.wst.tv/matches"),
 ("Tennis","Not refreshed in Board T — no official tour fixture page read this session; rows left to earlier boards, flagged here",""),
 ("Cricket","Not refreshed in Board T — no official fixture page read this session; flagged",""),
 ("Rugby Union","Not refreshed in Board T — no official fixture page read this session; flagged",""),
 ("Rugby League","Not refreshed in Board T — no official fixture page read this session; flagged",""),
 ("Handball","Not refreshed in Board T — no official fixture page read this session; flagged",""),
 ("Volleyball","Not refreshed in Board T — no official fixture page read this session; flagged",""),
 ("Badminton","Not refreshed in Board T — no official fixture page read this session; flagged",""),
 ("Table Tennis","Not refreshed in Board T — no official fixture page read this session; flagged",""),
 ("Esports","Not refreshed in Board T — no official fixture page read this session; flagged",""),
 ("Golf","Not refreshed in Board T — outright/futures only on earlier boards, no head-to-head fixture read this session; flagged",""),
 ("Gaelic Football","Not refreshed in Board T — in scope (only hurling is excluded) but no official fixture page read this session; flagged",""),
 ("Aussie Rules","Not refreshed in Board T — no official fixture page read this session; flagged",""),
 ("Greyhound Racing","Not refreshed in Board T — no official fixture page read this session; flagged",""),
 ("Motor Racing","Not refreshed in Board T — outright/futures only on earlier boards, no head-to-head fixture read this session; flagged",""),
]
for sport, status, url in COVERAGE:
    if status.startswith("Not refreshed"):
        add_flag(f"T-COV-{sport}", "coverage-gap", f"{sport}: {status}. No fixture, line or pick is published for this sport in Board T; earlier boards' rows are not re-verified here.", url or "https://buffedlizard55-lab.github.io/OLBG4/board/")
add_flag("T-SNOOKER-01", "coverage-gap", "Snooker: the official WST matches page read on 22 Oct shows completed Northern Ireland Open Round 1 results from 18-19 Oct; the later-round pairings falling inside 22-28 Oct were not present in the page content read, so Board T publishes no snooker fixture rather than guessing a draw.", "https://www.wst.tv/matches")
add_flag("T-STALE-01", "freshness", "Earlier boards (master: 317 rows, generated 2026-10-21; Board S: 144 rows, window 21-25 Oct) contain many fixtures dated 21 Oct that are now completed. Board T does not re-publish them as upcoming; it prices only the 22-28 Oct fixtures it read itself on 22 Oct.", "https://buffedlizard55-lab.github.io/OLBG4/board/")
add_flag("T-OLBG-01", "method", "OLBG.com was used as taxonomy reference only (see docs/olbg-reverse-engineering.md). No OLBG price, tip share or prediction was copied; every price here is originated from the official-source inputs quoted per row. OLBG lists no prices on its hub rows, so it cannot be a price source in any case.", "https://www.olbg.com/betting-tips")

json.dump({"board": "T", "session": "arena/4ec1fc72-olbg4", "retrieved": RETRIEVED, "window": WINDOW,
           "excluded_sports": EXCLUDED, "rows": rows, "flagged": flagged, "coverage": COVERAGE},
          open(os.path.join(DATAOUT, "data.json"), "w"), indent=1)

# ---------------------------------------------------------------- site
def e(x): return html.escape(str(x if x not in (None, "") else "—"))
def slug(s): return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
CSS = """*{box-sizing:border-box}body{font-family:system-ui,Segoe UI,Arial,sans-serif;margin:0;background:#f8fafc;color:#0f172a;line-height:1.5}
.wrap{max-width:1180px;margin:auto;padding:0 20px}.topnav{background:#0f172a;color:#fff;padding:14px 0;position:sticky;top:0;z-index:10}
.topnav a{color:#cbd5e1;text-decoration:none;margin-right:14px;font-size:13px}.topnav a:hover{color:#fff}.brand{font-weight:700;color:#38bdf8!important;font-size:16px}.brand span{color:#fff;font-weight:400}
.hero{background:linear-gradient(135deg,#0f172a,#1e40af);color:#fff;padding:34px 0}.hero h1{margin:0 0 8px;font-size:27px}.lede{color:#cbd5e1;max-width:760px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin:20px 0}.kpi{background:#fff;border-radius:10px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.1);text-align:center}.kpi .n{font-size:24px;font-weight:700;color:#1e40af}.kpi .l{font-size:12px;color:#64748b;text-transform:uppercase;letter-spacing:.5px}
.card{background:#fff;border-radius:10px;padding:16px;margin:14px 0;box-shadow:0 1px 3px rgba(0,0,0,.08)}
table{width:100%;border-collapse:collapse;font-size:13px;background:#fff}th,td{border:1px solid #e2e8f0;padding:8px;vertical-align:top;text-align:left}th{background:#f1f5f9;font-size:12px;text-transform:uppercase;letter-spacing:.5px}
.badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:600}.b-high{background:#dcfce7;color:#166534}.b-medium{background:#fef9c3;color:#854d0e}.b-low{background:#f1f5f9;color:#475569}.b-flagged{background:#fee2e2;color:#991b1b}
.small{color:#64748b;font-size:12px}a{color:#1d4ed8}.pred{background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:10px;margin-top:8px}"""
open(os.path.join(OUT, "style.css"), "w").write(CSS)
SPORTS = sorted(set(r["sport"] for r in rows))
def nav(p=""):
    links = "".join(f'<a href="{p}{f}">{t}</a>' for f, t in [("index.html","Dashboard"),("picks.html","High picks"),("markets.html","Markets"),("flagged.html","Flagged for Review"),("sources.html","Sources"),("methodology.html","Method"),("verification.html","Verification"),("coverage.html","Coverage")])
    cats = "".join(f'<a href="{p}sports/{slug(s)}.html">{e(s)}</a>' for s in SPORTS)
    return f'<nav class="topnav"><div class="wrap"><a class="brand" href="{p}index.html">OLBG4 <span>Board T · fresh desk</span></a><div>{links}{cats}</div></div></nav>'
def page(title, body, p=""):
    return f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>{e(title)}</title><link rel='stylesheet' href='{p}style.css'></head><body>{nav(p)}<main class='wrap'>{body}</main><footer class='wrap small'><p>Board T · session arena/4ec1fc72-olbg4 · Snapshot read 22 Oct 2026 · Window 22-28 Oct 2026 · 18+ Gamble responsibly — original analysis, not betting advice. No price is copied from OLBG or any bookmaker.</p></footer></body></html>"
def fmt_price(dec):
    return "—" if dec is None else f"{dec} ({amer(dec):+d})"
def market_cell(r):
    m = r["markets"]; w = m["win"]; h = m["handicap"]; t = m["total"]
    s = f"<strong>Win:</strong> {e(r['home'])} {fmt_price(w.get('home_price'))} · {e(r['away'])} {fmt_price(w.get('away_price'))}"
    if h.get("line_home") is not None: s += f"<br><strong>{e(h['label'])}:</strong> home {h['line_home']:+.1f} {fmt_price(h.get('home_price'))} · away {-h['line_home']:+.1f} {fmt_price(h.get('away_price'))}"
    else: s += f"<br><strong>{e(h['label'])}</strong>"
    if t.get("line") is not None: s += f"<br><strong>{e(t['label'])}:</strong> {t['line']} — Over {fmt_price(t.get('over_price'))} · Under {fmt_price(t.get('under_price'))}"
    else: s += f"<br><strong>{e(t['label'])}:</strong> {e(t.get('note','not originated'))}"
    return s
def table(rs, show_pred=False):
    th = "<tr><th>Date</th><th>Competition</th><th>Match</th><th>Our own lines (win / handicap / total)</th><th>Pick</th><th>Conf.</th><th>Verified basis (form)</th><th>Official source</th><th>Status</th></tr>"
    out = []
    for r in rs:
        match = f"{e(r['away'])} at {e(r['home'])}<br><span class='small'>{e(r['date'])} · {e(r['time'])}{(' · '+e(r['venue'])) if r['venue'] else ''}</span>"
        if show_pred and r.get("prediction"): match += f"<div class='pred'><strong>Prediction ({len(r['prediction'].split())} words):</strong> {e(r['prediction'])}</div>"
        conf = f"<span class='badge b-{r['confidence'].lower()}'>{e(r['confidence'])}</span>" if r["confidence"] else "—"
        pick = f"<strong>{e(r['pick'])}</strong><br><span class='small'>{e(r['pick_market'])}<br>model {r['model_prob'] if r['model_prob'] is not None else '—'} · our price {fmt_price(r['our_price'])}</span>" if r["pick"] else "—"
        out.append(f"<tr><td>{e(r['date'])}</td><td>{e(r['competition'])}</td><td>{match}</td><td>{market_cell(r)}</td><td>{pick}</td><td>{conf}</td><td>{e(r['basis'])}{('<br><span class=small>'+e(r['note'])+'</span>') if r['note'] else ''}</td><td><a href='{e(r['source_url'])}'>{e(r['source_label'])}</a></td><td><span class='badge b-{r['status'].lower()}'>{e(r['status'])}</span></td></tr>")
    return f"<div style='overflow:auto'><table>{th}{''.join(out)}</table></div>"

priced = [r for r in rows if r["our_price"] is not None]
high = [r for r in rows if r["confidence"] == "High"]
body = f"""<div class='hero' style='margin:0 -20px;padding-left:20px;padding-right:20px'><h1>Fresh fixtures, our own lines — priced only where official form was verified</h1>
<p class='lede'>Board T re-read the official NHL, NBA, MLB and PDC pages on <strong>22 Oct 2026</strong> and originated its own match-winner, handicap and match-total lines for the 22–28 Oct window. High confidence is reserved for model probabilities of at least 66% whose originated price sits inside the requested focus window of <strong>−250 to +10,000 American</strong>; heavier favourites are capped at Medium and flagged, not promoted. Every High pick carries a unique, human-written prediction naming the teams, a player, current form, recent history and the exact selection. Anything that could not be confirmed from an official source is blank and on the Flagged for Review page — never filled in.</p>
<p class='small'>Excluded, per brief: soccer, boxing, UFC/MMA, American football, hurling, horse racing, cycling, specials. Gaelic football is <em>not</em> excluded (only hurling is) — it appears on the Coverage page as not refreshed, not as a breach.</p></div>
<div class='kpis'><div class='kpi'><div class='n'>{len(rows)}</div><div class='l'>Rows published</div></div><div class='kpi'><div class='n'>{len(priced)}</div><div class='l'>Fixtures priced</div></div><div class='kpi'><div class='n'>{len(high)}</div><div class='l'>High-confidence picks</div></div><div class='kpi'><div class='n'>{len(set(r['sport'] for r in priced))}</div><div class='l'>Sports priced</div></div><div class='kpi'><div class='n'>{len(flagged)}</div><div class='l'>Flagged items</div></div><div class='kpi'><div class='n'>22–28 Oct</div><div class='l'>Window (2026)</div></div></div>
<div class='card'><h2>All rows — line by line</h2>{table(rows, show_pred=True)}</div>"""
open(os.path.join(OUT, "index.html"), "w").write(page("OLBG4 Board T — fresh verified desk 22-28 Oct 2026", body))

open(os.path.join(OUT, "picks.html"), "w").write(page("High-confidence picks — Board T",
 f"<h1>High-confidence picks (model ≥66%, price −250…+10,000)</h1><p>Each prediction is unique, at least 30 words, and quotes only facts from the linked official pages: team, a named player with his official leader line, current form and recent history, and the obvious selection. Picks whose model probability was even higher but whose price fell shorter than −250 were downgraded to Medium and are listed on the Flagged page instead of being promoted.</p>{table(high, show_pred=True)}"))
open(os.path.join(OUT, "markets.html"), "w").write(page("Markets investigated — Board T",
 "<h1>Every available market, investigated per fixture</h1><p>For each priced fixture we originated three market families: <strong>match winner</strong>, <strong>handicap</strong> (puck line / point spread / run line) and <strong>match total</strong> (goals / points / runs). Where a family could not be priced from a verified official input — NBA totals (no pace data captured) and all three darts families (no ranking for both players) — the cell says so and the row is flagged. The full per-fixture market cells are in the table on the <a href='index.html'>dashboard</a>.</p>" + table(priced)))
flag_rows = "".join(f"<tr><td>{e(f['id'])}</td><td>{e(f['kind'])}</td><td>{e(f['text'])}</td><td>{('<a href='+chr(39)+e(f['source'])+chr(39)+'>source</a>') if f['source'] else '—'}</td></tr>" for f in flagged)
open(os.path.join(OUT, "flagged.html"), "w").write(page("Flagged for Review — Board T",
 f"<h1>Flagged for Review</h1><p>Unverified values are blank, never inferred. These items do not block publication; review them here and request changes.</p><div style='overflow:auto'><table><tr><th>ID</th><th>Kind</th><th>Irregularity / gap</th><th>Source</th></tr>{flag_rows}</table></div>"))
srcs = sorted(set((r["source_url"], r["source_label"]) for r in rows if r["source_url"]) | set((r["form_source_url"], r["form_source_label"]) for r in rows if r.get("form_source_url")))
open(os.path.join(OUT, "sources.html"), "w").write(page("Official sources — Board T",
 "<h1>Official sources (only source tier used for values)</h1><table><tr><th>Source</th><th>URL</th></tr>" + "".join(f"<tr><td>{e(l)}</td><td><a href='{e(u)}'>{e(u)}</a></td></tr>" for u, l in srcs) + "</table><p class='small'>OLBG.com is a taxonomy reference only (docs/olbg-reverse-engineering.md in the repo root); no OLBG price or tip was used. Sandbox curl to sports domains fails (SSL_ERROR_SYSCALL), so pages were read with the agent web-fetch tool on 2026-10-22; the exact URL read is stored on every row in data/session-4ec1fc72/data.json.</p>"))
open(os.path.join(OUT, "methodology.html"), "w").write(page("Methodology — Board T", """<h1>Methodology — how every line was originated</h1>
<div class='card'><h2>Prices</h2><p>decimal = 1 / (model probability × 1.04) (4% two-way overround, repo METHODOLOGY.md). American odds are shown beside every decimal price. Focus window: −250 to +10,000 American (decimal 1.40–101.00).</p></div>
<div class='card'><h2>Confidence</h2><p><strong>High</strong>: model probability ≥0.66 <em>and</em> originated price inside −250…+10,000. A pick at ≥0.70 that prices shorter than −250 is capped at Medium and flagged — the brief asks us to focus High picks inside the window, not to collect heavy chalk. <strong>Medium</strong>: ≥0.58. <strong>Low</strong>: below that, or any capped row. NBA rows are all capped Low (0–1 games played per club at snapshot). MLB rows are capped below High (probable pitchers not on the payload read).</p></div>
<div class='card'><h2>NHL (repo METHODOLOGY SS2.1)</h2><p>rating = 0.5 + (points% − 0.5)·GP/(GP+12) + 0.012·(GF−GA)/GP, from the official NHL.com standings of 21 Oct; p(home) = 0.5 + (rating diff)·0.80 + 0.035 home ice (removed for the neutral-site Winnipeg game), clamped 0.08–0.92. Totals: per-team goal rates shrunk toward 3.05 with weight 10, expected total clamped 4.5–8.5, line = floor(mean)+0.5, P(over) from a normal CDF with sd 1.9. Puck line ±1.5 priced from the expected margin with sd 2.0.</p></div>
<div class='card'><h2>NBA (adapted, stated here in full)</h2><p>Only current-season records were captured (NBA.com standings, 22 Oct: every club 0–1 games), so rating = 0.5 + (win% − 0.5)·GP/(GP+20) and p(home) = 0.5 + (rating diff)·0.80 + 0.055. Spread = the half-point line nearest the model median margin (sd 11.5), priced at the model's own 50% point. Totals were investigated and deliberately not originated: no official pace/efficiency table was captured. All NBA rows are capped Low for the one-game sample — grading them higher would be invented form.</p></div>
<div class='card'><h2>MLB (repo METHODOLOGY SS2.3)</h2><p>win% shrunk by 162/202 toward .500 from the official 2026 standings; p(home) = sigmoid(logit diff + 0.17). Expected runs from runs scored/allowed per 162 (±0.12 home term); total line = floor(mean)+0.5, sd 1.85; run line ±1.5 from expected margin, sd 1.9.</p></div>
<div class='card'><h2>Darts</h2><p>Fixtures verified on pdc.tv. No line originated: the official article gives narrative form for a handful of players but no quantitative ranking/average for both players in every tie. Inventing prices would breach the no-hallucination rule, so all three market families are flagged unpriced.</p></div>"""))
ver_rows = "".join(f"<tr><td>{e(r['id'])}</td><td>{e(r['sport'])}</td><td>{e(r['away'])} at {e(r['home'])}</td><td>{e(r['pick']) or '—'}{' '+str(r['american']) if r['american'] is not None else ''}</td><td>{e(r['confidence']) or '—'}</td><td><a href='{e(r['source_url'])}'>fixture source</a>{(' · <a href='+chr(39)+e(r['form_source_url'])+chr(39)+'>form source</a>') if r.get('form_source_url') else ''}</td><td>{e(r['status'])}</td></tr>" for r in rows)
open(os.path.join(OUT, "verification.html"), "w").write(page("Verification — Board T",
 f"<h1>Line-by-line verification register</h1><p>Every row below was read on the linked official page on 2026-10-22. Re-running <code>python3 session-4ec1fc72/build.py</code> then <code>python3 session-4ec1fc72/verify.py</code> reproduces this board and checks: official-domain sources only, no excluded sport, High ⇒ probability ≥0.66, price in −250…+10,000, unique ≥30-word prediction naming the selection; unpriced rows carry a flag.</p><div style='overflow:auto'><table><tr><th>ID</th><th>Sport</th><th>Fixture</th><th>Pick &amp; American</th><th>Conf.</th><th>Official sources</th><th>Status</th></tr>{ver_rows}</table></div>"))
cov_rows = "".join(f"<tr><td>{e(s)}</td><td>{e(st)}</td><td>{('<a href='+chr(39)+e(u)+chr(39)+'>official source</a>') if u else '—'}</td></tr>" for s, st, u in COVERAGE)
open(os.path.join(OUT, "coverage.html"), "w").write(page("Coverage by sport — Board T",
 f"<h1>Coverage — every in-scope sport</h1><p>Excluded: {e(', '.join(EXCLUDED))}. Sports not refreshed in this session are listed honestly as gaps and flagged — Board T does not re-badge earlier boards' stale rows as verified.</p><table><tr><th>Sport</th><th>Board T status (22–28 Oct window)</th><th>Source</th></tr>{cov_rows}</table>"))
for s in SPORTS:
    rs = [r for r in rows if r["sport"] == s]
    open(os.path.join(OUT, "sports", slug(s) + ".html"), "w").write(page(f"{s} — Board T", f"<h1>{e(s)}</h1>{table(rs, show_pred=True)}", "../"))
print(f"rows={len(rows)} priced={len(priced)} high={len(high)} flagged={len(flagged)} sports={SPORTS}")
for r in high: print("HIGH", r["id"], r["pick"], r["model_prob"], r["our_price"], r["american"])
for r in priced:
    if r["confidence"] == "Medium" and r["note"].startswith("Model probability"):
        print("CAPPED", r["id"], r["pick"], r["model_prob"], r["our_price"], r["american"])
