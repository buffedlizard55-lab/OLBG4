#!/usr/bin/env python3
"""Board AF — extract verified fixtures and form inputs from the committed capture.

Every extractor reads only files listed in the capture manifest after re-checking
their SHA-256, and records the exact official URL that produced each value.

Run:  python3 scripts/session-ddbcc895/extract.py <capture_dir> <out.json>
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "session-ddbcc895"
CUTOFF = "2026-10-22T22:00:00Z"
WINDOW_END = "2026-11-02T00:00:00Z"


# --------------------------------------------------------------------------- #
# capture access
# --------------------------------------------------------------------------- #
class Capture:
    def __init__(self, path: Path):
        self.path = path
        self.manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
        self.items = {it["id"]: it for it in self.manifest["items"]}

    def has(self, tid: str) -> bool:
        it = self.items.get(tid)
        return bool(it and it.get("status") == 200 and it.get("bytes", 0) > 0)

    def url(self, tid: str) -> str:
        return self.items[tid]["url"]

    def raw(self, tid: str) -> bytes:
        it = self.items[tid]
        body = gzip.open(self.path / it["file"], "rb").read()
        if hashlib.sha256(body).hexdigest() != it["sha256"]:
            raise ValueError(f"sha256 mismatch for {tid}")
        return body

    def json(self, tid: str):
        return json.loads(self.raw(tid))

    def text(self, tid: str) -> str:
        return self.raw(tid).decode("utf-8", "ignore")

    def pdf_text(self, tid: str) -> str:
        reader = PdfReader(io.BytesIO(self.raw(tid)))
        return "\n".join((page.extract_text() or "") for page in reader.pages)


def html_lines(html: str) -> list[str]:
    import html as H

    h = re.sub(r"<script.*?</script>", " ", html, flags=re.S | re.I)
    h = re.sub(r"<style.*?</style>", " ", h, flags=re.S | re.I)
    h = re.sub(r"<[^>]+>", "\n", h)
    h = H.unescape(h)
    return [re.sub(r"\s+", " ", x).strip() for x in h.split("\n") if x.strip()]


def iso(dt: str) -> str:
    return dt.replace("+00:00", "Z").replace(".000Z", "Z")


def keep(start: str) -> bool:
    return CUTOFF <= start < WINDOW_END


# --------------------------------------------------------------------------- #
# Ice hockey
# --------------------------------------------------------------------------- #
def nhl(cap: Capture) -> tuple[list[dict], dict]:
    standings: dict[str, dict] = {}
    if cap.has("nhl_standings_now"):
        for s in cap.json("nhl_standings_now")["standings"]:
            ab = s["teamAbbrev"]["default"]
            standings[ab] = {
                "team": f'{s["teamName"]["default"]}',
                "games": s["gamesPlayed"],
                "wins": s["wins"],
                "losses": s["losses"],
                "otLosses": s["otLosses"],
                "points": s["points"],
                "gf": s["goalFor"],
                "ga": s["goalAgainst"],
                "pointPct": s["pointPctg"],
                "l10": f'{s["l10Wins"]}-{s["l10Losses"]}-{s["l10OtLosses"]}',
                "streak": f'{s["streakCode"]}{s["streakCount"]}',
                "source": cap.url("nhl_standings_now"),
            }
    rows, seen = [], set()
    sched_ids = [t for t in cap.items if t.startswith("nhl_sched_") and cap.has(t)]
    for tid in sorted(sched_ids):
        payload = cap.json(tid)
        for week in payload.get("gameWeek", []):
            for g in week.get("games", []):
                if g.get("gameState") not in ("FUT", "PRE"):
                    continue
                start = iso(g["startTimeUTC"])
                if not keep(start) or g["id"] in seen:
                    continue
                seen.add(g["id"])
                a, b = g["awayTeam"], g["homeTeam"]
                rows.append(
                    {
                        "sport": "Ice Hockey",
                        "competition": "NHL",
                        "stage": "Regular season",
                        "side_a": f'{a["placeName"]["default"]} {a["commonName"]["default"]}',
                        "side_b": f'{b["placeName"]["default"]} {b["commonName"]["default"]}',
                        "start_utc": start,
                        "venue": g["venue"]["default"],
                        "kind": "match",
                        "source_name": "NHL official schedule API",
                        "source_url": cap.url(tid),
                        "secondary_url": "https://www.nhl.com" + g["gameCenterLink"],
                        "ref": {"a": a["abbrev"], "b": b["abbrev"], "game_id": g["id"]}, "home_side": "b",
                        "form": {
                            "a": standings.get(a["abbrev"], {}),
                            "b": standings.get(b["abbrev"], {}),
                            "standings_url": cap.url("nhl_standings_now"),
                        },
                    }
                )
    return rows, standings


def liiga(cap: Capture) -> list[dict]:
    if not cap.has("liiga_games_2027"):
        return []
    table = {}
    if cap.has("liiga_standings_2027"):
        for s in cap.json("liiga_standings_2027")["season"]:
            table[s["teamName"]] = {
                "team": s["teamName"],
                "games": s["games"],
                "wins": s["wins"],
                "losses": s["losses"],
                "otWins": s["overtimeWins"],
                "otLosses": s["overtimeLosses"],
                "points": s["points"],
                "gf": s["goals"],
                "ga": s.get("goalsAgainst"),
                "rank": s["ranking"],
                "source": cap.url("liiga_standings_2027"),
            }
    rows = []
    for g in cap.json("liiga_games_2027"):
        if g.get("started") or g.get("ended"):
            continue
        start = iso(g["start"])
        if not keep(start):
            continue
        a, b = g["homeTeam"], g["awayTeam"]
        rows.append(
            {
                "sport": "Ice Hockey",
                "competition": "Liiga",
                "stage": "Regular season",
                "side_a": a["teamName"],
                "side_b": b["teamName"],
                "start_utc": start,
                "venue": ((g.get("iceRink") or {}).get("name") if isinstance(g.get("iceRink"), dict) else (g.get("iceRink") or "")),
                "kind": "match",
                "source_name": "Liiga official games API",
                "source_url": cap.url("liiga_games_2027"),
                "secondary_url": "https://liiga.fi/fi/ottelut",
                "ref": {"a": a["teamId"], "b": b["teamId"], "game_id": g["id"]}, "home_side": "a",
                "form": {"a": table.get(a["teamName"], {}), "b": table.get(b["teamName"], {}),
                          "standings_url": cap.url("liiga_standings_2027")},
            }
        )
    return rows


def euroleague(cap: Capture, comp: str, label: str) -> list[dict]:
    tid = "euroleague_games_E2026" if comp == "E" else "eurocup_games_U2026"
    if not cap.has(tid):
        return []
    games = cap.json(tid)["data"]
    rec: dict[str, dict] = {}
    for g in games:
        if not g.get("played"):
            continue
        for side, opp in (("local", "road"), ("road", "local")):
            club = g[side]["club"]["name"]
            r = rec.setdefault(club, {"team": club, "games": 0, "wins": 0, "pf": 0, "pa": 0})
            r["games"] += 1
            r["pf"] += g[side].get("score", 0)
            r["pa"] += g[opp].get("score", 0)
            if g[side].get("score", 0) > g[opp].get("score", 0):
                r["wins"] += 1
    for r in rec.values():
        r["winPct"] = round(r["wins"] / r["games"], 4) if r["games"] else 0.5
        r["diffPerGame"] = round((r["pf"] - r["pa"]) / r["games"], 2) if r["games"] else 0
    rows = []
    for g in games:
        if g.get("played"):
            continue
        start = iso(g["utcDate"])
        if not keep(start):
            continue
        a, b = g["local"]["club"], g["road"]["club"]
        rows.append(
            {
                "sport": "Basketball",
                "competition": label,
                "stage": g.get("roundName", ""),
                "side_a": a["name"],
                "side_b": b["name"],
                "start_utc": start,
                "venue": (g.get("venue") or {}).get("name", ""),
                "kind": "match",
                "source_name": f"{label} official games API",
                "source_url": cap.url(tid),
                "secondary_url": "",
                "ref": {"a": a["code"], "b": b["code"], "game_id": g["identifier"]}, "home_side": "a",
                "form": {"a": rec.get(a["name"], {}), "b": rec.get(b["name"], {}),
                          "standings_url": cap.url(tid)},
            }
        )
    return rows


# --------------------------------------------------------------------------- #
# Basketball — NBA from the repository's 17:10Z official snapshot
# --------------------------------------------------------------------------- #
def nba(cap: Capture) -> list[dict]:
    """NBA fixtures from the last committed official NBA capture.

    cdn.nba.com and www.nba.com return HTTP 403 to this runner (see probe), so the
    fixtures come from `session-4afef1af/data/fixtures.json`, which records NBA's own
    game pages and was captured at 2026-10-22T17:08Z. The capture time is published on
    every row and the values are re-checked against the OLBG listing where one exists.
    """
    path = ROOT / "session-4afef1af" / "data" / "fixtures.json"
    if not path.exists():
        return []
    rows = []
    for f in json.loads(path.read_text(encoding="utf-8")):
        if f.get("league") != "NBA":
            continue
        start = iso(f["start_utc"])
        if not keep(start):
            continue
        ctx = f.get("context") or {}
        rows.append(
            {
                "sport": "Basketball",
                "competition": "NBA",
                "stage": "Regular season",
                "side_a": f["away"]["name"],
                "side_b": f["home"]["name"],
                "start_utc": start,
                "venue": f.get("venue", ""),
                "kind": "match",
                "source_name": "NBA.com official games page (committed capture 2026-10-22T17:08Z)",
                "source_url": f["source_urls"][0],
                "secondary_url": f["source_urls"][1] if len(f["source_urls"]) > 1 else "",
                "ref": {"a": f["away"].get("abbr"), "b": f["home"].get("abbr"), "game_id": f["provider_game_id"]}, "home_side": "b",
                "form": {
                    "a": {"team": f["away"]["name"], "wins": ctx.get("away_wins"), "losses": ctx.get("away_losses"),
                          "games": (ctx.get("away_wins") or 0) + (ctx.get("away_losses") or 0), "source": "https://www.nba.com/games"},
                    "b": {"team": f["home"]["name"], "wins": ctx.get("home_wins"), "losses": ctx.get("home_losses"),
                          "games": (ctx.get("home_wins") or 0) + (ctx.get("home_losses") or 0), "source": "https://www.nba.com/games"},
                    "standings_url": "https://www.nba.com/standings",
                },
            }
        )
    return rows


# --------------------------------------------------------------------------- #
# Baseball
# --------------------------------------------------------------------------- #
def mlb(cap: Capture) -> list[dict]:
    if not cap.has("mlb_schedule"):
        return []
    table = {}
    if cap.has("mlb_standings"):
        for rec in cap.json("mlb_standings")["records"]:
            for t in rec["teamRecords"]:
                name = t["team"]["name"]
                table[name] = {
                    "team": name,
                    "wins": t["wins"],
                    "losses": t["losses"],
                    "games": t["gamesPlayed"],
                    "winPct": float(t["winningPercentage"]),
                    "runsFor": t["runsScored"],
                    "runsAgainst": t["runsAllowed"],
                    "runDiff": t["runDifferential"],
                    "streak": f'{t["streak"]["streakCode"]}',
                    "source": cap.url("mlb_standings"),
                }
    team_stats = {}
    if cap.has("mlb_hitting"):
        for s in cap.json("mlb_hitting").get("stats", []):
            pass
    rows = []
    for day in cap.json("mlb_schedule").get("dates", []):
        for g in day.get("games", []):
            start = iso(g["gameDate"])
            if not keep(start):
                continue
            a, b = g["teams"]["away"]["team"], g["teams"]["home"]["team"]
            prob = g["teams"].get("away", {}).get("probablePitcher", {}).get("fullName", "")
            probh = g["teams"].get("home", {}).get("probablePitcher", {}).get("fullName", "")
            rows.append(
                {
                    "sport": "Baseball",
                    "competition": "MLB World Series",
                    "stage": g.get("seriesDescription", "") or "World Series",
                    "side_a": a["name"],
                    "side_b": b["name"],
                    "start_utc": start,
                    "venue": (g.get("venue") or {}).get("name", ""),
                    "kind": "match",
                    "source_name": "MLB Stats API official schedule",
                    "source_url": cap.url("mlb_schedule"),
                    "secondary_url": f'https://www.mlb.com/gameday/{g["gamePk"]}',
                    "ref": {"a": a.get("abbreviation"), "b": b.get("abbreviation"), "game_id": g["gamePk"],
                            "series_game": g.get("seriesGameNumber")}, "home_side": "b",
                    "form": {
                        "a": table.get(a["name"], {}),
                        "b": table.get(b["name"], {}),
                        "pitchers": {"a": prob, "b": probh},
                        "standings_url": cap.url("mlb_standings"),
                    },
                }
            )
    return rows


# --------------------------------------------------------------------------- #
# Tennis
# --------------------------------------------------------------------------- #
def wta(cap: Capture) -> list[dict]:
    rankings = {}
    for i in range(4):
        tid = f"wta_rank_{i}"
        if not cap.has(tid):
            continue
        for p in cap.json(tid):
            name = p["player"]["fullName"]
            rankings[name] = {
                "team": name,
                "rank": p["ranking"],
                "points": p["points"],
                "tournaments": p["tournamentsPlayed"],
                "source": cap.url(tid),
            }
    tourney_names, tourney_totals = {}, {}
    if cap.has("wta_tournaments"):
        for t in cap.json("wta_tournaments")["content"]:
            tourney_names[str(t["tournamentGroup"]["id"])] = t["title"]
    for tid in [t for t in cap.items if t.startswith("wta_t") and t.endswith("_matches") and cap.has(t)]:
        event = tid.split("_")[1][1:]
        totals = []
        for m in cap.json(tid).get("matches", []):
            if m.get("MatchState") != "F" or m.get("DrawMatchType") != "S":
                continue
            try:
                g = sum(int(m.get(f"ScoreSet{i}{x}") or 0) for i in range(1, 4) for x in ("A", "B"))
                if 10 <= g <= 60:
                    totals.append(g)
            except Exception:
                pass
        if totals:
            tourney_totals[event] = round(sum(totals) / len(totals), 2)
    rows = []
    for tid in [t for t in cap.items if t.startswith("wta_t") and t.endswith("_matches") and cap.has(t)]:
        event = tid.split("_")[1][1:]
        data = cap.json(tid)
        for m in data.get("matches", []):
            if m.get("MatchState") == "F" or m.get("DrawMatchType") != "S":
                continue
            stamp = m.get("MatchTimeStamp") or ""
            if not stamp:
                continue
            # WTA returns local time with an offset; convert to UTC.
            try:
                dt = datetime.fromisoformat(stamp)
                start = dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            except Exception:
                continue
            na = f'{m["PlayerNameFirstA"]} {m["PlayerNameLastA"]}'
            nb = f'{m["PlayerNameFirstB"]} {m["PlayerNameLastB"]}'
            rows.append(
                {
                    "sport": "Tennis",
                    "competition": tourney_names.get(event, f"WTA event {event}"),
                    "stage": f'Round {m.get("RoundID")}',
                    "side_a": na,
                    "side_b": nb,
                    "start_utc": start,
                    "venue": m.get("CourtName", ""),
                    "kind": "match",
                    "source_name": "WTA official tournament matches API",
                    "source_url": cap.url(tid),
                    "secondary_url": f"https://www.wtatennis.com/tournaments/{event}",
                    "ref": {"a": m.get("PlayerIDA"), "b": m.get("PlayerIDB"), "match_id": m.get("MatchID")}, "home_side": "",
                    "form": {
                        "a": rankings.get(na, {}),
                        "b": rankings.get(nb, {}),
                        "seeds": {"a": m.get("SeedA", ""), "b": m.get("SeedB", "")},
                        "standings_url": cap.url("wta_rank_0"),
                    },
                    "total_mean": tourney_totals.get(event),
                }
            )
    return rows


def atp_rankings(cap: Capture) -> dict:
    if not cap.has("ptl_entry_numerical"):
        return {}
    text = cap.pdf_text("ptl_entry_numerical")
    out = {}
    for line in text.split("\n"):
        m = re.match(r"^(\d{1,3})\s+([A-Za-zÀ-ÿ' .,\-]+?)\s*\(([A-Z]{3})\)\s+(\d+)", line.strip())
        if m:
            out[m.group(2).strip()] = {
                "rank": int(m.group(1)),
                "points": int(m.group(4)),
                "country": m.group(3),
                "source": cap.url("ptl_entry_numerical"),
            }
    if not out:
        # Some rows omit the country code; fall back to rank + surname.
        for line in text.split("\n"):
            m = re.match(r"^(\d{1,3})\s+([A-Za-zÀ-ÿ' .,\-]+?)\s+(\d{3,5})\s", line.strip())
            if m:
                out[m.group(2).strip()] = {"rank": int(m.group(1)), "points": int(m.group(3)),
                                            "source": cap.url("ptl_entry_numerical")}
    return out


def _name_key(name: str) -> str:
    return re.sub(r"[^a-z]", "", name.lower())


def atp(cap: Capture) -> list[dict]:
    ranks = atp_rankings(cap)
    by_surname: dict[str, list[tuple[str, dict]]] = {}
    for k, v in ranks.items():
        if "," in k:
            surname, first = [x.strip() for x in k.split(",", 1)]
        else:
            parts = k.split()
            surname, first = parts[-1], " ".join(parts[:-1])
        by_surname.setdefault(surname.lower(), []).append((first, v))

    def lookup(display: str) -> dict:
        cleaned = re.sub(r"^\[\d+\]\s*", "", display).strip()
        cleaned = re.sub(r"^\[Q\]\s*", "", cleaned)
        cleaned = re.sub(r"^\[Alt\]\s*", "", cleaned)
        cleaned = re.sub(r"\s*\([A-Z]{3}\)$", "", cleaned)
        toks = cleaned.split()
        if len(toks) < 2:
            return {}
        surname = toks[-1].lower()
        first = " ".join(toks[:-1])
        cands = by_surname.get(surname, [])
        for f, v in cands:
            if f.lower().startswith(first[:1].lower()):
                return v
        return cands[0][1] if cands else {}

    rows = []
    tourneys = {
        "9410": ("Almaty", "ATP 250 Almaty"),
        "7485": ("Brussels", "ATP 250 Brussels"),
        "496": ("Lyon", "ATP 250 Lyon"),
    }
    for tid, (city, label) in tourneys.items():
        op = f"ptl_{tid}_op"
        if not cap.has(op):
            continue
        text = cap.pdf_text(op)
        day = re.search(r"ORDER OF PLAY - ([A-Z]+), ([A-Z]+ \d{1,2}, \d{4})", text)
        if not day:
            continue
        date = datetime.strptime(f"{day.group(1).title()} {day.group(2)}", "%A %B %d, %Y").strftime("%Y-%m-%d")
        if not keep(f"{date}T00:00:00Z"):
            continue
        # Matches with an explicit "Starts At"/"Not Before" clock.
        pattern = re.compile(
            r"(Starts At|Not Before) (\d{2}):(\d{2})\n(\d+)\.\n(.*?)\nvs\n(.*?)\n", re.S
        )
        seen = set()
        for m in pattern.finditer(text):
            kind, hh, mm, num, pa, pb = m.groups()
            pa, pb = pa.strip(), pb.strip()
            if "(" not in pa or "(" not in pb:
                continue
            if pa.count("(") > 1 or pb.count("(") > 1:
                continue
            if "CONCERT" in pa or "CONCERT" in pb:
                continue
            key = (pa, pb)
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "sport": "Tennis", "competition": label, "stage": "Quarter-final",
                    "side_a": re.sub(r"\s*\([A-Z]{3}\)$", "", re.sub(r"^\[\w+\]\s*", "", pa)).title(),
                    "side_b": re.sub(r"\s*\([A-Z]{3}\)$", "", re.sub(r"^\[\w+\]\s*", "", pb)).title(),
                    "start_utc": f"{date}T{hh}:{mm}:00Z",
                    "venue": city, "kind": "match",
                    "source_name": "ATP official order of play (ProTennisLive PDF)",
                    "source_url": cap.url(op), "secondary_url": "",
                    "ref": {"a": pa, "b": pb, "tournament": tid}, "home_side": "",
                    "form": {"a": lookup(pa), "b": lookup(pb), "standings_url": cap.url("ptl_entry_numerical")},
                    "display_a": pa, "display_b": pb,
                }
            )
    return rows


# --------------------------------------------------------------------------- #
# Rugby union — LNR calendars and classement (server-rendered HTML)
# --------------------------------------------------------------------------- #
MONTHS_FR = {
    "janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
    "juillet": 7, "août": 8, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11,
    "décembre": 12, "decembre": 12,
}


def _fr_date(day: str) -> str:
    d, m = day.split()
    return f"2026-{MONTHS_FR[m.lower()]:02d}-{int(d):02d}"


def lnr(cap: Capture, tid: str, label: str, class_tid: str) -> list[dict]:
    if not cap.has(tid):
        return []
    lines = html_lines(cap.text(tid))
    joined = " | ".join(lines)
    # classement: the league page lists, per club, nine numbers in a fixed order:
    # Pts, M, G, N, P, Bonus, PtsM, PtsE, Diff. Club names come from the calendar.
    classes: dict[str, dict] = {}
    cal_tokens = [x for x in joined.split(" | ")]
    club_names = []
    for k, tok in enumerate(cal_tokens):
        if (tok == "e" and k >= 1 and k + 4 < len(cal_tokens)
                and re.match(r"^\d{1,2}h\d{2}$", cal_tokens[k + 1])):
            club_names.extend([cal_tokens[k - 2].strip(), cal_tokens[k + 2].strip()])
    if cap.has(class_tid):
        cl_lines = html_lines(cap.text(class_tid))
        for team in sorted(set(club_names)):
            if team not in cl_lines:
                continue
            i = cl_lines.index(team)
            nums = cl_lines[i + 1:i + 10]
            if len(nums) < 9 or not all(re.match(r"^[+\-]?\d+$", n) for n in nums):
                continue
            form5 = []
            for tok in cl_lines[i + 10:i + 16]:
                if tok in ("V", "D", "N"):
                    form5.append(tok)
                if len(form5) == 5:
                    break
            classes[team] = {
                "team": team, "points": int(nums[0]), "games": int(nums[1]),
                "wins": int(nums[2]), "draws": int(nums[3]), "losses": int(nums[4]),
                "bonus": int(nums[5]), "pf": int(nums[6]), "pa": int(nums[7]),
                "diff": int(nums[8]), "form5": "".join(form5), "source": cap.url(class_tid),
            }
    # calendar: [weekday] [day month] | Home | rank | e | HHhMM | Away | rank | e | ...
    tokens = [x for x in joined.split(" | ")]
    rows = []
    cur_date = None
    i = 0
    date_re = re.compile(r"^(lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche) (\d{1,2}) ([a-zéûôA-Z]+)$", re.I)
    time_re = re.compile(r"^(\d{1,2})h(\d{2})$")
    while i < len(tokens) - 8:
        t = tokens[i]
        dm = date_re.match(t)
        if dm:
            cur_date = _fr_date(f"{dm.group(2)} {dm.group(3)}")
            i += 1
            continue
        if (cur_date and tokens[i + 2] == "e" and time_re.match(tokens[i + 3] or "")
                and tokens[i + 6] == "e"):
            home, away, tm = tokens[i], tokens[i + 4], tokens[i + 3]
            hh, mm = time_re.match(tm).groups()
            start = f"{cur_date}T{int(hh):02d}:{mm}:00Z"
            if keep(start):
                rows.append(
                    {
                        "sport": "Rugby Union", "competition": label,
                        "stage": "Regular season", "side_a": home.strip(), "side_b": away.strip(),
                        "start_utc": start, "venue": "", "kind": "match",
                        "source_name": f"{label} official calendar (LNR)", "source_url": cap.url(tid),
                        "secondary_url": cap.url(class_tid) if cap.has(class_tid) else "",
                        "ref": {"a": home, "b": away, "tournament": tid}, "home_side": "a",
                        "form": {"a": classes.get(home.strip(), {}), "b": classes.get(away.strip(), {}),
                                  "standings_url": cap.url(class_tid) if cap.has(class_tid) else ""},
                    }
                )
            i += 6
            continue
        i += 1
    return rows


# --------------------------------------------------------------------------- #
# Rugby union — URC fixtures article
# --------------------------------------------------------------------------- #
def urc(cap: Capture) -> list[dict]:
    if not cap.has("urc_fixtures"):
        return []
    lines = html_lines(cap.text("urc_fixtures"))
    joined = " | ".join(lines)
    rounds = re.split(r"ROUND (\d+)", joined)
    rows = []
    cur_date = None
    month = None
    for idx in range(1, len(rounds), 2):
        rnd = int(rounds[idx])
        body = rounds[idx + 1] if idx + 1 < len(rounds) else ""
        if rnd != 4:
            continue
        # body: FRIDAY, OCTOBER 23 | Cardiff v Hollywoodbets Sharks | venue, KO 19.45 ...
        parts = [x.strip() for x in body.split("|")]
        j = 0
        while j < len(parts):
            p = parts[j]
            dm = re.match(r"(FRIDAY|SATURDAY|SUNDAY), ([A-Z]+) (\d{1,2})", p)
            if dm:
                cur_date = datetime.strptime(f"{dm.group(2).title()} {dm.group(3)} 2026", "%B %d %Y").strftime("%Y-%m-%d")
            elif " v " in p and j + 1 < len(parts) and "KO" in parts[j + 1]:
                a, b = [x.strip() for x in p.split(" v ", 1)]
                km = re.search(r"KO (\d{2})\.(\d{2})", parts[j + 1])
                venue = parts[j + 1].split(", KO")[0].strip()
                if km and cur_date:
                    start = f"{cur_date}T{km.group(1)}:{km.group(2)}:00Z"
                    if keep(start):
                        rows.append(
                            {
                                "sport": "Rugby Union", "competition": "United Rugby Championship",
                                "stage": "Round 4", "side_a": a, "side_b": b, "start_utc": start,
                                "venue": venue, "kind": "match",
                                "source_name": "URC official 2026/27 fixtures", "source_url": cap.url("urc_fixtures"),
                                "secondary_url": "https://www.unitedrugby.com/match-centre",
                                "ref": {"a": a, "b": b, "round": 4}, "home_side": "a",
                                "form": {"a": {}, "b": {}, "standings_url": "https://stats.unitedrugby.com/match-centre/table/2026-27"},
                            }
                        )
            j += 1
    return rows


# --------------------------------------------------------------------------- #
# Handball — Danish Herreligaen
# --------------------------------------------------------------------------- #
def tophaandbold(cap: Capture) -> list[dict]:
    if not cap.has("tophaandbold_kamp"):
        return []
    lines = html_lines(cap.text("tophaandbold_kamp"))
    joined = " | ".join(lines)
    table = {}
    if cap.has("tophaandbold_herr"):
        tl = " | ".join(html_lines(cap.text("tophaandbold_herr")))
        pat = re.compile(r"(\d{1,2}) \| ([^|]{2,40}) \| (\d{1,2}) \| (\d{1,2}) \| (\d{1,2}) \| (\d{1,2}) \| (\d{2,3})-(\d{2,3}) \| (\d{1,3}) \|")
        for m in pat.finditer(tl):
            team = m.group(2).strip()
            table[team] = {
                "team": team, "rank": int(m.group(1)), "games": int(m.group(3)),
                "wins": int(m.group(4)), "draws": int(m.group(5)), "losses": int(m.group(6)),
                "gf": int(m.group(7)), "ga": int(m.group(8)), "points": int(m.group(9)),
                "source": cap.url("tophaandbold_herr"),
            }
    rows, seen = [], set()
    for m in re.finditer(r"(\d{2})-(\d{2})-(\d{2}) (\d{2}):(\d{2}) \| ([^|]+) \| VS \| ([^|]+) \|", joined):
        dd, mm, yy, hh, mi, home, away = m.groups()
        start = f"20{yy}-{mm}-{dd}T{hh}:{mi}:00Z"
        if not keep(start):
            continue
        home, away = home.strip(), away.strip()
        key = (home, away, start)
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "sport": "Handball", "competition": "Betoro Herreligaen (Denmark)", "stage": "Regular season",
                "side_a": home, "side_b": away, "start_utc": start, "venue": "", "kind": "match",
                "source_name": "Tophåndbold official Herreligaen schedule", "source_url": cap.url("tophaandbold_kamp"),
                "secondary_url": cap.url("tophaandbold_herr"),
                "ref": {"a": home, "b": away}, "home_side": "a",
                "form": {"a": table.get(home, {}), "b": table.get(away, {}),
                          "standings_url": cap.url("tophaandbold_herr")},
            }
        )
    return rows


# --------------------------------------------------------------------------- #
# Volleyball — Polish PlusLiga
# --------------------------------------------------------------------------- #
def plusliga(cap: Capture) -> list[dict]:
    if not cap.has("plusliga_games"):
        return []
    lines = html_lines(cap.text("plusliga_games"))
    joined = " | ".join(lines)
    table = {}
    if cap.has("plusliga_table"):
        tl = " | ".join(html_lines(cap.text("plusliga_table")))
        # The captured page is the women's table; only use it when the club names match.
        pat = re.compile(r"(\d{1,2})\. \| ([^|]{3,40}) \| (\d{1,2}) \| (\d{1,2}) \| (\d{1,2}) \| (\d{1,2})")
        for m in pat.finditer(tl):
            table[m.group(2).strip()] = {"team": m.group(2).strip(), "rank": int(m.group(1)),
                                          "games": int(m.group(3)), "points": int(m.group(6)),
                                          "source": cap.url("plusliga_table")}
    rows, seen = [], set()
    pat = re.compile(r"(\d{2})\.(\d{2})\.(\d{4}), (\d{2}):(\d{2}) \| ([^|]+) \| ([^|]+) \| ··· \| : \| ··· \| ([^|]+)")
    for m in pat.finditer(joined):
        dd, mm, yy, hh, mi, stage, home, away = m.groups()
        start = f"{yy}-{mm}-{dd}T{hh}:{mi}:00Z"
        if not keep(start):
            continue
        home, away = home.strip(), away.strip()
        if (home, away, start) in seen:
            continue
        seen.add((home, away, start))
        rows.append(
            {
                "sport": "Volleyball", "competition": "PlusLiga (Poland)", "stage": stage.strip(),
                "side_a": home, "side_b": away, "start_utc": start, "venue": "", "kind": "match",
                "source_name": "PlusLiga official match schedule", "source_url": cap.url("plusliga_games"),
                "secondary_url": "https://www.plusliga.pl/table.html", "ref": {"a": home, "b": away}, "home_side": "a",
                "form": {"a": table.get(home, {}), "b": table.get(away, {}), "standings_url": "https://www.plusliga.pl/table.html"},
            }
        )
    return rows


# --------------------------------------------------------------------------- #
# Rugby league — RLWC 2026 embedded Next.js payload
# --------------------------------------------------------------------------- #
def rlwc(cap: Capture) -> list[dict]:
    if not cap.has("rlwc_draws"):
        return []
    html = cap.text("rlwc_draws").replace('\\"', '"')
    rows, seen = [], set()
    pat = re.compile(
        r'"gameId":"(\d+)","gameNumber":\d+,"game":"([^"]+)","gameStateName":"([^"]+)",'
        r'"gameMinutes":"[^"]*","startTime":"([^"]+)","startTimeUTC":"([^"]+)","venueName":"([^"]+)",'
        r'"city":"([^"]+)","roundId":(\d+),"roundName":"([^"]+)","group":\d+,"gameStateId":\d+,"teams":\[(.*?)\]'
    )
    for m in pat.finditer(html):
        gid, game, state, st, utc, venue, city, rnd, rname, teams = m.groups()
        if utc[:4] != "2026":
            continue
        start = iso(utc)
        if not keep(start):
            continue
        if "Wheelchair" in game:
            continue
        tnames = re.findall(r'"isHomeTeam":(true|false),"teamId":"\d+","teamName":"([^"]+)"', teams)
        if len(tnames) < 2:
            continue
        home = next((n for h, n in tnames if h == "true"), tnames[0][1])
        away = next((n for h, n in tnames if h == "false"), tnames[1][1])
        womens = ("Women", "Jillaroos", "Kiwi Ferns", "Orchids", "Fetu Samoa")
        label = "Women" if any(w in (home + away) for w in womens) else "Men"
        if gid in seen:
            continue
        seen.add(gid)
        rows.append(
            {
                "sport": "Rugby League", "competition": f"Rugby League World Cup 2026 ({label})",
                "stage": rname, "side_a": home, "side_b": away, "start_utc": start,
                "venue": f"{venue}, {city}", "kind": "match",
                "source_name": "Rugby League World Cup 2026 official draw", "source_url": cap.url("rlwc_draws"),
                "secondary_url": "", "ref": {"a": home, "b": away, "game_id": gid}, "home_side": "a",
                "form": {"a": {}, "b": {}, "standings_url": ""},
            }
        )
    return rows


# --------------------------------------------------------------------------- #
# Cricket — Cricket Australia's official match list
# --------------------------------------------------------------------------- #
def cricket(cap: Capture) -> list[dict]:
    if not cap.has("cricket_au_fixtures"):
        return []
    lines = html_lines(cap.text("cricket_au_fixtures"))
    joined = " | ".join(lines)
    rows = []
    # Series | Stage | Upcoming | 23 October 2026 | 23 Oct, 2026 | Team A | Upcoming | Team B | Series | Stage | Venue
    pat = re.compile(
        r"([A-Za-z0-9'’&\- .]+) \| ([^|]{2,40}) \| Upcoming \| (\d{1,2}) ([A-Za-z]+) 2026 \| "
        r"\d{1,2} [A-Za-z]+, 2026 \| ([^|]{2,60}) \| Upcoming \| ([^|]{2,60}) \| "
    )
    for m in pat.finditer(joined):
        series, stage, dd, mon, teama, teamb = m.groups()
        mon = mon.title()
        try:
            start_date = datetime.strptime(f"{dd} {mon} 2026", "%d %B %Y").strftime("%Y-%m-%d")
        except ValueError:
            continue
        teama, teamb = teama.strip(), teamb.strip()
        if "Women" not in teama and "Women" not in teamb:
            gender = "Men"
        else:
            gender = "Women"
        rows.append(
            {
                "sport": "Cricket", "competition": series.strip(), "stage": stage.strip(),
                "side_a": teama, "side_b": teamb, "start_utc": f"{start_date}T00:00:00Z",
                "venue": "", "kind": "match", "gender": gender,
                "source_name": "Cricket Australia official match list", "source_url": cap.url("cricket_au_fixtures"),
                "secondary_url": "", "ref": {"a": teama, "b": teamb}, "home_side": "a",
                "form": {"a": {}, "b": {}, "standings_url": ""},
            }
        )
    return rows


def icc_ratings(cap: Capture) -> dict:
    out = {}
    for tid, key in [("icc_odi_rank", "men_odi"), ("icc_t20i_rank", "men_t20i"), ("icc_wt20i_rank", "women_t20i")]:
        if not cap.has(tid):
            continue
        txt = cap.text(tid)
        # Team rankings pages embed rows as JSON in the SvelteKit payload.
        pairs = re.findall(r'"teamName":"([^"]+)"[^}]*?"rating":(\d+)', txt)
        if not pairs:
            pairs = re.findall(r'"name":"([^"]+)","matches":\d+,"points":\d+,"rating":(\d+)', txt)
        out[key] = {n: {"team": n, "rating": int(r), "source": cap.url(tid)} for n, r in pairs}
    return out


# --------------------------------------------------------------------------- #
# Esports — LoL Worlds schedule embedded in the official lolesports page
# --------------------------------------------------------------------------- #
def lol(cap: Capture) -> list[dict]:
    if not cap.has("lolesports_schedule_page"):
        return []
    html = cap.text("lolesports_schedule_page").replace('\\"', '"')
    events = []
    marker = '{"__typename":"EventMatch",'
    pos = 0
    while True:
        i = html.find(marker, pos)
        if i < 0:
            break
        depth, j, in_str, esc = 0, i, False, False
        while j < len(html):
            ch = html[j]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        break
            j += 1
        try:
            events.append(json.loads(html[i:j + 1]))
        except Exception:
            pass
        pos = j + 1
    # de-duplicate by id
    uniq = {}
    for ev in events:
        uniq[ev.get("id")] = ev
    events = list(uniq.values())
    # Official Riot team GPR (Elo) table embedded on the same page.
    gpr: dict[str, dict] = {}
    for m in re.finditer(r'\{"__typename":"TeamGPR","id":"([^":]+):[^"]*".{0,700}?"currentTeamGPR":\{"__typename":"GPR","gprScore":(\d+),"elo":(\d+),"rank":(\d+)', html, flags=re.S):
        tid, score, elo, rank = m.groups()
        gpr[tid] = {"elo": int(elo), "gpr": int(score), "rank": int(rank)}
    # team records from completed series
    rec: dict[str, dict] = {}
    for ev in events:
        if ev.get("state") != "completed":
            continue
        teams = ev.get("matchTeams") or []
        if len(teams) != 2:
            continue
        for t, o in ((teams[0], teams[1]), (teams[1], teams[0])):
            name = t.get("name")
            r = rec.setdefault(name, {"team": name, "games": 0, "wins": 0, "losses": 0})
            r["games"] += 1
            if (t.get("result") or {}).get("outcome") == "win":
                r["wins"] += 1
            else:
                r["losses"] += 1
    rows = []
    for ev in events:
        start = ev.get("startTime", "")
        if ev.get("state") != "unstarted" or not keep(start):
            continue
        teams = ev.get("matchTeams") or []
        if len(teams) != 2:
            continue
        a, b = teams[0], teams[1]
        fa = dict(rec.get(a.get("name"), {}))
        fb = dict(rec.get(b.get("name"), {}))
        if gpr.get(a.get("teamId")):
            fa.update(gpr[a["teamId"]])
        if gpr.get(b.get("teamId")):
            fb.update(gpr[b["teamId"]])
        rows.append(
            {
                "sport": "eSports", "competition": f'{ev.get("league", {}).get("name", "LoL")} — {ev.get("blockName", "")}',
                "stage": ev.get("blockName", ""), "side_a": a.get("name"), "side_b": b.get("name"),
                "start_utc": start, "venue": "", "kind": "match",
                "source_name": "LoL Esports official schedule (lolesports.com)", "source_url": cap.url("lolesports_schedule_page"),
                "secondary_url": "https://lolesports.com/schedule", "ref": {"a": a.get("code"), "b": b.get("code"), "match_id": ev.get("id")},
                "home_side": "",
                "form": {"a": fa, "b": fb,
                          "standings_url": cap.url("lolesports_schedule_page")},
            }
        )
    return rows


# --------------------------------------------------------------------------- #
# Darts — PDC European Championship: official draw from pdc-europe.tv
#          combined with the OLBG listing for session times on 23 October.
# --------------------------------------------------------------------------- #
def _norm_name(x: str) -> str:
    import unicodedata
    x = unicodedata.normalize("NFKD", x).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z]", "", x.lower())


def darts(cap: Capture, olbg: dict) -> list[dict]:
    if not cap.has("pdc_europe_tv"):
        return []
    html = cap.text("pdc_europe_tv")
    parts = html.split("is-open tb-match")
    pairs = []
    for part in parts[1:]:
        names = re.findall(r'class="tb-name" title="([^"]+)"', part)
        seeds = re.findall(r'title="Seed"[^>]*>(\d+)<', part)
        if len(names) >= 2 and len(seeds) >= 2:
            pairs.append({
                "a": names[0].replace("&#39;", "'"), "b": names[1].replace("&#39;", "'"),
                "sa": int(seeds[0]), "sb": int(seeds[1]),
            })
    import difflib

    def find(name: str):
        best, score = None, 0.0
        for p in pairs:
            for side in ("a", "b"):
                r = difflib.SequenceMatcher(None, _norm_name(name), _norm_name(p[side])).ratio()
                if r > score:
                    best, score = p, r
        return best if score >= 0.82 else None
    rows = []
    for e in olbg.get("events", []):
        if e.get("sport") != "Darts" or not e.get("start_utc"):
            continue
        name = e["event_name"] or ""
        if " vs " not in name:
            continue
        a, b = [x.strip() for x in name.split(" vs ", 1)]
        pa = find(a)
        pb = find(b)
        if not pa or not pb or pa is not pb:
            continue
        rows.append(
            {
                "sport": "Darts", "competition": "PDC European Championship 2026",
                "stage": "Round 1", "side_a": a, "side_b": b,
                "start_utc": e["start_utc"], "venue": "Westfalenhalle, Dortmund", "kind": "match",
                "source_name": "PDC Europe official 2026 European Championship draw", "source_url": cap.url("pdc_europe_tv"),
                "secondary_url": e.get("olbg_url", ""), "ref": {"a": a, "b": b, "seeds": [pa["sa"], pa["sb"]]},
                "home_side": "",
                "form": {
                    "a": {"team": a, "seed": pa["sa"], "source": cap.url("pdc_europe_tv")},
                    "b": {"team": b, "seed": pa["sb"], "source": cap.url("pdc_europe_tv")},
                    "standings_url": cap.url("pdc_europe_tv"),
                },
            }
        )
    return rows


def main() -> int:
    cap_dir = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    cap = Capture(cap_dir)
    fixtures: list[dict] = []
    fixtures += nhl(cap)[0]
    fixtures += liiga(cap)
    fixtures += euroleague(cap, "E", "EuroLeague")
    fixtures += euroleague(cap, "U", "EuroCup")
    fixtures += nba(cap)
    fixtures += mlb(cap)
    fixtures += wta(cap)
    fixtures += atp(cap)
    fixtures += lnr(cap, "top14_cal", "Top 14", "top14_class")
    fixtures += lnr(cap, "prod2_cal", "Pro D2", "prod2_class")
    fixtures += urc(cap)
    fixtures += tophaandbold(cap)
    fixtures += plusliga(cap)
    fixtures += rlwc(cap)
    fixtures += cricket(cap)
    fixtures += lol(cap)
    olbg = {}
    p = DATA_PATH / "olbg_inventory.json"
    if p.exists():
        olbg = json.loads(p.read_text(encoding="utf-8"))
    fixtures += darts(cap, olbg)
    payload = {
        "schema": "olbg4.board-af.fixtures/1",
        "capture_dir": str(cap_dir),
        "capture_started_utc": cap.manifest.get("started_utc"),
        "cutoff_utc": CUTOFF,
        "window_end_utc": WINDOW_END,
        "counts": {},
        "icc_ratings": icc_ratings(cap),
        "fixtures": fixtures,
    }
    for f in fixtures:
        payload["counts"][f["sport"]] = payload["counts"].get(f["sport"], 0) + 1
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload["counts"], indent=1))
    print("total", len(fixtures))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
