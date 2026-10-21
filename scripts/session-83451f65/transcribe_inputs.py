#!/usr/bin/env python3
"""Transcribe the fixtures that were opened on official sources during this session.

Every field below was read from the source named in `sources` and nothing is inferred:
blank means "not published on the page we opened".  The output is
data/integrated/inputs.json, the only input to model.py.

Source of each block (all opened 2026-10-21 UTC with the web fetch tool):
  NHL    https://api-web.nhle.com/v1/score/2026-10-22   (and /2026-10-23)
  NBA    https://www.nba.com/games?date=YYYY-MM-DD
  MLB    https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-21&endDate=2026-10-31&...
  EHF    https://ehfcl.eurohandball.com/men/2026-27/matches/
  RU     https://www.premrugby.com/fixtures-results?competition=gallagher-prem&round=4
  SNO    https://www.wst.tv/matches/
"""
import json, pathlib

OUT = pathlib.Path(__file__).resolve().parents[2] / "data" / "integrated" / "inputs.json"
RETRIEVED = "2026-10-21T08:00Z"

SOURCES = [
 {"id": "nhl-score-1022", "sport": "Ice Hockey", "org": "NHL",
  "url": "https://api-web.nhle.com/v1/score/2026-10-22",
  "page": "NHL official score/schedule feed (JSON) for 22 Oct 2026",
  "fields": "game id, venue, startTimeUTC, away/home abbreviation, season record, team leaders"},
 {"id": "nhl-score-1023", "sport": "Ice Hockey", "org": "NHL",
  "url": "https://api-web.nhle.com/v1/score/2026-10-23",
  "page": "NHL official score/schedule feed (JSON) for 23 Oct 2026",
  "fields": "game id, venue, startTimeUTC, away/home abbreviation, season record, team leaders"},
 {"id": "nba-1021", "sport": "Basketball", "org": "NBA",
  "url": "https://www.nba.com/games?date=2026-10-21",
  "page": "NBA.com games page, 21 Oct 2026", "fields": "matchups, tip-off (ET), records, game ids"},
 {"id": "nba-1023", "sport": "Basketball", "org": "NBA",
  "url": "https://www.nba.com/games?date=2026-10-23",
  "page": "NBA.com games page, 23 Oct 2026", "fields": "matchups, tip-off (ET), records, game ids"},
 {"id": "nba-1024", "sport": "Basketball", "org": "NBA",
  "url": "https://www.nba.com/games?date=2026-10-24",
  "page": "NBA.com games page, 24 Oct 2026", "fields": "matchups, tip-off (ET), records, game ids"},
 {"id": "nba-1025", "sport": "Basketball", "org": "NBA",
  "url": "https://www.nba.com/games?date=2026-10-25",
  "page": "NBA.com games page, 25 Oct 2026", "fields": "matchups, tip-off (ET), records, game ids"},
 {"id": "mlb-ws", "sport": "Baseball", "org": "MLB",
  "url": "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-21&endDate=2026-10-31&fields=dates,date,games,gamePk,teams,home,away,team,name,venue,gameDate,status,detailedState,seriesDescription",
  "page": "MLB official StatsAPI schedule, 21-31 Oct 2026", "fields": "gamePk, clubs, venue, series, UTC start, status"},
 {"id": "ehf-cl", "sport": "Handball", "org": "EHF",
  "url": "https://ehfcl.eurohandball.com/men/2026-27/matches/",
  "page": "EHF Champions League men 2026/27 match list", "fields": "round, pairing, published tip time, match detail URL"},
 {"id": "prem-r4", "sport": "Rugby Union", "org": "Premiership Rugby",
  "url": "https://www.premrugby.com/fixtures-results?competition=gallagher-prem&round=4",
  "page": "Gallagher Premiership Round 4 fixtures & results", "fields": "date, venue, published time, recent form string, match centre URL"},
 {"id": "wst-nio", "sport": "Snooker", "org": "World Snooker Tour",
  "url": "https://www.wst.tv/matches/",
  "page": "BetVictor Northern Ireland Open 2026 match list", "fields": "round, match number, pairing, published session time, match centre URL"},
]

