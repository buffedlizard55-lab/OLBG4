#!/usr/bin/env python3
"""Board K remediation of the Build D hub dataset (data/matches.json).

Applies the fixes Board J (arena/e1e0c27e-olbg4) logged as cross-session requests but
could not apply itself, because the file belongs to Board D.

Every correction below was re-checked by this session against an official governing-body
page on 2026-10-21 (the URL is stored on the row as `k_verification.source` and in the
remediation log). Per the brief:

  * a value that could not be confirmed on an official domain is set to "" (blank) and
    flagged - never inferred, never carried over from a secondary site;
  * `verified` is only true where the row's own source link is a governing body;
  * nothing is deleted - withdrawn text is preserved on the row as `k_withdrawn`.

Findings addressed: F-01, F-02, F-03, F-04, F-08. (F-11/F-12 were fixed by re-running
Build A's own generator; F-07 by scripts/session-47b1b4e2/fix_build_b_flag.py.)

Run:  python3 scripts/session-47b1b4e2/remediate.py
Out:  data/matches.json (in place), data/session-47b1b4e2/remediation.json (audit trail)
"""
import json
import os
import sys
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MATCHES = os.path.join(ROOT, "data", "matches.json")
OUTDIR = os.path.join(ROOT, "data", "session-47b1b4e2")

# ---------------------------------------------------------------------------
# F-01: source-domain classification.
# Explicit allowlist of the governing bodies / leagues / tours that actually own the
# sport in question. Anything not on this list is treated as secondary, so a row can
# never be marked `verified` on the strength of a news aggregator or wiki page.
# ---------------------------------------------------------------------------
OFFICIAL_DOMAINS = {
    "nba.com": "NBA (league)",
    "nhl.com": "NHL (league)",
    "mlb.com": "MLB (league)",
    "atptour.com": "ATP Tour",
    "wtatennis.com": "WTA Tour",
    "pgatour.com": "PGA TOUR",
    "lpga.com": "LPGA",
    "cricket.com.au": "Cricket Australia",
    "pcb.com.pk": "Pakistan Cricket Board",
    "ecb.co.uk": "England and Wales Cricket Board",
    "fivb.com": "FIVB (volleyball)",
    "ittf.com": "ITTF (table tennis)",
    "fftt.com": "French Table Tennis Federation",
    "ehfcl.eurohandball.com": "EHF Champions League",
    "ihf.info": "IHF (handball)",
    "afl.com.au": "AFL (Australian Rules)",
    "nrl.com": "NRL (rugby league)",
    "rlwc2026.com": "Rugby League World Cup 2026 (tournament organiser)",
    "pdc.tv": "PDC (darts)",
    "wst.tv": "World Snooker Tour",
    "euroleaguebasketball.net": "EuroLeague Basketball",
    "world.rugby": "World Rugby",
    "bwfbadminton.com": "BWF (badminton)",
    "lolesports.com": "Riot Games / LoL Esports",
    "valorantesports.com": "Riot Games / Valorant Esports",
    "suncorpstadium.com.au": "Suncorp Stadium (venue operator)",
    "anadoluefessk.org": "Anadolu Efes SK (club)",
    "galwaygaa.ie": "Galway GAA (county board)",
}

# Domains that are useful for locating an official page but are not the governing body.
KNOWN_SECONDARY = {
    "espn.com", "en.wikipedia.org", "bbc.com", "cricinfo.com", "skysports.com",
    "etusuora.com", "olympics.com", "basketnews.com", "findmygroup.uk",
    "sportsdata.usatoday.com", "en.tempo.co", "montpellier.fr", "olbg.com",
    "bostonglobe.com", "habseyesontheprize.com",
}


def domain_of(url):
    return urllib.parse.urlparse(url or "").netloc.lower().replace("www.", "")


def classify(url):
    d = domain_of(url)
    if d in OFFICIAL_DOMAINS:
        return "official", d
    if "olbg.com" in d:
        return "olbg", d
    if d in KNOWN_SECONDARY:
        return "secondary", d
    return "secondary", d  # unrecognised => treated conservatively as non-official


# ---------------------------------------------------------------------------
# F-04: entry classification. The brief asks for a list of matches; about half of the
# hub's 66 "entries" are tournaments, rounds, completed results or off-season notes.
# They are labelled rather than deleted, and the UI splits them out of the match table.
# ---------------------------------------------------------------------------
ENTRY_TYPE = {}
for i in ["NBA01", "NBA02", "NBA03", "NBA04", "NBA05", "NBA06", "NBA07",
          "EL01", "EL02",
          "MLB01", "MLB02", "MLB03", "MLB04",
          "CRK01", "CRK02", "CRK03", "CRK04", "CRK05",
          "RUG01", "RUG02", "RUG03", "RUG04", "RUG05", "RUG06",
          "NHL01", "NHL02", "NHL03", "NHL04", "NHL05", "NHL06", "NHL07",
          "RL01"]:
    ENTRY_TYPE[i] = "match"
