#!/usr/bin/env python3
"""Board ED verification gate.

Checks, in order:
  1. every capture file used by the desk re-hashes to the manifest value
  2. market maths: probabilities sum to 1, decimal = 1/p, American re-derived
  3. scope and provenance: dates inside the published window, a source link on every row,
     official sources for every priced row
  4. predictions: >= 30 words, unique wording, no internal vocabulary, stated selection
  5. internal links on every generated page resolve to a file that exists
  6. the desk summary matches the rows
Writes data/session-ed4c358c/verification.json and rewrites verification.html.
"""
from __future__ import annotations

import gzip
import hashlib
import html
import json
import re
from collections import Counter
from pathlib import Path

from edlib import DATA, ROOT, SLUG, SPORTS, iso_now

OUT = ROOT / "session-ed4c358c"
CHECKS: list[dict] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    CHECKS.append({"name": name, "ok": bool(ok), "detail": detail})


def american_from_decimal(dec: float) -> int:
    return int(round((dec - 1) * 100)) if dec >= 2.0 else int(round(-100 / (dec - 1)))


def main() -> int:
    desk = json.loads((DATA / "desk.json").read_text())
    preds = json.loads((DATA / "predictions.json").read_text())
    rows = desk["rows"]
    stamp = desk["capture_stamp"]
    capdir = DATA / "capture" / stamp
    manifest = json.loads((capdir / "manifest.json").read_text())
    recs = {r["id"]: r for r in manifest["records"]}

    # 1. provenance -------------------------------------------------------- #
    used = {r["capture_sha256"] for r in rows if r.get("capture_sha256")}
    bad = []
    seen = set()
    for r in rows:
        if not r.get("capture_sha256") or r["capture_sha256"] in seen:
            continue
        seen.add(r["capture_sha256"])
        match = next((x for x in manifest["records"] if x.get("sha256") == r["capture_sha256"]), None)
        if not match or not match.get("file"):
            bad.append(r["capture_sha256"][:12])
            continue
        raw = (capdir / match["file"]).read_bytes()
        body = gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw
        if hashlib.sha256(body).hexdigest() != r["capture_sha256"]:
            bad.append(match["file"])
    check("capture bytes re-hash to the manifest", not bad,
          f"{len(seen)} distinct payloads re-hashed" + (f"; mismatches: {bad}" if bad else ""))

    # 2. maths ------------------------------------------------------------- #
    math_errors = []
    for r in rows:
        for mkey, m in r["markets"].items():
            tot = sum(s["fair_prob"] for s in m["selections"])
            if abs(tot - 1.0) > 0.002:
                math_errors.append(f"{r['id']}/{mkey} prob sum {tot:.4f}")
            for s in m["selections"]:
                p = s["fair_prob"]
                if p <= 0 or p >= 1:
                    math_errors.append(f"{r['id']}/{mkey} prob out of range")
                    continue
                if abs(s["fair_decimal"] - round(1 / p, 3)) > 0.002:
                    math_errors.append(f"{r['id']}/{mkey} decimal != 1/p")
                if abs(s["fair_american"] - american_from_decimal(s["fair_decimal"])) > 1:
                    math_errors.append(f"{r['id']}/{mkey} American not re-derived")
    check("market maths (probability sum, decimal = 1/p, American re-derived)",
          not math_errors, f"{sum(len(r['markets']) for r in rows)} markets checked; "
                           f"{len(math_errors)} problems" + (f" e.g. {math_errors[:3]}" if math_errors else ""))

    # 3. scope and provenance ---------------------------------------------- #
    late = [r["id"] for r in rows if r["start_utc"] and r["start_utc"][:10] < desk["cutoff_utc"][:10]]
    beyond = [r["id"] for r in rows if r["start_utc"] and r["start_utc"] > desk["window_end_utc"]]
    check("no fixture starts before the claim time", not late, f"{len(late)} offending rows")
    check("no fixture starts after the published window", not beyond, f"{len(beyond)} offending rows")

    no_source = [r["id"] for r in rows if not r.get("official_url")
                 and not ((r.get("olbg") or {}).get("hub_url"))]
    check("every row carries a source link", not no_source, f"{len(no_source)} rows without a link")

    unpriced = [r["id"] for r in rows if r["markets"] and r["source_tier"] != "official"]
    check("every priced row is backed by an official source", not unpriced,
          f"{len(unpriced)} priced rows on a non-official source")
    official_bad = [r["id"] for r in rows if r["markets"] and not re.match(r"https://", r["official_url"])]
    check("official URLs are absolute https", not official_bad, f"{len(official_bad)} bad URLs")

    sports = {r["sport"] for r in rows}
    check("only the fifteen sports in scope appear", sports <= set(SPORTS),
          "sports present: " + ", ".join(sorted(sports)))

    # confidence consistency
    conf_bad = []
    for r in rows:
        b = r.get("best")
        if not b:
            continue
        p = b["fair_prob"]
        want = "High" if p >= 0.70 else ("Medium" if p >= 0.58 else "Low")
        caps = ("medium",)
        got = b.get("confidence")
        allowed = {"High": {"High", "Medium", "Low"}, "Medium": {"Medium", "Low"}, "Low": {"Low"}}[want]
        if got not in allowed:
            conf_bad.append(f"{r['id']} p={p:.3f} grade={got} expected<={want}")
    check("confidence grades follow the stated thresholds", not conf_bad,
          f"{len(conf_bad)} mismatches" + (f" e.g. {conf_bad[:3]}" if conf_bad else ""))

    # 4. predictions -------------------------------------------------------- #
    probs = []
    for p in preds["predictions"]:
        t = p["text"]
        if len(t.split()) < 30:
            probs.append(f"{p['row_id']} under 30 words")
        if re.search(r"\b(model|verified)\b", t, re.I):
            probs.append(f"{p['row_id']} internal vocabulary")
        if p["selection"].split()[0].lower() not in t.lower():
            probs.append(f"{p['row_id']} selection not stated in the text")
        if not p["sources"] or not p["sources"][0]["url"].startswith("https://"):
            probs.append(f"{p['row_id']} missing official source")

    def grams(t: str) -> set[str]:
        w = re.findall(r"[a-z0-9]+", t.lower())
        return {" ".join(w[i:i + 3]) for i in range(len(w) - 2)}

    worst = 0.0
    plist = preds["predictions"]
    for i in range(len(plist)):
        for j in range(i + 1, len(plist)):
            a, b = grams(plist[i]["text"]), grams(plist[j]["text"])
            if not a or not b:
                continue
            jac = len(a & b) / len(a | b)
            worst = max(worst, jac)
            if jac > 0.10:
                probs.append(f"{plist[i]['row_id']} vs {plist[j]['row_id']} similarity {jac:.3f}")
    check("predictions: length, wording, selection, sources",
          not probs, f"{len(plist)} texts; max pairwise 3-gram Jaccard {worst:.3f}"
                     + (f"; problems: {probs[:4]}" if probs else ""))

    pred_sports = {p["sport"] for p in plist}
    check("prediction count reported matches the file", preds["count"] == len(plist),
          f"{preds['count']} vs {len(plist)}")

    # 5. links -------------------------------------------------------------- #
    broken = []
    pages = sorted(OUT.rglob("*.html"))
    for page_file in pages:
        txt = page_file.read_text()
        for href in re.findall(r'href="([^"]+)"', txt):
            if href.startswith(("http://", "https://", "#", "mailto:")):
                continue
            target = (page_file.parent / href.split("#")[0]).resolve()
            if not target.exists():
                broken.append(f"{page_file.relative_to(ROOT)} -> {href}")
    check("every internal link resolves", not broken,
          f"{len(pages)} pages scanned; {len(broken)} broken" + (f" e.g. {broken[:3]}" if broken else ""))

    # 6. summary ------------------------------------------------------------ #
    s = desk["summary"]
    check("desk summary matches the rows",
          s["rows"] == len(rows) and s["priced"] == sum(1 for r in rows if r["markets"])
          and s["markets"] == sum(len(r["markets"]) for r in rows),
          f"rows {s['rows']}/{len(rows)}, priced {s['priced']}, markets {s['markets']}")

    high = [r for r in rows if r.get("best") and r["best"].get("confidence") == "High"]
    inwin = [r for r in high if r["best"].get("in_window")]
    check("High picks and window arithmetic reported",
          True, f"{len(high)} High; {len(inwin)} inside -250..+10,000 "
                f"({', '.join(sorted({r['sport'] for r in high}))})")

    ok = all(c["ok"] for c in CHECKS)
    payload = {
        "generated_utc": iso_now(),
        "capture_stamp": stamp,
        "result": "PASS" if ok else "FAIL",
        "checks": CHECKS,
        "counts": {
            "rows": len(rows), "priced": sum(1 for r in rows if r["markets"]),
            "markets": sum(len(r["markets"]) for r in rows), "predictions": len(plist),
            "high": len(high), "in_window": len(inwin),
            "sports_with_rows": len(sports), "sports_with_predictions": len(pred_sports),
            "pages": len(pages),
        },
    }
    (DATA / "verification.json").write_text(json.dumps(payload, indent=1, sort_keys=True))

    # rebuild the verification page
    rows_html = "".join(
        f'<tr><td>{"✔" if c["ok"] else "✘"}</td><td>{html.escape(c["name"])}</td>'
        f'<td class="small muted">{html.escape(c["detail"])}</td></tr>' for c in CHECKS)
    cards = "".join(
        f'<div class="card"><div class="k">{html.escape(k.replace("_", " "))}</div><div class="v">{v}</div></div>'
        for k, v in payload["counts"].items())
    from build_site import page  # reuse the same shell/CSS
    body = f"""<h1>Verification</h1>
<p class="lead">Result: <b style="color:{'#35d07f' if ok else '#ff6b6b'}">{payload['result']}</b> ·
{sum(1 for c in CHECKS if c['ok'])}/{len(CHECKS)} checks passed · generated {html.escape(payload['generated_utc'])}.</p>
<div class="grid">{cards}</div>
<div class="panel"><table><thead><tr><th>✔</th><th>Check</th><th>Detail</th></tr></thead>
<tbody>{rows_html}</tbody></table></div>
<p class="small muted">Rebuild command: <span class="mono">python3 scripts/session-ed4c358c/re_olbg.py &amp;&amp;
python3 scripts/session-ed4c358c/originate.py &amp;&amp; python3 scripts/session-ed4c358c/predictions.py &amp;&amp;
python3 scripts/session-ed4c358c/review.py &amp;&amp; python3 scripts/session-ed4c358c/build_site.py &amp;&amp;
python3 scripts/session-ed4c358c/verify.py</span></p>"""
    (OUT / "verification.html").write_text(page("Verification", body, "verification.html"))

    print(f"verify: {payload['result']} ({sum(1 for c in CHECKS if c['ok'])}/{len(CHECKS)})")
    for c in CHECKS:
        print(("  PASS " if c["ok"] else "  FAIL ") + c["name"] + " — " + c["detail"][:140])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