R = []
def add(**kw):
    kw.setdefault("hform", ""); kw.setdefault("aform", "")
    kw.setdefault("hlead", ""); kw.setdefault("alead", ""); kw.setdefault("tnote", "")
    R.append(kw)

# ---------------- NHL, 22 Oct 2026 (full 12-game slate) ----------------
nhl22 = [
 ("nsh-bos","NSH","Boston Bruins","Nashville Predators","3-2-3","7-2-1","TD Garden, Boston","2026-10-22T23:00:00Z","2026020154",
  "Ryan O'Reilly 4G / Roman Josi 8A / Juuse Saros 3W","David Pastrnak 4G, 8A / Jeremy Swayman 6W"),
 ("nyr-tor","NYR","Toronto Maple Leafs","New York Rangers","7-3-1","5-4-2","Scotiabank Arena, Toronto","2026-10-22T23:00:00Z","2026020155",
  "Alexis Lafreniere 7G / Adam Fox 10A / Dylan Garand 4W","Auston Matthews 8G, 10A / Anthony Stolarz 3W"),
 ("sjs-ott","SJS","Ottawa Senators","San Jose Sharks","5-4-1","6-3-0","Canadian Tire Centre, Ottawa","2026-10-22T23:00:00Z","2026020156",
  "Macklin Celebrini 5G, 9A / Alex Nedeljkovic 3W","Tim Stutzle 5G, 7A / Linus Ullmark 6W"),
 ("ana-njd","ANA","New Jersey Devils","Anaheim Ducks","4-5-0","5-4-0","Prudential Center, Newark","2026-10-22T23:00:00Z","2026020157",
  "Beckett Sennecke 5G / Leo Carlsson 9A / Lukas Dostal 3W","Nico Hischier 4G / Jack Hughes 7A / Jake Allen 4W"),
 ("fla-pit","FLA","Pittsburgh Penguins","Florida Panthers","5-2-2","3-6-1","PPG Paints Arena, Pittsburgh","2026-10-22T23:00:00Z","2026020158",
  "Brady Tkachuk 6G / Matthew Tkachuk 11A / Jacob Markstrom 3W","Evgeni Malkin 5G / Erik Karlsson 10A / Arturs Silovs 3W"),
 ("lak-nyi","LAK","New York Islanders","Los Angeles Kings","1-4-2","5-3-1","UBS Arena, Elmont","2026-10-22T23:30:00Z","2026020159",
  "Artemi Panarin 4G / Brandt Clarke 4A / Darcy Kuemper 1W","Bo Horvat 5G / Matthew Schaefer 8A / Ilya Sorokin 5W"),
 ("vgk-stl","VGK","St. Louis Blues","Vegas Golden Knights","8-3-0","4-4-1","Enterprise Center, St. Louis","2026-10-23T00:00:00Z","2026020160",
  "Mark Stone 8G / Jack Eichel 13A / Carter Hart 4W","Mason McTavish 5G / Dylan Holloway 6A / Joel Hofer 3W"),
 ("wpg-dal","WPG","Dallas Stars","Winnipeg Jets","4-3-2","5-3-1","American Airlines Center, Dallas","2026-10-23T00:00:00Z","2026020161",
  "Kyle Connor 8G / Mark Scheifele 6A / Stuart Skinner 3W","Mikko Rantanen 5G / Jason Robertson 6A / Jake Oettinger 4W"),
 ("min-cgy","MIN","Calgary Flames","Minnesota Wild","6-2-2","2-6-0","Scotiabank Saddledome, Calgary","2026-10-23T01:00:00Z","2026020162",
  "Kirill Kaprizov 11G / Quinn Hughes 11A / Jesper Wallstedt 6W","Morgan Frost 3G / Joel Farabee 5A / Dustin Wolf 1W"),
 ("car-edm","CAR","Edmonton Oilers","Carolina Hurricanes","8-2-1","7-1-1","Rogers Place, Edmonton","2026-10-23T01:00:00Z","2026020163",
  "Andrei Svechnikov 6G / Jackson Blake 10A / Pyotr Kochetkov 6W","Leon Draisaitl 8G / Connor McDavid 20A / Devon Levi 5W"),
 ("uta-sea","UTA","Seattle Kraken","Utah Mammoth","7-3-0","6-3-1","Climate Pledge Arena, Seattle","2026-10-23T02:00:00Z","2026020164",
  "Nick Schmaltz 7G / Clayton Keller 9A / Karel Vejmelka 5W","Frederick Gaudreau 5G / Chandler Stephenson 8A / Philipp Grubauer 3W"),
 ("det-van","DET","Vancouver Canucks","Detroit Red Wings","3-3-3","2-8-1","Rogers Arena, Vancouver","2026-10-23T02:00:00Z","2026020165",
  "Alex DeBrincat 6G, 5A / John Gibson 2W","Paul Cotter 4G / Elias Pettersson 8A / Leevi Merilainen 1W"),
]
for slug, aab, home, away, arec, hrec, venue, utc, gid, alead, hlead in nhl22:
    add(id=f"nhl-{utc[:10]}-{aab.lower()}-{slug.split('-')[1].upper()}", sport="Ice Hockey", comp="NHL regular season 2026-27",
        date="2026-10-22", time=utc, tnote="UTC start time exactly as published by the NHL feed",
        venue=venue, home=home, away=away, hrec=hrec, arec=arec, hlead=hlead, alead=alead,
        src="nhl-score-1022", ev=f"NHL game {gid}")

