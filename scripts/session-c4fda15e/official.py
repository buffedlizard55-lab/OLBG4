#!/usr/bin/env python3
"""Board W - normalise official captures into data/session-c4fda15e/official.json.

Inputs are only bytes committed under data/session-c4fda15e/capture/<stamp>/ (each with
URL + SHA-256 in that capture's manifest.json). Every record written here carries the
official URL and the capture file/sha it came from. Values the source does not print
are left out (never estimated).
"""
from __future__ import annotations

import gzip
import html as H
import io
import json
import os
import re
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CAP = os.path.join(ROOT, "data", "session-c4fda15e", "capture")
OUT = os.path.join(ROOT, "data", "session-c4fda15e", "official.json")


def manifests():
    idx = {}
    for stamp in sorted(os.listdir(CAP)):
        mp = os.path.join(CAP, stamp, "manifest.json")
        if not os.path.exists(mp):
            continue
        for it in json.load(open(mp, encoding="utf-8"))["items"]:
            if it.get("status") == 200 and it.get("file"):
                it = dict(it, capture=stamp, path=os.path.join(CAP, stamp, it["file"]))
                idx[it["id"]] = it  # later captures override earlier ones
    return idx


IDX = manifests()


def raw(cid):
    it = IDX[cid]
    return gzip.open(it["path"]).read()


def prov(cid):
    it = IDX[cid]
    return {"url": it["url"], "capture": f"data/session-c4fda15e/capture/{it['capture']}/{it['file']}",
            "sha256": it["sha256"], "fetched_utc": it["fetched_utc"]}


def text_of(cid):
    h = raw(cid).decode("utf-8", "replace")
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", h, flags=re.S)
    t = H.unescape(re.sub(r"<[^>]+>", "|", t))
    return re.sub(r"\s*\|\s*(\|\s*)*", "|", t)


# ----------------------------------------------------------------------------- tennis
def atp_rankings():
    from pypdf import PdfReader
    r = PdfReader(io.BytesIO(raw("atp_rankings_pdf")))
    out = {}
    rx = re.compile(r"^\s*(\d+)\s+(.+?)\s+(?:\(([A-Z]{3})\)\s+)?(\d+)\s+(\d+)\s")
    for page in r.pages:
        for line in (page.extract_text() or "").splitlines():
            m = rx.match(line)
            if m and "," in m.group(2):
                last, first = [x.strip() for x in m.group(2).split(",", 1)]
                out[f"{first} {last}"] = {"rank": int(m.group(1)), "points": int(m.group(4)), "nat": m.group(3) or ""}
    return {"as_of": "2026-10-19", "players": out, "source": prov("atp_rankings_pdf"),
            "source_name": "ATP Singles Rankings (numerical), ProTennisLive official posting"}


def wta_rankings():
    out, srcs = {}, []
    for cid in ("wta_rankings_api", "wta_rankings_api_p1", "wta_rankings_api_p2", "wta_rankings_api_p3"):
        if cid not in IDX:
            continue
        srcs.append(prov(cid))
        for x in json.loads(raw(cid)):
            p = x["player"]
            out[p["fullName"]] = {"rank": x["ranking"], "points": x["points"], "nat": p.get("countryCode", ""), "ranked_at": x.get("rankedAt")}
    return {"as_of": "2026-10-19", "players": out, "sources": srcs, "source_name": "WTA official rankings API (api.wtatennis.com)"}


def wta_matches(cid, tid, name):
    d = json.loads(raw(cid))
    rows = []
    for x in d["matches"]:
        if x["DrawMatchType"] != "S" or x["DrawLevelType"] != "M":
            continue
        rows.append({"match_id": x["MatchID"], "round_id": x["RoundID"], "state": x["MatchState"], "time": x["MatchTimeStamp"],
                     "a": f"{x['PlayerNameFirstA']} {x['PlayerNameLastA']}", "b": f"{x['PlayerNameFirstB']} {x['PlayerNameLastB']}",
                     "seed_a": x.get("SeedA") or "", "seed_b": x.get("SeedB") or "", "result": x.get("ResultString") or "",
                     "winner": x.get("Winner")})
    return {"tournament_id": tid, "name": name, "matches": rows, "source": prov(cid),
            "page_url": f"https://www.wtatennis.com/tournaments/{tid}/{name.lower().split()[0]}/2026/scores"}


