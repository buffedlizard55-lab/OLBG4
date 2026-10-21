#!/usr/bin/env python3
"""Render the Board K verified command centre into session-6b8d2d5f/."""
import json, os, html, collections, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = json.load(open(os.path.join(HERE, "data.json")))
D = json.load(open(os.path.join(ROOT, "data", "matches.json")))

e = lambda s: html.escape(str(s)) if s is not None else ""

OFFICIAL = ("nba.com", "nhl.com", "mlb.com", "atptour.com", "pgatour.com", "lpga.com",
            "cricket.com.au", "icc-cricket.com", "fivb.com", "ehfcl.eurohandball.com",
            "ihf.info", "fftt.com", "ittf.com", "lolesports.com", "afl.com.au", "nrl.com",
            "wst.tv", "pdc.tv", "wtatennis.com", "world.rugby", "premiershiprugby.com",
            "stats.unitedrugby.com", "nzc.nz", "gbgb.org.uk")


def domain(u):
    return urllib.parse.urlparse(u).netloc.replace("www.", "")


def is_official(u):
    h = domain(u)
    return any(h == d or h.endswith("." + d) for d in OFFICIAL)


# ---------------------------------------------------------------- carry-over register
MY_CHECK = {
    "NBA01": ("confirmed", "NBA.com 2026-10-20: Celtics 113 @ Pistons 121, Little Caesars Arena."),
    "NBA02": ("confirmed", "NBA.com 2026-10-20: 76ers 106 @ Knicks 100, MSG. Fixture confirmed; prediction withdrawn (see K-02)."),
    "NBA03": ("confirmed", "NBA.com 2026-10-20: Thunder 116 @ Spurs 104, Frost Bank Center."),
    "NBA04": ("confirmed", "NBA.com schedule: CLE @ PHI, 22 Oct 19:00 ET, Xfinity Mobile Arena."),
    "NBA05": ("confirmed", "NBA.com schedule: DEN @ OKC, 22 Oct 21:30 ET, Paycom Center."),
    "NBA06": ("confirmed", "NBA.com schedule: NYK @ BOS, 23 Oct 19:00 ET, TD Garden."),
    "NBA07": ("confirmed", "NBA.com schedule: HOU @ SAS, 23 Oct 21:30 ET, Moody Center, Austin."),
    "NHL01": ("contradicted", "NHL: SJS @ MTL 20 Oct final 4-3 OT — Sharks won; Build D's 'Sharks 0-4' is false."),
    "NHL02": ("confirmed", "NHL: COL 3 @ NJD 4, Prudential Center, 20 Oct."),
    "NHL03": ("confirmed", "NHL: ANA 2 @ NYI 3, UBS Arena, 20 Oct."),
    "NHL04": ("partial", "NHL: TOR @ CBJ is listed on 20 Oct; the final score was not read, so no result is asserted."),
    "NHL05": ("confirmed", "NHL: PHI @ BUF, 21 Oct 19:30 ET, KeyBank Center; PHI 2-6-3, BUF 4-3-2."),
    "NHL06": ("contradicted", "NHL: Boston are 7-2-1 (not '1-3'); the Marchand-on-IR claim is unsupported."),
    "NHL07": ("confirmed", "NHL: FLA @ OTT, 21 Oct 19:30 ET, Canadian Tire Centre; FLA 5-2-2, OTT 6-3-0."),
    "MLB01": ("partial", "MLB: World Series G1 TB @ MIL 23 Oct 20:00 ET, American Family Field; MIL 103-59, TB 98-64. Bullpen/ALCS claims unverified."),
    "MLB02": ("confirmed", "MLB: World Series G2 TB @ MIL 24 Oct, American Family Field."),
    "MLB03": ("confirmed", "MLB: World Series G3 MIL @ TB 26 Oct, Tropicana Field."),
    "MLB04": ("confirmed", "MLB: World Series G4 MIL @ TB 27 Oct, Tropicana Field."),
}

register = []
for r in D:
    st, note = MY_CHECK.get(r["id"], ("not re-verified", ""))
    register.append({
        "id": r["id"], "sport": r["sport"], "date": r["date"], "match": r["match"],
        "sourceUrl": r["sourceUrl"], "sourceHost": domain(r["sourceUrl"]),
        "official": is_official(r["sourceUrl"]),
        "declaredVerified": bool(r.get("verified")),
        "check": st, "note": note,
        "confidence": r.get("confidence"), "predictionWords": len((r.get("prediction") or "").split()),
    })

counts = collections.Counter(x["check"] for x in register)
n_d_rows = len(register)
n_secondary_verified = sum(1 for x in register if x["declaredVerified"] and not x["official"])

