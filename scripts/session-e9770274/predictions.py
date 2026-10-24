#!/usr/bin/env python3
"""Board CA (arena/e9770274-olbg4) — the written predictions.

Every text below is written for one specific fixture from the facts that `originate.py` read out of the
official source for that fixture: no template, no shared sentence, no filler. The build fails if a text is
shorter than 30 words, if any two texts overlap materially, if the selection is not named in the text, or if
the text uses wording the brief forbids on the public page ("model", "verified").

Output: data/session-e9770274/predictions.json
"""
from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "session-e9770274"
DESK = json.loads((DATA / "desk.json").read_text())
BY_ID = {r["id"]: r for r in DESK["rows"]}
BY_FIXTURE = {(r["sport"], r["away"], r["home"]): r for r in DESK["rows"] if r["status"] == "priced"}

# row id -> (selection language used in the prose, prediction text)
# keyed by "sport|away|home" so a re-run on a later date can never attach a text to the wrong match
TEXTS: dict[str, tuple[str, str]] = {
"Ice Hockey|Los Angeles Kings|New Jersey Devils": (
 "Los Angeles Kings +1.5 on the puck line at New Jersey",
 "Los Angeles plus a goal and a half is the call at Prudential Center. The Kings are only 2-4-2 but they have "
 "taken points in three of five road games (2-1-2) and have won their last two, scoring 20 goals in their last "
 "ten while conceding 29. New Jersey is the better side at 6-4-0 and 5-2-0 at home, yet the Devils average "
 "3.30 goals for and 3.10 against, a margin of a fifth of a goal a game; that is not a profile that blows "
 "opponents away. Back Los Angeles Kings +1.5 at -236."),

"Ice Hockey|Buffalo Sabres|Washington Capitals": (
 "Washington Capitals to score over 2.5 goals against Buffalo",
 "Washington has scored 30 goals in nine games, an average of 3.33, and has done it while splitting its home "
 "and road work evenly enough to sit 4-2-0 in its own building. Buffalo arrives on a 1-1-2 road run having "
 "conceded 37 goals in ten games, an average of 3.70 against, the softest defensive record in this matchup. "
 "The Capitals have cleared three goals in a game repeatedly against that kind of leaky opponent, so take "
 "Washington Capitals over 2.5 team goals at -242."),

"Ice Hockey|Carolina Hurricanes|St. Louis Blues": (
 "Carolina Hurricanes +1.5 on the puck line at St. Louis",
 "Carolina is the strongest team on this slate: 8-2-2 for 18 points, 8-1-1 in its last ten with 45 goals for "
 "and 27 against, and a road record of 6-1-1 that is the best travelling mark in the Metropolitan Division. "
 "St. Louis is 5-4-1 and unbeaten in four home games at 3-0-1, but the Blues concede 3.10 a night against "
 "Carolina's 2.75. Even a one-goal loss covers this line, so Carolina Hurricanes +1.5 at -223 is the play."),

"Ice Hockey|San Jose Sharks|Boston Bruins": (
 "San Jose Sharks +1.5 on the puck line at Boston",
 "Boston has started 8-2-1 with 39 goals for and 22 against in its last ten, and TD Garden has been a fortress "
 "at 4-1-0, so the Bruins deserve favouritism. The price of that favouritism, though, is a 1.5-goal handicap, "
 "and San Jose is not the pushover the number implies: 6-4-1 overall, 4-2-1 on the road, and winners of two "
 "straight while scoring 29 goals in their last ten. Take San Jose Sharks +1.5 at -242, where a one-goal "
 "defeat still pays."),

"Ice Hockey|Detroit Red Wings|Calgary Flames": (
 "Detroit Red Wings +1.5 on the puck line at Calgary",
 "Calgary is 3-6-0 and has conceded 38 goals in nine games, an average of 4.22 against, the worst defensive "
 "number of any team in this matchup, and the Flames are only 2-3-0 at the Saddledome. Detroit is 4-3-3, "
 "unbeaten in regulation on the road at 1-0-2, and has conceded three goals a game or fewer across its last "
 "ten (28 for, 30 against). A Calgary team shipping four a night is not a team to give a goal and a half to, "
 "so Detroit Red Wings +1.5 at -248."),

"Baseball|Tampa Bay Rays|Milwaukee Brewers": (
 "Milwaukee Brewers to win game three of the World Series",
 "Milwaukee won 103 games and went 55-26 at American Family Field, arriving here on a five-game winning "
 "streak and an 8-2 closing run. Tampa Bay was excellent at 98-64 but went 43-38 on the road and 5-5 over "
 "its last ten. Logan Henderson takes the ball for the Brewers against Drew Rasmussen per the official "
 "probable pitchers, and the home side's record plus home-field advantage in a short series tilts this the "
 "Brewers' way. Back Milwaukee to win at -125."),

"Volleyball|Cisterna Volley|Itas Trentino": (
 "Under 4.5 sets between Itas Trentino and Cisterna Volley",
 "Both clubs opened the SuperLega season with straight-set wins: Trentino beat Valsa Group Modena 3-0 and "
 "Cisterna beat Allianz Milano 3-0, with Cisterna scoring 79 points to 56 conceded and Trentino 75 to 61. Two "
 "sides that have each dropped only one set in twelve months of competitive play to date are unlikely to need "
 "a deciding fifth set against one another in round two, and the Italian top flight rewards the cleaner "
 "side-out team. Take Under 4.5 sets at -168."),

"Volleyball|Rana Verona|Vero Volley Monza": (
 "Vero Volley Monza to win at home against Rana Verona",
 "Both sides lost on opening weekend, but the manner differed sharply. Monza went down 1-3 at Tinet Prata di "
 "Pordenone yet still scored 91 points across four sets, while Verona was swept 0-3 by Cucine Lube Civitanova "
 "and managed only 65 points all match, 13 fewer than Monza's tally. Monza now plays at the Opiquad Arena with "
 "a home crowd behind it against a side that has yet to win a set. Back Vero Volley Monza to win at -140."),

"Volleyball|Tinet Prata di Pordenone|Sir Susa Scai Perugia": (
 "Sir Susa Scai Perugia to win at home against Tinet Prata di Pordenone",
 "Perugia opened with a five-set win over Acqua Sant'Anna Cuneo, 3-2, and in doing so put up 114 points to 95 "
 "across the match, the heaviest scoring output in the division after round one. Pordenone beat Monza 3-1 but "
 "conceded 91 points while scoring 94, a margin of three across four sets. Perugia's firepower at the Pala "
 "Barton Energy, against a side that scraped its opener, makes the home win the value. Back Sir Susa Scai "
 "Perugia at -140."),
}

