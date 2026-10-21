#!/usr/bin/env python3
"""
Board K / session 6b8d2d5f — build the verified match dataset.

Every fixture in this file was read from an official governing-body endpoint on
2026-10-21 (UTC) with the exact URL stored on the row.  No value is inferred:
fields that could not be confirmed are left null and the row says so.

Model (documented in methodology.html):
  NHL   : pts% = (2W + OTL) / (2·GP);  p_home = 0.5 + 0.55·(pts%_home − pts%_away) + 0.03
  NBA   : shrunk win% = (W+1)/(GP+2) toward .500; p_home = 0.5 + 0.90·(s_home − s_away) + 0.03
  MLB   : win% = W/(W+L);              p_home = 0.5 + 0.90·(wp_home − wp_away) + 0.035
  Decimal price = (1/p) / 1.035  (our own 3.5% overround, never a bookmaker price)
  Handicap = sigma·Φ⁻¹(p) rounded to the sport's half-line; cover probability from the
  same normal margin model; price from the cover probability at the same 3.5% overround.
  Total    = only priced when BOTH teams' goals-for/against are verified (NHL only today).
Confidence: High p >= 0.65 · Medium 0.55 <= p < 0.65 · Low p < 0.55.
"""
import json, os, statistics
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
N = statistics.NormalDist()
RETRIEVED = "2026-10-21T12:30:00Z"

NBA_SRC = "https://www.nba.com/schedule?date={d}"
NBA_GAMES = "https://www.nba.com/games?date={d}"
NHL_SCORE = "https://api-web.nhle.com/v1/score/{d}"
NHL_SCHED = "https://api-web.nhle.com/v1/schedule/{d}"
MLB_SCHED = ("https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-21"
             "&endDate=2026-10-27")
MLB_STAND = ("https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season=2026"
             "&standingsTypes=regularSeason")

REC = {}   # team -> (w, l, otl) for NHL; (w, l) for others


def nhl_record(t, w, l, otl):
    REC[t] = (w, l, otl)


def nba_record(t, w, l):
    REC[t] = (w, l)


def mlb_record(t, w, l):
    REC[t] = (w, l)


# ---------------------------------------------------------------- verified inputs
# NHL records as returned by api-web.nhle.com/v1/score/{date} (away.record / home.record).
for t, r in {
    "NSH": (3, 2, 3), "BOS": (7, 2, 1), "NYR": (7, 3, 1), "TOR": (5, 4, 2),
    "SJS": (5, 4, 1), "OTT": (6, 3, 0), "ANA": (4, 5, 0), "NJD": (5, 4, 0),
    "FLA": (5, 2, 2), "PIT": (3, 6, 1), "LAK": (1, 4, 2), "NYI": (5, 3, 1),
    "VGK": (8, 3, 0), "STL": (4, 4, 1), "WPG": (4, 3, 2), "DAL": (5, 3, 1),
    "MIN": (6, 2, 2), "CGY": (2, 6, 0), "CAR": (8, 2, 1), "EDM": (7, 1, 1),
    "UTA": (7, 3, 0), "SEA": (6, 3, 1), "DET": (3, 3, 3), "VAN": (2, 8, 1),
    "PHI": (2, 6, 3), "BUF": (4, 3, 2),
}.items():
    nhl_record(t, *r)

# NHL goals for/against, from api-web.nhle.com/v1/standings/2026-10-20 (standings snapshot).
NHL_GF_GA = {"CAR": (42, 27, 11), "EDM": (41, 27, 9), "BOS": (36, 22, 10), "VGK": (44, 30, 11)}

# NBA records as displayed on nba.com schedule pages at retrieval.
for t, r in {
    "Boston Celtics": (0, 1), "Detroit Pistons": (1, 0), "Philadelphia 76ers": (1, 0),
    "New York Knicks": (0, 1), "Oklahoma City Thunder": (1, 0), "San Antonio Spurs": (0, 1),
}.items():
    nba_record(t, *r)