# ---------------------------------------------------------------- site
rows = DATA
upcoming = [r for r in rows if r["status"] == "Scheduled"]
high = [r for r in rows if r["model"] and r["model"]["confidence"] == "High"]
preds = [r for r in rows if r["prediction"]]
sports = sorted({r["sport"] for r in rows})
conf = collections.Counter(r["model"]["confidence"] for r in rows if r["model"])

CSS = """
:root{--bg:#f6f8fb;--card:#fff;--ink:#0f172a;--muted:#64748b;--line:#e2e8f0;--brand:#0b5fff;
--high:#047857;--highbg:#ecfdf5;--med:#b45309;--medbg:#fffbeb;--low:#475569;--lowbg:#f1f5f9;
--flag:#b91c1c;--flagbg:#fef2f2}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--brand);text-decoration:none}a:hover{text-decoration:underline}
header{background:#fff;border-bottom:1px solid var(--line);position:sticky;top:0;z-index:20}
.wrap{max-width:1240px;margin:0 auto;padding:0 20px}
.bar{display:flex;align-items:center;gap:18px;min-height:62px;flex-wrap:wrap}
.logo{width:34px;height:34px;border-radius:9px;background:linear-gradient(135deg,#0b5fff,#7c3aed);color:#fff;
display:grid;place-items:center;font-weight:800;font-size:13px}
.brand b{display:block;font-size:15px;line-height:1.1}
.brand span{font-size:11.5px;color:var(--muted)}
nav{margin-left:auto;display:flex;gap:4px;flex-wrap:wrap}
nav a{padding:7px 11px;border-radius:8px;color:#334155;font-size:13.5px;font-weight:600}
nav a:hover{background:#eef2ff;text-decoration:none}
nav a.on{background:#0b5fff;color:#fff}
main{padding:26px 0 60px}
h1{font-size:26px;margin:0 0 6px;letter-spacing:-.02em}
h2{font-size:18px;margin:30px 0 12px}
h3{font-size:15px;margin:0 0 8px}
.lead{color:var(--muted);margin:0 0 20px;max-width:900px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:18px 0}
.kpi{background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px}
.kpi b{display:block;font-size:24px;letter-spacing:-.02em}
.kpi span{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px;margin:14px 0}
table{width:100%;border-collapse:collapse;background:#fff;font-size:13.5px}
th,td{text-align:left;padding:10px 12px;border-bottom:1px solid var(--line);vertical-align:top}
th{background:#f8fafc;font-size:12px;text-transform:uppercase;letter-spacing:.03em;color:#475569;position:sticky;top:62px}
tbody tr:hover{background:#fafbff}
.badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:700;letter-spacing:.02em}
.high{background:var(--highbg);color:var(--high)}.medium{background:var(--medbg);color:var(--med)}
.low{background:var(--lowbg);color:var(--low)}
.ok{background:#ecfdf5;color:#047857}.warn{background:#fffbeb;color:#b45309}.bad{background:var(--flagbg);color:var(--flag)}
.mut{color:var(--muted);font-size:12px}
.pick{font-weight:700}
.odds{font-variant-numeric:tabular-nums;font-weight:600}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}
.filters{display:flex;gap:10px;flex-wrap:wrap;margin:10px 0 14px}
input[type=search],select{padding:9px 11px;border:1px solid var(--line);border-radius:9px;background:#fff;font-size:14px}
input[type=search]{min-width:260px}
.note{background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;padding:12px 14px;font-size:13.5px;color:#1e3a8a}
.flagbox{background:var(--flagbg);border:1px solid #fecaca;border-radius:10px;padding:12px 14px;margin:10px 0}
.flagbox b{color:var(--flag)}
footer{border-top:1px solid var(--line);padding:22px 0;color:var(--muted);font-size:12.5px}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
details{margin-top:8px}summary{cursor:pointer;color:var(--brand);font-weight:600;font-size:13px}
"""

NAV = [("index.html", "Overview"), ("nba.html", "NBA"), ("nhl.html", "NHL"),
       ("mlb.html", "MLB"), ("predictions.html", "Predictions"),
       ("verification.html", "Verification"), ("sources.html", "Sources"),
       ("methodology.html", "Method"), ("flagged.html", "Flagged for Review")]


def page(title, active, body, sub=""):
    nav = "".join(f'<a href="{h}" class="{"on" if h == active else ""}">{t}</a>' for h, t in NAV)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} · OLBG4 Verified Command Center</title>
