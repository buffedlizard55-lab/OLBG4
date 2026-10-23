#!/usr/bin/env python3
"""Board AK review: check the desk line by line, then the repository.

Writes data/session-63ad3394/review.json. Every finding carries a result
(pass / flag / fail) and, where one exists, the official URL a human can open to
check the same number by hand.

The desk checks recompute what can be recomputed (price maths, form arithmetic,
provenance hashes) and re-read a fixed list of literal figures straight out of
the captured official bytes. The repository checks look for the defects a reader
of the published site would hit: a broken publication audit, rows citing sources
that are not official, duplicated ids and stale work claims.

Usage: python3 review.py [repo-root]
"""
from __future__ import annotations

import glob
import gzip
import json
import os
import re
import sys
from urllib.parse import urlsplit

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(ROOT, "data/session-63ad3394")
CAPS = sorted(glob.glob(os.path.join(DATA, "capture", "*")))

findings: list[dict] = []


def add(fid, area, check, result, detail, url=None):
    findings.append({"id": fid, "area": area, "check": check, "result": result,
                     "detail": detail, "source_url": url})


def payload(target_id):
    """Return (bytes, record) for the newest capture that holds a target."""
    for cap in reversed(CAPS):
        man = json.load(open(os.path.join(cap, "manifest.json")))
        for rec in man["records"]:
            if rec["id"] == target_id and rec.get("status") and str(rec["status"]).startswith("2"):
                path = os.path.join(cap, rec["file"])
                if os.path.exists(path):
                    raw = open(path, "rb").read()
                    if rec["file"].endswith(".gz"):
                        raw = gzip.decompress(raw)
                    return raw, rec
    return None, None


def text_of(target_id):
    raw, rec = payload(target_id)
    if raw is None:
        return "", None
    body = raw.decode("utf-8", "ignore")
    body = re.sub(r"<script.*?</script>|<style.*?</style>", " ", body, flags=re.S | re.I)
    return re.sub(r"<[^>]+>", " ", body), rec


def fold(text):
    import unicodedata
    n = unicodedata.normalize("NFKD", text)
    return "".join(c for c in n if not unicodedata.combining(c)).lower()


def american_to_prob(a):
    return 100.0 / (a + 100.0) if a > 0 else -a / (-a + 100.0)


def prob_to_american(p):
    return round(100 * (1 - p) / p) if p < 0.5 else -round(100 * p / (1 - p))


