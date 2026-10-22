#!/usr/bin/env python3
"""Board AD verifier: re-derives every published number from board.json, re-hashes
every payload, checks predictions and internal links. Exit 0 = PASS.
Run: python3 scripts/session-7c581d22/verify.py (after build.py + render.py)"""
import gzip, hashlib, json, os, re, sys

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
D = os.path.join(ROOT, "data", "session-7c581d22")
S = os.path.join(ROOT, "session-7c581d22")
errs = []
def chk(cond, msg):
    if not cond: errs.append(msg)

B = json.load(open(os.path.join(D, "board.json")))
rows = B["rows"]; R = {r["id"]: r for r in rows}
EXCLUDED = {"soccer", "football", "boxing", "ufc", "mma", "american football", "hurling",
            "horse racing", "cycling", "specials"}

def dec(p): return round(1.0 / p, 2)
def amer(p):
    d = 1.0 / p
    return int(round(-100 / (d - 1))) if d < 2 else int(round((d - 1) * 100))
def check_price(obj, ctx):
    chk(abs(obj["decimal"] - dec(obj["p"])) < 0.011, f"{ctx}: decimal {obj['decimal']} != 1/p for p={obj['p']}")
    chk(obj["american"] == amer(obj["p"]), f"{ctx}: american {obj['american']} != {amer(obj['p'])} for p={obj['p']}")
    chk(0 < obj["p"] < 1, f"{ctx}: p out of range {obj['p']}")

chk(len(R) == len(rows), "duplicate row ids")
for r in rows:
    ctx = r["id"]
    chk(r["sport"].lower() not in EXCLUDED, f"{ctx}: excluded sport published")
    chk("2026-10-23" <= r["date"] <= "2026-11-05", f"{ctx}: date {r['date']} outside window")
    chk(r["source_url"].startswith("https://"), f"{ctx}: missing official source URL")
    chk("olbg.com" not in r["source_url"], f"{ctx}: OLBG used as fixture source")
    chk(bool(r["fixture"]) and bool(r["competition"]), f"{ctx}: blank fixture/competition")
    if r["status"] == "priced":
        chk(r["pick"] is not None and "moneyline" in r["markets"], f"{ctx}: priced without pick/moneyline")
        mm = r["markets"]["moneyline"]
        chk(abs(mm["a"]["p"] + mm["b"]["p"] - 1) < 0.002, f"{ctx}: moneyline probs do not sum to 1")
        check_price(mm["a"], ctx + " ML a"); check_price(mm["b"], ctx + " ML b")
        for k in ("puck_line", "run_line"):
            if k in r["markets"]:
                m = r["markets"][k]
                chk(abs(m["fav_minus"]["p"] + m["dog_plus"]["p"] - 1) < 0.002, f"{ctx}: {k} probs do not sum to 1")
                check_price(m["fav_minus"], ctx + " " + k); check_price(m["dog_plus"], ctx + " " + k)
        if "spread" in r["markets"]:
            m = r["markets"]["spread"]
            chk(abs(m["a"]["p"] + m["b"]["p"] - 1) < 0.002, f"{ctx}: spread probs do not sum to 1")
            check_price(m["a"], ctx + " spread"); check_price(m["b"], ctx + " spread")
            chk(abs(m["home_line"] * 2 - round(m["home_line"] * 2)) < 1e-9 and m["home_line"] % 1 != 0,
                f"{ctx}: spread line not a half-point {m['home_line']}")
        if "total" in r["markets"]:
            t = r["markets"]["total"]
            chk(abs(t["over"]["p"] + t["under"]["p"] - 1) < 0.002, f"{ctx}: total probs do not sum to 1")
            check_price(t["over"], ctx + " over"); check_price(t["under"], ctx + " under")
        p = r["pick"]
        check_price(p, ctx + " pick")
        want = "High" if p["p"] >= 0.70 else ("Medium" if p["p"] >= 0.58 else "Low")
        if r["sport"] == "Darts" and want == "High": want = "Medium"  # documented cap
        if r["sport"] == "Ice Hockey" and want == "High":
            if min(r["inputs"]["away"]["gp"], r["inputs"]["home"]["gp"]) < 8: want = "Medium"
        if r["sport"] == "Basketball" and want == "High":
            if min(r["inputs"]["away"]["gp"], r["inputs"]["home"]["gp"]) < 7: want = "Medium"
        chk(p["confidence"] == want, f"{ctx}: confidence {p['confidence']} != rule {want} (p={p['p']})")
        chk(p["in_focus_window"] == (-250 <= p["american"] <= 10000), f"{ctx}: window flag wrong")
    else:
        chk(r["pick"] is None and r["markets"] == {}, f"{ctx}: unpriced row carries prices/pick")
        chk(bool(r.get("unpriced_reason")), f"{ctx}: unpriced without reason")

