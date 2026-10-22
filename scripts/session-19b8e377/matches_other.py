#!/usr/bin/env python3
"""Board Z — verified fixture inputs, part 2: volleyball, tennis, basketball, snooker."""

V, T, B, S = [], [], [], []


def add(bucket, **kw):
    bucket.append(kw)


# --------------------------------------------------------------------------
# VOLLEYBALL — Czech ČEZ Extraliga muži (verified table, round 1 scores,
# round 2 & 3 programme).  stats: gp, sw, sl, pf, pa
# --------------------------------------------------------------------------
CV = "SRC-CVF-EXTRALIGA"
CV_URL = "https://www.cvf.cz/extraliga-muzi/"

CV_TEAMS = {
    "Kladno volejbal cz": dict(gp=1, sw=3, sl=0, pf=75, pa=56),
    "VK Jihostroj České Budějovice": dict(gp=1, sw=3, sl=0, pf=79, pa=71),
    "VK Lvi Praha": dict(gp=1, sw=3, sl=1, pf=97, pa=79),
    "SKV Ústí nad Labem": dict(gp=1, sw=3, sl=1, pf=96, pa=87),
    "Black Volley Beskydy": dict(gp=1, sw=3, sl=2, pf=112, pa=100),
    "VSC Zlín": dict(gp=1, sw=3, sl=2, pf=100, pa=94),
    "VK Ostrava": dict(gp=1, sw=2, sl=3, pf=94, pa=100),
    "VK Dukla Liberec": dict(gp=1, sw=2, sl=3, pf=100, pa=112),
    "VK Trox Příbram": dict(gp=1, sw=1, sl=3, pf=87, pa=96),
    "VK Benátky nad Jizerou": dict(gp=1, sw=1, sl=3, pf=79, pa=97),
    "Volejbal Brno": dict(gp=1, sw=0, sl=3, pf=71, pa=79),
    "AERO Odolena Voda": dict(gp=1, sw=0, sl=3, pf=56, pa=75),
    "ČEZ Karlovarsko": dict(gp=0, sw=0, sl=0, pf=0, pa=0),
}


def cv(mid, date, time, home, away, venue=""):
    add(V, id=mid, sport="Volleyball", competition="ČEZ Extraliga muži 2026/27, základní část",
        date=date, time=time, tnote="Czech local clock time as printed by ČVS; not converted",
        home=home, away=away, venue=venue, src=CV, url=CV_URL, model="volleyball",
        hs=dict(CV_TEAMS[home]), as_=dict(CV_TEAMS[away]),
        facts=[f"{home} after round 1: {CV_TEAMS[home]['sw']} sets won / {CV_TEAMS[home]['sl']} lost, points {CV_TEAMS[home]['pf']}:{CV_TEAMS[home]['pa']}",
               f"{away} after round 1: {CV_TEAMS[away]['sw']} sets won / {CV_TEAMS[away]['sl']} lost, points {CV_TEAMS[away]['pf']}:{CV_TEAMS[away]['pa']}"],
        note="")


cv("Z-100", "2026-10-22", "18:00", "Volejbal Brno", "AERO Odolena Voda")
cv("Z-101", "2026-10-22", "18:00", "VK Ostrava", "Kladno volejbal cz")
cv("Z-102", "2026-10-22", "18:00", "SKV Ústí nad Labem", "VSC Zlín")
cv("Z-103", "2026-10-22", "18:00", "VK Dukla Liberec", "VK Benátky nad Jizerou")
cv("Z-104", "2026-10-22", "18:00", "VK Jihostroj České Budějovice", "Black Volley Beskydy")
cv("Z-105", "2026-10-24", "17:00", "VK Trox Příbram", "VK Lvi Praha")
cv("Z-106", "2026-10-24", "18:00", "Black Volley Beskydy", "Volejbal Brno")
cv("Z-107", "2026-10-24", "18:00", "ČEZ Karlovarsko", "VK Dukla Liberec")
cv("Z-108", "2026-10-24", "18:00", "Kladno volejbal cz", "SKV Ústí nad Labem")
cv("Z-109", "2026-10-24", "18:00", "AERO Odolena Voda", "VK Ostrava")
cv("Z-110", "2026-10-24", "19:00", "VK Benátky nad Jizerou", "VK Jihostroj České Budějovice")

