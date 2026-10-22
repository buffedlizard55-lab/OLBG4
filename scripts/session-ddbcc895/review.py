#!/usr/bin/env python3
"""Board AF — line-by-line review of the repository's shared desks.

Every finding is a fact about a row in a committed dataset, with the row's own
source URL (or the absence of one) recorded. The review does not edit any other
session's files; it publishes the defects for manual review on the site.
"""
from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "session-ddbcc895"
CUTOFF = "2026-10-22T22:00:00Z"
EXCLUDED = ["soccer", "football", "american football", "boxing", "ufc", "mma", "hurling",
            "horse racing", "cycling", "specials"]
DATASETS = [
    ("data/master.json", "Canonical merged board (master.json)", "rows"),
    ("data/session-22ca2e95/desk.json", "Board AE desk (22ca2e95)", "rows"),
    ("data/session-3a6388d2/desk.json", "Board AD desk (3a6388d2)", "rows"),
    ("data/session-e1161e0e/board.json", "Board X desk (e1161e0e)", "rows"),
    ("data/session-9359e596/desk.json", "Board Z desk (9359e596)", "rows"),
]


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    s = re.sub(r"\b(fc|cf|sc|ac|club|the)\b", " ", s.lower())
    return re.sub(r"[^a-z0-9]", "", s)


def date_of(r: dict) -> str:
    for k in ("start_utc", "time_utc", "kickoff_utc", "date", "start"):
        v = r.get(k)
        if v:
            return str(v)[:10]
    return ""


def teams_of(r: dict) -> tuple[str, str]:
    a = r.get("home") or r.get("side_a") or r.get("team_a") or ""
    b = r.get("away") or r.get("side_b") or r.get("team_b") or ""
    if "matchup" in r and not (a and b):
        parts = re.split(r"\s+vs?\.?\s+", str(r.get("matchup")), maxsplit=1)
        if len(parts) == 2:
            a, b = parts
    return str(a), str(b)


def pick_of(r: dict) -> str:
    for k in ("pick", "pick_label", "winner_pick", "match_winner_pick", "featured_pick", "selection"):
        v = r.get(k)
        if isinstance(v, dict):
            v = v.get("selection") or v.get("label")
        if v and isinstance(v, str):
            return v
    return ""


def source_of(r: dict) -> str:
    for k in ("source_url", "official_url", "url"):
        v = r.get(k)
        if v and str(v).startswith("http"):
            return str(v)
    return ""


def price_of(r: dict, pick: str = ""):
    for k in ("pick_book_american", "match_winner_book_american", "book_american", "pick_amer", "odds_american"):
        v = r.get(k)
        if isinstance(v, (int, float)):
            return int(v)
    markets = r.get("markets")
    if isinstance(markets, list):
        for m in markets:
            if not isinstance(m, dict):
                continue
            sel = str(m.get("selection") or "")
            if pick and (pick.lower() in sel.lower() or sel.lower() in pick.lower()):
                for k in ("book_american", "am", "american"):
                    if isinstance(m.get(k), (int, float)):
                        return int(m[k])
    if isinstance(markets, dict):
        ml = markets.get("moneyline") or markets.get("match_winner")
        if isinstance(ml, dict):
            if pick and pick.lower() == str(ml.get("a_label", "")).lower():
                return int(ml.get("am_a")) if isinstance(ml.get("am_a"), (int, float)) else None
            if pick and pick.lower() == str(ml.get("b_label", "")).lower():
                return int(ml.get("am_b")) if isinstance(ml.get("am_b"), (int, float)) else None
        for name, m in markets.items():
            if isinstance(m, dict) and pick:
                for label, val in m.items():
                    if isinstance(label, str) and pick and pick.lower() in label.lower():
                        try:
                            dec = float(val)
                            return int(round((dec - 1) * 100)) if dec >= 2 else int(round(-100 / (dec - 1)))
                        except Exception:
                            pass
    win = r.get("win") or {}
    odds = win.get("odds") if isinstance(win, dict) else None
    if isinstance(odds, dict) and len(odds) == 2:
        vals = []
        for v in odds.values():
            try:
                vals.append(float(v))
            except Exception:
                pass
        if len(vals) == 2:
            return vals
    return None


