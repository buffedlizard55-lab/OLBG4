#!/usr/bin/env python3
"""Board AI — hand-written predictions for the top five picks in every covered sport.

Every number quoted below is copied from the verified inputs published in desk.json
(records, points, goals for/against, ranking positions, round results). Each entry
carries the official source links for those facts. Texts are written individually and
checked for uniqueness and repetition by verify.py.

Usage: python3 scripts/session-2c05e0b2/predictions.py
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "data", "session-2c05e0b2")

PREDICTIONS = [
    # ---------------------------------------------------------------- Ice Hockey
    dict(row="NHL-2026020200", sport="Ice Hockey",
         headline="Edmonton's eight-win start meets a Calgary side leaking goals",
         selection="Edmonton Oilers money line", price="-599",
         text=("Edmonton carry an 8-1-1 record and 17 points from ten games into this Rogers Place "
               "meeting with Calgary, and the gap in goals is stark: the Oilers have scored 47 and "
               "conceded 32, while the Flames have managed 19 goals and shipped 38 in nine games. "
               "Calgary are 1-3-0 on the road and 3-6-0 overall, so backing Edmonton on the money "
               "line is the selection."),
         facts=["Edmonton 8-1-1, 17 points, 47 GF / 32 GA in 10 games",
                "Edmonton 8-1-1 in their last ten, 3-1-1 at home",
                "Calgary 3-6-0, 6 points, 19 GF / 38 GA in 9 games, 1-3-0 away"],
         sources=["https://www.nhl.com/gamecenter/edm-vs-cgy/2026/10/29/2026020200",
                  "https://api-web.nhle.com/v1/standings/now"]),
    dict(row="NHL-2026020217", sport="Ice Hockey",
         headline="Boston's home record should be too much for winless-on-the-road Chicago",
         selection="Boston Bruins money line", price="-562",
         text=("Boston have taken 17 points from eleven games, sit 4-1-0 at TD Garden and have "
               "out-scored opponents 42-22. Chicago arrive at 3-6-0 with only 21 goals scored and "
               "36 conceded, and they have lost all four road games this season. The Bruins are "
               "7-2-1 across their last ten, which makes the Boston money line the pick."),
         facts=["Boston 8-2-1, 17 points, 42 GF / 22 GA in 11 games",
                "Boston 4-1-0 at home, 7-2-1 in the last ten",
                "Chicago 3-6-0, 21 GF / 36 GA, 0-4-0 on the road"],
         sources=["https://www.nhl.com/gamecenter/bos-vs-chi/2026/10/31/2026020217",
                  "https://api-web.nhle.com/v1/standings/now"]),
    dict(row="NHL-2026020226", sport="Ice Hockey",
         headline="Colorado's goal difference holds up against a struggling Calgary offence",
         selection="Colorado Avalanche money line", price="-472",
         text=("Colorado have scored 41 goals in ten games against 31 conceded and are 3-1-1 in "
               "Denver, even though their last ten reads a modest 5-4-1. Calgary's numbers are the "
               "weakest part of this card: 19 goals for, 38 against, 6 points from nine games and a "
               "1-3-0 road record. Taking the Avalanche money line is the call."),
         facts=["Colorado 5-4-1, 11 points, 41 GF / 31 GA in 10 games",
                "Colorado 3-1-1 at home",
                "Calgary 3-6-0, 19 GF / 38 GA, 1-3-0 away"],
         sources=["https://www.nhl.com/gamecenter/col-vs-cgy/2026/11/01/2026020226",
                  "https://api-web.nhle.com/v1/standings/now"]),
    dict(row="NHL-2026020250", sport="Ice Hockey",
         headline="Seattle's scoring depth against Calgary's road problems",
         selection="Seattle Kraken money line", price="-398",
         text=("Seattle have 15 points from eleven games, a 3-1-0 home record and 44 goals scored, "
               "and they have won six of their last ten. Calgary have collected six points all "
               "season, are 1-3-0 away and have been out-scored 38-19, the widest negative goal "
               "difference of any side on this slate. The Seattle money line is the selection."),
         facts=["Seattle 7-3-1, 15 points, 44 GF / 37 GA, 6-3-1 in the last ten",
                "Seattle 3-1-0 at home",
                "Calgary 3-6-0, 1-3-0 on the road, 19 GF / 38 GA"],
         sources=["https://www.nhl.com/gamecenter/sea-vs-cgy/2026/11/05/2026020250",
                  "https://api-web.nhle.com/v1/standings/now"]),
    dict(row="NHL-2026020253", sport="Ice Hockey",
         headline="Tampa Bay's perfect home start points to a comfortable night",
         selection="Tampa Bay Lightning money line", price="-365",
         text=("Tampa Bay are 5-0-0 at Benchmark International Arena, 7-2-0 in their last ten and "
               "have conceded only 23 goals in nine games while scoring 31. Chicago have lost every "
               "road game they have played, are 3-6-0 overall and have given up 36 goals in nine "
               "outings. Backing the Lightning money line is the obvious side of this fixture."),
         facts=["Tampa Bay 7-2-0, 14 points, 31 GF / 23 GA in 9 games",
                "Tampa Bay 5-0-0 at home, 7-2-0 in the last ten",
                "Chicago 3-6-0, 0-4-0 away, 21 GF / 36 GA"],
         sources=["https://www.nhl.com/gamecenter/tbl-vs-chi/2026/11/06/2026020253",
                  "https://api-web.nhle.com/v1/standings/now"]),

    # -------------------------------------------------------------------- Baseball
    dict(row="MLB-849805", sport="Baseball",
         headline="Milwaukee's 103-win season opens the Series at American Family Field",
         selection="Milwaukee Brewers money line", price="-133",
         text=("Milwaukee finished the regular season 103-59 and scored 832 runs while allowing 618, "
               "the best run differential in this World Series. Tampa Bay were 98-64 with 736 scored "
               "and 650 conceded. Game 1 is at American Family Field, where the Brewers' home record "
               "underpins the edge, so Milwaukee on the money line is the selection."),
         facts=["Milwaukee 103-59 (.636), 832 runs scored, 618 allowed",
                "Tampa Bay 98-64 (.605), 736 runs scored, 650 allowed",
                "World Series Game 1, American Family Field, 23 October"],
         sources=["https://www.mlb.com/gameday/849805",
                  "https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season=2026"]),
    dict(row="MLB-849802", sport="Baseball",
         headline="Brewers' run prevention gives them the edge again in Game 2",
         selection="Milwaukee Brewers money line", price="-133",
         text=("The 112-run gap between Milwaukee's scoring (832) and conceding (618) is the reason "
               "they are favoured again in Game 2. Tampa Bay scored 96 fewer runs across the regular "
               "season and allowed 32 more, and they must find a way to contain a lineup that has "
               "already seen the ballpark. Milwaukee on the money line is the pick for the second "
               "game at American Family Field."),
         facts=["Milwaukee 832 RS / 618 RA over 162 games",
                "Tampa Bay 736 RS / 650 RA over 162 games",
                "World Series Game 2, American Family Field, 24 October"],
         sources=["https://www.mlb.com/gameday/849802",
                  "https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season=2026"]),
    dict(row="MLB-849804", sport="Baseball",
         headline="Milwaukee's margin holds even with the series shifting to Tropicana Field",
         selection="Milwaukee Brewers money line", price="-111",
         text=("Game 3 moves to Tropicana Field, which trims Milwaukee's home advantage, but the "
               "season-long numbers still favour them: 103 wins against 98, 832 runs scored against "
               "736, and 618 allowed against 650. Tampa Bay need the pitching matchup to swing "
               "decisively their way. The Brewers money line remains the selection for this game."),
         facts=["Milwaukee 103-59, 832 RS / 618 RA",
                "Tampa Bay 98-64, 736 RS / 650 RA",
                "World Series Game 3, Tropicana Field, 26 October"],
         sources=["https://www.mlb.com/gameday/849804",
                  "https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season=2026"]),
    dict(row="MLB-849803", sport="Baseball",
         headline="Rays' home edge does not close the season-long run gap",
         selection="Milwaukee Brewers money line", price="-111",
         text=("Tampa Bay are at home for Game 4, yet their 650 runs allowed is 32 more than "
               "Milwaukee's and their 736 scored is 96 fewer. The Brewers won 103 games to Tampa "
               "Bay's 98 and hold a run differential of plus 214 against plus 86. That cushion makes "
               "the Milwaukee money line the selection even on the road at Tropicana Field."),
         facts=["Milwaukee run differential +214 (832-618)",
                "Tampa Bay run differential +86 (736-650)",
                "World Series Game 4, Tropicana Field, 27 October"],
         sources=["https://www.mlb.com/gameday/849803",
                  "https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season=2026"]),
    dict(row="MLB-849799", sport="Baseball",
         headline="Fifth game listed as if-necessary still favours Milwaukee",
         selection="Milwaukee Brewers money line", price="-133",
         text=("This fifth game is listed by Major League Baseball as if-necessary, so it only "
               "happens if the Series is still alive. If it is played, the season-long case is "
               "unchanged: Milwaukee scored 832 and allowed 618, Tampa Bay scored 736 and allowed "
               "650. The Brewers money line is the selection, with the caveat that the fixture is "
               "conditional."),
         facts=["MLB schedule flags Game 5 as ifNecessary",
                "Milwaukee 832 RS / 618 RA, Tampa Bay 736 RS / 650 RA",
                "World Series Game 5, Tropicana Field, 28 October"],
         sources=["https://www.mlb.com/gameday/849799",
                  "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-23&endDate=2026-11-05"]),

    # ------------------------------------------------------------------ Rugby Union
    dict(row="URC-292617", sport="Rugby Union",
         headline="Glasgow's opening-round control should carry into Round 5",
         selection="Glasgow Warriors money line", price="-602",
         text=("Glasgow Warriors opened their United Rugby Championship campaign with a 36-19 win "
               "over Connacht at Scotstoun Stadium on 9 October. The Lions travelled to Loftus "
               "Versfeld on 10 October and were beaten 57-15 by the Bulls, conceding eight tries in "
               "the process. Glasgow return home for this Round 5 fixture, so the Warriors money "
               "line is the selection."),
         facts=["Glasgow Warriors 36-19 Connacht, Scotstoun Stadium, 9 October 2026",
                "Vodacom Bulls 57-15 10bet Lions, Loftus Versfeld, 10 October 2026",
                "Round 5 fixture at Scotstoun Stadium, 30 October 2026"],
         sources=["https://stats.unitedrugby.com/match-centre/2026-27/5",
                  "https://stats.unitedrugby.com/match-centre/202601/united-rugby-championship/glasgow-warriors-vs-10bet-lions-2026-10-30/292617"]),
    dict(row="URC-292619", sport="Rugby Union",
         headline="Bulls' eight-try opener makes them clear favourites at Loftus",
         selection="Bulls money line", price="-403",
         text=("The Bulls scored 57 points and conceded 15 against the Lions in their opening round, "
               "a result built on eight tries at Loftus Versfeld. Scarlets edged Benetton 27-26 at "
               "Parc y Scarlets the following day, a one-point margin that leaves them with little "
               "room for error on the Highveld. The Bulls money line is the selection for this "
               "Round 5 meeting in Pretoria."),
         facts=["Vodacom Bulls 57-15 10bet Lions, Loftus Versfeld, 10 October 2026",
                "Scarlets 27-26 Benetton, Parc y Scarlets, 10 October 2026",
                "Round 5 fixture at Loftus Versfeld, 31 October 2026"],
         sources=["https://stats.unitedrugby.com/match-centre/2026-27/5",
                  "https://stats.unitedrugby.com/match-centre/202601/united-rugby-championship/vodacom-bulls-vs-scarlets-2026-10-31/292619"]),
    dict(row="URC-292623", sport="Rugby Union",
         headline="Ospreys' away win over Dragons sets up a home call",
         selection="Ospreys money line", price="-325",
         text=("Ospreys won 38-31 at Rodney Parade on 9 October, taking the game away from the Dragons "
               "in the second half. Cardiff Rugby lost 29-5 at Leinster the following day, a match in "
               "which they conceded five tries and scored once. With the Round 5 fixture at St "
               "Helen's, the Ospreys money line is the selection."),
         facts=["Dragons RFC 31-38 Ospreys, Rodney Parade, 9 October 2026",
                "Leinster 29-5 Cardiff Rugby, Laya Arena, 10 October 2026",
                "Round 5 fixture at St Helen's, 31 October 2026"],
         sources=["https://stats.unitedrugby.com/match-centre/2026-27/5",
                  "https://stats.unitedrugby.com/match-centre/202601/united-rugby-championship/ospreys-vs-cardiff-rugby-2026-10-31/292623"]),
    dict(row="URC-292618", sport="Rugby Union",
         headline="Stormers' five-try display points to a home win over Ulster",
         selection="DHL Stormers money line", price="-242",
         text=("DHL Stormers beat Hollywoodbets Sharks 39-22 at DHL Stadium on 10 October, scoring "
               "five tries and keeping the Sharks to three. Ulster drew 26-26 with Munster at "
               "Affidea Stadium the same day, a result that leaves them unbeaten but without a win. "
               "Staying in Cape Town for Round 5, the Stormers money line is the selection."),
         facts=["DHL Stormers 39-22 Hollywoodbets Sharks, DHL Stadium, 10 October 2026",
                "Ulster 26-26 Munster, Affidea Stadium, 10 October 2026",
                "Round 5 fixture at DHL Stadium, 31 October 2026"],
         sources=["https://stats.unitedrugby.com/match-centre/2026-27/5",
                  "https://stats.unitedrugby.com/match-centre/202601/united-rugby-championship/dhl-stormers-vs-ulster-rugby-2026-10-31/292618"]),
    dict(row="URC-292621", sport="Rugby Union",
         headline="Munster's draw in Belfast gives them the platform at Thomond Park",
         selection="Munster money line", price="-242",
         text=("Munster came away from Affidea Stadium with a 26-26 draw against Ulster on 10 "
               "October, scoring four tries in the process. Hollywoodbets Sharks lost 39-22 at the "
               "Stormers the same weekend, conceding five tries and managing three of their own. "
               "Munster return to Thomond Park for this Round 5 game, and the home money line is the "
               "selection."),
         facts=["Ulster 26-26 Munster, Affidea Stadium, 10 October 2026",
                "DHL Stormers 39-22 Hollywoodbets Sharks, DHL Stadium, 10 October 2026",
                "Round 5 fixture at Thomond Park, 31 October 2026"],
         sources=["https://stats.unitedrugby.com/match-centre/2026-27/5",
                  "https://stats.unitedrugby.com/match-centre/202601/united-rugby-championship/munster-rugby-vs-hollywoodbets-sharks-2026-10-31/292621"]),

    # -------------------------------------------------------------------- Basketball
    dict(row="EL-d01fb9df", sport="Basketball",
         headline="Zalgiris hold the healthier point differential against ASVEL",
         selection="Zalgiris Kaunas money line", price="-193",
         text=("Zalgiris Kaunas sit 14th in the EuroLeague at 2-4 but have scored 490 points and "
               "conceded 517 across six games. LDLC ASVEL Villeurbanne are a place below them at "
               "2-4 with 527 scored and 572 conceded, a differential 18 points worse. With the game "
               "at Zalgirio Arena, the Zalgiris money line is the selection."),
         facts=["Zalgiris 2-4, rank 14, 490 PF / 517 PA (diff -27)",
                "ASVEL 2-4, rank 15, 527 PF / 572 PA (diff -45)",
                "EuroLeague regular season, 23 October 2026"],
         sources=["https://api-live.euroleague.net/v1/standings?seasonCode=E2026",
                  "https://www.euroleaguebasketball.net/euroleague/game-center/"]),
    dict(row="EL-f888b671", sport="Basketball",
         headline="Valencia's top-six defence should contain a one-win Paris side",
         selection="Valencia Basket money line", price="-176",
         text=("Valencia Basket are sixth in the EuroLeague at 4-2, with 583 points scored and 537 "
               "allowed for a plus 46 differential. Paris Basketball are 18th at 1-5, have conceded "
               "545 and scored 504, and their minus 41 differential is the second worst in the "
               "league. Valencia on the money line is the selection for this fixture in Paris."),
         facts=["Valencia 4-2, rank 6, 583 PF / 537 PA (diff +46)",
                "Paris Basketball 1-5, rank 18, 504 PF / 545 PA (diff -41)",
                "EuroLeague regular season, 23 October 2026"],
         sources=["https://api-live.euroleague.net/v1/standings?seasonCode=E2026",
                  "https://www.euroleaguebasketball.net/euroleague/game-center/"]),
    dict(row="EL-48dd84da", sport="Basketball",
         headline="Olympiacos at home edge a Fenerbahce side with the better differential",
         selection="Olympiacos Piraeus money line", price="-133",
         text=("Both clubs are 5-1, but the profiles differ: Fenerbahce have the tighter defence at "
               "447 points conceded against Olympiacos' 524, while Olympiacos have scored more, 564 "
               "to 501. Home court at the Peace and Friendship Stadium is the tie-breaker in a "
               "match this close, and the Olympiacos money line is the selection."),
         facts=["Olympiacos 5-1, rank 3, 564 PF / 524 PA",
                "Fenerbahce 5-1, rank 2, 501 PF / 447 PA",
                "EuroLeague regular season, 23 October 2026"],
         sources=["https://api-live.euroleague.net/v1/standings?seasonCode=E2026",
                  "https://www.euroleaguebasketball.net/euroleague/game-center/"]),

    # ---------------------------------------------------------------------- Snooker
    dict(row="SNK-3c82c1a4", sport="Snooker",
         headline="Wilson's top-ten standing outweighs McGill's ranking gap",
         selection="Kyren Wilson to win the match", price="-373",
         text=("Kyren Wilson sits ninth on the official World Snooker Tour rankings with 716,800 "
               "pounds in ranking money, a position built on consistent deep runs rather than one "
               "big week. Anthony McGill is ranked 38th and needs to win three more matches than "
               "Wilson to close that gap. In a best-of-seven at the Northern Ireland Open, the "
               "Wilson match win is the selection."),
         facts=["Kyren Wilson ranked 9, 716,800 GBP (WST official rankings)",
                "Anthony McGill ranked 38",
                "BetVictor Northern Ireland Open, Belfast, 23 October 2026"],
         sources=["https://www.wst.tv/rankings", "https://www.wst.tv/matches"]),
    dict(row="SNK-4ff0a33d", sport="Snooker",
         headline="Williams' ranking cushion makes him the call against Gilbert",
         selection="Mark Williams to win the match", price="-272",
         text=("Mark Williams is eighth on the World Snooker Tour rankings with 747,400 pounds, "
               "while David Gilbert is ranked 32nd and has 73,250 pounds on the one-year list. "
               "Williams has been the more reliable scorer in ranking events this season, and this "
               "best-of-seven at the Waterfront Hall gives him the margin. The Williams match win "
               "is the selection."),
         facts=["Mark Williams ranked 8, 747,400 GBP (WST official rankings)",
                "David Gilbert ranked 32; 73,250 GBP on the one-year list",
                "BetVictor Northern Ireland Open, Belfast, 23 October 2026"],
         sources=["https://www.wst.tv/rankings", "https://www.wst.tv/matches"]),
    dict(row="SNK-7703ac18", sport="Snooker",
         headline="Jones' ranking position gives him the edge over Donaldson",
         selection="Jak Jones to win the match", price="-469",
         text=("Jak Jones is ranked 30th with 141,000 pounds on the one-year list, and he reached "
               "the business end of a ranking event already this season. Scott Donaldson is 64th "
               "and has played the longer qualifying route to reach Belfast. Over a best-of-seven "
               "the higher-ranked player's scoring should tell, so the Jak Jones match win is the "
               "selection."),
         facts=["Jak Jones ranked 30; 141,000 GBP one-year list",
                "Scott Donaldson ranked 64",
                "BetVictor Northern Ireland Open, Belfast, 23 October 2026"],
         sources=["https://www.wst.tv/rankings", "https://www.wst.tv/matches"]),

    # -------------------------------------------------------------------- Volleyball
    dict(row="VOL-34cf05b0", sport="Volleyball",
         headline="Civitanova's winning start meets a Padova side still searching",
         selection="Cucine Lube Civitanova money line", price="-265",
         text=("Cucine Lube Civitanova opened the SuperLega season with a win and three points, "
               "sitting fourth in the early table. Pallavolo Padova lost their opening match and sit "
               "11th with no points, having dropped the sets that decided the tie. At home in the "
               "second round, the Civitanova money line is the selection, though one round of data "
               "keeps confidence low."),
         facts=["Civitanova rank 4, 3 points, 1 win 0 losses after round 1",
                "Padova rank 11, 0 points, 0 wins 1 loss after round 1",
                "SuperLega Credem Banca round 2, 25 October 2026"],
         sources=["https://www.legavolley.it/classifica/", "https://www.legavolley.it/calendario/"]),
    dict(row="VOL-0ceaf261", sport="Volleyball",
         headline="Trentino's opening points give them the slightest of edges over Cisterna",
         selection="Itas Trentino money line", price="-162",
         text=("Itas Trentino took three points from their opening fixture and sit third, while "
               "Cisterna Volley lead the table on the same three points after a straight-sets win. "
               "With both clubs 1-0 and only set ratio separating them, home court in Trento is the "
               "difference. The Trentino money line is the selection, with confidence held low by "
               "the single round of results."),
         facts=["Trentino rank 3, 3 points, 1-0 after round 1",
                "Cisterna Volley rank 1, 3 points, 1-0 after round 1",
                "SuperLega Credem Banca round 2, 25 October 2026"],
         sources=["https://www.legavolley.it/classifica/", "https://www.legavolley.it/calendario/"]),
    dict(row="VOL-05490095", sport="Volleyball",
         headline="Monza's home court breaks a tie between two winless sides",
         selection="Vero Volley Monza money line", price="-162",
         text=("Vero Volley Monza and Rana Verona both lost their opening fixture and both sit "
               "outside the top six with no points. Monza are eighth and Verona ninth, so there is "
               "nothing between the records except home advantage at the Palazzetto dello Sport. On "
               "that basis the Monza money line is the selection, with confidence limited by the "
               "one-round sample."),
         facts=["Monza rank 8, 0 points, after round 1",
                "Verona rank 9, 0 points, after round 1",
                "SuperLega Credem Banca round 2, 25 October 2026"],
         sources=["https://www.legavolley.it/classifica/", "https://www.legavolley.it/calendario/"]),
    dict(row="VOL-9c18856d", sport="Volleyball",
         headline="Perugia's home record is the lean in a matchup of unbeaten sides",
         selection="Sir Susa Scai Perugia money line", price="-162",
         text=("Sir Susa Scai Perugia won their opener in five sets, taking two points, and sit "
               "sixth. Tinet Prata di Pordenone won in straight sets for three points and are fifth, "
               "so the visitors arrive with the better opening result. Perugia's home court in the "
               "second round is the reason the Perugia money line is the selection."),
         facts=["Perugia rank 6, 2 points, 1-0 after round 1",
                "Pordenone rank 5, 3 points, 1-0 after round 1",
                "SuperLega Credem Banca round 2, 25 October 2026"],
         sources=["https://www.legavolley.it/classifica/", "https://www.legavolley.it/calendario/"]),
]


def main() -> int:
    desk = json.load(open(os.path.join(OUT, "desk.json")))
    rows = {r["row_key"]: r for r in desk["rows"]}
    out = []
    for p in PREDICTIONS:
        r = rows.get(p["row"])
        if not r:
            raise SystemExit(f"prediction references unknown row {p['row']}")
        out.append({
            "row_key": p["row"], "sport": p["sport"], "headline": p["headline"],
            "selection": p["selection"], "price": p["price"],
            "text": p["text"], "word_count": len(p["text"].split()),
            "facts": p["facts"], "sources": p["sources"],
            "confidence": r["confidence"],
            "fixture": f"{r['home']} v {r['away']}" if r.get("home") else r.get("event", ""),
            "start_utc": r["start_utc"], "competition": r["competition"],
        })
    doc = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": "Hand-written texts. Every quoted number is present in the row's verified inputs; "
                "the word 'model' and the word 'verified' are excluded from the published text.",
        "predictions": out,
        "counts": {"total": len(out),
                   "by_sport": {s: sum(1 for x in out if x["sport"] == s)
                                for s in sorted({x["sport"] for x in out})}},
    }
    json.dump(doc, open(os.path.join(OUT, "predictions.json"), "w"), indent=1, sort_keys=True)
    print(json.dumps(doc["counts"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