# Completed fixtures kept for form - a result, not an upcoming match.
for i in ["EL03", "ATP05", "BDM01"]:
    ENTRY_TYPE[i] = "result"
# Tournaments / rounds / sessions / series summaries - not one match.
for i in ["ATP01", "ATP02", "ATP03", "ATP04", "WTA01",
          "SNK01", "SNK02", "SNK03", "SNK04",
          "DRT01", "DRT02", "DRT03", "DRT04",
          "GLF01", "GLF02", "GLF03", "GLF04", "GLF05",
          "BDM02", "BDM03",
          "TTT01", "TTT02", "TTT03",
          "ESP01", "ESP02",
          "HDB01", "HDB02",
          "CRK06"]:
    ENTRY_TYPE[i] = "tournament"
# Notes with no fixture at all.
for i in ["VBL01", "VBL02", "AFL01"]:
    ENTRY_TYPE[i] = "note"

ENTRY_TYPE_LABEL = {
    "match": "Match - a single head-to-head fixture with named participants",
    "result": "Result - a completed fixture retained for form, not an upcoming match",
    "tournament": "Tournament / round - an event, session or series summary, not one match",
    "note": "Note - off-season, qualification or coverage information; no fixture",
}


# ---------------------------------------------------------------------------
# Targeted corrections. Each entry records what changed, the official page it was
# checked against on 2026-10-21, and the Board J finding it resolves.
# `set` values are applied verbatim; "" means "blank it, do not infer".
# ---------------------------------------------------------------------------
MLB_FAQ = "https://www.mlb.com/news/2026-mlb-world-series-faq-schedule-times-teams-and-more"
MLB_HFA = "https://www.mlb.com/news/world-series-home-field-advantage"
NHL_SJS_PREVIEW = "https://www.nhl.com/news/san-jose-sharks-montreal-canadiens-game-preview-october-20-2026"
NHL_SJS_RECAP = "https://www.nhl.com/news/san-jose-sharks-montreal-canadiens-game-recap-october-20-2026"
NHL_BOS_PREVIEW = "https://www.nhl.com/news/boston-bruins-dallas-stars-game-preview-october-20-2026"
NHL_BOS_RECAP = "https://www.nhl.com/news/boston-bruins-dallas-stars-game-recap-october-20-2026"
NHL_BOS_GAMEDAY = "https://www.nhl.com/stars/news/game-day-guide-boston-bruins-vs-dallas-stars-102026"
EL_SCHEDULE = "https://www.euroleaguebasketball.net/en/euroleague/news/the-2026-27-euroleague-schedule-is-official/"
EL_HOME = "https://www.euroleaguebasketball.net/en/euroleague/"
EFES_CLUB = "https://www.anadoluefessk.org/en"
PDC_SCHEDULE = "https://www.pdc.tv/news/2026/october/19/2026-machineseeker-european-championship-schedule-confirmed/"
PCB_TRISERIES = ("https://www.pcb.com.pk/press-release-detail/pakistan-to-host-sri-lanka-and-"
                 "england-for-t20is-odi-tri-series-and-tests.html")
PCB_ADVISORY = ("https://www.pcb.com.pk/press-release-detail/media-advisory-men-s-odi-tri-series-"
                "pakistan-england-sri-lanka-rawalpindi-leg.html")
ECB_TRISERIES = "https://www.ecb.co.uk/news/4562387/pakistan-to-host-sri-lanka-and-england-in-odi-triseries"
RLWC_DRAW = "https://www.rlwc2026.com/draws-and-pools"
RLWC_AUSFIJI = "https://www.rlwc2026.com/draw/mens/2026/round-2/australia-v-fiji"
SUNCORP = "https://suncorpstadium.com.au/events/rugby-league-world-cup-2026--men-s-australia-v-fiji"