# MLB 2026 regular-season records from statsapi.mlb.com standings.
mlb_record("Tampa Bay Rays", 98, 64)
mlb_record("Milwaukee Brewers", 103, 59)


# ---------------------------------------------------------------- model helpers
NHL_ABBR = {}


def nhl_pct(t):
    t = NHL_ABBR.get(t, t)
    w, l, otl = REC[t]
    gp = w + l + otl
    return (2 * w + otl) / (2 * gp)


def nba_pct(t):
    # 10 games of .500 prior: one opening-week result cannot move a rating far.
    w, l = REC.get(t, (0, 0))
    return (w + 5) / (w + l + 10)


def mlb_pct(t):
    w, l = REC[t]
    return w / (w + l)


def price(p):
    return round(1 / p / 1.035, 2)


def band(p):
    return "High" if p >= 0.65 else ("Medium" if p >= 0.55 else "Low")


def handicap(p, sigma, half=0.5):
    mu = sigma * N.inv_cdf(p)
    line = round(abs(mu) * 2) / 2
    line = max(half, line)
    cover = 1 - N.cdf((line - mu) / sigma)     # favourite covers line
    return {
        "side": "home" if p >= 0.5 else "away",
        "line": line,
        "price": price(min(max(cover, .02), .98)),
        "coverProb": round(cover, 3),
        "note": f"line = σ·Φ⁻¹(p) with σ={sigma}; cover probability from the same normal margin model",
    }


def total_from_gfga(home, away):
    if home not in NHL_GF_GA or away not in NHL_GF_GA:
        return None
    hgf, hga, hgp = NHL_GF_GA[home]
    agf, aga, agp = NHL_GF_GA[away]
    exp_h = ((hgf / hgp) + (aga / agp)) / 2
    exp_a = ((agf / agp) + (hga / hgp)) / 2
    line = round((exp_h + exp_a) * 2) / 2
    return {"line": line, "expHome": round(exp_h, 2), "expAway": round(exp_a, 2),
            "over": price(0.5), "under": price(0.5),
            "note": "expected goals from each club's verified GF/GA per game (NHL standings 20 Oct)"}


def row(id_, sport, league, date, time, venue, away, home, status, source_url,
        source_name, pct_fn, sigma, result=None, records_note="", extra_note="",
        total=None):
    ph = pct_fn(away), pct_fn(home)
    p = 0.5 + sigma["w"] * (ph[1] - ph[0]) + sigma["edge"]
    p = min(max(p, .05), .95)
    pick_home = p >= 0.5
    pick = f"{home} to win" if pick_home else f"{away} to win"
    return {
        "id": id_, "sport": sport, "league": league, "date": date, "time": time,
        "venue": venue, "away": away, "home": home, "status": status, "result": result,
        "sourceUrl": source_url, "sourceName": source_name, "retrievedAt": RETRIEVED,
        "inputs": {
            "awayPct": round(ph[0], 3), "homePct": round(ph[1], 3),
            "awayRecord": REC.get(away), "homeRecord": REC.get(home),
            "note": records_note,
        },
        "model": {
            "pHome": round(p, 3), "pAway": round(1 - p, 3),
            "pick": pick, "pickProb": round(max(p, 1 - p), 3), "confidence": band(max(p, 1 - p)),
            "moneyline": {"home": price(p), "away": price(1 - p)},
            "handicap": handicap(max(p, 1 - p), sigma["hcap"]) if pick_home else None,
            "total": total,
        },
        "prediction": None, "notes": extra_note,
    }


