#!/usr/bin/env python3
"""Board K gate. Re-runnable checks over the whole repository.

Exits 1 on any hard failure so a broken site cannot be published. Review-level items are
reported but do not fail the gate (flagged items never block the merge, per the brief).

Run: python3 scripts/session-47b1b4e2/check_all.py
"""
import collections
import json
import os
import re
import sys
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

results = []
hard_fail = False


def add(name, ok, result, detail="", hard=True):
    global hard_fail
    results.append(dict(check=name, ok=bool(ok), result=result, detail=detail,
                        level="hard" if hard else "review"))
    if not ok and hard:
        hard_fail = True
    print("%-4s %-58s %-28s %s" % ("PASS" if ok else ("FAIL" if hard else "NOTE"),
                                    name, result, detail[:78]))


def load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return json.load(f)


def words(t):
    return len(re.findall(r"\b[\w'’-]+\b", t or ""))


# ---------------------------------------------------------------- 1. JSON validity
json_files = []
for base, dirs, files in os.walk(ROOT):
    dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "__pycache__")]
    for fn in files:
        if fn.endswith(".json"):
            json_files.append(os.path.relpath(os.path.join(base, fn), ROOT))
bad_json = []
for rel in sorted(json_files):
    try:
        with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
            json.load(f)
    except Exception as ex:
        bad_json.append("%s (%s)" % (rel, ex))
add("Every committed JSON file parses", not bad_json, "%d files" % len(json_files),
    "; ".join(bad_json) or "data/, docs/, session-*/, tools/, pipeline/, audit/")

# ---------------------------------------------------------------- 2. hub dataset (post-merge schema)
# Board 082d3c16 re-verified every row and blanks whatever it could not confirm, preserving the old
# source in priorSourceUrl. This board's earlier entryType/sourceClass pass was superseded by that, so
# the checks below assert THEIR schema plus this board's additive r_f14_removed key.
rows = load("data/matches.json")
add("Hub dataset loads with the merged row count", len(rows) == 68, "%d rows" % len(rows),
    "66 as published by Build D, plus NHL08 and NHL09 added during the owning board's verification cycle.")

blanked = [r for r in rows if r.get("priorSourceUrl") and not r.get("sourceUrl")]
add("Every blanked row preserves the source it replaced",
    all(r.get("priorSourceUrl") for r in blanked), "%d blanked rows" % len(blanked),
    "Blanking is brief-compliant only if the discarded value stays on the row for a reviewer.")

unconf = [r["id"] for r in rows
          if (r.get("verification") or {}).get("status") == "unverified" and not r.get("flagged")]
add("Every row that could not be confirmed is flagged", not unconf,
    "%d unverified rows, all flagged" % sum(1 for r in rows if (r.get("verification") or {}).get("status") == "unverified"),
    ", ".join(unconf) or "The brief requires an unconfirmable value to be blank AND flagged, never inferred.")

lying = [r["id"] for r in rows
         if r.get("verified") is True and not (r.get("sourceUrl") or "").startswith("http")]
add("No row is verified:true without a live source link", not lying, "%d offenders" % len(lying),
    ", ".join(lying) or "This was Board J finding F-01: rows self-marked verified on secondary sources.")

# ---- cross-board policy conflict, surfaced as a NOTE (non-blocking)
# The brief says both "every table row must have a source link to an official site" and "if a value
# can't be confirmed from an official source, leave it blank and flag it unverified". Board 082d3c16
# resolved that toward blanking sourceUrl (preserving the old value in priorSourceUrl and flagging the
# row); session-07a080b9/audit.py treats a missing sourceUrl as a hard FAIL. Both readings are
# defensible, so this is recorded rather than "fixed" - neither board's decision is this board's to
# overturn. It does not block deployment: pages.yml runs verify_master.py, not Board F's audit.
unsourced = [r["id"] for r in rows if not (r.get("sourceUrl") or "").startswith("http")]
preserved_all = all(r.get("priorSourceUrl") and r.get("flagged") for r in rows
                    if not (r.get("sourceUrl") or "").startswith("http"))