# live spot-check anchors (L02): four 24-Oct NHL games read live this session
for gid, fa, fb, ven in [("2026020168", "Anaheim Ducks", "Philadelphia Flyers", "Xfinity Mobile Arena"),
                         ("2026020169", "Los Angeles Kings", "New Jersey Devils", "Prudential Center"),
                         ("2026020170", "San Jose Sharks", "Boston Bruins", "TD Garden"),
                         ("2026020171", "New York Rangers", "Ottawa Senators", "Canadian Tire Centre")]:
    r = R.get(f"AD-NHL-{gid}")
    chk(r is not None, f"L02 anchor missing: {gid}")
    if r: chk(r["side_a"] == fa and r["side_b"] == fb and r["venue"] == ven and r["date"] == "2026-10-24",
              f"L02 anchor mismatch: {gid} -> {r['fixture']} / {r['venue']} / {r['date']}")

# focus picks
preds = []
for f in B["focus_picks"]:
    ctx = f["prediction_key"]
    chk(f["p"] >= 0.70, f"{ctx}: focus p<0.70")
    chk(-250 <= f["american"] <= 10000, f"{ctx}: focus american outside window {f['american']}")
    check_price(f, ctx)
    r = R[f["row_id"]]
    t = f["prediction"]
    chk(len(t.split()) >= 30, f"{ctx}: prediction {len(t.split())} words <30")
    chk(r["side_a"] in t and r["side_b"] in t, f"{ctx}: prediction must name both sides")
    sel_team = f["selection"].replace(" (moneyline)", "").replace(" (match winner)", "") \
        .replace(" +1.5 (puck line)", "").replace(" +1.5 (run line)", "")
    chk(sel_team in t, f"{ctx}: prediction does not name the selection side")
    chk(any(k in t for k in ("Selection:", "Prediction:")), f"{ctx}: no explicit selection statement")
    if "+1.5" in f["selection"]: chk("+1.5" in t, f"{ctx}: handicap not stated in prediction")
    preds.append(t)
chk(len(set(preds)) == len(preds), "duplicate prediction text")
def words(t): return set(re.findall(r"[a-z0-9']+", t.lower()))
for i in range(len(preds)):
    for j in range(i + 1, len(preds)):
        a, b = words(preds[i]), words(preds[j])
        jac = len(a & b) / max(1, len(a | b))
        chk(jac < 0.55, f"predictions {i} and {j} too similar (Jaccard {jac:.2f})")

# high-outside list consistency
for h in B["high_shorter_than_minus250"]:
    r = R[h["row_id"]]
    chk(r["pick"] and r["pick"]["confidence"] == "High" and h["american"] < -250,
        f"high-outside inconsistent: {h['row_id']}")

# sources: re-hash payloads
SRC = json.load(open(os.path.join(D, "sources.json")))["sources"]
for s in SRC:
    if s.get("repo_file"):
        p = os.path.join(ROOT, s["repo_file"])
        chk(os.path.exists(p), f"source payload missing: {s['repo_file']}")
        if not os.path.exists(p): continue
        h = hashlib.sha256(gzip.open(p, "rb").read()).hexdigest() if p.endswith(".gz") \
            else hashlib.sha256(open(p, "rb").read()).hexdigest()
        chk(h == s["sha256"], f"hash drift for {s['name']}")

# coverage: every in-scope OLBG sport present, no excluded sport rows anywhere
olbg = json.load(open(os.path.join(ROOT, "data", "olbg-structure.json")))
in_scope = {s["name"] for s in olbg["sports_enumerated"] if s["in_scope"]}
cov = {c["sport"] for c in B["coverage"]}
chk(in_scope <= cov, f"coverage missing sports: {in_scope - cov}")

# site: files + internal links + published counts match data
expected_pages = {"index.html", "entries.html", "picks.html", "markets.html", "coverage.html",
                  "methodology.html", "sources.html", "verification.html", "flagged.html", "style.css"}
have = set(os.listdir(S))
chk(expected_pages <= have, f"missing pages: {expected_pages - have}")
for fn in have:
    if fn.endswith(".html"):
        body = open(os.path.join(S, fn), encoding="utf-8").read()
        for href in re.findall(r'href="([^"]+)"', body):
            if href.startswith("http") or href.startswith("#") or href.startswith("mailto:"): continue
            chk(href.split("#")[0] in have, f"{fn}: broken internal link {href}")
entries = open(os.path.join(S, "entries.html"), encoding="utf-8").read()
chk(entries.count("<tr>") >= len(rows), "entries.html row count below data rows")
picks = open(os.path.join(S, "picks.html"), encoding="utf-8").read()
for f in B["focus_picks"]:
    chk(f["prediction"].split(".")[0][:40] in picks.replace("&#x27;", "'") or
        f["selection"] in picks, f"picks.html missing card for {f['prediction_key']}")

print(f"rows={len(rows)} priced={sum(r['status']=='priced' for r in rows)} "
      f"unpriced={sum(r['status']=='unpriced' for r in rows)} focus={len(B['focus_picks'])} "
      f"high_outside={len(B['high_shorter_than_minus250'])} sources={len(SRC)}")
if errs:
    print(f"FAIL ({len(errs)} errors)")
    for e in errs: print(" -", e)
    sys.exit(1)
print("PASS — 0 errors")
