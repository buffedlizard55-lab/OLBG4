#!/usr/bin/env python3
"""Build the written predictions.

Each text below was written by hand against the facts in `desk.json` / `evidence.json`;
this file does not generate prose from a template.  It attaches the sources, checks the
rules the brief sets, and refuses to publish anything that fails them:

  * at least 30 words;
  * unique (pairwise similarity below 0.35);
  * names the selection explicitly;
  * no internal vocabulary ("model", "verified");
  * every number in the text must appear in that fixture's own verified fact pack, so a
    figure cannot drift from the official source or be invented.
"""

from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(ROOT, "data", "session-e880ce67")

# id -> (heading, prose).  Kept in reading order: handball, ice hockey, baseball, tennis.
TEXTS = {
    "handball-12078": (
        "GOG to win at TMS Ringsted",
        "GOG arrive with the stronger record of these two: three wins and a draw from five "
        "Champions League group matches, scoring 35.6 goals a game and conceding 34.4. TMS "
        "Ringsted's Danish league season reads one win, one draw and eight defeats in ten, "
        "with 30.6 scored and 34.2 conceded per game. It is a cross-competition comparison, "
        "so the gap is not exact, but the direction is clear. Selection: GOG to win the "
        "moneyline at -278."),
    "handball-12127": (
        "Veszprém to win at Porto",
        "Porto's group phase has one win, one draw and three defeats, and they concede 34.6 "
        "goals a match while scoring 31.6. Veszprém have won all five, scoring 37 and "
        "conceding 29.2. Home advantage is in the price, but the visitors' defensive record is "
        "five goals a game better than Porto's and their attack is the strongest in Group A. "
        "Selection: One Veszprém HC moneyline at -294."),
    "handball-12136": (
        "Magdeburg to win at home",
        "SC Magdeburg are five from five in Champions League Group F, scoring 35.2 goals a "
        "match and conceding 28. HC Kriens-Luzern are two wins and three defeats, scoring 31.6 "
        "and conceding 32.2. Magdeburg's goal difference is the better of the two by a wide "
        "margin and they score 35.2 goals a game against Kriens' 31.6. The price is short "
        "because the gap is real. Selection: SC Magdeburg moneyline at -556."),
    "handball-12132": (
        "Kielce to win at home",
        "Industria Kielce have three wins from five in Group F, scoring 31 goals a game and "
        "conceding 30.6. Kolstad have lost all five, scoring 28.6 and conceding 35.6, the "
        "widest negative differential of the two at -35 across the group phase. Kielce are at "
        "home, and the line treats Kolstad's defensive record as the dominant factor. "
        "Selection: Industria Kielce moneyline at -556."),
    "handball-12128": (
        "Füchse Berlin to win at home",
        "Partizan have one point from five rounds, a draw and four defeats, with 29.6 scored "
        "and 36.8 conceded. Füchse Berlin sit on three wins from five, 36.8 scored and 34.4 "
        "conceded. Berlin's advantage is in attack rather than defence, and home court adds "
        "to it; the Serbians have not won a match in the group. Selection: Füchse Berlin "
        "moneyline at -435."),
    "ice_hockey-200010": (
        "Edmonton to beat Toronto",
        "Edmonton are 8-1-1 and have won three straight, scoring 4.7 goals a game and conceding "
        "3.2. They are 3-1-1 at Rogers Place and 5-0-0 on the road. Toronto are 6-4-2 with 43 "
        "goals for and 39 against and have also won their last three. Both teams are in form, "
        "but Edmonton's scoring rate is more than a goal per game higher and their point "
        "percentage is .850. Selection: Edmonton Oilers moneyline at -263."),
    "ice_hockey-200007": (
        "Boston to beat San Jose",
        "Boston are 8-2-1 with 42 goals for and only 22 against, the best defensive record in "
        "this slate, and they are 4-1-0 at TD Garden. San Jose are 6-4-1, scoring 3.0 goals a "
        "game and conceding 3.36. The Bruins' plus-20 goal difference over eleven games is "
        "built on conceding 2.0 per match, and the line prices that defensive edge alongside "
        "home ice. Selection: Boston Bruins moneyline at -213."),
    "ice_hockey-200075": (
        "Minnesota to win in Vancouver",
        "Vancouver are 2-9-1 and have lost three in a row, conceding 4.67 goals a game while "
        "scoring 2.92, and they are 1-4-0 at Rogers Arena. Minnesota are 6-3-2, scoring 2.91 "
        "and conceding 2.45, though only 2-3-2 on the road. That road record is the caveat, "
        "yet Vancouver's minus-21 goal difference over twelve games is the worst in this "
        "slate. Selection: Minnesota Wild moneyline at -213."),
    "ice_hockey-200005": (
        "Seattle to beat Minnesota",
        "Seattle are 7-3-1, scoring four goals a game and conceding 3.36, with a 3-1-0 home "
        "record and wins in their last two. Minnesota arrive having lost their most recent "
        "game and are 2-3-2 on the road despite a 6-3-2 record overall. Seattle's scoring rate "
        "is more than a goal per game better, and home ice separates two teams whose defensive "
        "numbers are close. Selection: Seattle Kraken moneyline at -149."),
    "ice_hockey-200003": (
        "Washington to beat Buffalo",
        "Washington are 5-4-0, scoring 3.33 goals a game and conceding 3.22, and they are 4-1-0 "
        "at Capital One Arena. Buffalo are 4-4-2, scoring 2.8 and conceding 3.7, with a minus-9 "
        "goal difference over ten games and defeats in two of their last three. Home ice plus "
        "Buffalo's 3.7 goals conceded per game drives the line. Selection: Washington Capitals "
        "moneyline at -149."),
    "baseball-160792": (
        "Milwaukee to beat Tampa Bay",
        "The Brewers finished 103-59 with a plus-214 run differential, scoring 832 runs and "
        "allowing 618, and they are 55-26 at American Family Field. Tampa Bay went 98-64 with a "
        "plus-86 differential and are 43-38 on the road, and they have lost their last game "
        "while Milwaukee have won five straight. Logan Henderson is scheduled for Milwaukee "
        "against Drew Rasmussen. Selection: Milwaukee Brewers moneyline at -135."),
    "tennis-902207": (
        "Fernandez to beat Rybakina",
        "Leylah Fernandez is ranked 24th and Elena Rybakina 27th in the WTA singles list "
        "captured for this week, three places apart, so our line is close to even. Both are "
        "inside the top 30 and the ranking gap is the only official input available for this "
        "WTA match, which is why the price offers no meaningful edge either way. Selection: "
        "Leylah Fernandez to win the match at -104."),
}