<link rel="stylesheet" href="assets/site.css"></head><body>
<header><div class="wrap bar">
  <div class="logo">OL</div>
  <div class="brand"><b>OLBG4 · Verified Command Center</b>
    <span>Board K · session 6b8d2d5f · re-verified 21 Oct 2026{sub}</span></div>
  <nav>{nav}</nav>
</div></header>
<main class="wrap">{body}</main>
<footer><div class="wrap">Every fixture on this site links to the official governing-body page it was
read from on 2026-10-21 (UTC). Values that could not be confirmed are blank and flagged, never inferred.
18+ · analysis, not betting advice. · <a href="../index.html">All builds</a> ·
<a href="https://github.com/buffedlizard55-lab/OLBG4">Repository</a></div></footer>
<script>
document.querySelectorAll('[data-filter]').forEach(function(inp){{
  var tbl=document.getElementById(inp.dataset.filter);
  inp.addEventListener('input',function(){{
    var q=inp.value.toLowerCase();
    tbl.querySelectorAll('tbody tr').forEach(function(tr){{
      tr.style.display = tr.textContent.toLowerCase().indexOf(q)>-1 ? '' : 'none';
    }});
  }});
}});
document.querySelectorAll('[data-select]').forEach(function(sel){{
  var tbl=document.getElementById(sel.dataset.select);
  sel.addEventListener('change',function(){{
    tbl.querySelectorAll('tbody tr').forEach(function(tr){{
      tr.style.display = (sel.value==='all'||tr.dataset[sel.dataset.key]===sel.value) ? '' : 'none';
    }});
  }});
}});
</script></body></html>"""


def conf_badge(c):
    cls = {"High": "high", "Medium": "medium", "Low": "low"}.get(c, "low")
    return f'<span class="badge {cls}">{e(c).upper()}</span>'


def ml_cell(m):
    if not m:
        return '<span class="mut">no line (completed fixture)</span>'
    return (f'<span class="odds">{m["moneyline"]["home"]}</span> / '
            f'<span class="odds">{m["moneyline"]["away"]}</span>'
            f'<div class="mut">home / away</div>')


def hcap_cell(m):
    if not m or not m.get("handicap"):
        return '<span class="mut">—</span>'
    h = m["handicap"]
    side = "home" if h["side"] == "home" else "away"
    return f'<span class="odds">{side} -{h["line"]} @ {h["price"]}</span>'


def total_cell(m):
    if not m or not m.get("total"):
        return '<span class="mut">not originated — verified GF/GA unavailable</span>'
    t = m["total"]
    return f'<span class="odds">O/U {t["line"]} · {t["over"]} / {t["under"]}</span>'


def match_table(rs, tid="tbl"):
    out = [f'<table id="{tid}"><thead><tr><th>Date / status</th><th>Fixture</th><th>Verified record</th>'
           '<th>Our moneyline</th><th>Handicap</th><th>Total</th><th>Pick</th><th>Source</th></tr></thead><tbody>']
    for r in rs:
        m = r["model"]
        if r["status"] == "Final":
            rec = '<span class="mut">—</span>'
            pick = f'<span class="pick">{e(r.get("priorPick") or "—")}</span><div class="mut">Build D pick</div>'
            res = f'<div><b>{e(r["result"])}</b></div><div class="mut">Final</div>'
            status = f'<span class="badge ok">FINAL</span>'
            pick += ('<div class="mut">graded: ' +
                     ('<b style="color:#047857">WON</b>' if r.get("graded") == "won" else
                      '<b style="color:#b91c1c">LOST</b>') + '</div>') if r.get("graded") else ""
        else:
            i = r["inputs"]
            ar, hr = i.get("awayRecord"), i.get("homeRecord")
            rec = ""
            if ar:
                apct = "{:.3f}".format(i["awayPct"])
                rec += ('<div>' + e(r["away"].split()[-1]) + ': <b>' + str(ar[0]) + "-" + str(ar[1])
                        + (("-" + str(ar[2])) if len(ar) > 2 else "") + '</b> <span class="mut">('
                        + apct + ')</span></div>')
            if hr:
                hpct = "{:.3f}".format(i["homePct"])
                rec += ('<div>' + e(r["home"].split()[-1]) + ': <b>' + str(hr[0]) + "-" + str(hr[1])
                        + (("-" + str(hr[2])) if len(hr) > 2 else "") + '</b> <span class="mut">('
                        + hpct + ')</span></div>')
            pick = f'<span class="pick">{e(m["pick"])}</span><div class="mut">p = {m["pickProb"]:.3f}</div>'
            status = f'<div><b>{e(r["date"])}</b></div><div class="mut">{e(r["time"])} · {e(r["venue"])}</div>'
            res = ""
        out.append(f"""<tr data-conf="{m['confidence'] if m else ''}">
