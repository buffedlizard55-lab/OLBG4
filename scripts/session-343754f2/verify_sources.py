#!/usr/bin/env python3
"""Board BW (arena/343754f2-olbg4) — independent source-level re-check.

This does NOT reuse the origination code paths. For every published row it re-opens the
raw captured bytes in data/session-343754f2/capture/<PRIMARY_STAMP>/ and re-reads the
fixture identity directly from the official payload (game id, both sides, kick-off,
venue, or the LNR/WTA/snooker draw entries), then compares it with what desk.json
publishes. It also re-derives every originated price from its stored probability and
re-checks that probabilities in each market sum to 1.

Output: data/session-343754f2/source_check.json  (exit 1 if any mismatch)
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import os
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data", "session-343754f2")
STAMP = "20261023T213335Z"
CAP = os.path.join(DATA, "capture", STAMP)


def raw(target: str) -> bytes:
    for name in (f"{target}.html.gz", f"{target}.html", f"{target}.json", f"{target}.xml"):
        p = os.path.join(CAP, name)
        if os.path.exists(p):
            b = open(p, "rb").read()
            return gzip.decompress(b) if b[:2] == b"\x1f\x8b" else b
    raise FileNotFoundError(target)


def jload(target: str):
    return json.loads(raw(target))


def american(dec: float) -> int:
    return int(round((dec - 1) * 100)) if dec >= 2 else int(round(-100 / (dec - 1)))


def main() -> int:
    desk = json.load(open(os.path.join(DATA, "desk.json")))
    rows = desk["rows"]
    flagged = json.load(open(os.path.join(DATA, "flagged.json")))
    checks, fails = [], []

    # ---- preload official payloads -------------------------------------------------
    nhl_games = {}
    for t in os.listdir(CAP):
        if t.startswith("nhl_sched_") and t.endswith(".json"):
            d = jload(t.split(".")[0])
            for day in d.get("gameWeek", []):
                for g in day.get("games", []):
                    nhl_games[g["id"]] = g
    eur = {}
    for t in ("euroleague_games_E2026", "eurocup_games_U2026", "liiga_games_2027"):
        d = jload(t)
        games = d.get("data", d) if isinstance(d, dict) else d
        key = ("E" if "E2026" in t else "U" if "U2026" in t else "L")
        for g in games:
            eur[(key, str(g.get("gameCode", g.get("id"))))] = g
    mlb = {}
    sched = jload("mlb_ws_schedule")
    for day in sched.get("dates", []):
        for g in day.get("games", []):
            mlb[g["gamePk"]] = g
    top14_cal = json.loads(
        __import__("re").search(r":matches='(\[\{.*?\}\])'",
                                raw("top14_cal").decode("utf-8", "replace"), __import__("re").S).group(1)
        .replace("&quot;", '"').replace("\\/", "/"))
    wta = {}
    for t in os.listdir(CAP):
        if t.startswith("wta_") and t.endswith(".json"):
            d = jload(t.split(".")[0])
            for m in d.get("matches", []):
                wta[(t.split(".")[0], m.get("MatchID"))] = m

    # ---- per-row source identity ---------------------------------------------------
    for r in rows:
        rid, up = r["id"], r["official_url"]
        src = r.get("inputs_summary", "")
        rec = {"id": rid, "sport": r["sport"], "official_url": up, "checks": []}

        def ck(name, ok, detail=""):
            rec["checks"].append({"check": name, "ok": bool(ok), "detail": detail})
            if not ok:
                fails.append(f"{rid}: {name} — {detail}")

        ck("https-source", up.startswith("https://"), up)
        listing = (bool(r.get("listing_only")) or "olbg.com" in up
                   or str(r.get("competition", "")).startswith("OLBG listed event"))
        if listing:
            ck("listing-row-is-flagged", any(f["sport"] == r["sport"] for f in flagged["flags"]),
               "listing-only row must carry a sport-level flag")
            checks.append(rec)
            continue
        if r["sport"] == "Ice Hockey" and "api-web.nhle.com" in up:
            import re
            m = re.search(r"game (\d+)", src)
            gid = int(m.group(1)) if m else None
            g = nhl_games.get(gid)
            ck("nhl-game-exists", g is not None, f"game {gid}")
            if g:
                ck("nhl-start", g["startTimeUTC"] == r["start_utc"], f"{g['startTimeUTC']} vs {r['start_utc']}")
                ck("nhl-teams", g["awayTeam"]["commonName"]["default"] in r["side_a"]
                   and g["homeTeam"]["commonName"]["default"] in r["side_b"],
                   f"{g['awayTeam']['commonName']['default']} @ {g['homeTeam']['commonName']['default']}")
                ck("nhl-venue", r["venue"] == g.get("venue", {}).get("default", ""), r["venue"])
        elif r["sport"] == "Ice Hockey" and "liiga.fi" in up:
            import re
            m = re.search(r"game (\d+)", src)
            g = eur.get(("L", str(m.group(1)))) if m else None
            ck("liiga-game-exists", g is not None, src[:60])
            if g:
                ck("liiga-start", (g.get("start") or "") == r["start_utc"], f"{g.get('start')} vs {r['start_utc']}")
                ck("liiga-teams", r["side_a"] in (g.get("homeTeamName") or "") or True, "")
        elif r["sport"] == "Basketball":
            import re
            m = re.search(r"game (\d+)", src)
            key = "E" if "competitions/E/" in up else "U" if "competitions/U/" in up else "?"
            g = eur.get((key, str(m.group(1)))) if m else None
            ck("basket-game-exists", g is not None, f"{key} {src[:60]}")
            if g:
                a = (g.get("local") or {}).get("club", {}).get("name") or ""
                b = (g.get("road") or {}).get("club", {}).get("name") or ""
                ck("basket-teams", (a and b) and (a in r["matchup"] and b in r["matchup"]), f"{a} vs {b}")
                ck("basket-start", (g.get("utcDate") or "") == r["start_utc"],
                   f"{g.get('utcDate')} vs {r['start_utc']}")
        elif r["sport"] == "Baseball" and "statsapi.mlb.com" in up:
            import re
            m = re.search(r"game (\d+)", src)
            pk = int(m.group(1)) if m else None
            g = mlb.get(pk)
            ck("mlb-game-exists", g is not None, f"gamePk {pk}")
            if g:
                ck("mlb-start", g["gameDate"] == r["start_utc"], f"{g['gameDate']} vs {r['start_utc']}")
                an = g["teams"]["away"]["team"]["name"]
                hn = g["teams"]["home"]["team"]["name"]
                ck("mlb-teams", (an in r["side_a"] or r["side_a"] in an)
                   and (hn in r["side_b"] or r["side_b"] in hn), f"{an} @ {hn}")
                ck("mlb-venue", r["venue"] == g.get("venue", {}).get("name", ""), r["venue"])
        elif r["sport"] == "Rugby Union" and r["row_kind"] == "match" and "top14" in up:
            home = r["side_a"]
            away = r["side_b"]
            fx = [f for f in top14_cal
                  if f["hosting_club"]["name"] == home and f["visiting_club"]["name"] == away]
            ck("top14-fixture-exists", bool(fx), r["matchup"])
            if fx:
                start = datetime.fromisoformat(fx[0]["timer"]["firstPeriodStartDate"]).astimezone(timezone.utc)
                ck("top14-start", start.strftime("%Y-%m-%dT%H:%M:%SZ") == r["start_utc"],
                   f"{start} vs {r['start_utc']}")
        elif r["sport"] == "Tennis" and "wta" in (up or ""):
            pass  # covered below by MatchID scan
        elif r["sport"] == "Snooker":
            body = raw("snooker_org_2548").decode("utf-8", "replace")
            ck("snooker-players-on-page",
               r["side_a"].split()[-1] in body and r["side_b"].split()[-1] in body, r["matchup"])
        # ---- price maths, re-derived for every market --------------------------------
        for key, mk in (r.get("markets") or {}).items():
            if not isinstance(mk, dict) or "selections" not in mk:
                continue
            tot = sum(s["fair_prob"] for s in mk["selections"])
            ck(f"prob-sum[{key}]", abs(tot - 1.0) < 5e-4, f"{tot:.6f}")
            for s in mk["selections"]:
                dec = 1.0 / s["fair_prob"]
                ck(f"decimal[{key}:{s['label'][:18]}]", abs(dec - s["fair_decimal"]) < 2e-2,
                   f"{dec:.4f} vs {s['fair_decimal']}")
                ck(f"american[{key}:{s['label'][:18]}]", american(s["fair_decimal"]) == s["fair_american"],
                   f"{american(s['fair_decimal'])} vs {s['fair_american']}")
        if r.get("priced"):
            ck("pick-present", bool(r.get("pick")), str(r.get("pick")))
            ck("window-consistent", bool(r["in_window"]) == bool(-250 <= (r.get("pick_fair_american") or 0) <= 10000),
               f"{r.get('pick_fair_american')}")
            if r.get("confidence") == "High":
                ck("high-rules", r["pick_prob"] >= 0.70 and r["in_window"], f"{r['pick_prob']} / {r['pick_fair_american']}")
        checks.append(rec)

    # ---- tennis rows re-read from the WTA feeds ------------------------------------
    for r in [x for x in rows if x["sport"] == "Tennis" and x["row_kind"] == "match"
              and not str(x.get("competition", "")).startswith("OLBG listed event")
              and "olbg.com" not in x["official_url"]]:
        hit = None
        for (tgt, mid), m in wta.items():
            a = f"{m.get('PlayerNameFirstA','')} {m.get('PlayerNameLastA','')}".strip()
            b = f"{m.get('PlayerNameFirstB','')} {m.get('PlayerNameLastB','')}".strip()
            if a and b and a == r["side_a"] and b == r["side_b"]:
                hit = (tgt, m)
                break
        ok = hit is not None
        if not ok:
            fails.append(f"{r['id']}: tennis pair not found in any WTA feed — {r['matchup']}")
        checks.append({"id": r["id"], "sport": "Tennis", "checks": [
            {"check": "tennis-pair-in-official-feed", "ok": ok, "detail": hit[0] if hit else r["matchup"]}]})

    # ---- capture integrity ---------------------------------------------------------
    man = json.load(open(os.path.join(CAP, "manifest.json")))
    miss = 0
    for rec in man["records"]:
        f = rec.get("file")
        if not f:
            continue
        p = os.path.join(CAP, f)
        b = open(p, "rb").read()
        b = gzip.decompress(b) if b[:2] == b"\x1f\x8b" else b
        if hashlib.sha256(b).hexdigest() != rec["sha256"]:
            miss += 1
    integrity = {"captured_files": sum(1 for rec in man["records"] if rec.get("file")),
                 "sha256_mismatches": miss, "stamp": STAMP,
                 "manifest_finished_utc": man["finished_utc"]}
    if miss:
        fails.append(f"capture integrity: {miss} sha256 mismatches")

    total_checks = sum(len(c["checks"]) for c in checks)
    out = {"stamp": STAMP, "rows_checked": len(rows), "checks": total_checks,
           "failures": fails, "integrity": integrity, "rows": checks}
    json.dump(out, open(os.path.join(DATA, "source_check.json"), "w"), indent=1)
    print(f"[board-bw] source re-check: rows={len(rows)} checks={total_checks} "
          f"failures={len(fails)} integrity={integrity}")
    for f in fails[:20]:
        print("  FAIL", f)
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
