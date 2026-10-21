"""Fact assembly, prediction writing and prediction linting.

Every sentence produced here is built only from fields that arrived in an official
league feed and are stored on the fixture or in the training sample. No news, quotes,
injuries or transfers are invented: if a fact is not in the data it cannot appear in the
copy. Each prediction carries a `facts` list so a reviewer can trace every claim, and
pipeline/verify.py fails the build if any prediction breaks the style rules below.
"""
from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from datetime import datetime

from .records import parse_iso

BANNED = [
    "guaranteed", "guarantee", "lock of the", "sure thing", "can't lose", "cannot lose",
    "risk-free", "risk free", "certainty", "surefire", "banker",
]

NUMBER_WORDS = {0: "no", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}

UNIT = {"basketball": "points", "ice_hockey": "goals", "baseball": "runs"}


# ---------------------------------------------------------------------------
# facts
# ---------------------------------------------------------------------------
def build_form(results: list[dict], sport: str, before: datetime) -> dict[str, dict]:
    """Recent results per team, newest first, from official final scores only."""
    by_team: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        if r.get("sport") != sport:
            continue
        try:
            dt = parse_iso(r["date_utc"])
        except Exception:  # noqa: BLE001
            continue
        if dt >= before:
            continue
        base = {
            "date": r["date_utc"],
            "game_id": r.get("game_id"),
            "game_url": r.get("source_url"),
            "home_name": r.get("home_name"),
            "away_name": r.get("away_name"),
            "season": r.get("season"),
        }
        by_team[str(r["home_id"])].append(
            {**base, "venue": "home", "opponent": str(r["away_id"]),
             "team_score": r["home_score"], "opp_score": r["away_score"]}
        )
        by_team[str(r["away_id"])].append(
            {**base, "venue": "away", "opponent": str(r["home_id"]),
             "team_score": r["away_score"], "opp_score": r["home_score"]}
        )
    out: dict[str, dict] = {}
    for tid, games in by_team.items():
        games.sort(key=lambda g: g["date"], reverse=True)
        for g in games:
            g["won"] = g["team_score"] > g["opp_score"]
        last5 = games[:5]
        wins = sum(1 for g in last5 if g["won"])
        streak = 0
        for g in games:
            if streak == 0:
                streak = 1 if g["won"] else -1
            elif (streak > 0) == g["won"]:
                streak += 1 if g["won"] else -1
            else:
                break
        played = len(last5)
        out[tid] = {
            "games": len(games),
            "last5": last5,
            "wins_last5": wins,
            "losses_last5": played - wins,
            "streak": streak,
            "record": f"{sum(1 for g in games if g['won'])}-{sum(1 for g in games if not g['won'])}",
            "last_game": games[0] if games else None,
            "avg_scored_last5": round(sum(g["team_score"] for g in last5) / played, 1) if played else None,
            "avg_allowed_last5": round(sum(g["opp_score"] for g in last5) / played, 1) if played else None,
        }
    return out


def head_to_head(results: list[dict], home_id: str, away_id: str, before: datetime,
                 limit: int = 3) -> list[dict]:
    meetings = []
    for r in results:
        if {str(r["home_id"]), str(r["away_id"])} != {str(home_id), str(away_id)}:
            continue
        try:
            if parse_iso(r["date_utc"]) >= before:
                continue
        except Exception:  # noqa: BLE001
            continue
        meetings.append(r)
    meetings.sort(key=lambda r: r["date_utc"], reverse=True)
    return meetings[:limit]


# ---------------------------------------------------------------------------
# prose helpers
# ---------------------------------------------------------------------------
def _form_phrase(form: dict, team: str) -> str:
    n = form.get("wins_last5", 0)
    played = len(form.get("last5", []))
    if played == 0:
        return f"{team} have no completed games in our verified sample yet"
    if n == played == 5:
        return f"{team} have won all five of their last five completed games"
    if n == 0 and played == 5:
        return f"{team} have lost all five of their last five completed games"
    if form.get("streak", 0) >= 3:
        return f"{team} arrive on a {form['streak']}-game winning run"
    if form.get("streak", 0) <= -3:
        return f"{team} are on a {abs(form['streak'])}-game losing run"
    return (
        f"{team} have won {NUMBER_WORDS.get(n, n)} of their last "
        f"{NUMBER_WORDS.get(played, played)} completed games"
    )


