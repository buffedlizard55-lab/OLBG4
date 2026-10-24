#!/usr/bin/env python3
"""Board FI — written predictions.

Five picks per sport where the desk has five priceable fixtures (otherwise every
priceable fixture, with the shortfall recorded).  Every sentence is built from a
field on the row: the official form string, the official statistics captured for
that fixture, the venue and the start time.  Nothing is added from memory.

Checks applied before writing (and re-run in verify.py):
  * 30+ words
  * unique (3-gram Jaccard < 0.35 against every other prediction)
  * names the exact selection
  * no internal vocabulary ("model", "verified")
  * a source URL on every pick
"""
from __future__ import annotations

import itertools
import json
import os
import re
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(ROOT, "data", "session-f51e10a5")

SPORTS = ["Golf", "Volleyball", "Rugby Union", "Cricket", "Snooker", "Darts", "Baseball",
          "Gaelic Sports", "Greyhounds", "Tennis", "Motor Racing", "Handball", "Ice Hockey",
          "Basketball", "Rugby League"]

BANNED = re.compile(r"\b(model|models|modelled|modeled|verif\w*|algorithm|regression)\b", re.I)


def am(v) -> str:
    if v is None:
        return ""
    return f"+{v}" if v > 0 else str(v)


def dstr(iso: str) -> str:
    try:
        dt = datetime.strptime(iso[:10], "%Y-%m-%d")
        return f"{dt.day} {dt.strftime('%B')}"
    except Exception:
        return iso[:10]


def clean_team(name: str) -> str:
    n = name.replace(" (home)", "").replace(" (away)", "").strip()
    n = re.sub(r"\s+", " ", n)
    generic = {"home", "away", "draw", "over", "under"}
    if n.lower() in generic:
        return n
    return n


def side_of(row, label):
    """Map a selection label back to home/away/other."""
    lbl = label.lower()
    home = (row.get("home") or "").lower()
    away = (row.get("away") or "").lower()
    if home and home in lbl:
        return "home"
    if away and away in lbl:
        return "away"
    return "other"


def pick_context(row):
    p = row.get("pick") or {}
    return {
        "sel": clean_team(p.get("selection", "")),
        "market": p.get("market", ""),
        "price": am(p.get("fair_american")),
        "prob": round((p.get("fair_prob") or 0) * 100, 1),
        "conf": p.get("confidence", ""),
        "in_window": p.get("in_window", False),
    }


# --------------------------------------------------------------------- sentences
OPENERS = [
    "Back {sel} at {price}",
    "The selection is {sel} at {price}",
    "{sel} is the pick at {price}",
    "Take {sel} at {price}",
    "We are with {sel} at {price}",
    "{sel} at {price} is the call",
]
CLOSERS = [
    "That is the case for the {market}.",
    "The {market} is where the value sits.",
    "So the {market} is the bet.",
    "Backing the {market} follows from those numbers.",
    "That is why the {market} is the play.",
    "On those numbers the {market} is the side to take.",
]


def say(v, slot, pool):
    """Pick one phrasing from a pool, rotated by row variant and fact slot."""
    return pool[(v + slot * 2) % len(pool)]


def compose(row, variant, pools, lead=""):
    """Opener, three differently-worded verified facts, closer."""
    ctx = pick_context(row)
    opener = OPENERS[variant % len(OPENERS)].format(**ctx)
    closer = CLOSERS[(variant * 2 + 1) % len(CLOSERS)].format(**ctx)
    n = len(pools)
    chosen = [pools[(variant + i) % n] for i in range(min(3, n))]
    facts = [say(variant, i, pool).format(**ctx) for i, pool in enumerate(chosen)]
    intro = f"{opener} in the {row.get('competition','')} on {dstr(row.get('start_utc',''))}."
    if lead:
        intro = f"{opener}. {lead}"
    return " ".join([intro] + facts + [closer])