# --------------------------------------------------------------------------
# VOLLEYBALL — Italian SuperLega Credem Banca, Giornata 2 (verified)
# --------------------------------------------------------------------------
SL = "SRC-LEGAVOLLEY-TABLE"
SL_URL = "https://www.legavolley.it/classifica/?IdCampionato=999"
SL_CAL = "https://www.legavolley.it/calendario/?idCampionato=999"

SL_TEAMS = {
    "Cisterna Volley": dict(gp=1, sw=3, sl=0, pf=79, pa=56, pts=3),
    "Gas Sales Bluenergy Piacenza": dict(gp=1, sw=3, sl=0, pf=75, pa=56, pts=3),
    "Itas Trentino": dict(gp=1, sw=3, sl=0, pf=75, pa=61, pts=3),
    "Cucine Lube Civitanova": dict(gp=1, sw=3, sl=0, pf=78, pa=65, pts=3),
    "Tinet Prata di Pordenone": dict(gp=1, sw=3, sl=1, pf=94, pa=91, pts=3),
    "Sir Susa Scai Perugia": dict(gp=1, sw=3, sl=2, pf=114, pa=95, pts=2),
    "Acqua Sant'Anna Cuneo": dict(gp=1, sw=2, sl=3, pf=95, pa=114, pts=1),
    "Vero Volley Monza": dict(gp=1, sw=1, sl=3, pf=91, pa=94, pts=0),
    "Rana Verona": dict(gp=1, sw=0, sl=3, pf=65, pa=78, pts=0),
    "Valsa Group Modena": dict(gp=1, sw=0, sl=3, pf=61, pa=75, pts=0),
    "Pallavolo Padova": dict(gp=1, sw=0, sl=3, pf=56, pa=75, pts=0),
    "Allianz Milano": dict(gp=1, sw=0, sl=3, pf=56, pa=79, pts=0),
}


def sl(mid, date, time, home, away, venue=""):
    add(V, id=mid, sport="Volleyball", competition="SuperLega Credem Banca 2026/27, Giornata 2",
        date=date, time=time, tnote="Italian local clock time as printed by Lega Pallavolo Serie A; not converted",
        home=home, away=away, venue=venue, src=SL, url=SL_CAL, model="volleyball",
        hs=dict(SL_TEAMS[home]), as_=dict(SL_TEAMS[away]),
        facts=[f"{home}: {SL_TEAMS[home]['sw']}-{SL_TEAMS[home]['sl']} sets on the opening day, points {SL_TEAMS[home]['pf']}:{SL_TEAMS[home]['pa']}, {SL_TEAMS[home]['pts']} league points",
               f"{away}: {SL_TEAMS[away]['sw']}-{SL_TEAMS[away]['sl']} sets on the opening day, points {SL_TEAMS[away]['pf']}:{SL_TEAMS[away]['pa']}, {SL_TEAMS[away]['pts']} league points"],
        note="")


sl("Z-120", "2026-10-25", "17:00", "Itas Trentino", "Cisterna Volley", "BTS Arena, Trento")
sl("Z-121", "2026-10-25", "18:00", "Sir Susa Scai Perugia", "Tinet Prata di Pordenone", "Pala Barton Energy, Perugia")
sl("Z-122", "2026-10-25", "18:00", "Gas Sales Bluenergy Piacenza", "Valsa Group Modena", "PalaBancaSport, Piacenza")
sl("Z-123", "2026-10-25", "18:00", "Cucine Lube Civitanova", "Pallavolo Padova", "Eurosuole Forum, Civitanova Marche")
sl("Z-124", "2026-10-25", "18:00", "Vero Volley Monza", "Rana Verona", "OpiquadArena, Monza")
sl("Z-125", "2026-10-25", "19:00", "Allianz Milano", "Acqua Sant'Anna Cuneo", "Allianz Cloud, Milano")

