#!/usr/bin/env python3
"""Natural, fact-linked prediction copy for selections that passed every A172 gate."""
from __future__ import annotations

import engine


def _price(value: int) -> str:
    return f"+{value}" if value > 0 else str(value)


def _recent(row: dict, side: str) -> str:
    items = (row.get("recent") or {}).get(side) or []
    return "; ".join(item["text"] for item in items[:2])


def _nhl_players(ev: engine.Evidence, code: str, prefer_goalie: bool = False) -> list[dict]:
    players = [dict(name=name, **item) for name, item in engine.player_facts(ev).items() if item.get("team") == code]
    skaters = [p for p in players if "points" in p or "goals" in p]
    goalies = [p for p in players if "goalsAgainstAverage" in p or "savePctg" in p]
    skaters.sort(key=lambda p: (p.get("points", -1), p.get("goals", -1)), reverse=True)
    goalies.sort(key=lambda p: p.get("goalsAgainstAverage", 99))
    ordered = (goalies + skaters) if prefer_goalie else (skaters + goalies)
    return ordered[:1]


def _player_fact(player: dict) -> tuple[str, str, str]:
    parts = []
    if "goals" in player:
        parts.append(f"{player['goals']} goals")
    if "points" in player:
        parts.append(f"{player['points']} points")
    if "goalsAgainstAverage" in player:
        parts.append(f"{player['goalsAgainstAverage']:.2f} GAA")
    if "savePctg" in player:
        parts.append(f"{player['savePctg']:.3f} save percentage")
    source_key = "nhl_goalies" if "goalsAgainstAverage" in player or "savePctg" in player else "nhl_skaters"
    return player["name"], ", ".join(parts), source_key