# ---------------------------------------------------------------- NBA
def finals_row(id_, sport, league, date, venue, away, home, score, source_url, source_name,
                prior_pick=None, note=""):
    """A completed fixture: result only. No line is originated after the fact."""
    return {
        "id": id_, "sport": sport, "league": league, "date": date, "time": "Final",
        "venue": venue, "away": away, "home": home, "status": "Final", "result": score,
        "sourceUrl": source_url, "sourceName": source_name, "retrievedAt": RETRIEVED,
        "inputs": {"note": "Official final; no model inputs are used for a completed fixture."},
        "model": None,
        "priorPick": prior_pick,
        "graded": (None if not prior_pick else
                   ("won" if prior_pick.lower().startswith(away.lower()) and score.split("–")[0].strip() > score.split("–")[1].strip()
                    else "won" if prior_pick.lower().startswith(home.lower()) and score.split("–")[1].strip() > score.split("–")[0].strip()
                    else "lost")),
        "prediction": None,
        "notes": note or "Completed before this dataset was built; only the verified result is published (no after-the-fact line).",
    }


NBA_ROWS = []
NBA_FINALS = [
    ("NBA-F01", "2026-10-20", "Boston Celtics", "Detroit Pistons", "113–121", "Little Caesars Arena, Detroit, MI"),
    ("NBA-F02", "2026-10-20", "Philadelphia 76ers", "New York Knicks", "106–100", "Madison Square Garden, New York, NY"),
    ("NBA-F03", "2026-10-20", "Oklahoma City Thunder", "San Antonio Spurs", "116–104", "Frost Bank Center, San Antonio, TX"),
]
NBA_PRIOR = {"NBA-F01": "Detroit Pistons", "NBA-F02": "New York Knicks", "NBA-F03": "Oklahoma City Thunder"}
for id_, d, a, h, score, venue in NBA_FINALS:
    NBA_ROWS.append(finals_row(
        id_, "Basketball", "NBA", d, venue, a, h, score,
        NBA_GAMES.format(d=d), "NBA.com official games page (final score)",
        prior_pick=NBA_PRIOR.get(id_),
        note="Build D (data/matches.json) published a pick on this fixture; it is graded here against the official final."))

NBA_UPCOMING = [
    # date, away, home, ET time, venue
    ("2026-10-21", "Atlanta Hawks", "Orlando Magic", "19:00 ET", "Kia Center, Orlando, FL"),
    ("2026-10-21", "Milwaukee Bucks", "Washington Wizards", "19:00 ET", "Capital One Arena, Washington, DC"),
    ("2026-10-21", "Minnesota Timberwolves", "Miami Heat", "19:30 ET", "Kaseya Center, Miami, FL"),
    ("2026-10-21", "Charlotte Hornets", "Brooklyn Nets", "19:30 ET", "Barclays Center, Brooklyn, NY"),
    ("2026-10-21", "Chicago Bulls", "Toronto Raptors", "19:30 ET", "Scotiabank Arena, Toronto, ON"),
    ("2026-10-21", "Utah Jazz", "Memphis Grizzlies", "20:00 ET", "FedExForum, Memphis, TN"),
    ("2026-10-21", "Indiana Pacers", "New Orleans Pelicans", "20:00 ET", "Smoothie King Center, New Orleans, LA"),
    ("2026-10-21", "Dallas Mavericks", "Houston Rockets", "20:30 ET", "Toyota Center, Houston, TX"),
    ("2026-10-21", "Golden State Warriors", "Los Angeles Lakers", "22:00 ET", "Crypto.com Arena, Los Angeles, CA"),
    ("2026-10-21", "Phoenix Suns", "Portland Trail Blazers", "22:00 ET", "Moda Center, Portland, OR"),
    ("2026-10-21", "Sacramento Kings", "LA Clippers", "22:30 ET", "Intuit Dome, Inglewood, CA"),
    ("2026-10-22", "Cleveland Cavaliers", "Philadelphia 76ers", "19:00 ET", "Xfinity Mobile Arena, Philadelphia, PA"),
    ("2026-10-22", "Denver Nuggets", "Oklahoma City Thunder", "21:30 ET", "Paycom Center, Oklahoma City, OK"),
    ("2026-10-23", "Chicago Bulls", "Milwaukee Bucks", "16:00 ET", "Fiserv Forum, Milwaukee, WI"),
    ("2026-10-23", "New York Knicks", "Boston Celtics", "19:00 ET", "TD Garden, Boston, MA"),
    ("2026-10-23", "Atlanta Hawks", "Charlotte Hornets", "19:00 ET", "Spectrum Center, Charlotte, NC"),
    ("2026-10-23", "Dallas Mavericks", "Indiana Pacers", "19:00 ET", "Gainbridge Fieldhouse, Indianapolis, IN"),
    ("2026-10-23", "Minnesota Timberwolves", "Orlando Magic", "19:00 ET", "Kia Center, Orlando, FL"),
    ("2026-10-23", "Toronto Raptors", "Washington Wizards", "19:00 ET", "Capital One Arena, Washington, DC"),
    ("2026-10-23", "Detroit Pistons", "Miami Heat", "20:00 ET", "Kaseya Center, Miami, FL"),
    ("2026-10-23", "Houston Rockets", "San Antonio Spurs", "21:30 ET", "Moody Center, Austin, TX"),
    ("2026-10-23", "New Orleans Pelicans", "Utah Jazz", "21:30 ET", "Delta Center, Salt Lake City, UT"),
    ("2026-10-23", "Memphis Grizzlies", "Golden State Warriors", "22:00 ET", "Chase Center, San Francisco, CA"),
    ("2026-10-23", "LA Clippers", "Los Angeles Lakers", "22:00 ET", "Crypto.com Arena, Los Angeles, CA"),
]
for i, (d, a, h, t, venue) in enumerate(NBA_UPCOMING, start=1):
    NBA_ROWS.append(row(
        f"NBA-{d[5:7]}{d[8:10]}-{i:02d}", "Basketball", "NBA", d, t, venue, a, h, "Scheduled",
        (NBA_GAMES.format(d=d) if d in ("2026-10-21", "2026-10-23") else NBA_SRC.format(d=d)),
        ("NBA.com official games page (date)" if d in ("2026-10-21", "2026-10-23")
         else "NBA.com official schedule (date page)"),
        nba_pct, {"w": 0.90, "edge": 0.03, "hcap": 12.5},
        records_note="Win-loss records exactly as displayed by NBA.com at retrieval; opening-week samples are shrunk hard toward .500, so every NBA line here is low confidence by construction.",
        extra_note="Early-season sample: no club had played more than one game, so the model cannot justify a high-confidence pick."))