def _last_result_sentence(form: dict) -> str:
    last = form.get("last_game")
    if not last:
        return ""
    result = "beat" if last["won"] else "lost to"
    opp = last.get("home_name") if last["venue"] == "away" else last.get("away_name")
    opp = opp or "their last opponent"
    venue = "at home" if last["venue"] == "home" else "on the road"
    return f"They most recently {result} {opp} {last['team_score']}-{last['opp_score']} {venue}."


def _clean_record_label(label: str | None) -> str:
    if not label:
        return "record"
    low = label.lower()
    if "regular-season" in low or "regular season" in low:
        return "regular-season record"
    return "record"


def _record_sentence(team: str, record: str | None, label: str | None) -> str:
    if not record:
        return ""
    return f"{team} hold a {record} {_clean_record_label(label)}."


def _num(value: float | None, digits: int = 1) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def _signed(value: float | None) -> str:
    if value is None:
        return "0.0"
    return f"{value:+.1f}"


def _names_selection(text: str) -> bool:
    low = text.lower()
    return any(token in low for token in ("selection:", "backing", "pick is", "taking"))


def _seed(fixture_id: str, market: str) -> int:
    return int(hashlib.sha256(f"{fixture_id}|{market}".encode()).hexdigest()[:8], 16)


WINNER_TEMPLATES = [
    "{open_form}. {record} {last} Our model gives them a {prob}% win probability, priced at "
    "{american}. Selection: {selection}.",

    "{record} {open_form}, and the numbers point the same way. {last} We price {selection} at "
    "{american} after a {prob}% win probability in our model.",

    "{open_form} heading into this one at {venue}. {record} {model} We are backing {selection} "
    "at {american}.",

    "Our model separates these teams by {line} {unit}, and the form table supports it. {open_form}. "
    "{last} {model} Selection: {selection} at {american}.",

    "{open_form}, which is why our model has them {line} {unit} to the good. {record} {last} "
    "{model} The pick is {selection} at {american}.",

    "At {venue}, the model sees a {prob}% win probability for the {fav_short}. {open_form}. "
    "{record} {last} We are taking {selection} at {american}.",

    "{record} {open_form}. {last} That combination gives us a {prob}% win probability and a "
    "{line}-{unit} edge in the ratings. {model} Selection: {selection} at {american}.",

    "Two verified form lines meet here: {open_form}, while the {dog_short} have won {dog_wins} "
    "of their last {dog_played}. {last} Our model lands on {selection} at {american}, a {prob}% "
    "shot with a {line}-{unit} rating gap.",
]

HANDICAP_TEMPLATES = [
    "{open_form}, and our current number is {line} {unit} after opening at {opening_line}. "
    "{record} That move is why {selection} rates {prob}% to cover at {american}.",

    "We opened this spread at {opening_line} and now make it {line} {unit}, a move of "
    "{move} {unit} toward the {fav_short}. {open_form}. {record} Selection: {selection} at {american}.",

    "{record} {open_form}. Our opener of {opening_line} has moved to {line}, which puts "
    "{selection} at a {prob}% cover probability and {american}. {last}",

    "{open_form}. {last} The spread has shifted {move} {unit} from our opening {opening_line} to "
    "{line}, so the value sits with {selection} at {american} ({prob}% to cover).",

    "At {venue} our numbers put the {fav_short} {line} {unit} clear, up from an opening "
    "{opening_line}. {record} {open_form}. Selection: {selection} at {american}.",
]

TOTAL_TEMPLATES = [
    "{open_form}, and their last five have averaged {fav_avg} {unit} combined. {record} "
    "Our total opened at {opening_line} and now sits at {line}, which makes {selection} a "
    "{prob}% play at {american}.",

    "We opened the total at {opening_line} and have moved it to {line}. {open_form}, while "
    "the {dog_short} have conceded {dog_against} {unit} per game across their last five. "
    "Selection: {selection} at {american} ({prob}%).",

    "{record} {open_form}. {last} With the two recent scoring profiles at {fav_avg} and "
    "{dog_avg} {unit}, our number is {line} after an {opening_line} opener. The pick is "
    "{selection} at {american}, rated {prob}%.",

    "Our model projects {line} {unit} here, {move} {unit} away from the {opening_line} opener. "
    "{open_form}, and the {dog_short} are averaging {dog_avg} {unit} across their last five. "
    "{model} Selection: {selection} at {american}.",
]

