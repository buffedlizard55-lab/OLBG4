#!/usr/bin/env python3
"""Board R (session 47b1b4e2) - report builder.

Renders five pages into `session-47b1b4e2/`. The report describes the repository as it stands
AFTER merging `origin/main` (PRs #24-#54, Boards K/L/M/N/O/P/Q), not the state this session
produced before that merge - publishing pre-merge numbers would misrepresent the live site.

Board letter: three sessions independently claimed "Board K" (`83451f65`, `5838b25d`, this one).
Following the precedent Board L set for the same collision, this board's record is renamed R.
The directory name stays `session-47b1b4e2/` because it is keyed to the session id, which is unique.

Run: python3 scripts/session-47b1b4e2/build_report.py
"""
import html
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "session-47b1b4e2")
PAGES = [("index.html", "Overview"), ("draft-text.html", "Draft-text fix"),
         ("restored.html", "Restored files"), ("verification.html", "Verification"),
         ("merge.html", "Merge record")]


def e(s):
    return html.escape("" if s is None else str(s))


def load(rel, default=None):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def page(title, active, body):
    nav = "".join('<a href="%s"%s>%s</a>' % (h, ' class="on"' if h == active else "", l)
                  for h, l in PAGES)
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%s — OLBG4 Board R</title>
<style>
:root{--ink:#111827;--mut:#6b7280;--line:#e5e7eb;--bg:#f8fafc;--blue:#2563eb;--amber:#b45309;--green:#15803d}
*{box-sizing:border-box}
body{margin:0;font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;color:var(--ink);background:var(--bg)}
header{background:#fff;border-bottom:1px solid var(--line);padding:14px 0;position:sticky;top:0;z-index:5}
.wrap{max-width:1200px;margin:0 auto;padding:0 18px}
header .wrap{display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between}
b.brand{font-size:17px}b.brand span{color:var(--blue)}
nav{display:flex;flex-wrap:wrap;gap:4px}
nav a{padding:6px 11px;border-radius:8px;text-decoration:none;color:var(--mut);font-size:14px;font-weight:600}
nav a:hover{background:#eef2ff;color:var(--blue)}
nav a.on{background:var(--blue);color:#fff}
main{max-width:1200px;margin:0 auto;padding:22px 18px 60px}
h1{font-size:26px;margin:6px 0 4px}h2{font-size:19px;margin:30px 0 8px}
.lede{color:var(--mut);margin:0 0 18px}
.eyebrow{text-transform:uppercase;letter-spacing:.06em;color:var(--blue);font-weight:800;font-size:11.5px;margin:0 0 6px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(178px,1fr));gap:12px;margin:18px 0}
.kpi{background:#fff;border:1px solid var(--line);border-radius:12px;padding:13px 15px}
.kpi .l{font-size:12px;color:var(--mut);text-transform:uppercase;letter-spacing:.04em;font-weight:700}
.kpi .v{font-size:27px;font-weight:800;margin-top:3px}
.kpi .s{font-size:12.5px;color:var(--mut);margin-top:3px}
.tw{background:#fff;border:1px solid var(--line);border-radius:12px;overflow:auto;margin:10px 0}
table{border-collapse:collapse;width:100%%;font-size:13.5px}
th{background:#f1f5f9;text-align:left;padding:9px 11px;font-size:11.5px;text-transform:uppercase;letter-spacing:.04em;color:#475569;border-bottom:1px solid var(--line);white-space:nowrap}
td{padding:9px 11px;border-bottom:1px solid var(--line);vertical-align:top}
tr:last-child td{border-bottom:0}
.small{font-size:12.5px;color:var(--mut)}
.pill{display:inline-block;padding:2px 8px;border-radius:99px;font-size:11px;font-weight:800;letter-spacing:.03em}
.hi{background:#fee2e2;color:#991b1b}.me{background:#fef3c7;color:#92400e}.lo{background:#e0e7ff;color:#3730a3}
.ok{background:#dcfce7;color:#166534}
.note{background:#eff6ff;border:1px solid #cddffd;border-left:4px solid var(--blue);border-radius:10px;padding:12px 15px;margin:14px 0}
.warn{background:#fffbeb;border:1px solid #fde68a;border-left:4px solid var(--amber);border-radius:10px;padding:12px 15px;margin:14px 0}
.good{background:#f0fdf4;border:1px solid #bbf7d0;border-left:4px solid var(--green);border-radius:10px;padding:12px 15px;margin:14px 0}
code{background:#f1f5f9;padding:1px 5px;border-radius:5px;font-size:12.5px}
pre{background:#0f172a;color:#e2e8f0;padding:14px 16px;border-radius:10px;overflow:auto;font-size:12.5px;line-height:1.65}
a{color:var(--blue)}
.strike{text-decoration:line-through;color:var(--mut)}
ul{margin:8px 0 8px 20px;padding:0}li{margin:5px 0}
footer{border-top:1px solid var(--line);margin-top:40px;padding:18px 0;color:var(--mut);font-size:13px}
</style></head>
<body><header><div class="wrap">
<b class="brand">OLBG4 <span>· Board R</span></b>
<nav>%s</nav>
</div></header>
<main class="wrap">
%s
</main>
<footer class="wrap">Board R · session <code>arena/47b1b4e2-olbg4</code> · 2026-10-21 · remediation and
integration. Sources: official governing-body pages, linked inline. Nothing on this site is betting
advice; unconfirmed values are left blank and flagged rather than inferred.</footer>
</body></html>
""" % (e(title), nav, body)


def main():
    rows = load("data/matches.json", [])
    by_id = {r["id"]: r for r in rows if isinstance(r, dict) and "id" in r}
    fa = load("data/session-47b1b4e2/draft_artefacts.json") or {"changes": [], "rows_affected": 0}
    checks = load("data/session-47b1b4e2/checks.json")
    os.makedirs(OUT, exist_ok=True)

    n_conf = sum(1 for r in rows if (r.get("verification") or {}).get("status") == "confirmed")
    n_unver = sum(1 for r in rows if (r.get("verification") or {}).get("status") == "unverified")
    n_high = sum(1 for r in rows if r.get("confidence") == "High")
    n_flag = sum(1 for r in rows if r.get("flagged"))

    # ------------------------------------------------------------ index.html
    idx = """
<p class="eyebrow">Session <code>arena/47b1b4e2-olbg4</code> · 2026-10-21 · remediation + integration</p>
<h1>Board R — what this session changed, and what it did not</h1>
<p class="lede">This board opened to remediate Board J's findings. While it worked, <strong>Boards K, L, M, N,
O, P and Q merged 126 commits and 54 pull requests to <code>main</code></strong>, including a full
re-verification of the hub dataset and a rebuilt root landing page. This board merged all of it, kept
it, and reports the repository <em>as it now stands</em>. Where this session's earlier work was
superseded by a stricter pass, that is stated plainly rather than presented as still live.</p>

<div class="kpis">
 <div class="kpi"><div class="l">Commits merged from main</div><div class="v">126</div><div class="s">PRs #24–#54, Boards K/L/M/N/O/P/Q — all retained, nothing discarded</div></div>
 <div class="kpi"><div class="l">Conflicted files resolved</div><div class="v">25</div><div class="s">theirs taken for files other boards own; <a href="merge.html">resolution log</a></div></div>
 <div class="kpi"><div class="l">New defect found &amp; fixed</div><div class="v">%(nf14)d</div><div class="s">rows publishing unfinished draft text — finding R-F14, reported by no other board</div></div>
 <div class="kpi"><div class="l">Build A rows restored</div><div class="v">144</div><div class="s">from 137; 4 deleted sport pages back; byte-identical to the generator's own output</div></div>
 <div class="kpi"><div class="l">Hub rows confirmed on an official source</div><div class="v">%(nconf)d <span class="small">/ %(nrows)d</span></div><div class="s">%(nunver)d blanked and flagged by the owning board's stricter cycle</div></div>
 <div class="kpi"><div class="l">Final gate</div><div class="v">%(gpct)s</div><div class="s">%(glinks)s</div></div>
</div>

<div class="warn"><strong>Superseded, and deliberately not re-applied.</strong> Before the merge this board
had remediated the hub's 66 rows itself: 26 downgraded from <code>verified:true</code>, 14 corrected
against official pages, 23 predictions withdrawn with text preserved, and an <code>entryType</code> and
<code>sourceClass</code> added to every row. Board <code>082d3c16</code> had independently run a
<strong>stricter</strong> cycle over the same file — it re-read each fixture from an official API or
governing-body page, and where it could not confirm a value it <em>blanked</em> the time, venue, source
and prediction and moved the old source to <code>priorSourceUrl</code>. That is more conservative than
this board's labelling approach, it satisfies the brief more directly, and it is the version now on
<code>main</code>. <strong>This board took theirs and did not overwrite it.</strong> Its own
<code>k_withdrawn</code> / <code>k_verification</code> / <code>entryType</code> keys are therefore not in
the live dataset. The evidence this session gathered is still offered to the owning board on the
<a href="verification.html">Verification</a> page.</div>

<h2>What this board contributed that is live now</h2>
<div class="tw"><table><thead><tr><th>Item</th><th>Status</th><th>Detail</th></tr></thead><tbody>
<tr><td><strong>R-F14</strong> — unfinished draft text in rendered fields</td><td><span class="pill ok">LIVE</span></td>
<td><strong>Found by this board; reported by no other.</strong> %(nf14)d hub rows published unresolved
self-corrections ("Chengdu<strong>? Actually</strong> Chennai") and working notes ("monitor entry lists")
in <code>competition</code>, <code>pick</code>, <code>originatedSpread</code>, <code>marketFocus</code> and
<code>teamB</code> — fields both the hub pages and the consolidated <code>/board/</code> render. Ten
boards audited or re-verified this dataset without reporting it. <a href="draft-text.html">Field-level detail →</a></td></tr>
<tr><td><strong>Build A restoration</strong> (Board J F-11/F-12)</td><td><span class="pill ok">LIVE</span></td>
<td><code>data/rows.json</code> 137 → <strong>144</strong> rows and the four deleted
<code>docs/sports/*.html</code> pages restored, by re-running Build A's own unmodified generator so the
output is byte-identical to <code>5918922</code>. The 25 templated predictions that had overwritten
Build B's file are archived verbatim. <a href="restored.html">Details →</a></td></tr>
<tr><td><strong>Build B renderer repaired</strong></td><td><span class="pill ok">LIVE</span></td>
<td><code>scripts/build_site.py</code> raised <code>KeyError: 'match_id'</code> on the restored dataset.
Repointed at the build-owned <code>data/session-7114b6a1/predictions.json</code> with a root fallback —
18 pages, exit 0.</td></tr>
<tr><td><strong>F-07 retraction</strong> — "Gaelic football is excluded"</td><td><span class="pill ok">LIVE</span></td>
<td>The brief excludes <em>hurling</em>, not Gaelic football. Retracted in <code>data/flag_notes.json</code>
(the authored source — <code>scripts/verify.py</code> regenerates <code>data/flagged.json</code>, so editing
the generated file is silently wiped). Build B's original wording is preserved verbatim and renders with
the galwaygaa.ie link.</td></tr>
<tr><td><strong>Reproducible gate</strong> <code>check_all.py</code></td><td><span class="pill ok">LIVE</span></td>
<td>Repository-wide checks over JSON validity, source links, prediction rules, exclusions, local links and
placeholder tokens. Exits non-zero on any hard failure. %(gpct)s.</td></tr>
<tr><td><strong><code>restore_docs_banner.py</code></strong></td><td><span class="pill ok">LIVE</span></td>
<td><code>gen_pages.py</code> destroys Board B's additive <code>docs/index.html</code> banner on every run
(observed twice). This re-inserts it so Build A's build order is reproducible.</td></tr>
<tr><td><strong>Official-source evidence</strong> for rows the owning board left blank</td><td><span class="pill me">OFFERED</span></td>
<td>15 governing-body pages re-opened line by line, including fixtures the owning board marked
<code>unverified</code> (PDC European Championship session times, EuroLeague Round 7, the RLWC Round 2
fixture). Published as evidence and logged as a request in <code>COORDINATION.md</code> —
<strong>not</strong> written into another board's rows, because it deliberately blanked them.
<a href="verification.html">Verification →</a></td></tr>
<tr><td>Hub remediation (26 downgrades, 14 corrections, 23 withdrawals, <code>entryType</code>)</td><td><span class="pill lo">SUPERSEDED</span></td>
<td>Retained in this branch's history at commits <code>094a817</code> and <code>d1c5fcf</code>, and
described in <code>data/session-47b1b4e2/remediation.json</code>. Not live: the owning board's stricter
cycle is. No conflict — both reaches the same conclusion on F-01, theirs goes further.</td></tr>
</tbody></table></div>

<h2>One conflict this board found but did not resolve</h2>
<div class="warn"><strong>Two published gates disagree about blanking a source link, and it is not this
board's call to make.</strong> The brief says both <em>"every table row must have a source link to an
official site"</em> and <em>"if a value can't be confirmed from an official source, leave it blank and flag
it unverified"</em>. Board <code>082d3c16</code> resolved that tension toward blanking: %(nunver)d hub rows
now have an empty <code>sourceUrl</code>, with the previous value preserved in <code>priorSourceUrl</code>
and the row flagged. <code>session-07a080b9/audit.py</code> (Board F) treats a missing
<code>sourceUrl</code> as a hard <strong>FAIL</strong> and reports all %(nunver)d.
<br><br>
Both readings are defensible, so this board <strong>recorded the conflict rather than "fixing" it in either
direction</strong> — overturning the owning board's blanking would discard its verification work, and
editing Board F's audit script would rewrite another board's findings. It is surfaced as a non-blocking
NOTE in <code>check_all.py</code> and logged in <code>COORDINATION.md</code> for the two boards to settle.
It does not block deployment: <code>pages.yml</code> runs <code>tools/verify_master.py</code>, which passes,
not Board F's audit.</div>

<h2>Where to look next</h2>
<div class="tw"><table><thead><tr><th>Page</th><th>What it contains</th></tr></thead><tbody>
<tr><td><a href="draft-text.html">Draft-text fix</a></td><td>Finding R-F14: every affected row, the exact string that was published, what replaced it, and why the "Actually …" answer was not adopted.</td></tr>
<tr><td><a href="restored.html">Restored files</a></td><td>What commit <code>cf9f024</code> overwrote, how Build A and Build B were restored, and the byte-identity check.</td></tr>
<tr><td><a href="verification.html">Verification</a></td><td>The 15 official pages re-opened, what each confirmed, what this board did <em>not</em> re-verify, and the final gate results.</td></tr>
<tr><td><a href="merge.html">Merge record</a></td><td>All 25 conflicted files, which side was taken and why, and the regeneration steps run afterwards.</td></tr>
<tr><td><a href="../board/">Consolidated master board</a></td><td>The live integration desk built from all six builds (317 rows), which this board's R-F14 fix now feeds.</td></tr>
<tr><td><a href="../session-e1e0c27e/flagged.html">Board J findings</a></td><td>The 13 findings this board opened to remediate, with its 18 spot checks and cross-build conflict table.</td></tr>
</tbody></table></div>
""" % dict(nf14=fa.get("rows_affected", 0), nrows=len(rows), nconf=n_conf, nunver=n_unver,
           gpct=("%d/%d checks pass" % (checks["passed"], checks["total"])) if checks else "not run",
           glinks=(checks["checks"][[c["check"] for c in checks["checks"]].index(
               "No broken local links anywhere in the repository")]["result"]) if checks else "")

    # ------------------------------------------------------- draft-text.html
    trs = []
    for c in fa.get("changes", []):
        rid = c["id"]
        r = by_id.get(rid, {})
        for field, action in c["fields"]:
            before = (c.get("originals") or {}).get(field, "")
            after = r.get(field, "")
            trs.append(
                "<tr><td><strong>%s</strong><div class='small'>%s</div></td><td><code>%s</code></td>"
                "<td><span class='pill %s'>%s</span></td>"
                "<td class='small'><span class='strike'>%s</span></td>"
                "<td class='small'>%s</td><td class='small'>%s</td></tr>"
                % (e(rid), e(r.get("sport", "")), e(field),
                   "hi" if action == "blanked" else "me", e(action.upper()),
                   e(before), e(after) if str(after).strip() else "<em>(blank)</em>",
                   e(((c.get("reasons") or {}).get(field) or ""))))
    draft = """
<h1>Finding R-F14 — unfinished draft text published in rendered fields</h1>
<p class="lede">Discovered by this board while writing the artefact check in <code>check_all.py</code>.
Ten boards (F, G, I, J, K, L, M, N, P, Q) audited or re-verified this dataset without reporting it;
Board J caught one instance of the same pattern, in EL02's prediction text only.</p>

<div class="warn"><strong>The defect.</strong> <code>data/matches.json</code> published unresolved
self-corrections of the form "X? Actually Y" — the author wrote a value, doubted it, wrote another, and
shipped both — in fields the site renders directly. It also published instructions to the author where a
pick belongs. Because <code>assets/js/main.js</code> renders <code>competition</code>, <code>pick</code>,
<code>originatedSpread</code> and <code>marketFocus</code>, and <code>tools/build_master.py</code> reads
<code>pick</code>, <code>competition</code>, <code>teamB</code> and <code>originatedSpread</code> into the
consolidated board, these strings were live on both the hub category pages and <code>/board/</code>.</div>

<h2>What a reader was being shown</h2>
<div class="tw"><table><thead><tr><th>Field</th><th>Published string (verbatim)</th></tr></thead><tbody>
<tr><td><code>competition</code></td><td>WTT Youth/Feeder Concurrent — Chengdu<strong>? Actually</strong> Chennai</td></tr>
<tr><td><code>originatedSpread</code></td><td>Game Handicap: MS -<strong>? Actually</strong> badminton: -6.5 points handicap @ 1.91</td></tr>
<tr><td><code>teamB</code></td><td>Course: El Tigre<strong>? Actually</strong> Vidanta Vallarta — par 71, wide fairways</td></tr>
<tr><td><code>originatedSpread</code></td><td>Game Handicap -1.5 @ 1.91 (Best of 5 last-16<strong>? Actually</strong> Champions is Bo5 R32-16, Bo7 QF onward; <strong>check WTT rules</strong>)</td></tr>
<tr><td><code>pick</code></td><td>Sei Young Kim (defending) to contend — but low confidence outright; back Over -18.5 winning score<strong>? Actually</strong> course plays under, lean Under -18.5 if wind</td></tr>
<tr><td><code>pick</code></td><td>No pick yet — <strong>monitor</strong> entry lists (Alcaraz/Sinner expected in Basel/Vienna)</td></tr>
<tr><td><code>marketFocus</code></td><td>No match markets until draw — <strong>monitor</strong> pools</td></tr>
</tbody></table></div>

<h2>Every field changed (%(n)d rows)</h2>
<div class="tw"><table><thead><tr><th>Row</th><th>Field</th><th>Action</th><th>Was published as</th><th>Now</th><th>Why</th></tr></thead>
<tbody>%(trs)s</tbody></table></div>

<div class="note"><strong>Why the "Actually …" answer was not adopted.</strong> It looks like the author
left the correct value in the string, so simply keeping the second half is tempting. This board did not do
that. Picking between two values the author never reconciled, with no governing-body page behind either,
is <em>inference</em> — and the brief is explicit: if a value cannot be confirmed from an official source,
leave it blank and flag it as unverified; never infer or fill values. So the field is blanked, the row is
flagged, and the original string is preserved on the row under <code>r_f14_removed</code> so a reviewer can
see exactly what was removed and confirm it against a source themselves.</div>

<div class="good"><strong>Nothing was lost and nothing else was touched.</strong> The fix adds only the
<code>r_f14_removed</code> key, appends to <code>flagReason</code> and sets <code>flagged</code>. It never
rewrites <code>verification</code>, <code>priorSourceUrl</code>, <code>verified</code> or
<code>confidence</code>, which belong to the board that wrote them. Rows another board had already blanked
during its own verification cycle were skipped. The script is idempotent: a second run reports
"changed this run: 0".</div>

<h2>Reproduce</h2>
<pre>python3 scripts/session-47b1b4e2/fix_draft_artefacts.py   # writes data/session-47b1b4e2/draft_artefacts.json
python3 tools/build_master.py &amp;&amp; BOARD_OUT=board BOARD_EXT="../" python3 tools/build_master_site.py
BOARD_DIR=board python3 tools/verify_master.py            # master-board gate</pre>
""" % dict(n=fa.get("rows_affected", 0), trs="".join(trs))

    # --------------------------------------------------------- restored.html
    restored = """
<h1>Restored files — Board J findings F-11 and F-12</h1>
<p class="lede">Commit <code>cf9f024</code>, from another session, overwrote parts of Build A and Build B
with generated filler. Board J proved it; this board repaired it. All of this survived the merge and is
live on <code>main</code>.</p>

<h2>What <code>cf9f024</code> did</h2>
<div class="tw"><table><thead><tr><th>File</th><th>Before</th><th>After <code>cf9f024</code></th><th>Now</th></tr></thead><tbody>
<tr><td><code>data/rows.json</code></td><td>144 rows, 15 sports, 12 hand-written predictions</td><td>137 rows; 7 lost</td><td><strong>144 restored</strong></td></tr>
<tr><td><code>docs/sports/*.html</code></td><td>15 sport pages</td><td>11 — gaelic-football, golf, greyhound-racing and motor-racing deleted</td><td><strong>15 restored</strong></td></tr>
<tr><td><code>data/predictions.json</code></td><td>Build B's 9 per-claim-sourced predictions</td><td>25 templated entries, no <code>match_id</code>; 13 shared one identical PDC opener; an NHL template carried a <code>.,</code> artefact; a Bruins v Predators entry discussed the San Jose Sharks</td><td><strong>9 restored</strong>; the 25 archived verbatim</td></tr>
</tbody></table></div>

<h2>How it was restored — and why not <code>git checkout</code></h2>
<div class="note">The obvious fix, <code>git checkout 5918922 -- data/rows.json</code>, was
<strong>not</strong> used. That would have left the repository's committed output disagreeing with the
generator that produces it, so the next build would silently undo the repair. Instead Build A's own
<em>unmodified</em> generator was re-run and its output compared to the pre-overwrite commit:
<pre>python3 build_site.py     # rows 144 high 12 flagged 15
python3 gen_pages.py      # pages built 15</pre>
<code>data/rows.json</code> came back <strong>byte-identical</strong> to <code>5918922:data/rows.json</code>,
and 17 of the 18 <code>docs/</code> files byte-identical too. The generator stays authoritative.</div>

<h2>The one file that was not byte-identical, and why</h2>
<p><code>docs/index.html</code> differed by exactly one <code>difflib</code> <code>delete</code> op: a
681-character banner Board B had added after <code>&lt;body&gt;</code>. <code>grep</code> on the working
file gave a false negative, so the diff was located with <code>SequenceMatcher</code> instead. The banner
was re-inserted at <code>new.index('&lt;header&gt;')</code> — not <code>&lt;main&gt;</code>, which is where
a first attempt put it — restoring byte-identity.</p>
<div class="warn"><strong>This is a live trap for any board that rebuilds Build A.</strong>
<code>gen_pages.py</code> rewrites <code>docs/index.html</code> from scratch and destroys that banner on
<em>every</em> run; it was observed doing so twice during this board's work.
<code>scripts/session-47b1b4e2/restore_docs_banner.py</code> re-inserts it, verbatim, with a Board R
correction nested inside retracting its "Gaelic football is on the exclusion list" sentence. The correct
order is:
<pre>python3 build_site.py &amp;&amp; python3 gen_pages.py &amp;&amp; python3 scripts/session-47b1b4e2/restore_docs_banner.py</pre></div>

<h2>Two other generated-file traps found while repairing this</h2>
<div class="tw"><table><thead><tr><th>Trap</th><th>Consequence</th><th>Correct target</th></tr></thead><tbody>
<tr><td><code>data/flagged.json</code> is generated — <code>scripts/verify.py</code> line 42 rewrites it from <code>data/flag_notes.json</code> + <code>data/model_assumptions.json</code></td><td>Editing <code>flagged.json</code> directly is silently wiped on the next verifier run. This board's first attempt at the F-07 retraction was lost exactly this way.</td><td>Patch <code>data/flag_notes.json</code>. Note <code>scripts/build_site.py</code> renders only <code>what</code>/<code>detail</code>/<code>source</code>, so retraction text must be folded into <code>detail</code>.</td></tr>
<tr><td><code>scripts/build_site.py</code> read <code>data/predictions.json</code> and required <code>match_id</code></td><td><code>KeyError: 'match_id'</code> — Build B's site could not be rebuilt at all after the restoration.</td><td>Repointed at <code>data/session-7114b6a1/predictions.json</code> with a root fallback. 18 pages, exit 0.</td></tr>
</tbody></table></div>

<h2>The withdrawn templated predictions were archived, not deleted</h2>
<p>All 25 entries that <code>cf9f024</code> introduced are preserved verbatim, with a
<code>reason</code> and <code>status: "WITHDRAWN"</code> on each, at
<code>data/archive/session-4359d6a4-templated-predictions.json</code>. Another session's output is
evidence about that session; deleting it would have destroyed the record Board J's finding rests on.</p>
"""

    # ----------------------------------------------------- verification.html
    doms = sorted({(r.get("verification") or {}).get("officialUrl", "").split("/")[2]
                   for r in rows if (r.get("verification") or {}).get("officialUrl")
                   and len((r.get("verification") or {}).get("officialUrl", "").split("/")) > 2})
    verification = """
<h1>Verification — what was checked, and what was not</h1>
<p class="lede">This session re-opened the official pages behind every claim rather than accepting earlier
sessions' verification. Checks were performed on 2026-10-21 with the agent's web fetch and search tools;
the sandbox shell has egress only to github.com, npmjs.org and pypi.org, so no official sports endpoint is
reachable from <code>bash</code> here.</p>

<h2>Official pages re-opened by this session</h2>
<p class="lede">These confirmed Board J's contradictions, and in several cases went further than Board J:
both <code>nrl.com</code> URLs Board J cited for the RLWC Round 2 fixture <strong>return 404</strong>, so the
correct sources were located instead. Rows marked <em>offered</em> are ones the owning board has since
blanked — the evidence is published here and logged as a request rather than written into its rows.</p>
<div class="tw"><table><thead><tr><th>Official source</th><th>What it confirmed</th><th>Rows</th><th>Status</th></tr></thead><tbody>
<tr><td><a href="https://www.nhl.com/news/san-jose-sharks-montreal-canadiens-game-preview-october-20-2026" target="_blank" rel="noopener">NHL.com — Sharks at Canadiens preview</a></td><td class="small">"SHARKS (4-4-1) at CANADIENS (4-3-1), 7 p.m. ET" — contradicts the published "San Jose 0-4"</td><td>NHL01</td><td><span class="pill ok">superseded</span></td></tr>
<tr><td><a href="https://www.nhl.com/news/san-jose-sharks-montreal-canadiens-game-recap-october-20-2026" target="_blank" rel="noopener">NHL.com — recap</a></td><td class="small">San Jose won 4-3 in OT; Sharks to 5-4-1, Canadiens to 4-3-2 — the fixture was already final and the High pick had lost</td><td>NHL01</td><td><span class="pill ok">superseded</span></td></tr>
<tr><td><a href="https://www.nhl.com/news/boston-bruins-dallas-stars-game-preview-october-20-2026" target="_blank" rel="noopener">NHL.com — Bruins at Stars preview</a></td><td class="small">"BRUINS (7-2-0) at STARS (4-3-1)"; Boston's injured list reads <strong>"None"</strong>, so "Marchand on IR" was fabricated</td><td>NHL06</td><td><span class="pill ok">superseded</span></td></tr>
<tr><td><a href="https://www.mlb.com/news/2026-mlb-world-series-faq-schedule-times-teams-and-more" target="_blank" rel="noopener">MLB.com — World Series FAQ</a></td><td class="small">Rays beat the Guardians in <strong>six</strong> ALCS games, not seven; Brewers "took two of three", they were not swept; Brewers 103-59, Rays 98-64; Game 1 Fri 23 Oct, 8 p.m. ET, American Family Field</td><td>MLB01</td><td><span class="pill ok">superseded</span></td></tr>
<tr><td><a href="https://www.mlb.com/news/world-series-home-field-advantage" target="_blank" rel="noopener">MLB.com — home-field advantage</a></td><td class="small">"The Rays will host Games 3, 4 and 5 (if necessary) at <strong>Tropicana Field</strong>" — the FAQ page does not name the venue, so this page is the one to cite</td><td>MLB03</td><td><span class="pill ok">superseded</span></td></tr>
<tr><td><a href="https://www.pcb.com.pk/press-release-detail/pakistan-to-host-sri-lanka-and-england-for-t20is-odi-tri-series-and-tests.html" target="_blank" rel="noopener">PCB — tri-series announcement</a></td><td class="small">Pakistan v England is the <strong>second</strong> match (20 Oct, Rawalpindi); match 1 was Pakistan v Sri Lanka (18 Oct); the final is <strong>31 Oct</strong> at Gaddafi Stadium, Lahore — not 29 Oct</td><td>CRK03, CRK05</td><td><span class="pill ok">superseded</span></td></tr>
<tr><td><a href="https://www.pcb.com.pk/press-release-detail/media-advisory-men-s-odi-tri-series-pakistan-england-sri-lanka-rawalpindi-leg.html" target="_blank" rel="noopener">PCB — Rawalpindi media advisory</a></td><td class="small">Sri Lanka v England, third match, 22 Oct, "from <strong>1pm PKT</strong>" (toss 12.30pm) — the published 14:30 was wrong</td><td>CRK04</td><td><span class="pill ok">superseded</span></td></tr>
<tr><td><a href="https://www.ecb.co.uk/news/4562387/pakistan-to-host-sri-lanka-and-england-in-odi-triseries" target="_blank" rel="noopener">ECB — tri-series schedule</a></td><td class="small">Independently corroborates all seven fixtures and the 31 October final</td><td>CRK03, CRK05</td><td><span class="pill ok">superseded</span></td></tr>
<tr><td><a href="https://www.pdc.tv/news/2026/october/19/2026-machineseeker-european-championship-schedule-confirmed/" target="_blank" rel="noopener">PDC — European Championship schedule of play</a></td><td class="small">Thursday 22 and Friday 23 October are <strong>1900–2300 CEST</strong> / 1800–2200 BST at the Westfalenhalle, Dortmund. The hub printed CET. £750k Premier event, 32 players; reigning champion Gian van Veen; Humphries world no. 2</td><td>DRT01–04</td><td><span class="pill me">offered</span></td></tr>
<tr><td><a href="https://www.euroleaguebasketball.net/en/euroleague/news/the-2026-27-euroleague-schedule-is-official/" target="_blank" rel="noopener">EuroLeague Basketball — schedule release</a></td><td class="small">Round 7 on 22 October carries the first Turkish derby (Anadolu Efes v Beşiktaş) and the first Serbian derby. The listing shows <strong>17:30</strong>, EFS(13) v BJK(11) — the published "Efes 4-2 / Besiktas 2-4" had the records <strong>inverted</strong>. Venue is the Basketball Development Center, not Sinan Erdem Dome. Efes <em>lost</em> 93–101 at home to Bayern on 14 Oct</td><td>EL01, EL02</td><td><span class="pill me">offered</span></td></tr>
<tr><td><a href="https://www.rlwc2026.com/draws-and-pools" target="_blank" rel="noopener">RLWC2026.com — official draws &amp; pools</a></td><td class="small">Round 1 Pool A, Thu 15 Oct: Australia 24–22 New Zealand, Allianz Stadium Sydney (fulltime). 18 Oct: Fiji 40–12 Cook Islands, Newcastle. Round 2 Pool A on Sun 25 Oct in Brisbane is <strong>Australia v Fiji</strong>. The published "Pacific Championships Australia v New Zealand, 25 Oct, Brisbane" <strong>does not exist</strong>; "NZ lost to Tonga 18 Oct" is wrong; the final is <strong>15 Nov at Suncorp Stadium, Brisbane</strong>, not 8 Nov in Sydney</td><td>RL01</td><td><span class="pill me">offered</span></td></tr>
<tr><td><a href="https://www.rlwc2026.com/draw/mens/2026/round-2/australia-v-fiji" target="_blank" rel="noopener">RLWC2026.com — Australia v Fiji match centre</a></td><td class="small">Official match centre for the corrected fixture</td><td>RL01</td><td><span class="pill me">offered</span></td></tr>
<tr><td><a href="https://suncorpstadium.com.au/events/rugby-league-world-cup-2026--men-s-australia-v-fiji" target="_blank" rel="noopener">Suncorp Stadium — event page</a></td><td class="small">"Rugby League World Cup 2026: Men's Australia v Fiji", Sunday 25 October 2026, kick off 7:05pm AEST</td><td>RL01</td><td><span class="pill me">offered</span></td></tr>
<tr><td><a href="https://www.galwaygaa.ie/fixtures/?user=6929" target="_blank" rel="noopener">Galway GAA — fixtures</a></td><td class="small">Basis of the F-07 retraction: Build A's Galway row (24 Oct, 19:00, Pearse Stadium) is correct, and Gaelic football is not on the exclusion list</td><td>Build A</td><td><span class="pill ok">live</span></td></tr>
</tbody></table></div>

<div class="warn"><strong>Two dead links, logged so no later board re-cites them.</strong> Board J's finding
F-02 cites <code>nrl.com/news/2026-10-20/...</code> twice for the RLWC Round 2 fixture.
<strong>Both return 404.</strong> The correct sources are <code>rlwc2026.com/draws-and-pools</code> and
<code>/draw/mens/2026/round-N/&lt;slug&gt;</code>. Separately, <code>fetch_page</code> on the MLB World
Series FAQ reports a different <code>url</code> in its metadata than the one requested while serving the
correct body — that mismatch is a tool artefact, not a failure.</div>

<h2>What this board did <em>not</em> re-verify</h2>
<div class="warn"><ul>
<li><strong>The other builds' rows.</strong> Boards A, B, C, E and G publish several hundred further rows.
This board repaired what Board J proved broken and re-verified only the hub rows it changed. Board J's
audit remains the reference for the rest; its 18 spot checks (9 confirmed, 5 partial, 4 contradicted) are
at <a href="../session-e1e0c27e/spot-checks.html">session-e1e0c27e/spot-checks.html</a>.</li>
<li><strong>Originated prices.</strong> Moneyline, handicap and total figures come from each build's own
model. This board corrected fixture facts and removed draft text; it did not re-derive any price.</li>
<li><strong>The consolidated master board's 317 rows.</strong> <code>tools/verify_master.py</code> is that
board's own gate and it passes. This board ran it to confirm the R-F14 fix did not break it, not to
re-audit its content.</li>
<li><strong>Anything after 2026-10-21.</strong> The dataset is a snapshot at that cut-off.</li>
<li><strong>Values left blank.</strong> %(nunver)d hub rows have no confirmed official source, so their
time, venue, source and prediction are blank. They were <em>not</em> filled in — including where this
board had found a plausible source, because the owning board's decision to blank them stands.</li>
</ul></div>

<h2>Governing-body domains the owning board confirmed against</h2>
<p class="lede">%(ndom)d distinct domains across %(nconf)d confirmed rows, read from each row's
<code>verification.officialUrl</code>.</p>
<div class="tw"><table><thead><tr><th>Domain</th><th>Confirmed rows</th></tr></thead><tbody>
%(domrows)s
</tbody></table></div>

<h2>Reproducible checks — run in this order</h2>
<pre>python3 scripts/session-47b1b4e2/fix_draft_artefacts.py    # R-F14, idempotent
python3 build_site.py &amp;&amp; python3 gen_pages.py               # Build A: 144 rows, 15 sport pages
python3 scripts/session-47b1b4e2/restore_docs_banner.py    # gen_pages.py clobbers Board B's banner
python3 scripts/verify.py --links &amp;&amp; python3 scripts/build_site.py   # Build B gate + 18 pages
bash scripts/session-74f9613e/build_all.sh                 # Build C gate + 18 pages
python3 -m pipeline.selftest                               # Build E self-tests
python3 scripts/audit_publication.py                       # cross-build publication audit
python3 tools/build_master.py &amp;&amp; BOARD_OUT=board BOARD_EXT="../" python3 tools/build_master_site.py
BOARD_DIR=board python3 tools/verify_master.py             # master-board gate
python3 scripts/session-47b1b4e2/build_report.py           # this report
python3 scripts/session-47b1b4e2/check_all.py              # final gate, exits non-zero on failure</pre>

<h2>Final gate — <code>check_all.py</code></h2>
<p class="lede">%(gpct)s. Run last, over the whole repository, after every build above has regenerated its
own output. Committed at <code>data/session-47b1b4e2/checks.json</code>.</p>
<div class="tw"><table><thead><tr><th>Check</th><th>Result</th><th>Why it matters</th></tr></thead><tbody>
%(gate)s
</tbody></table></div>
""" % dict(ndom=len(doms), nconf=n_conf, nunver=n_unver,
           domrows="".join(
               "<tr><td><code>%s</code></td><td>%d</td></tr>" % (e(d), sum(
                   1 for r in rows
                   if ((r.get("verification") or {}).get("officialUrl") or "").startswith("https://" + d)
                   or ((r.get("verification") or {}).get("officialUrl") or "").startswith("http://" + d)))
               for d in doms) or "<tr><td colspan='2' class='small'>none recorded</td></tr>",
           gpct=("%d/%d checks pass" % (checks["passed"], checks["total"])) if checks else "gate not run",
           gate="".join(
               "<tr><td>%s</td><td><span class='pill %s'>%s</span> <span class='small'>%s</span></td>"
               "<td class='small'>%s</td></tr>"
               % (e(c["check"]), "ok" if c["ok"] else ("hi" if c["level"] == "hard" else "me"),
                  "PASS" if c["ok"] else ("FAIL" if c["level"] == "hard" else "NOTE"),
                  e(c["result"]), e(c["detail"]))
               for c in (checks["checks"] if checks else [])))

    # ---------------------------------------------------------- merge.html
    merge = """
<h1>Merge record — 126 commits, 25 conflicted files</h1>
<p class="lede">This branch was cut from <code>main</code> at <code>43adf35</code>. By the time it was ready
to integrate, <code>main</code> had moved to <code>162c8e1</code>: 126 commits and pull requests #24–#54,
from Boards K (<code>83451f65</code>), K (<code>5838b25d</code>), L, M, N, O, P and Q. The brief requires
conflicts to be resolved <em>without discarding others' work</em>, so every resolution is recorded here.</p>

<h2>What had changed on main</h2>
<div class="tw"><table><thead><tr><th>Change</th><th>Consequence for this board</th></tr></thead><tbody>
<tr><td>The root landing page was <strong>replaced</strong> by a consolidated line desk, and the previous hub archived to <code>session-6b8d2d5f/hub-2026-10-21.html</code> + <code>archive/root-*/</code></td><td>This board's edits to <code>index.html</code> and <code>flagged.html</code> targeted a page that no longer exists. Theirs taken.</td></tr>
<tr><td><code>data/matches.json</code> re-verified row by row: 66 → <strong>68</strong> rows (NHL08, NHL09 added), all 66 original rows touched, new <code>verification</code>, <code>facts</code>, <code>priorSourceUrl</code> and <code>result</code> keys</td><td>This board's own remediation of the same file was superseded by a stricter pass. Theirs taken; see below.</td></tr>
<tr><td>A new master board: <code>tools/build_master.py</code> → <code>data/master.json</code> (317 rows) → <code>board/</code> (28 pages), with a CI gate that <strong>refuses to deploy if the committed dashboard is stale</strong></td><td>Any change to <code>data/matches.json</code> must be followed by regenerating and committing <code>board/</code> + <code>data/master*.json</code>. Done.</td></tr>
<tr><td>Three sessions independently claimed the letter <strong>Board K</strong></td><td>This is Board J's finding F-13 recurring. This board's record is renamed <strong>R</strong>, the next free letter, following Board L's precedent. The directory stays <code>session-47b1b4e2/</code> because it is keyed to the unique session id.</td></tr>
</tbody></table></div>

<h2>Resolution, file by file</h2>
<div class="tw"><table><thead><tr><th>Files</th><th>Resolution</th><th>Why</th></tr></thead><tbody>
<tr><td><code>data/matches.json</code></td><td><span class="pill ok">THEIRS</span></td><td>The owning board re-read every fixture from an official API or governing-body page and <strong>blanked</strong> whatever it could not confirm (41 rows), preserving the old source in <code>priorSourceUrl</code>. That is stricter than this board's approach of keeping a secondary link and labelling it <code>sourceClass:"secondary"</code>, and it satisfies the brief more directly. Overwriting it would have discarded 68 rows of another board's verification.</td></tr>
<tr><td><code>index.html</code>, <code>flagged.html</code>, 15 category pages</td><td><span class="pill ok">THEIRS</span></td><td>Their pages describe their dataset accurately ("UNVERIFIED means no official page could confirm it, so the time and venue are blank"). This board's wording corrections described a dataset that no longer exists, so keeping them would have published false statements.</td></tr>
<tr><td><code>assets/js/main.js</code></td><td><span class="pill ok">THEIRS</span></td><td>Their renderer reads their <code>verification</code> blocks. This board's renderer read <code>k_withdrawn</code>/<code>entryType</code> keys that are not in the merged data, so it would have rendered nothing.</td></tr>
<tr><td><code>docs/index.html</code></td><td><span class="pill ok">THEIRS</span></td><td>Build A's landing, rebuilt by its own generator on main. <code>restore_docs_banner.py</code> remains available if that banner is lost again.</td></tr>
<tr><td><code>audit/index.html</code>, <code>audit/report.json</code></td><td><span class="pill ok">THEIRS</span></td><td>Generated output; regenerated by its own tool.</td></tr>
<tr><td><code>.github/workflows/pages.yml</code></td><td><span class="pill lo">UNION</span></td><td>Kept all four of their new steps (rebuild master board, verify it, fail if stale) <em>and</em> added an <code>ls -la</code> assertion for this board's five report pages, so the report cannot silently fail to deploy.</td></tr>
<tr><td><code>README.md</code></td><td><span class="pill lo">UNION</span></td><td>Theirs as the base — it describes the live <code>/board/</code> site — plus a Board R section and the F-07 scope clarification.</td></tr>
<tr><td><code>COORDINATION.md</code></td><td><span class="pill lo">UNION</span></td><td>Append-only by rule. Their record kept verbatim; this board's appended below, renamed R, with the K-collision noted.</td></tr>
<tr><td><code>data/matches.json</code> — R-F14 fields only</td><td><span class="pill me">RE-APPLIED ON TOP</span></td><td>The one thing this board changed in their dataset: 8 rows publishing draft text. Additive keys only (<code>r_f14_removed</code>, <code>flagReason</code>, <code>flagged</code>). No <code>verification</code>, <code>verified</code>, <code>confidence</code> or <code>priorSourceUrl</code> value was touched.</td></tr>
</tbody></table></div>

<h2>Regenerated after the merge</h2>
<pre>python3 scripts/session-47b1b4e2/fix_draft_artefacts.py    # 8 rows, idempotent
python3 tools/build_master.py                              # 317 rows, 15 conflicts, 61 source domains
BOARD_OUT=board BOARD_EXT="../" python3 tools/build_master_site.py   # 28 pages
BOARD_DIR=board python3 tools/verify_master.py             # OK - all master-board checks passed
python3 scripts/session-47b1b4e2/build_report.py
python3 scripts/session-47b1b4e2/check_all.py</pre>
<p class="small">The staleness gate compares committed <code>board/</code>, <code>data/master.json</code> and
<code>data/master_conflicts.json</code> against freshly built output, so all three are committed with this
merge.</p>

<h2>Nothing discarded</h2>
<div class="good">Every commit from Boards K, L, M, N, O, P and Q is retained. This board's superseded hub
remediation is retained in branch history at <code>094a817</code> and <code>d1c5fcf</code>, and its
machine-readable record stays at <code>data/session-47b1b4e2/remediation.json</code> — it documents what
was independently found and confirmed against official pages, which remains useful evidence even though the
row-level edits are no longer live. The Build A restoration, the Build B renderer fix, the F-07 retraction
and the templated-prediction archive all survived the merge unchanged and are live.</div>
"""

    bodies = {"index.html": idx, "draft-text.html": draft, "restored.html": restored,
              "verification.html": verification, "merge.html": merge}
    titles = {"index.html": "Overview", "draft-text.html": "Draft-text fix",
              "restored.html": "Restored files", "verification.html": "Verification",
              "merge.html": "Merge record"}
    for fn, body in bodies.items():
        with open(os.path.join(OUT, fn), "w", encoding="utf-8") as f:
            f.write(page(titles[fn], fn, body))
    # remove pages from the pre-merge version of this report so nothing stale is served
    for stale in ("changes.html", "withdrawn.html"):
        p = os.path.join(OUT, stale)
        if os.path.exists(p):
            os.remove(p)
            print("removed superseded page:", stale)
    with open(os.path.join(OUT, ".nojekyll"), "w", encoding="utf-8") as f:
        f.write("")
    print("wrote %d pages to %s/" % (len(bodies), os.path.basename(OUT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
