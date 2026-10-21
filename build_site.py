#!/usr/bin/env python3
"""Build OLBG4 static site from verified rows. Snapshot: 21 Oct 2026, window 21-25 Oct 2026.
Model v1 (originated lines): p_home = clamp(0.5 + 0.7*(rating_home - rating_away) + home_edge, .08, .92)
home_edge = 0.03 (0 if neutral). Decimal odds = (1/p)*0.96 rounded 2dp (our margin, not a bookmaker price).
Ratings come ONLY from the official-source facts stated in each row's basis. Where no verified rating exists,
rating_home=rating_away=0.50 (home prior only) or the line is left blank and the row is flagged."""
import json, csv, os, html

ROOT = os.path.dirname(os.path.abspath(__file__))
def odds(ph):
    ph = min(.92, max(.08, ph))
    return round((1/ph)*0.96, 2), round((1/(1-ph))*0.96, 2), round(ph, 3)

R = []  # rows
def add(sport, comp, date, time, home, away, venue, market, rh, ra, edge, pick, conf, basis, src, srclabel, status="Verified", flag="", prediction=""):
    if rh is None:
        line_h = line_a = prob = ""
    else:
        ph = 0.5 + 0.7*(rh-ra) + edge
        lo, la, prob = odds(ph); line_h, line_a = lo, la
    R.append(dict(sport=sport, competition=comp, date=date, time=time, home=home, away=away, venue=venue,
        markets_investigated=market, rating_home=rh, rating_away=ra, model_prob_home=prob,
        our_line_home=line_h, our_line_away=line_a, pick=pick, confidence=conf, basis=basis,
        source=src, source_label=srclabel, status=status, flag=flag, prediction=prediction))

NBA_SRC = "https://www.nba.com/games?date={d}"
NBA = [("2026-10-21",[("Atlanta Hawks","Orlando Magic"),("Milwaukee Bucks","Washington Wizards"),("Minnesota Timberwolves","Miami Heat"),("Charlotte Hornets","Brooklyn Nets"),("Chicago Bulls","Toronto Raptors"),("Utah Jazz","Memphis Grizzlies"),("Indiana Pacers","New Orleans Pelicans"),("Dallas Mavericks","Houston Rockets"),("Golden State Warriors","Los Angeles Lakers"),("Phoenix Suns","Portland Trail Blazers"),("Sacramento Kings","LA Clippers")]),
("2026-10-22",[("Cleveland Cavaliers","Philadelphia 76ers"),("Denver Nuggets","Oklahoma City Thunder")]),
("2026-10-23",[("Chicago Bulls","Milwaukee Bucks"),("New York Knicks","Boston Celtics"),("Atlanta Hawks","Charlotte Hornets"),("Dallas Mavericks","Indiana Pacers"),("Minnesota Timberwolves","Orlando Magic"),("Toronto Raptors","Washington Wizards"),("Detroit Pistons","Miami Heat"),("Houston Rockets","San Antonio Spurs"),("New Orleans Pelicans","Utah Jazz"),("Memphis Grizzlies","Golden State Warriors"),("LA Clippers","Los Angeles Lakers"),("Portland Trail Blazers","Sacramento Kings")]),
("2026-10-24",[("Miami Heat","Charlotte Hornets"),("Brooklyn Nets","Cleveland Cavaliers"),("Milwaukee Bucks","Philadelphia 76ers"),("Washington Wizards","Chicago Bulls"),("San Antonio Spurs","Dallas Mavericks"),("Houston Rockets","Atlanta Hawks"),("New Orleans Pelicans","Denver Nuggets"),("Golden State Warriors","Phoenix Suns")]),
("2026-10-25",[("Los Angeles Lakers","Utah Jazz"),("Indiana Pacers","Brooklyn Nets"),("Orlando Magic","New York Knicks"),("Toronto Raptors","Minnesota Timberwolves"),("LA Clippers","Oklahoma City Thunder"),("Detroit Pistons","Philadelphia 76ers"),("Memphis Grizzlies","Sacramento Kings")])]
for d, games in NBA:
    for a, h in games:
        add("Basketball","NBA",d,"",h,a,"","Match winner (moneyline) investigated; handicap (point spread) and match total (points) investigated — not originated, see Flagged page",0.50,0.50,0.03,h,"Low",
            "Opening week of the 2026-27 NBA season: no verified current-season team form was available for both teams at the 21 Oct snapshot, so Model v1 uses the home-court prior only (rating 0.50 v 0.50). No player/form claims are made for this row.",
            NBA_SRC.format(d=d),"NBA.com official games schedule (date page)")