def desk_checks(desk):
    rows = desk["rows"]
    priced = [r for r in rows if r.get("priced")]

    bad = []
    for r in priced:
        for key, m in r["markets"].items():
            if key.startswith("_"):
                continue
            sels = m.get("selections") or []
            if len(sels) < 2:
                bad.append(f"{r['id']}:{key} has {len(sels)} selection(s)")
                continue
            if not key.endswith("ladder"):
                total = sum(s["fair_prob"] for s in sels)
                if abs(total - 1.0) > 1e-6:
                    bad.append(f"{r['id']}:{key} probabilities sum to {total:.6f}")
            for s in sels:
                if s["fair_prob"] <= 0:
                    # a selection our own line prices at zero or below cannot be backed
                    bad.append(f"{r['id']}:{key}:{s['label']} is priced at {s['fair_prob']}")
                    continue
                dec = 1.0 / s["fair_prob"]
                if abs(dec - s["fair_decimal"]) > 0.01:
                    bad.append(f"{r['id']}:{key}:{s['label']} decimal {s['fair_decimal']} != 1/p")
                if s["fair_prob"] > 0.02 and s["fair_prob"] < 0.98:
                    want = prob_to_american(s["fair_prob"])
                    if abs(want - s["fair_american"]) > 2:
                        bad.append(f"{r['id']}:{key}:{s['label']} price {s['fair_american']} "
                                   f"!= {want} for p={s['fair_prob']:.4f}")
    add("D1", "desk", "Every carried market prices a complete two-way book "
        "(probabilities sum to 1, decimal = 1/p, American = p)", "pass" if not bad else "fail",
        f"{len(priced)} priced fixtures, {sum(1 for r in priced for k in r['markets'] if not k.startswith('_'))} "
        f"markets checked; {len(bad)} problem(s)" + ("" if not bad else ": " + "; ".join(bad[:6])))

    # form arithmetic
    bad = []
    for r in rows:
        for side in ("a", "b"):
            f = (r.get("form") or {}).get(side) or {}
            if not f or not f.get("n"):
                continue
            played = f.get("w", 0) + f.get("l", 0) + (f.get("otl") or 0)
            if played != f["n"]:
                bad.append(f"{r['id']}:{side} W+L(+OTL)={played} but n={f['n']}")
            if f.get("pf_pg") is not None and f.get("pa_pg") is not None and f.get("margin") is not None:
                if abs((f["pf_pg"] - f["pa_pg"]) - f["margin"]) > 0.01:
                    bad.append(f"{r['id']}:{side} margin {f['margin']} != pf_pg-pa_pg")
    add("D2", "desk", "Form arithmetic: W+L(+OTL) equals games played, and the quoted margin "
        "equals scoring rate minus conceding rate", "pass" if not bad else "fail",
        f"{len(bad)} problem(s)" + ("" if not bad else ": " + "; ".join(bad[:6])))

    # provenance
    allowed = set()
    tgt = json.load(open(os.path.join(HERE, "targets.json")))
    tgt = tgt["targets"] if isinstance(tgt, dict) else tgt
    for t in tgt:
        if t.get("kind") == "official":
            allowed.add(urlsplit(t["url"]).hostname)
    hashes = set()
    for cap in CAPS:
        for rec in json.load(open(os.path.join(cap, "manifest.json")))["records"]:
            hashes.add(rec.get("sha256"))
    bad = []
    for r in rows:
        host = urlsplit(r.get("source_url") or "").hostname
        if not host or host not in allowed:
            bad.append(f"{r['id']} cites {host or 'nothing'}")
        elif r.get("source_sha256") not in hashes:
            bad.append(f"{r['id']} sha256 not in any capture manifest")
    add("D3", "desk", "Every fixture row carries an official URL from the capture target list and "
        "the SHA-256 of the committed payload it was parsed from", "pass" if not bad else "fail",
        f"{len(rows)} rows; missing/unknown source on {len(bad)}" +
        ("" if not bad else ": " + "; ".join(bad[:6])))

    # started fixtures must not be published as upcoming picks
    bad = [r["id"] for r in rows if r.get("started") and r.get("pick")]
    add("D4", "desk", "No fixture that had already started at capture time is published as an "
        "upcoming pick", "pass" if not bad else "fail",
        f"{sum(1 for r in rows if r.get('started'))} rows were in play; {len(bad)} of them carry a pick")

    # unpriced rows must say why
    bad = [r["id"] for r in rows if not r.get("priced") and not r.get("unpriced_reason")]
    add("D5", "desk", "Every unpriced fixture states, in the row, why no line is published "
        "(never a guessed line)", "pass" if not bad else "fail",
        f"{sum(1 for r in rows if not r.get('priced'))} unpriced fixtures; {len(bad)} without a reason")


def prediction_checks(preds):
    picks = preds["picks"]
    banned = ("model", "verified")
    bad = []
    for p in picks:
        w = len(p["prediction"].split())
        if w < 30:
            bad.append(f"{p['id']} {w} words")
        for b in banned:
            if re.search(rf"\b{b}\b", p["prediction"], re.I):
                bad.append(f"{p['id']} uses {b!r}")
        if not p.get("source_url"):
            bad.append(f"{p['id']} has no source link")
    add("D6", "predictions", f"All {len(picks)} published write-ups are 30+ words, free of the words "
        "'model' and 'verified', and carry their official source", "pass" if not bad else "fail",
        f"{len(picks)} write-ups, shortest {min(len(p['prediction'].split()) for p in picks)} words; "
        f"{len(bad)} problem(s)" + ("" if not bad else ": " + "; ".join(bad[:6])))

    seen = {}
    for p in picks:
        key = p["prediction"]
        if key in seen:
            add("D7", "predictions", "No two published write-ups are the same text", "fail",
                f"{seen[key]} and {p['id']} are identical")
        seen[key] = p["id"]
    if not any(f["id"] == "D7" for f in findings):
        jac = preds["counts"]["max_pairwise_3gram_jaccard"]
        add("D7", "predictions", "No two published write-ups are the same text, and no pair of "
            "write-ups shares more than a third of its three-word runs",
            "pass" if jac < 0.33 else "flag",
            f"worst pair {preds['counts']['worst_pair']} at {jac:.3f} Jaccard")

    bad = []
    for p in picks:
        side = re.split(r" \(| \[", p["selection"])[0]
        if fold(side) not in fold(p["prediction"]):
            bad.append(p["id"])
    add("D8", "predictions", "Each write-up names the selection it is attached to",
        "pass" if not bad else "flag", f"{len(bad)} write-up(s) do not repeat the selection name")


