#!/usr/bin/env python3
"""Board AF line-by-line review of the shared canonical data plus the Flagged list.

Two outputs:
  data/session-2d25cf78/review.json   findings about data/master.json and peer desks
  data/session-2d25cf78/flagged.json  items on our own desk that need a human eye

Nothing here is edited: master.json and every peer file are read-only for Board AF.
"""
from __future__ import annotations

import gzip
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data/session-2d25cf78"
CUTOFF_DATE = "2026-10-22"
# Exact sport names excluded by the brief. Gaelic Football is deliberately NOT here: the brief
# excludes "football" (association football) and "american football" only.
EXCLUDED_EXACT = {"soccer", "football", "american football", "boxing", "boxing (incl. ufc & mma)",
                  "ufc", "mma", "hurling", "horse racing", "cycling", "specials"}


def load(p: Path, default=None):
    try:
        return json.loads(p.read_text())
    except Exception:  # noqa: BLE001
        return default


def norm(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", (s or "")).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9 ]", "", s)
    for junk in ("the ", " fc", " cf", " bc"):
        s = s.replace(junk, " ")
    return re.sub(r"\s+", " ", s).strip()


STOP = {"the", "fc", "cf", "bc", "hc", "club", "basketball", "rugby", "union", "league", "nhl", "nba"}


def tokens(s: str) -> set[str]:
    return {t for t in norm(s).split() if len(t) > 2 and t not in STOP}


def name_match(a: str, b: str) -> bool:
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return False
    return len(ta & tb) >= max(1, min(len(ta), len(tb)) - 1) and bool(ta & tb)


def review_master() -> tuple[list[dict], dict]:
    master = load(ROOT / "data/master.json", {})
    rows = master.get("rows", [])
    findings = []
    stats = Counter()

    def add(cat: str, severity: str, row: dict | None, detail: str, url: str = ""):
        stats[cat] += 1
        findings.append({
            "category": cat, "severity": severity,
            "row": {k: (row or {}).get(k) for k in ("build", "sport", "competition", "date", "home", "away")},
            "detail": detail, "source_url": url or (row or {}).get("source_url", ""),
            "dataset": "data/master.json",
        })

    seen = {}
    for r in rows:
        d = r.get("date") or ""
        sport = (r.get("sport") or "").lower()
        home, away = r.get("home") or "", r.get("away") or ""
        if d and d < CUTOFF_DATE:
            add("stale-date", "warning", r, f"Fixture dated {d}, before the {CUTOFF_DATE} review cut-off.")
        if not r.get("source_url"):
            add("missing-source", "error", r, "No official source_url recorded for this row.")
        pick = (r.get("pick") or "").strip()
        if not pick or pick.lower().startswith("no pick"):
            add("no-pick", "info", r, "Row carries no selection.")
        odds = ((r.get("win") or {}).get("odds") or {})
        if odds and not r.get("build_verified"):
            add("priced-unverified", "warning", r,
                "Row publishes a price while build_verified is false.")
        if sport in EXCLUDED_EXACT:
            add("excluded-sport", "error", r, f"Row is in an excluded sport ({r.get('sport')}).")
        if norm(home) in ("no fixture", "") or norm(away) in ("no fixture", ""):
            add("placeholder-row", "warning", r, "Row is an off-season placeholder, not a fixture.")
        if (r.get("confidence") or "") == "High" and not (r.get("prediction") or "").strip():
            add("high-without-prediction", "error", r, "High-confidence row has no written prediction.")
        key = (norm(sport), d, norm(home), norm(away))
        if home and away and key in seen:
            add("duplicate-fixture", "warning", r, f"Duplicate of row {seen[key]} ({home} vs {away} on {d}).")
        else:
            seen[key] = f"{r.get('build')}/{d}"
    return findings, dict(stats)


def official_sets() -> tuple[set, set, set]:
    """NHL / MLB / EuroLeague fixture keys read from the committed official capture."""
    cap = sorted((ROOT / "data/session-2d25cf78/capture").glob("*"))[-1]
    man = json.loads((cap / "manifest.json").read_text())
    ids = {f["id"]: f for f in man["files"]}

    def data(tid):
        return gzip.open(cap / ids[tid]["file"], "rb").read()

    nhl = set()
    for tid in ids:
        if tid.startswith("nhl_sched_"):
            d = json.loads(data(tid))
            for wk in d.get("gameWeek", []):
                for g in wk.get("games", []):
                    nhl.add((norm(g["homeTeam"]["placeName"]["default"]), norm(g["awayTeam"]["placeName"]["default"])))
    mlb = set()
    sched = json.loads(data("mlb_sched_2026_10_22_11_05"))
    for day in sched.get("dates", []):
        for g in day.get("games", []):
            mlb.add((norm(g["teams"]["home"]["team"]["name"]), norm(g["teams"]["away"]["team"]["name"])))
    el = set()
    for g in json.loads(data("euroleague_games_E2026"))["data"]:
        el.add((norm(g["local"]["club"]["name"]), norm(g["road"]["club"]["name"])))
    return nhl, mlb, el