# ---------------- NHL, 23 Oct 2026 (both games) ----------------
nhl23 = [
 ("mtl","MTL","Chicago Blackhawks","Montreal Canadiens","4-3-2","3-6-0","United Center, Chicago","2026-10-24T00:00:00Z","2026020166",
  "Cole Caufield 6G / Nick Suzuki 7A / Jacob Fowler 3W","Frank Nazar 3G / Anton Frondell 5A / Spencer Knight 3W"),
 ("tbl","TBL","Colorado Avalanche","Tampa Bay Lightning","7-2-0","5-4-1","Ball Arena, Denver","2026-10-24T01:00:00Z","2026020167",
  "Brandon Hagel 7G / Nikita Kucherov 9A","Artturi Lehkonen 8G"),
]
for slug, aab, home, away, arec, hrec, venue, utc, gid, alead, hlead in nhl23:
    add(id=f"nhl-{utc[:10]}-{aab.lower()}-{slug.upper()}", sport="Ice Hockey", comp="NHL regular season 2026-27",
        date="2026-10-23", time=utc, tnote="UTC start time exactly as published by the NHL feed",
        venue=venue, home=home, away=away, hrec=hrec, arec=arec, hlead=hlead, alead=alead,
        src="nhl-score-1023", ev=f"NHL game {gid}")

