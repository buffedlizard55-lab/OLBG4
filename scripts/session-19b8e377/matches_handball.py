#!/usr/bin/env python3
"""
Board Z — verified fixture inputs for the 22-28 October 2026 window.

Every row below was read on the governing body's own page/endpoint on 22 October
2026 (or, where marked, from the repository's committed official capture of that
same endpoint).  Nothing in this file is inferred: if a number was not printed on
the official source, the field is absent and the row is published without a line.

`s` = the source id in sources_data.SOURCES that the row cites.
`hs` / `as_` = the two sides' verified season numbers, keyed per model.
`facts` = short, quotable, source-linked observations used only for the
          high-confidence write-ups.  Each is a literal reading of the source.
"""

H = []   # handball
V = []   # volleyball
T = []   # tennis
B = []   # basketball
S = []   # snooker


def add(bucket, **kw):
    bucket.append(kw)


# --------------------------------------------------------------------------
# HANDBALL — EHF Champions League Men, group phase (verified standings)
# stats: gp, w, d, l, gf, ga
# --------------------------------------------------------------------------
EHF = "SRC-EHFCL-STANDINGS"
EHF_URL = "https://ehfcl.eurohandball.com/men/2026-27/standings/"

EHF_TEAMS = {
    # Group A
    "One Veszprém HC": dict(gp=5, w=5, d=0, l=0, gf=185, ga=146, grp="A"),
    "Füchse Berlin": dict(gp=5, w=3, d=0, l=2, gf=184, ga=172, grp="A"),
    "FC Porto": dict(gp=5, w=1, d=1, l=3, gf=158, ga=173, grp="A"),
    "RK Partizan AdmiralBet": dict(gp=5, w=0, d=1, l=4, gf=148, ga=184, grp="A"),
    # Group B
    "Orlen Wisla Plock": dict(gp=4, w=3, d=0, l=1, gf=115, ga=108, grp="B"),
    "HBC Nantes": dict(gp=5, w=3, d=0, l=2, gf=142, ga=143, grp="B"),
    "MT Melsungen": dict(gp=4, w=2, d=0, l=2, gf=110, ga=112, grp="B"),
    "HC Vardar 1961": dict(gp=5, w=1, d=0, l=4, gf=154, ga=158, grp="B"),
    # Group C
    "Aalborg Håndbold": dict(gp=5, w=4, d=1, l=0, gf=170, ga=145, grp="C"),
    "Paris Saint-Germain": dict(gp=5, w=3, d=1, l=1, gf=182, ga=157, grp="C"),
    "HC Zagreb": dict(gp=5, w=2, d=0, l=3, gf=146, ga=158, grp="C"),
    "RK Celje Pivovarna Laško": dict(gp=5, w=0, d=0, l=5, gf=150, ga=188, grp="C"),
    # Group D
    "Sporting Clube de Portugal": dict(gp=4, w=3, d=1, l=0, gf=149, ga=125, grp="D"),
    "GOG": dict(gp=4, w=3, d=0, l=1, gf=145, ga=139, grp="D"),
    "OTP Bank - PICK Szeged": dict(gp=4, w=1, d=1, l=2, gf=139, ga=136, grp="D"),
    "IFK Kristianstad": dict(gp=4, w=0, d=0, l=4, gf=122, ga=155, grp="D"),
    # Group E
    "Barça": dict(gp=4, w=4, d=0, l=0, gf=137, ga=104, grp="E"),
    "SAH - Aarhus": dict(gp=5, w=2, d=1, l=2, gf=150, ga=163, grp="E"),
    "Dinamo Bucuresti": dict(gp=5, w=1, d=1, l=3, gf=134, ga=145, grp="E"),
    "Montpellier Handball": dict(gp=4, w=1, d=0, l=3, gf=116, ga=125, grp="E"),
    # Group F
    "SC Magdeburg": dict(gp=4, w=4, d=0, l=0, gf=141, ga=108, grp="F"),
    "Industria Kielce": dict(gp=5, w=3, d=0, l=2, gf=155, ga=153, grp="F"),
    "HC Kriens-Luzern": dict(gp=5, w=2, d=0, l=3, gf=158, ga=161, grp="F"),
    "Kolstad Håndball": dict(gp=4, w=0, d=0, l=4, gf=111, ga=143, grp="F"),
}