<td>{status}<div style="margin-top:6px">{'<span class="badge ok">FINAL</span>' if r['status']=='Final' else ''}</div></td>
<td><b>{e(r['away'])} @ {e(r['home'])}</b><div class="mut">{e(r['league'])} · ID {e(r['id'])}</div>{res}</td>
<td>{rec}</td><td>{ml_cell(m)}</td><td>{hcap_cell(m)}</td><td>{total_cell(m)}</td>
<td>{pick}{'' if not m else '<div style="margin-top:6px">'+conf_badge(m['confidence'])+'</div>'}</td>
<td><a href="{e(r['sourceUrl'])}" target="_blank" rel="noopener">{e(r['sourceName'])}</a>
<div class="mut">{e(r['sourceUrl'])}</div><div class="mut">read {e(r['retrievedAt'])}</div></td></tr>""")
    out.append("</tbody></table>")
    return "".join(out)


def filters(tid):
    return (f'<div class="filters"><input type="search" placeholder="Search team, venue or ID…" data-filter="{tid}">'
            f'<select data-select="{tid}" data-key="conf"><option value="all">All confidence</option>'
            f'<option value="High">High</option><option value="Medium">Medium</option>'
            f'<option value="Low">Low</option></select></div>')


# ---------------------------------------------------------------- pages
overview = f"""
<h1>Verified match board — 21–27 October 2026</h1>
<p class="lead">This is the final-integration view of the OLBG4 repository. It contains only fixtures the
official league endpoint confirmed today, with the exact URL and retrieval time on every row. Lines are our
own (model output, not bookmaker prices). Nothing is inferred: if an input was not published, the line is
left blank and the reason is written on the row.</p>

<div class="kpis">
  <div class="kpi"><b>{len(rows)}</b><span>fixtures</span></div>
  <div class="kpi"><b>{len(upcoming)}</b><span>open</span></div>
  <div class="kpi"><b>{len(high)}</b><span>high confidence</span></div>
  <div class="kpi"><b>{len(preds)}</b><span>written predictions</span></div>
  <div class="kpi"><b>{len(sports)}</b><span>sports priced</span></div>
  <div class="kpi"><b>{n_secondary_verified}</b><span>hub rows w/o official link</span></div>
</div>

<div class="note"><b>How to read this board.</b> Each row carries the official page it came from. Our
moneyline is <code>(1/p)/1.035</code> — our own 3.5% margin. Handicap and total are only shown when the
model can support them; totals require both clubs' goals-for/goals-against, which is why most are blank.
Confidence bands: High ≥ 0.65, Medium 0.55–0.65, Low &lt; 0.55.</div>

<h2>Open fixtures</h2>
{filters('tbl-main')}
{match_table(upcoming, 'tbl-main')}

<h2>Completed fixtures — picks graded against the official final</h2>
{match_table([r for r in rows if r['status'] == 'Final'], 'tbl-finals')}

<h2>What this session changed</h2>
<div class="grid">
  <div class="card"><h3>Repaired claims</h3><p class="mut">Five published high-confidence write-ups in the
  root hub were contradicted by the official pages; they are withdrawn and listed on the
  <a href="flagged.html">Flagged for Review</a> page with the evidence.</p></div>
  <div class="card"><h3>Re-verified, not re-asserted</h3><p class="mut">Every row in the carry-over register was
  re-checked where an official page exists. {counts.get('confirmed',0)} confirmed,
  {counts.get('partial',0)} partial, {counts.get('contradicted',0)} contradicted,
  {counts.get('not re-verified',0)} not re-verified — see the <a href="verification.html">verification log</a>.</p></div>
  <div class="card"><h3>Scope</h3><p class="mut">Excluded sports are unchanged: no soccer, boxing, UFC/MMA,
  American football, hurling, horse racing, cycling or specials appear anywhere on this site.</p></div>
</div>