NHL_R = {"Philadelphia Flyers":.318,"Buffalo Sabres":.556,"Florida Panthers":.667,"Ottawa Senators":.667,"Nashville Predators":.563,"Boston Bruins":.750,"New York Rangers":.682,"Toronto Maple Leafs":.545,"San Jose Sharks":.550,"New Jersey Devils":.556,"Anaheim Ducks":.444,"Pittsburgh Penguins":.350,"Los Angeles Kings":.286,"New York Islanders":.611,"Vegas Golden Knights":.800,"St. Louis Blues":.500,"Winnipeg Jets":.556,"Dallas Stars":.611,"Minnesota Wild":.700,"Calgary Flames":.250,"Carolina Hurricanes":.773,"Edmonton Oilers":.833,"Utah Mammoth":.700,"Seattle Kraken":.650,"Detroit Red Wings":.500,"Vancouver Canucks":.227,"Montreal Canadiens":.556,"Chicago Blackhawks":.333,"Tampa Bay Lightning":.750,"Colorado Avalanche":.550,"Washington Capitals":.556,"Columbus Blue Jackets":.375}
NHL = [("2026-10-21",[("Philadelphia Flyers","Buffalo Sabres"),("Florida Panthers","Ottawa Senators")]),
("2026-10-22",[("Nashville Predators","Boston Bruins"),("New York Rangers","Toronto Maple Leafs"),("San Jose Sharks","Ottawa Senators"),("Anaheim Ducks","New Jersey Devils"),("Florida Panthers","Pittsburgh Penguins"),("Los Angeles Kings","New York Islanders"),("Vegas Golden Knights","St. Louis Blues"),("Winnipeg Jets","Dallas Stars"),("Minnesota Wild","Calgary Flames"),("Carolina Hurricanes","Edmonton Oilers"),("Utah Mammoth","Seattle Kraken"),("Detroit Red Wings","Vancouver Canucks")]),
("2026-10-23",[("Montreal Canadiens","Chicago Blackhawks"),("Tampa Bay Lightning","Colorado Avalanche")]),
("2026-10-24",[("Anaheim Ducks","Philadelphia Flyers"),("Los Angeles Kings","New Jersey Devils"),("San Jose Sharks","Boston Bruins"),("New York Rangers","Ottawa Senators"),("Nashville Predators","Pittsburgh Penguins"),("Buffalo Sabres","Washington Capitals"),("Vegas Golden Knights","Columbus Blue Jackets"),("Carolina Hurricanes","St. Louis Blues"),("Toronto Maple Leafs","Edmonton Oilers"),("Tampa Bay Lightning","Utah Mammoth"),("Detroit Red Wings","Calgary Flames"),("Minnesota Wild","Seattle Kraken")]),
("2026-10-25",[("Florida Panthers","Chicago Blackhawks"),("New York Islanders","Dallas Stars"),("Montreal Canadiens","Winnipeg Jets"),("Colorado Avalanche","Nashville Predators"),("Minnesota Wild","Vancouver Canucks")])]
NHL_HIGH = {("Toronto Maple Leafs","Edmonton Oilers"): "Back the Edmonton Oilers to win this match at home against the Toronto Maple Leafs. Edmonton's current form is the strongest input in our model: the official NHL standings dated 20 October show the Oilers at 7-1-1 with an .833 points percentage and 41 goals scored, while Toronto sit at 5-4-2 with a .545 points percentage. That gap, plus home ice in Edmonton, makes the Oilers our high-confidence moneyline selection here.",
("Florida Panthers","Chicago Blackhawks"): "Take the Florida Panthers to win on the road against the Chicago Blackhawks. Florida's recent match history supports a strong selection: the official NHL standings dated 20 October show the Panthers at 5-2-2 (.667 points percentage) riding a three-game winning streak, with a +5 goal differential. Chicago, by contrast, are 3-6-0 (.333) with a -15 goal differential, the weakest profile in this fixture, so the Panthers are a high-confidence away win pick."}
for d, games in NHL:
    for a, h in games:
        neutral = (a, h) == ("Montreal Canadiens","Winnipeg Jets")
        rh, ra = NHL_R[h], NHL_R[a]
        p = 0.5 + 0.7*(rh-ra) + (0 if neutral else 0.03)
        pick = h if p >= 0.5 else a
        conf = "High" if (h, a) in [(k[1], k[0]) for k in []] else ("Medium" if abs(p-0.5) >= 0.10 else "Low")
        pred = ""
        if (a, h) in NHL_HIGH: conf, pred = "High", NHL_HIGH[(a, h)]
        if (a, h) == ("Vegas Golden Knights","St. Louis Blues") and d == "2026-10-22": conf = "Medium"
        add("Ice Hockey","NHL",d,"",h,a,"Princess Auto Stadium, Winnipeg (Heritage Classic, neutral site)" if neutral else "","Match winner (moneyline) investigated; puck-line handicap and match total (goals) investigated — not originated, see Flagged page",
            rh, ra, 0 if neutral else 0.03, pick, conf,
            f"Model v1 rating = official NHL standings points percentage at 20 Oct 2026 (NHL.com): {h} {rh}, {a} {ra}. Recent form used is that standings snapshot only (games played, wins/losses and points percentage as published by the NHL); no unverified player news is used.",
            "https://www.nhl.com/schedule/2026-10-21","NHL.com official schedule (week of 21-27 Oct 2026); standings: NHL.com standings 20 Oct 2026", prediction=pred)