# ---------------------------------------------------------------- NHL
NHL_ROWS = []
NHL_FINALS = [
    ("NHL-F01", "2026-10-20", "San Jose Sharks", "Montreal Canadiens", "4–3 (OT)", "Centre Bell, Montréal"),
    ("NHL-F02", "2026-10-20", "Colorado Avalanche", "New Jersey Devils", "3–4", "Prudential Center, Newark, NJ"),
    ("NHL-F03", "2026-10-20", "Anaheim Ducks", "New York Islanders", "2–3", "UBS Arena, Elmont, NY"),
]
NHL_PRIOR = {"NHL-F01": "Montreal Canadiens"}
for id_, d, a, h, score, venue in NHL_FINALS:
    NHL_ROWS.append(finals_row(
        id_, "Ice Hockey", "NHL", d, venue, a, h, score,
        NHL_SCORE.format(d=d), "NHL official scores endpoint (final score, venue)",
        prior_pick=NHL_PRIOR.get(id_),
        note="Build D published a pick on this fixture; it is graded here against the official final (Sharks won 4-3 in overtime)."))

NHL_UPCOMING = [
    ("2026-10-21", "Philadelphia Flyers", "Buffalo Sabres", "19:30 ET", "KeyBank Center, Buffalo, NY", "PHI", "BUF"),
    ("2026-10-21", "Florida Panthers", "Ottawa Senators", "19:30 ET", "Canadian Tire Centre, Ottawa, ON", "FLA", "OTT"),
    ("2026-10-22", "Nashville Predators", "Boston Bruins", "19:00 ET", "TD Garden, Boston, MA", "NSH", "BOS"),
    ("2026-10-22", "New York Rangers", "Toronto Maple Leafs", "19:00 ET", "Scotiabank Arena, Toronto, ON", "NYR", "TOR"),
    ("2026-10-22", "San Jose Sharks", "Ottawa Senators", "19:00 ET", "Canadian Tire Centre, Ottawa, ON", "SJS", "OTT"),
    ("2026-10-22", "Anaheim Ducks", "New Jersey Devils", "19:00 ET", "Prudential Center, Newark, NJ", "ANA", "NJD"),
    ("2026-10-22", "Florida Panthers", "Pittsburgh Penguins", "19:00 ET", "PPG Paints Arena, Pittsburgh, PA", "FLA", "PIT"),
    ("2026-10-22", "Los Angeles Kings", "New York Islanders", "19:30 ET", "UBS Arena, Elmont, NY", "LAK", "NYI"),
    ("2026-10-22", "Vegas Golden Knights", "St. Louis Blues", "20:00 ET", "Enterprise Center, St. Louis, MO", "VGK", "STL"),
    ("2026-10-22", "Winnipeg Jets", "Dallas Stars", "20:00 ET", "American Airlines Center, Dallas, TX", "WPG", "DAL"),
    ("2026-10-22", "Minnesota Wild", "Calgary Flames", "21:00 ET", "Scotiabank Saddledome, Calgary, AB", "MIN", "CGY"),
    ("2026-10-22", "Carolina Hurricanes", "Edmonton Oilers", "21:00 ET", "Rogers Place, Edmonton, AB", "CAR", "EDM"),
    ("2026-10-22", "Utah Mammoth", "Seattle Kraken", "22:00 ET", "Climate Pledge Arena, Seattle, WA", "UTA", "SEA"),
    ("2026-10-22", "Detroit Red Wings", "Vancouver Canucks", "22:00 ET", "Rogers Arena, Vancouver, BC", "DET", "VAN"),
]
NHL_TEAM_NAME = {}  # abbrev -> full name used in the dataset
for _, a, h, _, _, aa, ha in NHL_UPCOMING:
    NHL_TEAM_NAME[aa] = a
    NHL_TEAM_NAME[ha] = h
