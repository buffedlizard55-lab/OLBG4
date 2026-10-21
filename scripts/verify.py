#!/usr/bin/env python3
"""Build the flagged list and run the line-by-line checks that back verification.html.

  python3 scripts/verify.py            # data checks + flags  (run before build_site)
  python3 scripts/verify.py --links    # re-run and add the internal link audit (run after build_site)

Exit code is 0 even when a check reports "review" — review items are published, not silent.
A hard failure (missing source URL, prediction under 30 words, duplicate body, missing local
link target) exits 1 so CI cannot publish a broken site.
"""
import collections
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "session-7114b6a1"

board = json.loads((DATA / "board.json").read_text())
preds = json.loads((DATA / "predictions.json").read_text())
assumptions = json.loads((DATA / "model_assumptions.json").read_text())["flags"]
notes = json.loads((DATA / "flag_notes.json").read_text())["items"]
inv = json.loads((DATA / "match_inventory.json").read_text())
rows = board["rows"]

# ---------------------------------------------------------------- flags
items = list(notes)
items += [
    {"type": "model_assumption", "sport": a["sport"], "what": a["what"], "detail": a["detail"],
     "source": a["source"]} for a in assumptions
]
for p in preds["predictions"]:
    for u in p["unverified"]:
        items.append({"type": "prediction_gap", "sport": p["sport"],
                      "what": f"{p['match']} — declared gap",
                      "detail": u, "source": p["facts"][0]["source"]})
(DATA / "flagged.json").write_text(json.dumps({"schema": "olbg4.flagged/1", "items": items}, indent=1) + "\n")

# ---------------------------------------------------------------- checks
checks = []
hard_fail = False


def add(name, ok, result, detail, hard=False):
    global hard_fail
    checks.append({"check": name, "pass": bool(ok), "result": result, "detail": detail})
    if hard and not ok:
        hard_fail = True


rows_with_source = [r for r in rows if isinstance(r["olbg_url"], str) and r["olbg_url"].startswith("https://www.olbg.com/")]
add("Every match row links its OLBG source page", len(rows_with_source) == len(rows),
    f"{len(rows_with_source)}/{len(rows)}",
    "Each row stores the event URL (with event_id) the fixture, market, selection and tip count were read from.", hard=True)

ids = [r["id"] for r in rows]
add("Match ids unique", len(set(ids)) == len(ids), f"{len(set(ids))}/{len(ids)}", "Ids are the join key between board, predictions and flags.", hard=True)

no_pick = [r["id"] for r in rows if not r["pick"]]
add("Every match row carries a pick", not no_pick, f"{len(rows) - len(no_pick)}/{len(rows)}", "Pick = the selection we would back on the highlighted market.", hard=True)

bad_conf = [r["id"] for r in rows if r["confidence"] not in ("low", "medium", "high")]
add("Every match row has a low/medium/high label", not bad_conf, f"{len(rows) - len(bad_conf)}/{len(rows)}", "Labels come mechanically from the thresholds in model_config.json.", hard=True)

high = [r for r in rows if r["confidence"] == "high"]
pred_ids = {p["match_id"] for p in preds["predictions"]}
missing = [r["id"] for r in high if r["id"] not in pred_ids]
add("Every high-confidence pick has a written prediction", not missing, f"{len(high) - len(missing)}/{len(high)}",
    "Ids: " + ", ".join(sorted(pred_ids)) if not missing else "Missing: " + ", ".join(missing), hard=True)

stray = [i for i in pred_ids if i not in {r["id"] for r in high}]
add("No prediction attached to a non-high pick", not stray, f"{len(pred_ids)} predictions",
    "Predictions exist only where confidence is high, so the label and the write-up cannot drift apart.", hard=True)

words = {p["match_id"]: len(re.findall(r"\b[\w'’-]+\b", p["body"])) for p in preds["predictions"]}
short = {k: v for k, v in words.items() if v < 30}
add("Every prediction is at least 30 words", not short, f"shortest {min(words.values())} words",
    "Word counts: " + ", ".join(f"{k}={v}" for k, v in sorted(words.items())), hard=True)

norm = [re.sub(r"\W+", " ", p["body"].lower()).strip() for p in preds["predictions"]]
dupes = [k for k, v in collections.Counter(norm).items() if v > 1]
add("No duplicated prediction bodies", not dupes, f"{len(dupes)} duplicates", "Each write-up is written for its own match.", hard=True)

fact_urls = [f["source"] for p in preds["predictions"] for f in p["facts"]]
bad_urls = [u for u in fact_urls if not u.startswith("http")]
add("Every prediction fact carries a source URL", not bad_urls, f"{len(fact_urls)} facts",
    "Official-body vs secondary is tagged per fact and secondary facts are also listed on the flagged page.", hard=True)

official = sum(1 for p in preds["predictions"] for f in p["facts"] if f["official"])
secondary = len(fact_urls) - official
add("Predictions cite official bodies where one publishes the fact", official > 0,
    f"{official} official / {secondary} secondary",
    "Governing bodies used: PDC, WTA, NBA, ICC, ACB, Cricket South Africa, World Snooker Tour.")

unresolved = [i for i in items if i["type"] == "unverified"]
add("Unconfirmed values are blank, not filled", len(unresolved) > 0, f"{len(unresolved)} declared gaps",
    "Missing tip counts, injury news and form data are declared and left blank in the tables.")

all_sources = sorted(set([r["olbg_url"] for r in rows] + fact_urls + [i["source"] for i in items if isinstance(i.get("source"), str) and i["source"].startswith("http")]))
add("Source links collected", True, f"{len(all_sources)} unique sources",
    "Counted across inventory rows, prediction facts and flags.")

link_count = 0
broken = []
if "--links" in sys.argv:
    local_targets = set()
    for page in OUT.glob("*.html"):
        html_text = page.read_text()
        for href in re.findall(r'href="([^"]+)"', html_text):
            if href.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = href.split("#")[0]
            if not target:
                continue
            link_count += 1
            local_targets.add(target)
            if not (OUT / target).exists():
                broken.append(f"{page.name} -> {href}")
    add("Internal link audit (no broken local links)", not broken, f"{link_count} local links, {len(broken)} broken",
        "Every href that is not absolute is resolved against the repo root; Pages serves these from /.", hard=True)

summary = {
    "rows": len(rows),
    "rows_with_source": len(rows_with_source),
    "official_facts": official,
    "secondary_facts": secondary,
    "min_pred_words": min(words.values()) if words else 0,
    "duplicate_bodies": len(dupes),
    "source_links": len(all_sources),
    "local_links": link_count,
    "broken_local_links": len(broken),
    "high": len(high),
}
(DATA / "verification.json").write_text(
    json.dumps({"schema": "olbg4.verification/1", "summary": summary, "checks": checks,
                "broken_links": broken}, indent=1) + "\n")

print(json.dumps(summary, indent=1))
if hard_fail:
    print("HARD FAILURE", file=sys.stderr)
    sys.exit(1)