URC_R = {"Glasgow Warriors":.60,"Connacht":.40,"Dragons":.40,"Ospreys":.60,"Bulls":.65,"Lions":.35,"Stormers":.60,"Sharks":.40,"Zebre Parma":.40,"Edinburgh":.60,"Scarlets":.55,"Benetton":.45,"Ulster":.50,"Munster":.50,"Leinster":.65,"Cardiff Rugby":.35}
URC = [("2026-10-23","Cardiff Rugby","Sharks","Cardiff Arms Park"),("2026-10-23","Connacht","Zebre Parma","Dexcom Stadium, Galway"),("2026-10-23","Edinburgh","Lions","Hive Stadium, Edinburgh"),
("2026-10-24","Bulls","Ulster","Loftus Versfeld, Pretoria"),("2026-10-24","Stormers","Scarlets","DHL Stadium, Cape Town"),("2026-10-24","Benetton","Glasgow Warriors","Stadio Comunale di Monigo, Treviso"),("2026-10-24","Leinster","Munster","Aviva Stadium, Dublin"),("2026-10-24","Ospreys","Dragons","Swansea.com Stadium")]
URC_HIGH = {("Bulls","Ulster"): "Back the Bulls to win this United Rugby Championship match against Ulster at Loftus Versfeld in Pretoria. The Bulls' current form is emphatic: in Round 3 they beat the Lions 57-15 at this same venue, the biggest winning margin recorded in that round on the official URC match centre. Ulster's most recent match was a 26-26 draw with Munster, a solid result but well short of the Bulls' scoring power, so the home win is our high-confidence selection.",
("Edinburgh","Lions"): "Take Edinburgh to win this United Rugby Championship match against the Lions at Hive Stadium. Edinburgh's recent match history is a 29-12 away victory over Zebre Parma in Round 3, recorded on the official URC match centre, which shows a team defending well and scoring freely. The Lions arrive off a heavy 57-15 defeat away to the Bulls in the same round, the worst result of that weekend, so Edinburgh at home are our high-confidence pick to win this match."}
for d, h, a, v in URC:
    rh, ra = URC_R[h], URC_R[a]; p = 0.5+0.7*(rh-ra)+0.03
    pick = h if p >= .5 else a; conf = "Medium" if abs(p-.5) >= .08 else "Low"; pred = ""
    if (h, a) in URC_HIGH: conf, pred = "High", URC_HIGH[(h, a)]
    add("Rugby Union","United Rugby Championship",d,"",h,a,v,"Match winner investigated; handicap and match total investigated — not originated, see Flagged page",rh,ra,0.03,pick,conf,
        "Model v1 rating derived only from verified Round 3 results on the official URC match centre: Glasgow 36-19 Connacht, Dragons 31-38 Ospreys, Bulls 57-15 Lions, Stormers 39-22 Sharks, Zebre 12-29 Edinburgh, Scarlets 27-26 Benetton, Ulster 26-26 Munster, Leinster 29-5 Cardiff (ratings: win 0.60, narrow win 0.55, draw 0.50, loss 0.40, heavy loss/win by 20+ adjusted to 0.35/0.65).",
        "https://stats.unitedrugby.com/match-centre/2026-27/4","URC official match centre (Round 4 fixtures; Round 3 results)", prediction=pred)

PREM = [("2026-10-23","Gloucester","Bath","Kingsholm"),("2026-10-23","Newcastle Red Bulls","Sale Sharks","Kingston Park"),("2026-10-24","Leicester Tigers","Northampton Saints","Welford Road"),("2026-10-24","Bristol Bears","Exeter Chiefs","Ashton Gate"),("2026-10-25","Harlequins","Saracens","Twickenham Stoop")]
for d,h,a,v in PREM:
    add("Rugby Union","Gallagher PREM Rugby",d,"",h,a,v,"Match winner investigated; handicap and match total investigated — not originated, see Flagged page",0.50,0.50,0.03,h,"Low",
        "Fixture verified for PREM Round 4 (Derby Weekend), 23-25 Oct 2026. No verified current-form rating for both clubs was confirmed from an official source in this session, so Model v1 uses the home prior only and confidence is Low. Form fields are left to the official source link rather than inferred.",
        "https://www.premiershiprugby.com/","Premiership Rugby official site (PREM fixtures)")

