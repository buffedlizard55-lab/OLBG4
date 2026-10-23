"""Board BW (arena/343754f2-olbg4) — line-by-line data review.

Re-reads the originated desk and re-checks every row against the rules the
board publishes: identity, official source link, market arithmetic
(prob_sum == 1 per market, decimal == 1/p, american conversion), confidence
tiers, the -250..+10000 window for high-confidence rows, prediction
presence/length/vocabulary for high-confidence rows, and strictly-blank
values for unpriced rows.

Writes data/session-343754f2/review.json + review.md. Exits 1 if any hard
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
DATA = os.path.join(ROOT, "data", "session-343754f2")

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



def repo_review() -> dict:
    """EZ4 — line-by-line review of the shared canonical datasets.

    Read-only: data/master.json and data/predictions.json are never modified.
    Every defect is recorded with its row coordinates and a manual-review URL,
    surfaced as non-blocking EZ4-REV-* flags on this session's Flagged page,
    and returned inside review.json under `repo_review`.
    """
    root = os.path.dirname(os.path.dirname(HERE))
    out = {"datasets": {}, "defects": [], "flags": []}
    master_path = os.path.join(root, "data", "master.json")
    m = json.load(open(master_path))
    rows = m.get("rows", [])
    gen = m.get("generated_on") or "9999-12-31"
    master_url = "https://github.com/buffedlizard55-lab/OLBG4/blob/main/data/master.json"
    per, defects = [], []

    def add(r, idx, issue, manual):
        defects.append({
            "dataset": "data/master.json", "row": idx, "build": r.get("build"),
            "sport": r.get("sport"), "date": r.get("date"),
            "matchup": f"{r.get('home') or ''} v {r.get('away') or ''}",
            "issue": issue, "manual_url": manual or r.get("source_url") or master_url,
        })

    classes: dict[str, list] = {}
    for idx, r in enumerate(rows):
        issues = []
        src = r.get("source_url") or ""
        date = r.get("date") or "9999-99-99"
        conf = r.get("confidence") or ""
        pred = r.get("prediction") or ""
        if not src:
            issues.append("no source_url — the dataset's own cutoff_note promises every row carries its build's source URL")
        if date < gen:
            issues.append(f"fixture date {date} predates the dataset generation date {gen} (stale or already-played row still published)")
        if conf == "High" and not r.get("build_verified"):
            issues.append("High confidence published on a row whose build_verified flag is false")
        if conf == "High" and not src:
            issues.append("High confidence published with no source_url")
        if pred and not src:
            issues.append("written prediction published without a source_url")
        if pred and not r.get("build_verified"):
            issues.append("written prediction published on a row whose build_verified flag is false")
        per.append({"row": idx, "ok": not issues, "issues": issues})
        for it in issues:
            add(r, idx, it, src)
            classes.setdefault(it.split(" — ")[0].split(" published")[0], []).append(idx)

    # taxonomy ambiguity provable from the file itself
    sports_in_scope = (m.get("counts") or {}).get("sports_in_scope") or []
    taxonomy = []
    norm = {sp: "".join(ch for ch in sp.lower() if ch.isalpha()) for sp in sports_in_scope}
    seen = {}
    for sp, n in norm.items():
        if n in seen:
            taxonomy.append(f"'{seen[n]}' and '{sp}' are both listed as in-scope sports labels")
        seen[n] = sp
    for t in taxonomy:
        defects.append({"dataset": "data/master.json", "row": None, "build": None,
                        "sport": "Repository", "date": None, "matchup": "",
                        "issue": t, "manual_url": master_url})
    per_status = {"rows": len(per), "clean": sum(1 for x in per if x["ok"]),
                  "with_defects": sum(1 for x in per if not x["ok"])}
    out["datasets"]["data/master.json"] = {
        "rows": len(rows), "generated_on": gen, "line_by_line": per,
        "summary": per_status,
        "defect_counts": {k: len(v) for k, v in sorted(classes.items())},
    }

    # ---- data/predictions.json — structural pass against its own stated rules ----
    pj_path = os.path.join(root, "data", "predictions.json")
    pj = json.load(open(pj_path))
    preds = pj.get("predictions") or []
    p_issues, p_ids = [], set()
    for i, pr in enumerate(preds):
        mid = pr.get("match_id") or f"#{i}"
        if mid in p_ids:
            p_issues.append(f"prediction {mid}: duplicate match_id")
        p_ids.add(mid)
        body = (pr.get("body") or "")
        if len(body.split()) < 30:
            p_issues.append(f"prediction {mid}: body under 30 words ({len(body.split())})")
        if (pr.get("confidence") or "").lower() == "high" and not (pr.get("pick") or "").strip():
            p_issues.append(f"prediction {mid}: high confidence without a pick")
        facts = pr.get("facts")
        if not isinstance(facts, list) or not facts:
            p_issues.append(f"prediction {mid}: facts list empty — dataset rules require a source URL per claim")
    for it in p_issues:
        defects.append({"dataset": "data/predictions.json", "row": None, "build": None,
                        "sport": "Repository", "date": None, "matchup": "",
                        "issue": it, "manual_url":
                            "https://github.com/buffedlizard55-lab/OLBG4/blob/main/data/predictions.json"})
    out["datasets"]["data/predictions.json"] = {
        "predictions": len(preds), "issues": len(p_issues),
        "summary": {"clean": len(preds) - len(set(x.split(":")[0] for x in p_issues)),
                    "with_defects": len(set(x.split(":")[0] for x in p_issues))},
    }

    out["defects"] = defects

    # ---- aggregate non-blocking flags (idempotent: EZ4-REV-* ids are rewritten) ----
    by_sport: dict[str, list] = {}
    for d in defects:
        by_sport.setdefault(d["sport"] or "Repository", []).append(d)
    n = 0
    for sport in sorted(by_sport):
        ds = by_sport[sport]
        n += 1
        samples = "; ".join(
            f"row {d['row']} ({d['build'] or '—'}, {d['sport']}, {d['date'] or '—'}, "
            f"{d['matchup'][:40]}): {d['issue']}"
            for d in ds[:6])
        more = f"; +{len(ds) - 6} more in review.json" if len(ds) > 6 else ""
        out["flags"].append({
            "id": f"EZ4-REV-{n:02d}", "severity": "review", "sport": sport,
            "title": f"{len(ds)} shared-dataset defect(s) flagged for manual review",
            "detail": f"Line-by-line review of data/master.json / data/predictions.json (read-only, nothing "
                      f"edited): {samples}{more}. Rows stay exactly as committed — defects are logged here, "
                      f"never corrected in place by this board.",
            "evidence_url": master_url, "manual_url": master_url,
        })
    return out


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

    # EZ4: line-by-line review of the shared datasets (read-only) + flagged page flags
    rr = repo_review()
    for d in rr["defects"]:
        warns.append(f"repo: {d['dataset']} row {d['row']} — {d['issue']}")
    out = {
        "checked_rows": len(rows),
        "checked_predictions": len(texts),
        "hard_failures": sorted(set(fails)),
        "warnings": sorted(set(warns)),
        "flags_total": len(flagged["flags"]),
        "flag_ids": flag_ids,
        "rows": out_rows,
        "repo_review": {k: v for k, v in rr.items() if k != "flags"},
    }
    os.makedirs(DATA, exist_ok=True)
    json.dump(out, open(os.path.join(DATA, "review.json"), "w"), indent=1)
    # publish EZ4-REV-* flags on the session Flagged page (idempotent rewrite)
    base_flags = [f for f in flagged["flags"] if not str(f.get("id", "")).startswith(("EZ4-REV-", "BW-REV-"))]
    all_flags = base_flags + rr["flags"]
    for f in all_flags:
        fid = str(f.get("id", ""))
        f["id"] = (fid.replace("EZ4-REV-", "BW-REV-").replace("EZ-F-", "BW-F-")
                   .replace("EZ-", "BW-"))
    merged = {"board": "BW", "generated_utc": flagged.get("generated_utc"), "flags": all_flags}
    json.dump(merged, open(os.path.join(DATA, "flagged.json"), "w"), indent=1, ensure_ascii=False)

    lines = ["# Board BW — line-by-line review", "",
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

    rr_sum = out["repo_review"]["datasets"]
    print(f"[board-bw] review: rows={len(rows)} preds={len(texts)} "
          f"hard_fails={len(out['hard_failures'])} warns={len(out['warnings'])} "
          f"repo_defects={len(rr['defects'])} "
          f"(master {rr_sum['data/master.json']['summary']['with_defects']}/"
          f"{rr_sum['data/master.json']['rows']} rows, "
          f"predictions.json issues={rr_sum['data/predictions.json']['issues']})")
    for f in out["hard_failures"][:20]:
        print("  FAIL", f)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