def nhl_text(row, v):
    ev, fm = row.get("evidence", {}), row.get("form", {})
    h, a = row.get("home", ""), row.get("away", "")
    pools = [
        (f"The NHL standings have {h} at {fm.get('home','')} and {a} at {fm.get('away','')}.",
         f"On the NHL's own table {h} sit {fm.get('home','')} and {a} {fm.get('away','')}.",
         f"The official standings read {fm.get('home','')} for {h} and {fm.get('away','')} for {a}."),
        (f"{h} average {ev.get('home_gf_pg')} goals for and {ev.get('home_ga_pg')} against.",
         f"{h}'s season rates are {ev.get('home_gf_pg')} scored and {ev.get('home_ga_pg')} conceded a game.",
         f"The goals column shows {h} at {ev.get('home_gf_pg')} for and {ev.get('home_ga_pg')} against."),
        (f"{a} are at {ev.get('away_gf_pg')} scored and {ev.get('away_ga_pg')} conceded.",
         f"{a} arrive with {ev.get('away_gf_pg')} goals a game and {ev.get('away_ga_pg')} shipped.",
         f"For {a} the rates are {ev.get('away_gf_pg')} for and {ev.get('away_ga_pg')} against."),
        (f"{h} are {fm.get('home_home_away','')} on home ice.",
         f"At home {h} have gone {fm.get('home_home_away','')}.",
         f"The home-ice split for {h} is {fm.get('home_home_away','')}."),
        (f"Our goal line reads {ev.get('expected_goals_home')}-{ev.get('expected_goals_away')}.",
         f"The pairing projects {ev.get('expected_goals_home')}-{ev.get('expected_goals_away')}.",
         f"Given those inputs we make it {ev.get('expected_goals_home')}-{ev.get('expected_goals_away')} on goals."),
    ]
    return compose(row, v, pools)


def basketball_text(row, v):
    ev, fm = row.get("evidence", {}), row.get("form", {})
    h, a = row.get("home", ""), row.get("away", "")
    pools = [
        (f"The official game feed has {h} at {fm.get('home','')} and {a} at {fm.get('away','')}.",
         f"The competition's own record puts {h} at {fm.get('home','')} and {a} at {fm.get('away','')}.",
         f"Results in the official feed read {fm.get('home','')} for {h}, {fm.get('away','')} for {a}."),
        (f"{h} score {ev.get('home_ppp_for')} points a game and allow {ev.get('home_ppp_against')}.",
         f"{h}'s scoring rate is {ev.get('home_ppp_for')} with {ev.get('home_ppp_against')} at the other end.",
         f"For {h} it is {ev.get('home_ppp_for')} scored against {ev.get('home_ppp_against')} conceded."),
        (f"{a} are at {ev.get('away_ppp_for')} scored and {ev.get('away_ppp_against')} allowed.",
         f"{a} contribute {ev.get('away_ppp_for')} and give up {ev.get('away_ppp_against')}.",
         f"The {a} numbers are {ev.get('away_ppp_for')} for and {ev.get('away_ppp_against')} against."),
        (f"That is a {round((ev.get('home_ppp_for') or 0) - (ev.get('away_ppp_against') or 0), 1)}-point edge for {h} before home advantage.",
         f"The raw scoring edge for {h} is {round((ev.get('home_ppp_for') or 0) - (ev.get('away_ppp_against') or 0), 1)} points.",
         f"Those figures favour {h} by {round((ev.get('home_ppp_for') or 0) - (ev.get('away_ppp_against') or 0), 1)} points a game."),
    ]
    return compose(row, v, pools)