def main() -> int:
    raw = json.loads((DATA / "fixtures_raw.json").read_text(encoding="utf-8"))
    official = []
    for f in raw["fixtures"]:
        official.append((norm(f["side_a"]), norm(f["side_b"]), f["start_utc"][:10], f))
    by_pair = defaultdict(list)
    for a, b, d, f in official:
        by_pair[(a, b)].append(d)
        by_pair[(b, a)].append(d)

    summary, findings = {}, []
    fid = 0
    for rel, label, key in DATASETS:
        p = ROOT / rel
        if not p.exists():
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        rows = data.get(key) if isinstance(data, dict) else data
        if not isinstance(rows, list):
            continue
        s = {
            "label": label, "path": rel, "rows": len(rows),
            "excluded_sport_rows": 0, "stale_rows": 0, "no_source": 0, "no_pick": 0,
            "no_price": 0, "duplicates": 0, "short_predictions": 0,
            "high_out_of_window": 0, "placeholder_rows": 0,
            "confirmed_by_evening_capture": 0, "not_found_in_evening_capture": 0,
            "date_conflicts": 0,
        }
        seen = set()
        examples = {"no_source": [], "stale": [], "placeholder": [], "duplicate": [], "no_pick": []}
        for r in rows:
            sport = str(r.get("sport") or "").lower()
            a, b = teams_of(r)
            d = date_of(r)
            pick = pick_of(r)
            src = source_of(r)
            conf = str(r.get("confidence") or "").lower()
            if "gaelic" in sport:
                pass
            elif any(x in sport for x in EXCLUDED):
                s["excluded_sport_rows"] += 1
            if d and d < CUTOFF[:10] and str(r.get("row_kind") or "match") == "match":
                s["stale_rows"] += 1
                if len(examples["stale"]) < 4:
                    examples["stale"].append((r.get("id") or "", sport, a, b, d))
            if not src:
                s["no_source"] += 1
                if len(examples["no_source"]) < 4:
                    examples["no_source"].append((r.get("id") or "", sport, a, b, d))
            if not pick and str(r.get("row_kind") or "match") == "match" and not re.search(r"result|note", str(r.get("status") or ""), re.I):
                s["no_pick"] += 1
            if pick and price_of(r, pick) is None:
                s["no_price"] += 1
            if re.search(r"\bno fixture\b|\bfield\b|^n/?a\b|^\u2014$|^-$", f"{a} {b} {pick}", re.I):
                s["placeholder_rows"] += 1
                if len(examples["placeholder"]) < 3:
                    examples["placeholder"].append((r.get("id") or "", sport, a, b, d))
            pred_obj = r.get("prediction") or r.get("prediction_text") or ""
            if isinstance(pred_obj, dict):
                pred_obj = pred_obj.get("text", "")
            pred = str(pred_obj)
            if pred:
                wc = len(re.findall(r"[A-Za-z0-9'\-]+", pred))
                if wc < 30:
                    s["short_predictions"] += 1
                    if len(findings) < 200:
                        findings.append({
                            "dataset": label, "row": r.get("id") or "", "sport": r.get("sport"),
                            "category": "prediction under 30 words",
                            "detail": f"Prediction has {wc} words; the brief requires at least 30.",
                            "source": src,
                        })
            key3 = (norm(a), norm(b), d)
            if a and b and key3 in seen:
                s["duplicates"] += 1
                if len(findings) < 200:
                    findings.append({
                        "dataset": label, "row": r.get("id") or "", "sport": r.get("sport"),
                        "category": "duplicate fixture",
                        "detail": f"{a} vs {b} appears more than once on {d}.",
                        "source": src,
                    })
            seen.add(key3)
            pr = price_of(r, pick)
            if conf == "high" and isinstance(pr, int) and not (-250 <= pr <= 10000):
                s["high_out_of_window"] += 1
            # cross-check against this evening's official capture
            if a and b and d and d >= "2026-10-23":
                dates = by_pair.get((norm(a), norm(b)))
                if dates:
                    def day_gap(x, y):
                        try:
                            return abs((datetime.strptime(x, "%Y-%m-%d") - datetime.strptime(y, "%Y-%m-%d")).days)
                        except Exception:
                            return 99
                    if any(day_gap(d, x) <= 1 for x in dates):
                        s["confirmed_by_evening_capture"] += 1
                    else:
                        s["date_conflicts"] += 1
                        if len(findings) < 200:
                            findings.append({
                                "dataset": label, "row": r.get("id") or "", "sport": r.get("sport"),
                                "category": "date conflict with 22 Oct official capture",
                                "detail": f"{a} vs {b} is dated {d} here; the same pairing is dated {', '.join(sorted(set(dates)))} on the official page captured 22 Oct 2026.",
                                "source": src,
                            })
                elif src:
                    s["not_found_in_evening_capture"] += 1
        for cat, items in examples.items():
            for rid, sport, a, b, d in items:
                findings.append({
                    "dataset": label, "row": rid, "sport": sport,
                    "category": {"no_source": "row has no official source URL",
                                 "stale": "row dated before the 22 Oct 2026 evening cutoff",
                                 "placeholder": "placeholder row rather than a fixture",
                                 "duplicate": "duplicate fixture",
                                 "no_pick": "no pick recorded"}[cat],
                    "detail": f"{a} vs {b} on {d}" if a or b else f"row {rid}",
                    "source": "",
                })
        summary[rel] = s

    payload = {
        "schema": "olbg4.board-af.review/1",
        "reviewed_utc": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cutoff_utc": CUTOFF,
        "datasets": summary,
        "findings": findings,
        "totals": {
            "rows": sum(v["rows"] for v in summary.values()),
            "stale_rows": sum(v["stale_rows"] for v in summary.values()),
            "no_source": sum(v["no_source"] for v in summary.values()),
            "no_pick": sum(v["no_pick"] for v in summary.values()),
            "excluded_sport_rows": sum(v["excluded_sport_rows"] for v in summary.values()),
            "duplicates": sum(v["duplicates"] for v in summary.values()),
            "short_predictions": sum(v["short_predictions"] for v in summary.values()),
        },
    }
    (DATA / "review.json").write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    for rel, s in summary.items():
        print(rel, {k: v for k, v in s.items() if isinstance(v, int) and k != "rows"})
    print("findings", len(findings))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