def _nhl(row: dict, candidate: dict, ev: engine.Evidence, prediction_id: str) -> dict | None:
    away_recent, home_recent = _recent(row, "away"), _recent(row, "home")
    if not away_recent or not home_recent:
        return None
    market_name = candidate["market"]
    selection = candidate["selection"]
    lower = f"{market_name} {selection}".lower()
    prefer_goalie = "under" in lower or "total" in lower
    away_players = _nhl_players(ev, row["a_code"], prefer_goalie)
    home_players = _nhl_players(ev, row["b_code"], prefer_goalie)
    if not away_players or not home_players:
        return None

    facts = [
        {"label": "Official fixture", "value": f"{row['match']}, {row['start_utc']}, {row['venue']}", "source_url": row["official_url"]},
        {"label": f"{row['side_a']} current form", "value": row["form"]["away"] + f"; away record {row['form']['away_home_away']}", "source_url": row["evidence"]["standings_source"]},
        {"label": f"{row['side_b']} current form", "value": row["form"]["home"] + f"; home record {row['form']['home_home_away']}", "source_url": row["evidence"]["standings_source"]},
        {"label": f"{row['side_a']} recent results", "value": away_recent, "source_url": row["recent"]["away"][0]["source_url"]},
        {"label": f"{row['side_b']} recent results", "value": home_recent, "source_url": row["recent"]["home"][0]["source_url"]},
        {"label": "Season scoring rates", "value": f"{row['side_a']} {row['evidence']['away_gf_pg']:.3f} for / {row['evidence']['away_ga_pg']:.3f} against; {row['side_b']} {row['evidence']['home_gf_pg']:.3f} for / {row['evidence']['home_ga_pg']:.3f} against", "source_url": row["evidence"]["standings_source"]},
        {"label": "My scoring calculation from official rates", "value": f"Expected regulation goals: {row['side_a']} {row['evidence']['expected_goals_away']:.2f}, {row['side_b']} {row['evidence']['expected_goals_home']:.2f}", "source_url": row["evidence"]["standings_source"]},
    ]
    player_sentences = []
    for player in away_players + home_players:
        name, values, source_key = _player_fact(player)
        facts.append({"label": f"{name} ({player['team']}) official season leaders", "value": values, "source_url": ev.url(source_key)})
        player_sentences.append(f"{name} brings {values}")

    a, b = row["side_a"], row["side_b"]
    eh, ea = row["evidence"]["expected_goals_home"], row["evidence"]["expected_goals_away"]
    total = eh + ea
    odds = _price(candidate["fair_american"])
    form_a = row["form"]["away"].split(" (")[0]
    form_h = row["form"]["home"].split(" (")[0]
    l10_a = row["form"]["away"].split("L10 ")[1].split(",")[0]
    l10_h = row["form"]["home"].split("L10 ")[1].split(",")[0]
    players = "; ".join(player_sentences)
    side_name = selection.rsplit(" ", 1)[0]
    if "+1.5" in selection:
        cover_rule = f"A {side_name} win or draw, or a one-goal defeat, covers; a loss by two or more does not."
    elif "+0.5" in selection:
        cover_rule = f"A {side_name} win or draw covers; a regulation defeat does not."
    elif "-0.5" in selection:
        cover_rule = f"A regulation win by {side_name} is required."
    elif "-1.5" in selection:
        cover_rule = f"A regulation win by at least two goals is required for {side_name}."
    else:
        cover_rule = "The stated goal line determines the settlement after regulation."

    if "team total" in lower:
        side_home = b in selection
        team = b if side_home else a
        expectation = eh if side_home else ea
        opponent = a if side_home else b
        text = (
            f"{selection} is the team-total selection at {odds}. {team} owns a {form_h if side_home else form_a} record, "
            f"with a {l10_h if side_home else l10_a} last-ten line, while {opponent} is {form_a if side_home else form_h} and has allowed "
            f"{row['evidence']['away_ga_pg' if side_home else 'home_ga_pg']:.2f} goals per game. "
            f"Recent scores for {team} are {home_recent if side_home else away_recent}; {opponent} posted {away_recent if side_home else home_recent}. "
            f"The scoring expectation for {team} is {expectation:.2f} in regulation, which frames the chosen barrier rather than hiding it. "
            f"{players}. Those player returns keep the attacking threat in view, but the opposing defensive rate and the selected goal line still make this the clearest position. "
            f"Back {selection}; the team total applies to regulation only."
        )
    elif "total goals" in lower:
        text = (
            f"{selection} is the total-goals pick at {odds} for {a} at {b}. "
            f"The away side is {form_a} and the home club {form_h}; their last-ten records are {l10_a} and {l10_h}. "
            f"Latest scores read {away_recent} for {a}, and {home_recent} for {b}. "
            f"Season rates stand at {row['evidence']['away_gf_pg']:.2f} scored and {row['evidence']['away_ga_pg']:.2f} allowed for {a}, "
            f"against {row['evidence']['home_gf_pg']:.2f} and {row['evidence']['home_ga_pg']:.2f} for {b}. "
            f"Combined regulation expectation is {total:.2f}. {players}. "
            f"That blend of team scoring rates and player evidence points toward {selection}, with the half-goal line removing a push."
        )
    elif "regulation 3-way" in lower:
        text = (
            f"{selection} is the regulation three-way selection at {odds}; a win after 60 minutes is required, while a draw loses this ticket. "
            f"The form line has {a} at {form_a} and {b} at {form_h}, with last-ten returns of {l10_a} and {l10_h}. "
            f"Recent results are {away_recent} for {a}, and {home_recent} for {b}. "
            f"Expected regulation goals are {ea:.2f} to {eh:.2f}, with home/away records of {row['form']['away_home_away']} and {row['form']['home_home_away']} adding context. "
            f"{players}. The regulation-only condition is explicit because overtime does not rescue this selection. "
            f"On the combined defensive, scoring and recent-form evidence, take {selection} in the three-way market."
        )
    elif any(word in lower for word in ("puck line", "handicap")):
        text = (
            f"{selection} is the regulation handicap selection at {odds}. "
            f"{a} arrive {form_a}, with {away_recent} in their latest results; {b} are {form_h}, with {home_recent}. "
            f"The last-ten split is {l10_a} against {l10_h}, so this is not simply a season-table argument. "
            f"Expected regulation goals are {ea:.2f} for {a} and {eh:.2f} for {b}, while their home/away records add useful context at {row['form']['away_home_away']} and {row['form']['home_home_away']}. "
            f"{players}. {cover_rule} "
            f"Take {selection}, settled after 60 minutes."
        )
    else:
        text = (
            f"{selection} is the moneyline selection at {odds}, including overtime and a shootout. "
            f"The form line has {a} at {form_a} and {b} at {form_h}, with last-ten returns of {l10_a} and {l10_h}. "
            f"Recent evidence is specific: {a} posted {away_recent}, while {b} posted {home_recent}. "
            f"Scoring rates and location splits feed a regulation expectation of {ea:.2f} to {eh:.2f}; {b} also owns a {row['form']['home_home_away']} home record. "
            f"{players}. There is enough offensive quality on both sides to respect the underdog, but the broader defensive and recent-form balance favors {selection}. "
            f"The moneyline, rather than a regulation-only result, is the intended bet."
        )

    return _finish(row, candidate, prediction_id, text, facts, ev)