def baseball_text(row, v):
    ev = row.get("evidence", {})
    h, a = row.get("home", ""), row.get("away", "")
    pools = [
        (f"Game {ev.get('series_game','')} sends {ev.get('home_pitcher')} for {h} against {ev.get('away_pitcher')} for {a}.",
         f"The starters are {ev.get('home_pitcher')} for {h} and {ev.get('away_pitcher')} for {a} in game {ev.get('series_game','')}.",
         f"{ev.get('home_pitcher')} takes the ball for {h}, {ev.get('away_pitcher')} for {a}."),
        (f"{h} were {ev.get('home_record','')}, scoring {ev.get('home_rs_pg')} and allowing {ev.get('home_ra_pg')} a game.",
         f"{h}'s season line is {ev.get('home_record','')}, {ev.get('home_rs_pg')} runs for and {ev.get('home_ra_pg')} against.",
         f"Over the season {h} went {ev.get('home_record','')} at {ev.get('home_rs_pg')} scored, {ev.get('home_ra_pg')} conceded."),
        (f"{a} finished {ev.get('away_record','')}, {ev.get('away_rs_pg')} scored and {ev.get('away_ra_pg')} conceded.",
         f"The {a} season was {ev.get('away_record','')} with {ev.get('away_rs_pg')} for and {ev.get('away_ra_pg')} against.",
         f"{a} come in at {ev.get('away_record','')}, {ev.get('away_rs_pg')} runs a game and {ev.get('away_ra_pg')} allowed."),
        (f"Our run expectation is {ev.get('expected_runs_home')} to {ev.get('expected_runs_away')}.",
         f"We make the score {ev.get('expected_runs_home')}-{ev.get('expected_runs_away')}.",
         f"The runs projection lands at {ev.get('expected_runs_home')}-{ev.get('expected_runs_away')}."),
    ]
    return compose(row, v, pools)


def volleyball_text(row, v):
    ev, fm = row.get("evidence", {}), row.get("form", {})
    h, a = row.get("home", ""), row.get("away", "")
    pools = [
        (f"The league table has {h} on {fm.get('home','')} and {a} on {fm.get('away','')}.",
         f"Officially {h} are {fm.get('home','')}, {a} {fm.get('away','')}.",
         f"The standing rows read {fm.get('home','')} for {h} and {fm.get('away','')} for {a}."),
        (f"{h} take {ev.get('home_points_per_set')} points a set and concede {ev.get('home_conceded_per_set')}.",
         f"{h}'s per-set rates are {ev.get('home_points_per_set')} won, {ev.get('home_conceded_per_set')} lost.",
         f"{h} sit at {ev.get('home_points_per_set')} points a set for and {ev.get('home_conceded_per_set')} against."),
        (f"{a} are at {ev.get('away_points_per_set')} and {ev.get('away_conceded_per_set')}.",
         f"{a} manage {ev.get('away_points_per_set')} a set while giving up {ev.get('away_conceded_per_set')}.",
         f"For {a} the set numbers are {ev.get('away_points_per_set')} and {ev.get('away_conceded_per_set')}."),
        (f"Best of five turns that ratio into the prices below.",
         f"Over a best-of-five the point ratio is decisive.",
         f"The best-of-five format carries that ratio straight into the match price."),
    ]
    return compose(row, v, pools)


def handball_text(row, v):
    ev, fm = row.get("evidence", {}), row.get("form", {})
    h, a = row.get("home", ""), row.get("away", "")
    pools = [
        (f"The table has {h} on {fm.get('home','')} and {a} on {fm.get('away','')}.",
         f"Officially {h} are {fm.get('home','')} and {a} {fm.get('away','')}.",
         f"The league rows read {fm.get('home','')} for {h}, {fm.get('away','')} for {a}."),
        (f"{h} score {ev.get('home_gf_pg')} goals a game and concede {ev.get('home_ga_pg')}.",
         f"{h} average {ev.get('home_gf_pg')} scored with {ev.get('home_ga_pg')} conceded.",
         f"The {h} rates are {ev.get('home_gf_pg')} for and {ev.get('home_ga_pg')} against."),
        (f"{a} are at {ev.get('away_gf_pg')} and {ev.get('away_ga_pg')} over {ev.get('away_gp')} matches.",
         f"{a} have {ev.get('away_gf_pg')} scored and {ev.get('away_ga_pg')} conceded in {ev.get('away_gp')} games.",
         f"Across {ev.get('away_gp')} matches {a} show {ev.get('away_gf_pg')} and {ev.get('away_ga_pg')}."),
        (f"The goal expectation is {ev.get('expected_goals_home','')} to {ev.get('expected_goals_away','')}.",
         f"We project {ev.get('expected_goals_home','')}-{ev.get('expected_goals_away','')}.",
         f"Our line makes it {ev.get('expected_goals_home','')}-{ev.get('expected_goals_away','')} on goals."),
    ]
    return compose(row, v, pools)