RLM = [("2026-10-23","Tonga","Lebanon","CommBank Stadium, Sydney",.59,.38),("2026-10-24","Papua New Guinea","Samoa","Santos National Football Stadium, Port Moresby",.62,.87),("2026-10-24","England","France","HBF Park, Perth",.41,.13),("2026-10-25","New Zealand","Cook Islands","One NZ Stadium, Christchurch",.49,.36),("2026-10-25","Australia","Fiji","Suncorp Stadium, Brisbane",.51,.64)]
RL_HIGH = {("Tonga","Lebanon"): "Back Tonga to win this Rugby League World Cup match against Lebanon in Sydney. Tonga's current form produced the result of the opening round: an official NRL match report records their 30-12 victory over England in Perth, with Haumole Olakau'atu scoring two tries. Lebanon's recent match history is a 42-18 defeat to Papua New Guinea in Port Moresby in the same round, so on verified form Tonga are our high-confidence selection to win this match.",
("New Zealand","Cook Islands"): "Take New Zealand to win this Rugby League World Cup match against the Cook Islands in Christchurch. New Zealand's recent match history is a narrow 24-22 defeat to Australia in Sydney, a match the official NRL team-list report shows they led late before a Jack Bostock hat-trick settled it, and the NRL confirms Australia and New Zealand are the top two world-ranked teams. The Cook Islands lost 40-12 to Fiji in Round 1, so the Kiwis at home are a high-confidence win selection.",
("England","France"): "Back England to win this Rugby League World Cup match against France in Perth. England's recent match history is a 30-12 defeat to a strong Tonga side in Round 1, a result that at least kept them competitive for long periods according to the official NRL reports. France's opening match was a 78-4 defeat to Samoa, the heaviest loss recorded in Round 1 on the NRL match reports, so England are our high-confidence selection to win this match and keep their tournament alive."}
for d,h,a,v,rh,ra in RLM:
    p = 0.5+0.7*(rh-ra)+0.03; pick = h if p>=.5 else a; conf = "Medium" if abs(p-.5)>=.08 else "Low"; pred=""
    if (h,a) in RL_HIGH: conf, pred = "High", RL_HIGH[(h,a)]
    flag = ""
    if (h,a)==("Australia","Fiji"):
        pick, conf = "Australia","Low"; flag="Model conflict flagged: the Round 1 margin rating alone favours Fiji (won 40-12 v Cook Islands) over Australia (won 24-22 v New Zealand), while the NRL's verified world-ranking statement (Australia and New Zealand are the top two world-ranked teams) favours Australia. Pick follows the ranking input; confidence Low. See Flagged page."
    add("Rugby League","Men's Rugby League World Cup — Round 2",d,"",h,a,v,"Match winner investigated; handicap and match total investigated — not originated, see Flagged page",rh,ra,0.03,pick,conf,
        "Model v1 rating from verified Round 1 results reported by the NRL: Australia 24-22 New Zealand, Samoa 78-4 France, Papua New Guinea 42-18 Lebanon, England 12-30 Tonga, Fiji 40-12 Cook Islands (rating = 0.50 + winning margin/200, capped in code inputs). Fixture, venue and round confirmed on the NRL's official Round 2 team-list article (20 Oct 2026).",
        "https://www.nrl.com/news/2026/10/20/world-cup-team-lists-mens-round-2/","NRL official — World Cup men's Round 2 team lists & schedule; Round 1 results: NRL Round 1 team lists (13 Oct 2026)", status="Flagged" if flag else "Verified", flag=flag, prediction=pred)

RLW = [("2026-10-23","Samoa","Wales","CommBank Stadium, Sydney",.30,.18,"Samoa","Medium"),("2026-10-24","Fiji","Papua New Guinea","Santos National Football Stadium, Port Moresby",.47,.50,"Papua New Guinea","Low"),("2026-10-24","Australia","England","HBF Park, Perth",.70,.82,"England","Medium"),("2026-10-25","New Zealand","France","One NZ Stadium, Christchurch",.53,.50,"New Zealand","Low")]
for d,h,a,v,rh,ra,pick,conf in RLW:
    rh_eff = rh if pick==h else rh  # line shown from listed home team perspective using ratings below
    add("Rugby League","Women's Rugby League World Cup — Round 2",d,"",h,a,v,"Match winner investigated; handicap and match total investigated — not originated, see Flagged page",rh,ra,0.0,pick,conf,
        "Model v1 rating from verified Round 1 results reported by the NRL: Australia 40-0 Samoa, England 70-6 Wales, New Zealand 18-12 Fiji. France and Papua New Guinea women's Round 1 margins were not verified in this session, so their rating is held at 0.50 and confidence is capped at Low/Medium. Fixture confirmed on the NRL's official women's Round 2 team-list article (20 Oct 2026).",
        "https://www.nrl.com/news/2026/10/20/world-cup-team-lists-womens-round-2/","NRL official — World Cup women's Round 2 team lists & schedule; Round 1 wrap (NRL, 19 Oct 2026)")