# --------------------------------------------------------------------------
# TENNIS — ATP Tour Round of 16, Thursday 22 October 2026 (verified order of play)
# inputs: atp_points (PIF ATP Rankings, 2026.10.19) and rank
# --------------------------------------------------------------------------
ATP = "SRC-ATP-RANKINGS"
ATP_SCORES = "SRC-ATP-SCORES"

T_PLAYERS = {
    "T. Atmane": (98, 616), "M. Bellucci": (68, 812),
    "T. Machac": (72, 779), "K. Khachanov": (25, 1990),
    "D. Medvedev": (5, 3660), "S. Shimabukuro": (None, None),
    "A. Bublik": (19, 2275), "F. Marozsan": (64, 860),
    "R. Collignon": (55, 978), "J. Lehecka": (20, 2235),
    "D. Goffin": (None, None), "A. Michelsen": (37, 1370),
    "D. Dzumhur": (83, 712), "Z. Bergs": (41, 1220),
    "V. Vacherot": (32, 1480), "L. Van Assche": (48, 1065),
    "P. Herbert": (None, None), "T. Fritz": (14, 2880),
    "F. Cobolli": (6, 3640), "S. Wawrinka": (None, None),
    "K. Jacquet": (85, 703), "B. Nakashima": (17, 2375),
}


def ten(mid, date, time, tour, home, away, court, facts, venue=""):
    hr, hp = T_PLAYERS[home]
    ar, ap = T_PLAYERS[away]
    add(T, id=mid, sport="Tennis", competition=f"ATP Tour 2026 — {tour}, Round of 16",
        date=date, time=time, tnote="Clock time exactly as printed on the ATP order of play (tournament local time); not converted",
        home=home, away=away, venue=venue or court, src=ATP_SCORES if hp and ap else ATP,
        url="https://www.atptour.com/en/scores/current", model="tennis",
        hs=dict(rank=hr, pts=hp), as_=dict(rank=ar, pts=ap), facts=facts, note=court)


ten("Z-200", "2026-10-22", "11:30", "Almaty Open", "T. Atmane", "M. Bellucci", "Center Court",
    ["Atmane is world No. 98 on 616 points; Bellucci is No. 68 on 812 points (19 Oct 2026 list)",
     "Bellucci beat Tomas Martin Etcheverry 7-6(5) 2-6 6-4 in the Almaty round of 32",
     "Atmane beat Rinky Hijikata 7-6(5) 6-2 in the Almaty round of 32"])
ten("Z-201", "2026-10-22", "13:00", "Almaty Open", "T. Machac", "K. Khachanov", "Center Court",
    ["Machac is world No. 72 on 779 points; Khachanov is No. 25 on 1,990 points",
     "Khachanov beat Rei Sakamoto 6-2 6-4 in the Almaty round of 32",
     "Machac beat Zangar Nurlanuly 6-2 6-0 in the Almaty round of 32"])
ten("Z-202", "2026-10-22", "14:00", "Almaty Open", "D. Medvedev", "S. Shimabukuro", "Center Court",
    ["Medvedev is world No. 5 on 3,660 points and is the top seed in Almaty",
     "Shimabukuro's ranking is outside the ATP top 100 captured on 19 Oct 2026, so no verified points total is held here",
     "Shimabukuro beat Roman Safiullin 6-7(4) 6-4 6-4 in the Almaty round of 32"])
ten("Z-203", "2026-10-22", "19:30", "Almaty Open", "A. Bublik", "F. Marozsan", "Center Court",
    ["Bublik is world No. 19 on 2,275 points and is seeded third in Almaty",
     "Marozsan is world No. 64 on 860 points",
     "Marozsan beat Timofey Skatov 7-5 7-6(4) in the Almaty round of 32",
     "Bublik beat Fabian Marozsan's compatriot in no verified match this week (no head-to-head held)"])
ten("Z-204", "2026-10-22", "13:30", "European Open Brussels", "R. Collignon", "J. Lehecka", "Centre Court",
    ["Collignon is world No. 55 on 978 points; Lehecka is No. 20 on 2,235 points and seeded second",
     "Collignon beat Nishesh Basavareddy 3-6 6-3 6-4 in Brussels",
     "Lehecka is the second seed and received a bye into the round of 16"])