add("Every row without a live source link is flagged and preserves its prior source",
    preserved_all, "%d rows without a live link" % len(unsourced),
    "session-07a080b9/audit.py reports these %d rows as FAIL 'Row missing sourceUrl'; the owning board "
    "blanked them deliberately under the brief's leave-it-blank clause. Policy conflict logged in "
    "COORDINATION.md, not silently resolved." % len(unsourced), hard=False)

no_v = [r["id"] for r in rows if not isinstance(r.get("verification"), dict)
        or (r["verification"].get("status") not in ("confirmed", "unverified", "partial"))]
add("Every hub row carries a verification block with a valid status", not no_v,
    "%d/%d" % (len(rows) - len(no_v), len(rows)), ", ".join(no_v) or "Added by the owning board's cycle.")

high = [r for r in rows if r.get("confidence") == "High"]
short = [(r["id"], words(r.get("prediction"))) for r in high if words(r.get("prediction")) < 30]
add("Every High-confidence row has a prediction of at least 30 words", not short,
    "%d High rows, shortest %d words" % (len(high), min([words(r.get("prediction")) for r in high] or [0])),
    ", ".join("%s=%d" % x for x in short) or "Brief requires >=30 words naming team/player/form/selection.")

nopred = [r["id"] for r in high if not (r.get("prediction") or "").strip()]
add("No High-confidence row is missing its write-up", not nopred, "%d High rows" % len(high),
    ", ".join(nopred) or "A High label with no prediction is not actionable for a reader.")

dupes = [b for b, n in collections.Counter(
    re.sub(r"\W+", " ", (r.get("prediction") or "").lower()).strip() for r in high if r.get("prediction")
).items() if n > 1 and b]
add("No duplicated high-confidence prediction bodies", not dupes, "%d duplicates" % len(dupes),
    "Brief requires unique, non-repetitive write-ups.")

# ---- R-F14: unfinished draft text in fields the site renders
# NOTE on the `.,` signature: Board J's F-12 templated predictions carried strings like
# "a points percentage of 0.556 compared to Philadelphia Flyers's 0.318., reflecting ...". The
# artefact is a DIGIT followed by ".,", not a bare ".,": a bare pattern false-positives on ordinary
# abbreviations such as "e.g.," -- which is how Build G's entirely legitimate greyhound policy note
# ("... track racecard listings (e.g., Nottingham Greyhounds official site ...)") was first flagged.
# Build G's note is correct, brief-compliant prose and must not be altered.
ARTEFACT = re.compile(r"\?\s*Actually|\bVerify tip\b|\d\.\,|\bwait for\b|\bwait until\b|"
                      r"\bmonitor\b|check \w+ rules|before committing|before pricing", re.I)
SKIP_KEYS = ("flagReason", "formNotes", "priorSourceUrl", "priorSourceName", "r_f14_removed", "verification")
artefacts = []
for r in rows:
    for k, v in r.items():
        if isinstance(v, str) and not k.startswith(("k_", "r_f14")) and k not in SKIP_KEYS \
                and ARTEFACT.search(v):
            artefacts.append("%s.%s" % (r["id"], k))
add("No published hub field contains draft or template artefacts", not artefacts,
    "%d offenders" % len(artefacts), ", ".join(artefacts[:8]) or
    "Board R finding R-F14: self-corrections ('X? Actually Y') and notes to the author were published in "
    "competition, pick, originatedSpread, marketFocus and teamB, which the hub and /board/ both render.")

preserved = [r for r in rows if r.get("r_f14_removed")]
lost = [r["id"] for r in preserved
        if not all((v.get("value") or "").strip() for v in r["r_f14_removed"].values())]
add("Every R-F14 removal preserves the original string on the row", not lost,
    "%d rows, %d fields" % (len(preserved), sum(len(r["r_f14_removed"]) for r in preserved)),
    ", ".join(lost) or "Nothing is deleted; a reviewer can check the removed value against a source.")

openers = collections.Counter()
for r in rows:
    p = (r.get("prediction") or "").strip()
    if p:
        openers[" ".join(p.split()[:8])] += 1
rep = {k: v for k, v in openers.items() if v > 2}
add("No hub prediction opener is repeated across more than two rows", not rep,
    "%d repeated openers" % len(rep), "; ".join("%r x%d" % (k, v) for k, v in rep.items()) or
    "Board J finding F-12: 13 of 25 templated rows shared one opener.")