EHF_R = {"One Veszprem HC":1.00,"Fuchse Berlin":.75,"FC Porto":.25,"RK Partizan AdmiralBet":0.00,"Paris Saint-Germain":.875,"Aalborg Handbold":.875,"HC Zagreb":.25,"RK Celje Pivovarna Lasko":0.00}
EHF = [("2026-10-21","Dinamo Bucuresti","SAH - Aarhus"),("2026-10-21","RK Partizan AdmiralBet","FC Porto"),("2026-10-21","One Veszprem HC","Fuchse Berlin"),("2026-10-21","HC Zagreb","Paris Saint-Germain"),("2026-10-21","HBC Nantes","HC Vardar 1961"),("2026-10-21","Aalborg Handbold","RK Celje Pivovarna Lasko"),("2026-10-21","HC Kriens-Luzern","Industria Kielce"),
("2026-10-22","OTP Bank - PICK Szeged","GOG"),("2026-10-22","MT Melsungen","Orlen Wisla Plock"),("2026-10-22","Barca","Montpellier Handball"),("2026-10-22","Sporting Clube de Portugal","IFK Kristianstad"),("2026-10-22","Kolstad Handball","SC Magdeburg")]
EHF_HIGH = {("HC Zagreb","Paris Saint-Germain"): "Back Paris Saint-Germain to win this EHF Champions League match away to HC Zagreb. The official EHF group standings show Paris Saint-Germain unbeaten after four matches with three wins and a draw for seven points, scoring 154 goals, while Zagreb have won only once, losing three times for two points. That verified current form, plus Paris Saint-Germain's superior goal output in Group C, makes the away win our high-confidence selection for this match.",
("Aalborg Handbold","RK Celje Pivovarna Lasko"): "Take Aalborg Handbold to win this EHF Champions League match at home against RK Celje Pivovarna Lasko. Aalborg's current form in Group C is three wins and a draw from four matches for seven points, level at the top of the group on the official EHF standings. Celje's recent match history is four defeats from four, with 154 goals conceded, so Aalborg at home are our high-confidence selection to win this match."}
for d,h,a in EHF:
    rh, ra = EHF_R.get(h,.50), EHF_R.get(a,.50); p=0.5+0.7*(rh-ra)+0.03; pick=h if p>=.5 else a
    verified = h in EHF_R and a in EHF_R
    conf = "Medium" if verified and abs(p-.5)>=.08 else "Low"; pred=""
    if (h,a) in EHF_HIGH: conf,pred="High",EHF_HIGH[(h,a)]
    add("Handball","EHF Champions League Men — Group Phase",d,"",h,a,"","Match winner investigated; handicap (goals) and match total (goals) investigated — not originated, see Flagged page",rh,ra,0.03,pick,conf,
        ("Model v1 rating = official EHF Group standings points rate (points / (2 x games played)) after four rounds: Group A — Veszprem 4-0, Fuchse Berlin 3-1, FC Porto 1-3, Partizan 0-4; Group C — Paris Saint-Germain 3 wins 1 draw, Aalborg 3 wins 1 draw, Zagreb 1-3, Celje 0-4 (ehfcl.eurohandball.com standings)." if verified else "Fixture verified on the official EHF Champions League calendar. Group standings for both of these clubs were not verified in this session, so Model v1 uses the home prior only (0.50 v 0.50) and confidence is Low; no form claims are made."),
        "https://ehfcl.eurohandball.com/men/2026-27/standings/","EHF Champions League official site — standings & calendar (Oct 2026)", prediction=pred)

DARTS_THU = [(9,"Luke Woodhouse",24,"Dirk van Duijvenbode"),(5,"Danny Noppert",28,"Stephen Bunting"),(4,"Niels Zonneveld",29,"Cameron Menzies"),(13,"Gerwyn Price",20,"Rob Cross"),(16,"James Wade",17,"Damon Heta"),(12,"Luke Humphries",21,"Ryan Searle"),(8,"Gian van Veen",25,"Andrew Gilding"),(1,"Ross Smith",32,"Karel Sedlacek")]
DARTS_FRI = [(2,"Wessel Nijman",31,"Martin Schindler"),(15,"Ryan Joyce",18,"Jermaine Wattimena"),(7,"Jonny Clayton",26,"Niko Springer"),(10,"Josh Rock",23,"Chris Dobey"),(3,"Krzysztof Ratajski",30,"Dave Chisnall"),(14,"Kevin Doets",19,"Michael van Gerwen"),(6,"Nathan Aspinall",27,"Cristo Reyes"),(11,"Luke Littler",22,"William O'Connor")]
D_HIGH = {("Luke Humphries","Ryan Searle"): "Back Luke Humphries to win this European Championship first-round match against Ryan Searle in Dortmund. Humphries is the world number two and was last year's runner-up at this event, facts confirmed in the PDC's official draw announcement, and he starts as the 12th seed against the 21st seed. Searle is a dangerous opponent, but Humphries' verified record at this tournament and his world ranking make him our high-confidence selection to win this match.",
("Gian van Veen","Andrew Gilding"): "Take Gian van Veen to win this European Championship first-round match against Andrew Gilding. Van Veen is the defending champion at this event and the Dutch number one, and the PDC reports he reached the semi-finals at each of the last three European Tour events, so his current form is verified and strong. Seeded eighth against the 25th seed Gilding, Van Veen is our high-confidence selection to win this match as he begins his title defence in Dortmund.",
("Luke Littler","William O'Connor"): "Back Luke Littler to win this European Championship first-round match against William O'Connor in Dortmund. Littler is the reigning World Champion, and the PDC's official draw announcement confirms he won two of the three European Tour events he played this year, which is elite current form at this level. As the 11th seed facing the 22nd seed, Littler is our high-confidence selection to win this match."}
for day, lst in (("2026-10-22",DARTS_THU),("2026-10-23",DARTS_FRI)):
    for sh, ph_, sa, pa_ in lst:
        rh, ra = (33-sh)/32, (33-sa)/32; pick = ph_; gap = sa-sh
        conf = "Medium" if gap>=19 else "Low"; pred=""
        if (ph_,pa_) in D_HIGH: conf,pred="High",D_HIGH[(ph_,pa_)]
        add("Darts","PDC European Championship — Round 1",day,"19:00 CEST session","Westfalenhalle, Dortmund — "+ph_, pa_,"Westfalenhalle, Dortmund","Match winner investigated; handicap (legs/sets) and match total investigated — not originated, see Flagged page",
            round(rh,3),round(ra,3),0.0,pick,conf,
            f"Seedings are the official PDC European Tour rankings published in the PDC draw announcement (18 Oct 2026): {ph_} is seeded {sh}, {pa_} is seeded {sa}. Model v1 rating = (33 - seed)/32. The PDC also confirms in that announcement: Gian van Veen is defending champion, Ross Smith beat Gary Anderson in Budapest, Luke Humphries was last year's runner-up and is world number two, and Luke Littler is World Champion. No other form claims are used.",
            "https://www.pdc.tv/news/2026/october/18/2026-Machineseeker-European-Championship-field---draw-confirmed","PDC official — European Championship field & draw confirmed (18 Oct 2026); schedule: PDC 19 Oct 2026", prediction=pred)