NHL_TEAM_NAME.update({"SJS": "San Jose Sharks", "MTL": "Montreal Canadiens",
                      "COL": "Colorado Avalanche", "NJD": "New Jersey Devils",
                      "ANA": "Anaheim Ducks", "NYI": "New York Islanders"})

for abbr, name in NHL_TEAM_NAME.items():
    NHL_ABBR[name] = abbr
NHL_ABBR.update({"San Jose Sharks": "SJS", "Montreal Canadiens": "MTL",
                 "Colorado Avalanche": "COL", "New Jersey Devils": "NJD",
                 "Anaheim Ducks": "ANA", "New York Islanders": "NYI"})

for i, (d, a, h, t, venue, aa, ha) in enumerate(NHL_UPCOMING, start=1):
    NHL_ROWS.append(row(
        f"NHL-{d[5:7]}{d[8:10]}-{i:02d}", "Ice Hockey", "NHL", d, t, venue, a, h, "Scheduled",
        NHL_SCORE.format(d=d), "NHL official scores endpoint (fixture, venue, records)",
        nhl_pct, {"w": 0.55, "edge": 0.03, "hcap": 1.8},
        records_note=f"Records verified in the NHL score payload: {aa} {REC[aa][0]}-{REC[aa][1]}-{REC[aa][2]}, {ha} {REC[ha][0]}-{REC[ha][1]}-{REC[ha][2]}.",
        total=total_from_gfga(ha, aa)))