def ehf(mid, date, time, home, away, venue=""):
    add(H, id=mid, sport="Handball", competition="EHF Champions League Men 2026/27, group phase",
        date=date, time=time, tnote="Clock time exactly as printed by the EHF standings/calendar page (CET heading); not converted",
        home=home, away=away, venue=venue, src=EHF, url=EHF_URL, model="handball",
        hs=dict(EHF_TEAMS[home]), as_=dict(EHF_TEAMS[away]),
        facts=[f"{home} group-phase record {EHF_TEAMS[home]['w']}W-{EHF_TEAMS[home]['d']}D-{EHF_TEAMS[home]['l']}L in {EHF_TEAMS[home]['gp']} games, goals {EHF_TEAMS[home]['gf']}:{EHF_TEAMS[home]['ga']}",
               f"{away} group-phase record {EHF_TEAMS[away]['w']}W-{EHF_TEAMS[away]['d']}D-{EHF_TEAMS[away]['l']}L in {EHF_TEAMS[away]['gp']} games, goals {EHF_TEAMS[away]['gf']}:{EHF_TEAMS[away]['ga']}"],
        note=f"Group {EHF_TEAMS[home]['grp']}")


ehf("Z-007", "2026-10-22", "18:45", "MT Melsungen", "Orlen Wisla Plock")
ehf("Z-008", "2026-10-22", "18:45", "OTP Bank - PICK Szeged", "GOG")
ehf("Z-009", "2026-10-22", "20:45", "Sporting Clube de Portugal", "IFK Kristianstad")
ehf("Z-010", "2026-10-22", "20:45", "Barça", "Montpellier Handball")
ehf("Z-011", "2026-10-22", "20:45", "Kolstad Håndball", "SC Magdeburg")
ehf("Z-012", "2026-10-29", "18:45", "IFK Kristianstad", "OTP Bank - PICK Szeged")
ehf("Z-013", "2026-10-29", "18:45", "GOG", "Sporting Clube de Portugal")
ehf("Z-014", "2026-10-29", "18:45", "Füchse Berlin", "RK Partizan AdmiralBet")
ehf("Z-015", "2026-10-29", "20:45", "Montpellier Handball", "Dinamo Bucuresti")
ehf("Z-016", "2026-10-29", "20:45", "SAH - Aarhus", "Barça")
ehf("Z-017", "2026-10-28", "18:45", "Orlen Wisla Plock", "HBC Nantes")
ehf("Z-018", "2026-10-28", "18:45", "FC Porto", "One Veszprém HC")
ehf("Z-019", "2026-10-28", "18:45", "HC Vardar 1961", "MT Melsungen")
ehf("Z-020", "2026-10-28", "20:45", "Industria Kielce", "Kolstad Håndball")
ehf("Z-021", "2026-10-28", "20:45", "RK Celje Pivovarna Laško", "HC Zagreb")
ehf("Z-022", "2026-10-28", "20:45", "SC Magdeburg", "HC Kriens-Luzern")
ehf("Z-023", "2026-10-28", "20:45", "Paris Saint-Germain", "Aalborg Håndbold")

# --------------------------------------------------------------------------
# HANDBALL — Danish Betoro Herreligaen (verified table + match programme)
# --------------------------------------------------------------------------
DK = "SRC-TOPHAANDBOLD-TABLE"
DK_URL = "https://tophaandbold.dk/stillinger/herreligaen"
DK_PROG = "https://tophaandbold.dk/kampprogram/herreligaen"