CORRECTIONS = {
    # ------------------------------------------------------------------ F-02
    "MLB01": dict(
        finding="F-02",
        reason=("Prediction claimed a 'seven-game ALCS' and that Milwaukee 'swept the season "
                "series 2-0'. MLB.com states the Rays beat the Guardians in SIX games and that "
                "the Brewers 'took two of three' in their only regular-season meeting."),
        source=MLB_FAQ,
        set=dict(
            sourceUrl=MLB_FAQ,
            sourceName="MLB.com - 2026 World Series FAQ (schedule, times, teams)",
            prediction=(
                "Back the Milwaukee Brewers to win World Series Game 1 at American Family Field "
                "on Friday night. Milwaukee won a franchise-record 103 games to lead the majors "
                "for a second straight season, then took the NLDS from the Padres in four and "
                "swept the Dodgers in the NLCS, with Jake Bauers named NLCS MVP. Tampa Bay led "
                "the American League with 98 wins and beat Cleveland in six ALCS games, but this "
                "is their first Fall Classic since 2020 and they must open on the road. The "
                "Brewers took two of three from the Rays in their only regular-season meeting. "
                "Our selection is Milwaukee on the moneyline."
            ),
            formNotes=(
                "MLB.com: Brewers 103-59 (franchise record, best in MLB for a 2nd straight "
                "season), swept Dodgers 4-0 in NLCS, beat Padres 4-0 in NLDS; 2nd World Series "
                "appearance, first since 1982. Rays 98-64 (AL best, top seed), swept Yankees in "
                "ALDS, beat Guardians 4-2 in ALCS; first World Series since 2020. Head-to-head "
                "2026 regular season: Brewers took two of three. Brewers hold home-field "
                "advantage and host Games 1, 2 (and 6, 7 if needed)."
            ),
        ),
        verified_on="2026-10-21",
    ),
    "NHL01": dict(
        finding="F-02",
        reason=("Prediction said San Jose were '0-4 on their Eastern road trip' and Montreal "
                "'3-1 at home'. NHL.com's own preview lists SHARKS (4-4-1) at CANADIENS (4-3-1), "
                "and the game has since been played - San Jose won 4-3 in overtime."),
        source=NHL_SJS_PREVIEW,
        set=dict(
            status="Final - San Jose won 4-3 (OT)",
            confidence="Low",
            prediction="",
            formNotes=(
                "NHL.com pre-game preview listed SHARKS (4-4-1) at CANADIENS (4-3-1), 7 p.m. ET, "
                "Bell Centre. NHL.com recap: San Jose won 4-3 in OT on 20 Oct 2026 (Celebrini two "
                "goals incl. the OT power-play winner), moving to 5-4-1; Montreal to 4-3-2."
            ),
            sourceUrl=NHL_SJS_RECAP,
            sourceName="NHL.com - Sharks at Canadiens preview (20 Oct) and game recap",
        ),
        withdraw=dict(
            confidence_from="High",
            note=("Fixture is already final, so no bettable selection remains and the published "
                  "reasoning was contradicted by NHL.com. Confidence reduced to Low and the "
                  "prediction withdrawn rather than rewritten after the fact."),
        ),
        verified_on="2026-10-21",
    ),
    "NHL06": dict(
        finding="F-02",
        reason=("Prediction said Boston were '1-3 on their Texas swing' and 'without Marchand on "
                "IR'. NHL.com's preview lists BRUINS (7-2-0) at STARS (4-3-1) with 'Injured: "
                "None'; the Stars' game-day guide gives Boston 7-2-0, 14 points, 1st in the "
                "Atlantic. Marchand is not on Boston's roster. The game has been played."),
        source=NHL_BOS_PREVIEW,
        set=dict(
            status="Final - Dallas won 3-2 (OT)",
            confidence="Low",
            prediction="",
            formNotes=(
                "NHL.com pre-game preview listed BRUINS (7-2-0) at STARS (4-3-1), 8 p.m. ET, "
                "American Airlines Center; Boston's injured list was 'None'. NHL.com recap: "
                "Dallas won 3-2 in OT on 20 Oct 2026 on a Mikko Rantanen hat trick, stopping "
                "Boston's five-game win streak; Bruins to 7-2-1, Stars to 5-3-1."
            ),
            sourceUrl=NHL_BOS_RECAP,
            sourceName="NHL.com - Bruins at Stars preview (20 Oct) and game recap",
        ),
        withdraw=dict(
            confidence_from="High",
            note=("The pick (Dallas) happened to land, but every supporting claim in the "
                  "write-up was contradicted by NHL.com, so the prediction is withdrawn rather "
                  "than kept on a false basis. Fixture is final; confidence reduced to Low."),
        ),
        verified_on="2026-10-21",
    ),
    "EL02": dict(
        finding="F-02 / F-03 / F-08",
        reason=("Prediction inverted the records (said Efes 4-2 and Besiktas 2-4), contained an "
                "unedited draft fragment ('89-66 blowout of Efes? Actually Efes beat Bayern "
                "101-93...') and an instruction to self ('Verify tip via EuroLeague official "
                "calendar'). Venue and time label were also wrong."),
        source=EL_SCHEDULE,
        set=dict(
            time="2026-10-22 17:30 CET (20:30 Istanbul local)",
            venue="Basketball Development Center (Turkcell Basketbol Gelisim Merkezi), Istanbul",
            confidence="Low",
            prediction="",
            formNotes=(
                "EuroLeague Basketball confirms Round 7 on 22 October carries the first Turkish "
                "derby of the season, Anadolu Efes v Besiktas, and lists the tip at 17:30 with "
                "Efes 13th and Besiktas 11th after six rounds. Anadolu Efes SK's own fixture "
                "list gives the venue as Turkcell Basketbol Gelisim Merkezi at 20:30 local. "
                "Exact win-loss records are left blank: they were only confirmable on secondary "
                "sites at this cut-off, so they are not published as verified."
            ),
            sourceUrl=EL_SCHEDULE,
            sourceName="EuroLeague Basketball - 2026-27 schedule is official (Round 7)",
            teamA_record="",
            teamB_record="",
        ),
        withdraw=dict(
            confidence_from="High",
            note=("The official EuroLeague standings positions put Efes (13th) BELOW Besiktas "
                  "(11th), so a High-confidence Efes selection is not supported by verified "
                  "form. Reduced to Low and the write-up withdrawn; no replacement invented."),
        ),
        verified_on="2026-10-21",
    ),
    "RL01": dict(
        finding="F-02 / F-03 / F-04",
        reason=("Row described a 'Pacific Championships' with 'Australia vs NZ Oct 25 "
                "(Brisbane 7:50pm)', 'PNG vs NZ Nov 1' and 'Final Nov 8 Sydney'. There is no "
                "Pacific Championships in 2026 - the tournament is the Rugby League World Cup. "
                "rlwc2026.com shows Australia v New Zealand was Round 1 on 15 Oct in Sydney "
                "(Australia won 24-22); the 25 Oct Brisbane fixture is Australia v FIJI, and "
                "the final is 15 Nov in Brisbane. The row was also a tournament summary rather "
                "than a match."),
        source=RLWC_DRAW,
        set=dict(
            sport="Rugby League",
            competition="Rugby League World Cup 2026 - Men's Pool A, Round 2",
            date="2026-10-25",
            time="2026-10-25 19:05 AEST (local Brisbane)",
            venue="Suncorp Stadium, Brisbane",
            match="Australia v Fiji",
            teamA="Australia",
            teamB="Fiji",
            status="Scheduled",
            confidence="Medium",
            prediction="",
            formNotes=(
                "rlwc2026.com (official tournament site) confirms Round 2, Pool A: Australia v "
                "Fiji, Sunday 25 October, Suncorp Stadium, Brisbane. Verified Round 1 results "
                "from the same source: Australia 24-22 New Zealand (15 Oct, Allianz Stadium, "
                "Sydney) and Fiji 40-12 Cook Islands (18 Oct, McDonald Jones Stadium, Newcastle) "
                "- both Pool A sides are 1-0. Suncorp Stadium's own event page lists a 7:05pm "
                "kick-off. Our originated line is not published for this row: with both sides "
                "level on one win and Australia's opener decided by two points, there is no "
                "verified form basis strong enough to originate a price we would stand behind."
            ),
            sourceUrl=RLWC_AUSFIJI,
            sourceName="RLWC2026.com official match centre - Australia v Fiji (Round 2, Pool A)",
            originatedMoneyline=dict(a="", b=""),
            originatedSpread="",
            originatedTotal="",
        ),
        withdraw=dict(
            confidence_from="Medium",
            note=("Fixture identity was wrong, so the pick and line derived from it are withdrawn "
                  "rather than carried over to a different match. Corrected fixture fields are "
                  "published with the official source; the line is left blank because no "
                  "verified form basis supports originating one."),
        ),
        verified_on="2026-10-21",
    ),
    # ------------------------------------------------------------------ F-03
    "CRK03": dict(
        finding="F-03",
        reason=("Labelled 'Tri-Series Match 1'. The PCB lists Pakistan v England on 20 October "
                "at Rawalpindi as the SECOND match; Match 1 was Pakistan v Sri Lanka on 18 "
                "October. The hub also had the home side reversed."),
        source=PCB_TRISERIES,
        set=dict(
            match="Pakistan v England",
            teamA="Pakistan",
            teamB="England",
            competition="Pakistan ODI Tri-Series 2026-27 - 2nd match (England, Pakistan, Sri Lanka)",
            venue="Rawalpindi Cricket Stadium, Rawalpindi",
            time="2026-10-20 13:00 PKT",
            sourceUrl=PCB_TRISERIES,
            sourceName="PCB - Pakistan to host Sri Lanka and England for T20Is, ODI tri-series and Tests",
            formNotes=(
                "PCB: seven-match double round-robin ODI tri-series, 18-31 October. Match 1 was "
                "Pakistan v Sri Lanka (18 Oct, Rawalpindi); Pakistan v England is match 2 "
                "(20 Oct, Rawalpindi, 1pm PKT, toss 12.30pm). Corroborated by the ECB schedule."
            ),
        ),
        verified_on="2026-10-21",
    ),
    "CRK05": dict(
        finding="F-03",
        reason=("Dated the tri-series final 29 October. The PCB, the ECB and the PCB media "
                "advisory all put the final on 31 October at Gaddafi Stadium, Lahore; 29 October "
                "is the sixth match, Sri Lanka v England."),
        source=PCB_TRISERIES,
        set=dict(
            date="2026-10-31",
            competition="Pakistan ODI Tri-Series 2026-27 - Final (top two sides)",
            venue="Gaddafi Stadium, Lahore",
            time="2026-10-31 13:00 PKT",
            sourceUrl=PCB_TRISERIES,
            sourceName="PCB - ODI tri-series schedule (final 31 October, Gaddafi Stadium)",
            formNotes=(
                "PCB: 'the top two sides will meet in the final at the same venue on Saturday, "
                "31 October' (Gaddafi Stadium, Lahore). Participants are not yet determined, so "
                "they are left as TBD rather than guessed. 29 October is match 6, Sri Lanka v "
                "England. Corroborated by ECB and the PCB Rawalpindi-leg media advisory."
            ),
        ),
        verified_on="2026-10-21",
    ),
    "MLB03": dict(
        finding="F-03",
        reason=("Venue read 'George M. Steinbrenner Field'. MLB.com's home-field-advantage page "
                "states the Rays host Games 3, 4 and 5 at Tropicana Field."),
        source=MLB_HFA,
        set=dict(
            venue="Tropicana Field, St. Petersburg, FL",
            sourceUrl=MLB_HFA,
            sourceName="MLB.com - Who has home-field advantage in the 2026 World Series?",
            formNotes=(
                "MLB.com: 'The Rays will host Games 3, 4 and 5 (if necessary) at Tropicana "
                "Field.' Game 3 is Monday 26 October, 8 p.m. ET. Milwaukee hosts Games 1, 2 (and "
                "6, 7 if needed) at American Family Field."
            ),
        ),
        verified_on="2026-10-21",
    ),
    # ------------------------------------------- F-01 upgrades (official source found)
    "CRK04": dict(
        finding="F-01 / F-03",
        reason=("Row was sourced to Sky Sports and flagged unverified, and its start time read "
                "14:30 PKT. The PCB (and the ECB) confirm the fixture and give the start as "
                "1pm PKT, so the row can be published against a governing body."),
        source=PCB_ADVISORY,
        set=dict(
            competition="Pakistan ODI Tri-Series 2026-27 - 3rd match (England, Pakistan, Sri Lanka)",
            match="Sri Lanka v England",
            venue="Rawalpindi Cricket Stadium, Rawalpindi",
            time="2026-10-22 13:00 PKT",
            sourceUrl=PCB_ADVISORY,
            sourceName="PCB - Media advisory: men's ODI tri-series, Rawalpindi leg",
            formNotes=(
                "PCB media advisory: 'Sri Lanka and England will play the third match of the ODI "
                "tri-series at the Rawalpindi Cricket Stadium from 1pm PKT onwards' on 22 October; "
                "the PCB press release sets the toss in all matches at 12.30pm PKT. Corroborated "
                "by the ECB schedule. Form claims previously sourced to Sky Sports are withdrawn "
                "with the prediction below - they are not confirmable on a governing-body page."
            ),
        ),
        verified_on="2026-10-21",
    ),
    "EL01": dict(
        finding="F-01 / F-03",
        reason=("Row was sourced to olympics.com. EuroLeague Basketball's own schedule release "
                "confirms Round 7 on 22 October carries the first Serbian derby between Partizan "
                "and Crvena Zvezda, so the fixture is officially sourced. The published tip time "
                "(20:45 CET) and venue could NOT be confirmed on a governing-body domain, so per "
                "the brief they are blanked rather than kept on a secondary source."),
        source=EL_SCHEDULE,
        set=dict(
            sourceUrl=EL_SCHEDULE,
            sourceName="EuroLeague Basketball - 2026-27 schedule is official (Round 7, 22 October)",
            time="",
            venue="",
            formNotes=(
                "EuroLeague Basketball confirms Round 7 on 22 October features the first Serbian "
                "derby of the season, Partizan v Crvena Zvezda. Tip time and venue are left blank: "
                "they were only published on secondary sites at this cut-off and are not inferred. "
                "Previous values are preserved under k_unverified_values for review."
            ),
        ),
        verified_on="2026-10-21",
        preserve_unverified=["time", "venue"],
    ),
    # ------------------------------------------------------------------ F-08
    "DRT01": dict(finding="F-08", reason="Timezone printed as CET; the PDC publishes 1900-2300 CEST.",
                  source=PDC_SCHEDULE,
                  set=dict(time="2026-10-22 19:00-23:00 CEST (18:00-22:00 BST)",
                           sourceUrl=PDC_SCHEDULE,
                           sourceName="PDC - 2026 Machineseeker European Championship schedule confirmed",
                           formNotes="PDC official schedule of play: Thursday 22 October, 1900-2300 CEST, Round One x8, Westfalenhalle, Dortmund."),
                  verified_on="2026-10-21"),
    "DRT02": dict(finding="F-08", reason="Timezone printed as CET; the PDC publishes 1900-2300 CEST.",
                  source=PDC_SCHEDULE,
                  set=dict(time="2026-10-23 19:00-23:00 CEST (18:00-22:00 BST)",
                           sourceUrl=PDC_SCHEDULE,
                           sourceName="PDC - 2026 Machineseeker European Championship schedule confirmed",
                           formNotes="PDC official schedule of play: Friday 23 October, 1900-2300 CEST, Round One x8, Westfalenhalle, Dortmund."),
                  verified_on="2026-10-21"),
    "DRT03": dict(finding="F-08", reason="Timezone printed as CET; the PDC publishes the Dortmund sessions in CEST.",
                  source=PDC_SCHEDULE,
                  set=dict(time="2026-10-24 CEST (afternoon + evening sessions)",
                           sourceUrl=PDC_SCHEDULE,
                           sourceName="PDC - 2026 Machineseeker European Championship schedule confirmed",
                           formNotes="PDC official schedule of play: Saturday 24 October, eight Round Two ties across afternoon and evening sessions, Westfalenhalle, Dortmund."),
                  verified_on="2026-10-21"),
    "DRT04": dict(finding="F-08", reason="Timezone printed as CET; the PDC publishes the Dortmund sessions in CEST.",
                  source=PDC_SCHEDULE,
                  set=dict(time="2026-10-25 CEST (QF afternoon, SF + final evening)",
                           sourceUrl=PDC_SCHEDULE,
                           sourceName="PDC - 2026 Machineseeker European Championship schedule confirmed",
                           formNotes="PDC official schedule of play: Sunday 25 October, quarter-finals in the afternoon then semi-finals and final in the evening, Westfalenhalle, Dortmund."),
                  verified_on="2026-10-21"),
}