# ----------------------------------------------------------------------------- darts
def pdc_participants():
    out, srcs = {}, []
    for cid in ("pdc_participants", "pdc_participants_p2"):
        if cid not in IDX:
            continue
        srcs.append(prov(cid))
        for x in json.loads(raw(cid))["data"]:
            a = x["attributes"]
            nm = f"{a['firstName']} {a['lastName']}".strip()
            out[nm] = {"oom_rank": a.get("ranking"), "prize_money_gbp": a.get("prizeMoney"), "country": a.get("countryCode")}
    return {"players": out, "sources": srcs, "source_name": "PDC participants service used by pdc.tv (ranking = PDC Order of Merit position; prizeMoney field is undefined on the feed and is NOT used)"}


# ----------------------------------------------------------------------------- euroleague
def euroleague(cid):
    d = json.loads(raw(cid))["data"]
    games = []
    for g in d:
        games.append({"code": g["gameCode"], "round": g["round"], "utc": g["utcDate"], "played": g["played"],
                      "phase": g["phaseType"]["code"], "home": g["local"]["club"]["name"], "away": g["road"]["club"]["name"],
                      "hs": g["local"]["score"], "as": g["road"]["score"],
                      "venue": (g.get("venue") or {}).get("name") if isinstance(g.get("venue"), dict) else None})
    return {"games": games, "source": prov(cid)}


# ----------------------------------------------------------------------------- LNR rugby
def lnr_table(cid):
    t = text_of(cid)
    i = t.find("Prochain match")
    seg = t[i:]
    rows = {}
    rx = re.compile(r"\|([^|]+)\|(\d+)\|(\d+)\|(\d+)\|(\d+)\|(\d+)\|(\d+)\|(\d+)\|(\d+)\|([+-]?\d+)\|((?:[VDN]\|){1,5})")
    for m in rx.finditer(seg):
        name = m.group(1).strip()
        rows[name] = {"pts": int(m.group(2)), "played": int(m.group(3)), "w": int(m.group(4)), "d": int(m.group(5)), "l": int(m.group(6)),
                      "bonus": int(m.group(7)), "pf": int(m.group(8)), "pa": int(m.group(9)), "diff": int(m.group(10)),
                      "form_last5_as_printed": m.group(11).strip("|").replace("|", "")}
    for pos, k in enumerate(rows, 1):
        rows[k]["position"] = pos
    return {"table": rows, "source": prov(cid)}


FR_MONTHS = {"octobre": 10, "novembre": 11}


