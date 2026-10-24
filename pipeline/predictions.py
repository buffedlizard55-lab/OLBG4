"""Compose written predictions from verified facts.

Each prediction is assembled from five independent sentence blocks. The caller passes a
`variant` integer (unique per published pick in a snapshot), which is decoded into a
mixed-radix combination of block options. Two predictions therefore never share the same
structure until every combination is exhausted, which is what keeps the copy from
reading like a mail-merge.

Only fields that arrived in an official league feed are available to the templates:
record, last-five results with scores, venue, series context, probable pitchers, and our
own line and probability. Nothing speculative can be inserted.
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
    # "model" and "verify/verified/verification" are internal engineering terms; the
    # owner does not want them surfacing in the published, human-facing prediction text.
    "model", "verify", "verified", "verification",
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
def _wins_phrase(n: int) -> str:
    return {0: "none", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}.get(n, str(n))


def _wins_clause(n: int) -> str:
    """A grammatical clause for a 0-5 win count over the last five games."""
    n = int(n or 0)
    words = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}
    if n <= 0:
        return "have not won any of their last five"
    if n >= 5:
        return "have won each of their last five"
    return f"have won {words.get(n, n)} of their last five"


def _num(value: float | None, digits: int = 1) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


def _last_sentence(form: dict, opponent_name: str | None) -> str:
    last = form.get("last_game")
    if not last:
        return ""
    opp = opponent_name or "their last opponent"
    score = f"{last['team_score']}-{last['opp_score']}"
    where = "at home" if last["venue"] == "home" else "on the road"
    if last["won"]:
        return f"They most recently beat {opp} {score} {where}."
    return f"They most recently lost {score} to {opp} {where}."


def _clean_record_label(label: str | None) -> str:
    if not label:
        return "record"
    low = label.lower()
    if "regular-season" in low or "regular season" in low:
        return "regular-season record"
    return "record"


def _names_selection(text: str) -> bool:
    low = text.lower()
    return any(token in low for token in ("selection:", "backing", "pick is", "taking", "we take"))


def _seed(fixture_id: str, market: str) -> int:
    return int(hashlib.sha256(f"{fixture_id}|{market}".encode()).hexdigest()[:8], 16)


# ---------------------------------------------------------------------------
# sentence blocks
# ---------------------------------------------------------------------------
WINNER_BLOCKS = [
    [  # opener
        "{away} visit {venue} to face {home}, and our rating makes {fav} a {prob}% favourite.",
        "We make {fav} a {prob}% chance to beat {dog} at {venue}.",
        "{fav} rate {line_abs} {unit} stronger than {dog} on our numbers, a {prob}% win probability.",
        "Our rating has {fav} {line_abs} {unit} clear in this one, a {prob}% win probability.",
        "Our ratings have {fav} {line_abs} {unit} clear of {dog} going into this one.",
        "At {venue}, our rating splits this {prob}% in favour of {fav}.",
    ],
    [  # form
        "{fav} {wins5_clause}.",
        "{fav} arrive with a {record} {record_label} and {wins5_clause}.",
        "Form favours {fav}, who {wins5_clause}, while {dog} {dog_wins_clause}.",
        "{form_sentence}",
        "Across their last five, {fav} have averaged {avg_for} {unit} scored and {avg_against} conceded.",
    ],
    [  # last result
        "{last}",
        "{last}",
        "",
        "{last}",
    ],
    [  # model / price
        "We price that at {american}, inclusive of our 4.5% two-way margin.",
        "Our rated probability is {prob}%, and we quote {american}.",
        "At {american}, the implied probability after our margin is {prob}%.",
        "Our price of {american} reflects a {prob}% win probability.",
    ],
    [  # selection
        "Selection: {selection} at {american}.",
        "We are backing {selection} at {american}.",
        "The pick is {selection} at {american}.",
        "We are taking {selection} at {american}.",
    ],
]

HANDICAP_BLOCKS = [
    [
        "We opened this {market_name} at {opening_line} and now make it {line}, a move of {move} {unit}.",
        "Our opening number was {opening_line}; the current rating says {line}.",
        "The line has moved {move} {unit}, from {opening_line} to {line}, since our opener.",
        "{fav} sit {line_abs} {unit} clear of {dog} on our board; the opener had it at {opening_line_abs}.",
        "We make the {market_name} {line} for {fav}, having opened it at {opening_line}.",
    ],
    [
        "{fav} {wins5_clause}.",
        "{fav} hold a {record} {record_label} and {wins5_clause}.",
        "Recent form favors {fav}, who {wins5_clause}, while {dog} {dog_wins_clause}.",
        "{form_sentence}",
    ],
    [
        "{last}",
        "{record_sentence}",
        "",
    ],
    [
        "At the opening line, {selection} rates {prob}% to cover, priced at {american}.",
        "That gives {prob}% for {selection} at {american}.",
        "We price the cover at {american}, a {prob}% probability.",
    ],
    [
        "Selection: {selection} at {american}.",
        "We are backing {selection} at {american}.",
        "The pick is {selection} at {american}.",
        "We are taking {selection} at {american}.",
    ],
]

TOTAL_BLOCKS = [
    [
        "Our total opened at {opening_line} and now sits at {line}, a move of {move} {unit}.",
        "We opened this total at {opening_line}; the current rating projects {line}.",
        "The number has moved {move} {unit} from {opening_line} to {line}.",
        "We make the total {line}, against {opening_line} at the open.",
        "This total has been re-rated from {opening_line} to {line} on the recent scoring data.",
    ],
    [
        "{fav} have averaged {avg_for} {unit} scored and {avg_against} conceded across their last five.",
        "Across their last five, {fav} have scored {avg_for} and conceded {avg_against} {unit} per game.",
        "{fav} are averaging {avg_for} {unit}; {dog} are averaging {dog_avg}.",
        "The recent scoring profile is {avg_for} for {fav} and {dog_avg} for {dog}.",
    ],
    [
        "{record_sentence}",
        "{last}",
        "",
    ],
    [
        "{selection} rates {prob}% at {american} on our numbers.",
        "We price that outcome at {american}, a {prob}% probability.",
        "At {american} the implied probability is {prob}%.",
    ],
    [
        "Selection: {selection} at {american}.",
        "We are backing {selection} at {american}.",
        "The pick is {selection} at {american}.",
        "We are taking {selection} at {american}.",
    ],
]

BLOCKS_BY_MARKET = {
    "moneyline": WINNER_BLOCKS,
    "handicap": HANDICAP_BLOCKS,
    "total": TOTAL_BLOCKS,
}


def _decode(variant: int, sizes: list[int]) -> list[int]:
    """Mixed-radix decode with a prime stride.

    The stride is coprime with every block size used here, so distinct variants stay
    distinct (a bijection on the combination space) while consecutive predictions jump
    across all five blocks instead of only changing the first sentence.
    """
    product = 1
    for size in sizes:
        product *= size
    mixed = (variant * 7919) % product
    out = []
    for size in sizes:
        out.append(mixed % size)
        mixed //= size
    return out


def make_prediction(fixture: dict, analysis: dict, form: dict, h2h: list[dict],
                    source_urls: list[str], variant: int = 0) -> dict:
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
        market_name = "total"
    elif pick["market"] == "handicap":
        line = pick.get("line") or analysis["markets"]["handicap"]["line_home"]
        opening_line = analysis["markets"]["handicap"]["opening_line_home"]
        move_basis = analysis["edge"]["margin"]
        market_name = analysis["markets"]["handicap"].get("name", "handicap")
    else:
        line = cur["margin"]
        opening_line = opn["margin"]
        move_basis = analysis["edge"]["margin"]
        market_name = "moneyline"

    streak = fav_form.get("streak", 0)
    wins5 = fav_form.get("wins_last5", 0) or 0
    if streak >= 2:
        form_sentence = f"{fav['name']} are on a {streak}-game winning run."
    elif streak <= -2:
        form_sentence = f"{fav['name']} are on a {abs(streak)}-game losing run."
    else:
        form_sentence = f"{fav['name']} {_wins_clause(wins5)}."


    record_label = _clean_record_label(
        (fixture.get("context") or {}).get("home_record_label" if fav_is_home else "away_record_label")
    )
    record_sentence = (
        f"{fav['name']} hold a {fav['record']} {record_label}." if fav.get("record") else ""
    )
    last_opp = None
    last = fav_form.get("last_game")
    if last:
        last_opp = last.get("away_name") if last.get("venue") == "home" else last.get("home_name")

    values = {
        "away": away["name"],
        "home": home["name"],
        "fav": fav["name"],
        "dog": dog["name"],
        "venue": fixture.get("venue") or "the venue",
        "record": fav.get("record") or "n/a",
        "record_label": record_label,
        "record_sentence": record_sentence,
        "wins5": _wins_phrase(fav_form.get("wins_last5", 0)),
        "dog_wins5": _wins_phrase(dog_form.get("wins_last5", 0)),
        "avg_for": _num(fav_form.get("avg_scored_last5")),
        "avg_against": _num(fav_form.get("avg_allowed_last5")),
        "dog_avg": _num(dog_form.get("avg_scored_last5")),
        "form_sentence": form_sentence,
        "wins5_clause": _wins_clause(wins5),
        "dog_wins_clause": _wins_clause(dog_form.get("wins_last5", 0) or 0),
        "last": _last_sentence(fav_form, last_opp),
        "prob": _num(pick["prob_pct"], 1).rstrip("0").rstrip("."),
        "american": pick["american"],
        "line": f"{line:+.1f}" if pick["market"] != "total" else f"{line:.1f}",
        "line_abs": f"{abs(line):.1f}",
        "line_abs_unit": f"{abs(line):.1f}",
        "unit_singular": {"points": "point", "goals": "goal", "runs": "run"}[unit],
        "opening_line_abs": f"{abs(opening_line):.1f}",
        "opening_line": f"{opening_line:+.1f}" if pick["market"] != "total" else f"{opening_line:.1f}",
        "move": _num(abs(move_basis), 2),
        "unit": unit,
        "selection": pick["selection"],
        "market_name": market_name,
    }

    blocks = BLOCKS_BY_MARKET[pick["market"]]
    choices = _decode(variant, [len(block) for block in blocks])
    sentences = []
    for block, idx in zip(blocks, choices):
        text = block[idx % len(block)].format(**values).strip()
        if text:
            sentences.append(text)
    if pick["market"] != "total" and abs(line) < 0.05:
        sentences[0] = f"Our rating gives {fav['name']} a {values['prob']}% win probability."
    text = " ".join(sentences)
    text = re.sub(r"\s+", " ", text).replace(" .", ".").strip()
    # "a 86.2%" reads badly; use the correct indefinite article for eight-/eleven-/eighteen-
    text = re.sub(r"\ba (?=(?:8\d|11|18)\b)", "an ", text)
    if not _names_selection(text):
        text += f" Selection: {pick['selection']} at {pick['american']}."
    if len(text.split()) < 30:
        extra = record_sentence or f"{fav['name']} are {fav['record']} in the official table."
        text = (extra + " " + text).strip()

    return {
        "text": text,
        "word_count": len(text.split()),
        "facts": _facts(fixture, analysis, form, h2h, source_urls),
        "variant": variant,
        "market": pick["market"],
        "selection": pick["selection"],
    }


def _facts(fixture, analysis, form, h2h, sources) -> list[dict]:
    home, away = fixture["home"], fixture["away"]
    first_source = (fixture.get("source_urls") or [""])[0]
    facts = [
        {"fact": f"{home['name']} vs {away['name']}, scheduled {fixture['start_utc']}",
         "source": first_source},
        {"fact": f"Venue: {fixture.get('venue') or 'not published by the league'}",
         "source": first_source},
    ]
    for team in (home, away):
        rec = team.get("record")
        if rec:
            label = (fixture.get("context") or {}).get(
                "home_record_label" if team is home else "away_record_label"
            ) or "record"
            facts.append({"fact": f"{team['name']} {_clean_record_label(label)}: {rec}",
                          "source": first_source})
        f = form.get(str(team["id"]))
        if f and f.get("last5"):
            results = ", ".join(
                f"{'W' if g['won'] else 'L'} {g['team_score']}-{g['opp_score']}" for g in f["last5"]
            )
            facts.append({"fact": f"{team['name']} last five completed games: {results}",
                          "source": f["last5"][0].get("game_url") or first_source})
    ctx = fixture.get("context") or {}
    for key, label in (
        ("home_probable_pitcher", "Home probable pitcher"),
        ("away_probable_pitcher", "Away probable pitcher"),
        ("series", "Series"),
    ):
        if ctx.get(key):
            facts.append({"fact": f"{label}: {ctx[key]}", "source": first_source})
    if h2h:
        facts.append({
            "fact": f"{len(h2h)} previous meeting(s) in the official results sample; most recent "
                    f"{h2h[0]['date_utc'][:10]} ended {h2h[0]['away_score']}-{h2h[0]['home_score']} "
                    f"(away-home)",
            "source": h2h[0].get("source_url") or first_source,
        })
    pick = analysis["headline_pick"]
    facts.append({"fact": f"Our rated win probability {pick['prob_pct']}% priced at {pick['american']}",
                  "source": "derived: our own rating and pricing from official results"})
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
            f"{unit} {direction} our opening number, and our rating makes {pick['selection']} a "
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
        f"Rated margin {exp['margin']:+.1f} {unit} and a {pick['prob_pct']}% win probability for "
        f"{pick['selection']}, priced at {pick['american']}. Sample: {pick['sample_games_min']} "
        f"completed games per team."
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