DK_TEAMS = {
    "GOG": dict(gp=10, w=9, d=1, l=0, gf=352, ga=292),
    "Ribe-Esbjerg HH": dict(gp=10, w=7, d=1, l=2, gf=332, ga=311),
    "Aalborg Håndbold": dict(gp=10, w=7, d=1, l=2, gf=323, ga=306),
    "Bjerringbro-Silkeborg": dict(gp=11, w=6, d=1, l=4, gf=349, ga=349),
    "Sønderjyske Herrehåndbold": dict(gp=10, w=6, d=0, l=4, gf=314, ga=303),
    "Fredericia Håndboldklub": dict(gp=10, w=6, d=0, l=4, gf=306, ga=276),
    "Skjern Håndbold": dict(gp=10, w=6, d=0, l=4, gf=329, ga=309),
    "SAH": dict(gp=10, w=6, d=0, l=4, gf=334, ga=327),
    "Nordsjælland Håndbold": dict(gp=10, w=4, d=1, l=5, gf=301, ga=305),
    "TTH Holstebro": dict(gp=10, w=3, d=1, l=6, gf=306, ga=320),
    "Mors-Thy Håndbold": dict(gp=11, w=3, d=0, l=8, gf=325, ga=362),
    "KIF Kolding": dict(gp=10, w=2, d=1, l=7, gf=312, ga=349),
    "TMS Ringsted Herrer": dict(gp=10, w=1, d=1, l=8, gf=306, ga=342),
    "Skive fH": dict(gp=10, w=1, d=0, l=9, gf=328, ga=366),
}


def dk(mid, date, time, home, away, facts, venue=""):
    add(H, id=mid, sport="Handball", competition="Betoro Herreligaen 2026/27, grundspil",
        date=date, time=time, tnote="Danish local clock time as printed in the Tophaandbold match programme (CET/CEST); not converted",
        home=home, away=away, venue=venue, src=DK, url=DK_PROG, model="handball",
        hs=dict(DK_TEAMS[home]), as_=dict(DK_TEAMS[away]), facts=facts, note="")


dk("Z-030", "2026-10-22", "19:30", "Sønderjyske Herrehåndbold", "Nordsjælland Håndbold",
   ["Sønderjyske: 6W-0D-4L, goals 314:303 (+11) after 10 rounds",
    "Nordsjælland: 4W-1D-5L, goals 301:305 (-4) after 10 rounds",
    "Sønderjyske beat Skjern 30:25 on 17 October 2026",
    "Nordsjælland beat TTH Holstebro 36:28 on 17 October 2026"], venue="")
dk("Z-031", "2026-10-22", "20:00", "KIF Kolding", "Fredericia Håndboldklub",
   ["KIF Kolding: 2W-1D-7L, goals 312:349 (-37) after 10 rounds",
    "Fredericia: 6W-0D-4L, goals 306:276 (+30) after 10 rounds",
    "GOG beat KIF Kolding 39:30 on 18 October 2026",
    "Fredericia beat Skive fH 36:29 on 18 October 2026"], venue="")
dk("Z-032", "2026-10-24", "15:00", "Skive fH", "Aalborg Håndbold",
   ["Skive fH: 1W-0D-9L, goals 328:366 (-38) after 10 rounds, bottom of the table",
    "Aalborg: 7W-1D-2L, goals 323:306 (+17) after 10 rounds",
    "Aalborg beat Mors-Thy 37:26 on 18 October 2026",
    "GOG beat Skive 41:29 on 11 October 2026"], venue="")
dk("Z-033", "2026-10-24", "16:00", "Skjern Håndbold", "Ribe-Esbjerg HH",
   ["Skjern: 6W-0D-4L, goals 329:309 (+20) after 10 rounds",
    "Ribe-Esbjerg: 7W-1D-2L, goals 332:311 (+21) after 10 rounds",
    "Sønderjyske beat Skjern 30:25 on 17 October 2026",
    "SAH beat Ribe-Esbjerg 32:29 on 18 October 2026"], venue="")
