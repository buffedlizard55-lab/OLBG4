"""Board AH (arena/b2c7308d-olbg4) — line-by-line data review.

Re-reads the originated desk and re-checks every row against the rules the
board publishes: identity, official source link, market arithmetic
(prob_sum == 1 per market, decimal == 1/p, american conversion), confidence
tiers, the -250..+10000 window for high-confidence rows, prediction
presence/length/vocabulary for high-confidence rows, and strictly-blank
values for unpriced rows.

Writes data/session-b2c7308d/review.json + review.md. Exits 1 if any hard
check fails (soft warnings are recorded, not fatal).
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(ROOT, "data", "session-b2c7308d")

BANNED = ("model", "verified", "verify", "verifying")
SCOPE = {"Golf", "Volleyball", "Rugby Union", "Cricket", "Snooker", "Darts", "Baseball",
         "Gaelic Sports", "Greyhounds", "Tennis", "Motor Racing", "Handball",
         "Ice Hockey", "Basketball", "Rugby League"}


def load_bank():
    spec = importlib.util.spec_from_file_location(
        "pb", os.path.join(HERE, "predictions_bank.py"))
    pb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pb)
    return dict(pb.PREDICTIONS)


def american_from_prob(p: float) -> int:
    """Mirror originate_desk.american_from_decimal exactly (decimal rounded to 3dp)."""
    p = min(0.999, max(0.001, p))
    dec = round(1.0 / p, 3)
    return int(round((dec - 1.0) * 100)) if dec >= 2.0 else int(round(-100.0 / (dec - 1.0)))


def jaccard3(a: str, b: str) -> float:
    def ng(s):
        w = [x for x in "".join(c.lower() if c.isalnum() else " " for c in s).split() if len(x) > 2]
        return set(tuple(w[i:i + 3]) for i in range(len(w) - 2))
    ga, gb = ng(a), ng(b)
    return len(ga & gb) / max(1, len(ga | gb))


def main() -> int:
    desk = json.load(open(os.path.join(DATA, "desk.json")))
    flagged = json.load(open(os.path.join(DATA, "flagged.json")))
    bank = load_bank()
    rows = desk["rows"]
    flag_ids = sorted(f["id"] for f in flagged["flags"])
    sports_with_flags = {f["sport"] for f in flagged["flags"]}

    out_rows = {}
    fails: list[str] = []
    warns: list[str] = []

    ids = [r["id"] for r in rows]
    if len(ids) != len(set(ids)):
        fails.append("duplicate row ids")

    for r in rows:
        rid = r["id"]
        checks: list[dict] = []

        def ck(name, ok, detail, hard=True):
            checks.append({"name": name, "ok": bool(ok), "detail": detail})
            if not ok and hard:
                fails.append(f"{rid}: {name} — {detail}")
            elif not ok:
                warns.append(f"{rid}: {name} — {detail}")

        ck("sport-in-scope", r["sport"] in SCOPE, r["sport"])
        ck("matchup-present", bool(r.get("matchup")), r.get("matchup", ""))
        ck("source-link", r.get("official_url", "").startswith("https://"),
           r.get("official_url", ""))

        markets = r.get("markets") or {}
        if r.get("priced"):
            for mk, mdata in markets.items():
                ssum = mdata.get("prob_sum")
                ck(f"market[{mk}]-sum", isinstance(ssum, (int, float)) and abs(ssum - 1.0) < 0.005,
                   f"prob_sum={ssum}")
                for sel in mdata.get("selections", []):
                    p = sel.get("fair_prob")
                    dec = sel.get("fair_decimal")
                    am = sel.get("fair_american")
                    if isinstance(p, (int, float)) and 0 < p < 1:
                        # stored prob is rounded to 4dp before publication; allow the
                        # resulting <=0.003 drift in the 3dp decimal odds
                        ck(f"sel[{sel['label'][:24]}]-decimal",
                           isinstance(dec, (int, float)) and abs(dec - 1.0 / p) <= max(0.004, 0.001 / p),
                           f"dec={dec} vs 1/{p}")
                        if isinstance(dec, (int, float)) and dec != 1.0:
                            am2 = int(round((dec - 1.0) * 100)) if dec >= 2.0 else int(round(-100.0 / (dec - 1.0)))
                            ck(f"sel[{sel['label'][:24]}]-american", am == am2, f"am={am} vs {am2}")
                        else:
                            ck(f"sel[{sel['label'][:24]}]-american", False, f"dec={dec}")
                    else:
                        ck(f"sel[{sel['label'][:24]}]-band", False, f"prob={p}")
            p = r.get("pick_prob")
            am = r.get("pick_fair_american")
            if isinstance(p, (int, float)) and 0 < p < 1:
                ck("pick-american", am == american_from_prob(p), f"{p} -> {am} vs {am}")
                conf = r.get("confidence")
                inwin = r.get("in_window")
                ck("window-consistent", inwin == (-250 <= am <= 10000),
                   f"in_window={inwin} am={am}")
                if conf == "High":
                    ck("high-window", -250 <= am <= 10000, f"fair american {am}")
                    ck("high-prob", p >= 0.70, f"p={p}")
                    txt = bank.get(rid)
                    ck("high-has-prediction", bool(txt), "prediction text present")
                    if txt:
                        ck("prediction-length", len(txt.split()) >= 30, f"{len(txt.split())} words")
                        ck("prediction-vocabulary",
                           not any(b in txt.lower() for b in BANNED), "no internal vocabulary")
        else:
            blanks_ok = all(r.get(k) in (None, "") for k in
                            ("pick_prob", "pick_fair_american"))
            no_markets = markets == {}
            ck("unpriced-blank", blanks_ok and no_markets, "no prices/picks for unpriced row")
            ck("unpriced-flagged", r["sport"] in sports_with_flags,
               "sport carries a gap-explaining review flag")
        out_rows[rid] = {"checks": checks,
                         "status": "ok" if all(c["ok"] for c in checks) else "issue"}

    # prediction-level checks
    texts = list(bank.items())
    for rid, t in texts:
        if len(t.split()) < 30:
            fails.append(f"prediction {rid}: under 30 words ({len(t.split())})")
        if any(b in t.lower() for b in BANNED):
            fails.append(f"prediction {rid}: contains internal vocabulary")
        for rid2, t2 in texts:
            if rid < rid2 and jaccard3(t, t2) >= 0.30:
                fails.append(f"predictions {rid}/{rid2}: trigram Jaccard >= 0.30")
    by_id = {r["id"]: r for r in rows}
    for rid, _ in texts:
        r = by_id.get(rid)
        if not r or not r.get("priced"):
            fails.append(f"prediction {rid}: row missing or unpriced")
        elif r.get("pick_prob", 0) < 0.70:
            pass  # non-high rows may carry predictions (top-5 per sport rule)
        if r and r["sport"] not in SCOPE:
            fails.append(f"prediction {rid}: sport out of scope")

    # per-sport prediction coverage (brief target: >= 5 per covered sport)
    cov = Counter(by_id[rid]["sport"] for rid, _ in texts if rid in by_id)
    priced_sports = {r["sport"] for r in rows if r.get("priced")}
    for sp in sorted(priced_sports):
        n = cov.get(sp, 0)
        if n < 5:
            warns.append(f"coverage: {sp} has {n} predictions (target 5; limited by official inputs)")

    out = {
        "checked_rows": len(rows),
        "checked_predictions": len(texts),
        "hard_failures": sorted(set(fails)),
        "warnings": sorted(set(warns)),
        "flags_total": len(flagged["flags"]),
        "flag_ids": flag_ids,
        "rows": out_rows,
    }
    os.makedirs(DATA, exist_ok=True)
    json.dump(out, open(os.path.join(DATA, "review.json"), "w"), indent=1)

    lines = ["# Board AH — line-by-line review", "",
             f"Rows checked: **{len(rows)}** · predictions checked: **{len(texts)}** · "
             f"hard failures: **{len(out['hard_failures'])}** · warnings: **{len(out['warnings'])}**", "",
             "| Row | Matchup | Status | Checks passed |", "|---|---|---|---|"]
    for r in rows:
        st = out_rows[r["id"]]["status"]
        n_ok = sum(1 for c in out_rows[r["id"]]["checks"] if c["ok"])
        n_all = len(out_rows[r["id"]]["checks"])
        lines.append(f"| [{r['id']}](sports/{r['sport_slug']}.html#{r['id']}) "
                     f"| {r['matchup'][:60]} | {'✅ ' + st if st == 'ok' else '⚠️ ' + st} "
                     f"| {n_ok}/{n_all} |")
    open(os.path.join(DATA, "review.md"), "w").write("\n".join(lines) + "\n")

    print(f"[board-ah] review: rows={len(rows)} preds={len(texts)} "
          f"hard_fails={len(out['hard_failures'])} warns={len(out['warnings'])}")
    for f in out["hard_failures"][:20]:
        print("  FAIL", f)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