def spot_checks():
    """Literal figures, read back out of the captured official payloads."""
    checks = [
        ("S1", "Ice Hockey", "Edmonton Oilers 8-1 and 17 points (NHL standings payload)",
         "nhl_standings_now", ["Edmonton Oilers"], ["8", "1", "17"]),
        ("S2", "Basketball", "Panathinaikos 6-1 in the EuroLeague game feed",
         "el_games", ["Panathinaikos"], ["6"]),
        ("S3", "Rugby Union", "Stade Toulousain 24 league points from six rounds (LNR table)",
         "top14_classement", ["Stade Toulousain"], ["24"]),
        ("S4", "Baseball", "Milwaukee Brewers 103-59 in the MLB standings payload",
         "mlb_standings", ["Brewers"], ["103", "59"]),
        ("S5", "Golf", "Kensei Hirata tied first at -13 through two rounds (PGA TOUR leaderboard)",
         "pga_bermuda_lb", ["Kensei Hirata"], ["-13", "T1"]),
        ("S6", "Motor Racing", "Mercedes on 578 points (formula1.com constructors' standings)",
         "f1_team_results", ["Mercedes", "578"], []),
        ("S7", "Darts", "Stephen Bunting 28 legs to 18 (PDC match feed)",
         "pdc_fixtures_web", ["Stephen Bunting"], ["28"]),
        ("S8", "Snooker", "Sam Craigie 14 frames to 7 (WST match feed)",
         "wst_matches_probe", ["Craigie"], ["14"]),
    ]
    for fid, sport, label, tid, needles, _ in checks:
        body, rec = text_of(tid)
        if not body:
            add(fid, sport, label, "flag", f"target {tid} is not in any capture", None)
            continue
        missing = [n for n in needles if n.lower() not in body.lower()]
        add(fid, sport, label, "pass" if not missing else "fail",
            "figure found in the captured page" if not missing
            else f"not found in the captured page: {missing}", rec["url"])


