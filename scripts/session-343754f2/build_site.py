"""Board BW (arena/343754f2-olbg4) — site builder.

Builds the zero-CDN executive dashboard under `session-343754f2/`:
  index.html            executive summary + highest-confidence picks + coverage
  sports/<slug>.html    every row, every table row carrying its official source link
  predictions.html      the written picks (top five per covered sport)
  review.html           line-by-line review trail (per-row checks)
  flagged.html          gaps and irregularities, strictly non-blocking
  methodology.html      originated-line math, window rule, assumptions
  sources.html          official source registry for this board
Every table row carries its official source link; unconfirmed values are blank
plus a flag chip — never inferred. Requires review.py + build inputs to exist.
"""
from __future__ import annotations

import html
import importlib.util
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(ROOT, "data", "session-343754f2")
SITE = os.path.join(ROOT, "session-343754f2")

SPORTS = ["Ice Hockey", "Basketball", "Baseball", "Tennis", "Handball", "Volleyball",
          "Rugby Union", "Cricket", "Darts", "Snooker", "Golf", "Motor Racing",
          "Gaelic Sports", "Greyhounds", "Rugby League"]


def esc(x) -> str:
    return html.escape(str(x if x not in (None, "") else ""))


def load_bank():
    spec = importlib.util.spec_from_file_location(
        "pb", os.path.join(HERE, "predictions_bank.py"))
    pb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pb)
    return dict(pb.PREDICTIONS)


def css() -> str:
    return """:root{--ink:#10141d;--paper:#f6f7f9;--line:#d9dde3;--hi:#0b7a3d;--mid:#b98a00;--low:#8a8f98;--acc:#1c4fd8}
*{box-sizing:border-box}body{margin:0;font:16px/1.55 -apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:var(--ink);background:var(--paper)}
header{background:var(--ink);color:#fff;padding:20px 24px}header h1{margin:0 0 4px;font-size:1.35rem}header .sub{color:#c7cdd6;font-size:.9rem}
nav{background:#1b2230;padding:8px 24px;display:flex;flex-wrap:wrap;gap:4px}nav a{color:#dfe4ec;text-decoration:none;font-size:.86rem;padding:4px 10px;border-radius:6px}nav a:hover,nav a.on{background:#2c3650;color:#fff}
main{max-width:1180px;margin:0 auto;padding:22px 24px 60px}
h2{font-size:1.15rem;margin:28px 0 10px}h3{font-size:1rem;margin:18px 0 8px}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:12px;margin:14px 0}
.card{background:#fff;border:1px solid var(--line);border-radius:10px;padding:14px}
.card .n{font-size:1.5rem;font-weight:700}.card .t{font-size:.8rem;color:#5a6270}
table{border-collapse:collapse;width:100%;background:#fff;font-size:.86rem;margin:10px 0}
th,td{border:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}
th{background:#eef1f5;position:sticky;top:0}
td.num{text-align:right;white-space:nowrap}
.pill{display:inline-block;font-size:.72rem;font-weight:700;padding:2px 8px;border-radius:999px}
.pill.High{background:#d9f2e3;color:var(--hi)}.pill.Medium{background:#f6ecc8;color:#7a5c00}.pill.Low{background:#e8eaee;color:#565d68}
.chip{display:inline-block;font-size:.72rem;background:#fdeaea;color:#a02222;border:1px solid #efc9c9;border-radius:6px;padding:1px 6px;text-decoration:none;white-space:nowrap}
.src{font-size:.78rem;white-space:nowrap}
.blank{color:#b6bcc6}
.pred{background:#fff;border:1px solid var(--line);border-left:4px solid var(--acc);border-radius:8px;padding:12px 16px;margin:10px 0}
.pred .meta{font-size:.78rem;color:#5a6270;margin-bottom:6px}
footer{color:#7a828e;font-size:.8rem;padding:18px 24px;border-top:1px solid var(--line)}
a{color:var(--acc)}
"""


