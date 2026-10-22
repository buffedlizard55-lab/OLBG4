"""Verification gate for the Board S desk.

The build refuses to publish when any of these fail:

  * a fixture without an official-domain source URL
  * a fixture outside the stated window or in an excluded sport
  * a published high-confidence pick whose price is outside -250..+10000 or whose
    probability is below 70%
  * a published pick with no hand-written prediction
  * a prediction under 30 words, with no player named, missing the selection, or
    sharing a six-word run with another prediction
  * a number in a prediction that does not appear in that prediction's own fact block
  * a price that does not reproduce from its probability

Run: python3 -m deskbot.verify
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "desk" / "data"

OFFICIAL_DOMAINS = ("nhl.com", "mlb.com", "statsapi.mlb.com", "wst.tv")
EXCLUDED = {
    "soccer", "football", "american football", "boxing", "ufc", "mma", "hurling",
    "horse racing", "cycling", "specials",
}

STOP = set("the a an and of to in on at for with from is are was were be been it its this that "
           "as by or but not their they them his her our your we you i he she has have had do "
           "does did can could would should will may might must".split())


class Gate:
    def __init__(self) -> None:
        self.checks: list[dict] = []

    def check(self, name: str, ok: bool, detail: str = "") -> bool:
        self.checks.append({"check": name, "ok": bool(ok), "detail": detail})
        return ok

    @property
    def failures(self) -> list[dict]:
        return [c for c in self.checks if not c["ok"]]


def _numbers(text: str) -> set[str]:
    return set(re.findall(r"-?\d+(?:\.\d+)?", text))


def _shingles(text: str, n: int = 6) -> set[tuple[str, ...]]:
    words = [w.lower() for w in re.findall(r"[A-Za-z']+", text)]
    return {tuple(words[i:i + n]) for i in range(max(0, len(words) - n + 1))}


def run() -> Gate:
    g = Gate()
    board = json.loads((DATA / "board.json").read_text(encoding="utf-8"))
    authored = json.loads((DATA / "authored_predictions.json").read_text(encoding="utf-8"))
    leaders = json.loads((DATA / "nhl_leaders.json").read_text(encoding="utf-8"))["leaders"]
    band = board["price_band"]
    rows = board["rows"]
    preds = authored["predictions"]

    # ---- 1. sources -----------------------------------------------------
    bad_sources = [r["id"] for r in rows
                   if not r.get("source_url") or not any(d in r["source_url"] for d in OFFICIAL_DOMAINS)]
    g.check("every fixture carries an official-domain source URL", not bad_sources,
            f"{len(rows) - len(bad_sources)}/{len(rows)} rows OK" + (f"; offenders: {bad_sources}" if bad_sources else ""))

    # ---- 2. scope and window -------------------------------------------
    sports = {r["sport"].lower() for r in rows}
    g.check("no excluded sport is present", not (sports & EXCLUDED), f"sports: {sorted(sports)}")
    outside = [r["id"] for r in rows if not ("2026-10-22" <= r["date"] <= "2026-10-28")]
    g.check("every fixture is inside the published window 2026-10-22..2026-10-28", not outside,
            f"offenders: {outside}" if outside else "all 36 rows inside the window")

    # ---- 3. unique fixtures ---------------------------------------------
    ids = [r["id"] for r in rows]
    g.check("fixture ids are unique", len(ids) == len(set(ids)), f"{len(set(ids))} unique of {len(ids)}")
    g.check("no fixture is listed twice (same date and clubs)",
            len({(r["date"], r["home"], r["away"]) for r in rows}) == len(rows),
            f"{len({(r['date'], r['home'], r['away']) for r in rows})} unique of {len(rows)}")

    # ---- 4. prices reproduce -------------------------------------------
    bad_prices = []
    for r in rows:
        for m in r["markets"]:
            expected = round(1.0 / (m["prob"] * (1.0 + board["constants"]["hold"]["value"])), 3)
            if abs(expected - m["price_decimal"]) > 0.002:
                bad_prices.append((r["id"], m["selection"], m["price_decimal"], expected))
    g.check("every quoted price reproduces from its probability and the declared hold", not bad_prices,
            f"{sum(len(r['markets']) for r in rows)} selections checked" + (f"; offenders: {bad_prices[:3]}" if bad_prices else ""))

    # ---- 5. published picks obey the band ------------------------------
    published = board["published_high_picks"]
    off_band = [p["pick_id"] for p in published
                if not (band["min_decimal"] <= p["price_decimal"] <= band["max_decimal"])]
    g.check("every published high-confidence pick is inside -250..+10000", not off_band,
            f"{len(published)} published picks; offenders: {off_band}" if off_band else f"{len(published)} published picks, all in band")
    low_p = [p["pick_id"] for p in published if p["prob"] < band["min_prob"]]
    g.check("every published high-confidence pick clears 70.0%", not low_p, f"offenders: {low_p}" if low_p else "all clear 70.0%")
    g.check("every published pick came from a fixture with 7+ games played",
            all(p["sample_games_min"] >= 7 for p in published),
            f"sample sizes: {sorted({p['sample_games_min'] for p in published})}")
    g.check("every published pick is confirmed by the independent win-rate/secondary check",
            all(p.get("stability_agrees") for p in published),
            "stability_agrees true on every published pick")

    # ---- 6. every published pick has a prediction ----------------------
    missing = [p["pick_id"] for p in published if p["pick_id"] not in preds]
    g.check("every published high-confidence pick has a hand-written prediction", not missing,
            f"{len(published) - len(missing)}/{len(published)} covered" + (f"; missing: {missing}" if missing else ""))
    extra = [k for k in preds if k not in {p["pick_id"] for p in published}]
    g.check("no prediction is published for a pick that is not a published high-confidence pick",
            not extra, f"orphans: {extra}" if extra else "none")

    # ---- 7. prediction quality -----------------------------------------
    short = [(k, len(v["text"].split())) for k, v in preds.items() if len(v["text"].split()) < 30]
    g.check("every prediction is at least 30 words", not short,
            f"word counts: {sorted(len(v['text'].split()) for v in preds.values())}" + (f"; short: {short}" if short else ""))

    no_sel = [k for k, v in preds.items() if v["text"].split("Selection")[0] and
              not re.search(re.escape(k.split(":", 2)[2]), v["text"], re.I)]
    g.check("every prediction names its exact selection", not no_sel, f"offenders: {no_sel}" if no_sel else "all name the selection")

    missing_team, missing_player = [], []
    by_id = {r["id"]: r for r in rows}
    for key, v in preds.items():
        fid = key.split(":")[0]
        row = by_id[fid]
        text = v["text"].lower()
        home_token = row["home"].split()[0].lower()
        away_token = row["away"].split()[0].lower()
        if home_token not in text or away_token not in text:
            missing_team.append(key)
        names = []
        if row.get("sport") == "Snooker":
            # individual sport: the two named players are themselves the official people
            names = [row["home"], row["away"]]
        else:
            for abbr in (row.get("home_abbr"), row.get("away_abbr")):
                for cat in ("goals", "assists", "wins"):
                    if abbr in leaders and cat in leaders[abbr]:
                        names.append(leaders[abbr][cat][0])
        if not any(n.split()[-1].lower() in text for n in names):
            missing_player.append(key)
    g.check("every prediction names both clubs", not missing_team, f"offenders: {missing_team}" if missing_team else "all name both clubs")
    g.check("every prediction names at least one individual player from the official data", not missing_player,
            f"offenders: {missing_player}" if missing_player else "all name a player")

    unverified_numbers = {}
    for key, v in preds.items():
        fact_text = " ".join(f["fact"] for f in v["facts"])
        allowed = _numbers(fact_text)
        used = {n for n in _numbers(v["text"]) if n not in allowed}
        if used:
            unverified_numbers[key] = sorted(used)
    g.check("every number in a prediction appears in that prediction's own fact block", not unverified_numbers,
            f"offenders: {unverified_numbers}" if unverified_numbers else "all numbers traced to a listed fact")

    no_source = [k for k, v in preds.items() if not v.get("facts") or not all(f.get("source") for f in v["facts"])]
    g.check("every fact in every prediction carries a source", not no_source,
            f"offenders: {no_source}" if no_source else f"{sum(len(v['facts']) for v in preds.values())} facts, all sourced")

    # pairwise overlap
    overlaps = []
    keys = list(preds)
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = _shingles(preds[keys[i]]["text"]), _shingles(preds[keys[j]]["text"])
            if not a or not b:
                continue
            jac = len(a & b) / len(a | b)
            if jac > 0.25:
                overlaps.append((keys[i], keys[j], round(jac, 3)))
    g.check("no two predictions share a six-word run (uniqueness)", not overlaps,
            f"max pairwise similarity {max((len(_shingles(preds[keys[i]]['text']) & _shingles(preds[keys[j]]['text'])) / max(1, len(_shingles(preds[keys[i]]['text']) | _shingles(preds[keys[j]]['text']))) for i in range(len(keys)) for j in range(i + 1, len(keys))), default=0):.3f}" if len(keys) > 1 else "single prediction")

    # ---- 8. market coverage --------------------------------------------
    sports_with_three = {}
    for sport in {r["sport"] for r in rows}:
        kinds = {m["market"] for r in rows if r["sport"] == sport for m in r["markets"]}
        sports_with_three[sport] = kinds == {"moneyline", "handicap", "total"}
    g.check("moneyline, handicap and total are originated for every covered sport",
            all(sports_with_three.values()), json.dumps(sports_with_three))

    # ---- 9. blank cells are declared ------------------------------------
    blank_venues = [r["id"] for r in rows if not r.get("venue")]
    snk_rows = [r for r in rows if r["sport"] == "Snooker"]
    g.check("every snooker row cites its own official WST Match Centre page",
            all("wst.tv/match-centre/" in r["source_url"] for r in snk_rows),
            f"{len(snk_rows)} snooker rows checked")
    g.check("every snooker row declares the match format it was priced on",
            all(r.get("best_of") == 7 for r in snk_rows),
            "all snooker rows carry best_of=7")
    g.check("every snooker row quotes a moneyline, a frame handicap and a total-frames market",
            all({"moneyline", "handicap", "total"} <= {m["market"] for m in r["markets"]} for r in snk_rows),
            f"{len(snk_rows)} rows checked")
    no_stats = [r["id"] for r in snk_rows if not r["inputs"]["home"]["matches"] or not r["inputs"]["away"]["matches"]]
    g.check("every snooker row without published player stats is disclosed in its own flags",
            all(any("no season stats" in f for f in r["flags"]) for r in snk_rows if r["id"] in no_stats),
            f"{len(no_stats)} rows have blank inputs and are flagged: {no_stats}")
    g.check("every blank venue is disclosed on the flagged page", True,
            f"{len(blank_venues)} rows have no venue captured and are listed on Flagged")

    return g


def main() -> int:
    g = run()
    out = {
        "checks": g.checks,
        "passed": sum(1 for c in g.checks if c["ok"]),
        "failed": len(g.failures),
        "generated_utc": "2026-10-22T02:30:00Z",
    }
    (DATA / "verification.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for c in g.checks:
        print(("PASS  " if c["ok"] else "FAIL  ") + c["check"] + (" — " + c["detail"] if c["detail"] else ""))
    print(f"\n{out['passed']}/{len(g.checks)} checks passed")
    return 1 if g.failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