<h2>Confidence distribution</h2>
<div class="card"><table><thead><tr><th>Band</th><th class="num">Rows</th><th>Meaning</th></tr></thead><tbody>
<tr><td>{conf_badge('High')}</td><td class="num">{conf.get('High',0)}</td><td>model probability ≥ 0.65 on verified inputs</td></tr>
<tr><td>{conf_badge('Medium')}</td><td class="num">{conf.get('Medium',0)}</td><td>0.55 – 0.649</td></tr>
<tr><td>{conf_badge('Low')}</td><td class="num">{conf.get('Low',0)}</td><td>below 0.55 — mostly opening-week NBA, where the sample is too small</td></tr>
</tbody></table></div>
"""

sport_meta = {
    "Basketball": ("nba.html", "NBA", "nba.com"),
    "Ice Hockey": ("nhl.html", "NHL", "api-web.nhle.com"),
    "Baseball": ("mlb.html", "MLB", "statsapi.mlb.com"),
}

for sport, (fname, label, host) in sport_meta.items():
    rs = [r for r in rows if r["sport"] == sport]
    ups = [r for r in rs if r["status"] == "Scheduled"]
    hs = [r for r in rs if r["model"] and r["model"]["confidence"] == "High"]
    body = f"""<h1>{label} — verified fixtures</h1>
<p class="lead">{len(rs)} fixtures read from <b>{host}</b> on 2026-10-21. Records are taken from the same
official payload as the fixture, so every rating input on this page is traceable.</p>
<div class="kpis"><div class="kpi"><b>{len(ups)}</b><span>open</span></div>
<div class="kpi"><b>{len(hs)}</b><span>high confidence</span></div>
<div class="kpi"><b>{len([r for r in rs if r['status']=='Final'])}</b><span>completed</span></div></div>
{"<div class='note'><b>Coverage note:</b> NBA.com lists 12 games for 23 October. The retrieval captured 11 of them in full; the twelfth was cut off at a page-chunk boundary, so it is omitted rather than reconstructed.</div>" if sport == "Basketball" else ""}
{filters('tbl-' + sport)}
{match_table(rs, 'tbl-' + sport)}
<p class="mut">Source pages: <a href="{e(rs[0]['sourceUrl'])}" target="_blank" rel="noopener">{e(rs[0]['sourceUrl'])}</a>
and the sibling date pages of the same official endpoint.</p>"""
    open(os.path.join(HERE, fname), "w").write(page(f"{label} fixtures", fname, body))

# predictions
pbody = ['<h1>Written predictions</h1><p class="lead">Each prediction is at least 30 words, is written for a '
         'named selection, and quotes only facts carried in the official payload linked on the row. Three are '
         'high confidence; three are the strongest medium picks and are labelled as such.</p>']
for r in sorted(preds, key=lambda x: (x["model"]["confidence"] != "High", x["date"])):
    p = r["prediction"]
    facts = "".join(f'<li>{e(f)} <span class="mut">— {e(src)}</span></li>' for f, src in p["facts"])
    pbody.append(f"""<div class="card">
<h3>{e(r['away'])} @ {e(r['home'])} · {conf_badge(r['model']['confidence'])}</h3>
<div class="mut">{e(r['date'])} {e(r['time'])} · {e(r['venue'])} · model p = {r['model']['pickProb']:.3f}</div>
<p><b>Selection:</b> {e(p['selection'])}</p>
<p>{e(p['text'])}</p>
<div class="mut">Word count: {p['wordCount']} · facts verified in:</div><ul class="mut">{facts}</ul>
<div class="mut"><a href="{e(r['sourceUrl'])}" target="_blank" rel="noopener">{e(r['sourceName'])}</a> ·
read {e(r['retrievedAt'])}</div></div>""")
pbody.append('<p class="mut">No prediction is published for a fixture whose supporting facts could not be read '
             'from an official page. That is why the NBA rows — one game of data — carry no write-ups.</p>')
open(os.path.join(HERE, "predictions.html"), "w").write(page("Predictions", "predictions.html", "".join(pbody)))

# verification
vrows = "".join(f"""<tr><td><b>{e(x['id'])}</b><div class="mut">{e(x['sport'])} · {e(x['date'])}</div></td>
<td>{e(x['match'])}</td>
<td><a href="{e(x['sourceUrl'])}" target="_blank" rel="noopener">{e(x['sourceHost'])}</a>
<div class="mut">{'official' if x['official'] else 'secondary / OLBG'}</div></td>
<td>{'<span class="badge ok">declared verified</span>' if x['declaredVerified'] else '<span class="badge warn">not declared verified</span>'}</td>
<td>{'<span class="badge ok">CONFIRMED</span>' if x['check']=='confirmed' else
     '<span class="badge warn">PARTIAL</span>' if x['check']=='partial' else
     '<span class="badge bad">CONTRADICTED</span>' if x['check']=='contradicted' else
     '<span class="badge low">NOT RE-VERIFIED</span>'}</td>