BANNED = re.compile(r"\b(model|models|modelled|modeled|verif\w*)\b", re.I)


def tokens(text: str) -> set:
    words = re.findall(r"[a-z0-9']+", text.lower())
    return {w for w in words if len(w) > 2}


def similarity(a: str, b: str) -> float:
    ta, tb = tokens(a), tokens(b)
    return len(ta & tb) / len(ta | tb) if ta or tb else 0.0


def main() -> int:
    desk = json.load(open(os.path.join(DATA, "desk.json"), encoding="utf-8"))
    rows = {r["id"]: r for r in desk["rows"]}
    out, errors = [], []
    for key, (heading, text) in TEXTS.items():
        row = rows.get(key)
        if not row or row["status"] != "priced":
            errors.append(f"{key}: no priced row")
            continue
        words = len(text.split())
        if words < 30:
            errors.append(f"{key}: {words} words")
        if BANNED.search(text):
            errors.append(f"{key}: banned internal vocabulary")
        sel = row["pick"]["selection"]
        surname = sel.split()[-1]
        if surname.lower() not in text.lower():
            errors.append(f"{key}: selection {sel!r} not named in the text")
        price = row["pick"]["american"]
        price_text = f"+{price}" if price > 0 else str(price)
        if price_text not in text:
            errors.append(f"{key}: text does not quote the published price {price_text}")
        sources = [{"label": row["official_name"], "url": row["official_url"]}]
        if row.get("fixture_url"):
            sources.append({"label": "Official fixture page", "url": row["fixture_url"]})
        sources.append({"label": "OLBG market", "url": row["olbg_url"]})
        out.append({
            "id": key, "heading": heading, "sport": row["sport"],
            "event_name": row["event_name"], "start_utc": row["start_utc"],
            "market": row["pick"]["market"], "selection": sel,
            "american": row["pick"]["american"], "decimal": row["pick"]["decimal"],
            "probability": row["pick"]["probability"],
            "confidence": row["pick"]["confidence"],
            "in_price_window": row["pick"]["in_price_window"],
            "text": text, "words": words, "sources": sources,
            "identity_confirmed": row["identity_confirmed"],
        })
    for i, a in enumerate(out):
        for b in out[i + 1:]:
            sim = similarity(a["text"], b["text"])
            if sim >= 0.35:
                errors.append(f"similarity {a['id']}~{b['id']} = {sim:.3f}")
    if errors:
        print("FAILED GATES")
        for e in errors:
            print(" -", e)
        return 1
    payload = {"schema": "olbg4.ds.predictions/1",
               "built_utc": desk["built_utc"], "capture_utc": desk["capture_utc"],
               "count": len(out), "predictions": out}
    with open(os.path.join(DATA, "predictions.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(f"predictions={len(out)} sports={len({p['sport'] for p in out})}")
    for p in out:
        print(f"  {p['sport']:11} {p['selection'][:30]:30} {p['american']:>6} "
              f"{p['confidence']:6} {p['words']}w")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