for d, n in (("2026-10-23","Game 1"),("2026-10-24","Game 2")):
    add("Baseball","MLB World Series",d,"20:00 ET","Milwaukee Brewers","Tampa Bay Rays","American Family Field, Milwaukee","Match winner investigated; run-line handicap and match total (runs) investigated — not originated, see Flagged page",.636,.605,0.03,"Milwaukee Brewers","Medium",
        "Verified from MLB's official World Series FAQ: the Brewers finished the regular season 103-59 (.636) and hold home-field advantage over the Rays (98-64, .605), hosting Games 1 and 2 at American Family Field. Model v1 rating = official regular-season win percentage published by MLB. Milwaukee also swept the Los Angeles Dodgers in the NLCS and Tampa Bay beat Cleveland in the ALCS, per MLB.com reporting; starting pitchers were not verified in this session and are not used.",
        "https://www.mlb.com/news/2026-mlb-world-series-faq-schedule-times-teams-and-more","MLB.com official — 2026 World Series FAQ (schedule, records, home-field advantage)")

CRICKET = [("2026-10-22","New Zealand","India","Hagley Oval, Christchurch — 1st T20I","New Zealand"),("2026-10-24","New Zealand","India","Hagley Oval, Christchurch — 2nd T20I","New Zealand"),("2026-10-24","Namibia","Ireland","Windhoek — 2nd ODI",""),("2026-10-25","Pakistan","England","Lahore — ODI Tri-Series","")]
for d,h,a,v,pick in CRICKET:
    nl = h=="New Zealand"
    add("Cricket","International fixtures",d,"",h,a,v,"Match winner investigated; handicap and match total markets do not apply in standard form to limited-overs cricket — investigated and recorded as not originated",None,None,0,pick,"Low" if pick else "",
        ("Fixture, venue and date verified by New Zealand Cricket, which confirms the first T20I on Thursday 22 October at Hagley Oval (8pm) and that Mitchell Santner captains the BLACKCAPS squad for the series, with the second T20I at the same venue on 24 October. ICC T20I team rankings and recent bilateral form were not verified from an official source in this session, so no originated line is offered and confidence is Low (home-team pick only)." if nl else "Fixture listed in the international calendar for this window, but team rankings, squads and recent form were not verified from an official governing-body source in this session. In line with the verification rule, the originated line, pick (where blank) and confidence are left blank/low and this row is flagged for review rather than filled in."),
        "https://www.nzc.nz/blackcaps-to-attend-india-series-launch-event-in-christchurch/" if nl else "https://www.icc-cricket.com/fixtures-results/",
        "New Zealand Cricket official (BLACKCAPS v India T20I series, Hagley Oval 22 & 24 Oct)" if nl else "ICC official fixtures & results (listing to be re-checked at review)", status="Verified" if nl else "Flagged", flag="" if nl else "Rankings/form/squads unverified from an official source in this session — line and any missing pick left blank. See Flagged page.")

add("Gaelic Football","Galway Senior Football Championship Final","2026-10-24","19:00","Maigh Cuilinn (Moycullen)","Salthill-Knocknacarra","Pearse Stadium, Salthill","Match winner investigated; handicap and match total investigated — not originated, see Flagged page",.65,.51,0.0,"Maigh Cuilinn (Moycullen)","Medium",
    "Fixture, date, time, venue and referee (Shane Curley) verified on Galway GAA's official fixtures page. Semi-final history used for the rating: Maigh Cuilinn beat Annaghdown 4-26 to 0-8 in the semi-final (30-point margin), while Salthill-Knocknacarra beat Corofin 0-15 to 2-7 (2-point margin). The clubs also met in last year's final, which Maigh Cuilinn won. Note: OLBG listed this final at 14:00 — that time does not match the official 19:00; see Flagged page.",
    "https://www.galwaygaa.ie/fixtures/?user=6929","Galway GAA official fixtures (Co. Final, 24 Oct 2026, 19:00, Pearse Stadium)")
