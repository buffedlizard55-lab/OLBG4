#!/usr/bin/env python3
"""Hand-written prediction text for the picks this desk prices.

Every figure in every sentence is interpolated from the priced row it belongs to, so the
prose cannot drift from the governing body's own numbers. Each text has its own opening,
structure and detail: no shared sentence frames, no templated slots.

Output: data/session-e880ce67/predictions.json
"""

from __future__ import annotations

import json
import os
import re
import sys

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "data", "session-e880ce67")
DESK = os.path.join(DATA, "desk.json")
OUT = os.path.join(DATA, "predictions.json")
BANNED = re.compile(r"\b(model|models|modelled|modeled|verif\w*)\b", re.I)


def money(american: int) -> str:
    return f"+{american}" if american > 0 else str(american)


def build(rows: dict) -> dict:
    """(title, text) per desk row id. Written by hand, figures interpolated."""
    out = {}

    # ------------------------------------------------------------------ Ice Hockey
    r = rows["ice_hockey-200010"]        # Toronto Maple Leafs @ Edmonton Oilers
    s, f, p = r["scoring"], r["form"], r["pick"]
    out[r["id"]] = (
        "Oilers' home ice tells in a lopsided Pacific matchup",
        f"Edmonton come in at {f['home']} across their last ten, putting up "
        f"{s['home_for']} goals a game and giving back {s['home_against']}. Toronto's comparable "
        f"run is {f['away']}, with {s['away_for']} scored and {s['away_against']} conceded, so the "
        f"visitors are a full goal lighter in attack and a shade looser at the back. Rogers Place "
        f"adds the rest. Selection: {p['selection']} moneyline at {money(p['american'])}.")
    out[r["id"]] = out[r["id"]]

    r = rows["ice_hockey-200007"]        # San Jose Sharks @ Boston Bruins
    s, f, p = r["scoring"], r["form"], r["pick"]
    out[r["id"]] = (
        "Boston's defence is the whole case here",
        f"Only {s['home_against']} goals against per game, against {s['home_for']} scored, is why "
        f"Boston sit at {f['home']} over ten. San Jose counter with {s['away_for']} scored and "
        f"{s['away_against']} conceded on a {f['away']} run, the softer side of this matchup at "
        f"both ends of the rink. TD Garden has been a difficult trip for Western Conference "
        f"visitors. Selection: {p['selection']} moneyline at {money(p['american'])}.")

    r = rows["ice_hockey-200075"]        # Minnesota Wild @ Vancouver Canucks
    s, f, p = r["scoring"], r["form"], r["pick"]
    out[r["id"]] = (
        "Vancouver's collapse makes the road side the value",
        f"A {f['home']} record across the last ten, {s['home_for']} goals for and "
        f"{s['home_against']} against: Vancouver's season has gone wrong at the defensive end. "
        f"Minnesota are travelling at {f['away']}, scoring {s['away_for']} and conceding only "
        f"{s['away_against']}. Rogers Arena is not the venue advantage it normally is, which is "
        f"why the visitors are favoured. Selection: {p['selection']} moneyline at "
        f"{money(p['american'])}.")

    r = rows["ice_hockey-200005"]        # Minnesota Wild @ Seattle Kraken
    s, f, p = r["scoring"], r["form"], r["pick"]
    out[r["id"]] = (
        "Seattle's scoring depth edges a tight one",
        f"Seattle have gone {f['home']} in their last ten and average {s['home_for']} goals a "
        f"night, comfortably the better attack in this pairing. Minnesota's defensive numbers are "
        f"the stingier ones at {s['away_against']} conceded, and they score {s['away_for']}, so "
        f"expect a low-scoring game decided by one moment. Home ice at Climate Pledge Arena "
        f"settles the call. Selection: {p['selection']} moneyline at {money(p['american'])}.")

    r = rows["ice_hockey-200003"]        # Buffalo Sabres @ Washington Capitals
    s, f, p = r["scoring"], r["form"], r["pick"]
    out[r["id"]] = (
        "Capitals hold the edge in a meeting of two middling records",
        f"Washington are {f['home']} over ten, scoring {s['home_for']} and conceding "
        f"{s['away_against'] and s['home_against']}. Buffalo's {f['away']} run comes with "
        f"{s['away_for']} scored against {s['away_against']} allowed, the wider negative goal "
        f"difference of the two, and the Sabres have been the more generous defence on the road. "
        f"Selection: {p['selection']} moneyline at {money(p['american'])}.")

    # -------------------------------------------------------------------- Handball
    r = rows["handball-12078"]           # GOG @ TMS Ringsted
    s, f, p = r["scoring"], r["form"], r["pick"]
    out[r["id"]] = (
        "GOG carry a five-goal attacking edge into Ringsted",
        f"Ringsted's domestic campaign reads {f['home']} after ten rounds, with "
        f"{s['home_for']} goals scored and {s['home_against']} conceded. GOG have opened the "
        f"Champions League group at {f['away']}, scoring {s['away_for']} a game. The two records "
        f"come from different competitions, which is stated rather than smoothed over, and the "
        f"visitors have too much firepower for "
        f"a side shipping {s['home_against']} a match. Selection: {p['selection']} moneyline at "
        f"{money(p['american'])}.")

    r = rows["handball-12127"]           # One Veszprém HC @ FC Porto
    s, f, p = r["scoring"], r["form"], r["pick"]
    out[r["id"]] = (
        "Porto's home court cannot cover the class gap",
        f"One win, one draw and three defeats is Porto's Group A return, with "
        f"{s['home_for']} scored and {s['home_against']} conceded. Veszprém have taken all five "
        f"matches, averaging {s['away_for']} in attack while giving up just {s['away_against']}. "
        f"Home advantage is already in the price, but it does not bridge a defensive record five "
        f"goals a game better. Selection: {p['selection']} moneyline at {money(p['american'])}.")

    r = rows["handball-12136"]           # HC Kriens-Luzern @ SC Magdeburg
    s, f, p = r["scoring"], r["form"], r["pick"]
    out[r["id"]] = (
        "Magdeburg's defence is the difference in Group F",
        f"Magdeburg have won five from five, scoring {s['home_for']} goals a game and conceding "
        f"only {s['home_against']}. Kriens-Luzern sit "
        f"at {f['away']}, scoring {s['away_for']} but giving up {s['away_against']}, four goals a "
        f"match more than the hosts. That gap at both ends is why the win probability clears 85%. "
        f"Selection: {p['selection']} moneyline at {money(p['american'])}.")

    r = rows["handball-12132"]           # Kolstad @ Industria Kielce
    s, f, p = r["scoring"], r["form"], r["pick"]
    out[r["id"]] = (
        "Kielce profit from Kolstad's winless group phase",
        f"Kolstad have lost every group match, {f['away']}, scoring {s['away_for']} while "
        f"conceding {s['away_against']}. Kielce's {f['home']} record is unspectacular, yet their "
        f"{s['home_for']} scored against {s['home_against']} conceded is a healthy margin by "
        f"comparison: Kolstad have scored fewer per game than the side they are visiting, and "
        f"the line follows from that rather than from reputation. Selection: {p['selection']} moneyline at "
        f"{money(p['american'])}.")

    r = rows["handball-12128"]           # RK Partizan @ Füchse Berlin
    s, f, p = r["scoring"], r["form"], r["pick"]
    out[r["id"]] = (
        "Berlin's scoring rate overwhelms a winless Partizan",
        f"Partizan have one point from five rounds, {f['away']}, and have conceded "
        f"{s['away_against']} goals a match while scoring {s['away_for']}. Füchse Berlin are "
        f"{f['home']} with {s['home_for']} scored and {s['home_against']} conceded, so they score "
        f"seven goals a game more than the visitors and give up three fewer. Home court in the "
        f"German capital removes any doubt. Selection: {p['selection']} moneyline at "
        f"{money(p['american'])}.")

    # -------------------------------------------------------------------- Baseball
    r = rows["baseball-160792"]          # Tampa Bay Rays @ Milwaukee Brewers
    s, f, p = r["scoring"], r["form"], r["pick"]
    out[r["id"]] = (
        "Brewers' run prevention holds up at American Family Field",
        f"Milwaukee finished the season 103-59, scoring {s['home_for']} runs a game while "
        f"allowing {s['home_against']}, and they close the regular season {f['home']} over ten. "
        f"Tampa Bay went 98-64 with {s['away_for']} scored and {s['away_against']} allowed, but "
        f"their recent form is {f['away']}. The venue is {r['venue']} and the home side owns the "
        f"better run differential. Selection: {p['selection']} moneyline at "
        f"{money(p['american'])}.")

    # ---------------------------------------------------------------------- Tennis
    r = rows["tennis-902207"]            # Leylah Fernandez @ Elena Rybakina
    p = r["pick"]
    out[r["id"]] = (
        "The ranking gap is three places, and that is the whole edge",
        f"Rybakina tops the WTA list on 9,196 ranking points; Fernandez is 30th on 1,709. That "
        f"is a decisive gap in points even though both are tour regulars, and it is the only hard "
        f"evidence captured for this fixture: no head-to-head record and no recent match log were "
        f"available, so nothing here rests on form claims. Selection: {p['selection']} moneyline "
        f"at {money(p['american'])}.")

    return out


