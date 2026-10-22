#!/usr/bin/env python3
"""Board AD — line-by-line verification gate.

Re-derives every published number from the committed data and fails loudly on any
inconsistency, any row without an official source, any prediction whose statistics are
not traceable to that row's verified inputs, and any broken internal link on the site.

Run:  python3 scripts/session-3a6388d2/verify.py     (exit 0 = pass)
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data", "session-3a6388d2")
SITE = os.path.join(ROOT, "session-3a6388d2")

WINDOW_START, WINDOW_END = "2026-10-22", "2026-11-08"
EXCLUDED = {"soccer", "football", "american football", "boxing", "ufc", "mma", "hurling",
            "horse racing", "cycling", "specials", "gaelic football"}

errors: list[str] = []
checks = 0


def check(cond: bool, msg: str) -> None:
    global checks
    checks += 1
    if not cond:
        errors.append(msg)


def dec_to_amer(d: float) -> int:
    if d >= 2.0:
        return int(round((d - 1.0) * 100))
    return int(round(-100.0 / (d - 1.0)))


def main() -> int:
    with open(os.path.join(DATA, "desk.json"), encoding="utf-8") as fh:
        desk = json.load(fh)
    rows = desk["rows"]
    preds = {}
    ppath = os.path.join(DATA, "predictions.json")
    if os.path.exists(ppath):
        with open(ppath, encoding="utf-8") as fh:
            preds = {p["row_id"]: p for p in json.load(fh).get("predictions", [])}

    print(f"verifying {len(rows)} rows…")
    seen_pred_texts: dict[str, str] = {}
    for r in rows:
        rid = r["id"]
        # ---- scope -----------------------------------------------------------------
        check(r["sport"].lower() not in EXCLUDED, f"{rid}: sport '{r['sport']}' is on the exclusion list")
        # ---- official source on every row ------------------------------------------
        check(bool(r.get("source_url", "").strip()), f"{rid}: no official source URL")
        check(bool(r.get("source_name", "").strip()), f"{rid}: no source name")
        # ---- date window -------------------------------------------------------------
        check(bool(r.get("date")), f"{rid}: empty date")
        check(WINDOW_START <= r.get("date", "") <= WINDOW_END, f"{rid}: date {r.get('date')} outside window")
        tu = r.get("time_utc") or ""
        if tu:
            # the league's own date (US/Eastern for the NHL) can be the day before the UTC kick-off
            from datetime import date as _d
            y1, m1, d1 = (int(x) for x in r["date"].split("-"))
            y2, m2, d2 = (int(x) for x in tu[:10].split("-"))
            gap = abs((_d(y2, m2, d2) - _d(y1, m1, d1)).days)
            check(gap <= 1, f"{rid}: time_utc {tu} more than a day from date {r['date']}")
        # ---- parties named -------------------------------------------------------------
        check(bool(r.get("home") or r.get("away")), f"{rid}: no teams/participants and no event name")

        if r.get("markets"):
            # ---- prices self-consistent -------------------------------------------------
            for m in r["markets"]:
                p = m["p"]
                check(0.0 < p < 1.0, f"{rid}: market probability {p} out of range")
                check(abs(m["fair_dec"] - 1.0 / p) / (1.0 / p) < 1e-3,
                      f"{rid}: fair decimal {m['fair_dec']} != 1/p ({1.0/p:.4f})")
                check(abs(m["fair_american"] - dec_to_amer(m["fair_dec"])) <= 1,
                      f"{rid}: fair american {m['fair_american']} != {dec_to_amer(m['fair_dec'])}")
                check(m["book_dec"] < m["fair_dec"], f"{rid}: book decimal not shorter than fair")
                check(min(abs(m["book_dec"] - 1.0 / (p * 1.042)),
                          abs(m["book_dec"] - 1.0 / (p * 1.052))) < 3e-3,
                      f"{rid}: book decimal {m['book_dec']} inconsistent with the published over-round")
                check(abs(m["book_american"] - dec_to_amer(m["book_dec"])) <= 1,
                      f"{rid}: book american {m['book_american']} != {dec_to_amer(m['book_dec'])}")
            # ---- two-way markets sum to 1 (before the over-round) -----------------------
            win = [m for m in r["markets"] if "Winner" in m["market"] and "Outright" not in m["market"]]
            draw = [m for m in r["markets"] if m["market"] == "Draw"]
            if len(win) == 2:
                total = sum(m["p"] for m in win) + sum(m["p"] for m in draw)
                check(abs(total - 1.0) < 0.02,
                      f"{rid}: win probabilities (+draw) sum to {total:.4f}")
            # ---- pick and confidence ------------------------------------------------------
            pick = r.get("pick") or {}
            check(bool(pick.get("selection")), f"{rid}: priced row without a pick")
            pp = pick.get("p", 0)
            check(abs(pick["fair_american"] - dec_to_amer(1.0 / pp)) <= 1,
                  f"{rid}: pick price inconsistent with probability")
            check(r["confidence"] in ("High", "Medium", "Low"), f"{rid}: bad confidence '{r['confidence']}'")
            exp = "High" if pp >= 0.70 else ("Medium" if pp >= 0.60 else "Low")
            order = ("Low", "Medium", "High")
            if "capped" in (r.get("confidence_rule") or "").lower():
                # a documented sample cap can only lower the grade, never raise it
                exp = exp if order.index(exp) <= order.index("Medium") else "Medium"
            check(r["confidence"] == exp,
                  f"{rid}: confidence {r['confidence']} but p={pp} implies {exp}")
            check(r.get("in_odds_window") == (-250 <= pick["fair_american"] <= 10000),
                  f"{rid}: odds-window flag does not match the fair price {pick['fair_american']}")
        else:
            # ---- unpriced rows must be honestly blank ------------------------------------
            check(not r.get("pick"), f"{rid}: unpriced row publishes a pick")
            check(not r.get("confidence"), f"{rid}: unpriced row publishes a confidence")
            check(bool(r.get("flags")), f"{rid}: unpriced row carries no explanation flag")

    # ---- predictions -------------------------------------------------------------------
    high = [r for r in rows if r.get("confidence") == "High"]
    print(f"verifying {len(high)} high-confidence predictions…")
    for r in high:
        rid = r["id"]
        pr = preds.get(rid)
        check(pr is not None, f"{rid}: High-confidence row has no prediction")
        if not pr:
            continue
        text = pr["text"]
        words = len(text.split())
        check(words >= 30, f"{rid}: prediction is {words} words (minimum 30)")
        check(text.strip() not in seen_pred_texts, f"{rid}: prediction text duplicates {seen_pred_texts.get(text.strip())}")
        seen_pred_texts[text.strip()] = rid
        check(pr["selection"] == r["pick"]["selection"], f"{rid}: prediction selection != row pick")
        low = text.lower()
        def names_a_side(name: str) -> bool:
            if not name:
                return False
            return name.lower() in low or any(
                w.lower() in low for w in re.findall(r"[A-Za-z]{5,}", name))
        check(names_a_side(r.get("home")) or names_a_side(r.get("away")),
              f"{rid}: prediction does not name either side")
        check(("selection is" in low) or ("pick is" in low) or ("back " in low) or ("take " in low),
              f"{rid}: prediction does not state the selection explicitly")
        # every number quoted must exist in the row's verified official inputs
        numeric_inputs = [v for v in r.get("model_inputs", {}).values() if isinstance(v, (int, float))]
        str_numbers = []
        for v in r.get("model_inputs", {}).values():
            if isinstance(v, str):
                str_numbers += re.findall(r"\d+(?:\.\d+)?", v)
        numeric_inputs += [r["pick"]["p"] * 100]
        for num in re.findall(r"\d+\.\d+", text):
            if len(num.split(".")[0]) > 2:       # skip things like 2026.10
                continue
            val = float(num)
            ok = (num in str_numbers or f"{val:.2f}" in str_numbers
                  or any(abs(val - v) <= 0.0051 for v in numeric_inputs)
                  or any(abs(val - float(x)) <= 0.0051 for x in str_numbers))
            check(ok, f"{rid}: prediction quotes {num} which is not in the row's verified inputs")

    # ---- site: internal links resolve ---------------------------------------------------
    print("checking site links…")
    pages = []
    for dirpath, _, filenames in os.walk(SITE):
        for fn in filenames:
            if fn.endswith(".html"):
                pages.append(os.path.join(dirpath, fn))
    for page in pages:
        html = open(page, encoding="utf-8").read()
        for href in re.findall(r'href="([^"#][^"]*)"', html):
            if href.startswith(("http", "mailto:", "../data/")) or href.startswith("//"):
                continue
            target = os.path.normpath(os.path.join(os.path.dirname(page), href.split("?")[0]))
            check(os.path.exists(target), f"{os.path.relpath(page, SITE)}: broken link {href}")
        # every data table row must carry an official source link
        if os.path.basename(page) in ("matches.html", "picks.html") or "/sports/" in page:
            body_rows = re.findall(r"<tbody>(.*?)</tbody>", html, re.S)
            trs = sum(len(re.findall(r"<tr", b)) for b in body_rows)
            links = sum(b.count('target="_blank"') for b in body_rows)
            check(links >= trs, f"{os.path.relpath(page, SITE)}: {trs} rows but only {links} source links")

    # ---- capture evidence -----------------------------------------------------------------
    print("checking capture evidence…")
    manifests = [f for f in os.listdir(DATA) if f.startswith("manifest") and f.endswith(".json")]
    check(bool(manifests), "no capture manifest committed")
    total = ok = 0
    for mf in manifests:
        with open(os.path.join(DATA, mf), encoding="utf-8") as fh:
            m = json.load(fh)
        total += m["targets_total"]
        ok += m["ok"]
        for e in m["entries"]:
            if e.get("saved_as"):
                check(os.path.exists(os.path.join(ROOT, e["saved_as"])),
                      f"{mf}: raw file missing for {e['id']}")

    # ---- completeness: every official in-window fixture must appear on the desk ----------
    completeness = {}
    sys.path.insert(0, os.path.join(ROOT, "scripts", "session-3a6388d2"))
    try:
        import originate as O                       # reuses the same raw reader the desk is built from
        sched = {}
        for f in ("nhl_sched_w1", "nhl_sched_w2", "nhl_sched_w3"):
            d = O.raw_json(f)
            for day in d.get("gameWeek", []):
                for g in day.get("games", []):
                    sched[g["id"]] = (day["date"], g)
        inwin = [(dt, g) for dt, g in sched.values()
                 if WINDOW_START <= dt <= WINDOW_END and g.get("gameType") in (2, 3)]
        desk_nhl = set((r["date"], r["away"].split()[-1], r["home"].split()[-1])
                       for r in rows if r["sport"] == "Ice Hockey")
        desk_hockey_rows = sum(1 for r in rows if r["sport"] == "Ice Hockey")
        for dt, g in inwin:
            key = (dt, g["awayTeam"]["commonName"]["default"].split()[-1],
                   g["homeTeam"]["commonName"]["default"].split()[-1])
            check(key in desk_nhl,
                  f"NHL {dt}: {key[1]} @ {key[2]} is on the official schedule but not on the desk")
        completeness["Ice Hockey"] = {
            "official_source": "https://api-web.nhle.com/v1/schedule/2026-10-22",
            "official_fixtures_captured": len(sched),
            "official_fixtures_in_window": len(inwin),
            "desk_rows": desk_hockey_rows,
            "missing_from_desk": len(inwin) - sum(
                1 for dt, g in inwin
                if (dt, g["awayTeam"]["commonName"]["default"].split()[-1],
                    g["homeTeam"]["commonName"]["default"].split()[-1]) in desk_nhl),
        }
        print(f"completeness: NHL {len(desk_nhl)} desk rows vs {len(inwin)} official in-window fixtures "
              f"({completeness['Ice Hockey']['missing_from_desk']} missing)")
    except Exception as exc:                        # never let the report step mask a real finding
        errors.append(f"completeness check could not run: {exc}")

    report = {
        "schema": "olbg4/board-ad-verify/v1",
        "session": "arena/3a6388d2-olbg4",
        "board": "AD",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window": {"start": WINDOW_START, "end": WINDOW_END},
        "checks_run": checks,
        "rows": len(rows),
        "priced": sum(1 for r in rows if r["markets"]),
        "flagged_no_line": sum(1 for r in rows if not r["markets"]),
        "by_confidence": dict(Counter(r["confidence"] or "no line" for r in rows)),
        "high_picks": len(high),
        "high_in_odds_window": sum(1 for r in high if r.get("in_odds_window")),
        "captures_ok": ok,
        "captures_total": total,
        "completeness": completeness,
        "errors": errors,
        "passed": not errors,
    }
    with open(os.path.join(DATA, "verify_report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
        fh.write("\n")

    print(f"\nchecks run: {checks}")
    print(f"captures:   {ok}/{total} official requests returned HTTP 200")
    print(f"rows:       {len(rows)} ({sum(1 for r in rows if r['markets'])} priced, "
          f"{sum(1 for r in rows if not r['markets'])} flagged without a line)")
    print(f"confidence: {dict(Counter(r['confidence'] or 'no line' for r in rows))}")
    print(f"high picks: {len(high)} ({sum(1 for r in high if r['in_odds_window'])} inside -250…+10000)")
    if errors:
        print(f"\nFAILED — {len(errors)} problem(s):")
        for e in errors[:60]:
            print("  -", e)
        return 1
    print("\nPASS — every row, price, prediction and link verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