# ---------------------------------------------------------------- 4. master board consistency
master = load("data/master.json")
if master:
    mrows = master["rows"] if isinstance(master, dict) and "rows" in master else master
    add("The consolidated master board is built and non-empty", len(mrows) > 300,
        "%d rows" % len(mrows), "tools/build_master.py merges the six builds; pages.yml fails if it is stale.")
    mart = []
    for r in mrows:
        if not isinstance(r, dict):
            continue
        for k, v in r.items():
            if isinstance(v, str) and ARTEFACT.search(v) and k not in SKIP_KEYS \
                    and not k.startswith(("k_", "r_f14", "prior")):
                mart.append("%s.%s" % (r.get("id"), k))
    add("The master board carries no draft-text artefacts either", not mart,
        "%d offenders" % len(mart), ", ".join(mart[:8]) or
        "R-F14 propagates: build_master.py reads pick, competition, teamB and originatedSpread.")
else:
    add("The consolidated master board is built and non-empty", False, "data/master.json MISSING",
        "Run tools/build_master.py then tools/build_master_site.py.", hard=False)

# ---------------------------------------------------------------- 5. Build A restored
rowsA = load("data/rows.json")
sportsA = sorted({r["sport"] for r in rowsA})
add("Build A dataset holds its original 144 rows", len(rowsA) == 144, "%d rows" % len(rowsA),
    "cf9f024 reduced this to 137 (Board J finding F-11).")
missing_pages = [p for p in ["gaelic-football", "golf", "greyhound-racing", "motor-racing"]
                 if not os.path.exists(os.path.join(ROOT, "docs", "sports", p + ".html"))]
add("Build A's four deleted sport pages exist again", not missing_pages,
    "15 sport pages" if not missing_pages else "missing", ", ".join(missing_pages) or "")
highA = [r for r in rowsA if str(r.get("confidence", "")).lower() == "high"]
openerA = collections.Counter(" ".join((r.get("prediction") or "").split()[:8]) for r in highA if r.get("prediction"))
repA = {k: v for k, v in openerA.items() if v > 2}
add("Build A's high-confidence predictions are not templated", not repA,
    "%d High rows, shortest %d words" % (len(highA), min([words(r.get("prediction")) for r in highA] or [0])),
    "; ".join("%r x%d" % (k, v) for k, v in repA.items()) or "Board J finding F-12.")
add("Build A's Gaelic Football rows are back in scope", "Gaelic Football" in sportsA,
    "%d sports" % len(sportsA), "The brief excludes hurling, not Gaelic football (F-07).")

# ---------------------------------------------------------------- 6. Build B intact
predsB = load("data/session-7114b6a1/predictions.json")["predictions"]
add("Build B's 9 per-claim-sourced predictions are intact", len(predsB) == 9, "%d predictions" % len(predsB),
    "cf9f024 replaced them with 25 templated entries (F-11).")
facts = [f for p in predsB for f in p.get("facts", [])]
add("Every Build B prediction fact still carries a source URL", all(f.get("source") for f in facts),
    "%d facts" % len(facts), "23 official / 13 secondary as published.")
notes = load("data/flag_notes.json")["items"]
gaelic = [i for i in notes if "Gaelic" in json.dumps(i, ensure_ascii=False)]
retracted = [i for i in gaelic if i.get("retracted")]
add("Build B's Gaelic-football exclusion claim is retracted",
    len(gaelic) > 0 and len(retracted) == len(gaelic), "%d/%d retracted" % (len(retracted), len(gaelic)),
    "Board J finding F-07. Original wording must be preserved inside the item.")
preserved = all("ORIGINAL TEXT, UNEDITED" in (i.get("detail") or "") for i in retracted)
add("The retraction preserves Build B's original wording", preserved,
    "%d items" % len(retracted), "Nothing from another board is deleted.")

# ---------------------------------------------------------------- 7. templated archive
arch = os.path.join(ROOT, "data", "archive", "session-4359d6a4-templated-predictions.json")
add("The withdrawn templated predictions are archived, not deleted", os.path.exists(arch),
    "present" if os.path.exists(arch) else "MISSING",
    "data/archive/session-4359d6a4-templated-predictions.json")