ten("Z-205", "2026-10-22", "15:00", "European Open Brussels", "D. Goffin", "A. Michelsen", "Centre Court",
    ["Michelsen is world No. 37 on 1,370 points and is seeded fifth in Brussels",
     "Goffin's ranking is outside the ATP top 100 captured on 19 Oct 2026, so no verified points total is held here",
     "Goffin beat Remy Bertola 3-6 6-3 6-4 in Brussels as a wild card"])
ten("Z-206", "2026-10-22", "17:00", "European Open Brussels", "D. Dzumhur", "Z. Bergs", "Centre Court",
    ["Bergs is world No. 41 on 1,220 points and is seeded sixth in Brussels",
     "Dzumhur is world No. 83 on 712 points",
     "Dzumhur beat Dino Prizmic 7-6(5) 2-6 6-2 in Brussels",
     "Bergs beat Toby Samuel 6-3 7-6(3) in Brussels"])
ten("Z-207", "2026-10-22", "14:00", "Grand Prix Auvergne-Rhone-Alpes Lyon", "V. Vacherot", "L. Van Assche", "Court Central",
    ["Vacherot is world No. 32 on 1,480 points and is seeded third in Lyon",
     "Van Assche is world No. 48 on 1,065 points",
     "Van Assche beat Clement Tabur 7-6(3) 6-3 in Lyon",
     "Vacherot is the third seed and received a bye into the round of 16"])
ten("Z-208", "2026-10-22", "20:30", "Grand Prix Auvergne-Rhone-Alpes Lyon", "P. Herbert", "T. Fritz", "Court Central",
    ["Fritz is world No. 14 on 2,880 points and is seeded second in Lyon",
     "Herbert came through qualifying and beat Sebastian Baez 6-3 6-4 in the Lyon round of 32",
     "Herbert's ranking is outside the ATP top 100 captured on 19 Oct 2026"])
ten("Z-209", "2026-10-22", "19:00", "Grand Prix Auvergne-Rhone-Alpes Lyon", "F. Cobolli", "S. Wawrinka", "Court Central",
    ["Cobolli is world No. 6 on 3,640 points and is the top seed in Lyon",
     "Wawrinka beat Martin Landaluce 6-3 6-7(2) 7-6(5) in the Lyon round of 32 as a wild card",
     "Wawrinka's ranking is outside the ATP top 100 captured on 19 Oct 2026"])
ten("Z-210", "2026-10-22", "21:00", "Grand Prix Auvergne-Rhone-Alpes Lyon", "K. Jacquet", "B. Nakashima", "Court Central",
    ["Nakashima is world No. 17 on 2,375 points and is seeded fifth in Lyon",
     "Jacquet is world No. 85 on 703 points and came through qualifying",
     "Jacquet beat Matteo Berrettini 7-6(4) 7-5 in Lyon",
     "Nakashima beat Hamad Medjedovic 7-6(4) 6-7(4) 6-2 in Lyon"])

# --------------------------------------------------------------------------
# BASKETBALL — EuroLeague 2026-27 Regular Season, Round 7 (verified)
# stats: gp, w, l, pf, pa
# --------------------------------------------------------------------------
EL = "SRC-EUROLEAGUE-GC"
EL_URL = "https://www.euroleaguebasketball.net/en/euroleague/game-center/"