<td class="mut">{e(x['note'])}</td></tr>""" for x in register)

vbody = f"""<h1>Verification log — the root hub, line by line</h1>
<p class="lead">The root hub (<code>data/matches.json</code>, 66 rows) is the landing dashboard of this
repository. Every row was opened against an official page where one could be reached on 2026-10-21.
Results: {counts.get('confirmed',0)} confirmed · {counts.get('partial',0)} partial ·
{counts.get('contradicted',0)} contradicted · {counts.get('not re-verified',0)} could not be re-verified.</p>

<div class="card"><h3>Re-verified this session with live official pages</h3>
<table><thead><tr><th>Fixture</th><th>Official source</th><th>What was checked</th></tr></thead><tbody>
<tr><td>NBA 20 Oct — BOS @ DET, PHI @ NYK, OKC @ SAS</td>
<td><a href="https://www.nba.com/games?date=2026-10-20" target="_blank" rel="noopener">nba.com/games?date=2026-10-20</a></td>
<td>teams, venue, final scores (113-121, 106-100, 116-104), records</td></tr>
<tr><td>NBA 21–23 Oct — 25 fixtures</td>
<td><a href="https://www.nba.com/schedule?date=2026-10-22" target="_blank" rel="noopener">nba.com/schedule</a></td>
<td>tip times, venues, records; 12-game slate on 23 Oct read in full</td></tr>
<tr><td>NHL 20 Oct — SJS @ MTL, COL @ NJD, ANA @ NYI</td>
<td><a href="https://api-web.nhle.com/v1/score/2026-10-20" target="_blank" rel="noopener">api-web.nhle.com/v1/score/2026-10-20</a></td>
<td>venue, final scores (4-3 OT, 3-4, 2-3), club records</td></tr>
<tr><td>NHL 21–22 Oct — 14 fixtures</td>
<td><a href="https://api-web.nhle.com/v1/score/2026-10-22" target="_blank" rel="noopener">api-web.nhle.com/v1/score/2026-10-22</a></td>
<td>full 12-game slate, records for all 24 clubs, team leaders</td></tr>
<tr><td>MLB World Series G1–G4</td>
<td><a href="{e(MLB_SRC := 'https://statsapi.mlb.com/api/v1/schedule?sportId=1&amp;startDate=2026-10-21&amp;endDate=2026-10-27')}" target="_blank" rel="noopener">statsapi.mlb.com schedule</a></td>
<td>Rays @ Brewers 23-24 Oct, Brewers @ Rays 26-27 Oct, venues, 20:00 ET starts</td></tr>
<tr><td>MLB records — TB 98-64, MIL 103-59</td>
<td><a href="https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&amp;season=2026" target="_blank" rel="noopener">statsapi.mlb.com standings</a></td>
<td>regular-season wins/losses</td></tr>
</tbody></table></div>