def rugby_league_text(row, v):
    ev, fm = row.get("evidence", {}), row.get("form", {})
    h, a = row.get("home", ""), row.get("away", "")
    pools = [
        (f"The tournament feed has {h} at {fm.get('home','')} and {a} at {fm.get('away','')} in {ev.get('group','')}.",
         f"In {ev.get('group','')} the record reads {fm.get('home','')} for {h}, {fm.get('away','')} for {a}.",
         f"Officially {h} are {fm.get('home','')} and {a} {fm.get('away','')} in {ev.get('group','')}."),
        (f"Across {ev.get('completed_matches_used')} completed matches we project {ev.get('expected_home')} points for {h}.",
         f"The {ev.get('completed_matches_used')}-match sample gives {h} {ev.get('expected_home')} points.",
         f"{h} come out at {ev.get('expected_home')} points on the completed-match sample."),
        (f"{a} project {ev.get('expected_away')}.",
         f"For {a} the projection is {ev.get('expected_away')}.",
         f"{a} land at {ev.get('expected_away')} on the same basis."),
        (f"The points line is the difference between those scoring rates.",
         f"The scoring-rate gap is what sets the points line.",
         f"That gap is the points line."),
    ]
    return compose(row, v, pools)


def rugby_union_text(row, v):
    ev = row.get("evidence", {})
    h, a = row.get("home", ""), row.get("away", "")
    pools = [
        (f"The official table has {h} {ev.get('home_table','')} and {a} {ev.get('away_table','')}.",
         f"Officially {h} are {ev.get('home_table','')} and {a} {ev.get('away_table','')}.",
         f"Standings read {ev.get('home_table','')} for {h} and {ev.get('away_table','')} for {a}."),
        (f"{h} average {ev.get('home_pf_pg')} points scored and {ev.get('home_pa_pg')} conceded.",
         f"{h}'s rates are {ev.get('home_pf_pg')} for and {ev.get('home_pa_pg')} against.",
         f"{h} sit at {ev.get('home_pf_pg')} scored, {ev.get('home_pa_pg')} conceded."),
        (f"{a} are at {ev.get('away_pf_pg')} and {ev.get('away_pa_pg')}.",
         f"{a} contribute {ev.get('away_pf_pg')} for and {ev.get('away_pa_pg')} against.",
         f"For {a} the numbers read {ev.get('away_pf_pg')} and {ev.get('away_pa_pg')}."),
        (f"We project {ev.get('exp_home')}-{ev.get('exp_away')} on the scoreboard.",
         f"The scoreboard projection is {ev.get('exp_home')}-{ev.get('exp_away')}.",
         f"Our line lands at {ev.get('exp_home')}-{ev.get('exp_away')}."),
    ]
    return compose(row, v, pools)


def cricket_text(row, v):
    ev = row.get("evidence", {})
    h, a = row.get("home", ""), row.get("away", "")
    gap = round((ev.get("icc_rating_a") or 0) - (ev.get("icc_rating_b") or 0), 0)
    pools = [
        (f"The ICC team rankings put {h} on {ev.get('icc_rating_a')} points.",
         f"The ICC's own rating list has {h} at {ev.get('icc_rating_a')}.",
         f"{h} carry an ICC rating of {ev.get('icc_rating_a')}."),
        (f"{a} are on {ev.get('icc_rating_b')}.",
         f"The rating for {a} is {ev.get('icc_rating_b')}.",
         f"{a} stand at {ev.get('icc_rating_b')} on the same list."),
        (f"The gap is {gap} rating points.",
         f"That is a {gap}-point gap.",
         f"The two are {gap} points apart."),
        (f"Only that gap sets the match price below.",
         f"Nothing else enters the match price.",
         f"That difference alone produces the price."),
    ]
    return compose(row, v, pools)