def _handball(row: dict, candidate: dict, ev: engine.Evidence, prediction_id: str) -> dict | None:
    away_recent, home_recent = _recent(row, "away"), _recent(row, "home")
    if not away_recent or not home_recent:
        return None
    e = row["evidence"]
    facts = [
        {"label": "Official fixture", "value": f"{row['match']}, {row['start_utc']}", "source_url": row["official_url"]},
        {"label": f"{row['side_a']} current form", "value": row["form"]["away"], "source_url": e["table_source"]},
        {"label": f"{row['side_b']} current form", "value": row["form"]["home"], "source_url": e["table_source"]},
        {"label": f"{row['side_a']} recent results", "value": away_recent, "source_url": row["recent"]["away"][0]["source_url"]},
        {"label": f"{row['side_b']} recent results", "value": home_recent, "source_url": row["recent"]["home"][0]["source_url"]},
        {"label": "Official league scoring totals", "value": f"{row['side_a']} {e['away_gf']}:{e['away_ga']} in {e['away_played']} games; {row['side_b']} {e['home_gf']}:{e['home_ga']} in {e['home_played']} games", "source_url": e["table_source"]},
        {"label": "My scoring calculation from official rates", "value": f"Expected regulation goals: {row['side_a']} {e['expected_goals_away']:.2f}, {row['side_b']} {e['expected_goals_home']:.2f}", "source_url": e["table_source"]},
    ]
    selection = candidate["selection"]
    odds = _price(candidate["fair_american"])
    text = (
        f"{selection} is the regulation match-result pick at {odds}. "
        f"{row['side_a']} bring a {row['form']['away']} season line, compared with {row['form']['home']} for {row['side_b']}. "
        f"The latest programme results add match-level context: {row['side_a']} posted {away_recent}, while {row['side_b']} posted {home_recent}. "
        f"Across the official season samples ({e['away_played']} away and {e['home_played']} home games), the scoring and concession totals support an expectation of {e['expected_goals_away']:.2f} away goals and {e['expected_goals_home']:.2f} home goals. "
        f"That gap matters more than a short winning streak alone because it is grounded in both attack and defence. "
        f"The draw remains a separate regulation outcome, but the away side's superior points return and goal balance make {selection} the preferred position."
    )
    return _finish(row, candidate, prediction_id, text, facts, ev)


def _finish(row: dict, candidate: dict, prediction_id: str, text: str, facts: list[dict], ev: engine.Evidence) -> dict:
    return {
        "prediction_id": prediction_id, "row_id": row["id"], "sport": row["sport"],
        "competition": row["competition"], "match": row["match"], "start_utc": row["start_utc"],
        "venue": row["venue"], "market": candidate["market"], "market_key": candidate["market_key"],
        "selection": candidate["selection"], "prob": candidate["fair_prob"],
        "fair_decimal": candidate["fair_decimal"], "fair_american": candidate["fair_american"],
        "confidence": "High",
        "confidence_reason": "Above 70%, fair American price in the requested band, official fixture, captured OLBG event, adequate sample and recent-result evidence.",
        "prediction_text": " ".join(text.split()), "selection_language": candidate["selection"],
        "word_count": len(" ".join(text.split()).split()), "facts": facts,
        "official_source_url": row["official_url"], "official_source_name": row["official_source_name"],
        "official_capture_id": row["capture_id"], "official_sha256": ev.sha(row["capture_id"]),
        "olbg_url": row["olbg"]["url"], "olbg_event_id": row["olbg"]["event_id"],
        "sample_games": int("".join(ch for ch in row["sample"].split()[0] if ch.isdigit()) or 0),
        "availability_note": "No official injury or team-news report is present in this capture; no availability claim is made.",
    }


def make_prediction(row: dict, candidate: dict, ev: engine.Evidence, prediction_id: str) -> dict | None:
    if row["sport"] == "Ice Hockey":
        return _nhl(row, candidate, ev, prediction_id)
    if row["sport"] == "Handball":
        return _handball(row, candidate, ev, prediction_id)
    return None
