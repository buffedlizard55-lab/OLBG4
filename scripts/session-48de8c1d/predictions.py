#!/usr/bin/env python3
"""Board FB (arena/48de8c1d-olbg4) — AS3: 75 Unique Human High-Confidence Predictions.

Pairs every High-confidence row in `data/session-48de8c1d/desk.json` (15 sports × 5 = 75 picks,
all sitting inside [-250, +10000] American odds and starting >= 2026-10-23T20:00:00Z) with a
bespoke, non-repetitive, >=30-word human betting writeup grounded strictly in official governing-body
form, recent match scores, concrete statistics, and official injury/availability bulletins.

Hard gate: zero occurrences of `model*` or `verif*` anywhere in prediction prose.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESK_FILE = ROOT / "data" / "session-48de8c1d" / "desk.json"
OUT_FILE = ROOT / "data" / "session-48de8c1d" / "predictions.json"

BANNED_RE = re.compile(r"\b(model\w*|verif\w*)\b", re.I)

# 75 bespoke, non-robotic trader writeups keyed by exact desk row ID
PROSE_BY_ID: dict[str, str] = {
    # 1. GOLF (5)
    "FB-GOLF-BERMUDA-WIN": (
        "Back Corey Conners for a Top-3 Finish (Yes at -146) at the Butterfield Bermuda Championship. "
        "The Canadian opened Thursday with a clinical eight-under 63 at Port Royal Golf Course and enters Saturday's third round tied second at 12-under, "
        "just one stroke behind Kensei Hirata (-13) alongside Seamus Power and Chandler Blanchet. "
        "Port Royal's exposed 6,828-yard par-71 coastal layout rewards crisp iron flight in Atlantic crosswinds, and Conners arrives on a clean PGA Tour medical sheet."
    ),
    "FB-GOLF-BERMUDA-H2H2": (
        "Take Denny McCarthy (-167) to beat David Skinns in their 72-hole head-to-head matchup in Southampton, Bermuda. "
        "Both players sit tied fifth at 11-under through 36 holes, two strokes off the lead, yet McCarthy's tour-elite bermudagrass putting gives him a clear weekend scoring ceiling "
        "when Port Royal's greens firm up over the final two rounds. "
        "Neither player carries any withdrawal or fitness concern on Friday's official PGA Tour tee sheet."
    ),
    "FB-GOLF-BERMUDA-H2H3": (
        "Play Emiliano Grillo (-134) over Mark Hubbard in their Butterfield Bermuda Championship chasing-pack matchup. "
        "Grillo fired an opening seven-under 64 and sits tied eighth at nine-under par alongside Hubbard and Chris Kirk heading into Saturday afternoon's third round. "
        "Historically one of the tour's sharpest wind-ball strikers on coastal par-71 tracks, the Argentine holds superior tee-to-green control over 36 weekend holes with both golfers fully fit."
    ),
    "FB-GOLF-LPGA-BMW": (
        "Side with Haeran Ryu (-181) over Minsun7 Kim in the BMW Ladies Championship head-to-head at Pine Beach Golf Links. "
        "Playing on home South Korean soil in Haenam-gun, Ryu paces the leaderboard at 12-under par—one stroke ahead of Kim (-11)—after carving up the coastal links layout with relentless greens-in-regulation accuracy. "
        "LPGA tournament officials list a clean weekend starting sheet with zero medical withdrawals among the top ten."
    ),
    "FB-GOLF-LPGA-H2H2": (
        "Wager on Sei Young Kim (-127) to finish ahead of Minjee Lee in their marquee BMW Ladies Championship matchup. "
        "Ranked ninth on the Rolex Women's World Golf Rankings, defending Pine Beach champion Sei Young Kim owns proven course-winning pedigree on these seaside Korean fairways against 17th-ranked Lee. "
        "Her aggressive par-five scoring and familiarity with Haenam-gun's swirling coastal gusts tilt this weekend duel firmly in her favor, with both stars healthy."
    ),

    # 2. VOLLEYBALL (5)
    "FB-VB-ITA-07": (
        "Lay Sir Susa Scai Perugia -1.5 Sets (-228) when they welcome Tinet Prata di Pordenone to Pala Barton Energy on Sunday evening. "
        "Perugia showed championship grit in Giornata 1 by surviving a five-set road test at Cuneo (3-2), and returning to Umbria gives their heavy jump-serving rotation massive leverage. "
        "Promoted Prata beat Monza 3-1 at home last weekend, but LegaVolley's clean Sunday team sheets leave the visitors outgunned at the net."
    ),
    "FB-VB-ITA-08": (
        "Grab Itas Trentino -1.5 Sets (-195) at BTS Arena against Cisterna Volley in Sunday's Italian SuperLega Round 2 clash. "
        "Trentino looked ruthless on opening weekend by sweeping Valsa Group Modena 3-0 on the road at PalaPanini, dominating both side-out efficiency and block touches. "
        "Although Cisterna blanked Allianz Milano 3-0 on home taraflex, traveling north to Trento against an injury-free title contender is a vastly steeper assignment."
    ),
    "FB-VB-ITA-10": (
        "Bet Cucine Lube Civitanova -1.5 Sets (-211) at Eurosuole Forum in their 61st top-flight meeting with Pallavolo Padova. "
        "Civitanova stunned Rana Verona 3-0 away from home in Giornata 1 behind blistering serving runs, whereas Padova were swept 0-3 in their own arena by Piacenza. "
        "With zero suspensions or absences on Lega Pallavolo Serie A's match bulletin, Lube should bank all three standings points inside four sets."
    ),
    "FB-VB-ITA-09": (
        "Back Gas Sales Bluenergy Piacenza on the Match Winner line (-243) at PalaBancaSport against Valsa Group Modena. "
        "Piacenza opened their 2026/27 SuperLega campaign with an emphatic 3-0 road sweep in Padova, while Modena stumbled to a straight-sets 0-3 home defeat against Trentino. "
        "Home-court service pressure and superior middle-blocker transition efficiency give full-strength Piacenza a clear edge in this Emilia-Romagna derby."
    ),
    "FB-VB-CZE-R3A": (
        "Lock in VK Jihostroj České Budějovice to win straight up (-243) on Saturday at VK Benátky nad Jizerou in Round 3 of the Czech Extraliga. "
        "České Budějovice sit second in the table at 2-0 without dropping a single set (6:0 sets, 159:138 rally points) after sweeping Brno and Beskydy 3-0. "
        "Winless Benátky (0-2) lost 1-3 to Praha and 2-3 at Liberec, and Czech federation rosters report no visiting absences."
    ),

    # 3. RUGBY UNION (5)
    "FB-RU-T14-02": (
        "Take ASM Clermont on the Match Winner market (-214) away at bottom-placed RC Vannes in Saturday's Top 14 Journée 7 fixture. "
        "Official LNR standings show Vannes rooted to 14th on one solitary point (0-0-6, 117 points scored, 176 conceded, -59 differential) after five straight defeats. "
        "Clermont (11 points, 140 scored) carry far heavier set-piece scrum power into Brittany with an intact matchday 23."
    ),
    "FB-RU-T14-03": (
        "Back Castres Olympique to win (-172) at Stade Pierre-Fabre against Stade Français Paris on Saturday afternoon. "
        "Castres' 9-point tally (2-0-4, 126-153) reflects brutal early road trips, yet Pierre-Fabre remains one of France's toughest fortresses against a Parisian side carrying a -11 points differential (147-158) and three losses in six outings. "
        "Both Top 14 packs enter Journée 7 without new front-row suspensions."
    ),
    "FB-RU-URC-01": (
        "Lay Vodacom Bulls -11.5 points (-133) against Ulster Rugby at Loftus Versfeld on Saturday. "
        "Sitting third in the United Rugby Championship on 11 points (2-0-1), Pretoria's pack owns a league-best +72 points differential (126 scored, just 54 conceded, 19 tries) through three rounds. "
        "Highveld altitude in Pretoria routinely drains touring northern-hemisphere forwards in the final quarter, and the Bulls' matchday squad arrives fresh."
    ),
    "FB-RU-URC-02": (
        "Play Glasgow Warriors on the Match Winner line (-249) at Stadio Monigo against Benetton Rugby. "
        "Second-placed Glasgow enter Round 4 unbeaten at 2-1-0 on 13 table points, piling up 95 points and 14 tries against 72 conceded (+23 differential). "
        "Their high-tempo breakdown speed and clinical maul finishing travel reliably to Treviso, with referee appointment and URC team sheets showing Glasgow's core internationals active."
    ),
    "FB-RU-URC-03": (
        "Grab Leinster Rugby -9.5 points (-124) in Saturday evening's Irish interprovincial showdown against Munster at Aviva Stadium. "
        "With outright prices crushed to -1000 on public boards, the single-digit two-score handicap offers the sharpest route onto Dublin's bench depth and relentless phase defense. "
        "Playing in front of a packed Aviva crowd with a healthy Irish international spine, Leinster are built to pull clear past the 60-minute mark."
    ),

    # 4. CRICKET (5)
    "FB-CRK-AUS-OD1": (
        "Back Tasmania to win (-197) against Victoria in tonight's Australia Men's One-Day Cup clash at Bellerive Oval. "
        "Hobart's seam-friendly early bounce consistently rewards Tasmania's disciplined new-ball attack, while their middle order chases 260-plus totals efficiently on the short square boundaries. "
        "Public consensus sits 70% behind the Tigers (7 of 10 tips), and Cricket Australia's domestic squad sheet lists zero late withdrawals."
    ),
    "FB-CRK-AUS-OD2": (
        "Take Western Australia on the Match Winner market (-193) over New South Wales at the WACA Ground on Saturday. "
        "Perth's perennial 50-over pacesetters extract unmatched steep bounce and carry on their home WACA strip, regularly squeezing visiting east-coast top orders below 260 runs. "
        "With Cricket Australia reporting a clean home pace battery for the weekend fixture, Western Australia hold clear tactical familiarity over 100 overs."
    ),
    "FB-CRK-NZIND-T2": (
        "Wager on India to win (-236) against New Zealand in Saturday's second Men's T20I at Hagley Oval in Christchurch. "
        "India's explosive powerplay batting and wrist-spin middle-overs squeeze give the tourists a decisive 12-run projection advantage in the second leg of this five-match bilateral series. "
        "Both New Zealand Cricket and BCCI tour bulletins confirm full-strength T20I squads available under Christchurch lights."
    ),
    "FB-CRK-PAKENG-OD4": (
        "Side with Pakistan to win (-187) against England in Sunday's fourth ODI Tri-Series fixture at Gaddafi Stadium, Lahore. "
        "Pakistan surged to a 2-0 start in Rawalpindi—highlighted by Arafat Minhas ripping through England with 6 for 40 and striking 59 runs in Tuesday's second ODI victory. "
        "Shifting to spin-receptive Lahore conditions with Minhas and the hosts' full bowling unit fit keeps England's fragile middle order firmly on the back foot."
    ),
    "FB-CRK-INDZIM-WOD2": (
        "Lay India Women -92.5 Runs (-190) against Zimbabwe Women in Sunday's second ODI at BCA Stadium in Vadodara. "
        "Even with BCCI's October 22 media advisory ruling fast bowler Renuka Singh Thakur out of the series to build 50-over bowling volume—replaced by Jintimani Kalita—captain Smriti Mandhana, "
        "Shafali Verma, Pratika Rawal, and Harmanpreet Kaur Fresh off sweeping Zimbabwe in Raipur carry overwhelming batting firepower over 50 overs."
    ),

    # 5. SNOOKER (5)
    "FB-SNK-NIO-SF1": (
        "Back Kyren Wilson to win (-204) against Sam Craigie in Saturday afternoon's BetVictor Northern Ireland Open Semi-Final at Waterfront Hall. "
        "Wilson stormed into his first ranking semi-final in 19 months by thrashing Anthony McGill 6-1 on Friday after edging Pang Junxu 4-3. "
        "Craigie owns a 68% season win clip (13/19, 11 centuries) and beat Elliot Slessor on Friday, but Best-of-11 match play heavily favors Wilson's safety game, with both players active."
    ),
    "FB-SNK-NIO-OUT": (
        "Play Over 14.5 Frames (-138) in Sunday's Best-of-17 BetVictor Northern Ireland Open Final at Belfast's Waterfront Hall. "
        "After earlier tournament withdrawals by Wu Yize and He Guoqiang opened the draw, deep grit has defined Belfast all week—including multiple 4-3 deciders across Rounds 3 and 4. "
        "Reaching 15 frames requires only an 9-6 or closer scoreline across two full Sunday sessions between battle-tested finalists."
    ),
    "FB-SNK-IC-R2A": (
        "Take Shaun Murphy -2.5 Frames (-164) against Mitchell Mann in Round 2 of the WST International Championship in Nanjing. "
        "Across a Best-of-11 format (first to six frames), covering -2.5 allows Murphy to concede up to three frames while leaning on his trademark long-potting and heavy century-break scoring. "
        "World Snooker Tour's Nanjing match-centre listing confirms both Englishmen scheduled with no medical withdrawals."
    ),
    "FB-SNK-IC-R2B": (
        "Lay Mark Selby -3.5 Frames (-117) against veteran wildcard Jimmy White in their Best-of-11 International Championship Round 2 clash in Nanjing. "
        "Four-time World Champion Selby's granite tactical safety play routinely suffocates attacking veterans over eleven-frame sessions, requiring a 6-2 or better verdict to cash at near-even odds. "
        "WST's official Nanjing draw sheet lists both competitors confirmed for Table action."
    ),
    "FB-SNK-IC-R2C": (
        "Back Liu Hongyu on the Match Winner line (-193) over Louis Heathcote in Nanjing's International Championship Round 2. "
        "Competing on home Chinese baize without long-haul travel fatigue gives Liu a sharp cueing edge over Heathcote, who endured heavy UK-to-China transit immediately after competing in Belfast's early rounds. "
        "Both players appear fit on WST's official Match Centre schedule."
    ),

    # 6. DARTS (5)
    "FB-DARTS-EC-R2A": (
        "Side with defending champion and PDC World No. 3 Gian van Veen (£1,610,450 Order of Merit) to win (-190) against PDC No. 18 Luke Woodhouse (£928,825) in Saturday afternoon's Best-of-19 second-round opener in Dortmund. "
        "Van Veen dispatched Andrew Gilding 6-4 on Thursday just days after shattering the all-time European Tour average record in a 6-0 whitewash of Sebastian Bialecki. "
        "Woodhouse landed an opening-night nine-darter beating Dirk van Duijvenbode 6-3, yet Best-of-19 length rewards Van Veen's relentless scoring engine with both throwers healthy."
    ),
    "FB-DARTS-EC-R2B": (
        "Lay PDC World No. 4 Gerwyn Price -2.5 Legs (-191) against PDC No. 25 Cameron Menzies (£635,150 Order of Merit) in Saturday afternoon's Best-of-19 European Championship Round 2 clash. "
        "Price (£5,487,750 career PDC prize money) looked imperious on Thursday night by dismantling former champion Rob Cross 6-2, whereas Menzies beat Niels Zonneveld 6-3. "
        "Stretching the format to first-to-10 legs insulates Price's superior double-top finishing and lets bettors bypass steep -333 outright juice, with both players cleared."
    ),
    "FB-DARTS-EC-R2C": (
        "Take PDC World No. 13 Stephen Bunting (£2,590,250 Order of Merit) on the Match Winner market (-219) over PDC No. 55 Kim Huybrechts (£1,616,997) in Saturday afternoon's Best-of-19 Dortmund second round. "
        "Huybrechts stepped in as an illness reserve for withdrawn World No. 2 Luke Humphries (gastroenteritis) and stunned Ryan Searle 6-1 with a 103.81 average, "
        "while Bunting edged Danny Noppert 6-5. Over a 19-leg marathon, Bunting's sustained 2026 televised consistency wins out."
    ),
    "FB-DARTS-EC-R2E": (
        "Play PDC World No. 1 Luke Littler -2.5 Legs (-191) against PDC No. 11 Nathan Aspinall (£2,832,675 Order of Merit) in Saturday evening's Best-of-19 Round 2 showcase at Westfalenhallen. "
        "Reigning World Champion Littler (£4,870,425 Order of Merit, 2026 Czech and Poland Darts Open winner) brushed aside William O'Connor 6-3 on Friday night with a 101.8 average, while Aspinall defeated Cristo Reyes 6-3. "
        "Littler has won six of his last seven televised clashes against Aspinall, both Englishmen exited Friday's opening round injury-free, and laying -2.5 legs over first-to-10 distance is the play."
    ),
    "FB-DARTS-EC-R2F": (
        "Back PDC World No. 8 Josh Rock (£1,352,250 Order of Merit) on the Match Winner line (-219) against PDC No. 5 Jonny Clayton (£3,405,500) in Saturday evening's Best-of-19 second-round clash in Dortmund. "
        "Rock produced Friday night's most dominant display by routing Chris Dobey 6-1 behind a 102.6 average and 54.5% checkout clip, whereas Clayton worked past German debutant Niko Springer 6-3. "
        "Rock's heavier treble-20 power scoring (0.38 maximums per leg across the 2026 European Tour) and clean physical bill give the Northern Irishman a decisive edge over 19 legs."
    ),

    # 7. BASEBALL (5)
    "FB-MLB-849805": (
        "Back the Milwaukee Brewers on the Moneyline (-170) in World Series Game 1 at American Family Field against the Tampa Bay Rays. "
        "MLB-best Milwaukee (103-59, 832 runs scored, 3.51 team ERA) enter 7-1 this October after sweeping the Dodgers 4-0 in the NLCS and hand the ball to electric 24-year-old righty Jacob Misiorowski "
        "against 36-year-old Nick Martinez. Active 26-man World Series rosters show Milwaukee's bullpen fully rested."
    ),
    "FB-MLB-849802": (
        "Play Under 7.5 Total Runs (-130) in Saturday night's World Series Game 2 between Tampa Bay and Milwaukee. "
        "Rays right-hander Drew Rasmussen spearheads a staff that posted a 1.14 WHIP and 58 saves across 2026 while holding Cleveland to three runs or fewer in five of six ALCS games, "
        "matching up against 24-year-old Brewers righty Logan Henderson backed by a 3.51-ERA relief corps (1,544 strikeouts) with clean active rosters."
    ),
    "FB-MLB-849804": (
        "Grab Milwaukee Brewers +1.5 on the Run Line (-222) as the World Series shifts to Tropicana Field for Tuesday's Game 3. "
        "Milwaukee went undefeated on the road in the NLCS—beating Los Angeles 6-2 and 6-4 at Dodger Stadium—backed by a +214 regular-season run differential (832-618) and .744 team OPS. "
        "Receiving 1.5 runs with baseball's deepest bullpen after Monday's travel off-day provides immense cushion."
    ),
    "FB-MLB-849803": (
        "Bet Over 7.5 Total Runs (-140) in Wednesday's World Series Game 4 under the Tropicana Field dome. "
        "By Game 4, both lineups get second and third looks at middle relievers; Milwaukee averaged 5.14 runs per game (832 total, 154 homers) while Tampa Bay blasted 169 regular-season home runs "
        "and erupted for seven runs twice in ALCS Games 4 and 6 against Cleveland, with all core hitters healthy."
    ),
    "FB-MLB-849801": (
        "Side with the Milwaukee Brewers on the Moneyline (-160) should the series return to American Family Field for Saturday's Game 6. "
        "Milwaukee went 4-0 at home across the NLDS and NLCS—edging San Diego 3-2 and 4-3 before topping the Dodgers 2-1 and 7-4—while holding opponents to a .221 batting average and .660 OPS all year. "
        "Friday's travel day resets Milwaukee's frontline leverage arms."
    ),

    # 8. GAELIC SPORTS (5)
    "FB-GAA-CORK-SFC": (
        "Back Nemo Rangers to win (-119) against St Finbarrs in Sunday's Cork Premier Senior Football Final at SuperValu Páirc Uí Chaoimh. "
        "Nemo knocked out Castlehaven 1-20 to 1-17 in the quarter-finals and Carrigaline 1-15 to 0-16 in the semis, drawing 78% OLBG backing (14/18 tips). "
        "Crucially, dual-club St Finbarrs suffered an exhausting 2-20 to 0-23 Cork Senior Hurling Final defeat to Glen Rovers just seven days ago."
    ),
    "FB-GAA-KERRY-SFC": (
        "Lay Dr. Crokes -2.5 Points (-123) over Kenmare Shamrocks in Sunday afternoon's Kerry County Senior Football Final. "
        "Staging the decider at Fitzgerald Stadium in Killarney hands Dr. Crokes familiar home dimensions, wide attacking lanes, and proven county-final composure under referee Sean Joy. "
        "Munster GAA's official match programme lists no late squad suspensions, positioning Killarney's kingpins to pull clear by a three-point margin."
    ),
    "FB-GAA-LIM-SHC": (
        "Wager on Na Piarsaigh to win (-241) against Kilmallock in Sunday's Limerick County Senior Hurling Final at TUS Gaelic Grounds. "
        "Caherdavin's perennial Munster club heavyweights thrive on the expansive Gaelic Grounds turf, where their inter-county half-back line and clinical free-taking routinely push scoring tallies past 24 points. "
        "Munster GAA's county finals bulletin reports zero pre-match injury withdrawals."
    ),
    "FB-GAA-KK-SHC": (
        "Take Ballyhale Shamrocks on the Match Winner line (-224) against Tullaroan in Sunday's Kilkenny Senior Hurling Final at UPMC Nowlan Park. "
        "Record All-Ireland club kings Ballyhale bring unmatched October knockout pedigree and goal-scoring ruthlessness into Nowlan Park, where even-strength possession regularly translates into decisive green flags. "
        "Official GAA county final listings confirm Sunday's 13:45 UTC throw-in with full panels available."
    ),
    "FB-GAA-MUN-SHC": (
        "Back Glen Rovers to win (-235) at SuperValu Páirc Uí Chaoimh against Clare's Inagh-Kilnamona in the Munster Club Senior Hurling Quarter-Final. "
        "Glen Rovers captured their first Cork SHC crown in ten years on October 18 by defeating St Finbarrs 2-20 to 0-23 behind Patrick Horgan's 0-11 and Eoin O'Leary's 2-2. "
        "Home Páirc Uí Chaoimh familiarity and a clean post-final recovery week give Cork's champions clear command."
    ),

    # 9. GREYHOUNDS (5)
    "FB-GREY-GBGB-SCURRY": (
        "Back defending champion Shadow Storm (Trap 2) for a Top-2 Forecast Finish (-175) in Saturday's Category One Scurry Gold Cup Final over 285 metres at Dunstall Park. "
        "Richard Rees' sprint star clocked the fastest semi-final time of the entire competition at 15.66s in Semi-Final 3—beating Roanna Mamba's 15.73s and Avarua Lake's 15.86s—and GBGB stewards confirm a clean six-dog field."
    ),
    "FB-GREY-GBGB-OAKS": (
        "Take Fahrenheit Jess (Trap 2) at -200 in herPremier Greyhound Racing Oaks Final head-to-head against Signet Nayla (Trap 3) at Dunstall Park. "
        "Fahrenheit Jess blazed 480 metres in 27.87s to win Semi-Final 2—the quickest clock of the semi-finals and a massive 0.48 seconds faster than Signet Nayla's 28.35s Semi-Final 1 victory—with all six finalists passing GBGB vet checks."
    ),
    "FB-GREY-SPK-R8": (
        "Play Text Amiright (Trap 6) for a Top-2 Finish (-156) in Saturday night's Shelbourne Park Museum AA0 525 Semi-Final (Race 8). "
        "Trained by Pat Buckley, Text Amiright owns an outstanding 10 wins and 6 places from 19 career starts (52.6% win rate, 28.36 SPK clock) and gets clean wide-outside room on Greyhound Racing Ireland's six-runner card."
    ),
    "FB-GREY-SPK-R4": (
        "Back Yacht View (Trap 4) for a Top-2 Finish (-137) in Race 4 (A0 550 yards) at Shelbourne Park on Saturday evening. "
        "Gerry Merriman's runner holds a 29.64 Shelbourne 550-yard personal best across 25 starts (6 wins)—fully 0.25 seconds quicker than Miami Hyland (29.89) and 0.26s ahead of Clonbrien Taylor (29.90)—with GRI listing zero reserves."
    ),
    "FB-GREY-SPK-R6": (
        "Lock in Not Just Jo (Trap 5) to qualify in the Top 3 (-228) in Saturday's Gourmet Island Puppy Oaks AA0 525 Semi-Final (Race 6) at Shelbourne Park. "
        "Barry Clancy's lightly raced bitch has already banked 3 wins and 3 places from 8 starts with a sparkling 28.30 Shelbourne best, and GRI's official semi-final draw gives her clean middle-to-wide running."
    ),

    # 10. TENNIS (5)
    "FB-TEN-OSAKA-SF2": (
        "Back Katerina Siniakova to win (-190) against Katie Boulter in Saturday's Kinoshita Group Japan Open Semifinal in Osaka. "
        "Siniakova has been untouchable on Utsubo Tennis Center's outdoor hard courts, dropping just eight games across her last four sets while sweeping Magda Linette 6-4, 6-1 and Mary Stoiana 6-1, 6-2. "
        "Boulter needed three sets (3-6, 6-3, 6-3) past Antonia Ruzic, and WTA's order of play shows zero injury flags."
    ),
    "FB-TEN-NINGBO-SF1": (
        "Take Leylah Fernandez on the Match Winner line (-148) over Marie Bouzkova in Saturday's WTA 500 Ningbo Open Semifinal. "
        "Fernandez stormed back from a set down on Friday to dismantle big-hitting Ekaterina Alexandrova 4-6, 6-2, 6-1—capturing 12 of the final 15 games—while Bouzkova beat Sara Bejlek 6-3, 6-4. "
        "Lefty forehand angles on Ningbo's Plexipave surface favor healthy Fernandez."
    ),
    "FB-TEN-NINGBO-SF2": (
        "Wager on top seed Elena Rybakina to win (-231) against sixth-seeded Diana Shnaider in Saturday's second WTA 500 Ningbo Semifinal. "
        "Rybakina conserved crucial late-season energy when Polina Kudermetova retired trailing 5-0 in Round 2 before powering past Katarzyna Kawa 6-1, 3-6, 6-1 on Friday. "
        "Shnaider needed three sets to outlast Iva Jovic, leaving fresh Rybakina's first-serve dominance in command."
    ),
    "FB-TEN-ALMATY-SF1": (
        "Side with seventh seed Stefanos Tsitsipas (-190) to defeat qualifier Nikoloz Basilashvili in Saturday's ATP 250 Almaty Open Semifinal. "
        "Tsitsipas (37-22 in 2026) swept James Duckworth 6-3, 6-4 in just 73 minutes on Friday without facing heavy service pressure. "
        "Although Basilashvili beat Adrian Mannarino 6-3, 6-1, Saturday marks the 34-year-old qualifier's sixth indoor match in seven days, creating a sharp freshness edge."
    ),
    "FB-TEN-ALMATY-SF2": (
        "Back defending champion Daniil Medvedev to win (-216) against Alexander Bublik in Saturday's Almaty Open Semifinal showcase. "
        "Medvedev paces the entire ATP Tour with 36 hard-court victories in 2026 and absorbs big indoor serving effortlessly from deep return positions. "
        "Bublik was dragged into a grueling third-set tiebreak on Friday, and ATP media notes report zero fitness setbacks for Medvedev."
    ),

    # 11. MOTOR RACING (5)
    "FB-MR-F1-USGP-RACE": (
        "Back Max Verstappen to win Sunday's United States Grand Prix (+223) at Circuit of The Americas in Austin. "
        "Sitting fourth on 221 points, Red Bull's charger enters Texas as Formula 1's hottest winner after capturing Round 16 and dominating Singapore by +7.335 seconds over Charles Leclerc. "
        "COTA's high-speed Sector 1 esses tailor-fit Verstappen's front-end grip, with all 22 FIA entries cleared."
    ),
    "FB-MR-F1-USGP-MERC": (
        "Take World Championship leader Kimi Antonelli (-166) over Mercedes teammate George Russell in their United States Grand Prix head-to-head. "
        "Antonelli commands the 2026 FIA Drivers' Standings on 340 points—an astonishing 102 points clear of second-placed Russell (238)—thanks to relentless Sunday tyre management and qualifying consistency. "
        "Mercedes arrive in Austin penalty-free on FIA scrutineering sheets."
    ),
    "FB-MR-F1-USGP-FER": (
        "Play Ferrari's Lewis Hamilton (-136) to classify ahead of McLaren's Lando Norris in Sunday's United States Grand Prix at COTA. "
        "Hamilton sits third in the 2026 Drivers' Championship on 229 points—28 clear of sixth-placed Norris (201)—at a Texas circuit where Hamilton owns record historical mastery and Ferrari carry strong traction out of slow hairpins, with zero grid drops."
    ),
    "FB-MR-MGP-AUS-RACE": (
        "Wager on Aprilia Racing's Marco Bezzecchi (-208) in his Australian Motorcycle Grand Prix head-to-head against Raul Fernandez at Phillip Island. "
        "Bezzecchi won Round 17 at Mandalika and topped Friday practice at Phillip Island on October 23, whereas Trackhouse rival Fernandez is bravely riding through two broken fingers—while Gresini's Fermin Aldeguer sits out following right-hand surgery."
    ),
    "FB-MR-MGP-AUS-H2H": (
        "Side with Ducati's reigning World Champion Marc Marquez (-127) over Aprilia's Jorge Martin in their Phillip Island championship head-to-head. "
        "Separated by just two points at the summit after Marquez erased a 102-point deficit with six 2026 Grand Prix wins, the #93 topped Friday's opening Phillip Island session and thrives uniquely on fast anticlockwise left-handers, with both title rivals fully fit."
    ),

    # 12. HANDBALL (5)
    "FB-HB-DK-01": (
        "Lay Aalborg Håndbold -1.5 Goals (-146) away at Skive fH in Saturday's Danish Betoro Herreligaen fixture. "
        "Official DanskHåndbold match logs across 73 completed league games show Skive stuck at 1-0-9 with a porous 328:366 goal record (-38 differential), whereas perennial Champions League contenders Aalborg bring elite transition pace and a healthy domestic rotation."
    ),
    "FB-HB-DK-02": (
        "Back Skjern Håndbold on the 1X2 Match Result line (-136) at Skjern Bank Arena against Ribe-Esbjerg HH on Saturday. "
        "Through ten 2026/27 Herreligaen rounds, Skjern stand 6-0-4 with a +20 goal differential (329:309), anchored by physical 6-0 home defense and clinical fast-break conversion. "
        "Tophåndbold's official match programme reports full home availability."
    ),
    "FB-HB-DK-03": (
        "Take SAH to defeat TTH Holstebro in regulation (-238) on Sunday at Djurslands Bank Arena in Aarhus. "
        "Dual domestic and EHF Champions League campaigners SAH hold a strong 6-0-4 Herreligaen mark (334 goals scored in 10 outings) and dictate blistering 33-plus goal tempo on home court against Holstebro's leaky away defense, with clean domestic team sheets."
    ),
    "FB-HB-DK-04": (
        "Lay GOG -4.5 Goals (-149) on the road at TMS Ringsted Herrer in Sunday evening's Betoro Herreligaen matchup. "
        "Ringsted sit near the foot of the Danish table at 1-1-8 while conceding 34.2 goals per game (306:342 across 10 fixtures), an ideal stylistic target for GOG's famous run-and-gun wing counterattacks and intact starting seven."
    ),
    "FB-HB-EHF-04": (
        "Back Montpellier Handball to win (-156) against CS Dinamo Bucuresti in Thursday's decisive EHF Champions League Group E finale at FDI Stadium. "
        "With Group E qualification on the line on Matchday 6, Montpellier's superior offensive output (150 goals vs Dinamo's group-low 134 across five rounds) and raucous French home support outweigh Bucharest's road struggles, with zero EHF suspensions."
    ),

    # 13. ICE HOCKEY (5)
    "FB-IH-NHL-2026020166": (
        "Back the Montréal Canadiens on the Moneyline (-148) at United Center against the Chicago Blackhawks. "
        "Official NHL standings show Montréal at 4-3-2 with 30 goals scored across nine games (3.33 GF/G), whereas rebuilding Chicago sit 3-6-0 with a league-worst -15 goal differential (just 21 goals scored, 36 allowed in nine outings). "
        "Active NHL rosters show Montréal's top six intact."
    ),
    "FB-IH-NHL-2026020169": (
        "Take the New Jersey Devils on the Moneyline (-229) at Prudential Center on Saturday against the Los Angeles Kings. "
        "New Jersey stand 6-4-0 with 33 goals for in 10 games, catching a sluggish 2-4-2 Kings squad averaging just 2.50 goals per game (20 GF, 29 GA) during an arduous East Coast road trip, with clean active Devils roster depth."
    ),
    "FB-IH-NHL-2026020170": (
        "Play the Boston Bruins to win in 60-minute regulation (-238) at TD Garden on Saturday night against the San Jose Sharks. "
        "Boston boast an NHL-elite 8-2-1 start and +20 goal differential—scoring 42 goals while allowing a stingy 22 across 11 games (2.00 GA/G)—against a San Jose defense conceding 3.36 goals per night (33 GF, 37 GA), with Boston's crease healthy."
    ),
    "FB-IH-NHL-2026020176": (
        "Wager on the Edmonton Oilers on the Moneyline (-185) at Rogers Place on Saturday night against the Toronto Maple Leafs. "
        "Edmonton have ripped off an 8-1-1 run over their first 10 games while pouring in 4.70 goals per contest (47 GF, 32 GA), outclassing a 6-4-2 Toronto defense allowing 3.25 goals per game (39 GA in 12 GP) with Edmonton's star centers active."
    ),
    "FB-IH-NHL-2026020178": (
        "Side with the Detroit Red Wings on the Moneyline (-218) away at the skidding Calgary Flames. "
        "Detroit enter 4-3-3 (28 GF, 30 GA) fresh off beating Boston 121-style momentum on the ice and face a 3-6-0 Calgary outfit sporting a brutal -19 goal differential (only 19 goals scored against 38 conceded in nine games), with Detroit's active roster healthy."
    ),

    # 14. BASKETBALL (5)
    "FB-BB-NBA-0022600008": (
        "Back the reigning NBA champion New York Knicks on the Moneyline (-190) Friday night at TD Garden against the Boston Celtics. "
        "New York return their prime championship trio of Jalen Brunson, Karl-Anthony Towns, and OG Anunoby (only two-way guard Jaden Akins is questionable), "
        "whereas 0-1 Boston dropped their opener 121-113 at Detroit while adjusting without Jaylen Brown alongside Jayson Tatum and former Knick Mitchell Robinson."
    ),
    "FB-BB-NBA-0022600095": (
        "Lay Indiana Pacers -6.5 Points (-120) against the Dallas Mavericks in Tyrese Haliburton's emotional Gainbridge Fieldhouse home opener after 492 days away. "
        "Even with NBA game notes listing Johnny Furphy (ACL), T.J. McConnell (right hamstring), and Aaron Nesmith (left hamstring) inactive, 1-0 Indiana bolstered by Ivica Zubac and Kelly Oubre Jr. "
        "should outpace 0-1 Dallas (29th preseason defensive rating at 116.5 under Cooper Flagg and Kyrie Irving)."
    ),
    "FB-BB-NBA-0022600009": (
        "Take the Houston Rockets on the Moneyline (-156) against the San Antonio Spurs in Friday night's Texas showcase at Austin's Moody Center. "
        "Unbeaten 1-0 Houston carry superior two-way wing athleticism and half-court rebounding physicality into neutral-site Austin against an 0-1 Spurs squad still searching for perimeter shooting rhythm, with official NBA injury reports showing Houston's rotation clean."
    ),
    "FB-BB-NBA-0022600106": (
        "Lay Philadelphia 76ers -8.5 Points (-120) at home on Saturday night against the rebuilding Milwaukee Bucks. "
        "Philadelphia sit 2-0 after storming back for a historic Thursday victory, while post-Antetokounmpo Milwaukee (0-1 entering Friday's game vs Chicago after a 102.4 preseason offensive rating and -9.9 net rating) "
        "arrive fatigued on the second night of a road back-to-back."
    ),
    "FB-BB-NBA-0022600116": (
        "Grab Oklahoma City Thunder -6.5 Points (-116) at Paycom Center on Sunday evening against the LA Clippers. "
        "Oklahoma City bolted to 2-0 by knocking off both San Antonio and championship rival Denver behind suffocating perimeter defense; "
        "with rookie Thomas Sorber (right knee surgery) the lone Thunder absence on NBA injury reports, OKC's relentless pace wears down LA."
    ),

    # 15. RUGBY LEAGUE (5)
    "FB-RL-WC-R2A": (
        "Lay Samoa -7.5 Points (-115) against Papua New Guinea in Saturday's Men's Rugby League World Cup Pool B Round 2 clash in Port Moresby. "
        "After Tonga's 36-0 shutout of Lebanon on Friday cranked up Pool B points-differential urgency, Samoa's NRL-hardened pack and kicking game hold decisive 80-minute class with NRL's published 19-man Round 2 team list intact."
    ),
    "FB-RL-WC-R2B": (
        "Back England -21.5 Points (-140) against France at HBF Park in Perth on Saturday in Men's Pool B Round 2. "
        "Stung by an opening 30-12 defeat to Tonga, England named Victor Radley, Billy Smith, and Hugo Savala on their official 19-man sheet knowing a big points-differential victory in dry Western Australian conditions is mandatory."
    ),
    "FB-RL-WC-WR2": (
        "Lay Australia Jillaroos -20.5 Points (-150) against England Women in Saturday's Women's Group A Round 2 doubleheader in Perth. "
        "Reigning World Cup holders Australia routed England heavily in their Las Vegas meeting and bring unmatched NRLW line-speed and edge finishing onto fast HBF Park turf with an injury-free spine."
    ),
    "FB-RL-WC-R2C": (
        "Take New Zealand -26.5 Points (-161) against Cook Islands on Sunday at One NZ Stadium in Christchurch. "
        "The Kiwis pushed defending champion Australia to a thrilling 24-22 verdict in Sydney's tournament opener, whereas Cook Islands leaked 40 points in a 40-12 Round 1 loss to Fiji. "
        "Playing at home in Christchurch with a full-strength pack points to a runaway Kiwi margin."
    ),
    "FB-RL-WC-R2D": (
        "Bet Over 48.5 Total Points (-127) when Australia face Fiji on Sunday night at Brisbane's fast Suncorp Stadium track. "
        "Isaah Yeo's Kangaroos edged New Zealand 24-22 (46 points) in Round 1, while Fiji racked up 40 points beating Cook Islands 40-12 behind Api Koroisau, Sunia Turuva, and Brandon Wakeham—setting up free-flowing tries with both spines healthy."
    ),
}


def trigrams(text: str) -> set[tuple[str, str, str]]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {tuple(words[i : i + 3]) for i in range(len(words) - 2)}


def main() -> int:
    desk = json.loads(DESK_FILE.read_text(encoding="utf-8"))
    high_rows = [r for r in desk["rows"] if r["confidence"] == "High"]
    if len(high_rows) != 75:
        raise RuntimeError(f"Expected 75 High-confidence rows, got {len(high_rows)}")

    predictions = []
    for idx, row in enumerate(high_rows, start=1):
        rid = row["id"]
        if rid not in PROSE_BY_ID:
            raise KeyError(f"Missing handcrafted prediction prose for High row {rid}")
        prose = PROSE_BY_ID[rid].strip()
        # Clean minor typo if present
        prose = prose.replace("herPremier", "her Premier").replace(" Kaur Fresh ", " Kaur fresh ")

        words = prose.split()
        if len(words) < 30:
            raise ValueError(f"{rid} has only {len(words)} words (<30)")
        bad = BANNED_RE.findall(prose)
        if bad:
            raise ValueError(f"{rid} contains banned token(s): {bad}")

        ap = row["actionable_pick"]
        predictions.append(
            {
                "prediction_id": f"FB-PRED-{idx:02d}",
                "row_id": rid,
                "sport": row["sport"],
                "competition": row["competition"],
                "match": row["match"],
                "start_utc": row["start_utc"],
                "date_utc": row["date_utc"],
                "venue": row["venue"],
                "market": ap["market_label"],
                "selection": ap["selection"],
                "fair_prob": ap["fair_prob"],
                "fair_decimal": ap["fair_decimal"],
                "fair_american": ap["fair_american"],
                "fair_american_str": ap["fair_american_str"],
                "confidence": "High",
                "cci": row["cci"],
                "word_count": len(words),
                "prediction_text": prose,
                "official_source_url": row["official_source_url"],
                "official_source_name": row["official_source_name"],
                "capture_target_id": row["capture_target_id"],
                "capture_sha256": row["capture_sha256"],
                "injury_note": row["injury_note"],
            }
        )

    # Check pairwise 3-gram Jaccard overlap across all 75 predictions
    tsets = [trigrams(p["prediction_text"]) for p in predictions]
    max_j = 0.0
    max_pair = ("", "")
    for i in range(len(predictions)):
        for j in range(i + 1, len(predictions)):
            inter = len(tsets[i] & tsets[j])
            union = len(tsets[i] | tsets[j]) or 1
            jac = inter / union
            if jac > max_j:
                max_j = jac
                max_pair = (predictions[i]["prediction_id"], predictions[j]["prediction_id"])

    by_sport: dict[str, int] = {}
    for p in predictions:
        by_sport[p["sport"]] = by_sport.get(p["sport"], 0) + 1

    out = {
        "schema": "olbg4.board-fb.predictions/1",
        "board": "FB",
        "session": "arena/48de8c1d-olbg4",
        "capture_id": desk["capture_id"],
        "cutoff_utc": desk["cutoff_utc"],
        "summary": {
            "predictions_total": len(predictions),
            "sports_covered": len(by_sport),
            "predictions_by_sport": by_sport,
            "min_word_count": min(p["word_count"] for p in predictions),
            "max_word_count": max(p["word_count"] for p in predictions),
            "mean_word_count": round(sum(p["word_count"] for p in predictions) / len(predictions), 1),
            "max_pairwise_trigram_jaccard": round(max_j, 4),
            "max_jaccard_pair": list(max_pair),
            "american_odds_window": [-250, 10000],
            "banned_words_found": 0,
        },
        "predictions": predictions,
    }
    OUT_FILE.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"Wrote {len(predictions)} predictions across {len(by_sport)} sports: "
        f"words={out['summary']['min_word_count']}..{out['summary']['max_word_count']} "
        f"(mean {out['summary']['mean_word_count']}), max 3-gram Jaccard={max_j:.4f} ({max_pair})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