# ---------------------------------------------------------------------------
# F-02 (second limb). Board J named these rows as carrying narrative form/injury
# claims that are contradicted by, or absent from, official sources. This session
# re-verified MLB01 line by line against MLB.com and rewrote it; it did NOT have an
# official source for the claims in the rows below, so per the brief ("never mark
# anything verified without checking it against an official source") their write-ups
# are withdrawn and their confidence capped. Text is preserved on the row, and every
# withdrawal is published on the Flagged for Review page with the link to check.
# ---------------------------------------------------------------------------
NARRATIVE_WITHDRAWAL = {
    "NBA02": "Board J F-02: narrative claims not confirmable on NBA.com at this cut-off.",
    "EL01": ("Fixture confirmed on euroleaguebasketball.net, but the prediction's head-to-head "
             "and attendance claims ('sold-out Belgrade Arena', 'beat Zvezda in two of three') "
             "were sourced to olympics.com / basketnews.com, not a governing body."),
    "CRK01": ("Board J F-02: the series-state and form claims were not re-confirmable on "
              "cricket.com.au by this session."),
    "CRK04": ("Fixture, venue and 1pm PKT start now confirmed on pcb.com.pk, but the prediction's "
              "form claim ('England swept Sri Lanka 3-0 in ODIs in September') is sourced to "
              "Sky Sports, not a governing body."),
    "CRK06": ("Board J F-02: the '18 straight home ODIs' and '3-0 sweep of Bangladesh' claims "
              "were not re-confirmable on cricket.com.au by this session."),
    "RUG01": "Board J F-02: home-record and head-to-head claims sourced to bbc.com, not World Rugby or the IRFU.",
    "RUG02": "Board J F-02: winning-streak and margin claims sourced to bbc.com, not World Rugby or SA Rugby.",
    "RUG05": "Board J F-02: Twickenham head-to-head claims sourced to bbc.com, not World Rugby or the RFU.",
    "RUG06": "Board J F-02: unbeaten-record and points claims sourced to bbc.com, not World Rugby or the FFR.",
    "BDM02": ("Board J F-02: the outright pick rests on wikipedia.org; also an event-level "
              "outright rather than a match, so it cannot be a high-confidence match pick."),
}