def layout(title: str, active: str, body: str, depth: int = 0) -> str:
    nav_items = [("index.html", "Summary"), ("sports/ice-hockey.html", "Ice Hockey"),
                 ("sports/basketball.html", "Basketball"), ("sports/baseball.html", "Baseball"),
                 ("sports/tennis.html", "Tennis"), ("sports/handball.html", "Handball"),
                 ("sports/volleyball.html", "Volleyball"), ("sports/rugby-union.html", "Rugby Union"),
                 ("sports/cricket.html", "Cricket"), ("sports/darts.html", "Darts"),
                 ("sports/snooker.html", "Snooker"), ("sports/golf.html", "Golf"),
                 ("sports/motor-racing.html", "Motor Racing"), ("sports/gaelic-sports.html", "Gaelic"),
                 ("sports/greyhounds.html", "Greyhounds"), ("sports/rugby-league.html", "Rugby League"),
                 ("predictions.html", "Predictions"), ("review.html", "Review"),
                 ("flagged.html", "Flagged"), ("methodology.html", "Methodology"),
                 ("sources.html", "Sources")]
    pre = "" if depth == 0 else "../"
    href = lambda t: t if t.startswith("http") else pre + t
    items = []
    for t, lbl in nav_items:
        cls = ' class="on"' if t == active else ""
        items.append(f'<a href="{href(t)}"{cls}>{lbl}</a>')
    nav_html = "".join(items)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} — OLBG4 Board BW</title>
<link rel="stylesheet" href="{pre}assets/style.css"></head>
<body><header><h1>OLBG4 — Board BW · Line-Origination Desk</h1>
<div class="sub">Session arena/343754f2-olbg4 · 15-sport scope · every price is originated, every row links its official source · built 2026-10-23</div></header>
<nav>{nav_html}</nav><main>{body}</main>
<footer>Originated lines are this board's own documented computation from official sources — not bookmaker prices. Blank values are blank because no official source confirmed them; each blank links a Flagged entry. <a href="https://github.com/buffedlizard55-lab/OLBG4/tree/arena/343754f2-olbg4">repository</a></footer></body></html>"""


def pick_pill(r) -> str:
    c = r.get("confidence")
    return f'<span class="pill {esc(c)}">{esc(c)}</span>' if c else '<span class="blank">—</span>'


def flag_chips(flags_by_row, rid) -> str:
    ids = flags_by_row.get(rid, [])
    if not ids:
        return ""
    return " ".join(f'<a class="chip" href="flagged.html#{esc(f)}" title="unconfirmed detail">{esc(f)}</a>'
                    for f in ids)


def sport_table(rows, flags_by_row, depth=1) -> str:
    pre = "" if depth == 0 else "../"
    out = ["<table><thead><tr><th>Matchup</th><th>Start (UTC)</th><th>Our pick</th>"
           "<th>Fair price</th><th>Conf.</th><th>Inputs &amp; source</th><th>Flags</th></tr></thead><tbody>"]
    for r in rows:
        rid = r["id"]
        start_disp = (r.get("start_utc") or "")[:16] or r.get("start_date") or ""
        start = esc(start_disp) or '<span class="blank">not published</span>'
        if r.get("priced"):
            pick = f"{esc(r['pick'])}"
            amv = r.get("pick_fair_american")
            price = f"{amv:+d}" if isinstance(amv, int) else esc(amv or "")
            price_cell = f"<td class='num'>{price}</td>"
            pick_cell = f"<td><strong>{pick}</strong><br><span class='blank'>p={r.get('pick_prob')}</span></td>"
        else:
            pick_cell = "<td><span class='blank'>no originated price — inputs missing</span></td>"
            price_cell = "<td class='num'><span class='blank'>—</span></td>"
        src = (f"<a class='src' href='{esc(r.get('official_url'))}' target='_blank' rel='noopener'>"
               f"{esc(r.get('official_source_name'))}</a>"
               f"<br><span class='blank'>{esc(rid)} · capture {esc(r.get('capture_stamp'))}</span>")
        out.append(f"<tr id='{esc(rid)}'><td>{esc(r.get('matchup'))}"
                   f"<br><span class='blank'>{esc(r.get('competition'))}{(' · ' + r['venue']) if r.get('venue') else ''}</span></td>"
                   f"<td>{start}</td>{pick_cell}{price_cell}<td>{pick_pill(r)}</td>"
                   f"<td>{src}</td><td>{flag_chips(flags_by_row, rid)}</td></tr>")
    out.append("</tbody></table>")
    return "\n".join(out)