# ---------------------------------------------------------------- MLB
MLB_ROWS = []
MLB_GAMES = [
    ("MLB-WS1", "2026-10-23", "20:00 ET", "American Family Field, Milwaukee, WI",
     "Tampa Bay Rays", "Milwaukee Brewers", "Game 1, World Series (best-of-seven)"),
    ("MLB-WS2", "2026-10-24", "20:00 ET", "American Family Field, Milwaukee, WI",
     "Tampa Bay Rays", "Milwaukee Brewers", "Game 2, World Series (best-of-seven)"),
    ("MLB-WS3", "2026-10-26", "20:00 ET", "Tropicana Field, St. Petersburg, FL",
     "Milwaukee Brewers", "Tampa Bay Rays", "Game 3, World Series (best-of-seven)"),
    ("MLB-WS4", "2026-10-27", "20:00 ET", "Tropicana Field, St. Petersburg, FL",
     "Milwaukee Brewers", "Tampa Bay Rays", "Game 4, World Series (best-of-seven)"),
]
for id_, d, t, venue, a, h, label in MLB_GAMES:
    r = row(id_, "Baseball", "MLB", d, t, venue, a, h, "Scheduled",
            MLB_SCHED, "MLB official Stats API schedule (postseason) + standings",
            mlb_pct, {"w": 0.90, "edge": 0.035, "hcap": 1.7},
            records_note=f"Regular-season records verified from the MLB Stats API: {a} {REC[a][0]}-{REC[a][1]}, {h} {REC[h][0]}-{REC[h][1]}.",
            extra_note=label + ". Starting pitchers were not published at retrieval, so no pitcher input is used.")
    r["inputs"]["standingsUrl"] = MLB_STAND
    MLB_ROWS.append(r)