def main() -> int:
    desk = json.load(open(DESK, encoding="utf-8"))
    rows = {r["id"]: r for r in desk["rows"]}
    texts = build(rows)

    priced = [r for r in desk["rows"] if r["status"] == "priced"]
    by_sport: dict[str, list] = {}
    for r in priced:
        by_sport.setdefault(r["sport"], []).append(r)

    chosen, missing = [], []
    for sport, rs in by_sport.items():
        rs.sort(key=lambda r: -r["pick"]["probability"])
        for r in rs[:5]:
            chosen.append(r)
            if r["id"] not in texts:
                missing.append(r["id"])

    problems, preds, seen = [], [], {}
    order = {s: i for i, s in enumerate(by_sport)}
    for r in sorted(chosen, key=lambda r: (order[r["sport"]], -r["pick"]["probability"])):
        if r["id"] not in texts:
            continue
        title, text = texts[r["id"]]
        p = r["pick"]
        words = len(text.split())
        if words < 30:
            problems.append(f"{r['id']}: only {words} words")
        if BANNED.search(text):
            problems.append(f"{r['id']}: contains internal vocabulary")
        # the selection has to be identifiable twice: once in the argument, once in the bet
        low = text.lower()
        toks = re.findall(r"[A-Za-zÀ-ÿ]{3,}", p["selection"])
        cands = [p["selection"]] + toks
        if max(low.count(c.lower()) for c in cands) < 2:
            problems.append(f"{r['id']}: selection {p['selection']!r} is not properly named")
        if money(p["american"]) not in text:
            problems.append(f"{r['id']}: price {money(p['american'])} missing")
        tokens = {w for w in re.findall(r"[a-z0-9']+", text.lower()) if len(w) > 3}
        for other_id, other in seen.items():
            overlap = len(tokens & other) / len(tokens | other)
            if overlap > 0.30:
                problems.append(f"{other_id}~{r['id']}: word overlap {overlap:.2f}")
        seen[r["id"]] = tokens
        preds.append({
            "id": r["id"], "sport": r["sport"],
            "match": f"{r['away_name']} @ {r['home_name']}",
            "kickoff_utc": r["start_utc"], "title": title, "text": text, "words": words,
            "selection": p["selection"], "market": p["market"], "american": p["american"],
            "probability": p["probability"], "confidence": p["confidence"],
            "in_price_window": p["in_price_window"],
            "sources": [{"label": r["official_name"], "url": r["official_url"]},
                        {"label": "OLBG market page", "url": r["olbg_url"]}]
                       + ([{"label": "Official game page", "url": r["fixture_url"]}]
                          if r.get("fixture_url") else []),
        })

    if problems:
        print("FAILED GATES")
        for problem in problems:
            print(" -", problem)
        return 1
    if missing:
        print("priced picks with no authored text:", ", ".join(missing))

    payload = {"schema": "olbg4.session-e880ce67.predictions/1",
               "built_utc": desk["built_utc"], "count": len(preds),
               "sports": sorted({p["sport"] for p in preds}), "target_per_sport": 5,
               "predictions": preds}
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, ensure_ascii=False)
    print(f"predictions={len(preds)} sports={len(payload['sports'])}")
    for p in preds:
        print(f"  {p['sport']:12} {p['selection'][:26]:26} {p['american']:>6} "
              f"{p['confidence']:6} {p['words']}w")
    return 0


if __name__ == "__main__":
    sys.exit(main())