def paris_to_utc(day: int, month: int, hhmm: str) -> str:
    h, mi = [int(x) for x in hhmm.split("h")]
    local = datetime(2026, month, day, h, mi)
    # CEST (UTC+2) until 25 Oct 2026 03:00 local, CET (UTC+1) afterwards
    off = 2 if local < datetime(2026, 10, 25, 3, 0) else 1
    return (local - timedelta(hours=off)).replace(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def lnr_calendar(cid):
    t = text_of(cid)
    m = re.search(r"Journée (\d+)", t)
    j = int(m.group(1)) if m else None
    seg = t[t.find("Journée"):]
    seg = seg[:seg.find("Les avantages")] if "Les avantages" in seg else seg
    fixtures, cur = [], None
    toks = [x.strip() for x in seg.split("|") if x.strip()]
    k = 0
    while k < len(toks):
        tok = toks[k]
        dm = re.match(r"(lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche) (\d+) (\w+)", tok)
        if dm:
            cur = (int(dm.group(2)), FR_MONTHS.get(dm.group(3), 0))
            k += 1
            continue
        if cur and k + 6 < len(toks) and re.match(r"^\d+$", toks[k + 1]) and toks[k + 2] == "e" and re.match(r"^\d+h\d+$", toks[k + 3]):
            home, hpos, hhmm, away, apos = tok, int(toks[k + 1]), toks[k + 3], toks[k + 4], int(toks[k + 5])
            fixtures.append({"date": f"2026-{cur[1]:02d}-{cur[0]:02d}", "local_time": hhmm, "utc": paris_to_utc(cur[0], cur[1], hhmm),
                             "home": home, "home_pos": hpos, "away": away, "away_pos": apos})
            k += 7
            continue
        k += 1
    return {"round": j, "fixtures": fixtures, "source": prov(cid)}


# ----------------------------------------------------------------------------- MLB / Liiga
def mlb():
    st = json.loads(raw("mlb_standings_2026"))
    teams = {}
    for rec in st["records"]:
        for t in rec["teamRecords"]:
            sp = {r["type"]: f"{r['wins']}-{r['losses']}" for r in t["records"].get("splitRecords", [])}
            teams[t["team"]["name"]] = {"w": t["wins"], "l": t["losses"], "rs": t.get("runsScored"), "ra": t.get("runsAllowed"),
                                        "rd": t.get("runDifferential"), "home": sp.get("home"), "away": sp.get("away"), "last10": sp.get("lastTen")}
    sch = json.loads(raw("mlb_postseason_schedule"))
    games = []
    for date in sch["dates"]:
        for g in date["games"]:
            if g.get("gameType") not in ("D", "L", "W", "F"):
                continue
            a, h = g["teams"]["away"], g["teams"]["home"]
            games.append({"pk": g["gamePk"], "type": g["gameType"], "utc": g["gameDate"], "state": g["status"]["detailedState"],
                          "away": a["team"]["name"], "home": h["team"]["name"], "as": a.get("score"), "hs": h.get("score"),
                          "series": g.get("seriesDescription"), "game_no": g.get("seriesGameNumber"),
                          "away_pp": (a.get("probablePitcher") or {}).get("fullName"), "home_pp": (h.get("probablePitcher") or {}).get("fullName"),
                          "venue": (g.get("venue") or {}).get("name")})
    return {"standings": teams, "standings_source": prov("mlb_standings_2026"), "postseason": games, "schedule_source": prov("mlb_postseason_schedule")}


def liiga():
    s = json.loads(raw("liiga_standings_2027"))
    table = {r["teamName"]: {k: r.get(k) for k in ("ranking", "games", "wins", "overtimeWins", "losses", "overtimeLosses", "ties", "goals", "goalsAgainst", "points")}
             for r in s["season"]}
    g = json.loads(raw("liiga_games_2027"))
    games = [{"id": x["id"], "utc": x["start"], "home": x["homeTeam"]["teamName"], "away": x["awayTeam"]["teamName"],
              "hg": x["homeTeam"].get("goals"), "ag": x["awayTeam"].get("goals"), "ended": x.get("ended")} for x in g]
    return {"table": table, "table_source": prov("liiga_standings_2027"), "games": games, "games_source": prov("liiga_games_2027")}


def main():
    out = {
        "generated_from_captures": sorted({v["capture"] for v in IDX.values()}),
        "atp_rankings": atp_rankings(),
        "wta_rankings": wta_rankings(),
        "wta_osaka": wta_matches("wta_405_matches_r2" if "wta_405_matches_r2" in IDX else "wta_405_matches", 405, "Osaka"),
        "wta_ningbo": wta_matches("wta_2092_matches", 2092, "Ningbo"),
        "pdc": pdc_participants(),
        "euroleague_2026": euroleague("euroleague_games_E2026"),
        "euroleague_2025": euroleague("euroleague_games_E2025"),
        "prod2_table": lnr_table("prod2_table"),
        "prod2_calendar": lnr_calendar("prod2_calendar"),
        "top14_table": lnr_table("top14_table"),
        "top14_calendar": lnr_calendar("top14_calendar"),
        "mlb": mlb(),
        "liiga": liiga(),
    }
    json.dump(out, open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("atp", len(out["atp_rankings"]["players"]), "wta", len(out["wta_rankings"]["players"]), "pdc", len(out["pdc"]["players"]),
          "el26", len(out["euroleague_2026"]["games"]), "el25", len(out["euroleague_2025"]["games"]),
          "prod2", len(out["prod2_table"]["table"]), len(out["prod2_calendar"]["fixtures"]),
          "top14", len(out["top14_table"]["table"]), len(out["top14_calendar"]["fixtures"]))


if __name__ == "__main__":
    main()