MODEL_SENTENCES = [
    "That is a {prob}% win probability in our model, priced at {american}.",
    "We price that outcome at {american}, implying {prob}% after our margin.",
    "Our model makes it {prob}%, which we quote at {american}.",
]

TEMPLATES_BY_MARKET = {
    "moneyline": WINNER_TEMPLATES,
    "handicap": HANDICAP_TEMPLATES,
    "total": TOTAL_TEMPLATES,
}


def make_prediction(fixture: dict, analysis: dict, form: dict, h2h: list[dict],
                    source_urls: list[str]) -> dict:
    """Compose the high-confidence write-up for one pick."""
    pick = analysis["headline_pick"]
    sport = fixture["sport"]
    unit = UNIT[sport]
    home, away = fixture["home"], fixture["away"]
    cur = analysis["expected"]["current"]
    opn = analysis["expected"]["opening"]

    if pick["market"] == "total":
        fav_is_home = cur["margin"] >= 0
    else:
        fav_is_home = pick.get("side") == "home"
    fav, dog = (home, away) if fav_is_home else (away, home)
    fav_form = form.get(str(fav["id"]), {})
    dog_form = form.get(str(dog["id"]), {})

    if pick["market"] == "total":
        line = analysis["markets"]["total"]["line"]
        opening_line = analysis["markets"]["total"]["opening_line"]
        move_basis = cur["total"] - opn["total"]
    elif pick["market"] == "handicap":
        line = pick.get("line") or analysis["markets"]["handicap"]["line_home"]
        opening_line = analysis["markets"]["handicap"]["opening_line_home"]
        move_basis = analysis["edge"]["margin"]
    else:
        line = cur["margin"]
        opening_line = opn["margin"]
        move_basis = analysis["edge"]["margin"]

    values = {
        "open_form": _form_phrase(fav_form, fav["name"]),
        "record": _record_sentence(
            fav["name"], fav.get("record"),
            (fixture.get("context") or {}).get("home_record_label" if fav_is_home else "away_record_label"),
        ),
        "last": _last_result_sentence(fav_form),
        "prob": _num(pick["prob_pct"], 1).rstrip("0").rstrip("."),
        "american": pick["american"],
        "line": _signed(line) if pick["market"] != "total" else _num(line),
        "opening_line": _signed(opening_line) if pick["market"] != "total" else _num(opening_line),
        "move": _num(abs(move_basis), 2),
        "unit": unit,
        "selection": pick["selection"],
        "venue": fixture.get("venue") or "their home venue",
        "fav_short": fav["name"].split()[-1],
        "dog_short": dog["name"].split()[-1],
        "dog_wins": NUMBER_WORDS.get(dog_form.get("wins_last5", 0), dog_form.get("wins_last5", 0)),
        "dog_played": NUMBER_WORDS.get(len(dog_form.get("last5", [])), len(dog_form.get("last5", []))),
        "fav_avg": _num(fav_form.get("avg_scored_last5")),
        "fav_against": _num(fav_form.get("avg_allowed_last5")),
        "dog_avg": _num(dog_form.get("avg_scored_last5")),
        "dog_against": _num(dog_form.get("avg_allowed_last5")),
        "model": MODEL_SENTENCES[_seed(fixture["id"], pick["market"]) % len(MODEL_SENTENCES)].format(
            prob=_num(pick["prob_pct"], 1).rstrip("0").rstrip("."), american=pick["american"]
        ),
    }
    templates = TEMPLATES_BY_MARKET[pick["market"]]
    template = templates[_seed(fixture["id"], pick["market"]) % len(templates)]
    text = re.sub(r"\s+", " ", template.format(**values)).replace(" .", ".").strip()
    if not _names_selection(text):
        text += f" Selection: {pick['selection']} at {pick['american']}."

    return {
        "text": text,
        "word_count": len(text.split()),
        "facts": _facts(fixture, analysis, form, h2h, source_urls),
        "template": templates.index(template),
        "market": pick["market"],
        "selection": pick["selection"],
    }