# ---------------- NBA ----------------
nba = [
 # date, tip (ET as published), away abbr, away name, arec, home abbr, home name, hrec, game id, source
 ("2026-10-21","19:00 ET","ATL","Atlanta Hawks","0-0","ORL","Orlando Magic","0-0","","nba-1021"),
 ("2026-10-21","19:00 ET","MIL","Milwaukee Bucks","0-0","WAS","Washington Wizards","0-0","","nba-1021"),
 ("2026-10-21","19:30 ET","MIN","Minnesota Timberwolves","0-0","MIA","Miami Heat","0-0","","nba-1021"),
 ("2026-10-21","19:30 ET","CHA","Charlotte Hornets","0-0","BKN","Brooklyn Nets","0-0","","nba-1021"),
 ("2026-10-21","19:30 ET","CHI","Chicago Bulls","0-0","TOR","Toronto Raptors","0-0","","nba-1021"),
 ("2026-10-21","20:00 ET","IND","Indiana Pacers","0-0","NOP","New Orleans Pelicans","0-0","","nba-1021"),
 ("2026-10-21","20:00 ET","UTA","Utah Jazz","0-0","MEM","Memphis Grizzlies","0-0","","nba-1021"),
 ("2026-10-21","20:30 ET","DAL","Dallas Mavericks","0-0","HOU","Houston Rockets","0-0","","nba-1021"),
 ("2026-10-21","22:00 ET","GSW","Golden State Warriors","0-0","LAL","Los Angeles Lakers","0-0","","nba-1021"),
 ("2026-10-21","22:00 ET","PHX","Phoenix Suns","0-0","POR","Portland Trail Blazers","0-0","","nba-1021"),
 ("2026-10-21","22:30 ET","SAC","Sacramento Kings","0-0","LAC","LA Clippers","0-0","","nba-1021"),
 ("2026-10-23","16:00 ET","CHI","Chicago Bulls","0-0","MIL","Milwaukee Bucks","0-0","0022600099","nba-1023"),
 ("2026-10-23","19:00 ET","NYK","New York Knicks","0-1","BOS","Boston Celtics","0-1","0022600008","nba-1023"),
 ("2026-10-23","19:00 ET","TOR","Toronto Raptors","0-0","WAS","Washington Wizards","0-0","0022600097","nba-1023"),
 ("2026-10-23","19:00 ET","ATL","Atlanta Hawks","0-0","CHA","Charlotte Hornets","0-0","0022600094","nba-1023"),
 ("2026-10-23","19:00 ET","MIN","Minnesota Timberwolves","0-0","ORL","Orlando Magic","0-0","0022600096","nba-1023"),
 ("2026-10-23","19:00 ET","DAL","Dallas Mavericks","0-0","IND","Indiana Pacers","0-0","0022600095","nba-1023"),
 ("2026-10-23","20:00 ET","DET","Detroit Pistons","1-0","MIA","Miami Heat","0-0","0022600098","nba-1023"),
 ("2026-10-23","21:30 ET","HOU","Houston Rockets","0-0","SAS","San Antonio Spurs","0-1","0022600009","nba-1023"),
 ("2026-10-23","21:30 ET","NOP","New Orleans Pelicans","0-0","UTA","Utah Jazz","0-0","0022600100","nba-1023"),
 ("2026-10-23","22:00 ET","MEM","Memphis Grizzlies","0-0","GSW","Golden State Warriors","0-0","","nba-1023"),
 ("2026-10-24","18:00 ET","MIA","Miami Heat","0-0","CHA","Charlotte Hornets","0-0","0022600104","nba-1024"),
 ("2026-10-24","19:30 ET","MIL","Milwaukee Bucks","0-0","PHI","Philadelphia 76ers","1-0","0022600106","nba-1024"),
 ("2026-10-24","19:30 ET","BKN","Brooklyn Nets","0-0","CLE","Cleveland Cavaliers","0-0","0022600105","nba-1024"),
 ("2026-10-24","20:00 ET","SAS","San Antonio Spurs","0-1","DAL","Dallas Mavericks","0-0","0022600109","nba-1024"),
 ("2026-10-24","20:00 ET","WAS","Washington Wizards","0-0","CHI","Chicago Bulls","0-0","0022600108","nba-1024"),
 ("2026-10-24","20:30 ET","HOU","Houston Rockets","0-0","ATL","Atlanta Hawks","0-0","0022600107","nba-1024"),
 ("2026-10-24","21:00 ET","NOP","New Orleans Pelicans","0-0","DEN","Denver Nuggets","0-0","0022600110","nba-1024"),
 ("2026-10-24","22:00 ET","GSW","Golden State Warriors","0-0","PHX","Phoenix Suns","0-0","0022600111","nba-1024"),
 ("2026-10-25","17:00 ET","LAL","Los Angeles Lakers","0-0","UTA","Utah Jazz","0-0","0022600112","nba-1025"),
 ("2026-10-25","18:00 ET","IND","Indiana Pacers","0-0","BKN","Brooklyn Nets","0-0","0022600113","nba-1025"),
 ("2026-10-25","19:00 ET","LAC","LA Clippers","0-0","OKC","Oklahoma City Thunder","1-0","0022600116","nba-1025"),
 ("2026-10-25","19:00 ET","ORL","Orlando Magic","0-0","NYK","New York Knicks","0-1","0022600114","nba-1025"),
 ("2026-10-25","19:00 ET","TOR","Toronto Raptors","0-0","MIN","Minnesota Timberwolves","0-0","0022600115","nba-1025"),
 ("2026-10-25","19:30 ET","DET","Detroit Pistons","1-0","PHI","Philadelphia 76ers","1-0","0022600117","nba-1025"),
 ("2026-10-25","21:00 ET","MEM","Memphis Grizzlies","0-0","SAC","Sacramento Kings","0-0","0022600118","nba-1025"),
]
for date, tip, aab, aname, arec, hab, hname, hrec, gid, src in nba:
    add(id=f"nba-{date.replace('-','')}-{aab.lower()}-{hab.lower()}", sport="Basketball", comp="NBA regular season 2026-27",
        date=date, time=tip, tnote="Tip-off in ET exactly as published on nba.com; UTC not derived",
        venue="", home=hname, away=aname, hrec=hrec, arec=arec, src=src,
        ev=(f"NBA game {gid}" if gid else "NBA.com games page listing"))