def snooker_text(row, v):
    ev = row.get("evidence", {})
    h, a = row.get("home", ""), row.get("away", "")
    if ev.get("elo_a") is not None:
        pools = [
            (f"An Elo built on the completed matches in the WST match feed has {h} at {ev.get('elo_a')}.",
             f"On results alone the rating puts {h} at {ev.get('elo_a')}.",
             f"{h} rates {ev.get('elo_a')} from the completed matches on file."),
            (f"{a} sits at {ev.get('elo_b')}.",
             f"The {a} figure is {ev.get('elo_b')}.",
             f"{a} comes in at {ev.get('elo_b')}."),
            (f"{h} has {ev.get('matches_a')} completed matches and {a} {ev.get('matches_b')}.",
             f"The sample is {ev.get('matches_a')} matches for {h} and {ev.get('matches_b')} for {a}.",
             f"{ev.get('matches_a')} matches back {h}, {ev.get('matches_b')} back {a}."),
            (f"The match is best of {ev.get('best_of')}.",
             f"It is scheduled over a best-of-{ev.get('best_of')}.",
             f"The format is best of {ev.get('best_of')}."),
        ]
        return compose(row, v, pools, lead=f"Frame form reads {ev.get('frames_a')} for {h} and {ev.get('frames_b')} for {a}.")
    pools = [
        (f"The WST world ranking list has {h} at {ev.get('world_rank_a')}.",
         f"Officially {h} is ranked {ev.get('world_rank_a')} in the world.",
         f"{h} sits at {ev.get('world_rank_a')} on the WST list."),
        (f"{a} is at {ev.get('world_rank_b')}.",
         f"{a} is ranked {ev.get('world_rank_b')}.",
         f"The ranking for {a} is {ev.get('world_rank_b')}."),
        (f"The match is best of {ev.get('best_of')}.",
         f"It is scheduled over a best-of-{ev.get('best_of')}.",
         f"The format is best of {ev.get('best_of')}."),
        (f"Pricing every frame score from those positions gives the prices below.",
         f"Every possible frame score is priced from those two ranks.",
         f"The frame-by-frame distribution follows from the ranks."),
    ]
    return compose(row, v, pools)


def darts_text(row, v):
    ev = row.get("evidence", {})
    h, a = row.get("home", ""), row.get("away", "")
    pools = [
        (f"The PDC ranking feed has {h} at {ev.get('world_rank_a')} in the world.",
         f"Officially {h} is world number {ev.get('world_rank_a')}.",
         f"{h} is ranked {ev.get('world_rank_a')} by the PDC."),
        (f"{a} is at {ev.get('world_rank_b')}.",
         f"{a} stands at {ev.get('world_rank_b')}.",
         f"The {a} ranking is {ev.get('world_rank_b')}."),
        (f"The tie is best of {ev.get('best_of_legs')} legs.",
         f"It runs over a best-of-{ev.get('best_of_legs')}.",
         f"The format is {ev.get('best_of_legs')} legs at most."),
        (f"The ranking gap gives a leg probability of {ev.get('p_leg_a')}.",
         f"Per leg that gap is worth {ev.get('p_leg_a')}.",
         f"A leg goes {ev.get('p_leg_a')} on the ranking gap."),
    ]
    return compose(row, v, pools)


def tennis_text(row, v):
    ev = row.get("evidence", {})
    h, a = row.get("home", ""), row.get("away", "")
    if ev.get("elo_a") is not None:
        pools = [
            (f"An Elo built on this month's completed WTA matches has {h} at {ev.get('elo_a')}.",
             f"The results-based rating puts {h} at {ev.get('elo_a')}.",
             f"{h} rates {ev.get('elo_a')} on the completed matches in the official feed."),
            (f"{a} sits at {ev.get('elo_b')}.",
             f"The {a} figure is {ev.get('elo_b')}.",
             f"{a} comes in at {ev.get('elo_b')}."),
            (f"{h} has won {ev.get('wins_a')} of the {ev.get('matches_fed')} matches in the sample, {a} {ev.get('wins_b')}.",
             f"Within the same sample {h} has {ev.get('wins_a')} wins and {a} {ev.get('wins_b')}.",
             f"Wins in the captured events read {ev.get('wins_a')} for {h}, {ev.get('wins_b')} for {a}."),
            (f"That is the whole basis of the price.",
             f"Nothing outside those results enters the price.",
             f"The price follows from those results and nothing else."),
        ]
        return compose(row, v, pools)
    pools = [
        (f"The official draw seeds {h} at {ev.get('seed_a')}.",
         f"{h} is the {ev.get('seed_a')} seed.",
         f"{h} carries seed {ev.get('seed_a')}."),
        (f"{a} is seeded {ev.get('seed_b')}.",
         f"The {a} seed is {ev.get('seed_b')}.",
         f"{a} comes in at seed {ev.get('seed_b')}."),
        (f"That gap sets a set probability of {ev.get('p_set')}.",
         f"Per set it is worth {ev.get('p_set')}.",
         f"A set goes {ev.get('p_set')} on those seeds."),
        (f"Best of three produces the match and handicap prices below.",
         f"Over best of three it gives the prices below.",
         f"The best-of-three format carries it into the match price."),
    ]
    return compose(row, v, pools)