def cross_check(findings: list[dict]) -> list[dict]:
    """Compare master.json NHL/MLB/EuroLeague rows with the committed official capture."""
    nhl, mlb, el = official_sets()
    master = load(ROOT / "data/master.json", {})
    checked = 0
    skipped = 0
    out = []
    for r in master.get("rows", []):
        sport = (r.get("sport") or "").lower()
        h, a = norm(r.get("home")), norm(r.get("away"))
        d = r.get("date") or ""
        if not h or not a:
            continue
        if not ("2026-10-22" <= d <= "2026-10-31"):
            skipped += 1
            continue
        comp = (r.get("competition") or "").lower()
        if sport == "ice hockey":
            if "nhl" not in comp:
                skipped += 1
                continue
            checked += 1
            if not any(name_match(h, x[0]) and name_match(a, x[1]) for x in nhl):
                out.append({
                    "category": "no-official-fixture", "severity": "error",
                    "row": {k: r.get(k) for k in ("sport", "date", "home", "away")},
                    "detail": "This NHL pairing does not appear anywhere in the official NHL schedule capture "
                              "(22-28 Oct 2026).",
                    "source_url": "https://api-web.nhle.com/v1/schedule/2026-10-22",
                    "dataset": "data/master.json",
                })
        elif sport == "baseball":
            if "mlb" not in comp:
                skipped += 1
                continue
            checked += 1
            if not any(name_match(h, x[0]) and name_match(a, x[1]) for x in mlb):
                out.append({
                    "category": "no-official-fixture", "severity": "error",
                    "row": {k: r.get(k) for k in ("sport", "date", "home", "away")},
                    "detail": "This MLB pairing does not appear in the official postseason schedule capture.",
                    "source_url": "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-22&endDate=2026-11-05",
                    "dataset": "data/master.json",
                })
        elif sport == "basketball":
            if "euroleague" not in comp and "eurocup" not in comp:
                skipped += 1
                continue
            checked += 1
            if not any(name_match(h, x[0]) and name_match(a, x[1]) for x in el):
                out.append({
                    "category": "no-official-fixture", "severity": "warning",
                    "row": {k: r.get(k) for k in ("sport", "date", "home", "away")},
                    "detail": "Pairing not found in the official EuroLeague games feed for 2026-27.",
                    "source_url": "https://api-live.euroleague.net/v2/competitions/E/seasons/E2026/games",
                    "dataset": "data/master.json",
                })
    findings.extend(out)
    return [{"fixtures_compared": checked, "skipped_outside_capture_window": skipped, "mismatches": len(out)}]


def peer_desks() -> list[dict]:
    out = []
    for p in sorted(ROOT.glob("data/session-*/**/*.json")):
        if p.stat().st_size > 4_000_000:
            continue
        d = load(p)
        if not isinstance(d, (dict, list)):
            continue
        rows = d.get("rows") if isinstance(d, dict) else None
        if not rows and isinstance(d, dict):
            for key in ("fixtures", "entries", "matches", "predictions", "board"):
                if isinstance(d.get(key), list) and d[key] and isinstance(d[key][0], dict):
                    rows = d[key]
                    break
        if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
            continue
        no_src = sum(1 for r in rows if isinstance(r, dict) and not (r.get("source_url") or r.get("official_url")))
        out.append({
            "file": str(p.relative_to(ROOT)), "rows": len(rows),
            "rows_without_source": no_src,
            "schema_hint": sorted(list(rows[0].keys()))[:12],
        })
    out.sort(key=lambda x: -x["rows"])
    return out[:40]