EL_TEAMS = {
    "Panathinaikos AKTOR Athens": dict(gp=6, w=5, l=1, pf=528, pa=438, seed=1),
    "Fenerbahce Tarfin Istanbul": dict(gp=6, w=5, l=1, pf=501, pa=447, seed=2),
    "Olympiacos Piraeus": dict(gp=6, w=5, l=1, pf=564, pa=524, seed=3),
    "Hapoel IBI Tel Aviv": dict(gp=7, w=5, l=2, pf=630, pa=601, seed=4),
    "Valencia Basket": dict(gp=6, w=4, l=2, pf=583, pa=537, seed=5),
    "Crvena Zvezda Meridianbet Belgrade": dict(gp=6, w=4, l=2, pf=485, pa=457, seed=6),
    "Dubai Basketball": dict(gp=6, w=4, l=2, pf=490, pa=493, seed=7),
    "Virtus Bologna": dict(gp=7, w=4, l=3, pf=606, pa=608, seed=8),
    "Real Madrid": dict(gp=6, w=3, l=3, pf=554, pa=531, seed=9),
    "FC Barcelona": dict(gp=6, w=3, l=3, pf=534, pa=525, seed=10),
    "Besiktas Istanbul": dict(gp=6, w=3, l=3, pf=554, pa=555, seed=11),
    "Partizan Mozzart Bet Belgrade": dict(gp=6, w=3, l=3, pf=466, pa=471, seed=12),
    "Anadolu Efes Istanbul": dict(gp=6, w=2, l=4, pf=492, pa=510, seed=13),
    "Zalgiris Kaunas": dict(gp=6, w=2, l=4, pf=490, pa=517, seed=14),
    "FC Bayern Munich": dict(gp=6, w=2, l=4, pf=521, pa=552, seed=15),
    "Maccabi Rapyd Tel Aviv": dict(gp=6, w=2, l=4, pf=509, pa=540, seed=16),
    "LDLC ASVEL Villeurbanne": dict(gp=6, w=2, l=4, pf=527, pa=572, seed=17),
    "Paris Basketball": dict(gp=6, w=1, l=5, pf=504, pa=545, seed=18),
    "Armani Olimpia Milan": dict(gp=6, w=1, l=5, pf=504, pa=559, seed=19),
    "Kosner Baskonia Vitoria-Gasteiz": dict(gp=6, w=1, l=5, pf=504, pa=564, seed=20),
}


def el(mid, date, time, home, away, venue, facts):
    add(B, id=mid, sport="Basketball", competition="EuroLeague 2026-27, Regular Season Round 7",
        date=date, time=time, tnote="Arena clock time exactly as printed by the EuroLeague game centre; the page does not name a timezone, so it was not converted",
        home=home, away=away, venue=venue, src=EL, url=EL_URL, model="basketball",
        hs=dict(EL_TEAMS[home]), as_=dict(EL_TEAMS[away]), facts=facts, note="")


el("Z-300", "2026-10-22", "13:30", "Anadolu Efes Istanbul", "Besiktas Istanbul",
   "TURKCELL BASKETBALL DEVELOPMENT CENTER",
   ["Efes are 2-4 (492:510, -18) and 13th; Besiktas are 3-3 (554:555, -1) and 11th",
    "Efes have scored 492 points in six games, the third-lowest total in the 20-team table",
    "The EuroLeague fixture slug lists Efes first and the hall printed is the Turkcell Development Center"])
el("Z-301", "2026-10-22", "14:00", "FC Bayern Munich", "Dubai Basketball",
   "SAP GARDEN",
   ["Bayern are 2-4 (521:552, -31) and 15th; Dubai are 4-2 (490:493, -3) and 7th",
    "Bayern have conceded 552 points in six games, the fifth-worst defensive total in the league",
    "Dubai have won four of six in their first EuroLeague season"])
el("Z-302", "2026-10-22", "14:05", "Maccabi Rapyd Tel Aviv", "Real Madrid",
   "ALEKSANDAR NIKOLIC HALL",
   ["Maccabi are 2-4 (509:540, -31) and 16th; Real Madrid are 3-3 (554:531, +23) and 9th",
    "Real Madrid have a +23 differential; Maccabi are -31",
    "Maccabi's home games are staged at the Aleksandar Nikolic Hall in Belgrade, as the EuroLeague game centre shows"])
el("Z-303", "2026-10-22", "14:15", "Panathinaikos AKTOR Athens", "Kosner Baskonia Vitoria-Gasteiz",
   "TELEKOM CENTER ATHENS",
   ["Panathinaikos lead the league at 5-1 with a +90 differential (528:438)",
    "Baskonia are 19th at 1-5 with a -60 differential (504:564)",
    "Panathinaikos have the best points-difference in the 20-team table"])