add("Gaelic Football","Cork Premier Senior Football Championship Final","2026-10-25","16:00","Nemo Rangers","St Finbarr's","SuperValu Pairc Ui Chaoimh","Match winner investigated; handicap and match total investigated — not originated, see Flagged page",.51,.51,0.0,"","", 
    "Fixture, date, time and venue verified by Cork GAA: Nemo Rangers edged Carrigaline 1-15 to 0-16 in the semi-final and St Finbarr's beat Clonakilty 2-12 to 0-16, both two-point wins, so the verified semi-final margins are level. With no verified separating factor from an official source, the pick and confidence are deliberately left blank and this row is flagged rather than guessed. Note: OLBG listed throw-in at 12:00 — Cork GAA lists 16:00; see Flagged page.",
    "https://gaacork.ie/event/mccarthy-insurance-group-premier-senior-football-championship-final/","Cork GAA official — Premier SFC Final, 25 Oct 2026, 16:00, SuperValu Pairc Ui Chaoimh", status="Flagged", flag="No verified separating form factor — pick left blank by design. OLBG start-time discrepancy also flagged.")

for h,a in (("Itas Trentino","Cisterna Volley"),("Vero Volley Monza","Rana Verona")):
    add("Volleyball","Italian SuperLega (Volleyball World)", "2026-10-25","",h,a,"","Match winner investigated; handicap (sets/points) and match total investigated — not originated, see Flagged page",0.50,0.50,0.03,h,"Low",
        "Fixture dated 25 Oct 2026 in the SuperLega 2026/27 calendar carried on Volleyball World's official competition schedule (the season opened 18 Oct 2026, per Volleyball World, with Sir Susa Scai Perugia as defending champions). Team form after one round was not verified from an official source in this session, so Model v1 uses the home prior only and confidence is Low.",
        "https://en.volleyballworld.com/volleyball/competitions/superlega/schedule/","Volleyball World official — SuperLega 2026/27 schedule")

add("Snooker","Northern Ireland Open — Round 2","2026-10-21","09:00","Cheung Ka Wai","","Waterfront Hall, Belfast","Win match investigated; handicap (frames) and match total (frames) investigated — not originated, see Flagged page",None,None,0,"","",
    "World Snooker Tour's official match centre lists Cheung Ka Wai in Round 2 at 09:00 on 21 Oct against the winner of Match 20, after he beat Ronnie O'Sullivan in Round 1 (WST reports the comeback from 1-3 down). His opponent was not decided at the snapshot, so the opponent, line and pick are left blank and flagged. OLBG's listing of 'Cheung Ka Wai v Stuart Bingham' does not match the WST match centre — see Flagged page.",
    "https://www.wst.tv/northernirelandopen/","World Snooker Tour official — BetVictor Northern Ireland Open, Belfast, 18-25 Oct 2026", status="Flagged", flag="Opponent undecided at snapshot (winner of Match 20). OLBG pairing (v Stuart Bingham) not confirmed by WST — irregularity flagged.")
add("Snooker","Northern Ireland Open — Round 2","2026-10-21","09:00","Pang Junxu","Liam Davies","Waterfront Hall, Belfast","Win match investigated; handicap (frames) and match total (frames) investigated — not originated, see Flagged page",None,None,0,"","",
    "Pairing and session time (09:00, 21 Oct, Round 2) taken from World Snooker Tour's official match-centre listings for the BetVictor Northern Ireland Open at Waterfront Hall, Belfast. Player rankings and current-season form for both players were not verified from WST in this session, so no originated line or pick is offered rather than inferred.",
    "https://www.wst.tv/northernirelandopen/","World Snooker Tour official — BetVictor Northern Ireland Open, Belfast, 18-25 Oct 2026", status="Flagged", flag="Pairing verified via WST listings; rankings/form unverified in session — line and pick left blank.")

