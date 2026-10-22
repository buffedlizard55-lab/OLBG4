#!/usr/bin/env python3
"""Board AC verifier: every published claim re-derived from the committed data."""
from __future__ import annotations

import hashlib
import html
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
DATA = REPO / "data/session-1695b749/ac"
SITE = REPO / "session-1695b749/ac"
sys.path.insert(0, str(HERE))

import ac_model as M  # noqa: E402

FAILS: list[str] = []
CHECKS = 0


def check(name, cond, detail=""):
    global CHECKS
    CHECKS += 1
    if not cond:
        FAILS.append(f"{name}: {detail}")


def american(p):
    return M.american(p)


def main():
    desk = json.loads((DATA / "desk.json").read_text())
    ver = json.loads((DATA / "verification.json").read_text())
    cov = json.loads((DATA / "coverage.json").read_text())
    flags = json.loads((DATA / "flagged.json").read_text())
    listing = json.loads((DATA / "listing.json").read_text())
    sources = json.loads((DATA / "sources.json").read_text())
    review = json.loads((DATA / "review.json").read_text())
    spec = json.loads((DATA / "model_spec.json").read_text())
    authored = json.loads((DATA / "authored_predictions.json").read_text())["items"]

    fx = desk["fixtures"]
    t = desk["totals"]

    # ---- counts agree with the data ----
    check("fixture count", t["fixtures"] == len(fx))
    check("priced count", t["priced_fixtures"] == sum(1 for f in fx if f.get("priced") is not False))
    check("selection count", t["selections"] == sum(f["n_selections"] for f in fx))
    check("pick count", t["picks"] == sum(len(f.get("picks", [])) for f in fx))
    win = [(f, s) for f in fx for s in f.get("picks", []) if s["grade"] == "High" and s["in_window"]]
    check("in-window count", t["high_in_window"] == len(win))
    check("picks_in_window length", len(desk["picks_in_window"]) == len(win))
    for k in ("picks_high", "picks_medium", "picks_low"):
        got = sum(1 for f in fx for s in f.get("picks", []) if s["grade"] == k.split("_")[1].capitalize())
        check(f"{k} count", t[k] == got, f"{t[k]} != {got}")

    # ---- every fixture has an official source and a good hash ----
    cache = {}
    for f in fx:
        check(f"{f['id']} has a source", bool(f["sources"]))
        for s in f["sources"]:
            check(f"{f['id']} source is https", s["url"].startswith("https://"), s["url"])
            path = REPO / s["file"]
            check(f"{f['id']} source file exists", path.exists(), s["file"])
            if path.exists():
                if s["file"] not in cache:
                    cache[s["file"]] = hashlib.sha256(path.read_bytes()).hexdigest()
                check(f"{f['id']} source hash", cache[s["file"]] == s["sha256"], s["file"])

    # ---- model arithmetic re-derived ----
    for f in fx:
        if f.get("priced") is False:
            check(f"{f['id']} unpriced has no markets", not f["markets"])
            continue
        check(f"{f['id']} model sums to one", abs(f["model"]["home"] + f["model"]["away"] - 1) < 1e-9)
        for market, sels in f["markets"].items():
            for s in sels:
                check(f"{f['id']} price matches p", s["price"] == american(s["p"]), f"{s['price']} vs {american(s['p'])}")
                check(f"{f['id']} implied matches price", abs(s["implied"] - M.implied(s["price"])) < 0.0002)
                want = "High" if s["p"] >= 0.70 else ("Medium" if s["p"] >= 0.62 else "Low")
                check(f"{f['id']} grade rule", s["grade"] == want, f"{s['grade']} vs {want}")
                check(f"{f['id']} window flag", s["in_window"] == (-250 <= s["price"] <= 10000))
        for s in f["picks"]:
            check(f"{f['id']} pick is the best of its market", s["p"] == max(x["p"] for x in f["markets"][s["core_market"]]))
        # moneyline two-way consistency
        ml = {x["side"]: x["p"] for x in f["markets"]["moneyline"]}
        check(f"{f['id']} moneyline complements", abs(ml["home"] + ml["away"] - 1) < 0.02, f"{ml}")

    # ---- predictions ----
    def tokens(text):
        return text.lower().split()

    texts = [a["text"] for a in authored]
    check("prediction count matches", len(texts) == len(win), f"{len(texts)} vs {len(win)}")
    for a in authored:
        check(f"{a['fixture']} words >= 30", a["words"] >= 30, str(a["words"]))
        check(f"{a['fixture']} words counted right", a["words"] == len(a["text"].split()))
        check(f"{a['fixture']} names the selection", a["selection"].split()[0].lower() in a["text"].lower()
              or (a["selection"] == "Under" and "under" in a["text"].lower())
              or (a["selection"] == "Over" and "over" in a["text"].lower()), a["selection"])
        f = next((x for x in fx if x["id"] == a["fixture"]), None)
        check(f"{a['fixture']} exists", f is not None)
        if f:
            match = [s for s in f["picks"] if s["market"] == a["market"] and s["line"] == a["line"] and s["selection"] == a["selection"]]
            check(f"{a['fixture']} prediction matches a pick", len(match) == 1)
            if match:
                check(f"{a['fixture']} prediction pick is High in window", match[0]["grade"] == "High" and match[0]["in_window"])
                check(f"{a['fixture']} pick carries text", match[0].get("write_up") == a["text"])
    def shingles(text):
        w = tokens(text)
        return {tuple(w[i:i + 8]) for i in range(len(w) - 7)}
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            shared = shingles(texts[i]) & shingles(texts[j])
            check(f"unique write-ups {i}/{j}", not shared, " ".join(next(iter(shared))) if shared else "")

    # ---- scope ----
    excluded = ["soccer", "boxing", "ufc", "mma", "american football", "hurling", "horse racing", "cycling", "specials"]
    for f in fx:
        low = (f["sport"] + " " + f["competition"]).lower()
        check(f"{f['id']} not excluded", not any(w in low for w in excluded), f["sport"])
    for r in listing["rows"]:
        check(f"listing {r['event'][:20]} not excluded", not any(w in r["sport"].lower() for w in excluded))
        check(f"listing {r['event'][:20]} blank source", r["official_source"] == "" and r["price"] == "" and r["pick"] == "")
        check(f"listing {r['event'][:20]} unverified", r["status"] == "unverified")

    # ---- coverage ----
    check("coverage labels", len(cov["rows"]) == 19, str(len(cov["rows"])))
    check("coverage priced labels", cov["summary"]["priced_labels"] == sum(1 for r in cov["rows"] if r["priced"]))
    priced_sports = {f["sport"] for f in fx if f.get("priced") is not False}
    check("priced labels match fixtures", {r["sport"] for r in cov["rows"] if r["priced"]} == priced_sports,
          str(priced_sports))

    # ---- flags and sources ----
    check("flag ids unique", len({i["id"] for i in flags["items"]}) == len(flags["items"]))
    for i in flags["items"]:
        check(f"{i['id']} has a source", bool(i["sources"]))
        check(f"{i['id']} source is a url", all(u.startswith("https://") for u in i["sources"]))
    for s in sources["sources"]:
        check(f"source {s['url'][:40]} hash", len(s["sha256"]) == 64)

    # ---- register ----
    check("register rows", len(ver["rows"]) == len(fx))
    check("register ids", [r["id"] for r in ver["rows"]] == [f["id"] for f in fx])
    for r in ver["rows"]:
        check(f"register {r['id']} fields", len(r["fields"]) >= 3)
        for x in r["fields"]:
            check(f"register {r['id']} field source", x["source"].startswith("https://"), x["source"])
            check(f"register {r['id']} field hash", len(x["sha256"]) == 64)
        check(f"register {r['id']} not_checked listed", len(r["not_checked"]) == 5)

    # ---- review ----
    check("review covers the repo", review["totals"]["files"] > 800, str(review["totals"]["files"]))
    failed = [(f["path"], c["name"]) for f in review["files"] for c in f["checks"] if not c["ok"]]
    mine = [x for x in failed if x[0].startswith(("session-1695b749/ac/", "data/session-1695b749/ac/", "scripts/session-1695b749/ac_"))]
    check("no failures on this board's own files", not mine, str(mine))
    flag_text = " ".join(u for i in flags["items"] for u in i["sources"])
    orphans = [x for x in failed if not any(part in flag_text for part in [x[0].split("/")[0], x[0]])]
    check("every review failure is published in a flag", not orphans, str(orphans))

    # ---- HTML ----
    pages = sorted(SITE.glob("*.html")) + sorted((SITE / "sports").glob("*.html"))
    check("page count", len(pages) >= 13, str(len(pages)))
    ids = {}
    for p in pages:
        text = p.read_text()
        check(f"{p.name} doctype", text.lstrip().lower().startswith("<!doctype html>"))
        check(f"{p.name} closes html", "</html>" in text)
        check(f"{p.name} no localhost call", "http://localhost" not in text and "https://localhost" not in text and "127.0.0.1" not in text)
        check(f"{p.name} no placeholder", "TODO" not in text and "lorem ipsum" not in text.lower())
        ids[p] = set(re.findall(r'id="([^"]+)"', text))
    # internal links and fragment targets
    for p in pages:
        text = p.read_text()
        for href in re.findall(r'href="([^"]+)"', text):
            if href.startswith(("http://", "https://", "mailto:")):
                continue
            target, _, frag = href.partition("#")
            dest = (p.parent / target).resolve() if target else p.resolve()
            check(f"{p.name} link target exists", dest.exists(), href)
            if frag and dest.exists() and dest.suffix == ".html":
                dest_text = dest.read_text()
                check(f"{p.name} fragment {frag}", f'id="{frag}"' in dest_text, href)
    # pages carry the published numbers
    picks_html = (SITE / "picks.html").read_text()
    for s in [x for f in fx for x in f.get("picks", []) if x["grade"] == "High" and x["in_window"]]:
        implied = abs(s["price"]) / (abs(s["price"]) + 100.0) if s["price"] < 0 else 100.0 / (s["price"] + 100.0)
        check(f"{s['selection']} window price implies > 69%", implied > 0.69, f"{implied:.3f}")
        check(f"{s['selection']} in window price >= -250", s["price"] >= -250)
    check("picks page cards", picks_html.count('class="pick"') == len(win), str(picks_html.count('class="pick"')))
    listing_html = (SITE / "listing.html").read_text()
    check("listing page rows", listing_html.count("<tr>") >= len(listing["rows"]))
    check("verification page rows", (SITE / "verification.html").read_text().count("<tr id=") == len(ver["rows"]))
    check("flagged page items", (SITE / "flagged.html").read_text().count('class="card"') >= len(flags["items"]))

    # ---- data files parse and are deterministic ----
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in DATA.glob("*.json")}
    subprocess.run([sys.executable, str(HERE / "ac_build.py")], check=True, capture_output=True)
    after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in DATA.glob("*.json")}
    check("rebuild is byte-identical", before == after,
          ", ".join(sorted(k for k in before if before[k] != after.get(k))))

    print(json.dumps({"assertions": CHECKS, "failures": len(FAILS),
                      "fixtures": len(fx), "priced": t["priced_fixtures"],
                      "high_in_window": len(win), "predictions": len(authored),
                      "pages": len(pages)}, indent=1))
    for f in FAILS[:40]:
        print("FAIL", f)
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