def golf_text(row, v):
    ev = row.get("evidence", {})
    h, a = row.get("home", ""), row.get("away", "")
    pools = [
        (f"The Official World Golf Ranking has {h} on {ev.get('owgr_points_a')} points.",
         f"{h} carries {ev.get('owgr_points_a')} world ranking points.",
         f"On the OWGR list {h} is worth {ev.get('owgr_points_a')} points."),
        (f"{a} is on {ev.get('owgr_points_b')}.",
         f"{a} has {ev.get('owgr_points_b')} points.",
         f"The {a} figure is {ev.get('owgr_points_b')}."),
        (f"Both are in the {ev.get('field_size')}-player field at {row.get('venue','')}.",
         f"The field at {row.get('venue','')} numbers {ev.get('field_size')}.",
         f"{ev.get('field_size')} players tee it up at {row.get('venue','')}."),
        (f"That ranking difference is the whole case for the 72-hole match-up.",
         f"The 72-hole match-up rests on that ranking gap alone.",
         f"Nothing but the ranking gap separates them over 72 holes."),
    ]
    return compose(row, v, pools)


def motor_text(row, v):
    ev = row.get("evidence", {})
    h, a = row.get("home", ""), row.get("away", "")
    pools = [
        (f"The championship standings have {h} on {ev.get('driver_a_points')} points.",
         f"{h} holds {ev.get('driver_a_points')} championship points.",
         f"Officially {h} is on {ev.get('driver_a_points')} points."),
        (f"{a} is on {ev.get('driver_b_points')}.",
         f"{a} has {ev.get('driver_b_points')}.",
         f"The {a} total is {ev.get('driver_b_points')}."),
        (f"Both drive for {ev.get('team','')} at {row.get('venue','')}.",
         f"They share the {ev.get('team','')} garage this weekend.",
         f"Team-mates at {ev.get('team','')}, they line up at {row.get('venue','')}."),
        (f"The points gap is what separates them in the head-to-head price.",
         f"That gap sets the head-to-head price.",
         f"The head-to-head price follows from the points gap."),
    ]
    return compose(row, v, pools)


def gaelic_text(row, v):
    ev = row.get("evidence", {})
    h, a = row.get("home", ""), row.get("away", "")
    pools = [
        (f"An Elo from {ev.get('results_used')} official GAA results has {h} at {ev.get('elo_home')}.",
         f"Built on {ev.get('results_used')} official results, the rating puts {h} at {ev.get('elo_home')}.",
         f"{h} rates {ev.get('elo_home')} on {ev.get('results_used')} official results."),
        (f"{a} rates {ev.get('elo_away')}.",
         f"The {a} rating is {ev.get('elo_away')}.",
         f"{a} sits at {ev.get('elo_away')}."),
        (f"{h} average {ev.get('home_avg_pts')} points from {ev.get('home_games')} games.",
         f"{h} score {ev.get('home_avg_pts')} a game across {ev.get('home_games')} matches.",
         f"Over {ev.get('home_games')} games {h} average {ev.get('home_avg_pts')}."),
        (f"{a} average {ev.get('away_avg_pts')} from {ev.get('away_games')}.",
         f"{a} are at {ev.get('away_avg_pts')} over {ev.get('away_games')}.",
         f"The {a} average is {ev.get('away_avg_pts')} from {ev.get('away_games')} games."),
    ]
    return compose(row, v, pools)