def _facts(fixture, analysis, form, h2h, sources) -> list[dict]:
    home, away = fixture["home"], fixture["away"]
    first_source = (fixture.get("source_urls") or [""])[0]
    facts = [
        {
            "fact": f"{home['name']} vs {away['name']}, scheduled {fixture['start_utc']}",
            "source": first_source,
        },
        {
            "fact": f"Venue: {fixture.get('venue') or 'not published by the league'}",
            "source": first_source,
        },
    ]
    for team in (home, away):
        rec = team.get("record")
        if rec:
            label = (fixture.get("context") or {}).get(
                "home_record_label" if team is home else "away_record_label"
            ) or "record"
            facts.append(
                {"fact": f"{team['name']} {_clean_record_label(label)}: {rec}", "source": first_source}
            )
        f = form.get(str(team["id"]))
        if f and f.get("last5"):
            results = ", ".join(
                f"{'W' if g['won'] else 'L'} {g['team_score']}-{g['opp_score']}" for g in f["last5"]
            )
            facts.append(
                {
                    "fact": f"{team['name']} last five completed games: {results}",
                    "source": f["last5"][0].get("game_url") or first_source,
                }
            )
    ctx = fixture.get("context") or {}
    for key, label in (
        ("home_probable_pitcher", "Home probable pitcher"),
        ("away_probable_pitcher", "Away probable pitcher"),
        ("series", "Series"),
    ):
        if ctx.get(key):
            facts.append({"fact": f"{label}: {ctx[key]}", "source": first_source})
    if h2h:
        facts.append(
            {
                "fact": f"{len(h2h)} previous meeting(s) in the verified sample; most recent "
                        f"{h2h[0]['date_utc'][:10]} ended {h2h[0]['away_score']}-{h2h[0]['home_score']} "
                        f"(away-home)",
                "source": h2h[0].get("source_url") or first_source,
            }
        )
    pick = analysis["headline_pick"]
    facts.append(
        {
            "fact": f"Model win probability {pick['prob_pct']}% priced at {pick['american']}",
            "source": "derived: pipeline/model.py + pipeline/markets.py",
        }
    )
    return facts


def short_rationale(fixture: dict, analysis: dict) -> str:
    pick = analysis["headline_pick"]
    exp = analysis["expected"]["current"]
    unit = UNIT[fixture["sport"]]
    if pick["market"] == "total":
        edge = analysis["edge"]["total"]
        direction = "above" if edge > 0 else "below"
        return (
            f"Our current total is {analysis['markets']['total']['line']:.1f}, {abs(edge):.2f} "
            f"{unit} {direction} our opening number, and the model makes {pick['selection']} a "
            f"{pick['prob_pct']}% chance at {pick['american']}."
        )
    if pick["market"] == "handicap":
        edge = analysis["edge"]["margin"]
        direction = "further" if edge > 0 else "the other way"
        return (
            f"Our current line is {analysis['markets']['handicap']['line_home']:+.1f}, {abs(edge):.2f} "
            f"{unit} {direction} from the opener, and {pick['selection']} covers "
            f"{pick['prob_pct']}% of the time at {pick['american']}."
        )
    return (
        f"Model margin {exp['margin']:+.1f} {unit} and a {pick['prob_pct']}% win probability for "
        f"{pick['selection']}, priced at {pick['american']}. Sample: {pick['sample_games_min']} "
        f"verified games per team."
    )


# ---------------------------------------------------------------------------
# lint
# ---------------------------------------------------------------------------
def lint(predictions: list[dict], min_words: int = 30, max_similarity: float = 0.55) -> list[str]:
    problems: list[str] = []
    seen: list[tuple[str, set[str]]] = []
    for p in predictions:
        pid = p.get("fixture_id", "?")
        text = p.get("text", "")
        words = len(text.split())
        if words < min_words:
            problems.append(f"{pid}: prediction has {words} words (<{min_words})")
        low = text.lower()
        for bad in BANNED:
            if bad in low:
                problems.append(f"{pid}: banned phrase {bad!r}")
        if not _names_selection(text):
            problems.append(f"{pid}: selection not explicit")
        if not p.get("selection"):
            problems.append(f"{pid}: missing selection field")
        tokens = set(re.findall(r"[a-z0-9]+", low))
        for other_id, other in seen:
            if not tokens or not other:
                continue
            j = len(tokens & other) / len(tokens | other)
            if j > max_similarity:
                problems.append(f"{pid}: {j:.2f} similarity with {other_id}")
        seen.append((pid, tokens))
    return problems