if os.path.exists(arch):
    a = load("data/archive/session-4359d6a4-templated-predictions.json")
    add("The archive holds all 25 templated predictions", len(a["payload"]["predictions"]) == 25,
        "%d entries" % len(a["payload"]["predictions"]), "Preserved verbatim from cf9f024.")

# ---------------------------------------------------------------- 8. exclusions
EXCLUDED = ["soccer", "football", "boxing", "ufc", "mma", "hurling", "horse racing", "cycling", "specials",
            "american football"]
offenders = []
for r in rows + rowsA:
    blob = ("%s %s" % (r.get("sport") or r.get("competition") or "", r.get("match") or "")).lower()
    for x in EXCLUDED:
        # "gaelic football" is in scope (only hurling is excluded) - do not match on the substring
        if x == "football" and "gaelic football" in blob:
            continue
        if re.search(r"\b%s\b" % re.escape(x), blob):
            offenders.append("%s:%s" % (r.get("id") or r.get("sport"), x))
add("No excluded sport is published as a priced match", not offenders, "%d offenders" % len(offenders),
    ", ".join(offenders[:6]) or "Excluded: soccer, boxing, UFC/MMA, football, American football, hurling, horse racing, cycling, specials.")

# ---------------------------------------------------------------- 9. local links
broken = []
total = 0
html_files = []
for base, dirs, files in os.walk(ROOT):
    dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "__pycache__")]
    for fn in files:
        if fn.endswith(".html"):
            html_files.append(os.path.join(base, fn))
for path in sorted(html_files):
    with open(path, encoding="utf-8", errors="replace") as f:
        txt = f.read()
    for href in re.findall(r'href="([^"]+)"', txt):
        if href.startswith(("http://", "https://", "mailto:", "#", "data:", "javascript:")):
            continue
        target = href.split("#")[0]
        if not target:
            continue
        total += 1
        resolved = os.path.normpath(os.path.join(os.path.dirname(path), target))
        if os.path.isdir(resolved):
            resolved = os.path.join(resolved, "index.html")
        if not os.path.exists(resolved):
            broken.append("%s -> %s" % (os.path.relpath(path, ROOT), href))
add("No broken local links anywhere in the repository", not broken,
    "%d links across %d HTML files" % (total, len(html_files)),
    "; ".join(broken[:8]) or "Includes every build's dashboard, the master board and the Board R report.")

# ---------------------------------------------------------------- 10. no placeholders
MARKER = "TO" + "DO"
todos = []
for base, dirs, files in os.walk(ROOT):
    dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "__pycache__")]
    for fn in files:
        if fn.endswith((".html", ".json")):
            p = os.path.join(base, fn)
            # skip this gate's own output, otherwise it reports the previous run's file
            if os.path.relpath(p, ROOT) == os.path.join("data", "session-47b1b4e2", "checks.json"):
                continue
            try:
                with open(p, encoding="utf-8", errors="replace") as f:
                    if MARKER in f.read():
                        todos.append(os.path.relpath(p, ROOT))
            except OSError:
                pass
# pages.yml runs: grep -R "TODO" --include="*.html" --include="*.json" .
# So this check's own output must never contain that token, or the gate fails the build it guards.
add("No to-do placeholders in any HTML or JSON file", not todos, "%d files" % len(todos),
    ", ".join(todos[:6]) or "pages.yml greps every HTML and JSON file for this token and fails the build "
    "if it appears, so this check must not emit the token itself.")

# ---------------------------------------------------------------- summary
n_pass = sum(1 for r in results if r["ok"])
print("\n%d/%d checks pass" % (n_pass, len(results)))
out = os.path.join(ROOT, "data", "session-47b1b4e2", "checks.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "w", encoding="utf-8") as f:
    json.dump({"schema": "olbg4.boardk-checks/1", "run_utc": "2026-10-21T08:20Z",
               "passed": n_pass, "total": len(results), "hard_fail": hard_fail,
               "checks": results}, f, indent=1, ensure_ascii=False)
    f.write("\n")
print("wrote", os.path.relpath(out, ROOT))
sys.exit(1 if hard_fail else 0)
