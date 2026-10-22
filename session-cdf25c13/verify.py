"""Gate for Board T. Fails (non-zero) on anything that would make the desk wrong or broken.

Checks
  * every row has a pick, an official source URL and a date inside the window
  * every High pick has a written prediction of at least 30 words, all texts unique
  * every published selection is inside the requested -250..+10,000 window
  * no excluded sport appears anywhere
  * predictions name the fixture and the selection
  * every local link in the rendered pages resolves
"""
from __future__ import annotations

import json
import os
import re
import sys

from .predictions import PREDICTIONS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "session-cdf25c13")
DATA = os.path.join(ROOT, "data", "session-cdf25c13")

OFFICIAL = ("nhl.com", "nba.com", "mlb.com", "unitedrugby.com")
EXCLUDED = {"Soccer", "Football", "American Football", "Boxing", "UFC", "MMA", "Hurling",
            "Horse Racing", "Cycling", "Specials", "Gaelic Football"}
FAILS: list[str] = []


def check(cond, msg):
    if not cond:
        FAILS.append(msg)


def words(t):
    return len(re.findall(r"[A-Za-z0-9'’\-]+", t))


def main() -> int:
    payload = json.load(open(os.path.join(DATA, "rows.json")))
    rows = payload["rows"]
    check(payload["window"] == ["2026-10-22", "2026-10-28"], "window header changed")
    check(len(rows) == 91, f"expected 91 rows, found {len(rows)}")

    seen_ids = set()
    for r in rows:
        check(r["id"] not in seen_ids, f"duplicate id {r['id']}")
        seen_ids.add(r["id"])
        check("2026-10-22" <= r["date"] <= "2026-10-28", f"{r['id']} outside the window")
        check(r["sport"] not in EXCLUDED, f"{r['id']} is an excluded sport ({r['sport']})")
        check(bool(r.get("source_url")), f"{r['id']} has no source URL")
        host = r["source_url"].split("//")[-1].split("/")[0]
        check(any(host == d or host.endswith("." + d) for d in OFFICIAL),
              f"{r['id']} source {host} is not an official league domain")
        check(bool(r.get("pick")), f"{r['id']} has no pick")
        if r.get("pick"):
            check(1.40 <= r["pick"]["decimal"] <= 101.00,
                  f"{r['id']} pick price {r['pick']['decimal']} is outside the window")
            check(r["window_ok"] is True, f"{r['id']} window flag is false")
            check(0 < r["pick"]["prob"] < 1, f"{r['id']} probability out of range")

    high = [r for r in rows if r["confidence"] == "High"]
    check(len(high) == 8, f"expected 8 High rows, found {len(high)}")
    check(set(p["id"] for p in rows if p["confidence"] == "High") == set(PREDICTIONS),
          "the set of High rows and the set of written predictions differ")

    texts = []
    for r in high:
        pred = PREDICTIONS.get(r["id"])
        check(pred is not None, f"{r['id']} is High but has no written prediction")
        if not pred:
            continue
        texts.append(pred["text"])
        n = words(pred["text"])
        check(n >= 30, f"{r['id']} prediction is only {n} words")
        check(pred["selection"] == r["pick"]["selection"],
              f"{r['id']} prediction names a different selection")
        check(pred["price"] == r["pick"]["american"],
              f"{r['id']} prediction price does not match the row")
        check(r["home"].split()[-1] in pred["text"] or r["away"].split()[-1] in pred["text"],
              f"{r['id']} prediction does not name either club")
        check(len(pred["facts"]) >= 4, f"{r['id']} has fewer than four cited facts")
        for _, _, url in pred["facts"]:
            check(url.startswith("https://"), f"{r['id']} fact URL is not https")
    # claims guard: the standings feed holds record, goals for/against, last ten and streak only,
    # so any league-wide superlative or home/road split in the prose would be unverified.
    banned = ("weakest", "strongest", "at home", "on the road", "top-six", "league's best",
              "best defensive", "worst defensive", "unbeaten", "record-breaking",
              "earlier in the week", "earlier this week", "last week", "last night",
              "salt lake city", "built on defence")
    venue_words = re.compile(r"\b(center|centre|arena|stadium|gardens?)\b", re.I)
    for r in high:
        pred = PREDICTIONS.get(r["id"])
        low = pred["text"].lower() if pred else ""
        for phrase in banned:
            if phrase in low:
                FAILS.append(f"{r['id']} contains unverifiable claim '{phrase}'")
        if pred and not r.get("venue") and venue_words.search(pred["text"]):
            FAILS.append(f"{r['id']} names a venue but the row has no verified venue")

    check(len(texts) == len(set(texts)), "two predictions are byte-identical")
    # crude near-duplicate guard: share of 3-grams
    def grams(t):
        w = re.findall(r"[a-z0-9']+", t.lower())
        return {tuple(w[i:i + 3]) for i in range(len(w) - 3)}
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            g1, g2 = grams(texts[i]), grams(texts[j])
            if g1 and g2:
                jac = len(g1 & g2) / len(g1 | g2)
                check(jac < 0.20, f"predictions {i} and {j} are near-duplicates ({jac:.2f})")

    # rendered pages
    pages = [f for f in os.listdir(OUT) if f.endswith(".html")]
    check(len(pages) >= 12, f"only {len(pages)} pages rendered")
    for f in pages:
        s = open(os.path.join(OUT, f)).read()
        check("<title>" in s and "</html>" in s, f"{f} is not a complete document")
        for m in re.finditer(r'(?:href|src)="([^"]+)"', s):
            u = m.group(1)
            if u.startswith(("http", "mailto:", "#")):
                continue
            t = u.split("#")[0]
            if t and not os.path.exists(os.path.join(OUT, t)):
                FAILS.append(f"{f} links to missing {t}")
    for f in ("index.html", "picks.html", "flagged.html", "coverage.html",
              "methodology.html", "verification.html", "sources.html", "markets.html"):
        check(f in pages, f"{f} was not rendered")

    if FAILS:
        print(f"FAIL — {len(FAILS)} problem(s)")
        for f in FAILS:
            print("  -", f)
        return 1
    print(f"OK — {len(rows)} rows, {len(high)} High with predictions, "
          f"{len(pages)} pages, all links local, all sources official, window clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