def main() -> int:
    desk = json.load(open(os.path.join(DATA, "desk.json")))
    flagged = json.load(open(os.path.join(DATA, "flagged.json")))
    review = json.load(open(os.path.join(DATA, "review.json")))
    bank = load_bank()
    rows = desk["rows"]
    summary = desk["summary"]
    flags_by_row = {}
    for f in flagged["flags"]:
        for rid in [f["row_id"]] if f.get("row_id") else f.get("rows", []):
            flags_by_row.setdefault(rid, []).append(f["id"])

    os.makedirs(SITE, exist_ok=True)
    os.makedirs(os.path.join(SITE, "sports"), exist_ok=True)
    os.makedirs(os.path.join(SITE, "assets"), exist_ok=True)
    open(os.path.join(SITE, "assets", "style.css"), "w").write(css())

    by_sport = {}
    for r in rows:
        by_sport.setdefault(r["sport"], []).append(r)

    # ---------- index ----------
    high_rows = [r for r in rows if r.get("confidence") == "High" and r.get("in_window")]
    high_rows.sort(key=lambda r: -r["pick_prob"])
    idx = ["<h2>Executive summary — highest-confidence originated picks (all in the −250…+10,000 window)</h2>",
           "<div class='cards'>",
           f"<div class='card'><div class='n'>{summary['rows']}</div><div class='t'>rows across the 15-sport brief</div></div>",
           f"<div class='card'><div class='n'>{summary['priced']}</div><div class='t'>rows with originated prices</div></div>",
           f"<div class='card'><div class='n'>{summary['high_in_window']}</div><div class='t'>high-confidence picks inside the window</div></div>",
           f"<div class='card'><div class='n'>{len(flagged['flags'])}</div><div class='t'>flagged gaps (non-blocking, linked per row)</div></div>",
           f"<div class='card'><div class='n'>{len(bank)}</div><div class='t'>written predictions (top five per priced sport)</div></div>",
           "</div>",
           "<table><thead><tr><th>Matchup</th><th>Kick-off (UTC)</th><th>Market</th><th>Selection</th>"
           "<th>Fair price</th><th>Win prob.</th><th>Source</th></tr></thead><tbody>"]
    for r in high_rows:
        am = r["pick_fair_american"]
        idx.append(f"<tr><td>{esc(r['matchup'])}</td><td>{esc((r.get('start_utc') or '')[:16] or r.get('start_date') or '')}</td>"
                   f"<td>{esc(r['pick_market'])}</td><td><strong>{esc(r['pick'])}</strong></td>"
                   f"<td class='num'>{am:+d}</td><td class='num'>{r['pick_prob']}</td>"
                   f"<td><a class='src' href='{esc(r['official_url'])}' target='_blank' rel='noopener'>{esc(r['official_source_name'])}</a></td></tr>")
    idx.append("</tbody></table>")
    idx.append("<h2>Coverage by sport</h2><table><thead><tr><th>Sport</th><th>Rows</th><th>Priced</th>"
               "<th>Written predictions</th><th>Why blanks exist</th></tr></thead><tbody>")
    for sp in SPORTS:
        srows = by_sport.get(sp, [])
        npriced = sum(1 for r in srows if r["priced"])
        npred = sum(1 for rid, _ in bank.items()
                    if any(r["id"] == rid and r["sport"] == sp for r in rows))
        spflags = [f for f in flagged["flags"] if f["sport"] == sp]
        why = "; ".join(esc(f["title"]) for f in spflags[:2]) or "—"
        slug = srows[0]['sport_slug'] if srows else sp.lower().replace(' ', '-')
        idx.append(f"<tr><td><a href='sports/{esc(slug)}.html'>{esc(sp)}</a></td>"
                   f"<td class='num'>{len(srows)}</td><td class='num'>{npriced}</td>"
                   f"<td class='num'>{npred}</td><td>{why}</td></tr>")
    idx.append("</tbody></table>")
    idx.append("<p>The <strong>−250…+10,000 window</strong>: every published fair price must fall inside it, and a "
               "high-confidence label additionally requires a win probability of at least 70%. Fair price −250 equals "
               "decimal 1.40 (1/1.40 = 71.43%), so the two rules together pin every High pick between 70.0% and 71.4% "
               "(−250 to −233). Everything else is published with its tier but never sold as high confidence — the "
               "<a href='methodology.html'>methodology page</a> shows the arithmetic.</p>")
    open(os.path.join(SITE, "index.html"), "w").write(layout("Executive Summary", "index.html", "\n".join(idx)))

    # ---------- sport pages ----------
    for sp in SPORTS:
        srows = by_sport.get(sp, [])
        slug = srows[0]["sport_slug"] if srows else sp.lower().replace(" ", "-")
        preds_for_sport = [(rid, t) for rid, t in bank.items()
                           if any(r["id"] == rid and r["sport"] == sp for r in rows)]
        body = [f"<h2>{esc(sp)} — all rows</h2>"]
        if not srows:
            sp_flags = [f for f in flagged["flags"] if f["sport"] == sp]
            body.append(f"<p>No {esc(sp)} fixtures were listed by the captured sources at build time. ")
            if sp_flags:
                body.append("Gaps: " + "; ".join(
                    f"<a href='../flagged.html#{esc(f['id'])}'>{esc(f['id'])} {esc(f['title'])}</a>" for f in sp_flags))
            body.append("</p>")
        else:
            npriced = sum(1 for r in srows if r["priced"])
            body.append(f"<p>{len(srows)} rows · {npriced} priced · capture cut-off 2026-10-23T19:36Z. "
                        f"Blank prices link to a Flagged entry explaining exactly which input is missing.</p>")
            body.append(sport_table(srows, flags_by_row, depth=1))
        if preds_for_sport:
            body.append(f"<h3>Written picks — {esc(sp)}</h3>")
            for rid, t in preds_for_sport:
                r = next(x for x in rows if x["id"] == rid)
                body.append(f"<div class='pred'><div class='meta'>{esc(r['matchup'])} · "
                            f"{esc((r.get('start_utc') or '')[:16] or r.get('start_date') or 'start not published')} · "
                            f"<a href='{esc(r['official_url'])}' target='_blank' rel='noopener'>official source</a></div>"
                            f"{esc(t)}</div>")
        open(os.path.join(SITE, "sports", f"{slug}.html"),
             "w").write(layout(f"{sp}", f"sports/{slug}.html", "\n".join(body), depth=1))

    # ---------- predictions ----------
    pb_ = ["<h2>Written predictions — top five per covered sport</h2>",
           "<p>Each text names the teams or players, quotes current form from the linked official source, and states "
           "one obvious selection. Injuries are deliberately omitted: no injury report was captured in this session's "
           "sources (see <a href='flagged.html'>Flagged</a>), so none is claimed.</p>"]
    tier_rank = {"High": 0, "Medium": 1, "Low": 2}
    bank_rows = sorted(bank.items(), key=lambda kv: (tier_rank.get(by_id_conf(kv[0], rows), 9), -(by_id_prob(kv[0], rows))))
    for rid, t in bank_rows:
        r = next(x for x in rows if x["id"] == rid)
        pb_.append(f"<div class='pred'><div class='meta'><strong>{esc(r['sport'])}</strong> · {esc(r['matchup'])} · "
                   f"{esc((r.get('start_utc') or '')[:16] or r.get('start_date') or 'start not published')} · pick {esc(r['pick'])} at {r['pick_fair_american']:+d} fair · "
                   f"{pick_pill(r)} · <a href='{esc(r['official_url'])}' target='_blank' rel='noopener'>official source</a> · "
                   f"<a href='sports/{esc(r['sport_slug'])}.html#{esc(rid)}'>row</a></div>{esc(t)}</div>")
    open(os.path.join(SITE, "predictions.html"), "w").write(layout("Predictions", "predictions.html", "\n".join(pb_)))

    # ---------- review ----------
    rv = ["<h2>Line-by-line review trail</h2>",
          f"<p>Rows checked: <strong>{review['checked_rows']}</strong> · predictions checked: "
          f"<strong>{review['checked_predictions']}</strong> · hard failures: <strong>{len(review['hard_failures'])}</strong> · "
          f"warnings: <strong>{len(review['warnings'])}</strong>. Every priced market re-verified: probability pair sums to 1, "
          "decimal odds equal 1/p, american prices recomputed, window arithmetic re-checked.</p>"]
    if review["warnings"]:
        rv.append("<ul>" + "".join(f"<li>{esc(w)}</li>" for w in review["warnings"]) + "</ul>")
    rr = review.get("repo_review") or {}
    if rr:
        msum = (rr.get("datasets") or {}).get("data/master.json", {})
        rv.append("<h2>Shared-dataset review (read-only)</h2>")
        rv.append(f"<p>data/master.json: <strong>{msum.get('summary', {}).get('with_defects', 0)}/"
                  f"{msum.get('rows', 0)}</strong> rows carry at least one logged defect (missing source URL, "
                  "stale date against the dataset's own generation date, or a High/prediction published on an "
                  "unverified build); data/predictions.json: <strong>"
                  f"{(rr.get('datasets') or {}).get('data/predictions.json', {}).get('issues', 0)}</strong> "
                  "structural issues. Nothing was edited — every defect is listed below with its manual-review "
                  "URL and mirrored as EZ4-REV-* flags on the <a href='flagged.html'>Flagged</a> page.</p>")
        rv.append("<table><thead><tr><th>Dataset</th><th>Row</th><th>Build</th><th>Sport</th><th>Matchup</th>"
                  "<th>Defect</th><th>Manual review</th></tr></thead><tbody>")
        for d in rr.get("defects", [])[:80]:
            man = (f"<a class='src' href='{esc(d.get('manual_url'))}' target='_blank' rel='noopener'>open</a>"
                   if d.get("manual_url") else "<span class='blank'>—</span>")
            rv.append(f"<tr><td>{esc(d.get('dataset'))}</td><td class='num'>{esc(str(d.get('row')))}</td>"
                      f"<td>{esc(str(d.get('build') or '—'))}</td><td>{esc(d.get('sport') or '')}</td>"
                      f"<td>{esc((d.get('matchup') or '')[:44])}</td><td>{esc(d.get('issue')[:150])}</td>"
                      f"<td>{man}</td></tr>")
        extra = len(rr.get("defects", [])) - 80
        if extra > 0:
            rv.append(f"<tr><td colspan='7' class='blank'>+{extra} more defects in "
                      "data/session-343754f2/review.json (repo_review.defects)</td></tr>")
        rv.append("</tbody></table>")
    n_ok = sum(1 for x in review["rows"].values() if x["status"] == "ok")
    rv.append(f"<p><strong>{n_ok}/{len(review['rows'])}</strong> rows passed every automated check "
              "(identity, source link, market arithmetic, window rule). Failures never ship — the build fails instead.</p>")
    rv.append("<table><thead><tr><th>Row</th><th>Matchup</th><th>Status</th><th>Checks</th></tr></thead><tbody>")
    for r in rows:
        st = review["rows"][r["id"]]["status"]
        checks = review["rows"][r["id"]]["checks"]
        ok = sum(1 for c in checks if c["ok"])
        det = "; ".join(f"{esc(c['name'])}" for c in checks[:6])
        rv.append(f"<tr><td>{esc(r['id'])}</td><td>{esc(r['matchup'])[:60]}</td>"
                  f"<td>{'✅' if st == 'ok' else '⚠️'} {esc(st)}</td><td>{ok}/{len(checks)}: {det}</td></tr>")
    rv.append("</tbody></table>")
    open(os.path.join(SITE, "review.html"), "w").write(layout("Review", "review.html", "\n".join(rv)))

    # ---------- flagged ----------
    fl = ["<h2>Flagged for review</h2>",
          "<p>Non-blocking. A flag means an input was missing, ambiguous, or unverifiable — the affected values stay "
          "<strong>blank</strong> on the row (never inferred) and every blank links here.</p>",
          "<table><thead><tr><th>Flag</th><th>Sport</th><th>What is missing</th><th>Evidence / manual check</th></tr></thead><tbody>"]
    for f in flagged["flags"]:
        ev = f"<a class='src' href='{esc(f['evidence_url'])}' target='_blank' rel='noopener'>evidence</a>" if f.get("evidence_url") else "<span class='blank'>—</span>"
        man = f" · <a class='src' href='{esc(f['manual_url'])}' target='_blank' rel='noopener'>manual check</a>" if f.get("manual_url") else ""
        fl.append(f"<tr id='{esc(f['id'])}'><td><strong>{esc(f['id'])}</strong> "
                  f"<span class='pill {'Low' if f['severity'] == 'review' else 'Medium'}'>{esc(f['severity'])}</span></td>"
                  f"<td>{esc(f['sport'])}</td><td><strong>{esc(f['title'])}</strong><br>{esc(f['detail'])}</td>"
                  f"<td>{ev}{man}</td></tr>")
    fl.append("</tbody></table>")
    open(os.path.join(SITE, "flagged.html"), "w").write(layout("Flagged for Review", "flagged.html", "\n".join(fl)))

    # ---------- methodology ----------
    mt = ["<h2>Methodology — how every originated line is computed</h2>",
          "<h3>Window rule</h3><p>A selection is labelled high-confidence only when (a) its originated win probability "
          "is at least 70% and (b) its fair american price falls between −250 and +10,000. Fair price −250 is decimal "
          "1.40, i.e. probability 1/1.40 = 71.43%, so rules (a) and (b) together pin every High pick between 70.0% "
          "and 71.4% (−250 to −233); the desk scans handicap and total markets for the best in-window selection "
          "on every row.</p>",
          "<h3>Per sport</h3><ul>",
          "<li><strong>Ice Hockey (NHL/SHL/Liiga)</strong> — Poisson goal model on official schedule + standings inputs; "
          "attack/defence rates shrunk toward the league mean by minutes-weighted reliability; home allowance +4.5% "
          "(NHL), +4.5% away-side allowance (SHL). Puck line −1.5 = win by 2+; total line 6.0 two-way.</li>",
          "<li><strong>Basketball (EuroLeague/EuroCup)</strong> — per-game for/against from the official game feed, "
          "normal margin model (σ=10.5 documented); handicap −4.5 two-way with P(margin &gt; 4.5); totals at the "
          "computed mean.</li>",
          "<li><strong>Baseball (World Series)</strong> — Poisson runs model on official season scoring/allowance rates, "
          "run line −1.5 = win by 2+.</li>",
          "<li><strong>Tennis</strong> — draw seeds and completed-set/game form from the official WTA tournament "
          "feeds drive a logistic match line (seed gap weight 0.30, event set/game form); the total-games line "
          "anchors a 62% three-set rate at even money and falls linearly with the mismatch. Ties between "
          "unseeded players with no completed match at the event carry no official strength input and are "
          "published unpriced (flagged). ATP order-of-play PDFs were captured but the PDF reader is absent in "
          "this environment, so no ATP row is published.</li>",
          "<li><strong>Handball (Denmark)</strong> — season goals for/against from the official table, shrunk; expected "
          "margin in goals with home allowance +3.5%; handicap −3.5 and totals two-way.</li>",
          "<li><strong>Volleyball (SuperLega)</strong> — match winner only: points-per-game and set-quotient "
          "difference from the official legavolley.it classifica through a normal-CDF link (+0.15 home, clamped "
          "[0.15, 0.85]); set handicaps and set totals are not modelled and stay blank (flagged). Other "
          "national leagues are listing-only.</li>",
          "<li><strong>Snooker (Northern Ireland Open)</strong> — win match only: world ranks carried in the "
          "snooker.org event draw through a normal-CDF rank-gap link, clamped [0.15, 0.85], with event frame form "
          "from the same page feeding the written pick; frame handicaps/totals are not originated (flagged).</li>",
          "<li><strong>Rugby Union (TOP 14)</strong> — the official LNR league table gives matches played, "
          "points for and against per club; attack/defence rates are divided by the league mean of points scored "
          "per match (27.50 at this capture) and combined into independent Poisson scoring expectations with a "
          "1.08 home factor. The two-way win price removes the draw mass, the handicap ladder is priced from the "
          "same joint distribution, and the match total line is the nearest half point to the modelled total. "
          "URC and Premiership fixtures are listed unpriced because their official tables did not render.</li>",
          "<li><strong>Cricket, Darts, Golf, Motor Racing, Gaelic, Greyhounds, Rugby League</strong> — fixtures "
          "published as a complete list; rows stay unpriced where an official numeric input (standings, ratings, "
          "rankings, racecards) was not capturable — every such row links its flag.</li>",
          "</ul><h3>Republication rule</h3><p>Bookmaker prices are never shown. Every published price is this desk's "
          "own fair computation (decimal = 1/p, american converted at 100·(d−1) or −100/(d−1)), and the review gate "
          "re-derives all of it before the site builds.</p>"]
    open(os.path.join(SITE, "methodology.html"), "w").write(layout("Methodology", "methodology.html", "\n".join(mt)))

    # ---------- sources ----------
    seen, srcs = set(), []
    for r in rows:
        key = r["official_url"]
        if key not in seen:
            seen.add(key)
            srcs.append((r["official_source_name"], key, r["capture_stamp"]))
    so = ["<h2>Official sources used</h2>",
          "<p>Every row links one of these. Captures are sha-256 recorded in "
          "<code>data/session-343754f2/capture/&lt;stamp&gt;/manifest.json</code>.</p>",
          "<table><thead><tr><th>Source</th><th>URL</th><th>First capture</th></tr></thead><tbody>"]
    for name, url, stamp in sorted(srcs):
        so.append(f"<tr><td>{esc(name)}</td><td><a class='src' href='{esc(url)}' target='_blank' rel='noopener'>{esc(url)}</a></td>"
                  f"<td>{esc(stamp)}</td></tr>")
    so.append("</tbody></table>")
    open(os.path.join(SITE, "sources.html"), "w").write(layout("Sources", "sources.html", "\n".join(so)))

    print(f"[board-bw] site built under session-343754f2/ ({len(rows)} rows, "
          f"{len(flagged['flags'])} flags, {len(bank)} predictions)")


def by_id_conf(rid, rows):
    r = next(x for x in rows if x["id"] == rid)
    return r.get("confidence") or "Low"


def by_id_prob(rid, rows):
    r = next(x for x in rows if x["id"] == rid)
    return r.get("pick_prob") or 0


if __name__ == "__main__":
    main()