dk("Z-034", "2026-10-25", "16:00", "SAH", "TTH Holstebro",
   ["SAH: 6W-0D-4L, goals 334:327 (+7) after 10 rounds",
    "TTH Holstebro: 3W-1D-6L, goals 306:320 (-14) after 10 rounds",
    "SAH beat Ribe-Esbjerg 32:29 on 18 October 2026",
    "Nordsjælland beat TTH Holstebro 36:28 on 17 October 2026"], venue="")
dk("Z-035", "2026-10-25", "18:00", "TMS Ringsted Herrer", "GOG",
   ["TMS Ringsted: 1W-1D-8L, goals 306:342 (-36) after 10 rounds",
    "GOG: 9W-1D-0L, goals 352:292 (+60) after 10 rounds, league leaders",
    "GOG beat KIF Kolding 39:30 on 18 October 2026",
    "Bjerringbro-Silkeborg beat TMS Ringsted 31:30 on 18 October 2026"], venue="")

# --------------------------------------------------------------------------
# HANDBALL — French Daikin StarLigue, J08 (verified table + LNH calendar)
# --------------------------------------------------------------------------
FR = "SRC-LNH-TABLE"
FR_URL = "https://www.lnh.fr/daikin-starligue/classement"
FR_CAL = "https://www.lnh.fr/daikin-starligue/calendrier"

FR_TEAMS = {
    "Paris": dict(gp=7, w=7, d=0, l=0, gf=239, ga=190, pts=14),
    "Nantes": dict(gp=7, w=6, d=0, l=1, gf=244, ga=203, pts=12),
    "Montpellier": dict(gp=7, w=4, d=2, l=1, gf=234, ga=205, pts=10),
    "Nîmes": dict(gp=7, w=5, d=0, l=2, gf=228, ga=228, pts=10),
    "Limoges": dict(gp=7, w=4, d=0, l=3, gf=234, ga=214, pts=8),
    "Chartres": dict(gp=7, w=3, d=1, l=3, gf=204, ga=224, pts=7),
    "Tremblay": dict(gp=7, w=3, d=1, l=3, gf=231, ga=227, pts=7),
    "Aix": dict(gp=7, w=3, d=0, l=4, gf=227, ga=223, pts=6),
    "Sélestat": dict(gp=7, w=3, d=0, l=4, gf=208, ga=217, pts=6),
    "Chambéry": dict(gp=7, w=2, d=2, l=3, gf=224, ga=231, pts=6),
    "Saran": dict(gp=7, w=3, d=0, l=4, gf=202, ga=216, pts=6),
    "Caen": dict(gp=7, w=3, d=0, l=4, gf=198, ga=235, pts=6),
    "Toulouse": dict(gp=7, w=3, d=0, l=4, gf=198, ga=201, pts=6),
    "Saint-Raphaël": dict(gp=7, w=2, d=0, l=5, gf=207, ga=225, pts=4),
    "Cesson-Rennes": dict(gp=7, w=1, d=0, l=6, gf=209, ga=227, pts=2),
    "Dunkerque": dict(gp=7, w=1, d=0, l=6, gf=175, ga=196, pts=2),
}


def fr(mid, date, time, home, away, facts, venue=""):
    add(H, id=mid, sport="Handball", competition="Daikin StarLigue 2026/27, J08",
        date=date, time=time, tnote="French local clock time as printed by the LNH calendar (CET/CEST); not converted",
        home=home, away=away, venue=venue, src=FR, url=FR_CAL, model="handball",
        hs=dict(FR_TEAMS[home]), as_=dict(FR_TEAMS[away]), facts=facts, note="")


fr("Z-040", "2026-10-23", "20:00", "Aix", "Toulouse",
   ["Aix sit 8th on 6 points from 7 matches, goals 227:223",
    "Toulouse sit 13th on 6 points from 7 matches, goals 198:201"], venue="")