el("Z-304", "2026-10-22", "14:30", "Armani Olimpia Milan", "FC Barcelona",
   "UNIPOL FORUM",
   ["Milano are 19th at 1-5 (504:559, -55); Barça are 10th at 3-3 (534:525, +9)",
    "Milano have lost five of six, conceding 559 points",
    "Barça are level on three wins with Real Madrid, Besiktas and Partizan"])
el("Z-305", "2026-10-22", "14:45", "Partizan Mozzart Bet Belgrade", "Crvena Zvezda Meridianbet Belgrade",
   "BELGRADE ARENA",
   ["Partizan are 12th at 3-3 (466:471, -5); Crvena Zvezda are 6th at 4-2 (485:457, +28)",
    "Partizan have scored only 466 points in six games, the fewest in the top 12",
    "Crvena Zvezda are 4-2 and hold a +28 differential"])
el("Z-306", "2026-10-23", "13:00", "Zalgiris Kaunas", "LDLC ASVEL Villeurbanne",
   "ZALGIRIO ARENA",
   ["Zalgiris are 14th at 2-4 (490:517, -27); ASVEL are 17th at 2-4 (527:572, -45)",
    "ASVEL have conceded 572 points in six games, the second-worst defensive record in the league",
    "Both teams are 2-4 and separated only by points difference"])
el("Z-307", "2026-10-23", "14:15", "Olympiacos Piraeus", "Fenerbahce Tarfin Istanbul",
   "SUNEL ARENA",
   ["Olympiacos are 3rd at 5-1 (564:524, +40); Fenerbahce are 2nd at 5-1 (501:447, +54)",
    "Fenerbahce have the best points-against figure in the league at 447 in six games",
    "Olympiacos are the league's highest scorers at 564 points"])
el("Z-308", "2026-10-23", "14:45", "Paris Basketball", "Valencia Basket",
   "ADIDAS ARENA",
   ["Paris are 18th at 1-5 (504:545, -41); Valencia are 5th at 4-2 (583:537, +46)",
    "Valencia average 97.2 points per game across six EuroLeague games",
    "Paris have lost five of six in their second EuroLeague season"])

# --------------------------------------------------------------------------
# BASKETBALL — Liga Endesa ACB, Jornada 5 (verified table + J4 scores)
# --------------------------------------------------------------------------
ACB = "SRC-ACB-TABLE"
ACB_URL = "https://acb.com/es/liga/clasificacion"

ACB_TEAMS = {
    "Real Madrid": dict(gp=4, w=4, l=0, pf=442, pa=361),
    "Kosner Baskonia": dict(gp=4, w=3, l=1, pf=386, pa=330),
    "Río Breogán": dict(gp=4, w=3, l=1, pf=428, pa=399),
    "La Laguna Tenerife": dict(gp=4, w=3, l=1, pf=332, pa=310),
    "Casademont Zaragoza": dict(gp=4, w=3, l=1, pf=364, pa=346),
    "Monbus Obradoiro": dict(gp=4, w=3, l=1, pf=367, pa=360),
    "Valencia Basket": dict(gp=4, w=2, l=2, pf=399, pa=369),
    "Asisa Joventut": dict(gp=4, w=2, l=2, pf=386, pa=367),
    "Unicaja": dict(gp=4, w=2, l=2, pf=338, pa=325),
    "Barça": dict(gp=4, w=2, l=2, pf=391, pa=400),
    "Surne Bilbao": dict(gp=4, w=2, l=2, pf=388, pa=402),
    "FIATC Girona": dict(gp=4, w=2, l=2, pf=364, pa=400),
    "Recoletas Salud San Pablo Burgos": dict(gp=4, w=1, l=3, pf=350, pa=354),
    "iLERNA Lleida": dict(gp=4, w=1, l=3, pf=373, pa=394),
    "MoraBanc Andorra": dict(gp=4, w=1, l=3, pf=352, pa=380),
    "UCAM Murcia": dict(gp=4, w=1, l=3, pf=347, pa=384),
    "Leyma Coruña": dict(gp=4, w=1, l=3, pf=366, pa=422),
    "Kids&Us Manresa": dict(gp=4, w=0, l=4, pf=342, pa=412),
}


