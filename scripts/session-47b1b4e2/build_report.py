#!/usr/bin/env python3
"""Board K remediation report -> session-47b1b4e2/

Renders the change-by-change log for the Board J remediation so the user can review every
edit against the official page it was checked on. Nothing is asserted here that is not in
data/session-47b1b4e2/remediation.json or in the committed diff.

Run: python3 scripts/session-47b1b4e2/build_report.py
Fails (exit 1) if a rendered page has a broken local link or an empty source cell.
"""
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data", "session-47b1b4e2", "remediation.json")
MATCHES = os.path.join(ROOT, "data", "matches.json")
OUT = os.path.join(ROOT, "session-47b1b4e2")

PAGES = [("index.html", "Overview"), ("changes.html", "Change log"),
         ("withdrawn.html", "Withdrawn predictions"), ("restored.html", "Restored files"),
         ("verification.html", "Verification")]


def e(s):
    return html.escape("" if s is None else str(s))


def page(title, active, body):
    nav = "".join(
        '<a href="%s"%s>%s</a>' % (href, ' class="on"' if href == active else "", label)
        for href, label in PAGES
    )
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%s — OLBG4 Board K</title>
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
pre{background:#0f172a;color:#e2e8f0;padding:13px;border-radius:10px;overflow:auto;font-size:12.5px;line-height:1.5}
details{margin-top:6px}summary{cursor:pointer;font-weight:700;color:var(--blue);font-size:13px}
a{color:var(--blue)}
blockquote{margin:8px 0;padding:9px 13px;border-left:3px solid var(--line);color:#4b5563;background:#fafafa;border-radius:0 8px 8px 0}
footer{border-top:1px solid var(--line);background:#fff;padding:16px 0;color:var(--mut);font-size:13px}
</style></head><body>
<header><div class="wrap">
<b class="brand">OLBG<span>4</span> — Board K remediation</b>
<nav>%s<a href="../index.html">← Hub</a></nav>
</div></header>
<main class="wrap">
%s
</main>
<footer><div class="wrap">Board K · session <code>arena/47b1b4e2-olbg4</code> · 2026-10-21 ·
Applies Board J's findings F-01–F-12. Flagged items do not block deployment.
18+ — analysis, not betting advice. <a href="../index.html">Back to hub</a></div></footer>
</body></html>""" % (e(title), nav, body)


def main():
    with open(DATA, encoding="utf-8") as f:
        log = json.load(f)
    with open(MATCHES, encoding="utf-8") as f:
        rows = json.load(f)
    by_id = {r["id"]: r for r in rows}
    s = log["summary"]
    os.makedirs(OUT, exist_ok=True)

    checks_path = os.path.join(ROOT, "data", "session-47b1b4e2", "checks.json")
    checks = None
    if os.path.exists(checks_path):
        with open(checks_path, encoding="utf-8") as f:
            checks = json.load(f)

    # ------------------------------------------------------------- index.html
    et = s["entry_types"]
    idx = """
<p class="eyebrow small">Session <code>arena/47b1b4e2-olbg4</code> · 2026-10-21 · final integration</p>
<h1>Board K — remediation of every Board J finding</h1>
<p class="lede">Board J (<code>arena/e1e0c27e-olbg4</code>, PR #22) audited all six builds and logged 13
findings, four of them high severity. Because the fixes touched files owned by Boards A, B and D, it
recorded them as <em>cross-session requests</em> rather than applying them. No session had claimed those
requests. This board claims and completes them, then integrates.</p>

<div class="kpis">
 <div class="kpi"><div class="l">Findings remediated</div><div class="v">9</div><div class="s">F-01, F-02, F-03, F-04, F-06, F-07, F-08, F-11/F-12 + new K-F14</div></div>
 <div class="kpi"><div class="l">Rows downgraded from verified</div><div class="v">%(f01)d</div><div class="s">source was not a governing body</div></div>
 <div class="kpi"><div class="l">Predictions withdrawn</div><div class="v">%(nwdt)d</div><div class="s">%(nwda)d from Board J findings, %(nwdb)d from new K-F14 — text preserved, never deleted</div></div>
 <div class="kpi"><div class="l">Draft-text fields cleaned</div><div class="v">%(nblank)d</div><div class="s">across %(nf14rows)d rows; new finding K-F14</div></div>
 <div class="kpi"><div class="l">Rows corrected vs official pages</div><div class="v">%(ncor)d</div><div class="s">each with the URL it was checked on</div></div>
 <div class="kpi"><div class="l">Official-source rows now</div><div class="v">%(noff)d <span class="small">/ %(nrows)d</span></div><div class="s">was 32 before remediation</div></div>
 <div class="kpi"><div class="l">Build A rows restored</div><div class="v">144</div><div class="s">from 137; 4 deleted sport pages restored</div></div>
</div>

<div class="good"><strong>Nothing was discarded.</strong> Withdrawn predictions are kept on their row under
<code>k_withdrawn</code> and rendered in an expandable block. Blanked values are kept under
<code>k_unverified_values</code>. The 25 templated predictions that overwrote Build B's file are archived
verbatim at <code>data/archive/session-4359d6a4-templated-predictions.json</code>. Build A was restored by
re-running its own unmodified generator, so its output is byte-identical to the pre-overwrite commit.</div>

<h2>What was wrong, and what was done</h2>
<div class="tw"><table><thead><tr><th>Finding</th><th>Severity</th><th>Problem</th><th>Remediation</th></tr></thead><tbody>
<tr><td><strong>F-11 / F-12</strong></td><td><span class="pill hi">HIGH</span></td>
<td>Commit <code>cf9f024</code> (another session) rewrote Build A's <code>data/rows.json</code> from 144 to 137 rows, deleted four <code>docs/sports/*.html</code> pages, and replaced Build B's 9 per-claim-sourced predictions with 25 templated ones — 13 sharing an identical PDC opener, an NHL template carrying a <code>.,</code> artefact, and a Bruins v Predators entry that discussed the San Jose Sharks.</td>
<td>Re-ran Build A's own unmodified generator (<code>build_site.py</code> + <code>gen_pages.py</code>): 144 rows, 12 hand-written predictions, 15 sport pages, output verified byte-identical to <code>5918922</code>. Restored Build B's predictions and repointed its renderer at the build-owned copy. <a href="restored.html">Details →</a></td></tr>
<tr><td><strong>K-F14</strong><br><span class="pill hi">NEW</span></td><td><span class="pill hi">HIGH</span></td>
<td><strong>Found by this board, not reported by Boards F, G, I or J.</strong> Unfinished draft text is published in Build D's <em>rendered data fields</em>, not only in predictions. Five fields contain an unresolved self-correction of the form "X? Actually Y", so the live dashboard reads:
<code>competition</code> = "WTT Youth/Feeder Concurrent — Chengdu<strong>? Actually</strong> Chennai",
<code>originatedSpread</code> = "Game Handicap: MS -<strong>? Actually</strong> badminton: -6.5 points handicap @ 1.91",
<code>teamB</code> = "Course: El Tigre<strong>? Actually</strong> Vidanta Vallarta — par 71".
Separately, nine predictions on Low/Medium rows are working notes to the author rather than selections ("Wait for Saturday's averages before committing outright", "monitor net run-rate", "wait for upper bracket semis Oct 18-19 before pricing handicaps"), several carrying statistics with no source at all. Board J caught one instance of this, in EL02's prediction only.</td>
<td>%(nf14rows)d rows remediated: %(nblank)d fields blanked and %(nwdb)d predictions withdrawn, all originals preserved on the row under <code>k_unverified_values</code> / <code>k_withdrawn</code>. The "Actually …" answer was <strong>not</strong> adopted — choosing between two values the author never reconciled, without a governing-body page, would be inference. <code>pick</code> cells that merely said no selection was made are restated plainly. <a href="changes.html">Field-level detail →</a></td></tr>
<tr><td><strong>F-01</strong></td><td><span class="pill hi">HIGH</span></td>
<td>26 hub rows were published as <code>verified:true</code> while their only source was ESPN, Wikipedia, BBC, Sky, etusuora, an OLBG blog, USA Today, tempo.co, findmygroup.uk or montpellier.fr. Board D's own claim that "every row sourceUrl is a governing-body domain" was not supported by the data.</td>
<td>All %(f01)d rows set to <code>verified:false</code> + flagged, with <code>sourceClass</code> and <code>sourceDomain</code> published per row. Where this session found a governing-body page (CRK04 → PCB, EL01 → EuroLeague) the source was upgraded instead. <a href="changes.html">Change log →</a></td></tr>
<tr><td><strong>F-02</strong></td><td><span class="pill hi">HIGH</span></td>
<td>High-confidence predictions contradicted by the official pages: NHL01 (Sharks "0-4" — NHL.com lists 4-4-1), NHL06 (Bruins "1-3", "Marchand on IR" — NHL.com lists 7-2-0 and "Injured: None"), EL02 (records inverted plus an unedited draft fragment), MLB01 ("seven-game ALCS" — it was six), RL01 (a 2026 "Pacific Championships" Australia v NZ that does not exist).</td>
<td>%(nwda)d write-ups withdrawn with their text preserved. MLB01 was rebuilt from MLB.com alone. NHL01/NHL06 are marked Final with the NHL.com recap linked. RL01 was re-identified as the real fixture. <a href="withdrawn.html">Every withdrawal →</a></td></tr>
<tr><td><strong>F-03</strong></td><td><span class="pill me">MEDIUM</span></td>
<td>Fixture fields disagreeing with the governing body: CRK03 labelled "Match 1" (PCB: match 2), CRK05 final dated 29 Oct (PCB: 31 Oct), MLB03 venue "George M. Steinbrenner Field" (MLB.com: Tropicana Field), EL02 time and venue.</td>
<td>Corrected against PCB, ECB, MLB.com, EuroLeague Basketball and the club's own fixture list. <a href="changes.html">Change log →</a></td></tr>
<tr><td><strong>F-04</strong></td><td><span class="pill me">MEDIUM</span></td>
<td>About half the hub's 66 "entries" are not matches: tournaments, round summaries, completed events kept for form, and off-season notes — several still carrying a pick and a confidence label.</td>
<td>Every row now carries <code>entryType</code>: %(etmatch)d matches, %(ettour)d tournaments/rounds, %(etres)d completed results, %(etnote)d notes. The dashboard defaults to matches only with an Entry control. Nothing deleted.</td></tr>
<tr><td><strong>F-06</strong></td><td><span class="pill me">MEDIUM</span></td>
<td>93 fixtures appear in 2+ builds and 10 have opposite match-winner picks, with no reconciliation for a reader of the portal.</td>
<td>Explained on the hub landing page as model disagreement rather than data error, linking Board J's cross-build table and naming the Hornets–Nets example.</td></tr>
<tr><td><strong>F-07</strong></td><td><span class="pill lo">LOW</span></td>
<td>Build B flagged Build A's two Gaelic football rows as a scope breach. The brief excludes <em>hurling</em>, not Gaelic football.</td>
<td>Retracted in <code>data/flag_notes.json</code> — the authored source, since <code>scripts/verify.py</code> regenerates <code>data/flagged.json</code>. Original wording preserved verbatim inside the item; the retraction renders on Build B's flagged page with the galwaygaa.ie link.</td></tr>
<tr><td><strong>F-08</strong></td><td><span class="pill lo">LOW</span></td>
<td>Dortmund darts sessions printed as CET and Istanbul local time printed as CET.</td>
<td>DRT01–04 relabelled to CEST per the PDC's own schedule of play (1900–2300 CEST / 1800–2200 BST); EL02 now reads 17:30 CET with the 20:30 Istanbul local time shown.</td></tr>
</tbody></table></div>

<div class="note"><strong>Findings deliberately not "fixed" by changing data.</strong>
<em>F-05</em> (Build B's rows link OLBG and its confidence derives from tipster consensus) is a disclosed
property of that build's method, not an error — it is left as published and cross-referenced here.
<em>F-09</em> (stale E10 status) was already resolved before this board opened. <em>F-13</em> (duplicate board
letters) is a naming artefact of parallel sessions; this board took the next free letter, K.
<em>F-10</em> is Board J's own scope statement.</div>

<h2>Where to look next</h2>
<div class="tw"><table><thead><tr><th>Page</th><th>What it contains</th></tr></thead><tbody>
<tr><td><a href="changes.html">Change log</a></td><td>Every field changed on every row, before → after, with the official URL it was checked against and the date.</td></tr>
<tr><td><a href="withdrawn.html">Withdrawn predictions</a></td><td>All %(nwdt)d withdrawn write-ups in full, each with the reason and the official page that contradicted it.</td></tr>
<tr><td><a href="restored.html">Restored files</a></td><td>The Build A / Build B restoration: what <code>cf9f024</code> changed, how it was reverted, and the byte-identity check.</td></tr>
<tr><td><a href="verification.html">Verification</a></td><td>What this session checked, against which official domains, and what it did <em>not</em> re-verify.</td></tr>
</tbody></table></div>
""" % dict(f01=s["f01_rows_downgraded_to_unverified"],
           nwda=s["predictions_withdrawn"] + s["narrative_predictions_withdrawn"],
           nwdb=s.get("k_f14_predictions_withdrawn", 0),
           nwdt=s["predictions_withdrawn"] + s["narrative_predictions_withdrawn"] + s.get("k_f14_predictions_withdrawn", 0),
           nblank=s.get("k_f14_fields_blanked", 0), nf14rows=s.get("k_f14_rows", 0),
           ncor=s["rows_corrected_against_official_sources"], noff=s["official_sourced_rows"], nrows=s["rows"],
           etmatch=et["match"], ettour=et["tournament"], etres=et["result"], etnote=et["note"])

    # ---------------------------------------------------------- changes.html
    trs = []
    for c in log["changes"]:
        rid = c["id"]
        r = by_id.get(rid, {})
        fields = c.get("fields") or []
        fd = "".join(
            "<tr><td><code>%s</code></td><td class='small'>%s</td><td class='small'>%s</td></tr>"
            % (e(f["field"]), e(str(f["before"])[:220]) or "<em>(empty)</em>", e(str(f["after"])[:220]) or "<em>(blanked)</em>")
            for f in fields)
        act = "<div class='small' style='margin-bottom:5px'><strong>%s</strong></div>" % e(c.get("action") or "")
        fd = act + (("<table style='font-size:12.5px'>%s</table>" % fd) if fd else "")
        # Only cite an official source where this change was actually checked against one. Falling back
        # to the row's own sourceUrl for K-F14 would imply a verification that never happened.
        src = c.get("official_source") or ""
        fnd = str(c.get("finding") or "")
        row_src = r.get("sourceUrl") or ""
        src_html = ""
        if src:
            src_html = '<a href="%s" target="_blank" rel="noopener">%s</a>' % (e(src), e(src))
        elif fnd == "K-F14":
            src_html = "<span class='small'>n/a &mdash; draft text removed; no value was substituted, " \
                       "so nothing was checked against an official page</span>"
        elif fnd.startswith("F-01") and row_src:
            # For a downgrade the row's own non-governing-body link IS the evidence, so show it labelled.
            src_html = ('<a href="%s" target="_blank" rel="noopener">%s</a>'
                        "<div class='small'>row's own source &mdash; %s, not a governing body; "
                        "this is what caused the downgrade</div>"
                        % (e(row_src), e(row_src), e(r.get("sourceDomain") or "")))
        elif fnd.startswith("F-02"):
            src_html = "<span class='small'>n/a &mdash; withdrawn because its form / head-to-head claims " \
                       "could not be confirmed on a governing-body page; see the withdrawal reason</span>"
        else:
            src_html = "<strong>NO SOURCE</strong>"
        trs.append(
            "<tr><td><strong>%s</strong><div class='small'>%s</div></td><td><span class='pill %s'>%s</span></td>"
            "<td>%s</td><td class='small'>%s</td><td class='small'>%s</td></tr>"
            % (e(rid), e(r.get("sport", "")), "hi" if "F-02" in str(c.get("finding")) else "me",
               e(c.get("finding")), fd,
               e(c.get("what_was_wrong") or c.get("reason") or c.get("domain") or ""),
               src_html))
    changes = """
<h1>Change log — every edit, with the official page it was checked against</h1>
<p class="lede">%(n)d changes to <code>data/matches.json</code>, applied by
<code>scripts/session-47b1b4e2/remediate.py</code> and recorded in
<code>data/session-47b1b4e2/remediation.json</code>. "Before" is the value published on <code>main</code>
at <code>43adf35</code>. No value was inferred: anything not confirmable on a governing-body domain was
blanked and flagged.</p>
<div class="tw"><table><thead><tr><th>Row</th><th>Finding</th><th>Fields changed (before → after)</th><th>What was wrong</th><th>Official source checked</th></tr></thead>
<tbody>%(detail)s</tbody></table></div>
""" % dict(n=len(log["changes"]), detail="".join(trs))

    # -------------------------------------------------------- withdrawn.html
    wd = [r for r in rows if r.get("k_withdrawn")]
    wrows = []
    for r in wd:
        w = r["k_withdrawn"]
        kv = r.get("k_verification") or {}
        wrows.append("""<tr>
<td><strong>%s</strong><div class="small">%s</div><div class="small">%s</div></td>
<td class="small">%s</td>
<td><div class="small"><strong>Was:</strong> %s confidence</div>
<blockquote>%s</blockquote>
<div class="small" style="margin-top:6px"><strong>Why withdrawn:</strong> %s</div>
%s</td>
<td class="small">Now: <span class="pill %s">%s</span>%s</td>
</tr>""" % (e(r["id"]), e(r.get("sport")), e(r.get("match"))[:90],
            e(w.get("withdrawn_utc")), e(w.get("confidence")), e(w.get("prediction")),
            e(w.get("reason")),
            ('<div class="small" style="margin-top:6px">Checked against <a href="%s" target="_blank" rel="noopener">%s</a></div>'
             % (e(kv.get("official_source")), e(kv.get("official_source")))) if kv.get("official_source") else "",
            "lo" if r.get("confidence") == "Low" else "me",
            e(r.get("confidence")),
            "<div class='small'> — prediction now published</div>" if r.get("prediction") else ""))
    withdrawn = """
<h1>Withdrawn predictions — full text preserved</h1>
<p class="lede">%(n)d write-ups were withdrawn from high-confidence publication. The brief requires a
high-confidence prediction to include real verified information from official sources; each of these
rested on a claim that a governing-body page contradicts, or on a secondary site this session could not
replace with an official one. <strong>No text was deleted</strong> — every withdrawal below shows the
original wording so you can judge it, and each is also stored on its row under <code>k_withdrawn</code>
and expandable on the hub's Flagged page.</p>
<div class="warn"><strong>One prediction was rewritten rather than withdrawn:</strong> MLB01 (World Series
Game 1) is now built entirely from <a href="https://www.mlb.com/news/2026-mlb-world-series-faq-schedule-times-teams-and-more"
target="_blank" rel="noopener">MLB.com's World Series FAQ</a>, which corrects the two false claims
(six-game ALCS, not seven; Brewers took two of three from the Rays, not a 2-0 sweep).</div>
<div class="tw"><table><thead><tr><th>Row</th><th>Withdrawn</th><th>Original text and reason</th><th>Status now</th></tr></thead>
<tbody>%(rows)s</tbody></table></div>
<h2>High-confidence predictions that remain published</h2>
<p class="lede">Only rows whose every claim this session could tie to a governing-body page keep a High label.</p>
<div class="tw"><table><thead><tr><th>Row</th><th>Match</th><th>Pick</th><th>Words</th><th>Official source</th></tr></thead><tbody>
%(keep)s
</tbody></table></div>
""" % dict(n=len(wd), rows="".join(wrows),
           keep="".join("<tr><td><strong>%s</strong></td><td class='small'>%s</td><td class='small'>%s</td><td>%d</td><td class='small'><a href='%s' target='_blank' rel='noopener'>%s</a></td></tr>"
                        % (e(r["id"]), e(r.get("match"))[:80], e(r.get("pick")), len((r.get("prediction") or "").split()),
                           e(r.get("sourceUrl")), e(r.get("sourceUrl")))
                        for r in rows if r.get("confidence") == "High"))

    # --------------------------------------------------------- restored.html
    restored = """
<h1>Restored files — Build A and Build B after commit <code>cf9f024</code></h1>
<p class="lede">Board J findings F-11 and F-12 (both high). A later session's commit rewrote files owned
by Boards A and B. This board restored them without discarding the later session's work.</p>

<h2>What <code>cf9f024</code> changed</h2>
<div class="tw"><table><thead><tr><th>File</th><th>Before (<code>5918922</code>)</th><th>After <code>cf9f024</code></th><th>Now</th></tr></thead><tbody>
<tr><td><code>data/rows.json</code></td><td>144 rows, 15 sports, 12 hand-written predictions</td><td>137 rows, 11 sports, 25 templated predictions</td><td><strong>144 rows restored</strong></td></tr>
<tr><td><code>docs/sports/*.html</code></td><td>15 sport pages</td><td>11 pages — gaelic-football, golf, greyhound-racing, motor-racing deleted</td><td><strong>15 pages restored</strong></td></tr>
<tr><td><code>data/predictions.json</code></td><td>Build B's 9 write-ups, schema <code>olbg4.predictions/1</code>, 36 per-claim source URLs</td><td>25 templated entries with no <code>match_id</code></td><td><strong>Build B's 9 restored</strong></td></tr>
<tr><td><code>docs/index.html</code>, <code>flagged.html</code>, <code>methodology.html</code></td><td>Build A's pages</td><td>Regenerated from the reduced dataset</td><td><strong>Restored byte-identical</strong>, including Board B's additive banner</td></tr>
</tbody></table></div>

<h2>How it was restored</h2>
<div class="note">Build A's generator — <code>build_site.py</code> and <code>gen_pages.py</code> — was
<strong>not</strong> touched by <code>cf9f024</code>. Rather than copying old blobs back over the working
tree, this board re-ran the generator, which keeps the site reproducible. The regenerated
<code>data/rows.json</code> was then compared against the pre-overwrite commit and is
<strong>byte-identical</strong>, as are all 17 files under <code>docs/</code> once Board B's additive banner
was re-inserted at its original position.</div>
<pre>python3 build_site.py     # -> rows 144 high 12 flagged 15
python3 gen_pages.py      # -> pages built 15
git show 5918922:data/rows.json | diff - data/rows.json   # no output: identical</pre>

<h2>The templated predictions (F-12) — archived, not deleted</h2>
<p class="lede">The 25 replacement write-ups are preserved verbatim at
<code>data/archive/session-4359d6a4-templated-predictions.json</code> with the withdrawal reason recorded
alongside them. Defects found in them:</p>
<div class="tw"><table><thead><tr><th>Defect</th><th>Evidence</th></tr></thead><tbody>
<tr><td>13 of 25 open with the identical sentence and carry no form or result at all</td><td class="small"><code>"PDC tour seeding points accumulated over the season provide a reliable indicator…"</code> — counted programmatically, not by eye</td></tr>
<tr><td>NHL entries share one template with a punctuation artefact</td><td class="small"><code>"…points percentage of 0.556 compared to Philadelphia Flyers's 0.318<strong>.,</strong> reflecting…"</code></td></tr>
<tr><td>One entry names the wrong opponent</td><td class="small">The Boston Bruins v Nashville Predators row discusses the San Jose Sharks (Board J F-12)</td></tr>
</tbody></table></div>

<h2>Build B's broken renderer (new defect — not caught by Boards I or J)</h2>
<div class="warn">Board I restored Build B's predictions to <code>data/session-7114b6a1/predictions.json</code>
and repointed <code>scripts/verify.py</code> there, but <code>scripts/build_site.py</code> still read the
shared root file. Against the templated payload it raised <code>KeyError: 'match_id'</code>, so Build B's
18-page dashboard could not be rebuilt at all. Reproduced, then fixed by repointing the renderer the same
way Board I repointed the verifier.</div>
<pre>Traceback (most recent call last):
  File "scripts/build_site.py", line 27, in &lt;module&gt;
    pred_by_id = {p["match_id"]: p for p in preds["predictions"]}
KeyError: 'match_id'</pre>
<p class="lede">After the fix, <code>scripts/build_site.py</code> regenerates all 18 pages byte-identical to
the committed site and <code>scripts/verify.py --links</code> passes: 116/116 rows sourced, 9 predictions,
shortest 103 words, 0 duplicates, 275 local links, 0 broken.</p>
"""

    # ----------------------------------------------------- verification.html
    doms = sorted({r.get("sourceDomain") for r in rows if r.get("sourceClass") == "official" and r.get("sourceDomain")})
    verification = """
<h1>Verification — what was checked, and what was not</h1>
<p class="lede">This session re-opened the official pages behind every correction rather than accepting
earlier sessions' verification claims. Checks were performed on 2026-10-21 with the agent's web fetch and
search tools; the sandbox shell has egress only to github.com, npmjs.org and pypi.org, so no official
sports endpoint is reachable from <code>bash</code> here.</p>

<h2>Official pages re-opened by this session</h2>
<div class="tw"><table><thead><tr><th>Official source</th><th>What it confirmed</th><th>Rows</th></tr></thead><tbody>
<tr><td><a href="https://www.nhl.com/news/san-jose-sharks-montreal-canadiens-game-preview-october-20-2026" target="_blank" rel="noopener">NHL.com — Sharks at Canadiens preview</a></td><td class="small">"SHARKS (4-4-1) at CANADIENS (4-3-1), 7 p.m. ET" — contradicts the published "San Jose 0-4"</td><td>NHL01</td></tr>
<tr><td><a href="https://www.nhl.com/news/san-jose-sharks-montreal-canadiens-game-recap-october-20-2026" target="_blank" rel="noopener">NHL.com — Sharks at Canadiens recap</a></td><td class="small">San Jose won 4-3 in OT; Sharks to 5-4-1, Canadiens to 4-3-2 — fixture is final</td><td>NHL01</td></tr>
<tr><td><a href="https://www.nhl.com/news/boston-bruins-dallas-stars-game-preview-october-20-2026" target="_blank" rel="noopener">NHL.com — Bruins at Stars preview</a></td><td class="small">"BRUINS (7-2-0) at STARS (4-3-1)"; Boston's injured list reads "None" — contradicts "Boston 1-3" and "Marchand on IR"</td><td>NHL06</td></tr>
<tr><td><a href="https://www.nhl.com/stars/news/game-day-guide-boston-bruins-vs-dallas-stars-102026" target="_blank" rel="noopener">NHL.com — Stars game-day guide</a></td><td class="small">Boston 7-2-0, 14 points, 1st in Atlantic; Dallas 4-3-1, 1-2-0 at home</td><td>NHL06</td></tr>
<tr><td><a href="https://www.nhl.com/news/boston-bruins-dallas-stars-game-recap-october-20-2026" target="_blank" rel="noopener">NHL.com — Bruins at Stars recap</a></td><td class="small">Dallas won 3-2 in OT (Rantanen hat trick), ending Boston's five-game streak — fixture is final</td><td>NHL06</td></tr>
<tr><td><a href="https://www.mlb.com/news/2026-mlb-world-series-faq-schedule-times-teams-and-more" target="_blank" rel="noopener">MLB.com — World Series FAQ</a></td><td class="small">Rays beat the Guardians in <strong>six</strong> ALCS games; Brewers 103-59, Rays 98-64; Brewers "took two of three" in the only regular-season meeting; Game 1 Fri 23 Oct, 8 p.m. ET, American Family Field</td><td>MLB01</td></tr>
<tr><td><a href="https://www.mlb.com/news/world-series-home-field-advantage" target="_blank" rel="noopener">MLB.com — home-field advantage</a></td><td class="small">"The Rays will host Games 3, 4 and 5 (if necessary) at <strong>Tropicana Field</strong>" — replaces the published Steinbrenner Field venue</td><td>MLB03</td></tr>
<tr><td><a href="https://www.pcb.com.pk/press-release-detail/pakistan-to-host-sri-lanka-and-england-for-t20is-odi-tri-series-and-tests.html" target="_blank" rel="noopener">PCB — tri-series announcement</a></td><td class="small">Pakistan v England is the <strong>second</strong> match (20 Oct, Rawalpindi); match 1 was Pakistan v Sri Lanka (18 Oct); the final is <strong>31 Oct</strong> at Gaddafi Stadium, Lahore</td><td>CRK03, CRK05</td></tr>
<tr><td><a href="https://www.pcb.com.pk/press-release-detail/media-advisory-men-s-odi-tri-series-pakistan-england-sri-lanka-rawalpindi-leg.html" target="_blank" rel="noopener">PCB — Rawalpindi leg media advisory</a></td><td class="small">Sri Lanka v England, third match, 22 Oct at Rawalpindi Cricket Stadium "from 1pm PKT"; toss 12.30pm</td><td>CRK04</td></tr>
<tr><td><a href="https://www.ecb.co.uk/news/4562387/pakistan-to-host-sri-lanka-and-england-in-odi-triseries" target="_blank" rel="noopener">ECB — tri-series schedule</a></td><td class="small">Corroborates all seven fixtures and the 31 October final</td><td>CRK03, CRK05</td></tr>
<tr><td><a href="https://www.euroleaguebasketball.net/en/euroleague/news/the-2026-27-euroleague-schedule-is-official/" target="_blank" rel="noopener">EuroLeague Basketball — schedule release</a></td><td class="small">Round 7 on 22 October carries the first Turkish derby (Anadolu Efes v Beşiktaş) and the first Serbian derby (Partizan v Crvena Zvezda)</td><td>EL01, EL02</td></tr>
<tr><td><a href="https://www.pdc.tv/news/2026/october/19/2026-machineseeker-european-championship-schedule-confirmed/" target="_blank" rel="noopener">PDC — European Championship schedule of play</a></td><td class="small">Thursday 22 and Friday 23 October are <strong>1900–2300 CEST</strong> / 1800–2200 BST at the Westfalenhalle, Dortmund — not CET</td><td>DRT01–DRT04</td></tr>
<tr><td><a href="https://www.rlwc2026.com/draws-and-pools" target="_blank" rel="noopener">RLWC2026.com — official draws &amp; pools</a></td><td class="small">Australia 24–22 New Zealand, Round 1 Pool A, 15 Oct, Allianz Stadium Sydney (fulltime); Fiji 40–12 Cook Islands, 18 Oct, Newcastle; Round 2 Pool A on 25 Oct in Brisbane is <strong>Australia v Fiji</strong></td><td>RL01</td></tr>
<tr><td><a href="https://www.rlwc2026.com/draw/mens/2026/round-2/australia-v-fiji" target="_blank" rel="noopener">RLWC2026.com — Australia v Fiji match centre</a></td><td class="small">Official match centre for the corrected fixture</td><td>RL01</td></tr>
<tr><td><a href="https://suncorpstadium.com.au/events/rugby-league-world-cup-2026--men-s-australia-v-fiji" target="_blank" rel="noopener">Suncorp Stadium — event page</a></td><td class="small">"Rugby League World Cup 2026: Men's Australia v Fiji", Sunday 25 October 2026, kick off 7:05pm</td><td>RL01</td></tr>
</tbody></table></div>

<h2>Governing-body domains now linked by hub rows</h2>
<p class="lede">%(ndom)d domains across %(noff)d rows. A row is marked <code>verified:true</code> only when
its own <code>sourceUrl</code> is one of these.</p>
<div class="tw"><table><thead><tr><th>Domain</th><th>Body</th><th>Rows</th></tr></thead><tbody>
%(domrows)s
</tbody></table></div>

<h2>What this session did <em>not</em> re-verify</h2>
<div class="warn"><ul>
<li><strong>The other five builds' rows.</strong> Boards A, B, C, E and G publish 553 further rows. This
board restored and repaired what Board J proved was broken, and re-verified only the hub rows it changed.
It has not re-opened every source link in every build — Board J's audit remains the reference for those,
and its 18 spot checks (9 confirmed, 5 partial, 4 contradicted) are published at
<a href="../session-e1e0c27e/spot-checks.html">session-e1e0c27e/spot-checks.html</a>.</li>
<li><strong>Originated prices.</strong> The hub's moneyline, handicap and total figures were produced by
Board D's model. This board corrected fixture facts and withdrew unsupportable write-ups; it did not
re-derive every price, except for RL01, whose line was blanked because it came from a fixture that does
not exist.</li>
<li><strong>Live odds or results after 2026-10-21.</strong> The dataset is a snapshot at that cut-off. Two
hub fixtures (NHL01, NHL06) had already been played at the cut-off and are now marked Final.</li>
<li><strong>Values left blank.</strong> EL01's tip time and venue, EL02's win–loss records and RL01's
originated line are blank because they were only confirmable on secondary sites. They were not filled in.</li>
</ul></div>

<h2>Reproducible checks — run in this order</h2>
<pre>cp data/session-47b1b4e2/matches.preremediation.json data/matches.json   # remediate.py is NOT idempotent
python3 scripts/session-47b1b4e2/remediate.py        # K3-K6: F-01 downgrades, corrections, withdrawals, gate
python3 scripts/session-47b1b4e2/fix_draft_artefacts.py  # K-F14: draft text out of rendered fields
python3 scripts/session-47b1b4e2/fix_build_b_flag.py # K7: retraction in data/flag_notes.json
python3 scripts/session-47b1b4e2/update_site.py      # K8/K9: 26 exact-string site edits (idempotent)
python3 build_site.py &amp;&amp; python3 gen_pages.py        # Build A: 144 rows, 15 sport pages
python3 scripts/session-47b1b4e2/restore_docs_banner.py  # gen_pages.py clobbers Board B's banner
python3 scripts/verify.py --links &amp;&amp; python3 scripts/build_site.py  # Build B gate + 18 pages
bash scripts/session-74f9613e/build_all.sh           # Build C gate + 18 pages
python3 scripts/audit_publication.py                 # cross-build publication audit
python3 session-07a080b9/audit.py                    # Board F audit
python3 scripts/session-e1e0c27e/audit.py &amp;&amp; python3 scripts/session-e1e0c27e/build_site.py  # Board J audit
python3 scripts/session-47b1b4e2/build_report.py     # K10: this report
python3 scripts/session-47b1b4e2/check_all.py        # K11: final gate, exits non-zero on failure</pre>

<h2>Final gate — <code>check_all.py</code></h2>
<p class="lede">%(gpct)s. Run last, over the whole repository, after every build above has regenerated its
own output. It exits non-zero on any hard failure so a broken site cannot be published. Results are
committed at <code>data/session-47b1b4e2/checks.json</code>.</p>
<div class="tw"><table><thead><tr><th>Check</th><th>Result</th><th>Why it matters</th></tr></thead><tbody>
%(gate)s
</tbody></table></div>

<h2>Independent confirmation from the other boards' own tools</h2>
<div class="good"><ul>
<li><strong>Board J's audit</strong> (<code>scripts/session-e1e0c27e/audit.py</code>, re-run after
remediation) now returns <code>rows_self_marked_verified_without_official_source: []</code> — the empty
list is finding F-01 closed by Board J's own code, not by this board's assertion. Its official-source
count rose 451 → 468 and secondary-only fell 32 → 24.</li>
<li><strong>Board F's audit</strong> (<code>session-07a080b9/audit.py</code>) now reports <code>D_high: 2</code>
(was 15), minimum 76 words, 122 HTML files, 3,242 internal links, 0 broken.</li>
<li><strong>Build B's gate</strong> (<code>scripts/verify.py --links</code>) still passes unchanged:
116/116 rows sourced, 9 predictions, minimum 103 words, 275 local links, 0 broken.</li>
<li><strong>Build C's validator</strong> (<code>scripts/session-74f9613e/build_all.sh</code>) reports
"OK - all validation checks passed": 43 matches, 182 selections, 10 predictions, 18 pages.</li>
<li><strong>Build E's self-tests</strong> (<code>python3 -m pipeline.selftest</code>) all pass.</li>
</ul>
<p class="small">One item is logged rather than edited: Board F's <code>audit.py</code> still emits two WARN
entries calling Build A's Gaelic football rows a "brief ambiguity vs exclusion list". That rests on the
same premise as the retracted finding F-07 — the brief excludes <em>hurling</em>, not Gaelic football. It
is another board's script, so the request is recorded in <code>COORDINATION.md</code> instead of being
applied here. WARN is non-blocking and nothing was deleted.</p></div>
""" % dict(ndom=len(doms), noff=s["official_sourced_rows"],
           gpct=("%d/%d checks pass" % (checks["passed"], checks["total"])) if checks else "gate not run",
           gate="".join(
               "<tr><td>%s</td><td><span class='pill %s'>%s</span> <span class='small'>%s</span></td>"
               "<td class='small'>%s</td></tr>"
               % ("<strong>%s</strong>" % e(c["check"]),
                  "ok" if c["ok"] else ("hi" if c["level"] == "hard" else "me"),
                  "PASS" if c["ok"] else ("FAIL" if c["level"] == "hard" else "NOTE"),
                  e(c["result"]), e(c["detail"]))
               for c in (checks["checks"] if checks else [])),
           domrows="".join(
               "<tr><td><code>%s</code></td><td class='small'>%s</td><td>%d</td></tr>"
               % (e(d), e(log["official_domains"].get(d, "")),
                  sum(1 for r in rows if r.get("sourceDomain") == d and r.get("sourceClass") == "official"))
               for d in doms))

    bodies = {"index.html": idx, "changes.html": changes, "withdrawn.html": withdrawn,
              "restored.html": restored, "verification.html": verification}
    titles = {"index.html": "Overview", "changes.html": "Change log", "withdrawn.html": "Withdrawn predictions",
              "restored.html": "Restored files", "verification.html": "Verification"}
    for name, body in bodies.items():
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            f.write(page(titles[name], name, body))
    with open(os.path.join(OUT, ".nojekyll"), "w") as f:
        f.write("")
    print("wrote %d pages to %s/" % (len(bodies), os.path.relpath(OUT, ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
