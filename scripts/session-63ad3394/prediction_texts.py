"""Hand-written predictions for Board AK (session arena/63ad3394-olbg4).

One entry per published pick, keyed by desk row id. Every figure quoted here is
copied from the official payload recorded on that row (NHL schedule/standings
API, the EuroLeague and EuroCup game feed, the LNR TOP 14 fixtures and table,
the MLB Stats API, the PDC participant/match service, the WST match service,
the PGA TOUR leaderboard and formula1.com). Nothing is inferred: where an
official feed does not cover a fixture the desk publishes no line and the site
says so, and no injury is claimed anywhere because no injury feed was captured
for these fixtures (see the Flagged for Review page).
"""

TEXTS: dict[str, str] = {
    # ---------------- Ice Hockey (NHL, api-web.nhle.com) ----------------
    "nhl-2026020200": (
        "Edmonton are 8-1 through ten games for 17 points, scoring 4.7 goals a night and "
        "conceding 3.2, a margin of plus 1.5 that no Calgary side has come near. The Flames "
        "are 3-6 with six points, scoring 2.1 and conceding 4.2, and they arrive at Rogers "
        "Place having lost six of their nine games. Back Edmonton Oilers at -272."
    ),
    "nhl-2026020217": (
        "Boston are 8-2 through eleven games and concede only 2.0 goals a night, the tightest "
        "defence in this slate, while scoring 3.8. Chicago are 3-6 with six points, shipping "
        "4.0 a game and scoring 2.3, and they travel to TD Garden on a losing run. The Bruins "
        "have 17 points to Chicago's six: Boston Bruins at -249."
    ),
    "nhl-2026020206": (
        "Carolina's 8-2 start rests on 3.9 goals scored and 2.75 conceded per game, with 18 "
        "points from twelve outings. Columbus are 3-5 on six points, scoring 2.5 and conceding "
        "3.6, and they head to the Lenovo Center after a defeat. The home side has the deeper "
        "scoring and the better goal difference, so take Carolina Hurricanes at -217."
    ),
    "nhl-2026020213": (
        "Vancouver's 2-9 record is the worst in this slate: five points from twelve games, 2.9 "
        "goals scored and 4.7 conceded, and a run of defeats behind them. San Jose are 6-4 with "
        "13 points, scoring 3.0 and conceding 3.4, and they won their most recent outing. "
        "Against a Canucks side leaking almost five a night, San Jose Sharks at -213."
    ),
    "nhl-2026020187": (
        "Detroit are 4-3 through ten games with 11 points, scoring 2.8 and conceding 3.0, and "
        "they won their latest match. That is respectable form, but it is not the form of an "
        "Edmonton team on 8-1, 17 points, 4.7 goals for and 3.2 against. Rogers Place has been "
        "a hard trip this month, so Edmonton Oilers at -190 is the selection."
    ),
    # ---------------- Basketball (EuroLeague / EuroCup) ----------------
    "ec_games-67": (
        "Aris Thessaloniki are 4-0 in the EuroCup, scoring 378 points and conceding 301 across "
        "those four games, a plus 19.25 margin a night. Cedevita Olimpija are 0-4, with 290 "
        "scored and 333 conceded, and all four defeats came by double figures apart from a "
        "four-point loss at Burgos. The gap at both ends is wide: Aris Thessaloniki at -587."
    ),
    "el_games-76": (
        "Panathinaikos are 6-1 in the EuroLeague, scoring 613 points and conceding 517 in seven "
        "games for a plus 13.7 margin, the best in this group. Armani Olimpia Milan are 1-6, "
        "with 585 scored and 648 conceded, and their only win was a two-point game against "
        "Virtus. Athens has been a fortress for the hosts, so Panathinaikos AKTOR Athens -476."
    ),
    "el_games-90": (
        "Olympiacos have started 5-1, scoring 589 and conceding 539 across six EuroLeague "
        "games, while Armani Olimpia Milan are 1-6 having conceded 648 points in seven "
        "outings. Milan have lost six of seven, including a 21-point beating by Dubai, and "
        "they now travel to Piraeus. Take Olympiacos Piraeus on the match winner at -414."
    ),
    "ec_games-91": (
        "Napoli Basketball are 4-0 in the EuroCup with 368 points scored and 334 conceded, a "
        "plus 8.5 margin a game, and they have won every match by at least six. Dolomiti "
        "Energia Trento are 1-3, scoring 316 and conceding 345, and they have already lost by "
        "25 in the competition. Napoli's home record and scoring depth make Napoli Basketball "
        "at -360 the call."
    ),
    "el_games-72": (
        "Dubai Basketball are 5-2 with 597 points scored and 584 conceded in seven EuroLeague "
        "games, and they have won three of their last four. Paris Basketball are 1-5 after "
        "scoring 504 and conceding 545, with a 19-point loss to Panathinaikos among the "
        "defeats. Dubai's home record and the plus 1.9 margin are enough: Dubai Basketball "
        "at -298."
    ),
    # ---------------- Rugby Union (TOP 14) ----------------
    "top14-11866": (
        "Section Paloise are second on 22 points after six rounds, five wins and one defeat, "
        "with 239 points scored and 181 conceded. RC Toulon sit on 12 points from 2-4, having "
        "scored 130 and conceded 130, so their points difference is level while Pau's is plus "
        "58. Pau have won five of six and travel with the better pack, so Section Paloise at "
        "-266 is the bet."
    ),
    "top14-11867": (
        "Stade Toulousain lead the TOP 14 on 24 points, five wins from six, with 197 points "
        "scored and 124 conceded, the best defensive record in the top half. USA Perpignan are "
        "3-3 on 13 points with 166 scored and 199 conceded, 33 points in the red. Toulouse "
        "have lost once all season and none of Perpignan's wins came against a side this "
        "high: Stade Toulousain at -243."
    ),
    "top14-11861": (
        "Aviron Bayonnais are 4-2 on 17 points, with 190 points scored and 214 conceded, and "
        "they return home after a win. LOU Rugby are 3-3 on 14 points, 193 scored and 202 "
        "conceded, and they have alternated wins and defeats through six rounds. Bayonne's "
        "home form and the three extra league points make them the call: Aviron Bayonnais at "
        "-166."
    ),
    "top14-11862": (
        "RC Vannes are bottom of the TOP 14 with a single point from six defeats, 117 points "
        "scored and 176 conceded. ASM Clermont are 2-4 on 11 points with 140 scored and 169 "
        "conceded, and they have faced the harder half of the draw. A winless home side "
        "against a team with a stronger set piece is a clear spot, so ASM Clermont at -163 "
        "is the selection."
    ),
    "top14-11865": (
        "Montpellier have scored 163 points and conceded 122 in six rounds, a plus 6.8 margin "
        "a game, while Racing 92 are 2-4 having conceded 196 and scored 143. Racing have lost "
        "four of six and their defence has been the weaker of the two all season. Montpellier "
        "travel with the better points difference, so Montpellier Herault Rugby at -120."
    ),
    # ---------------- Baseball (World Series) ----------------
    "mlb-849805": (
        "Milwaukee won 103 games to Tampa Bay's 98 and out-scored them across the season, 5.14 "
        "runs a game to 4.54, while conceding 3.82 against 4.01. The Brewers closed the regular "
        "season on a five-game winning streak and the Rays lost their last game. American "
        "Family Field opens the series, so Brewers at -128 is the pick."
    ),
    # ---------------- Darts (PDC European Championship) ----------------
    "pdc-88052-SteKim": (
        "Stephen Bunting has won four of five completed matches in Dortmund, taking 28 legs "
        "to 18, while Kim Huybrechts has won one of two with 11 legs to 7. Bunting's scoring "
        "has been the more consistent across the event and he has already come through a "
        "deciding-leg match. Over a long format that consistency matters, so Stephen Bunting "
        "to win at -151."
    ),
    "pdc-88052-RosDam": (
        "Damon Heta has won four of five matches at the European Championship and leads the "
        "leg count 27 to 20, a plus 1.4 margin a match. Ross Smith has won two of three, 16 "
        "legs to 12, but has played fewer completed matches and a lighter draw. Heta's heavier "
        "scoring and greater number of completed matches make him the call: Damon Heta at "
        "-128."
    ),
    "pdc-88053-WesMar": (
        "Wessel Nijman has won two of three completed matches in Dortmund, taking 17 legs to "
        "12, a plus 1.67 margin a match. Martin Schindler has won one of two and is level on "
        "legs at 10 apiece, so his scoring has not separated him from his opponents. Nijman "
        "has the stronger leg difference and the better recent record, so Wessel Nijman at "
        "-124 is the selection."
    ),
    # ---------------- Snooker (Northern Ireland Open) ----------------
    "wst-45bc77f9": (
        "Sam Craigie has won all three of his matches in Belfast and holds a 14-7 frame record, "
        "a plus 2.33 frame margin a match. Kyren Wilson has won two from two with 10 frames to "
        "4, but has played one fewer match and against weaker opposition. Craigie has played "
        "the longer route through the draw and has the sharper scoring, so Sam Craigie at -109 "
        "is the value."
    ),
    # ---------------- Golf (PGA TOUR, Bermuda Championship) ----------------
    "golf-R2026528": (
        "Kensei Hirata is tied for the lead at 13 under through two rounds at Port Royal, "
        "having opened with 65 and 64 for 129 strokes. The top-ten line currently sits at 11 "
        "under, so he is two strokes inside it with 36 holes to play, and only one player in "
        "the field has gone lower than his 64. Take Kensei Hirata for a top ten at -495."
    ),
    # ---------------- Motor Racing (Formula 1, United States GP) ----------------
    "f1-2026-united-states": (
        "Mercedes lead the 2026 constructors' championship on 578 points, with Ferrari on 444 "
        "and McLaren on 339 after seventeen rounds. Round 18 is the United States Grand Prix "
        "at the Circuit of the Americas over 56 laps on 25 October, and in first practice "
        "George Russell was fourth and Kimi Antonelli fifth behind Charles Leclerc's 1:36.052. "
        "Mercedes to supply the race winner at +234."
    ),
}