# ---------------- MLB World Series ----------------
mlb = [
 ("2026-10-23","2026-10-24T00:00:00Z",849805,"Tampa Bay Rays","Milwaukee Brewers","American Family Field"),
 ("2026-10-24","2026-10-25T00:00:00Z",849802,"Tampa Bay Rays","Milwaukee Brewers","American Family Field"),
 ("2026-10-26","2026-10-27T00:00:00Z",849804,"Milwaukee Brewers","Tampa Bay Rays","Tropicana Field"),
 ("2026-10-27","2026-10-28T00:00:00Z",849803,"Milwaukee Brewers","Tampa Bay Rays","Tropicana Field"),
 ("2026-10-28","2026-10-29T00:00:00Z",849799,"Milwaukee Brewers","Tampa Bay Rays","Tropicana Field"),
 ("2026-10-30","2026-10-31T00:00:00Z",849801,"Tampa Bay Rays","Milwaukee Brewers","American Family Field"),
 ("2026-10-31","2026-11-01T00:00:00Z",849800,"Tampa Bay Rays","Milwaukee Brewers","American Family Field"),
]
for d, utc, pk, away, home, venue in mlb:
    add(id=f"mlb-ws-{d.replace('-','')}", sport="Baseball", comp="MLB World Series 2026",
        date=d, time=utc, tnote="gameDate is UTC; the local game date published by MLB is the date shown",
        venue=venue, home=home, away=away, src="mlb-ws", ev=f"MLB gamePk {pk}, series World Series, status Scheduled")

# ---------------- EHF Champions League, 22 Oct ----------------
ehf = [
 ("Szeged","OTP Bank - PICK Szeged","GOG","18:45","202711020101043","202711020101043/OTPBankPICKSzeged-GOG"),
 ("melsungen","MT Melsungen","Orlen Wisla Plock","18:45","202711020101019","202711020101019/MTMelsungen-OrlenWislaPlock"),
 ("barca","Barça","Montpellier Handball","20:45","202711020101049","202711020101049/Bar%C3%A7a-MontpellierHandball"),
 ("sporting","Sporting Clube de Portugal","IFK Kristianstad","20:45","202711020101041","202711020101041/SportingClubedePortugal-IFKKristianstad"),
 ("kolstad","Kolstad Håndball","SC Magdeburg","20:45","202711020101064","202711020101064/KolstadH%C3%A5ndball-SCMagdeburg"),
]
for slug, home, away, t, mid, path in ehf:
    add(id=f"ehf-20261022-{slug}", sport="Handball", comp="EHF Champions League men 2026/27",
        date="2026-10-22", time=t, tnote="Session time exactly as published by EHF; the page does not state a timezone, so it was NOT converted",
        venue="", home=home, away=away, src="ehf-cl",
        ev=f"EHF match id {mid}",
        url_override=f"https://ehfcl.eurohandball.com/men/2026-27/matches/details/{path}/")