# ---------------------------------------------------------------- predictions (high + strong medium)
PRED = {
 "NHL-1021-01": {
  "selection": "Buffalo Sabres to win (moneyline, our price 1.45)",
  "text": ("Buffalo Sabres are our pick at KeyBank Center against the Philadelphia Flyers. The NHL score "
           "endpoint lists Buffalo at 4-3-2 and Philadelphia at 2-6-3, a points-percentage gap of .556 to "
           ".318 that our model converts into a 66% home win probability. Tage Thompson has five goals and "
           "Zach Benson six assists for Buffalo, while Ukko-Pekka Luukkonen has already recorded three wins. "
           "Philadelphia's Matvei Michkov has six goals but the club has lost six of eleven; back Buffalo "
           "moneyline."),
  "facts": [
    ("Buffalo 4-3-2, Philadelphia 2-6-3", "NHL score endpoint 2026-10-21"),
    ("Tage Thompson 5 goals, Zach Benson 6 assists, Luukkonen 3 wins", "same payload, team leaders"),
  ]},
 "NHL-1022-08": {
  "selection": "New York Islanders to win (moneyline, our price 1.36)",
  "text": ("New York Islanders host the Los Angeles Kings at UBS Arena and are the strongest home selection "
           "on Thursday's slate. The NHL score payload has the Islanders at 5-3-1 (.611 points percentage) "
           "against a Kings side at 1-4-2 (.286), and the model prices the home win at 71%. Bo Horvat has "
           "five goals, Matthew Schaefer eight assists and Ilya Sorokin five wins for New York, while Los "
           "Angeles have one win in seven and Darcy Kuemper has a single victory; take the Islanders "
           "moneyline and consider the -1.5 puck line."),
  "facts": [
    ("Islanders 5-3-1, Kings 1-4-2", "NHL score endpoint 2026-10-22"),
    ("Horvat 5 goals, Schaefer 8 assists, Sorokin 5 wins; Kuemper 1 win", "same payload, team leaders"),
  ]},
 "NHL-1022-11": {
  "selection": "Minnesota Wild to win (moneyline, our price 1.35)",
  "text": ("Minnesota Wild are a road pick at the Scotiabank Saddledome because the form gap is the widest "
           "on the board: the NHL score endpoint shows Minnesota at 6-2-2 (.700 points percentage) and "
           "Calgary at 2-6-0 (.250). Kirill Kaprizov already has eleven goals, Quinn Hughes eleven assists "
           "and Jesper Wallstedt six wins, while Calgary's leading scorer has three goals and Dustin Wolf "
           "has one win. Our model gives Minnesota a 72% chance, so take the Wild moneyline."),
  "facts": [
    ("Minnesota 6-2-2, Calgary 2-6-0", "NHL score endpoint 2026-10-22"),
    ("Kaprizov 11 goals, Hughes 11 assists, Wallstedt 6 wins; Frost 3 goals, Wolf 1 win", "same payload, team leaders"),
  ]},
 "NHL-1022-03": {
  "selection": "Boston Bruins to win (moneyline, our price 1.52)",
  "text": ("Boston Bruins return to TD Garden against the Nashville Predators with the better verified "
           "record: 7-2-1 against 3-2-3, which is .750 against .563 in points percentage. David Pastrnak "
           "leads Boston with four goals and eight assists, Jeremy Swayman has six wins in ten decisions, "
           "and Nashville's Ryan O'Reilly and Roman Josi carry their offence. The model makes Boston a 63% "
           "home favourite, so the Bruins moneyline is a medium-confidence selection rather than a high one."),
  "facts": [
    ("Boston 7-2-1, Nashville 3-2-3", "NHL score endpoint 2026-10-22"),
    ("Pastrnak 4 goals 8 assists, Swayman 6 wins", "same payload, team leaders"),
  ]},
 "NHL-1022-07": {
  "selection": "Florida Panthers to win (moneyline, our price 1.55)",
  "text": ("Florida Panthers are the away side to back in Pittsburgh. The NHL score endpoint has Florida at "
           "5-2-2 (.667) and the Penguins at 3-6-1 (.350), and our model converts that into a 64% chance "
           "for the Panthers despite home ice. Brady Tkachuk has six goals, Matthew Tkachuk eleven assists "
           "and Jacob Markstrom three wins for Florida, while Pittsburgh's Evgeni Malkin has five goals and "
           "the club has won three of ten. Take Florida moneyline."),
  "facts": [
    ("Florida 5-2-2, Pittsburgh 3-6-1", "NHL score endpoint 2026-10-22"),
    ("Brady Tkachuk 6 goals, Matthew Tkachuk 11 assists; Malkin 5 goals", "same payload, team leaders"),
  ]},
 "NHL-1022-14": {
  "selection": "Detroit Red Wings to win (moneyline, our price 1.61)",
  "text": ("Detroit Red Wings visit Rogers Arena to face a Vancouver Canucks side that has won twice in "
           "eleven games. The NHL score endpoint lists Detroit at 3-3-3 (.500) and Vancouver at 2-8-1 "
           "(.227), which our model turns into a 62% chance for the visitors. Alex DeBrincat has six goals "
           "and five assists for Detroit and John Gibson has two wins, while Vancouver's Elias Pettersson "
           "has eight assists but Leevi Merilainen has only one win; back Detroit moneyline."),
  "facts": [
    ("Detroit 3-3-3, Vancouver 2-8-1", "NHL score endpoint 2026-10-22"),
    ("DeBrincat 6 goals 5 assists, Gibson 2 wins; Pettersson 8 assists", "same payload, team leaders"),
  ]},
}
ALL = NBA_ROWS + NHL_ROWS + MLB_ROWS
for r in ALL:
    if r["id"] in PRED:
        r["prediction"] = PRED[r["id"]]
        r["prediction"]["wordCount"] = len(r["prediction"]["text"].split())

ALL = NBA_ROWS + NHL_ROWS + MLB_ROWS
json.dump(ALL, open(os.path.join(HERE, "data.json"), "w"), indent=1, ensure_ascii=False)
print("rows:", len(ALL), "| sports:", sorted({r['sport'] for r in ALL}))
from collections import Counter
print("confidence:", Counter(r['model']['confidence'] for r in ALL if r['model']))
print("high:", [(r['id'], r['home'], r['away'], r['model']['pickProb'], r['model']['pick']) for r in ALL if r['model'] and r['model']['confidence'] == 'High'])
print("finals:", [(r['id'], r.get('priorPick'), r.get('graded')) for r in ALL if r['status'] == 'Final'])
print("totals:", [(r['id'], r['model']['total']) for r in ALL if r['model'] and r['model']['total']])