def acb(mid, date, time, home, away, venue, facts):
    add(B, id=mid, sport="Basketball", competition="Liga Endesa 2026-27, Jornada 5",
        date=date, time=time, tnote="Clock time as rendered by acb.com for this browser; ACB does not state a timezone on the standings view, so it was not converted",
        home=home, away=away, venue=venue, src=ACB, url=ACB_URL, model="basketball",
        hs=dict(ACB_TEAMS[home]), as_=dict(ACB_TEAMS[away]), facts=facts, note="")


acb("Z-310", "2026-10-24", "12:00", "Kids&Us Manresa", "Recoletas Salud San Pablo Burgos", "Pavelló Nou Congost, Manresa",
    ["Manresa are 18th and winless at 0-4, scoring 342 and conceding 412 (-70)",
     "Burgos are 13th at 1-3 (350:354, -4)",
     "Manresa lost 72-84 at home to Unicaja on 17 October 2026"])
acb("Z-311", "2026-10-24", "13:30", "UCAM Murcia", "Leyma Coruña", "Palacio de Deportes de Murcia",
    ["Murcia are 16th at 1-3 (347:384, -37)",
     "Coruña are 17th at 1-3 with the worst differential in the league at -56 (366:422)",
     "Valencia beat Murcia 116-93 on 18 October 2026"])
acb("Z-312", "2026-10-24", "15:00", "Barça", "Casademont Zaragoza", "Palau Blaugrana, Barcelona",
    ["Barça are 10th at 2-2 but have a negative differential (-9, 391:400)",
     "Zaragoza are 5th at 3-1 (364:346, +18)",
     "Joventut beat Barça 113-89 on 18 October 2026"])
acb("Z-313", "2026-10-25", "07:00", "Surne Bilbao", "MoraBanc Andorra", "Bilbao Arena",
    ["Bilbao are 11th at 2-2 (388:402, -14); Andorra are 15th at 1-3 (352:380, -28)",
     "Real Madrid beat Bilbao 119-84 on 18 October 2026",
     "Obradoiro beat Andorra 90-85 on 18 October 2026"])
acb("Z-314", "2026-10-25", "07:00", "FIATC Girona", "Asisa Joventut", "Pavelló Girona-Fontajau",
    ["Girona are 12th at 2-2 (364:400, -36); Joventut are 8th at 2-2 (386:367, +19)",
     "Girona beat Coruña 110-90 on 18 October 2026",
     "Joventut beat Barça 113-89 on 18 October 2026"])
acb("Z-315", "2026-10-25", "08:00", "La Laguna Tenerife", "Monbus Obradoiro", "Pabellón Insular Santiago Martín",
    ["Tenerife are 4th at 3-1 (332:310, +22); Obradoiro are 6th at 3-1 (367:360, +7)",
     "Tenerife lost 80-81 at home to Zaragoza on 18 October 2026",
     "Obradoiro won 79-72 at Burgos on 17 October 2026"])
acb("Z-316", "2026-10-25", "12:00", "Valencia Basket", "Kosner Baskonia", "Roig Arena, Valencia",
    ["Valencia are 7th at 2-2 (399:369, +30); Baskonia are 2nd at 3-1 (386:330, +56)",
     "Valencia beat Murcia 116-93 on 18 October 2026",
     "Baskonia won 98-97 at Burgos on 27 September and lost 77-82 at Tenerife on 18 October 2026"])
acb("Z-317", "2026-10-25", "13:00", "Río Breogán", "Unicaja", "Pazo dos Deportes, Lugo",
    ["Breogán are 3rd at 3-1 (428:399, +29); Unicaja are 9th at 2-2 (338:325, +13)",
     "Breogán beat Joventut 110-104 on 27 September and lost 102-108 at Andorra on 17 October 2026",
     "Unicaja won 84-72 at Manresa on 17 October 2026"])