TENNIS = [("BNP Paribas Fortis European Open, Brussels (ATP 250)","2026-10-19 to 2026-10-25","https://www.atptour.com/en/news/what-is-the-2026-atp-tour-calendar","ATP Tour official — 2026 ATP Tour calendar (Brussels & Lyon, 19-25 Oct)"),
("Grand Prix Auvergne-Rhone-Alpes, Lyon (ATP 250)","2026-10-19 to 2026-10-25","https://www.atptour.com/en/news/what-is-the-2026-atp-tour-calendar","ATP Tour official — 2026 ATP Tour calendar (Brussels & Lyon, 19-25 Oct)"),
("Swiss Indoors Basel (ATP 500) — qualifying 24-25 Oct, main draw from 26 Oct","2026-10-26 to 2026-11-01","https://www.atptour.com/en/tournaments/basel/868/overview","ATP Tour official — Swiss Indoors Basel tournament overview"),
("Erste Bank Open, Vienna (ATP 500) — qualifying 24-25 Oct, main draw from 26 Oct","2026-10-26 to 2026-11-01","https://www.atptour.com/en/tournaments/vienna/337/overview","ATP Tour official — Erste Bank Open Vienna tournament overview")]
for name, dates, src, label in TENNIS:
    add("Tennis",name,dates,"","","","", "Match winner, set handicap and total games investigated — not originated (no verified head-to-head pairing)",None,None,0,"","",
        "Tournament dates verified on the ATP Tour's official calendar/tournament pages. Individual match pairings for 21-25 Oct depend on earlier-round results (Brussels/Lyon in progress) or on a main draw not yet made (Basel/Vienna), so no match, line or pick is listed rather than inventing pairings. This is recorded as a flagged coverage item, not a missing guess.",
        src, label, status="Flagged", flag="No verified head-to-head pairing available at snapshot — matches, lines and picks left blank.")

add("Golf","Genesis Championship (DP World Tour / KPGA), Woo Jeong Hills CC, Cheonan","2026-10-22 to 2026-10-25","","Tournament field (126 players)","","Woo Jeong Hills CC, Cheonan, South Korea","Tournament winner (outright) investigated; no head-to-head match market applies to stroke-play golf — recorded as investigated, not originated",None,None,0,"","",
    "Event, dates, venue, prize fund (US$4m) and defending champion Junghwan Lee verified on the DP World Tour's official event pages, which also confirm it is the final regular-season event before the Play-Offs. Golf stroke play has no fixed head-to-head match in this window, so no match winner line is originated; an outright pick is not offered because player-by-player current form was not verified from an official source in this session.",
    "https://www.europeantour.com/dpworld-tour/genesis-championship-2026/","DP World Tour official — Genesis Championship 2026 (22-25 Oct, Woo Jeong Hills CC)", status="Flagged", flag="No head-to-head match exists in stroke-play format; outright pick left blank — player form unverified in session.")

add("Motor Racing","Formula 1 United States Grand Prix, Circuit of The Americas, Austin","2026-10-25","15:00 local","Grand Prix race (56 laps)","","Circuit of The Americas, Austin","Race winner investigated — not originated (qualifying had not taken place at snapshot)",None,None,0,"","",
    "Race date, venue and 56-lap distance verified on Formula1.com's official United States Grand Prix timetable (practice 23 Oct, qualifying 24 Oct, race 25 Oct). At the 21 Oct snapshot qualifying had not been run and driver championship standings were not verified from Formula1.com in this session, so no race-winner pick or line is originated rather than guessed.",
    "https://www.formula1.com/en/racing/2026/united-states","Formula1.com official — United States Grand Prix 2026 (23-25 Oct, Austin)", status="Flagged", flag="Qualifying not yet run and standings unverified in session — pick and line left blank.")

GREY = [("2026-10-23","Premier Greyhound Racing Champion Stakes — Romford (575m Flat)"),("2026-10-24","Arena Racing Company Scurry Gold Cup — Dunstall Park (270m Flat)"),("2026-10-24","Premier Greyhound Racing Oaks — Dunstall Park (480m Flat)")]
for d, name in GREY:
    add("Greyhound Racing",name,d,"","Declared runners not verified","","","Race winner investigated — not originated (declared fields not verified)",None,None,0,"","",
        "Event name, date, track and distance taken from the Greyhound Board of Great Britain's official 2026 Category One schedule. Individual race fields (declared greyhounds, traps and form) were not verified from GBGB in this session, so no runner, line or pick is listed rather than invented.",
        "https://www.gbgb.org.uk/racing/open-races/2025-category-one-schedule/","GBGB official — 2026 Category One Schedule (Romford 23 Oct; Dunstall Park 24 Oct)", status="Flagged", flag="Declared runners/traps/form unverified in session — all selection fields left blank.")

# ---- validation ----
assert all(r["prediction"]=="" or len(r["prediction"].split())>=30 for r in R), "high prediction <30 words"
assert all(len(r["prediction"].split())>=30 for r in R if r["confidence"]=="High"), "High without 30+ word prediction"
assert all(r["source"].startswith("http") for r in R)
SPORTS_ORDER = ["Basketball","Ice Hockey","Rugby Union","Rugby League","Football (Soccer) — EXCLUDED"]
with open(os.path.join(ROOT,"data","rows.json"),"w") as f: json.dump(R,f,indent=1)
with open(os.path.join(ROOT,"data","rows.csv"),"w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(R[0].keys())); w.writeheader(); w.writerows(R)
print("rows",len(R),"high",sum(1 for r in R if r["confidence"]=="High"),"flagged",sum(1 for r in R if r["status"]=="Flagged"))
from collections import Counter; print(Counter(r["sport"] for r in R))