fr("Z-041", "2026-10-23", "20:00", "Chartres", "Nîmes",
   ["Chartres: 3W-1D-3L for 7 points, goals 204:224 (-20)",
    "Nîmes: 5W-0D-2L for 10 points, goals 228:228 (0)"], venue="")
fr("Z-042", "2026-10-23", "20:00", "Limoges", "Dunkerque",
   ["Limoges: 4W-0D-3L for 8 points, goals 234:214 (+20)",
    "Dunkerque: 1W-0D-6L for 2 points, goals 175:196"], venue="")
fr("Z-043", "2026-10-23", "20:30", "Sélestat", "Caen",
   ["Sélestat: 3W-0D-4L for 6 points, goals 208:217 (-9)",
    "Caen: 3W-0D-4L for 6 points, goals 198:235 (-37)"], venue="")
fr("Z-044", "2026-10-23", "20:30", "Tremblay", "Cesson-Rennes",
   ["Tremblay: 3W-1D-3L for 7 points, goals 231:227",
    "Cesson-Rennes: 1W-0D-6L for 2 points, goals 209:227"], venue="")
fr("Z-045", "2026-10-24", "19:00", "Nantes", "Chambéry",
   ["Nantes are 2nd with 6W-0D-1L for 12 points, goals 244:203 (+41)",
    "Chambéry are 10th with 2W-2D-3L for 6 points, goals 224:231"], venue="")
fr("Z-046", "2026-10-25", "16:00", "Saint-Raphaël", "Paris",
   ["Paris lead the league with 7W-0D-0L for 14 points, goals 239:190 (+49)",
    "Saint-Raphaël are 14th with 2W-0D-5L for 4 points, goals 207:225"], venue="")
fr("Z-047", "2026-10-25", "17:00", "Montpellier", "Saran",
   ["Montpellier are 3rd on 10 points with 4W-2D-1L, goals 234:205 (+29)",
    "Saran are 11th on 6 points with 3W-0D-4L, goals 202:216"], venue="")

# --------------------------------------------------------------------------
# HANDBALL — Spanish Liga ASOBAL (verified table + calendar)
# --------------------------------------------------------------------------
ES = "SRC-ASOBAL-TABLE"
ES_URL = "https://asobal.es/liga/clasificacion/"
ES_CAL = "https://asobal.es/liga/calendario/"

ES_TEAMS = {
    "Fraikin BM. Granollers": dict(gp=5, w=4, d=0, l=1, gf=170, ga=152, pts=8),
    "REBI Balonmano Cuenca": dict(gp=5, w=1, d=1, l=3, gf=160, ga=164, pts=3),
    "Barça": dict(gp=5, w=5, d=0, l=0, gf=210, ga=151, pts=10),
    "RECOLETAS SALUD AT. VALLADOLID": dict(gp=6, w=6, d=0, l=0, gf=202, ga=168, pts=12),
}


def es(mid, date, time, home, away, comp, facts, venue=""):
    add(H, id=mid, sport="Handball", competition=comp,
        date=date, time=time, tnote="Spanish local clock time as printed by ASOBAL (CET); not converted",
        home=home, away=away, venue=venue, src=ES, url=ES_CAL, model="handball",
        hs=dict(ES_TEAMS[home]), as_=dict(ES_TEAMS[away]), facts=facts, note="")


es("Z-050", "2026-10-22", "20:00", "Fraikin BM. Granollers", "REBI Balonmano Cuenca",
   "37ª Liga NEXUS ENERGIA ASOBAL, Jornada 4 (rearranged)",
   ["Granollers: 4W-0D-1L for 8 points, goals 170:152 (+18) in 5 games",
    "Cuenca: 1W-1D-3L for 3 points, goals 160:164 (-4) in 5 games",
    "ASOBAL lists the throw-off at 20:00 on 22 October 2026 at the Palau d'Esports de Granollers"],
   venue="Palau d'Esports de Granollers")