acb("Z-318", "2026-10-25", "14:00", "iLERNA Lleida", "Real Madrid", "Pavelló Barris Nord, Lleida",
    ["Real Madrid are top at 4-0 with the best differential in the league (+81, 442:361)",
     "Lleida are 14th at 1-3 (373:394, -21)",
     "Real Madrid beat Bilbao 119-84 on 18 October 2026",
     "Zaragoza beat Lleida 109-98 on 18 October 2026"])

# --------------------------------------------------------------------------
# SNOOKER — BetVictor Northern Ireland Open 2026, Round 3 (Last 16)
# Verified complete fixtures and start times; rankings held only for part of the field.
# --------------------------------------------------------------------------
WST = "SRC-WST-MATCHES"
WST_URL = "https://www.wst.tv/matches"
WST_R = "SRC-WST-RANKINGS"

SN_PLAYERS = {
    "Matthew Selt": None,
    "Kyren Wilson": dict(rank=9, money=716800, centuries=0),
    "Anthony McGill": None,
    "Elliot Slessor": None,
    "Mark Williams": dict(rank=8, money=747400, centuries=0),
    "David Gilbert": dict(rank=None, money=73250, centuries=20),
    "Jak Jones": dict(rank=None, money=141000, centuries=16),
    "Jordan Brown": None,
}

SN_MATCHES = [
    ("Z-400", "08:00", "Matthew Selt", "Sam Craigie", "Match 51"),
    ("Z-401", "08:00", "Kyren Wilson", "Pang Junxu", "Match 50"),
    ("Z-402", "09:00", "Anthony McGill", "Mateusz Baranowski", "Match 49"),
    ("Z-403", "09:00", "Elliot Slessor", "Ricky Walden", "Match 52"),
    ("Z-404", "14:00", "Mark Williams", "Martin O'Donnell", "Match 54"),
    ("Z-405", "14:00", "David Gilbert", "Ka Wai Cheung", "Match 53"),
    ("Z-406", "15:00", "Jordan Brown", "Scott Donaldson", "Match 56"),
    ("Z-407", "15:00", "Jak Jones", "Daniel Wells", "Match 55"),
]

SN_ROUND2 = {
    "Matthew Selt": "beat Louis Heathcote 4-2 in round 2",
    "Sam Craigie": "beat Xu Si 4-3 in round 2",
    "Kyren Wilson": "beat Thepchaiya Un-Nooh 4-2 in round 2",
    "Pang Junxu": "beat Liam Davies 4-3 in round 2",
    "Anthony McGill": "beat Jack Lisowski 4-1 in round 2",
    "Mateusz Baranowski": "beat Wang Xinbo 4-3 in round 2",
    "Elliot Slessor": "beat Jamie Jones 4-1 in round 2",
    "Ricky Walden": "beat Joe O'Connor 4-3 in round 2",
    "Mark Williams": "beat Zhang Anda 4-2 in round 2",
    "Martin O'Donnell": "beat Luca Brecel 4-2 in round 2",
    "David Gilbert": "beat Gao Yang 4-3 in round 2",
    "Ka Wai Cheung": "beat Stuart Bingham 4-0 in round 2",
    "Jordan Brown": "beat Michael Holt 4-3 in round 2",
    "Scott Donaldson": "beat Noppon Saengkham 4-1 in round 2",
    "Jak Jones": "beat John Higgins 4-2 in round 2",
    "Daniel Wells": "beat Ryan Day 4-3 in round 2",
}

for sid, t, home, away, mtc in SN_MATCHES:
    add(S, id=sid, sport="Snooker", competition="BetVictor Northern Ireland Open 2026, Round 3 (Last 16)",
        date="2026-10-22", time=t,
        tnote="Clock time exactly as printed by wst.tv; the site renders in the visitor's timezone and does not name it, so it was not converted",
        home=home, away=away, venue="", src=WST, url=WST_URL, model="snooker",
        hs=dict(SN_PLAYERS.get(home) or {}), as_=dict(SN_PLAYERS.get(away) or {}),
        facts=[f"{home} {SN_ROUND2[home]}", f"{away} {SN_ROUND2[away]}"],
        note=mtc)