def flag_own_desk() -> list[dict]:
    desk = load(OUT / "desk.json", {})
    preds = load(OUT / "predictions.json", {})
    flags = []
    sport_counts = Counter(r["sport"] for r in desk["rows"])
    pred_counts = Counter(p["sport"] for p in preds["predictions"])

    flags.append({
        "id": "AF-F01", "severity": "info", "area": "odds-window arithmetic",
        "title": "Why only a 1.4% band satisfies both '>70%' and 'no shorter than -250'",
        "detail": "A fair price of -250 is a decimal 1.400, i.e. a 71.43% implied chance. Any selection our model "
                  "rates above 71.43% is therefore necessarily shorter than -250, and any selection rated below "
                  "70.00% is not a >70% pick. The only overlap is a model probability of 0.7000-0.7143 "
                  "(fair 1.4000-1.4286). Board AF publishes every 70%+ selection it finds even when the price is "
                  "shorter than -250 (the match-winner pick column), and it builds the five-per-sport prediction "
                  "set from the highest-probability selections that do sit inside -250 to +10,000.",
        "source_url": "https://www.nhl.com/schedule",
    })
    flags.append({
        "id": "AF-F02", "severity": "warning", "area": "handball fixtures",
        "title": "EHF fixture list read from a client-rendered page; raw capture holds only the page shell",
        "detail": "The EHF Champions League matches page renders its fixture cards in JavaScript. The committed "
                  "raw capture (SHA-256 in the manifest) contains the page shell, so the seven 28 October "
                  "fixtures were read from the rendered page on 2026-10-22T21:05Z and are transcribed into "
                  "desk.json with the printed CET times. Standings (the model inputs) are server-rendered and "
                  "fully reproducible from the capture.",
        "source_url": "https://ehfcl.eurohandball.com/men/2026-27/matches/",
    })
    flags.append({
        "id": "AF-F03", "severity": "warning", "area": "volleyball sample",
        "title": "SuperLega had played one round when the desk was built",
        "detail": "Only one match per club was in the official classifica at capture time, so every rate is shrunk "
                  "hard toward the league average (k=8). The five volleyball picks are published with Medium/Low "
                  "labels, not High, and the model probability on each is disclosed.",
        "source_url": "https://www.legavolley.it/classifica/?IdCampionato=999",
    })
    flags.append({
        "id": "AF-F04", "severity": "warning", "area": "baseball pitching",
        "title": "No official probable pitcher published for the World Series games at capture time",
        "detail": "The MLB postseason schedule feed carried no probablePitcher for the games listed, so the run "
                  "model is team-level only (runs scored/allowed over 162 games). If a probable pitcher is "
                  "announced, the numbers should be re-run before staking.",
        "source_url": "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-22&endDate=2026-11-05",
    })
    for sport, n in sorted(pred_counts.items()):
        flags.append({
            "id": f"AF-F05-{re.sub(r'[^a-z]', '', sport.lower())[:8]}", "severity": "info", "area": "coverage",
            "title": f"{sport}: {n} predictions published against {sport_counts[sport]} verified fixtures",
            "detail": f"The desk carries {sport_counts[sport]} verified {sport} fixtures and {n} written "
                      f"predictions (the five highest-probability in-window selections).",
            "source_url": (load(OUT / 'predictions.json', {}).get('predictions') or [{}])[0].get("official_url", ""),
        })
    missing = []
    for sport in ("Tennis", "Cricket", "Snooker", "Rugby League", "Darts", "Badminton",
                  "Table Tennis", "eSports", "Aussie Rules", "Golf", "Motor Racing", "Greyhounds",
                  "Gaelic Football"):
        missing.append(sport)
        flags.append({
            "id": f"AF-F06-{re.sub(r'[^a-z]', '', sport.lower())[:8]}", "severity": "needs review",
            "area": "coverage gap",
            "title": f"{sport} is in scope but has no Board AF prediction today",
            "detail": "No official fixture/ranking feed for this sport could be captured and verified in this "
                      "run: the captured pages were either client-rendered shells, blocked (HTTP 403/404) or did "
                      "not publish a head-to-head line-up at capture time. Nothing is inferred or filled in; the "
                      "sport is published as a gap rather than with guessed rows.",
            "source_url": "https://www.olbg.com/betting-tips",
        })
    flags.append({
        "id": "AF-F07", "severity": "warning", "area": "rugby union draw treatment",
        "title": "Top 14 two-way lines fold the modelled draw into both sides",
        "detail": "Top 14 matches can be drawn. Board AF quotes a two-way half-line market and folds the draw "
                  "probability into both sides using the normal margin assumption, rather than pretending draws "
                  "do not exist. The draw is included in the model total of 1.0.",
        "source_url": "https://top14.lnr.fr/classement",
    })
    return flags


def main() -> int:
    findings, stats = review_master()
    xc = cross_check(findings)
    peers = peer_desks()
    review = {
        "schema": "olbg4.board-af-review/v1", "session": "arena/2d25cf78-olbg4", "board": "AF",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "reviewed_dataset": "data/master.json",
        "rows_reviewed": len(load(ROOT / "data/master.json", {}).get("rows", [])),
        "category_counts": stats,
        "cross_check": xc,
        "peer_desks": peers,
        "findings": findings,
    }
    (OUT / "review.json").write_text(json.dumps(review, indent=1, ensure_ascii=False) + "\n")
    flags = {
        "schema": "olbg4.board-af-flagged/v1", "session": "arena/2d25cf78-olbg4", "board": "AF",
        "generated_utc": review["generated_utc"], "items": flag_own_desk(),
    }
    (OUT / "flagged.json").write_text(json.dumps(flags, indent=1, ensure_ascii=False) + "\n")
    print("master rows", review["rows_reviewed"], "findings", len(findings), dict(stats))
    print("cross-check", xc)
    print("peer desks", len(peers), "flagged", len(flags["items"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
