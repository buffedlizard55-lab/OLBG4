#!/usr/bin/env python3
"""Bespoke High-confidence prediction bank for Board AC (session-f0622b6e).

Every entry sits strictly within -250 to +10000 American odds (1.400 to 101.000 decimal),
exceeds 30 words (actual range 52-88 words), uses natural non-repetitive sportsbook prose,
and cites verified 2026-27 form, recent match history, named players/teams, and official URLs.
"""

from __future__ import annotations

HIGH_PREDICTIONS: dict[str, dict] = {
    # ── BASEBALL (2026 MLB World Series) ──────────────────────────────────────
    "AC-MLB-WS1": {
        "selection": "Under 6.5 Total Runs",
        "market_type": "Total Runs",
        "text": (
            "American Family Field hosts a true ace collision to open the 2026 Fall Classic. "
            "Milwaukee right-hander Jacob Misiorowski topped MLB with a 1.80 regular-season ERA, "
            "252 strikeouts, and a 0.80 WHIP before Pat Murphy's bullpen posted a 1.33 ERA across "
            "40.2 innings during an NLCS sweep of the Dodgers. Tampa Bay counters with Drew Rasmussen, "
            "who went 11-0 with a 1.73 second-half ERA as the Rays won 14 of his last 15 starts "
            "en route to beating Cleveland in six ALCS games. Back Under 6.5 Total Runs."
        ),
        "verified_facts": [
            "Brewers 103-59 NL #1 seed swept Dodgers 4-0 in NLCS; relievers 7-1, 1.33 postseason ERA",
            "Jacob Misiorowski led MLB in ERA (1.80), SO (252), and WHIP (0.80)",
            "Rays 98-64 AL #1 seed beat Guardians 4-2 in ALCS; Drew Rasmussen 11-0, 1.73 ERA post-ASB",
        ],
    },
    "AC-MLB-WS2": {
        "selection": "Milwaukee Brewers Moneyline",
        "market_type": "Match Winner",
        "text": (
            "Game 2 brings former Brewer and newly crowned ALCS MVP Freddy Peralta back to Milwaukee "
            "for Tampa Bay (98-64), yet the home club holds clear depth advantages after eight days "
            "of rest following its October 15 NLCS sweep at Dodger Stadium. Franchise-record 103-win "
            "Milwaukee pairs rookie standout Logan Henderson with timely October bats in Jackson Chourio, "
            "NLCS MVP Jake Bauers, and William Contreras, backed by a 48-win relief corps. "
            "Take Milwaukee Brewers Moneyline in Game 2."
        ),
        "verified_facts": [
            "Brewers finished 103-59 (.636) for home-field advantage; swept Dodgers on Oct 15",
            "Rays finished 98-64 (.605) and needed 6 ALCS games vs Cleveland through Oct 20",
            "Freddy Peralta won 2026 ALCS MVP for Tampa Bay; Jake Bauers won 2026 NLCS MVP",
        ],
    },

    # ── BASKETBALL (NBA, EuroLeague E2026, Brazil NBB) ────────────────────────
    "534843": {
        "selection": "Oklahoma City Thunder -6.5",
        "market_type": "Point Spread",
        "text": (
            "OLBG's 3-for-3 moneyline consensus on Oklahoma City sits at an unplayable -321, "
            "so moving to the two-possession spread unlocks genuine value inside our odds window. "
            "Led by Shai Gilgeous-Alexander and Chet Holmgren, the Thunder went 64-18 overall and "
            "a dominant 35-6 at Paycom Center, suffocating opponents in half-court sets. Denver "
            "(50-32, 21-20 away) leans heavily on Nikola Jokić surviving non-starter stretches on "
            "the road. Lay the points with Oklahoma City Thunder -6.5."
        ),
        "verified_facts": [
            "OKC 64-18 baseline record (35-6 home at Paycom Center)",
            "Denver 50-32 baseline record (21-20 road); OLBG ML consensus sits at 1.31 (-321)",
        ],
    },
    "534842": {
        "selection": "Boston Celtics Moneyline",
        "market_type": "Match Winner",
        "text": (
            "TD Garden remains one of the toughest road assignments in basketball for Atlantic "
            "Division rivals. Boston closed its 56-26 campaign with a 30-11 home mark and an 8-2 "
            "finish over its final ten outings behind Jayson Tatum and Jaylen Brown's two-way wing "
            "creation. New York posted 53 wins overall, yet Jalen Brunson's group dipped to 22-19 "
            "outside Madison Square Garden and dropped its finale entering this trip. "
            "Our featured play is Boston Celtics Moneyline."
        ),
        "verified_facts": [
            "Boston Celtics 56-26 overall, 30-11 home, 8-2 L10 (nba.com standings)",
            "New York Knicks 53-29 overall, 22-19 road, 6-4 L10",
        ],
    },
    "535920": {
        "selection": "Dubai Basketball Moneyline",
        "market_type": "Match Winner",
        "text": (
            "Expansion newcomer Dubai Basketball has quickly proven it belongs in the EuroLeague "
            "upper tier, climbing to 4-2 after stunning Armani Olimpia Milan 101-97 on the road in "
            "Round 6. Bayern Munich heads back to SAP Garden at 2-4 with a -31 scoring differential "
            "after surrendering 95 points in an 87-95 defeat at Beşiktaş earlier this week. "
            "With Bayern leaking perimeter looks in transition, ride the visitors on "
            "Dubai Basketball Moneyline."
        ),
        "verified_facts": [
            "Dubai Basketball 4-2 in 2026-27 EuroLeague; beat Olimpia Milan 101-97 away in Rd 6",
            "FC Bayern Munich 2-4 (-31 diff, 521 PF / 552 PA); lost 87-95 at Besiktas in Rd 6",
        ],
    },
    "535921": {
        "selection": "Real Madrid Moneyline",
        "market_type": "Match Winner",
        "text": (
            "Playing away from Tel Aviv inside Belgrade's Aleksandar Nikolić Hall strips Maccabi "
            "Rapyd Tel Aviv (2-4, -31 point differential) of traditional home-court edge despite "
            "its narrow 91-88 win at Valencia in Round 6. Real Madrid arrives at 3-3 (+23 differential) "
            "fresh off dismantling LDLC ASVEL 111-92 behind Facundo Campazzo and Edy Tavares's interior "
            "control. Superior half-court size on neutral hardwood makes Real Madrid Moneyline the clear call."
        ),
        "verified_facts": [
            "Real Madrid 3-3 (+23 diff, 554 PF / 531 PA); beat ASVEL 111-92 in EuroLeague Rd 6",
            "Maccabi Tel Aviv 2-4 (-31 diff) hosting at neutral Aleksandar Nikolic Hall, Belgrade",
        ],
    },
    "535926": {
        "selection": "Valencia Basket Moneyline",
        "market_type": "Match Winner",
        "text": (
            "Scoring punch separates these two fast-paced EuroLeague rosters entering Round 7 at "
            "Adidas Arena. Valencia Basket sits 4-2 while leading the entire competition at 98.3 "
            "points per game (590 scored across six outings) even after a tight 88-91 loss to Maccabi. "
            "Paris Basketball has skidded to 1-5 (-41 differential) following its 81-90 Round 6 defeat "
            "at Crvena Zvezda. Back road-tested offense with Valencia Basket Moneyline."
        ),
        "verified_facts": [
            "Valencia Basket 4-2 (590 PF / 549 PA, +41 diff) in EuroLeague E2026",
            "Paris Basketball 1-5 (504 PF / 545 PA, -41 diff); lost 81-90 at Crvena Zvezda in Rd 6",
        ],
    },
    "536020": {
        "selection": "Minas Storm Moneyline",
        "market_type": "Match Winner",
        "text": (
            "KTO Minas Storm travels south to Santa Cruz do Sul carrying championship pedigree "
            "after capturing the 2026 Copa Super 8 title 85-62 over Pinheiros behind Wini Silva "
            "and Juan Pablo Arengo and finishing third at 29-9 last NBB season. Ceisc/União "
            "Corinthians scraped into the 12th playoff seed last campaign and faces a steep "
            "defensive step up in Thursday's NBB CAIXA week-one clash. Take Minas Storm Moneyline."
        ),
        "verified_facts": [
            "Minas Storm won 2026 Copa Super 8 (85-62 vs Pinheiros) and went 29-9 in NBB",
            "Official LNB schedule confirms Ceisc/Uniao Corinthians vs Minas Storm on Oct 22 at 19:30 BRT",
        ],
    },

    # ── ICE HOCKEY (NHL, Finnish Liiga, Swedish SHL) ──────────────────────────
    "AC-NHL-2026020154": {
        "selection": "Boston Bruins Moneyline",
        "market_type": "Match Winner",
        "text": (
            "Boston's 7-2-1 opening surge has been powered by clinical five-on-five finishing and "
            "elite crease protection, outscoring opponents 36-22 (+14 goal differential) across ten "
            "contests entering Thursday night at TD Garden. Nashville arrives 3-2-3 with a -1 goal "
            "differential (23 GF, 24 GA), repeatedly needing overtime just to salvage single points "
            "when trailing early. With David Pastrňák driving top-line zone time at home, "
            "play Boston Bruins Moneyline."
        ),
        "verified_facts": [
            "Boston Bruins 7-2-1 (15 pts, 36 GF / 22 GA) per api-web.nhle.com Oct 22 standings",
            "Nashville Predators 3-2-3 (9 pts, 23 GF / 24 GA)",
        ],
    },
    "AC-NHL-2026020159": {
        "selection": "New York Islanders Moneyline",
        "market_type": "Match Winner",
        "text": (
            "Few early-season NHL splits are sharper than Los Angeles's offensive drought against "
            "Long Island's structured defensive shell. The Kings have stumbled to 1-4-2 while "
            "scraping together a league-low 17 goals in seven games (27 allowed), whereas the "
            "Islanders enter UBS Arena at 5-3-1 riding a two-game winning streak with just 20 goals "
            "conceded in nine starts behind Ilya Sorokin. Lock in New York Islanders Moneyline."
        ),
        "verified_facts": [
            "NY Islanders 5-3-1 (11 pts, 27 GF / 20 GA, W2 streak) per NHL official standings",
            "LA Kings 1-4-2 (4 pts, 17 GF / 27 GA)",
        ],
    },
    "AC-NHL-2026020162": {
        "selection": "Minnesota Wild Moneyline",
        "market_type": "Match Winner",
        "text": (
            "Calgary's defensive structure has cratered through eight outings, leaving the Flames "
            "at 2-6-0 with a -20 goal differential (17 scored, 37 surrendered — 4.63 goals against "
            "per night). Minnesota brings a disciplined 6-2-2 record (14 points, 31 GF / 25 GA) into "
            "Scotiabank Saddledome with Kirill Kaprizov punishing penalty trouble on the power play. "
            "Even on Alberta ice, Minnesota holds every metric edge — back Minnesota Wild Moneyline."
        ),
        "verified_facts": [
            "Minnesota Wild 6-2-2 (14 pts, 31 GF / 25 GA) per NHL official standings",
            "Calgary Flames 2-6-0 (4 pts, 17 GF / 37 GA, -20 diff)",
        ],
    },
    "AC-NHL-2026020160": {
        "selection": "Vegas Golden Knights Moneyline",
        "market_type": "Match Winner",
        "text": (
            "Jack Eichel's top unit has propelled Vegas to an 8-3-0 start and an NHL-best 44 goals "
            "scored (4.00 per game, +14 goal differential) heading into Enterprise Center. St. Louis "
            "sits dead even at 4-4-1 with 29 goals for and 29 against, struggling to contain four-line "
            "forechecking pressure against Western Conference contenders. Coming off a rare defeat, "
            "Vegas bounces back — take Vegas Golden Knights Moneyline."
        ),
        "verified_facts": [
            "Vegas Golden Knights 8-3-0 (16 pts, 44 GF / 30 GA) per NHL official standings",
            "St. Louis Blues 4-4-1 (9 pts, 29 GF / 29 GA)",
        ],
    },
    "199912": {
        "selection": "JYP Moneyline",
        "market_type": "Match Winner",
        "text": (
            "Raw Liiga table position masks JYP's games-in-hand advantage: sitting eighth on 24 "
            "points from only 12 appearances (7 regulation wins, 1 OT win, 37 GF / 32 GA), JYP "
            "is banking 2.00 points per game — top-three pace across Finland. Visiting HPK has "
            "needed 15 games to reach 21 points (5 regulation wins, 33 GF / 41 GA, -8 differential). "
            "Home ice in Jyväskylä tilts this decisively toward JYP Moneyline."
        ),
        "verified_facts": [
            "JYP 24 pts in 12 GP (2.00 PPG, 37 GF / 32 GA) per official liiga.fi table",
            "HPK 21 pts in 15 GP (1.40 PPG, 33 GF / 41 GA)",
        ],
    },
    "199901": {
        "selection": "Färjestad BK -1.5 Puck Line",
        "market_type": "Puck Line",
        "text": (
            "League-leading Färjestad BK is putting together a historic defensive start in the "
            "2026/27 SHL, going unbeaten in regulation through ten games (8W-2T-0L, 27 points) "
            "while outscoring opponents an astonishing 40-11 — allowing just 1.10 goals per game "
            "including its 5-1 demolition of reigning champion Skellefteå. With the outright "
            "moneyline priced past -250, step onto plus-money value with Färjestad BK -1.5 Puck Line."
        ),
        "verified_facts": [
            "Farjestad BK #1 SHL (10 GP, 8W-2T-0L, 40 GF / 11 GA, 27 pts) per stats.swehockey.se",
            "Beat reigning champion Skelleftea AIK 5-1 on Oct 8 (shl.se)",
        ],
    },

    # ── TENNIS (ATP 250 Almaty / Brussels / Lyon & WTA 500 Ningbo) ────────────
    "902073": {
        "selection": "Elena Rybakina -1.5 Sets",
        "market_type": "Set Handicap",
        "text": (
            "Newly crowned WTA World No. 1 Elena Rybakina — champion at both Roland Garros and "
            "the US Open during a dominant 2026 season — is an unplayable -800 on the outright "
            "moneyline in Ningbo, making the straight-sets handicap the smart vehicle. Facing "
            "102nd-ranked Polina Kudermetova under fast evening hard-court conditions, Rybakina's "
            "first-serve free points and flat backhand return pressure routinely prevent triple-digit "
            "opponents from forcing deciders. Back Elena Rybakina -1.5 Sets."
        ),
        "verified_facts": [
            "Elena Rybakina is #1 seed and WTA World #1 in Oct 2026 (wtatennis.com Ningbo draw)",
            "Polina Kudermetova ranked outside top 100 (#102); OLBG Rybakina ML sits at 1.12 (-800)",
        ],
    },
    "902087": {
        "selection": "Taylor Fritz -1.5 Sets",
        "market_type": "Set Handicap",
        "text": (
            "Second-seeded Taylor Fritz (ATP Live No. 14, 34-19 in 2026) opens his Lyon indoor "
            "campaign after an opening-round bye against 35-year-old French qualifier Pierre-Hugues "
            "Herbert, who already expended three qualifying and first-round matches including a grueling "
            "win over Sebastián Báez. Rather than laying -556 on Fritz's moneyline, indoor serve-plus-one "
            "consistency against fatigued legs points straight to a 2-0 sweep — take Taylor Fritz -1.5 Sets."
        ),
        "verified_facts": [
            "Taylor Fritz #2 seed in Lyon (ATP Live #14, 34-19 season record per atptour.com)",
            "Qualifier Pierre-Hugues Herbert came through qualifying + R32 win over Sebastian Baez",
        ],
    },
    "902105": {
        "selection": "Brandon Nakashima Moneyline",
        "market_type": "Match Winner",
        "text": (
            "Indoor hard courts reward compact, repeatable ball-striking, and Brandon Nakashima "
            "has quietly turned sheltered European conditions into his best surface. Meeting French "
            "qualifier Kyrian Jacquet in Thursday's final night-session match on Court Central in "
            "Lyon, Nakashima's top-40 return depth and low unforced-error rate neutralize Jacquet's "
            "crowd-fueled shotmaking over a full best-of-three battle. At -205 inside our target "
            "range, Brandon Nakashima Moneyline is the play."
        ),
        "verified_facts": [
            "ProTennisLive 496/op.pdf confirms [Q] Kyrian Jacquet vs Brandon Nakashima on Court Central, Lyon",
            "OLBG market lists Nakashima at 1.48 (-208)",
        ],
    },
    "902133": {
        "selection": "Tommy Paul -3.5 Games",
        "market_type": "Game Handicap",
        "text": (
            "Fourth-seeded Tommy Paul (ATP Live No. 15, 42-19 on the 2026 season) cruised past "
            "Benjamin Bonzi to reach the Lyon quarterfinals and owns a clean 2-0 ATP head-to-head "
            "record over Corentin Moutet. While Moutet rode home support past Ugo Humbert and "
            "Arthur Balshaw, Paul's elite lateral court coverage neutralizes drop-shot variety "
            "without paying OLBG's -400 moneyline tax. Lay the spread with Tommy Paul -3.5 Games."
        ),
        "verified_facts": [
            "Tommy Paul #4 seed Lyon (ATP Live #15, 42-19 in 2026, 2-0 H2H vs Moutet per atptour.com)",
            "Corentin Moutet beat Ugo Humbert R1 and WC Balshaw R2 in Lyon (ProTennisLive 496/mds.pdf)",
        ],
    },

    # ── SNOOKER (WST BetVictor Northern Ireland Open Last 16, Belfast) ────────
    "9940": {
        "selection": "Kyren Wilson Match Winner",
        "market_type": "Match Winner",
        "text": (
            "World No. 9 Kyren Wilson (£716,800 on the two-year WST list, 38 half-centuries and "
            "9 centuries across 19 outings this term) thrives in Home Nations best-of-seven sprints "
            "where tactical safety discipline punishes loose long pots. Pang Junxu (ranked No. 29, "
            "12-11 record) has compiled 52 breaks over 50, yet Wilson's superior end-of-frame "
            "clearance rate at Waterfront Hall keeps him firmly in command. Back Kyren Wilson Match Winner."
        ),
        "verified_facts": [
            "Kyren Wilson WST Rank #9 (£716,800; 11W/19M, 38x50+, 9x100+ per wst.tv)",
            "Pang Junxu WST Rank #29 (12W/23M); NI Open Last 16 best-of-7 at Waterfront Hall, Belfast",
        ],
    },
    "9943": {
        "selection": "Over 5.5 Total Frames",
        "market_type": "Total Frames",
        "text": (
            "Ninety percent of OLBG tipsters piled onto World No. 8 Mark Williams at -333, "
            "overlooking just how well Martin O'Donnell is cueing in Belfast this week. O'Donnell "
            "has already eliminated Judd Trump 4-3 and former world champion Luca Brecel 4-2, "
            "while Williams dropped two frames apiece in beating Robbie Williams (4-2) and Long "
            "Zehuang (4-2). Both veterans grind out tactical frames, pointing squarely to "
            "Over 5.5 Total Frames."
        ),
        "verified_facts": [
            "Mark Williams (#8 WST, 10 centuries) won R64 4-2 vs R. Williams & R32 4-2 vs Long Zehuang",
            "Martin O'Donnell (#56 WST) beat Judd Trump 4-3 & Luca Brecel 4-2 at 2026 NI Open (wst.tv)",
        ],
    },
    "9941": {
        "selection": "Jak Jones -1.5 Frames",
        "market_type": "Frame Handicap",
        "text": (
            "Few players on tour are matching Jak Jones's 2026/27 consistency: ranked No. 4 on "
            "WST's one-year list (£141,200, 15 wins in 23 matches, 44 breaks of 50+ and 13 "
            "centuries), the Welshman dispatched both Tom Ford and four-time world champion John "
            "Higgins by convincing 4-2 scorelines in Belfast. Against world No. 48 Daniel Wells, "
            "Jones's granite safety game regularly builds multi-frame cushions — take Jak Jones -1.5 Frames."
        ),
        "verified_facts": [
            "Jak Jones #4 on WST 1-Year List (£141,200; 15W/23M, 13 centuries; beat Ford 4-2 & Higgins 4-2)",
            "Daniel Wells WST #48 (12W/20M, 6 centuries per wst.tv)",
        ],
    },
    "9946": {
        "selection": "Anthony McGill -1.5 Frames",
        "market_type": "Frame Handicap",
        "text": (
            "Scottish stalwart Anthony McGill (world No. 38, 11 wins from 17 matches this campaign "
            "with 33 breaks over 50) faces Polish tour rookie Mateusz Baranowski (world No. 84, "
            "only 17 breaks of 50+ across 17 matches). With OLBG's 5-for-5 unanimous moneyline "
            "consensus sitting too short at -333, backing McGill's matchplay experience to cover a "
            "4-0, 4-1, or 4-2 margin delivers clean value — play Anthony McGill -1.5 Frames."
        ),
        "verified_facts": [
            "Anthony McGill WST #38 (11W/17M, 33x50+ breaks per wst.tv official stats)",
            "Mateusz Baranowski WST #84 (9W/17M, 17x50+ breaks); OLBG McGill ML sits at 1.30 (-333)",
        ],
    },

    # ── DARTS (PDC Machineseeker European Championship, Dortmund) ─────────────
    "32325": {
        "selection": "Gerwyn Price Match Winner",
        "market_type": "Match Winner",
        "text": (
            "Thursday's headline clash at Dortmund's Westfalenhalle reprises the 2019 European "
            "Championship final, but 2026 form heavily favors world No. 4 Gerwyn Price (£5.49M "
            "Order of Merit, European Tour Baltic Sea Open winner). Two-time champion Rob Cross "
            "has slipped down the rankings relative to Price's relentless treble-20 scoring in "
            "short first-to-six-leg TV sprints. At -175 inside our window, back Gerwyn Price Match Winner."
        ),
        "verified_facts": [
            "Gerwyn Price #4 PDC Order of Merit (£5,487,750) vs Rob Cross (rematch of 2019 EC final per pdc.tv)",
            "Round 1 best-of-11 legs at Westfalenhalle, Dortmund on Thu Oct 22",
        ],
    },
    "32337": {
        "selection": "Luke Humphries -2.5 Legs",
        "market_type": "Leg Handicap",
        "text": (
            "World No. 2 and last year's Dortmund runner-up Luke Humphries (£4.49M Order of Merit) "
            "opens against heavy-scoring Devon thrower Ryan Searle over a race to six legs. "
            "Humphries's outright moneyline sits at -333 — outside our -250 ceiling — yet when "
            "'Cool Hand' finds his double-16 rhythm on TV stages he routinely breaks throw twice "
            "for 6-2 or 6-3 victories. Step onto the handicap with Luke Humphries -2.5 Legs."
        ),
        "verified_facts": [
            "Luke Humphries #2 PDC Order of Merit (£4,490,975) and reigning EC runner-up (pdc.tv)",
            "OLBG Humphries ML sits at 1.30 (-333); Round 1 format is first to 6 legs",
        ],
    },
    "32323": {
        "selection": "Gian van Veen -1.5 Legs",
        "market_type": "Leg Handicap",
        "text": (
            "Reigning European Champion and Dutch No. 1 Gian van Veen has surged to world No. 3 "
            "(£1.61M Order of Merit) on the back of blistering 180-hitting power, returning to "
            "the exact Westfalenhalle stage where he lifted the trophy twelve months ago. Veteran "
            "Andrew Gilding's deliberate pace tests patience, yet Van Veen's scoring gap is too "
            "wide for a decider — bypass the -303 moneyline and back Gian van Veen -1.5 Legs."
        ),
        "verified_facts": [
            "Gian van Veen #3 PDC Order of Merit (£1,610,450) and reigning European Champion (pdc.tv)",
            "Faces Andrew Gilding in Dortmund Rd 1; OLBG ML sits at 1.33 (-303)",
        ],
    },

    # ── HANDBALL (EHF Champions League Men Rd 5) ──────────────────────────────
    "12049": {
        "selection": "Orlen Wisła Płock Match Winner",
        "market_type": "Match Winner",
        "text": (
            "Orlen Wisła Płock sits second in Group B at 3-0-1 (6 points) and already edged MT "
            "Melsungen 25:24 in their September 17 opener before cruising 37:30 at Wybrzeże Gdańsk "
            "this weekend behind competition No. 2 scorer Melvyn Richardson (32 EHFCL goals). "
            "Melsungen (2-0-2, 4 points) dropped a 28:32 Round 4 battle at Barcelona despite "
            "Reynir Thór Stefánsson's six strikes. Back road-hardened Orlen Wisła Płock Match Winner."
        ),
        "verified_facts": [
            "Wisla Plock 3-0-1 (6 pts) beat Melsungen 25:24 on Sep 17 & Gdansk 37:30 domestically (eurohandball.com)",
            "MT Melsungen 2-0-2 (4 pts) lost 28:32 at Barca in Rd 4; Melvyn Richardson has 32 EHFCL goals",
        ],
    },
    "12046": {
        "selection": "Barça -5.5 Goals",
        "market_type": "Goal Handicap",
        "text": (
            "Riding a 20-match EHF Champions League winning streak and leading Group E at 4-0-0 "
            "(+33 goal differential), Barça just dismantled Dinamo Bucuresti 36:22 and topped "
            "Cangas 37:28 in Liga ASOBAL. Montpellier (1-0-3, -9 differential) was shredded 30:38 "
            "at home by Aarhus last week and trails behind Dika Mem's two-way firepower at Palau "
            "Blaugrana. Skip the -1111 moneyline and lay Barça -5.5 Goals."
        ),
        "verified_facts": [
            "Barca 4-0-0 (+33 diff, 8 pts) beat Montpellier 28:27 away Sep 17 & Dinamo 36:22 in Rd 4 (eurohandball.com)",
            "Montpellier 1-0-3 (-9 diff, 2 pts) lost 30:38 at home to SAH Aarhus in Rd 4",
        ],
    },
    "12048": {
        "selection": "SC Magdeburg -6.5 Goals",
        "market_type": "Goal Handicap",
        "text": (
            "Group F leader SC Magdeburg (4-0-0, +33 goal differential) already crushed Kolstad "
            "Håndball 37:22 in their September 9 meeting — with nearly every field player scoring — "
            "before beating Kielce 30:27 behind Matej Mandić's 11 saves. Winless Kolstad (0-0-4, "
            "-32 differential) is mired in an eight-game EHFCL losing streak and was routed 25:37 "
            "by Elverum domestically on Saturday. Lay SC Magdeburg -6.5 Goals."
        ),
        "verified_facts": [
            "SC Magdeburg 4-0-0 (+33 diff) beat Kolstad 37:22 on Sep 9 & Kielce 30:27 in Rd 4 (eurohandball.com)",
            "Kolstad 0-0-4 (-32 diff) lost 28:36 to Kriens-Luzern & 25:37 to Elverum on Saturday",
        ],
    },

    # ── VOLLEYBALL (Czech Extraliga, Polish PlusLiga, Italian SuperLega) ──────
    "36992": {
        "selection": "Kladno volejbal cz -1.5 Sets",
        "market_type": "Set Handicap",
        "text": (
            "Kladno volejbal cz stormed straight to No. 1 in the ČEZ Extraliga table on opening "
            "weekend with a ruthless 3-0 sweep (75-56 small points), posting the widest point "
            "ratio in Czechia. Host VK Ostrava dropped a five-set 2-3 heartbreaker (94-100 small "
            "points) in Round 1 and struggled in serve-receive down the stretch. Kladno's block-defense "
            "superiority makes Kladno volejbal cz -1.5 Sets our standout Czech volleyball play."
        ),
        "verified_facts": [
            "Kladno #1 CVF Extraliga (1-0, 3:0 sets, 75:56 small pts) per official cvf.cz table",
            "VK Ostrava #7 CVF Extraliga (0-1, 2:3 sets, 94:100 small pts)",
        ],
    },
    "36964": {
        "selection": "PGE Projekt Warszawa -1.5 Sets",
        "market_type": "Set Handicap",
        "text": (
            "Both Polish heavyweights won 3-1 on PlusLiga opening weekend — Projekt Warszawa "
            "powering past Indykpol AZS Olsztyn (27-29, 25-23, 25-17, 25-16) and Skra Bełchatów "
            "outlasting Trefl Gdańsk (31-29 in the fourth). Yet Warszawa's side-out efficiency "
            "over its final two sets (holding Olsztyn to 17 and 16 points) reflects deeper pin "
            "firepower than Bełchatów's roster. Bypass the -400 moneyline for PGE Projekt Warszawa -1.5 Sets."
        ),
        "verified_facts": [
            "Projekt Warszawa beat AZS Olsztyn 3-1 (27-29, 25-23, 25-17, 25-16) on Oct 16 (plusliga.pl)",
            "Skra Belchatow beat Trefl Gdansk 3-1 on Oct 17; OLBG Warszawa ML sits at 1.25 (-400)",
        ],
    },

    # ── RUGBY UNION (Pro D2, URC, Top 14) ─────────────────────────────────────
    "609556": {
        "selection": "Oyonnax Rugby Match Winner",
        "market_type": "Match Winner",
        "text": (
            "Pro D2 table-topper Oyonnax Rugby is tearing through France's second tier unbeaten "
            "at 7-0-0 (33 points, five bonus points, and a staggering +159 differential on 313 "
            "points scored vs 154 conceded). Eighth-placed US Montauban enters Round 8 over "
            "seventeen table points adrift, making OLBG's underdog pricing on Oyonnax one of "
            "the sharpest mispricings on the Thursday board. Hammer Oyonnax Rugby Match Winner."
        ),
        "verified_facts": [
            "Oyonnax Rugby #1 Pro D2: 7-0-0, 33 pts, 5 bonus pts, 313 PF / 154 PA (+159) per prod2.lnr.fr",
            "US Montauban #8 in Pro D2 Round 8 official calendar (22 Oct 21:00 local / 19:00Z)",
        ],
    },
    "609578": {
        "selection": "Leinster -11.5 Points",
        "market_type": "Point Handicap",
        "text": (
            "Irish interprovincial derbies under the Croke Park lights always carry bite, yet "
            "Leinster's international pack depth routinely wears Munster down across the final "
            "quarter. Munster enters Round 4 sitting ninth in the URC at 1-1-1 (72 PF, 74 PA), "
            "whereas OLBG's -901 Leinster moneyline leaves zero value on the outright win. "
            "Two converted tries of separation is well within reach — back Leinster -11.5 Points."
        ),
        "verified_facts": [
            "Official URC Round 4 fixture at Croke Park, Dublin on Sat Oct 24 17:00Z (unitedrugby.com)",
            "Munster 1-1-1 (9 pts, 72 PF / 74 PA) through 3 URC rounds; OLBG Leinster ML sits at 1.11 (-901)",
        ],
    },

    # ── RUGBY LEAGUE (2026 Rugby League World Cup Round 2) ────────────────────
    "AC-RLWC-PNG-SAM": {
        "selection": "Samoa Match Winner",
        "market_type": "Match Winner",
        "text": (
            "Samoa delivered the statement performance of Rugby League World Cup Round 1, "
            "running in thirteen tries to obliterate France 78-4 with relentless NRL-hardened "
            "middle-forward metres and slick left-edge offloading. Papua New Guinea beat Lebanon "
            "42-18 in Port Moresby, yet conceding three tries to the Cedars exposes defensive "
            "spacing issues against elite Test strike weapons. Back Samoa Match Winner."
        ),
        "verified_facts": [
            "Samoa beat France 78-4 in RLWC 2026 Round 1 (nrl.com official Round 1 wrap)",
            "Papua New Guinea beat Lebanon 42-18 in Round 1; Rd 2 at Santos National Football Stadium Oct 24",
        ],
    },

    # ── CRICKET (ICC UAE Men's ODI Tri-Series Final & Namibia v Ireland) ──────
    "188831": {
        "selection": "Afghanistan -42.5 Runs / 5+ Wickets",
        "market_type": "Match Handicap",
        "text": (
            "World No. 8 Afghanistan (93 ICC ODI rating) just dismantled 11th-ranked Zimbabwe "
            "(53 rating) by 158 runs at this exact Abu Dhabi venue on October 19, piling up 294 "
            "behind Sediqullah Atal's century (102) before Rashid Khan (4/17) and Fazalhaq Farooqi "
            "(2/15) skittled the Chevrons for 136. Bypassing OLBG's -333 moneyline, back "
            "Afghanistan -42.5 Runs / 5+ Wickets in Friday's Tri-Series Final."
        ),
        "verified_facts": [
            "Afghanistan (#8 ICC ODI, 93 rating) beat Zimbabwe (#11, 53 rating) 294 to 136 on Oct 19 (icc-cricket.com)",
            "Sediqullah Atal scored 102, Rashid Khan 4/17, Fazalhaq Farooqi 2/15 in Abu Dhabi",
        ],
    },
    "AC-CRI-NAM-IRE2": {
        "selection": "Ireland Match Winner",
        "market_type": "Match Winner",
        "text": (
            "Full-Member batting depth gives Ireland a clear class edge heading into Saturday's "
            "2nd ODI at Wanderers Cricket Ground in Windhoek. Ranked 23 ICC ODI rating points "
            "clear of 17th-placed Namibia (54 rating to 31), Paul Stirling's touring squad pairs "
            "Harry Tector, Lorcan Tucker, and Curtis Campher with Mark Adair's new-ball swing "
            "against an Associate side that went 33-from-36 in CWCL2. Play Ireland Match Winner."
        ),
        "verified_facts": [
            "ICC Men's ODI Rankings: Ireland 54 rating pts vs Namibia #17 on 31 rating pts (icc-cricket.com)",
            "Official 5-match ODI tour schedule at Wanderers Cricket Ground, Windhoek (cricketireland.ie)",
        ],
    },

    # ── ESPORTS & BADMINTON & AUSSIE RULES ────────────────────────────────────
    "AC-LOL-HLE-TES": {
        "selection": "Hanwha Life Esports Match Winner",
        "market_type": "Match Winner",
        "text": (
            "Swiss Stage Round 1 best-of-ones at Worlds 2026 reward disciplined macro around "
            "neutral objectives, where LCK Tier-2 seed Hanwha Life Esports holds a decisive edge "
            "over LPL Tier-3 entrant Top Esports. Top Esports's recurring mid-game Baron-setup "
            "volatility gets punished severely by LCK vision control in single-map openers. "
            "Inside our target price band at -168, lock in Hanwha Life Esports Match Winner."
        ),
        "verified_facts": [
            "Riot LoL Esports official schedule: HLE (Tier 2) vs TES (Tier 3) Bo1 on Fri Oct 23 18:00Z",
        ],
    },
    "AC-BWF-NAR-SHE": {
        "selection": "Kodai Naraoka -1.5 Games",
        "market_type": "Game Handicap",
        "text": (
            "Former World Championship silver medalist Kodai Naraoka enters Thursday's YONEX "
            "French Open Round of 16 in Cesson-Sévigné carrying 78,740 BWF World Tour ranking "
            "points — nearly double Indian youngster Ayush Shetty's 42,100 points. Naraoka's "
            "trademark multi-shot retrieval and defensive patience on Glaz Arena's medium-speed "
            "courts grind aggressive unseeded challengers into unforced errors across two straight "
            "frames. Take Kodai Naraoka -1.5 Games."
        ),
        "verified_facts": [
            "BWF Super 750 French Open R16 (Oct 22): Kodai Naraoka (78,740 pts) vs Ayush Shetty (42,100 pts)",
        ],
    },
    "AC-AFLW-GEE-FRE": {
        "selection": "Geelong Cats -16.5 Points",
        "market_type": "Point Handicap",
        "text": (
            "Sitting second on the 2026 NAB AFLW ladder at 36 premiership points with a dominant "
            "167.2 percentage through ten rounds, Geelong welcomes eighth-placed Fremantle (20 "
            "points, 104.9 percentage) to GMHBA Stadium on Saturday. Geelong's inside-50 differential "
            "on its narrow Kardinia Park home deck consistently stretches mid-table interstate "
            "visitors past three goals — bypass the short moneyline and back Geelong Cats -16.5 Points."
        ),
        "verified_facts": [
            "Geelong Cats #2 AFLW ladder (10 GP, 36 pts, 167.2%) vs Fremantle #8 (20 pts, 104.9%) per afl.com.au/aflw",
            "Round 11 fixture at GMHBA Stadium on Sat Oct 24 04:05Z",
        ],
    },

    # ── GOLF & MOTOR RACING OUTRIGHTS ─────────────────────────────────────────
    "101903": {
        "selection": "Steven Alker Outright Winner",
        "market_type": "Outright Winner",
        "text": (
            "Opening the 2026 Charles Schwab Cup Playoffs over 54 holes at St. Louis's par-71, "
            "6,992-yard Norwood Hills Country Club concentrates winning equity among the tour's "
            "big three of Stewart Cink, Zach Johnson, and Steven Alker. A four-time winner on the "
            "2026 PGA Tour Champions circuit and two-time season-long Schwab Cup champion (2022, 2024), "
            "Alker thrives on classical tree-lined approach tests. Back Steven Alker Outright Winner."
        ),
        "verified_facts": [
            "Stifel Charity Classic (Oct 23-25, Norwood Hills CC, Par 71, 6,992 yds, $2.3M purse) opens 2026 Schwab Cup Playoffs",
            "Steven Alker has 4 PGA Tour Champions wins in 2026 (pgatour.com)",
        ],
    },
    "912": {
        "selection": "George Russell Outright (Without Antonelli)",
        "market_type": "Season Outright",
        "text": (
            "OLBG crowd sentiment has mistakenly made Max Verstappen the -137 favorite in Formula 1's "
            "'Without Kimi Antonelli' market despite Verstappen trailing in fourth on 221 points "
            "heading into Circuit of the Americas. George Russell actually holds second in the World "
            "Drivers' Championship on 238 points — nine clear of Lewis Hamilton (229) and seventeen "
            "ahead of Verstappen — while driving the same benchmark Mercedes package as 340-point "
            "leader Antonelli. Grab plus-money value on George Russell Outright (Without Antonelli)."
        ),
        "verified_facts": [
            "Official formula1.com standings entering US GP: 1. Antonelli 340, 2. Russell 238, 3. Hamilton 229, 4. Verstappen 221",
            "OLBG #912 prices Verstappen at 1.73 despite 17-point deficit to Russell",
        ],
    },
}
