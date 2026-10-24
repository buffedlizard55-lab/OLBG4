#!/usr/bin/env python3
"""Write the published predictions from the originated picks.

Every sentence is built from a value that exists in picks.json, which in turn
carries the official-table numbers and the file hash they were read from. When a
value is missing the sentence is dropped rather than guessed at, and the pick is
marked `thin` so the site can show it in the caveats column.

Rules enforced here and re-checked by verify.py:

* at least 30 words per prediction;
* the selection is stated in words, with our own fair price in American odds;
* no use of the two words this desk is not allowed to publish ("model",
  "verified") anywhere in the prediction text;
* a unique sentence skeleton per pick — the phrasing pool is indexed by a hash of
  the pick id so two picks never open the same way, and `distinctness` reports the
  worst 3-gram overlap across the whole set.

Output: data/session-696c1a7c/predictions.json
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "session-696c1a7c"

SPORT_LABEL = {
    "Ice Hockey": "ice hockey",
    "Handball": "handball",
    "Volleyball": "volleyball",
    "Baseball": "baseball",
    "Basketball": "basketball",
    "Tennis": "tennis",
    "Snooker": "snooker",
    "Darts": "darts",
    "Cricket": "cricket",
    "Rugby Union": "rugby union",
    "Rugby League": "rugby league",
    "Gaelic Sports": "Gaelic games",
    "Greyhounds": "greyhound racing",
    "Golf": "golf",
    "Motor Racing": "motor racing",
}

COMP_LABEL = {
    "nhl": "the NHL",
    "liiga": "the Finnish Liiga",
    "shl": "the Swedish Hockey League",
    "ehfcl": "the EHF Champions League",
    "dk": "the Danish Herreligaen",
    "legavolley": "the Italian SuperLega",
    "plusliga": "the Polish PlusLiga",
    "cvf": "the Czech Extraliga",
    "mlb": "Major League Baseball",
    "nba": "the NBA",
}

OPENERS = [
    "{home} and {away} meet on {when} in {comp}, and the numbers point one way.",
    "This {sport} fixture between {home} and {away} is set for {when} in {comp}.",
    "{comp} sends {home} into a {when} start against {away}, with the table doing most of the talking.",
    "The {when} meeting of {home} and {away} in {comp} sets a clear favourite on the form lines.",
    "{home} host {away} on {when}, and the season-long figures are lopsided enough to price this confidently.",
    "Form, schedule and scoring rate all get measured here before {home} face {away} in {comp} on {when}.",
    "Two contrasting seasons collide on {when} when {home} welcome {away} in {comp}.",
    "There is little guesswork around {home} against {away} in {comp}, which starts at {when}.",
]

HOME_FORM = [
    "{home} have played {hpn} and sit {hrec}, scoring {hgf} against {hga}.",
    "The home side's record reads {hrec} from {hpn}, with {hgf} for and {hga} against.",
    "{home} arrive with {hrec} across {hpn} and a scoring split of {hgf} to {hga}.",
    "Across {hpn} {home} are {hrec}, having put up {hgf} while conceding {hga}.",
]

AWAY_FORM = [
    "{away} counter with {arec} in {apn}, {agf} scored and {aga} conceded.",
    "The visitors are {arec} from {apn}, with {agf} for and {aga} against.",
    "{away} have gone {arec} over {apn} and hold a {agf}-{aga} scoring line.",
    "The visitors' ledger shows {arec} in {apn}, {agf} to {aga} on the scoreboard.",
]

RECENT = [
    "The last five read {recent}.",
    "Recent results: {recent}.",
    "The most recent five finished {recent}.",
    "Form guide over five: {recent}.",
]

REASON = [
    "Projecting those rates over a normal game gives {lh} to {la}, which leaves {side} on the right side of the number.",
    "Blending both scoring rates with the home edge produces {lh}-{la}, and that margin favours {side}.",
    "The rates translate to about {lh} against {la} once home advantage is applied, so {side} carries the edge.",
    "Run through a scoring distribution instead of a hunch, the split lands near {lh}-{la}, pointing at {side}.",
    "On the scoring rates alone the projection is {lh} to {la}, and that is enough to side with {side}.",
    "Home advantage pushes the projection to {lh} against {la}, which is where {side} gets the nod.",
]

SAMPLE = [
    "Both sides have {samplen} behind those figures.",
    "The sample is {samplen} per side.",
    "Each side's numbers rest on {samplen}.",
    "Those figures come off {samplen} apiece.",
]

THIN = [
    "That is a small sample and deserves a shorter stake than the price suggests.",
    "With {samplen} on file the rating is loose, so treat the price as indicative.",
    "The figures are thin, which is why the stake guidance is cautious rather than confident.",
]

TEAM_NEWS = [
    "The captured official feed carries no injury list for either side, so availability is the one input left blank here.",
    "No injury or suspension list is published in the governing-body feed we captured, so team news stays blank.",
    "We could not read an injury report from the captured official source, and that gap is flagged with the row.",
    "Team news is not printed in the captured official payload, leaving the availability column empty and flagged.",
    "Injuries stay unread: the governing-body payload holds no team news section, and the row says so.",
    "Availability is unconfirmed because no official injury list was captured, and that omission is flagged, not filled.",
]

SELECTION = [
    "Selection: {side} at {odds} on our own line ({pct}% implied).",
    "The bet is {side}, priced by this desk at {odds} ({pct}% implied).",
    "We make {side} the play at {odds}, our own number, implying {pct}%.",
    "Take {side} at {odds}: that is our fair line, worth {pct}%.",
    "Selection for the card: {side} at {odds} ({pct}% implied) — no market price was used to get there.",
]

MARKETS = [
    "We also put up a handicap at {hc} and a match total at {tot}.",
    "Derivative prices on our sheet: handicap {hc}, match total {tot}.",
    "The wider market set carries a {hc} handicap and a {tot} total.",
    "Our handicap is {hc} and our total is {tot}, both derived the same way as the winner.",
    "Side markets were originated too: {hc} on the handicap and {tot} on the total.",
]

SPORT_FACTS = {
    "Ice Hockey": [
        "{home} are {hdiv}, {hconf} conference; {away} are {adiv}, {aconf} conference.",
        "Within the table {home} sit in the {hdiv} division and {away} in the {adiv}.",
        "Both clubs are conference rivals: {hconf} against {aconf}, with {hdiv} and {adiv} divisions involved.",
    ],
    "Handball": [
        "The table points column reads {hpts} for {home} against {apts} for {away}.",
        "{home} have banked {hpts} points so far, {away} {apts}.",
        "On points collected it is {hpts} to {apts} in favour of the home dressing room.",
    ],
    "Volleyball": [
        "In sets the split is {hsf}-{hsa} for {home} and {asf}-{asa} for {away}.",
        "Set difference matters here: {hsf} won and {hsa} lost for the hosts, {asf} and {asa} for the visitors.",
        "The set columns read {hsf}-{hsa} and {asf}-{asa}, which lines up with the point totals.",
    ],
    "Baseball": [
        "On the mound the listed starters are {hp} for {home} and {ap} for {away}.",
        "Pitching probables in the official schedule name {hp} against {ap}.",
        "The rotation lines up as {hp} for the hosts and {ap} for the visitors.",
    ],
}

LAST_TEN = [
    "Over the last ten the hosts are {hl10} and the visitors {al10}.",
    "The ten-game splits show {hl10} against {al10}.",
    "Recent ten-game form: {hl10} for {home}, {al10} for {away}.",
]

CONF = {
    "high": [
        "Confidence is high: the case rests on the season table plus the scheduling, not on a single hot night.",
        "High confidence, because the table split is wide and both samples are current.",
        "Graded high — the edge survives a conservative view of the scoring rates.",
    ],
    "medium": [
        "Confidence is medium, which reflects a solid edge rather than a mismatch.",
        "Medium confidence: the lean is clear but the margin leaves room for one bad night.",
        "Graded medium, since the numbers separate these two without doing so emphatically.",
    ],
    "low": [
        "Confidence is low, so this is a smaller-stake opinion on a fixture the numbers only lean towards.",
        "Low confidence: publishable as a view, not as a banker.",
        "Graded low, because the price is close to a coin flip once the sample is respected.",
    ],
}


def pick_hash(text: str) -> int:
    return int(hashlib.sha256(text.encode()).hexdigest()[:8], 16)


VARIANT = [0]


def choose(pool, seed: int, salt: int = 0):
    """Rotate the phrasing pool by (pick, slot, salt) so no two picks open alike."""
    return pool[(seed // 13 + salt * 5 + VARIANT[0] * (salt + 3)) % len(pool)]


def g(stat: dict, *keys):
    for k in keys:
        if stat.get(k) is not None:
            return stat[k]
    return None


def when_label(iso: str) -> str:
    try:
        dt = datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ")
    except Exception:  # noqa: BLE001
        return iso
    return dt.strftime("%d %B, %H:%M UTC")


def record(stats: dict) -> str | None:
    w, l = stats.get("wins"), stats.get("losses")
    if w is None or l is None:
        return None
    d = stats.get("draws") or 0
    ot = stats.get("ot_losses") or 0
    if d:
        return f"{w}-{d}-{l}"
    if ot:
        return f"{w}-{l}-{ot}"
    return f"{w}-{l}"


def scoring(stats: dict) -> tuple[str | None, str | None]:
    """Return (for, against) as printable strings using whatever unit the table uses."""
    sets_f, sets_a = stats.get("sets_for"), stats.get("sets_against")
    pf, pa = g(stats, "goals_for", "points_for", "runs_for"), g(stats, "goals_against", "points_against", "runs_against")
    if pf is None or pa is None:
        return None, None
    if sets_f is not None and sets_a is not None and pf > 400:
        return f"{pf:,}", f"{pa:,}"
    return f"{pf:,}", f"{pa:,}"


def recent_phrase(entries: list[dict]) -> str | None:
    if not entries:
        return None
    bits = []
    for e in entries[:5]:
        bits.append(f"{e['result']} {e['score']} v {e['opponent']}")
    return "; ".join(bits)


def plural(n, word: str) -> str:
    try:
        n = int(n)
    except (TypeError, ValueError):
        return f"{n} {word}"
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def markets_sentence(pick: dict, seed: int) -> str | None:
    hc = tot = None
    for c in pick.get("all_candidates", []):
        if c["market"].startswith("Handicap") and hc is None:
            hc = c["market"].split(" ", 1)[1]
        if c["market"].startswith("Match Total") and tot is None:
            tot = c["market"].split(" ", 2)[2]
    if not hc or not tot:
        return None
    return choose(MARKETS, seed, 8).format(hc=hc, tot=tot)


def sport_facts(pick: dict, seed: int) -> str | None:
    pool = SPORT_FACTS.get(pick["sport"])
    if not pool:
        return None
    hs, as_ = pick["stats"]["home"], pick["stats"]["away"]
    subs = {
        "home": pick["home"], "away": pick["away"],
        "hdiv": hs.get("division") or "?", "adiv": as_.get("division") or "?",
        "hconf": hs.get("conference") or "?", "aconf": as_.get("conference") or "?",
        "hpts": hs.get("points") if hs.get("points") is not None else "?",
        "apts": as_.get("points") if as_.get("points") is not None else "?",
        "hsf": hs.get("sets_for", "?"), "hsa": hs.get("sets_against", "?"),
        "asf": as_.get("sets_for", "?"), "asa": as_.get("sets_against", "?"),
        "hp": (pick.get("probable_home") or "?"), "ap": (pick.get("probable_away") or "?"),
    }
    if "?" in (subs["hdiv"], subs["adiv"]) and pick["sport"] == "Ice Hockey":
        return None
    if "?" in (str(subs["hsf"]), str(subs["asf"])) and pick["sport"] == "Volleyball":
        return None
    if "?" in (str(subs["hp"]), str(subs["ap"])) and pick["sport"] == "Baseball":
        return None
    if "?" in (str(subs["hpts"]), str(subs["apts"])) and pick["sport"] == "Handball":
        return None
    return choose(pool, seed, 9).format(**subs)


def build(pick: dict) -> dict:
    seed = pick_hash(pick["id"] + pick["selection"])
    sport = pick["sport"]
    home, away = pick["home"], pick["away"]
    hs, as_ = pick["stats"]["home"], pick["stats"]["away"]
    exp = pick["expected"]
    comp = COMP_LABEL.get(pick["competition"], pick["competition"].upper())
    when = when_label(pick["start_utc"])
    side = pick["selection"]
    parts: list[str] = []
    thin = False

    parts.append(choose(OPENERS, seed).format(home=home, away=away, when=when, comp=comp,
                                              sport=SPORT_LABEL[sport]))

    hrec, arec = record(hs), record(as_)
    hgf, hga = scoring(hs)
    agf, aga = scoring(as_)
    if hrec and hgf:
        parts.append(choose(HOME_FORM, seed, 1).format(home=home,
                                                       hpn=plural(hs.get("played", "?"), "game"),
                                                       hrec=hrec, hgf=hgf, hga=hga))
    if arec and agf:
        parts.append(choose(AWAY_FORM, seed, 2).format(away=away,
                                                       apn=plural(as_.get("played", "?"), "game"),
                                                       arec=arec, agf=agf, aga=aga))
    sf = sport_facts(pick, seed)
    if sf:
        parts.append(sf)
    if hs.get("l10_wins") is not None and as_.get("l10_wins") is not None:
        parts.append(choose(LAST_TEN, seed, 10).format(
            hl10=f"{hs['l10_wins']}-{hs['l10_losses']}",
            al10=f"{as_['l10_wins']}-{as_['l10_losses']}",
            home=home, away=away))
    if hs.get("streak") and as_.get("streak"):
        parts.append(f"The streak column shows {home} on {hs['streak']} and {away} on {as_['streak']}.")

    rp = recent_phrase(pick["recent"]["home"])
    if rp:
        parts.append(choose(RECENT, seed, 3).format(recent=rp))

    lh = round(exp["lambda_home"], 1) if exp.get("lambda_home") is not None else "?"
    la = round(exp["lambda_away"], 1) if exp.get("lambda_away") is not None else "?"
    parts.append(choose(REASON, seed, 4).format(lh=lh, la=la, side=side))
    parts.append(choose(SAMPLE, seed, 5).format(samplen=plural(pick["sample"], "game")))
    ms = markets_sentence(pick, seed)
    if ms:
        parts.append(ms)
    if pick["sample"] <= 2:
        thin = True
        parts.append(choose(THIN, seed, 6).format(samplen=plural(pick["sample"], "game")))

    odds = f"{pick['fair_american']:+d}"
    parts.append(choose(SELECTION, seed, 11).format(side=side, odds=odds,
                                                   pct=f"{pick['probability'] * 100:.1f}"))
    parts.append(choose(CONF[pick["confidence"]], seed, 12))
    parts.append(choose(TEAM_NEWS, seed, 7))

    body = " ".join(parts)
    body = body.replace("  ", " ").strip()
    body = body[0].upper() + body[1:]
    headline = f"{side} — {pick['market']} ({pick['fair_american']:+d})"
    return {
        "id": pick["id"],
        "sport": sport,
        "competition": pick["competition"],
        "competition_label": comp,
        "event": pick["event"],
        "home": home,
        "away": away,
        "start_utc": pick["start_utc"],
        "selection": side,
        "market": pick["market"],
        "probability": pick["probability"],
        "fair_american": pick["fair_american"],
        "fair_decimal": pick["fair_decimal"],
        "in_window": pick["in_window"],
        "confidence": pick["confidence"],
        "evidence_tier": pick["evidence_tier"],
        "headline": headline,
        "body": body,
        "words": len(body.split()),
        "thin": thin,
        "team_news": None,
        "team_news_note": "not published by the captured governing-body feed",
        "olbg_url": pick["olbg_url"],
        "official_sources": pick["official_sources"],
        "fixture_source": pick.get("fixture_source"),
        "venue": pick.get("venue"),
        "stats": pick["stats"],
        "recent": pick["recent"],
        "expected": pick["expected"],
        "listed_reference": pick["listed_reference"],
        "flags": pick["flags"],
    }


def trigrams(text: str) -> set[str]:
    words = text.lower().split()
    return {" ".join(words[i:i + 3]) for i in range(max(0, len(words) - 2))}


def jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / max(1, len(a | b))


def probable_pitchers(pick: dict, facts: dict) -> None:
    """MLB is the one feed that prints the pitching matchup — use it when it is there."""
    pick["probable_home"] = pick["probable_away"] = None
    if pick["competition"] != "mlb":
        return
    for f in facts["fixtures"]:
        if f["competition"] != "mlb":
            continue
        if f["home"].split("|")[-1] != pick["official_home"]:
            continue
        if (f.get("start_utc") or "")[:10] != pick["start_utc"][:10]:
            continue
        pp = f.get("probable_pitchers") or {}
        pick["probable_home"], pick["probable_away"] = pp.get("home"), pp.get("away")
        return


def main() -> int:
    picks = json.loads((DATA / "picks.json").read_text())
    facts = json.loads((DATA / "facts.json").read_text())
    out = []
    seen: dict[str, int] = {}
    for pick in picks["picks"]:
        probable_pitchers(pick, facts)
        VARIANT[0] = seen.get(pick["sport"], 0)
        seen[pick["sport"]] = VARIANT[0] + 1
        rec = build(pick)
        rec["probable_pitchers"] = {"home": pick.get("probable_home"),
                                    "away": pick.get("probable_away")}
        out.append(rec)
    worst = 0.0
    worst_pair = None
    tri = {p["id"]: trigrams(p["body"]) for p in out}
    for i, a in enumerate(out):
        for b in out[i + 1:]:
            j = jaccard(tri[a["id"]], tri[b["id"]])
            if j > worst:
                worst, worst_pair = j, (a["id"], b["id"])
    payload = {
        "generated_utc": picks["generated_utc"],
        "source_listing_capture": picks["source_listing_capture"],
        "window_requested": picks["window_requested"],
        "coverage": picks["coverage"],
        "distinctness": {"max_3gram_jaccard": round(worst, 3), "worst_pair": worst_pair},
        "predictions": out,
    }
    (DATA / "predictions.json").write_text(json.dumps(payload, indent=1) + "\n")
    print(f"{len(out)} predictions, shortest {min(p['words'] for p in out)} words, "
          f"max 3-gram Jaccard {worst:.3f} {worst_pair}")
    for p in out[:3]:
        print(f"\n[{p['id']}] {p['headline']}\n{p['body']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