def main():
    with open(MATCHES) as f:
        rows = json.load(f)

    log = {
        "schema": "olbg4.remediation/1",
        "session": "arena/47b1b4e2-olbg4 (Board K)",
        "performed_utc": "2026-10-21T07:45Z",
        "input": "data/matches.json (Build D hub, 66 rows)",
        "findings_addressed": ["F-01", "F-02", "F-03", "F-04", "F-08"],
        "rules": [
            "verified=true only where the row's own sourceUrl is a governing-body domain.",
            "A value that could not be confirmed on an official domain is set to \"\" and flagged - never inferred.",
            "Withdrawn prediction text is preserved on the row under k_withdrawn; nothing is deleted.",
            "Every correction stores the official URL it was checked against and the date it was checked.",
        ],
        "official_domains": OFFICIAL_DOMAINS,
        "entry_type_labels": ENTRY_TYPE_LABEL,
        "changes": [],
    }

    n_f01 = n_pred_withdrawn = n_corrected = n_high_capped = n_narrative = 0
    counts = {"match": 0, "result": 0, "tournament": 0, "note": 0}

    for r in rows:
        rid = r["id"]
        before = json.loads(json.dumps(r))
        cls, dom = classify(r.get("sourceUrl"))

        # ---- F-04: label what kind of entry this actually is
        et = ENTRY_TYPE.get(rid, "tournament")
        r["entryType"] = et
        r["entryTypeLabel"] = ENTRY_TYPE_LABEL[et]
        counts[et] += 1

        r["sourceClass"] = cls
        r["sourceDomain"] = dom

        # ---- F-01: a row cannot be 'verified' on a non-governing-body source
        if cls != "official":
            if r.get("verified") is True:
                n_f01 += 1
                log["changes"].append(dict(
                    id=rid, finding="F-01",
                    action="verified true -> false (source is not a governing body)",
                    domain=dom, sourceUrl=r.get("sourceUrl"),
                ))
            r["verified"] = False
            r["flagged"] = True
            r["sourceOfficial"] = False
            reason = (
                "Row's source link is %s, which is not the governing body for this sport, so the "
                "row cannot be published as verified. The link is kept for manual review; no "
                "value has been changed or inferred. Board J finding F-01." % dom
            )
            r["flagReason"] = reason if not r.get("flagReason") else r["flagReason"] + " | " + reason

        # ---- F-02 / F-03 / F-08: targeted, officially re-verified corrections
        c = CORRECTIONS.get(rid)
        if c:
            n_corrected += 1
            withdrawn = None
            if "withdraw" in c and r.get("prediction"):
                withdrawn = {
                    "prediction": r["prediction"],
                    "confidence": before.get("confidence"),
                    "reason": c["withdraw"]["note"],
                    "withdrawn_utc": "2026-10-21T07:45Z",
                }
                n_pred_withdrawn += 1
            elif r.get("prediction") and c["set"].get("prediction") == "":
                withdrawn = {
                    "prediction": r["prediction"],
                    "confidence": before.get("confidence"),
                    "reason": "Replaced by a write-up built only from officially verified facts.",
                    "withdrawn_utc": "2026-10-21T07:45Z",
                }
            if withdrawn:
                r["k_withdrawn"] = withdrawn

            changed = []
            for k, v in c["set"].items():
                if r.get(k) != v:
                    changed.append(dict(field=k, before=r.get(k), after=v))
                # Blank a value that could not be confirmed officially, but keep the old value
                # on the row so nothing is lost and the user can review what was removed.
                if v == "" and k in c.get("preserve_unverified", []) and before.get(k):
                    r.setdefault("k_unverified_values", {})[k] = {
                        "value": before.get(k),
                        "removed_because": "only published on a secondary site; not confirmable on a governing-body domain",
                    }
                r[k] = v

            r["k_verification"] = {
                "checked_by": "arena/47b1b4e2-olbg4 (Board K)",
                "checked_utc": c["verified_on"],
                "official_source": c["source"],
                "finding": c["finding"],
                "what_was_wrong": c["reason"],
            }
            # A correction backed by a governing-body page makes the row official-sourced.
            cls2, dom2 = classify(r["sourceUrl"])
            r["sourceClass"] = cls2
            r["sourceDomain"] = dom2
            if cls2 == "official":
                r["sourceOfficial"] = True
                r["verified"] = True
                # Still flagged: the row was corrected after publication, so it stays on the
                # Flagged for Review page for the user to inspect.
                r["flagged"] = True
                r["flagReason"] = (
                    "Corrected by Board K on 2026-10-21 after Board J finding %s. %s Re-verified "
                    "against %s. Kept on the Flagged page so the change is reviewable."
                    % (c["finding"], c["reason"], c["source"])
                )
            log["changes"].append(dict(
                id=rid, finding=c["finding"], action="field correction",
                official_source=c["source"], what_was_wrong=c["reason"],
                fields=changed, prediction_withdrawn=bool(withdrawn),
            ))

        # ---- F-02 (second limb): withdraw write-ups whose claims are not officially sourced
        if rid in NARRATIVE_WITHDRAWAL and (r.get("prediction") or "").strip():
            r["k_withdrawn"] = {
                "prediction": r["prediction"],
                "confidence": before.get("confidence"),
                "reason": NARRATIVE_WITHDRAWAL[rid],
                "withdrawn_utc": "2026-10-21T07:45Z",
            }
            r["prediction"] = ""
            if r.get("confidence") == "High":
                r["confidence"] = "Medium"
            r["flagged"] = True
            r["flagReason"] = ((r.get("flagReason") or "") + " | " if r.get("flagReason") else "") + (
                "High-confidence write-up withdrawn by Board K (2026-10-21): %s The text is "
                "preserved on the row for review and nothing was inferred or substituted."
                % NARRATIVE_WITHDRAWAL[rid]
            )
            n_narrative += 1
            log["changes"].append(dict(
                id=rid, finding="F-02", action="prediction withdrawn; confidence capped",
                reason=NARRATIVE_WITHDRAWAL[rid], sourceUrl=r.get("sourceUrl"),
            ))

        # ---- High-confidence gate (brief: a high-confidence pick must carry real verified
        # information FROM OFFICIAL SOURCES). A row whose only source is a news aggregator,
        # wiki or betting blog cannot support a High label or a published prediction, so it is
        # capped at Medium and its write-up is withdrawn (preserved, not deleted) and flagged.
        if r.get("confidence") == "High" and r.get("sourceClass") != "official":
            r["confidence"] = "Medium"
            r["flagged"] = True
            r["sourceOfficial"] = False
            if (r.get("prediction") or "").strip():
                r["k_withdrawn"] = {
                    "prediction": r["prediction"],
                    "confidence": "High",
                    "reason": ("Confidence capped at Medium and this write-up withdrawn from "
                               "high-confidence publication: its factual claims are sourced to "
                               "%s, which is not a governing body for this sport. The brief "
                               "requires high-confidence predictions to carry verified "
                               "information from official sources. Text preserved for review; "
                               "nothing here was inferred or replaced."
                               % r.get("sourceDomain")),
                    "withdrawn_utc": "2026-10-21T07:45Z",
                }
                r["prediction"] = ""
                n_high_capped += 1
            r["flagReason"] = (r.get("flagReason") or "") + (
                " | High confidence withdrawn by Board K: the row's source (%s) is not a "
                "governing body, so the pick cannot be published as high-confidence under the "
                "brief. Reduced to Medium." % r.get("sourceDomain")
            ).lstrip(" |")
            log["changes"].append(dict(
                id=rid, finding="F-01/F-02", action="High confidence capped to Medium; prediction withdrawn",
                domain=r.get("sourceDomain"), sourceUrl=r.get("sourceUrl"),
            ))

        # ---- consistency gate: never leave a High row without a prediction
        if r.get("confidence") == "High" and not (r.get("prediction") or "").strip():
            r["confidence"] = "Low"
            r["flagged"] = True
            r["flagReason"] = (r.get("flagReason") or "") + (
                " | Confidence reduced to Low: no verified prediction remains for this row."
            )

    with open(MATCHES, "w") as f:
        json.dump(rows, f, indent=1, ensure_ascii=False)
        f.write("\n")

    os.makedirs(OUTDIR, exist_ok=True)
    log["summary"] = {
        "rows": len(rows),
        "f01_rows_downgraded_to_unverified": n_f01,
        "rows_corrected_against_official_sources": n_corrected,
        "predictions_withdrawn": n_pred_withdrawn,
        "high_confidence_capped_to_medium": n_high_capped,
        "narrative_predictions_withdrawn": n_narrative,
        "entry_types": counts,
        "verified_rows": sum(1 for r in rows if r.get("verified")),
        "flagged_rows": sum(1 for r in rows if r.get("flagged")),
        "high_rows": sum(1 for r in rows if r.get("confidence") == "High"),
        "official_sourced_rows": sum(1 for r in rows if r.get("sourceClass") == "official"),
        "high_rows_without_prediction": sum(
            1 for r in rows if r.get("confidence") == "High" and not (r.get("prediction") or "").strip()),
    }
    with open(os.path.join(OUTDIR, "remediation.json"), "w") as f:
        json.dump(log, f, indent=1, ensure_ascii=False)
        f.write("\n")

    s = log["summary"]
    print("rows                     :", s["rows"])
    print("F-01 downgraded          :", s["f01_rows_downgraded_to_unverified"])
    print("corrected vs official    :", s["rows_corrected_against_official_sources"])
    print("predictions withdrawn    :", s["predictions_withdrawn"])
    print("High capped to Medium    :", s["high_confidence_capped_to_medium"])
    print("narrative withdrawals    :", s["narrative_predictions_withdrawn"])
    print("entry types              :", s["entry_types"])
    print("official-sourced rows    :", s["official_sourced_rows"])
    print("verified rows            :", s["verified_rows"])
    print("flagged rows             :", s["flagged_rows"])
    print("high rows                :", s["high_rows"])
    print("high w/o prediction      :", s["high_rows_without_prediction"])

    if s["high_rows_without_prediction"]:
        print("FAIL: high-confidence row without a prediction", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