# ---------------- Premiership Rugby, round 4 ----------------
ru = [
 ("2026-10-23","14:45","Kingsholm Stadium","Gloucester Rugby","Bath Rugby","W W L W W L","W W L","294923"),
 ("2026-10-23","14:45","Kingston Park","Newcastle Red Bulls","Sale Sharks","L L L L L L","L W W","294924"),
 ("2026-10-24","10:05","Mattioli Woods Welford Road","Leicester Tigers","Northampton Saints","L W W L W W","W L W","294925"),
 ("2026-10-24","12:30","Ashton Gate","Bristol Bears","Exeter Chiefs","W W L W W L","L L W","294926"),
 ("2026-10-25","11:00","Twickenham Stoop","Harlequins","Saracens","L L L L L L","W L W","294927"),
]
for d, t, venue, home, away, hform, aform, mid in ru:
    add(id=f"ru-{d.replace('-','')}-{home.split()[0].lower()}", sport="Rugby Union", comp="Gallagher Premiership 2026-27, Round 4",
        date=d, time=t, tnote="Clock time rendered to this browser's timezone by the source; printed verbatim and NOT converted",
        venue=venue, home=home, away=away, hform=hform, aform=aform, src="prem-r4",
        ev=f"Premiership match centre {mid}",
        url_override=f"https://www.premrugby.com/match-centre/{mid}/news")

# ---------------- WST Northern Ireland Open, 21 Oct ----------------
sno = [
 ("45","08:00","John Higgins","Jak Jones","eba55492-fba6-4a53-90be-a04b3560ae65"),
 ("38","09:00","Sam Craigie","Xu Si","afb42fc9-9654-479e-997e-d33d8a1a6888"),
 ("43","09:00","Zhang Anda","Mark Williams","480e5abf-5766-44ad-9918-f822ceefd4a5"),
 ("47","14:00","Michael Holt","Jordan Brown","e58a00e5-e6a7-479b-98d0-5c7867af28a8"),
 ("48","14:00","Noppon Saengkham","Scott Donaldson","3a24076e-455c-497b-abd5-976e194abc5e"),
 ("41","14:00","Gao Yang","David Gilbert","4fb27af0-7db4-4ec2-b93b-137de3f66135"),
 ("39","15:00","Elliot Slessor","Jamie Jones","f6536f1f-6c2d-47cd-b802-a81e6f04e4cc"),
 ("44","15:00","Luca Brecel","Martin O'Donnell","0c49ba0c-2d21-481e-a2ac-fbece616f591"),
]
for mn, t, p1, p2, mid in sno:
    add(id=f"sno-20261021-m{mn}", sport="Snooker", comp="BetVictor Northern Ireland Open 2026 (Belfast)",
        date="2026-10-21", time=t, tnote="Session time rendered to this browser's timezone by wst.tv; printed verbatim, NOT converted",
        venue="Waterfront Hall, Belfast", home=p1, away=p2, src="wst-nio",
        ev=f"WST match centre for match {mn}",
        url_override=f"https://www.wst.tv/match-centre/{mid}", neutral=True)

for r in R:
    r.setdefault("neutral", False)
    if "url_override" in r:
        r["url"] = r.pop("url_override")

doc = {"schema": "olbg4.integrated.inputs/1", "retrieved_at": RETRIEVED,
       "transcribed_by": "arena/83451f65-olbg4", "sources": SOURCES, "rows": R}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
print(f"wrote {OUT} with {len(R)} rows")
from collections import Counter
print(Counter(r["sport"] for r in R))