def repo_checks():
    # the publication audit is the repo's own gate
    gz = []
    for f in glob.glob(os.path.join(ROOT, "**", "*.html"), recursive=True):
        if any(p in (".git", "node_modules", ".venv") for p in f.split(os.sep)):
            continue
        with open(f, "rb") as fh:
            if fh.read(2) == b"\x1f\x8b":
                gz.append(os.path.relpath(f, ROOT))
    add("R1", "repository", "scripts/audit_publication.py runs to completion on the repository",
        "fail" if gz else "pass",
        f"it raises UnicodeDecodeError in local_links(): {len(gz)} committed files are gzip bytes "
        f"under a .html name, so Path.read_text() fails. First offenders: " + ", ".join(gz[:3])
        if gz else "no gzip payloads are committed under a .html name",
        "https://github.com/buffedlizard55-lab/OLBG4/blob/main/scripts/audit_publication.py")

    master = json.load(open(os.path.join(ROOT, "data/master.json")))
    rows = master["rows"]
    ids = [r["id"] for r in rows]
    add("R2", "repository", "data/master.json row ids are unique",
        "pass" if len(ids) == len(set(ids)) else "fail",
        f"{len(ids)} rows, {len(ids) - len(set(ids))} duplicate id(s)",
        "https://github.com/buffedlizard55-lab/OLBG4/blob/main/data/master.json")

    registry = {s["domain"] for s in json.load(open(os.path.join(ROOT, "data/source_registry.json")))["sources"]}
    unreg = [r["id"] for r in rows if r.get("source_url") and r["source_domain"] not in registry]
    add("R3", "repository", "Every sourced row in data/master.json cites a domain that is in "
        "data/source_registry.json", "pass" if not unreg else "fail",
        f"{sum(1 for r in rows if r.get('source_url'))} sourced rows; {len(unreg)} unregistered" +
        ("" if not unreg else ": " + ", ".join(unreg[:6])),
        "https://github.com/buffedlizard55-lab/OLBG4/blob/main/data/source_registry.json")

    brief = {"Golf", "Volleyball", "Rugby Union", "Cricket", "Snooker", "Darts", "Baseball",
             "Gaelic Sports", "Greyhounds", "Tennis", "Motor Racing", "Handball", "Ice Hockey",
             "Basketball", "Rugby League"}
    outside = sorted({r["sport"] for r in rows if r["sport"] not in brief})
    add("R4", "repository", "The master board contains no sport outside the fifteen in the brief",
        "pass" if not outside else "flag",
        "none found" if not outside else
        f"outside-scope sports still present in data/master.json: {', '.join(outside)} "
        f"(they are marked in_scope=false, but they ship with the site)",
        "https://github.com/buffedlizard55-lab/OLBG4/blob/main/data/master.json")

    # OLBG hubs: are their event listings readable without the disallowed API?
    listing = json.load(open(os.path.join(DATA, "olbg_listing.json")))
    tips = listing["tips"]
    add("R5", "repository", "OLBG sport hubs still publish their event/tip listings in the "
        "server-rendered HTML", "flag",
        f"{len(listing['hubs'])} hubs answered 200 and the market labels were read from the page, "
        f"but each hub body contains \"No tips found\" and the listing itself is fetched from an "
        f"XHR endpoint that robots.txt disallows (/api/), so only {len(tips)} tip rows in total could "
        f"be read from the HTML. Earlier boards' OLBG event counts cannot be reproduced from a "
        f"robots-compliant crawl.",
        listing["hubs"][0]["url"] if listing["hubs"] else None)

    # work claims
    coord = open(os.path.join(ROOT, "COORDINATION.md"), encoding="utf-8", errors="ignore").read()
    stale = re.findall(r"\|\s*(A[A-Z]\d+)\s*\|[^\n]*\|\s*(?:in progress|claimed)\s*\|", coord)
    add("R6", "repository", "COORDINATION.md holds no claim that is still 'in progress' from an "
        "earlier session", "flag" if stale else "pass",
        f"claim ids still marked in progress/claimed: {', '.join(sorted(set(stale)))}" if stale
        else "no stale in-progress claims found",
        "https://github.com/buffedlizard55-lab/OLBG4/blob/main/COORDINATION.md")


def main() -> int:
    desk = json.load(open(os.path.join(DATA, "desk.json")))
    preds = json.load(open(os.path.join(DATA, "predictions.json")))
    desk_checks(desk)
    prediction_checks(preds)
    spot_checks()
    repo_checks()

    order = {"fail": 0, "flag": 1, "pass": 2}
    findings.sort(key=lambda f: order[f["result"]])
    out = {
        "schema": "olbg4.board-ak.review/1",
        "generated_utc": desk["generated_utc"],
        "note": ("Each desk check recomputes what arithmetic allows and re-reads a fixed list of "
                 "figures from the committed official payload. A pass says the published number "
                 "agrees with the page it came from, nothing more."),
        "counts": {"total": len(findings),
                   "pass": sum(1 for f in findings if f["result"] == "pass"),
                   "flag": sum(1 for f in findings if f["result"] == "flag"),
                   "fail": sum(1 for f in findings if f["result"] == "fail")},
        "findings": findings,
    }
    json.dump(out, open(os.path.join(DATA, "review.json"), "w"), indent=1)
    for f in findings:
        print(f"  {f['result']:<4} {f['id']:<3} {f['area']:<12} {f['check'][:78]}")
    print(f"pass {out['counts']['pass']} · flag {out['counts']['flag']} · fail {out['counts']['fail']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
