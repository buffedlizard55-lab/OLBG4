#!/usr/bin/env python3
"""Board EC verification gate.

    python3 scripts/session-e0ca04cf/verify.py

Deterministic checks over the published data and pages.  Exit code 0 only when
every gate passes; the site must not be merged with a red gate.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data" / "session-e0ca04cf"
SITE = ROOT / "session-e0ca04cf"
SPORTS = ["Golf", "Volleyball", "Rugby Union", "Cricket", "Snooker", "Darts", "Baseball",
          "Gaelic Sports", "Greyhounds", "Tennis", "Motor Racing", "Handball", "Ice Hockey",
          "Basketball", "Rugby League"]
SLUG = {"Golf": "golf", "Volleyball": "volleyball", "Rugby Union": "rugby-union", "Cricket": "cricket",
        "Snooker": "snooker", "Darts": "darts", "Baseball": "baseball", "Gaelic Sports": "gaelic-sports",
        "Greyhounds": "greyhounds", "Tennis": "tennis", "Motor Racing": "motor-racing",
        "Handball": "handball", "Ice Hockey": "ice-hockey", "Basketball": "basketball",
        "Rugby League": "rugby-league"}

PASS, FAIL = [], []


def gate(name: str, ok: bool, detail: str = "") -> None:
    (PASS if ok else FAIL).append(f"{name}{(' — ' + detail) if detail else ''}")


def dec_from_p(p: float) -> float:
    return round(1.0 / min(max(p, 0.0001), 0.9999), 2)


def dec_to_american(d: float) -> int:
    return int(round((d - 1) * 100)) if d >= 2 else int(round(-100 / (d - 1)))


def main() -> int:
    desk = json.loads((DATA / "desk.json").read_text())
    preds = json.loads((DATA / "predictions.json").read_text())
    review = json.loads((DATA / "review.json").read_text())
    rows = desk["rows"]

    # ---------------------------------------------------------------- coverage
    sports = sorted({r["sport"] for r in rows})
    gate("the desk only contains in-scope sports", set(sports) <= set(SPORTS),
         f"{sorted(set(sports) - set(SPORTS))}")
    empty = [s for s in SPORTS if s not in sports]
    review_text = json.dumps(review, ensure_ascii=False)
    unexplained = [s for s in empty if s not in review_text]
    gate("every in-scope sport either has rows or a published reason for having none",
         not unexplained, ", ".join(unexplained))
    gate("no sport page is missing its capture note",
         all(desk.get("sport_notes", {}).get(s) for s in SPORTS),
         ", ".join(s for s in SPORTS if not desk.get("sport_notes", {}).get(s)))

    # ------------------------------------------------------------------ prices
    bad_math, bad_range, bad_band, half_line = [], [], [], []
    for r in rows:
        markets = r.get("markets") or {}
        for mname, mk in markets.items():
            probs = 0.0
            for s in mk.get("selections", []):
                p = s["p"]
                if not (0 < p < 1):
                    bad_range.append(f"{r['id']} {s['name']} p={p}")
                probs += p
            two_way = "3-way" not in (mk.get("note") or "")
            if two_way and abs(probs - 1.0) > 0.002:
                half_line.append(f"{r['id']} {mname} sums to {probs:.3f}")
        pick = r.get("pick")
        if pick:
            if not (1.40 <= pick["decimal"] <= 101.0):
                bad_band.append(f"{r['id']} {pick['decimal']}")
            if pick["p"] < 0.50:
                bad_band.append(f"{r['id']} p={pick['p']}")
            if abs(pick["decimal"] - dec_from_p(pick["p"])) > 0.011:
                bad_math.append(f"{r['id']} pick decimal")
            if pick["american"] != dec_to_american(pick["decimal"]):
                bad_math.append(f"{r['id']} pick american")
            sel = next((s for s in markets.get(pick["market"], {}).get("selections", [])
                        if s["name"] == pick["selection"]), None)
            if sel is None:
                bad_math.append(f"{r['id']} pick absent from its market")
            elif abs(sel["p"] - pick["p"]) > 1e-9:
                bad_math.append(f"{r['id']} pick price != market price")
    gate("every selection probability is in (0,1)", not bad_range, "; ".join(bad_range[:3]))
    gate("every two-way market sums to 1.000", not half_line, "; ".join(half_line[:3]))
    gate("decimal and American odds re-derive from p", not bad_math, "; ".join(bad_math[:3]))
    gate("every published pick sits inside -250…+10,000 and is at least evens-shot (50%)", not bad_band,
         "; ".join(bad_band[:3]))

    # ------------------------------------------------------------- confidence
    order = {"Low": 0, "Medium": 1, "High": 2}
    bad_conf = []
    for r in rows:
        pick = r.get("pick")
        if not pick:
            continue
        p = pick["p"]
        base = "High" if p >= 0.70 else ("Medium" if p >= 0.55 else "Low")
        if order[pick["confidence"]] > order[base]:
            bad_conf.append(f"{r['id']} {pick['confidence']} at p={p:.3f}")
    gate("no confidence label is higher than the probability supports", not bad_conf,
         "; ".join(bad_conf[:3]))

    # ------------------------------------------------------------------ sources
    no_source = [r["id"] for r in rows
                 if r.get("pick") and not r.get("source_url", "").startswith("https://")]
    gate("every priced row links an https source", not no_source, ", ".join(no_source[:3]))
    untraced = [r["id"] for r in rows if r.get("source_url") and not r.get("source_id")]
    gate("every sourced row names the capture payload it came from", not untraced,
         ", ".join(untraced[:3]))
    unpriced_unflagged = [r["id"] for r in rows if not r.get("pick") and not r.get("flags")]
    gate("every unpriced row explains itself", not unpriced_unflagged,
         ", ".join(unpriced_unflagged[:3]))

    # -------------------------------------------------------------- predictions
    short = [k for k, v in preds.items() if len(v["text"].split()) < 30]
    gate("every written prediction is at least 30 words", not short, ", ".join(short[:3]))
    banned = [k for k, v in preds.items()
              if re.search(r"\b(model|verified)\b", v["text"], re.I)]
    gate("no prediction uses the internal words 'model' or 'verified'", not banned, ", ".join(banned[:3]))
    notsel = [k for k, v in preds.items() if v["selection"].lower() not in v["text"].lower()]
    gate("every prediction names its selection verbatim", not notsel, ", ".join(notsel[:3]))
    missing_row = [k for k in preds if k not in {r["id"] for r in rows}]
    gate("every prediction attaches to a published row", not missing_row, ", ".join(missing_row[:3]))

    def toks(t):
        return set(re.findall(r"[a-z0-9]+", t.lower()))

    worst, pair = 0.0, ""
    keys = list(preds)
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = toks(preds[keys[i]]["text"]), toks(preds[keys[j]]["text"])
            s = len(a & b) / max(1, len(a | b))
            if s > worst:
                worst, pair = s, f"{keys[i]}/{keys[j]}"
    gate("no two predictions are near-duplicates (Jaccard ≤ 0.55)", worst <= 0.55, f"worst {worst:.2f} {pair}")

    # ------------------------------------------------------------------- pages
    pages = {p.name: p.read_text() for p in SITE.glob("*.html")}
    gate("site has a page per sport plus the nine desk pages", len(pages) == 24, f"{len(pages)} pages")
    for sport in SPORTS:
        gate(f"{sport} page exists", f"{SLUG[sport]}.html" in pages)
    index = pages.get("index.html", "")
    missing_nav = [s for s in SPORTS if f'href="{SLUG[s]}.html"' not in index]
    gate("overview links every sport page", not missing_nav, ", ".join(missing_nav))

    # links
    broken = []
    for name, html in pages.items():
        for href in re.findall(r'href="([^"]+)"', html):
            if href.startswith(("http://", "https://", "#", "mailto:")):
                continue
            target = (SITE / href.split("#")[0]) if not href.startswith("/") else None
            if target is None or not target.exists():
                broken.append(f"{name}->{href}")
    gate("no broken local links", not broken, ", ".join(broken[:5]))

    # every table row in a data table must carry a link
    for page in ("entries.html", "picks.html", "sources.html", "flagged.html"):
        html = pages.get(page, "")
        body = "".join(re.findall(r"<tbody>(.*?)</tbody>", html, re.S))
        rows_html = re.findall(r"<tr>(.*?)</tr>", body, re.S)
        bare = [r for r in rows_html if "href=" not in r]
        gate(f"{page}: every table row carries a link", not bare,
             f"{len(rows_html) - len(bare)}/{len(rows_html)}" + (f"; e.g. {bare[0][:120]}" if bare else ""))

    # --------------------------------------------------------------- manifest
    man = desk["manifest"]
    gate("capture manifest is recorded", bool(man.get("ok")), f"{man.get('ok')} responses")
    gate("every stored payload has a SHA-256", all(r.get("sha256") for r in man.get("records", [])))
    gate("failed targets are published, not hidden", isinstance(man.get("failures"), list),
         f"{len(man.get('failures') or [])} logged")
    gate("review findings are published with a source", all(f.get("source") for f in review["findings"]),
         f"{len(review['findings'])} findings")

    # ------------------------------------------------------------------ report
    for p in PASS:
        print("PASS", p)
    for f in FAIL:
        print("FAIL", f)
    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