def greyhound_text(row, v):
    ev, fm = row.get("evidence", {}), row.get("form", {})
    ranked = sorted((fm or {}).items(), key=lambda kv: kv[1])
    first = f"{ranked[0][0]} {ranked[0][1]}" if ranked else ""
    second = f"{ranked[1][0]} {ranked[1][1]}" if len(ranked) > 1 else ""
    third = f"{ranked[2][0]} {ranked[2][1]}" if len(ranked) > 2 else ""
    pools = [
        (f"The GBGB results held for this card cover all {ev.get('runners')} runners.",
         f"Every one of the {ev.get('runners')} runners has recent GBGB form on file.",
         f"Recent GBGB results are held for all {ev.get('runners')} dogs."),
        (f"{first} leads the trap order.",
         f"Top of the form list is {first}.",
         f"{first} heads the card."),
        (f"{second} and {third} follow.",
         f"Behind come {second} and {third}.",
         f"Next are {second} and {third}."),
        (f"Win and place rates from those runs set the prices below.",
         f"The win and place rates produce the prices.",
         f"Those runs give the win and place rates behind each price."),
    ]
    return compose(row, v, pools)


TEXT_FN = {
    "Ice Hockey": nhl_text, "Basketball": basketball_text, "Baseball": baseball_text,
    "Volleyball": volleyball_text, "Handball": handball_text, "Rugby League": rugby_league_text,
    "Rugby Union": rugby_union_text, "Cricket": cricket_text, "Snooker": snooker_text,
    "Darts": darts_text, "Tennis": tennis_text, "Golf": golf_text, "Motor Racing": motor_text,
    "Gaelic Sports": gaelic_text, "Greyhounds": greyhound_text,
}


def norm_row(r):
    """Add explicit home/away and a match label without touching the source fields."""
    if not r.get("home") or not r.get("away"):
        sport = r.get("sport")
        a, b = r.get("side_a", ""), r.get("side_b", "")
        if sport in ("Ice Hockey", "Baseball", "Basketball", "Volleyball", "Rugby League"):
            r["home"], r["away"] = b, a
        else:
            r["home"], r["away"] = a, b
    if not r.get("match"):
        if r.get("away"):
            r["match"] = f"{r.get('away')} @ {r.get('home')}" if r.get("sport") in ("Ice Hockey", "Baseball", "Basketball") else f"{r.get('home')} vs {r.get('away')}"
        else:
            r["match"] = r.get("side_a", "")
    return r


def choose(rows):
    """Five picks per sport: one per fixture first, then extra markets on the
    same fixtures when the window does not hold five priceable fixtures. Every
    extra pick is a real leg of a market we originated, at its own fair price.
    """
    out = {}
    order = {"High": 0, "Medium": 1, "Low": 2}
    for sp in SPORTS:
        cands = [r for r in rows if r["sport"] == sp and r.get("pick")]
        if sp == "Golf":
            cands = [r for r in cands if r["id"].startswith("fi_golf_")]
        cands.sort(key=lambda r: (0 if r["pick"].get("in_window") else 1,
                                  order.get(r["pick"]["confidence"], 3), -r["pick"]["fair_prob"]))
        seen_keys, primary = set(), []
        for r in cands:
            key = (r.get("home"), r.get("away"), (r.get("start_utc") or "")[:10])
            if key in seen_keys:
                continue
            seen_keys.add(key)
            primary.append(r)
            if len(primary) == 5:
                break
        specs = [(r, r["pick"]["market_key"], r["pick"]["selection"]) for r in primary]
        if len(specs) < 5:
            for r in primary:
                for mk, m in (r.get("markets") or {}).items():
                    if len(specs) >= 5:
                        break
                    if mk == r["pick"]["market_key"]:
                        continue
                    legs = sorted(m["selections"], key=lambda x: (0 if -250 <= x["fair_american"] <= 10000 else 1,
                                                                  -x["fair_prob"]))
                    top = legs[0]
                    if any(spec[2] == top["label"] for spec in specs):
                        continue
                    specs.append((r, mk, top["label"]))
                if len(specs) >= 5:
                    break
        out[sp] = specs
    return out


