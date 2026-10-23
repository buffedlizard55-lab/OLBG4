#!/usr/bin/env python3
"""Board FX line-by-line review of the shared datasets.

Reads (never writes) data/master.json and the peer desks under data/session-*/,
and checks them against the official bytes captured for this session.  A finding
is only raised when both sides of the comparison are printed, so the reader can
re-perform it from the linked official page.
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parse as P  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data", "session-4502eff5")


def norm(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"\(.*?\)", "", s)
    s = s.replace("&", "and")
    s = re.sub(r"\b(fc|afc|cf|sc|club|the)\b", "", s)
    return re.sub(r"[^a-z0-9]", "", s)


def official_index(cap: P.Capture):
    """(sport, normalised home, normalised away) -> official fixture dict."""
    idx = {}
    for f in P.read_nhl(cap):
        idx[("Ice Hockey", norm(f["side_b"]), norm(f["side_a"]))] = f
    liiga, _ = P.read_liiga(cap)
    for f in liiga:
        idx.setdefault(("Ice Hockey", norm(f["side_b"]), norm(f["side_a"])), f)
    for f in P.read_mlb(cap):
        idx[("Baseball", norm(f["side_b"]), norm(f["side_a"]))] = f
    for f in P.read_euroleague(cap, "el_games", "EuroLeague"):
        idx.setdefault(("Basketball", norm(f["side_b"]), norm(f["side_a"])), f)
    for f in P.read_euroleague(cap, "eurocup_games", "EuroCup"):
        idx.setdefault(("Basketball", norm(f["side_b"]), norm(f["side_a"])), f)
    for f in P.read_urc(cap):
        idx.setdefault(("Rugby Union", norm(f["side_b"]), norm(f["side_a"])), f)
    return idx


def main():
    cap_dir = sys.argv[1] if len(sys.argv) > 1 else sorted(glob.glob(os.path.join(ROOT, "data/session-4502eff5/capture/*")))[-1]
    cap = P.Capture(cap_dir)
    idx = official_index(cap)
    findings, flags = [], []

    def find(fid, severity, dataset, row, finding, verification, url):
        findings.append({"id": fid, "severity": severity, "dataset": dataset, "row": row,
                         "finding": finding, "verification": verification, "manual_url": url})

    def flag(fid, sport, row, issue, impact, url):
        flags.append({"id": fid, "sport": sport, "row": row, "issue": issue, "impact": impact, "source_url": url})

    # ---------------------------------------------------------------- master.json
    mp = os.path.join(ROOT, "data", "master.json")
    master = json.load(open(mp))
    mrows = master.get("rows", [])
    n = 0
    no_source = [r for r in mrows if not (r.get("source_url") or "").strip()]
    if no_source:
        find("FX4-M01", "high", "data/master.json", f"{len(no_source)} of {len(mrows)} rows",
             "Rows publish win/handicap/total/pick values with no source URL at all.",
             "Counted every row whose source_url is empty.", "https://buffedlizard55-lab.github.io/OLBG4/board/")
        flag("FX4-F01", "all", "data/master.json", f"{len(no_source)} rows without a source_url",
             "A reader cannot re-check these rows; they should not be treated as verified.", "")
    unverified = [r for r in mrows if r.get("build_verified") is False]
    if unverified:
        find("FX4-M02", "high", "data/master.json", f"{len(unverified)} rows",
             "Rows are published from builds whose own record says build_verified = false.",
             "Flag build_verified is false on the row itself.", "https://buffedlizard55-lab.github.io/OLBG4/board/")
    stale = [r for r in mrows if (r.get("date") or "") < "2026-10-23"]
    if stale:
        find("FX4-M03", "medium", "data/master.json", f"{len(stale)} rows",
             "Rows carry dates before the capture day, so they are results or expired fixtures, not upcoming matches.",
             "Compared each row date with 2026-10-23 (this session's capture date).", "https://buffedlizard55-lab.github.io/OLBG4/board/")
    bad_pred = []
    seen = Counter()
    for r in mrows:
        t = (r.get("prediction") or "").strip()
        if not t:
            continue
        seen[t] += 1
        if len(t.split()) < 30:
            bad_pred.append((r.get("sport"), r.get("home"), r.get("away"), len(t.split())))
        if re.search(r"\b(model|verified|verification)\b", t, re.I):
            bad_pred.append((r.get("sport"), r.get("home"), r.get("away"), "banned-word"))
    if bad_pred:
        find("FX4-M04", "medium", "data/master.json", f"{len(bad_pred)} predictions",
             "Predictions under 30 words or containing internal vocabulary (model/verified) that the brief forbids in published text.",
             f"Token counts and regex scan of every non-empty prediction; first three: {bad_pred[:3]}",
             "https://buffedlizard55-lab.github.io/OLBG4/board/")
    dupes = {t: c for t, c in seen.items() if c > 1}
    if dupes:
        find("FX4-M05", "medium", "data/master.json", f"{len(dupes)} duplicated texts",
             "The same prediction text is reused on more than one row.",
             f"Exact-string counts; worst repeat: {max(dupes.values())} copies.", "https://buffedlizard55-lab.github.io/OLBG4/board/")

    # matchup verification against the official feed
    checked = mismatched = ambiguous = 0
    examples = []
    for r in mrows:
        sport = r.get("sport")
        if sport not in ("Ice Hockey", "Basketball", "Baseball"):
            continue
        home, away = norm(r.get("home")), norm(r.get("away"))
        if not home or not away:
            continue
        checked += 1
        key = (sport, home, away)
        rev = (sport, away, home)
        f = idx.get(key) or idx.get(rev)
        if not f:
            ambiguous += 1
            if len(examples) < 5:
                examples.append(f"{r.get('home')} v {r.get('away')} ({r.get('date')})")
            continue
        if f["start_utc"][:10] != (r.get("date") or "")[:10]:
            mismatched += 1
            if len(examples) < 5:
                examples.append(f"{r.get('home')} v {r.get('away')}: master {r.get('date')} vs official {f['start_utc'][:10]}")
    if mismatched:
        find("FX4-M06", "high", "data/master.json", f"{mismatched} of {checked} matched rows",
             "For rows whose pairing does appear on the official schedule, the published date differs from the official date.",
             "Pairing matched on normalised club names against the captured NHL/MLB/EuroLeague feeds; date compared day-level. "
             f"Examples: {examples[:3]}", "https://api-web.nhle.com/v1/schedule/2026-10-24")
    if ambiguous:
        find("FX4-M07", "medium", "data/master.json", f"{ambiguous} of {checked} rows",
             "Fixtures could not be found on the official schedule for that pairing inside the captured window, so they are unverified.",
             "Normalised home/away pairing search in the captured official feeds. " + f"Examples: {examples[:3]}",
             "https://www.nhl.com/schedule")

    # ---------------------------------------------------------------- peer desks
    peer_total = peer_unpriced = peer_missing_src = 0
    peer_files = sorted(glob.glob(os.path.join(ROOT, "data", "session-*", "desk.json")))
    for pf in peer_files:
        sid = os.path.basename(os.path.dirname(pf))
        try:
            d = json.load(open(pf))
        except Exception as exc:  # noqa: BLE001
            find("FX4-P00", "medium", f"data/{sid}/desk.json", "-", f"Desk could not be parsed as JSON: {exc}",
                 "json.load raised.", "")
            continue
        rows = d.get("rows") if isinstance(d, dict) else d
        if not isinstance(rows, list):
            continue
        peer_total += len(rows)
        miss = sum(1 for r in rows if not r.get("official_url"))
        peer_missing_src += miss
        peer_unpriced += sum(1 for r in rows if not r.get("pick") and not r.get("markets"))
        if miss:
            find("FX4-P01", "medium", f"data/{sid}/desk.json", f"{miss} of {len(rows)} rows",
                 "Peer desk rows without an official source URL.",
                 "Counted rows whose official_url is empty.", "")
    if peer_files:
        find("FX4-P02", "info", "data/session-*/desk.json", f"{len(peer_files)} desks / {peer_total} rows",
             "Aggregate state of the peer desks at review time.",
             f"{peer_missing_src} rows without a source URL; {peer_unpriced} rows with neither a pick nor markets.",
             "")

    # ---------------------------------------------------------------- our own desk
    desk_path = os.path.join(DATA, "desk.json")
    if os.path.exists(desk_path):
        desk = json.load(open(desk_path))
        bad = []
        for r in desk["rows"]:
            for k, m in r["markets"].items():
                total = sum(s["fair_prob"] for s in m["selections"])
                if abs(total - 1.0) > 0.002:
                    bad.append((r["id"], k, round(total, 4)))
                for s in m["selections"]:
                    if not s.get("fair_prob"):
                        bad.append((r["id"], k, "zero-probability leg"))
                        continue
                    exp_dec = round(1 / s["fair_prob"], 2)
                    if abs(exp_dec - s["fair_decimal"]) > 0.02:
                        bad.append((r["id"], k, "decimal", exp_dec, s["fair_decimal"]))
        if bad:
            find("FX4-O01", "high", "data/session-4502eff5/desk.json", f"{len(bad)} market legs",
                 "Own-line probability pairs do not sum to 1 or the decimal price is not 1/p.",
                 f"Recomputed both quantities; examples {bad[:3]}", "")
        # coverage gaps: sports carried but not priced, with the reason we could not price them
        gaps = {
            "Handball": "EHF Champions League standings captured, but the official match list renders client-side; no fixture feed was captured, so the 30 OLBG-listed matches stay blank.",
            "Tennis": "WTA match feeds captured and parsed, but no official singles ranking list was reachable (api.wtatennis.com/atptour.com returned 403/404), so a ranking-based line would be a guess.",
            "Cricket": "cricket.com.au fixture list captured, but no official competition table or rating list was reachable, so no line is originated.",
            "Rugby Union": "United Rugby Championship fixture list captured, but the official table and results feeds render client-side; only the fixture list is published.",
            "Darts": "pdc.tv pages are the same client-side shell; no draw or Order of Merit data could be read, so the six listings stay blank.",
            "Gaelic Sports": "gaa.ie fixtures captured; no official form or scoring feed across the same competitions, so no line.",
            "Greyhounds": "GBGB returns completed results only; the racecard and meeting APIs returned 404, so no upcoming race could be priced.",
            "Snooker": "priced from the official world ranking gap, but the best-of-7/11 format keeps the strongest pick below the 70% line on this card.",
            "Rugby League": "priced from the official RLWC feed; two matches per side is too small a sample for a 70% label, so every pick is capped at Medium.",
        }
        for sport, why in gaps.items():
            srow = [r for r in desk["rows"] if r["sport"] == sport]
            priced = [r for r in srow if r.get("pick")]
            flags.append({"id": "FX4-COV-" + re.sub(r"\W+", "", sport)[:8].upper(), "sport": sport,
                          "row": f"{len(srow)} rows / {len(priced)} priced",
                          "issue": why, "impact": "published as a blank row or a capped label; nothing inferred",
                          "source_url": srow[0]["official_url"] if srow else ""})
        flags.append({"id": "FX4-COV-INJ", "sport": "all", "row": "14 High picks",
                      "issue": "No official team injury report was captured for any priced fixture. The predictions therefore carry no injury claim; "
                               "squad-news feeds (nhl.com, euroleague.net) publish rosters but not availability lists at capture time.",
                      "impact": "predictions are built on records, goals/points per game and splits only", "source_url": ""})
        if not bad:
            flags.append({"id": "FX4-F02", "sport": "all", "row": "our desk",
                          "issue": "0 arithmetic defects found in our own market legs (probabilities sum to 1, decimal = 1/p)",
                          "impact": "none - recorded as a positive check", "source_url": ""})

    out = {
        "schema": "fx-review-1",
        "session": "arena/4502eff5-olbg4",
        "capture": os.path.basename(cap_dir.rstrip("/")),
        "summary": {"findings": len(findings), "flags": len(flags), "master_rows": len(mrows),
                    "peer_files": len(peer_files), "peer_rows": peer_total,
                    "matchups_checked": checked, "matchups_unverified": ambiguous, "matchups_date_mismatch": mismatched},
        "findings": findings,
        "flags": flags,
    }
    json.dump(out, open(os.path.join(DATA, "review.json"), "w"), indent=1, sort_keys=True)
    json.dump({"flags": flags, "generated_utc": desk.get("generated_utc", "") if os.path.exists(desk_path) else "",
               "session": "arena/4502eff5-olbg4"},
              open(os.path.join(DATA, "flagged.json"), "w"), indent=1, sort_keys=True)
    print(json.dumps(out["summary"], indent=1))


if __name__ == "__main__":
    main()