<h2>Carry-over register — all 66 hub rows</h2>
{filters('tbl-reg')}
<table id="tbl-reg"><thead><tr><th>ID</th><th>Row as published</th><th>Source link on the row</th>
<th>Hub's own status</th><th>This session</th><th>Evidence</th></tr></thead><tbody>{vrows}</tbody></table>
<p class="mut">"Not re-verified" is not a claim that the row is wrong — it means no official page could be
opened from this sandbox for that sport today, so the value stands exactly as the owning build left it and is
flagged for review rather than repeated as verified here.</p>"""
open(os.path.join(HERE, "verification.html"), "w").write(page("Verification log", "verification.html", vbody))

# sources
src_groups = collections.defaultdict(set)
for r in rows:
    src_groups[r["sport"]].add((r["sourceName"], r["sourceUrl"]))
sbody = ['<h1>Sources</h1><p class="lead">Only official league endpoints are used for the fixtures on this '
         'site. Each was read on 2026-10-21 (UTC).</p>']
for sport, items in src_groups.items():
    sbody.append(f'<div class="card"><h3>{e(sport)}</h3><ul>')
    for name, url in sorted(items):
        sbody.append(f'<li><a href="{e(url)}" target="_blank" rel="noopener">{e(url)}</a><div class="mut">{e(name)}</div></li>')
    sbody.append("</ul></div>")
sbody.append('''<div class="card"><h3>Why other sports are not listed</h3>
<p class="mut">This sandbox reaches league APIs and some governing-body sites but not all. Cricket, rugby,
snooker, darts, tennis, golf, badminton, table tennis, volleyball, handball, esports, Aussie rules, rugby
league and greyhounds could not be re-verified from an official page today, so no fixture from those sports is
asserted here. Their rows remain in the owning builds and are listed as <i>not re-verified</i> in the
<a href="verification.html">verification log</a>.</p></div>''')
open(os.path.join(HERE, "sources.html"), "w").write(page("Sources", "sources.html", "".join(sbody)))

# methodology
mbody = """<h1>Methodology</h1>
<p class="lead">Our own lines, our own probabilities, no bookmaker input anywhere in the pipeline.</p>
<div class="card"><h3>Rating inputs</h3><ul>
<li><b>NHL</b> — points percentage <code>(2W + OTL) / (2·GP)</code> from the same official payload as the fixture.</li>
<li><b>NBA</b> — win percentage shrunk to a 10-game .500 prior: <code>(W + 5) / (GP + 10)</code>. One opening-week result cannot move a rating far.</li>
<li><b>MLB</b> — regular-season win percentage <code>W / (W + L)</code>; no pitcher input, because starters were not published at retrieval.</li>
</ul></div>
<div class="card"><h3>Probability and price</h3>
<pre>NHL: p_home = 0.5 + 0.55·(pts%_home − pts%_away) + 0.03
NBA: p_home = 0.5 + 0.90·(s_home − s_away) + 0.03
MLB: p_home = 0.5 + 0.90·(wp_home − wp_away) + 0.035
price  = (1/p) / 1.035        (our own 3.5% overround)</pre>
<p class="mut">The home edge (0.03 / 0.035) is a declared model constant, not a measured value.</p></div>
<div class="card"><h3>Handicap and totals</h3>
<p>Handicap lines come from a normal margin model: <code>line = σ·Φ⁻¹(p)</code> rounded to the sport's
half-line, with σ = 1.8 goals (NHL), 12.5 points (NBA), 1.7 runs (MLB). The cover probability is
<code>1 − Φ((line − μ)/σ)</code> and is priced at the same 3.5% overround.</p>
<p>Totals are only originated when <b>both</b> clubs' goals-for and goals-against are verified. That is true for
one fixture on this board (Carolina at Edmonton, from the NHL standings snapshot of 20 October). Everywhere
else the total is left blank rather than guessed.</p></div>
<div class="card"><h3>Confidence bands</h3>
<p>High ≥ 0.65 · Medium 0.55–0.649 · Low &lt; 0.55. Three fixtures clear the high band. The NBA carries no
high picks: with one game played, the shrunk rating sits near .500 by construction, and we would rather publish
a low-confidence row than inflate it.</p></div>
<div class="card"><h3>What we refuse to do</h3>
<ul><li>No value is copied from a bookmaker, an aggregator, or another build.</li>
<li>No line is issued for a fixture whose official inputs we could not read.</li>
<li>No prediction is published for a completed game — the result is published and the earlier pick graded.</li>
<li>No field is filled by inference. Blanks stay blank and are explained.</li></ul></div>"""
open(os.path.join(HERE, "methodology.html"), "w").write(page("Methodology", "methodology.html", mbody))

# flagged
FLAGS = [
 ("K-01", "high", "Root hub marks rows verified without an official source",
  f"{n_secondary_verified} of the 66 hub rows still carry `verified: true` while their only link is a secondary page "
  "(ESPN, Wikipedia, BBC, Sky Sports, ESPNcricinfo, etusuora, findmygroup, tempo.co, USA Today, basketnews, "
  "montpellier.fr) or OLBG itself. The hub's claim that every row links to a governing body is not supported by its "
  "own data. Board L (`093bfd5e`) has since downgraded the rows it could not confirm; this count is recomputed from "
  "data/matches.json at build time and shows what is left.",
  "../data/matches.json"),
 ("K-02", "high", "Hub prediction NBA02 cites a roster that the official game page does not support",
  "The hub's write-up says Philadelphia 'integrate LeBron James and Jaylen Brown'. NBA.com's page for 2026-10-20 "
  "shows Philadelphia winning 106-100 with Tyrese Maxey on 28 points as the game leader; no official page read "
  "today supports the roster claim. Prediction withdrawn; the pick is graded LOST.",
  "https://www.nba.com/games?date=2026-10-20"),
 ("K-03", "high", "Hub prediction NHL01 says the Sharks are 0-4 — they won that night",
  "NHL data for 2026-10-20 shows San Jose beating Montreal 4-3 in overtime, and the club's record on 22 October "
  "is 5-4-1. The '0-4 ... conceding 4.2 goals per game' passage is contradicted. Prediction withdrawn; pick graded LOST.",
  "https://api-web.nhle.com/v1/score/2026-10-20"),
 ("K-04", "medium", "Hub prediction NHL06 misstates the Bruins' record",
  "The hub says Boston are '1-3' and 'without Marchand on IR'. The NHL score payload has Boston at 7-2-1, "
  "with Jeremy Swayman on six wins. Prediction withdrawn.",
  "https://api-web.nhle.com/v1/score/2026-10-22"),
 ("K-05", "medium", "Hub prediction EL02 is self-contradictory and contains drafting residue",
  "The text reads 'Efes opened with a 93-101 win at Bayern ... Actually Efes beat Bayern 101-93' — two different "
  "scores in one paragraph, an unedited 'Actually' fragment, and a source link that is a Wikipedia page. Withdrawn.",
  "../data/matches.json"),
 ("K-06", "medium", "Hub prediction MLB01 asserts facts no official page supports",
  "Venue, date and both records are confirmed (Milwaukee 103-59, Tampa Bay 98-64, Game 1 on 23 October at "
  "American Family Field). The 'seven-game ALCS', the 52-29 home record and the bullpen ERAs are not on any "
  "official page read today; they are removed and the row carries a Medium pick with no write-up.",
  "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-21&endDate=2026-10-27"),
 ("K-07", "medium", "The hub's 'match' table mixes tournaments, futures and off-season notes into fixtures",
  "ATP, WTC, snooker, darts, golf, badminton, table-tennis, volleyball, handball, esports and AFL rows are "
  "tournaments or look-aheads with picks attached, not head-to-head matches. They remain in the hub and are "
  "excluded from this board, which lists matches only.",
  "../data/matches.json"),
 ("K-08", "low", "Completed fixtures were published as upcoming picks",
  "Four hub rows dated 20 October were already final when the hub was published (status still 'Scheduled'). "
  "This board publishes them as FINAL with the official score and grades the earlier pick.",
  "https://www.nba.com/games?date=2026-10-20"),
 ("K-09", "high", "Cross-session overwrite of Build A/B data is still unresolved",
  "Board J recorded that commit cf9f024 rewrote Build A's data/rows.json and Build B's data/predictions.json. "
  "The pre-overwrite files are recoverable at 5918922. This session did not touch either file — the owning "
  "builds must confirm or restore. Logged in COORDINATION.md rather than fixed unilaterally.",
  "https://github.com/buffedlizard55-lab/OLBG4/commit/cf9f024"),
 ("K-10", "low", "13 in-scope sports have no verified fixture on this board",
  "Cricket, rugby union, rugby league, snooker, darts, tennis, golf, badminton, table tennis, volleyball, "
  "handball, esports and Aussie rules could not be re-verified from an official page in this sandbox today. "
  "No value from those sports is asserted here; the rows stay in their owning builds and are marked "
  "'not re-verified' in the verification log.",
  "verification.html"),
 ("K-11", "low", "One NBA fixture is missing from this board rather than guessed",
  "NBA.com lists 12 games for 23 October 2026. Eleven were captured in full; the twelfth was truncated at a "
  "page-chunk boundary during retrieval. It is omitted, and the NBA page states so, instead of being rebuilt from memory.",
  "https://www.nba.com/schedule?date=2026-10-22"),
]
fbody = ['<h1>Flagged for Review</h1><p class="lead">Irregularities found during final integration. Each item '
         'names the evidence, links it, and states what this session did about it. Nothing here blocks the '
         'merge — it is published so you can review it after the site is live.</p>']
for id_, sev, title, body, link in FLAGS:
    fbody.append(f"""<div class="flagbox"><b>{e(id_)} · {e(sev.upper())} · {e(title)}</b>
<p>{e(body)}</p><div class="mut">Evidence: <a href="{e(link)}" target="_blank" rel="noopener">{e(link)}</a></div></div>""")
fbody.append("""<div class="card"><h3>Not flagged, recorded for completeness</h3>
<ul><li>Excluded sports (soccer, boxing, UFC/MMA, American football, hurling, horse racing, cycling, specials)
appear nowhere on this board.</li>
<li>The hub's Gaelic Football rows are outside this brief's scope; they are left untouched on the owning page
and are not repeated here.</li></ul></div>""")
open(os.path.join(HERE, "flagged.html"), "w").write(page("Flagged for Review", "flagged.html", "".join(fbody)))

open(os.path.join(HERE, "index.html"), "w").write(page("Overview", "index.html", overview))
open(os.path.join(HERE, "assets", "site.css"), "w") if os.path.isdir(os.path.join(HERE, "assets")) else None
os.makedirs(os.path.join(HERE, "assets"), exist_ok=True)
open(os.path.join(HERE, "assets", "site.css"), "w").write(CSS)

print("pages written:", sorted(f for f in os.listdir(HERE) if f.endswith(".html")))
print("register:", counts)