es("Z-051", "2026-10-24", "18:00", "Barça", "REBI Balonmano Cuenca",
   "37ª Liga NEXUS ENERGIA ASOBAL, Jornada 7",
   ["Barça: 5W-0D-0L for 10 points, goals 210:151 (+59) in 5 games",
    "Cuenca: 1W-1D-3L for 3 points, goals 160:164 (-4) in 5 games"], venue="")

# --------------------------------------------------------------------------
# HANDBALL — Swedish Handbollsligan (verified table + schedule)
# --------------------------------------------------------------------------
SE = "SRC-HBL-SE"
SE_URL = "https://handbollsligan.se/herr/tabell/"
SE_SCHED = "https://handbollsligan.se/herr/"

SE_TEAMS = {
    "IK Sävehof": dict(gp=4, w=4, d=0, l=0, gf=135, ga=105),
    "Hammarby IF HF": dict(gp=6, w=4, d=0, l=2, gf=174, ga=166),
    "IFK Kristianstad": dict(gp=5, w=4, d=0, l=1, gf=148, ga=144),
    "HK Malmö": dict(gp=6, w=4, d=0, l=2, gf=185, ga=182),
    "Amo HK": dict(gp=6, w=3, d=1, l=2, gf=191, ga=182),
    "Ystads IF HF": dict(gp=4, w=3, d=0, l=1, gf=125, ga=112),
    "Alingsås HK": dict(gp=6, w=3, d=0, l=3, gf=183, ga=176),
    "IFK Skövde HK": dict(gp=5, w=2, d=2, l=1, gf=154, ga=159),
    "OV Helsingborg HK": dict(gp=5, w=1, d=2, l=2, gf=139, ga=145),
    "Lugi HF": dict(gp=6, w=2, d=0, l=4, gf=184, ga=192),
    "HF Karlskrona": dict(gp=5, w=2, d=0, l=3, gf=156, ga=164),
    "Önnereds HK": dict(gp=5, w=0, d=2, l=3, gf=140, ga=152),
    "Skånela IF": dict(gp=5, w=1, d=0, l=4, gf=142, ga=155),
    "IF Hallby HK": dict(gp=6, w=0, d=1, l=5, gf=166, ga=188),
}


def se(mid, date, time, home, away, facts, venue=""):
    add(H, id=mid, sport="Handball", competition="Handbollsligan 2026/27 (Sweden)",
        date=date, time=time, tnote="Swedish local clock time as printed by Handbollsligan (CET/CEST); not converted",
        home=home, away=away, venue=venue, src=SE, url=SE_SCHED, model="handball",
        hs=dict(SE_TEAMS[home]), as_=dict(SE_TEAMS[away]), facts=facts, note="")


se("Z-060", "2026-10-22", "18:30", "Skånela IF", "HF Karlskrona",
   ["Skånela: 1W-0D-4L, goals 142:155 (-13) in 5 games",
    "Karlskrona: 2W-0D-3L, goals 156:164 (-8) in 5 games"], venue="")
se("Z-061", "2026-10-22", "19:00", "Önnereds HK", "Ystads IF HF",
   ["Önnereds: 0W-2D-3L, goals 140:152 (-12) in 5 games",
    "Ystads: 3W-0D-1L, goals 125:112 (+13) in 4 games"], venue="")
se("Z-062", "2026-10-25", "16:00", "HF Karlskrona", "IFK Kristianstad",
   ["Karlskrona: 2W-0D-3L, goals 156:164 (-8) in 5 games",
    "Kristianstad: 4W-0D-1L, goals 148:144 (+4) in 5 games"], venue="")
se("Z-063", "2026-10-25", "16:30", "Skånela IF", "IK Sävehof",
   ["Skånela: 1W-0D-4L, goals 142:155 (-13) in 5 games",
    "Sävehof: 4W-0D-0L, goals 135:105 (+30) in 4 games",
    "Sävehof won 36:27 at IF Hallby on 21 October 2026"], venue="")
