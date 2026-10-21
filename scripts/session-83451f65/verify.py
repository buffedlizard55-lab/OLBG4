#!/usr/bin/env python3
"""Line-by-line gate for the integrated build. Exits non-zero on any failure."""
import json, pathlib, re, sys
from urllib.parse import urlparse

ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "data" / "integrated"
E = json.loads((D / "entries.json").read_text())
P = json.loads((D / "predictions.json").read_text())
C = json.loads((D / "coverage.json").read_text())
F = json.loads((D / "findings.json").read_text())
S = json.loads((D / "sources.json").read_text())

OFFICIAL = set(S["official_domains"])
EXCLUDED = {"soccer", "football", "boxing", "ufc", "mma", "american football", "hurling",
            "horse racing", "cycling", "specials", "nfl"}
fails, warns, checks = [], [], []


def check(name, ok, detail=""):
    checks.append((name, bool(ok), detail))
    if not ok:
        fails.append(f"{name}: {detail}")


entries = E["entries"]
ids = [r["id"] for r in entries]
check("ids unique", len(ids) == len(set(ids)), f"{len(ids)} rows, {len(set(ids))} ids")

# 1. official source on every row
def host(u):
    return urlparse(u).netloc.lower().removeprefix("www.")

OFFICIAL_N = {h.removeprefix("www.") for h in OFFICIAL}
bad = [r["id"] for r in entries if host(r["source_url"]) not in OFFICIAL_N]
check("every row links to an official domain", not bad, f"{len(bad)} bad: {bad[:5]}")
check("no row links to OLBG", not any("olbg.com" in r["source_url"] for r in entries), "found olbg link")

# 2. exclusions
found = {r["sport"].lower() for r in entries} & EXCLUDED
check("no excluded sport in the dataset", not found, f"{found}")
blob = (D / "entries.json").read_text().lower()
check("no excluded sport named in entries.json", not any(f'"{s}"' in blob for s in EXCLUDED), "excluded sport string present")

# 3. picks / withheld honesty
withheld = [r for r in entries if not r["pick"]]
for r in withheld:
    st = r["markets"]["winner"]["status"]
    check(f"{r['id']} withheld pick has a reason", st.startswith("withheld"), st)
check("every pick is one of the two sides",
      all(r["pick"] in (r["home"], r["away"]) for r in entries if r["pick"]), "pick not a side")
check("every pick carries a price", all(str(r["pick_price"]).replace(".", "").isdigit() for r in entries if r["pick"]),
      "non-numeric price")
check("every priced pick sits between 1.01 and 30",
      all(1.01 <= float(r["pick_price"]) <= 30 for r in entries if r["pick"]), "out of range")

# 4. probability sanity
for r in entries:
    ph, pa = r["model_prob_home"], r["model_prob_away"]
    check(f"{r['id']} probabilities sum to 1", abs(ph + pa - 1) < 1e-6, f"{ph}+{pa}")
    check(f"{r['id']} probability inside [0.05,0.95]", 0.05 <= ph <= 0.95, str(ph))
    check(f"{r['id']} price is 1/(p*1.02)", abs(float(r["our_price_home"]) - round(1 / (ph * 1.02), 2)) <= 0.011,
          f'{r["our_price_home"]} vs {1/(ph*1.02):.3f}')

# 5. confidence coherence
for r in entries:
    n = min(len(re.findall(r"\d+-\d+", r["home_record"] or "")), 1)
    if r["confidence"] == "High":
        check(f"{r['id']} high grade has a large edge", abs(r["model_prob_home"] - 0.5) >= 0.18,
              str(r["model_prob_home"]))
        check(f"{r['id']} high grade has a strength input",
              r["strength_home"] is not None and r["strength_away"] is not None, "missing strength")
    if r["strength_home"] is None:
        check(f"{r['id']} no strength input cannot exceed Low", r["confidence"] == "Low", r["confidence"])

# 6. predictions
high = {r["id"] for r in entries if r["confidence"] == "High"}
pred_ids = [p["entry_id"] for p in P["predictions"]]
check("one write-up per high-confidence row", set(pred_ids) == high, f"preds {set(pred_ids)} vs high {high}")
check("no duplicate write-up", len(pred_ids) == len(set(pred_ids)), str(pred_ids))
texts = [p["text"] for p in P["predictions"]]
check("write-ups are unique", len(texts) == len(set(texts)), "duplicate text")
for p in P["predictions"]:
    r = next(x for x in entries if x["id"] == p["entry_id"])
    wc = len(p["text"].split())
    check(f"{p['entry_id']} write-up >= 30 words", wc >= 30, f"{wc} words")
    check(f"{p['entry_id']} names the selection", r["pick"].split()[-1] in p["text"], r["pick"])
    check(f"{p['entry_id']} names both sides",
          r["home"].split()[0] in p["text"] and r["away"].split()[0] in p["text"], "team missing")
    check(f"{p['entry_id']} cites at least two official facts",
          sum(1 for f in p["facts"] if host(f["url"]) in OFFICIAL_N) >= 2,
          f'{len(p["facts"])} facts')
    check(f"{p['entry_id']} price matches the model", str(p["our_price"]) == str(r["pick_price"]),
          f'{p["our_price"]} vs {r["pick_price"]}')
    for bad_word in ("TBD", "TODO", "lorem", "placeholder", "XXX"):
        check(f"{p['entry_id']} has no placeholder text", bad_word.lower() not in p["text"].lower(), bad_word)

# 7. coverage + findings completeness
sports = {s["sport"] for s in C["sports"]}
check("coverage lists every published sport", {r["sport"] for r in entries} <= sports, str(sports))
check("coverage has a source for every sport", all(s["source"].startswith("http") for s in C["sports"]), "missing url")
check("findings all carry links", all(f["links"] for f in F["items"]), "finding without link")
check("findings ids unique", len({f["id"] for f in F["items"]}) == len(F["items"]), "duplicate finding id")

# 8. html + links
pages = [ROOT / p for p in ["index.html", "entries.html", "predictions.html", "analysis.html", "coverage.html",
                            "flagged.html", "methodology.html", "sources.html", "archive.html"]] + \
        sorted((ROOT / "sports").glob("*.html"))
check("all pages exist", all(p.exists() for p in pages), "missing page")
link_re = re.compile(r'href="([^"#?]+)')
broken, scanned = [], 0
for p in pages:
    t = p.read_text()
    check(f"{p.name} has no TODO", "TODO" not in t, "TODO string")
    for href in link_re.findall(t):
        if href.startswith(("http", "mailto:", "#", "data:")):
            continue
        scanned += 1
        target = (p.parent / href).resolve()
        if not target.exists():
            broken.append((p.name, href))
check("no broken internal links", not broken, str(broken[:8]))
check("every page carries the disclaimer", all("not betting advice" in p.read_text() for p in pages), "missing disclaimer")
check("stylesheet exists", (ROOT / "assets" / "integrated.css").exists(), "no css")

# 9. row count printed on the site matches the data
check("dashboard shows the true row count", str(len(entries)) in (ROOT / "index.html").read_text(), "count missing")

print(f"{'PASS' if not fails else 'FAIL'}  {len(checks)} checks "
      f"({sum(1 for c in checks if c[1])} passed, {len(fails)} failed), {scanned} internal links scanned")
if fails:
    for f in fails[:40]:
        print("  FAIL", f)
    sys.exit(1)
print(f"  rows={len(entries)} sports={len(sports)} high={len(high)} predictions={len(P['predictions'])} "
      f"findings={len(F['items'])}")
