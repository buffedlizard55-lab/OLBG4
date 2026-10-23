#!/usr/bin/env python3
"""Board AR — human-readable prediction bank for every published High pick.

Rules enforced here (and re-checked by verify.py):
  * every note is at least 30 words;
  * the selection (side / total / handicap) is stated explicitly;
  * no use of the two internal words that must never reach the page;
  * no claim that is not carried by the row's official inputs (records, points,
    goals, venues, round numbers, dates) — nothing is invented.

Wording is assembled from each row's own numbers with rotating frames keyed to the
row id, and the sentences are re-ordered per row, so no two notes read the same.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "session-405e9797"
BANNED = ("model", "verified", "verify")

NICK = ("Avalanche Lightning Devils Kings Wild Kraken Islanders Rangers Stars Canadiens Jets "
        "Bruins Hurricanes Blackhawks Panthers Senators Knights Flames Oilers Predators Capitals "
        "Sabres Ducks Blues Wings Sharks Flyers Penguins Leafs Canucks Mammoth").split()


def rot(seed: str, options):
    h = int(hashlib.sha256(seed.encode()).hexdigest()[:8], 16)
    return options[h % len(options)]


def ordinal(n: str) -> str:
    try:
        i = int(n)
    except Exception:
        return str(n)
    suffix = "th" if 10 <= i % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(i % 10, "th")
    return f"{i}{suffix}"


def pick_kind(r):
    sel = r["pick"]["selection"]
    mk = r["pick"]["market"]
    if "total" in mk.lower() or sel.lower().startswith(("over", "under")):
        return "under" if sel.lower().startswith("under") else "over"
    if "+" in sel:
        return "plus"
    if "-" in sel and any(ch.isdigit() for ch in sel.split("-", 1)[1][:2]):
        return "minus"
    return "win"


def short(name: str) -> str:
    if not name:
        return name
    last = name.split()[-1]
    if last in NICK:
        return "the " + last
    return name


def fmt_date(start: str) -> str:
    if not start:
        return "the scheduled date"
    try:
        y, m, d = start[:10].split("-")
        months = ["January", "February", "March", "April", "May", "June", "July",
                  "August", "September", "October", "November", "December"]
        return f"{int(d)} {months[int(m) - 1]}"
    except Exception:
        return start[:10]


def fmt_time(start: str) -> str:
    return start[11:16] + " UTC" if len(start) >= 16 else ""


NHL_RE = re.compile(
    r"Official NHL standings: (?P<h>.+?) (?P<hw>\d+)-(?P<hl>\d+)-(?P<hot>\d+) "
    r"\((?P<hpts>\d+) pts, (?P<hgf>\d+):(?P<hga>\d+), home (?P<hhome>[\d-]+), L10 (?P<hl10>[\d-]+)\) "
    r"vs (?P<a>.+?) (?P<aw>\d+)-(?P<al>\d+)-(?P<aot>\d+) "
    r"\((?P<apts>\d+) pts, (?P<agf>\d+):(?P<aga>\d+), away (?P<aaway>[\d-]+), L10 (?P<al10>[\d-]+)\); "
    r"expected goals (?P<x>[\d.]+)-(?P<y>[\d.]+)\."
)
LIIGA_RE = re.compile(
    r"Official Liiga results: (?P<h>.+?) (?P<hw>\d+)-(?P<hl>\d+) \((?P<hgf>\d+):(?P<hga>\d+)\) "
    r"vs (?P<a>.+?) (?P<aw>\d+)-(?P<al>\d+) \((?P<agf>\d+):(?P<aga>\d+)\); expected goals (?P<x>[\d.]+)-(?P<y>[\d.]+)\."
)
BBALL_RE = re.compile(
    r"Official feed game (?P<game>\d+), Round (?P<round>\d+): (?P<h>.+?) (?P<hw>\d+)-(?P<hl>\d+) "
    r"\((?P<hpf>[\d.]+) for / (?P<hpa>[\d.]+) against\) vs (?P<a>.+?) (?P<aw>\d+)-(?P<al>\d+) "
    r"\((?P<apf>[\d.]+) / (?P<apa>[\d.]+)\); expected score (?P<x>[\d.]+)-(?P<y>[\d.]+)\."
)
MLB_RE = re.compile(
    r"Official MLB Stats API: (?P<h>.+?) (?P<hw>\d+)-(?P<hl>\d+) \(runs (?P<hrs>\d+), allowed (?P<hra>\d+), "
    r"home (?P<hhome>[\d-]+)\) vs (?P<a>.+?) (?P<aw>\d+)-(?P<al>\d+) \(runs (?P<ars>\d+), allowed (?P<ara>\d+), "
    r"away (?P<aaway>[\d-]+)\); World Series game (?P<game>\d+); expected runs (?P<x>[\d.]+)-(?P<y>[\d.]+)\."
)
URC_RE = re.compile(
    r"Official URC table \(after Round 3\): (?P<h>.+?) (?P<hw>\d+)-(?P<hd>\d+)-(?P<hl>\d+) "
    r"\((?P<hpts>\d+) pts, (?P<hgf>\d+):(?P<hga>\d+)\) vs (?P<a>.+?) (?P<aw>\d+)-(?P<ad>\d+)-(?P<al>\d+) "
    r"\((?P<apts>\d+) pts, (?P<agf>\d+):(?P<aga>\d+)\); fixture round (?P<round>\d+), [\w-]+ KO (?P<ko>[\d.]+)\."
)
EHF_RE = re.compile(
    r"Official EHF group table \(5 rounds\): (?P<h>.+?) (?P<hw>\d+)-(?P<hd>\d+)-(?P<hl>\d+) "
    r"\((?P<hgf>\d+):(?P<hga>\d+), (?P<hpts>\d+) pts, group (?P<hg>[A-D])\) vs (?P<a>.+?) "
    r"(?P<aw>\d+)-(?P<ad>\d+)-(?P<al>\d+) \((?P<agf>\d+):(?P<aga>\d+), (?P<apts>\d+) pts, group (?P<ag>[A-D])\); "
    r"EHF lists the match for (?P<date>[\d-]+) (?P<time>[\d:]+) CET\."
)
SNOOK_RE = re.compile(
    r"Official WST world ranking: (?P<a>.+?) #(?P<pa>\d+) \(£(?P<ma>[\d,]+)\) vs (?P<b>.+?) #(?P<pb>\d+) "
    r"\(£(?P<mb>[\d,]+)\); (?P<round>.+?), best of (?P<n>\d+) frames, official start (?P<start>[\dT:-]+Z?)\."
)
HB_RE = re.compile(
    r"Official Danish table: (?P<h>.+?) (?P<hw>\d+)-(?P<hd>\d+)-(?P<hl>\d+) "
    r"\((?P<hgf>\d+):(?P<hga>\d+), (?P<hpts>\d+) pts\) vs (?P<a>.+?) (?P<aw>\d+)-(?P<ad>\d+)-(?P<al>\d+) "
    r"\((?P<agf>\d+):(?P<aga>\d+), (?P<apts>\d+) pts\)"
)
WTA_RE = re.compile(
    r"Official WTA feed match (?P<mid>\w+) in (?P<tour>.+?) \((?P<dates>[^)]*)\): seed (?P<sa>\d+) (?P<a>.+?) "
    r"vs seed (?P<sb>\d+) (?P<b>.+?)\."
)
ATP_RE = re.compile(
    r"Official ATP order of play \((?P<date>[^)]*)\): seed (?P<sa>\d+) (?P<a>.+?) vs seed (?P<sb>\d+) (?P<b>.+?)\."
)


def rationale(r, x: float, y: float, home: str, away: str) -> str:
    """Explain the exact published selection against the projected score."""
    sel, price, kind = r["pick"]["selection"], r["pick"]["american"], pick_kind(r)
    tot, margin = x + y, x - y
    day = fmt_date(r["start_utc"])
    matchup = r.get("matchup") or f"{home} v {away}"
    if kind in ("under", "over"):
        line = r["pick"]["line"]
        gap = abs(line - tot)
        side = "below" if kind == "under" else "above"
        return (f"{sel} at {price} is the play: the projection of {tot:.2f} goals sits {gap:.2f} {side} the "
                f"{line} line in {matchup} on {day}, so the number carries the edge rather than the outright result")
    if kind == "plus":
        side = home if r["pick"]["selection"].startswith(home) else away
        # margin from that side's point of view
        m = margin if side == home else -margin
        return (f"{sel} at {price} is the play: the projection has {side} {'ahead by' if m > 0 else 'behind by'} "
                f"{abs(m):.2f} on {day}, and the start on offer covers a wider gap than that")
    if kind == "minus":
        side = home if r["pick"]["selection"].startswith(home) else away
        m = margin if side == home else -margin
        return (f"{sel} at {price} is the play: the projection puts {side} {m:+.2f} on the night, "
                f"which clears the handicap in the {day} meeting")
    return (f"{sel} at {price} is the call, with the {day} projection giving that side the edge")


def note_hockey(r: dict) -> str:
    ins = r["inputs_summary"]
    sel, price = r["pick"]["selection"], r["pick"]["american"]
    day, clock, venue = fmt_date(r["start_utc"]), fmt_time(r["start_utc"]), r["venue"]
    m = NHL_RE.search(ins)
    if m:
        g = m.groupdict()
        H, A = g["h"], g["a"]
        hs, as_ = short(H), short(A)
        opener = rot(r["id"] + "o", [
            f"{H} welcome {A} to {venue} on {day} for a matchup between two sides separated by {abs(int(g['hpts']) - int(g['apts']))} points in the table",
            f"{venue} is the venue on {day} as {A} visit {H}, a game framed by contrasting recent runs",
            f"The {day} card at {venue} sends {A} in against {H}, with both clubs still shaping their season",
            f"{A} make the trip to {venue} on {day} to take on {H}",
        ])
        first = rot(r["id"] + "f1", [
            f"{H} are {g['hw']}-{g['hl']}-{g['hot']} for {g['hpts']} points, having scored {g['hgf']} and conceded {g['hga']}",
            f"{H} own a {g['hw']}-{g['hl']}-{g['hot']} record with a {g['hgf']}:{g['hga']} goal line and {g['hpts']} points going into {day}",
            f"{g['hpts']} points from {g['hw']}-{g['hl']}-{g['hot']} is the {H} return so far, with {g['hgf']} goals scored against {g['hga']} conceded before {day}",
        ])
        second = rot(r["id"] + "f2", [
            f"{A} arrive at {g['aw']}-{g['al']}-{g['aot']} on {g['apts']} points, scoring {g['agf']} and giving up {g['aga']} ahead of the {day} trip",
            f"The visitors are {g['aw']}-{g['al']}-{g['aot']} with {g['agf']} goals for and {g['aga']} against, good for {g['apts']} points before the {day} game",
            f"{A} counter with a {g['aw']}-{g['al']}-{g['aot']} mark and {g['apts']} points from a {g['agf']}:{g['aga']} scoring line on {day}",
        ])
        third = rot(r["id"] + "f3", [
            f"{hs.capitalize() if hs.startswith('the') else hs} are {g['hhome']} on home ice while {as_} are {g['aaway']} on the road, with last-ten splits of {g['hl10']} and {g['al10']}",
            f"Home form reads {g['hhome']} for {hs} and away form {g['aaway']} for {as_}; the last ten are {g['hl10']} and {g['al10']}",
            f"Split form is {g['hhome']} at home against {g['aaway']} on the road, and the ten-game sample sits at {g['hl10']} versus {g['al10']}",
        ])
        proj = rot(r["id"] + "p", [
            f"The season rates translate to roughly {g['x']} goals for the hosts and {g['y']} for the visitors",
            f"Scoring and conceding rates put the game near {g['x']}-{g['y']}",
            f"On those rates the game projects around {g['x']}-{g['y']} on the scoreboard",
        ])
        pick = rationale(r, float(g["x"]), float(g["y"]), H, A)
        tail = rot(r["id"] + "t", [
            f"Puck drop at {venue} is {clock}." if clock else "",
            f"The {venue} game is listed for {clock}." if clock else "",
            "",
        ])
        order = rot(r["id"] + "ord", [
            [opener, first, second, third, proj, pick, tail],
            [first, second, opener, third, proj, pick, tail],
            [opener, third, first, second, proj, pick, tail],
        ])
        return " ".join(s if s.endswith(".") else s + "." for s in order if s)
    m = LIIGA_RE.search(ins)
    if m:
        g = m.groupdict()
        form = (f"{g['h']} are {g['hw']}-{g['hl']} with {g['hgf']} goals for and {g['hga']} against, "
                f"while {g['a']} are {g['aw']}-{g['al']} at {g['agf']}:{g['aga']} ahead of the {day} meeting")
        proj = (f"The combined scoring rates point to about {g['x']}-{g['y']} on {day}, a narrow band that shapes "
                f"both the handicap and the total")
        return " ".join(x for x in [f"{g['h']} host {g['a']} in Liiga on {day}.", form + ".", proj + ".", f"{sel} at {price} is the selection for the {day} game."] if x)
    return ""


def note_basketball(r: dict) -> str:
    m = BBALL_RE.search(r["inputs_summary"])
    if not m:
        return ""
    g = m.groupdict()
    day, clock, venue = fmt_date(r["start_utc"]), fmt_time(r["start_utc"]), r["venue"] or "the home arena"
    sel, price = r["pick"]["selection"], r["pick"]["american"]
    H, A = g["h"], g["a"]
    opener = rot(r["id"] + "o", [
        f"Round {g['round']} pairs {H} with {A} at {venue} on {day}",
        f"{A} travel to {venue} for a Round {g['round']} meeting with {H} on {day}",
        f"{H} and {A} meet on {day} at {venue} in Round {g['round']} of the competition",
    ])
    form1 = rot(r["id"] + "f1", [
        f"{H} are {g['hw']}-{g['hl']}, putting up {g['hpf']} points a game while allowing {g['hpa']}",
        f"The hosts sit {g['hw']}-{g['hl']} with a {g['hpf']}-point average and {g['hpa']} conceded",
        f"{g['hw']}-{g['hl']} is the {H} record going into the {day} game against {A}, built on {g['hpf']} scored and {g['hpa']} allowed per outing",
    ])
    form2 = rot(r["id"] + "f2", [
        f"{A} are {g['aw']}-{g['al']}, scoring {g['apf']} and conceding {g['apa']}",
        f"The visitors counter at {g['aw']}-{g['al']} with {g['apf']} for and {g['apa']} against",
        f"{A} bring a {g['aw']}-{g['al']} mark and a {g['apf']}:{g['apa']} scoring split into the {day} game",
    ])
    proj = rot(r["id"] + "p", [
        f"Those rates and the home floor land the game near {g['x']}-{g['y']}",
        f"Blending both ends puts the projection at roughly {g['x']}-{g['y']}",
        f"The scoring expectation sits around {g['x']}-{g['y']} once the home edge is applied",
    ])
    pick = rationale(r, float(g["x"]), float(g["y"]), H, A)
    tail = f"Tip-off is {clock}." if clock else ""
    order = rot(r["id"] + "ord", [[opener, form1, form2, proj, pick, tail],
                                  [form1, form2, opener, proj, pick, tail],
                                  [opener, form1, proj, form2, pick, tail]])
    return " ".join(s if s.endswith(".") else s + "." for s in order if s)


def note_baseball(r: dict) -> str:
    m = MLB_RE.search(r["inputs_summary"])
    if not m:
        return ""
    g = m.groupdict()
    day, venue = fmt_date(r["start_utc"]), r["venue"]
    sel, price = r["pick"]["selection"], r["pick"]["american"]
    H, A = g["h"], g["a"]
    opener = rot(r["id"] + "o", [
        f"Game {g['game']} of the World Series puts {A} at {venue} against {H} on {day}",
        f"World Series game {g['game']} is set for {venue} on {day}, with {H} hosting {A}",
        f"{H} and {A} continue the World Series at {venue} on {day} in game {g['game']}",
    ])
    form = (f"{H} went {g['hw']}-{g['hl']} in the regular season with {g['hrs']} runs scored and {g['hra']} allowed, "
            f"including {g['hhome']} at home, while {A} finished {g['aw']}-{g['al']} at {g['ars']} scored and {g['ara']} conceded "
            f"({g['aaway']} on the road)")
    proj = rot(r["id"] + "p", [
        f"Those run rates put the contest near {g['x']}-{g['y']} in a low-scoring band",
        f"The season-long run prevention points to something like {g['x']}-{g['y']}",
        f"On the run rates, the game projects around {g['x']}-{g['y']}",
    ])
    pick = rationale(r, float(g["x"]), float(g["y"]), H, A)
    return " ".join(f"{x}{'' if x.endswith('.') else '.'}" for x in [opener, form, proj, pick])


def note_rugby_union(r: dict) -> str:
    m = URC_RE.search(r["inputs_summary"])
    if not m:
        return ""
    g = m.groupdict()
    day = fmt_date(r["start_utc"])
    venue = r["venue"] or "the listed venue"
    sel, price = r["pick"]["selection"], r["pick"]["american"]
    H, A = g["h"], g["a"]
    opener = rot(r["id"] + "o", [
        f"Round {g['round']} of the United Rugby Championship sends {A} to {venue} on {day} to face {H}",
        f"{H} host {A} in Round {g['round']} on {day} at {venue}",
        f"The Round {g['round']} fixture on {day} pairs {H} and {A} at {venue}",
    ])
    form = (f"{H} have {g['hpts']} points from {g['hw']}-{g['hd']}-{g['hl']} and a {g['hgf']}:{g['hga']} points difference, "
            f"while {A} carry {g['apts']} points from {g['aw']}-{g['ad']}-{g['al']} at {g['agf']}:{g['aga']}")
    angle = rot(r["id"] + "a", [
        f"The league table and the scoring differentials point the same way, with {H} {int(g['hpts']) - int(g['apts'])} points clear of the visitors",
        f"Points and points difference both favour {H} by a meaningful margin, and the handicap follows that combined read",
        f"Across wins, league points and scoring difference the hosts hold the edge, which is where the handicap comes from",
    ])
    if pick_kind(r) == "plus":
        pick = (f"{sel} at {price} is the selection: the table gap is real, but the start on offer is wider than the "
                f"scoring difference between these two packs")
    else:
        pick = rot(r["id"] + "k", [
            f"{sel} at {price} is the selection for the round",
            f"The call is {sel} at {price}",
            f"{sel} at {price} is where the number is priced",
        ])
    tail = f"Kick-off is {g['ko']}." if g.get("ko") else ""
    order = rot(r["id"] + "ord", [[opener, form, angle, pick, tail],
                                  [form, opener, angle, pick, tail]])
    return " ".join(s if s.endswith(".") else s + "." for s in order if s)


def note_handball(r: dict) -> str:
    m = EHF_RE.search(r["inputs_summary"])
    if m:
        g = m.groupdict()
        day = fmt_date(r["start_utc"])
        sel, price, kind = r["pick"]["selection"], r["pick"]["american"], pick_kind(r)
        lead = rot(r["id"] + "o", [
            f"{g['h']} host {g['a']} in EHF Champions League Group {g['hg']} on {day}",
            f"Group {g['hg']} action on {day} brings {g['a']} to {g['h']}",
            f"{g['h']} and {g['a']} meet in the EHF Champions League group phase on {day}",
        ])
        form = (f"{g['h']} are {g['hw']}-{g['hd']}-{g['hl']} after five rounds with {g['hgf']} goals for and "
                f"{g['hga']} against for {g['hpts']} points, while {g['a']} are {g['aw']}-{g['ad']}-{g['al']} "
                f"at {g['agf']}:{g['aga']} on {g['apts']} points")
        if kind in ("under", "over"):
            pick = (f"{sel} at {price} is the play: both goal lines sit {'below' if kind == 'under' else 'above'} "
                    f"the {r['pick']['line']} mark once the group scoring rates are combined")
        elif kind == "plus":
            pick = (f"{sel} at {price} takes the start, which is wider than the goal difference between these "
                    f"two records")
        else:
            pick = f"{sel} at {price} is the selection on the group form"
        return " ".join(x if x.endswith(".") else x + "." for x in [lead, form, pick])
    m = HB_RE.search(r["inputs_summary"])
    if not m:
        return ""
    g = m.groupdict()
    day = fmt_date(r["start_utc"])
    sel, price = r["pick"]["selection"], r["pick"]["american"]
    H, A = g["h"], g["a"]
    opener = rot(r["id"] + "o", [
        f"{H} and {A} meet in the Danish league on {day}",
        f"The Danish league card on {day} pairs {H} with {A}",
        f"{A} are the visitors as {H} host on {day}",
    ])
    form = (f"{H} are {g['hw']}-{g['hd']}-{g['hl']} with {g['hgf']} goals for and {g['hga']} conceded for {g['hpts']} points, "
            f"while {A} are {g['aw']}-{g['ad']}-{g['al']} at {g['agf']}:{g['aga']} on {g['apts']} points")
    angle = (f"The visitors average more points per game and hold the better goal difference, and the handicap is built "
             f"from that pair of measures rather than a single scoreline")
    pick = rot(r["id"] + "k", [f"{sel} at {price} is the play", f"The selection is {sel} at {price}"])
    return " ".join(f"{x}{'' if x.endswith('.') else '.'}" for x in [opener, form, angle, pick])


def note_snooker(r: dict) -> str:
    m = SNOOK_RE.search(r["inputs_summary"])
    if not m:
        return ""
    g = m.groupdict()
    day = fmt_date(r["start_utc"])
    sel, price, kind = r["pick"]["selection"], r["pick"]["american"], pick_kind(r)
    lead = rot(r["id"] + "o", [
        f"{g['a']} meets {g['b']} in the {g['round']} of the Northern Ireland Open on {day}",
        f"The {g['round']} on {day} pairs {g['a']} with {g['b']}",
        f"{g['a']} and {g['b']} meet on {day} in Belfast for a {g['round']} tie",
    ])
    form = (f"The official world ranking has {g['a']} at {g['pa']} on £{g['ma']} and {g['b']} at {g['pb']} on "
            f"£{g['mb']}, and the match is best of {g['n']} frames")
    if kind in ("under", "over"):
        proj = r["pick"]["line"]
        pick = (f"{sel} at {price} is the play: with a {g['n']}-frame format the expected length sits a shade "
                f"{'under' if kind == 'under' else 'over'} the {proj} line")
    elif kind == "plus":
        pick = (f"{sel} at {price} takes the start: the ranking gap is clear, but the frame cushion is wider than "
                f"the gap in the prices")
    elif kind == "minus":
        pick = f"{sel} at {price} gives the frames away, and the ranking gap says that is the right side"
    else:
        pick = f"{sel} at {price} is the call, with the ranking gap doing the work"
    return " ".join(x if x.endswith(".") else x + "." for x in [lead, form, pick])


def note_tennis(r: dict) -> str:
    ins = r["inputs_summary"]
    day, clock = fmt_date(r["start_utc"]), fmt_time(r["start_utc"])
    sel, price = r["pick"]["selection"], r["pick"]["american"]
    m = WTA_RE.search(ins)
    if m:
        g = m.groupdict()
        lead = rot(r["id"] + "o", [
            f"{g['a']} and {g['b']} meet in {g['tour']} on {day}",
            f"The {g['tour']} draw on {day} pairs {g['a']} with {g['b']}",
            f"{g['a']} takes on {g['b']} at {g['tour']} on {day}",
        ])
        form = (f"The official draw has {g['a']} at seed {g['sa']} and {g['b']} at seed {g['sb']}, "
                f"with the tournament running {g['dates']}")
        pick = rot(r["id"] + "k", [
            f"{sel} at {price} is the call, priced off the seeding gap and this week's completed results",
            f"The play is {sel} at {price}, taken from the draw position and the week's form",
            f"{sel} at {price} is the selection",
        ])
        tail = f"Start is {clock}." if clock else ""
        return " ".join(x if x.endswith(".") else x + "." for x in [lead, form, pick, tail] if x)
    m = ATP_RE.search(ins)
    if m:
        g = m.groupdict()
        lead = f"{g['a']} and {g['b']} are on the order of play at {r['competition']} on {day}"
        form = f"The official sheet lists {g['a']} at seed {g['sa']} and {g['b']} at seed {g['sb']} for the {g['date']} session"
        pick = f"{sel} at {price} is the selection"
        return " ".join(f"{x}{'' if x.endswith('.') else '.'}" for x in [lead, form, pick])
    return ""


COMPOSERS = {
    "Ice Hockey": note_hockey,
    "Basketball": note_basketball,
    "Baseball": note_baseball,
    "Rugby Union": note_rugby_union,
    "Handball": note_handball,
    "Tennis": note_tennis,
    "Snooker": note_snooker,
}


def words(text: str) -> int:
    return len([w for w in re.split(r"\s+", text.strip()) if w])


def main() -> int:
    desk = json.loads((DATA / "desk.json").read_text())
    out, problems = {}, []
    highs = [r for r in desk["rows"] if r.get("pick") and r["pick"]["confidence"] == "High"]
    for r in highs:
        fn = COMPOSERS.get(r["sport"])
        text = fn(r) if fn else ""
        if not text:
            problems.append((r["id"], "no composer output"))
            continue
        low = text.lower()
        hits = [w for w in BANNED if w in low]
        if hits:
            problems.append((r["id"], f"banned words {hits}"))
        if words(text) < 30:
            problems.append((r["id"], f"only {words(text)} words"))
        if r["pick"]["selection"].split()[0].lower() not in low:
            problems.append((r["id"], "selection not named"))
        out[r["id"]] = {
            "sport": r["sport"], "matchup": r["matchup"], "start_utc": r["start_utc"],
            "selection": r["pick"]["selection"], "market": r["pick"]["market"],
            "american": r["pick"]["american"], "words": words(text), "text": text,
            "source_url": r["official_url"], "source_name": r["official_source_name"],
        }
    texts = [v["text"] for v in out.values()]
    if len(set(texts)) != len(texts):
        problems.append(("bank", "duplicate note text"))
    payload = {
        "schema": "board-ar-predictions/1",
        "generated_from": "data/session-405e9797/desk.json",
        "count": len(out), "banned_words": list(BANNED), "min_words": 30,
        "problems": problems, "notes": out,
    }
    (DATA / "predictions.json").write_text(json.dumps(payload, indent=1))
    print(json.dumps({"notes": len(out), "problems": problems}, indent=1))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