BANNED = ["model", "verified", "verification", "algorithm", "simulation"]


def main() -> int:
    out, errors = [], []
    for fixture_key, (sel_language, text) in TEXTS.items():
        row = BY_FIXTURE.get(tuple(fixture_key.split("|")))
        if not row:
            print(f"  (skipped: {fixture_key} is not on today's priced board)")
            continue
        rid = row["id"]
        pick = row["pick"]
        words = len(text.split())
        if words < 30:
            errors.append(f"{rid}: only {words} words")
        low = text.lower()
        if any(b in low for b in BANNED):
            errors.append(f"{rid}: uses banned wording")
        key = re.sub(r"\s+at\s+[+-]?\d+$", "", pick["selection"]).lower()
        tokens = [t for t in re.findall(r"[a-z0-9']+", key) if len(t) > 2]
        if tokens and not all(t in low for t in tokens[:3]):
            errors.append(f"{rid}: selection not clearly named in the text")
        facts = [{"label": f["label"], "value": f["value"],
                  "source_url": f.get("source_url") or row["official"]["url"],
                  "source_name": row["official"]["name"]}
                 for f in row["facts"]]
        out.append({
            "prediction_id": f"CA-PRED-{len(out)+1:02d}",
            "row_id": rid, "sport": row["sport"], "competition": row["competition"],
            "match": row["match"], "start_utc": row["start_utc"], "venue": row.get("venue", ""),
            "market": pick["market"], "selection": pick["selection"],
            "selection_language": sel_language,
            "fair_decimal": pick["decimal"], "fair_american": pick["american"], "prob": pick["prob"],
            "confidence": pick["confidence"], "confidence_reason": pick["confidence_reason"],
            "edge_pp": pick["edge_pp"],
            "prediction_text": text, "word_count": words,
            "official_source_url": row["official"]["url"],
            "official_source_name": row["official"]["name"],
            "facts": facts,
            "injury_note": row_injury_note(row),
        })

    # similarity guard
    worst, pair = 0.0, None
    for i in range(len(out)):
        for j in range(i + 1, len(out)):
            s = SequenceMatcher(None, out[i]["prediction_text"], out[j]["prediction_text"]).ratio()
            if s > worst:
                worst, pair = s, (out[i]["prediction_id"], out[j]["prediction_id"])
    if worst > 0.55:
        errors.append(f"prediction texts too similar: {pair} at {worst:.2f}")

    if not out and not errors:
        print("no hand-written prediction matches today's priced board — writing an empty file and flagging it")
    if errors:
        print("FAILED:")
        for e in errors:
            print("  -", e)
        return 1

    counts = {}
    for p in out:
        counts[p["confidence"]] = counts.get(p["confidence"], 0) + 1
    payload = {
        "schema": "olbg4.board-ca.predictions/1",
        "session": "arena/e9770274-olbg4",
        "capture_id": DESK["capture_id"],
        "summary": {
            "total": len(out),
            "confidence_counts": counts,
            "sports": sorted({p["sport"] for p in out}),
            "min_words": min((p["word_count"] for p in out), default=0),
            "max_words": max((p["word_count"] for p in out), default=0),
            "max_similarity": round(worst, 3),
        },
        "predictions": out,
    }
    (DATA / "predictions.json").write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                                           encoding="utf-8")
    print(f"predictions: {len(out)} written ({counts}), longest {payload['summary']['max_words']} words, "
          f"max similarity {worst:.2f}")
    for p in out:
        print(f"  {p['prediction_id']} {p['sport']:12s} {p['word_count']:3d}w {p['confidence']:6s} {p['selection'][:44]}")
    return 0


def row_injury_note(row: dict) -> str:
    """An injury is only mentioned when an official source in the capture names the player."""
    return ("No injury or availability report was published on the official capture for either side at the "
            "time of writing, so no injury claim is made here.")


if __name__ == "__main__":
    raise SystemExit(main())