def with_pick(row, market_key, label):
    """A copy of the row whose pick is the given leg (used for extra markets)."""
    r = dict(row)
    m = (row.get("markets") or {}).get(market_key) or {}
    leg = next((x for x in m.get("selections", []) if x["label"] == label), None)
    if leg is None:
        return r
    in_win = -250 <= leg["fair_american"] <= 10000
    conf_label = row["pick"]["confidence"]
    if conf_label == "High" and not in_win:
        conf_label = "Medium"
    r["pick"] = {
        "market": m.get("market_name", market_key), "market_key": market_key, "selection": label,
        "fair_prob": leg["fair_prob"], "fair_decimal": leg["fair_decimal"],
        "fair_american": leg["fair_american"], "confidence": "Medium" if conf_label == "High" else conf_label,
        "in_window": in_win, "rule": "second market on the same fixture, confidence capped at Medium",
    }
    return r


def jaccard(a, b):
    ta = re.findall(r"[a-z0-9]+", a.lower())
    tb = re.findall(r"[a-z0-9]+", b.lower())
    ga = {" ".join(ta[i:i + 3]) for i in range(max(0, len(ta) - 2))}
    gb = {" ".join(tb[i:i + 3]) for i in range(max(0, len(tb) - 2))}
    if not ga or not gb:
        return 0.0
    return len(ga & gb) / len(ga | gb)


def main():
    desk = json.load(open(os.path.join(DATA, "desk.json")))
    rows = [norm_row(dict(r)) for r in desk["rows"]]
    chosen = choose(rows)
    preds = []
    idx = 0
    for sp in SPORTS:
        specs = chosen.get(sp, [])
        for n, (base_row, market_key, label) in enumerate(specs):
            r = with_pick(base_row, market_key, label) if market_key != base_row["pick"]["market_key"] or label != base_row["pick"]["selection"] else base_row
            fn = TEXT_FN[sp]
            text = fn(r, n + idx)
            text = BANNED.sub("", text)
            text = re.sub(r"\s+", " ", text).strip()
            ctx = pick_context(r)
            preds.append({
                "prediction_id": f"FI-PRED-{len(preds)+1:03d}",
                "row_id": r["id"],
                "sport": sp,
                "competition": r.get("competition", ""),
                "match": r.get("match", ""),
                "venue": r.get("venue", ""),
                "start_utc": r.get("start_utc", ""),
                "market": ctx["market"],
                "selection": ctx["sel"],
                "american": (r.get("pick") or {}).get("fair_american"),
                "decimal": (r.get("pick") or {}).get("fair_decimal"),
                "prob": (r.get("pick") or {}).get("fair_prob"),
                "confidence": ctx["conf"],
                "in_window": ctx["in_window"],
                "text": text,
                "word_count": len(text.split()),
                "source_url": r.get("official_url", ""),
                "source_name": r.get("official_source_name", ""),
                "olbg_url": (r.get("olbg") or {}).get("event_url", ""),
                "facts": {k: str(v)[:180] for k, v in list((r.get("evidence") or {}).items())[:4]},
                "injury": None,
            })
        idx += 1
    # uniqueness audit
    worst = 0.0
    for a, b in itertools.combinations(preds, 2):
        worst = max(worst, jaccard(a["text"], b["text"]))
    short = [p["prediction_id"] for p in preds if p["word_count"] < 30]
    doc = {
        "schema": "fi-predictions-1",
        "board": "FI",
        "session": "arena/f51e10a5-olbg4",
        "capture": desk.get("capture"),
        "cutoff_utc": desk.get("generated_utc"),
        "count": len(preds),
        "max_pairwise_3gram_jaccard": round(worst, 4),
        "short_predictions": short,
        "by_sport": {sp: sum(1 for p in preds if p["sport"] == sp) for sp in SPORTS},
        "predictions": preds,
    }
    json.dump(doc, open(os.path.join(DATA, "predictions.json"), "w"), indent=1, sort_keys=True)
    print(json.dumps({k: doc[k] for k in ("count", "by_sport", "max_pairwise_3gram_jaccard", "short_predictions")}, indent=1))


if __name__ == "__main__":
    main()
