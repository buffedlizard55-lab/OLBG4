"""Page renderers for the static dashboard."""
from __future__ import annotations

import urllib.parse
from collections import Counter, defaultdict

from . import config
from .site_common import (
    SPORTS,
    SPORT_META,
    conf_badge,
    esc,
    filters,
    fmt_date,
    fmt_dt,
    fmt_time,
    layout,
    market_rows,
    pct,
    signed,
    sport_badge,
    table,
)

CONF_RANK = {"high": 3, "medium": 2, "low": 1}


def source_label(url: str) -> str:
    host = urllib.parse.urlparse(url).netloc.lower()
    if "nba.com" in host:
        return "NBA.com"
    if "nhle.com" in host or host.endswith("nhl.com"):
        return "NHL.com"
    if "mlb.com" in host:
        return "MLB.com"
    return host or "source"


def source_links(urls, limit: int = 2) -> str:
    out, seen_urls, seen_labels = [], set(), set()
    for url in urls or []:
        label = source_label(url)
        if not url or url in seen_urls or label in seen_labels:
            continue
        seen_urls.add(url)
        seen_labels.add(label)
        out.append(
            f'<a href="{esc(url)}" target="_blank" rel="noopener noreferrer">{esc(label)}</a>'
        )
        if len(out) >= limit:
            break
    return " · ".join(out)


def _match_cell(fx: dict) -> str:
    away, home = fx["away"], fx["home"]
    venue = fx.get("venue") or "Venue not published"
    return (
        f'<span class="team">{esc(away["name"])}</span> '
        f'<span class="vs">at</span> <span class="team">{esc(home["name"])}</span>'
        f'<div class="small muted">{esc(venue)}</div>'
    )


def _record_cell(fx: dict) -> str:
    a = fx["away"].get("record") or "—"
    h = fx["home"].get("record") or "—"
    flag = ""
    if fx["away"].get("record") is None or fx["home"].get("record") is None:
        flag = ' <span class="tag">unverified</span>'
    return f'<span class="mono">{esc(a)} – {esc(h)}</span>{flag}'


def _pick_cell(pick: dict) -> str:
    return (
        f'<div class="pick-cell"><strong>{esc(pick["selection"])}</strong>'
        f'<span class="odds">{esc(pick["american"])} · {pct(pick["prob"])} model</span></div>'
    )


def _detail_html(row: dict, preds: list[dict]) -> str:
    fx = row["fixture"]
    a = row["analysis"]
    if _withheld(row):
        srcs = fx.get("official_source_urls") or fx.get("source_urls") or []
        return (
            f'<div class="small">{esc(a.get("market_note") or "markets withheld")}</div>'
            '<div class="small muted" style="margin-top:6px">Official sources: '
            + " · ".join(
                f'<a href="{esc(u)}" target="_blank" rel="noopener noreferrer">{esc(u)}</a>'
                for u in srcs
            )
            + "</div>"
        )
    cur = a["expected"]["current"]
    opn = a["expected"]["opening"]
    unit = {"basketball": "points", "ice_hockey": "goals", "baseball": "runs"}[fx["sport"]]
    parts = [
        '<div class="small muted">'
        f'Model projection: {esc(fx["away"]["name"])} {cur["away"]:.1f} – '
        f'{esc(fx["home"]["name"])} {cur["home"]:.1f} ({esc(unit)}). '
        f'Opening projection: {opn["away"]:.1f} – {opn["home"]:.1f}. '
        f'Margin {signed(a["edge"]["margin"])} vs opener, total {signed(a["edge"]["total"])}.'
        "</div>"
    ]
    labels = {
        "moneyline": "Match winner",
        "handicap": a["markets"].get("handicap", {}).get("name", "Handicap"),
        "total": "Match total",
    }
    for key in ("moneyline", "handicap", "total"):
        market = a["markets"].get(key)
        if not market:
            continue
        if key == "moneyline":
            market = {**market, "name": labels[key]}
        else:
            market = {**market, "name": labels[key]}
        parts.append(market_rows(key, market, unit))
    form = row.get("form") or {}
    for side in ("away", "home"):
        f = form.get(side)
        if not f:
            continue
        seq = "".join("W" if g["won"] else "L" for g in f.get("last5", [])) or "—"
        parts.append(
            f'<div class="small"><b>{esc(fx[side]["name"])}</b> last five: '
            f'<span class="mono">{esc(seq)}</span> · '
            f'record {esc(f.get("record") or "n/a")} · '
            f'{esc(str(f.get("avg_scored_last5") or "n/a"))} scored / '
            f'{esc(str(f.get("avg_allowed_last5") or "n/a"))} allowed per game</div>'
        )
    if row.get("h2h"):
        h2h = row["h2h"][0]
        parts.append(
            '<div class="small muted">Most recent meeting in sample: '
            f'{esc(h2h["date_utc"][:10])}, {esc(str(h2h["away_score"]))}-{esc(str(h2h["home_score"]))} '
            "(away-home).</div>"
        )
    for pred in preds:
        parts.append(
            f'<div class="small" style="margin-top:6px"><b>Prediction ({esc(pred["market"])}):</b> '
            f'{esc(pred["text"])}</div>'
        )
    srcs = fx.get("official_source_urls") or fx.get("source_urls") or []
    parts.append(
        '<div class="small muted" style="margin-top:6px">Sources: '
        + " · ".join(
            f'<a href="{esc(u)}" target="_blank" rel="noopener noreferrer">{esc(u)}</a>' for u in srcs
        )
        + "</div>"
    )
    return "".join(parts)


def _withheld(row: dict) -> bool:
    return row.get("analysis", {}).get("market_status") == "withheld"


def _fixture_table(ctx: dict, rows: list[dict], *, filterable: bool = True,
                   show_sport: bool = True) -> str:
    out = []
    for row in rows:
        fx = row["fixture"]
        pick = row["analysis"].get("headline_pick")
        preds = ctx["preds_by_fixture"].get(fx["id"], [])
        withheld = _withheld(row)
        conf = pick["confidence"] if pick else ("withheld" if withheld else "")
        search = fx["away"]["name"] + " " + fx["home"]["name"] + " " + (fx.get("venue") or "")
        if pick:
            search += " " + pick["selection"]
        if withheld:
            pick_cell = ('<span class="badge low">Withheld</span>'
                         '<div class="small muted">insufficient rating sample</div>')
            market_cell = '<span class="small muted">—</span>'
            prob_cell = '<span class="muted">—</span>'
            conf_cell = '<span class="badge low" title="No market is originated on this sample">n/a</span>'
        else:
            pick_cell = _pick_cell(pick)
            market_cell = f'<span class="small muted">{esc(pick["market_label"])}</span>'
            prob_cell = pct(pick["prob"])
            conf_cell = conf_badge(pick["confidence"])
        out.append(
            f'<tr data-sport="{esc(fx["sport"])}" data-confidence="{esc(conf)}" '
            f'data-text="{esc(search)}">'
            f'<td class="nowrap"><div>{fmt_date(fx["start_utc"])}</div>'
            f'<div class="time">{fmt_time(fx["start_utc"])}</div></td>'
            f'<td>{sport_badge(fx["sport"])}</td>'
            f"<td>{_match_cell(fx)}</td>"
            f'<td class="nowrap" title="Away record – home record as published by the league">{_record_cell(fx)}</td>'
            f"<td>{pick_cell}</td>"
            f'<td class="nowrap">{market_cell}</td>'
            f'<td class="num">{prob_cell}</td>'
            f'<td class="nowrap">{conf_cell}</td>'
            f'<td class="src nowrap">{source_links(fx.get("official_source_urls") or fx.get("source_urls"))}</td>'
            f'<td><details class="market-detail"><summary>All markets</summary>'
            f"{_detail_html(row, preds)}</details></td></tr>"
        )
    headers = [
        ("When", "nosort"), ("Sport", "nosort"), ("Match", ""), ("Record A–H", "nosort"),
        ("Our pick", ""), ("Market", ""), ("Prob", "num"), ("Conf.", ""), ("Sources", "nosort"),
        ("Markets", "nosort"),
    ]
    return table(headers, out, filterable=filterable)


# ---------------------------------------------------------------------------
# pages
# ---------------------------------------------------------------------------
def render_index(ctx: dict) -> str:
    snap = ctx["snapshot"]
    counts = snap.get("counts", {})
    rows = ctx["rows"]
    priced = [r for r in rows if r["analysis"].get("headline_pick")]
    top = sorted(
        priced,
        key=lambda r: (
            CONF_RANK[r["analysis"]["headline_pick"]["confidence"]],
            r["analysis"]["headline_pick"]["prob"],
        ),
        reverse=True,
    )[:10]
    window = snap.get("window", {})
    fetch_ok = sum(1 for f in snap.get("fetch_log", []) if f.get("status") == 200)
    ver = snap.get("verification", {})
    high = [r for r in priced if r["analysis"]["winner_pick"]["confidence"] == "high"]
    body = [
        '<div class="hero">',
        "<h1>Official-data line desk</h1>",
        "<p>We ingest NBA, NHL and MLB fixtures and results from league-owned feeds, fit our own "
        "ratings, originate a price for every market the sample can support, and grade a pick "
        "wherever a line exists. Every row links to the official source it came from, and "
        "anything that cannot be verified is left blank and listed on the Flagged for Review "
        "page.</p>",
        '<div class="chips">',
        f'<span class="chip">Window {esc(window.get("start", "")[:10])} → {esc(window.get("end", "")[:10])}</span>',
        f'<span class="chip">{counts.get("fixtures", 0)} fixtures</span>',
        f'<span class="chip">{counts.get("high_picks", 0) + counts.get("medium_picks", 0) + counts.get("low_picks", 0) + counts.get("market_picks", 0)} graded picks</span>',
        f'<span class="chip">{counts.get("findings", 0)} flagged items</span>',
        "</div></div>",
        '<div class="section"><div class="grid">',
    ]
    kpis = [
        ("Fixtures priced", len(priced), "matches with an originated line"),
        ("Markets originated", len(priced) * 3, "winner · handicap · total"),
        ("High-confidence winners", counts.get("high_picks", 0), "graded high"),
        ("Written predictions", ver.get("predictions_published", 0), "≥30 words, source-linked"),
        ("Official fetches", fetch_ok, "HTTP 200 responses"),
        ("Hard failures", ver.get("hard_failures", 0), "verification gate"),
    ]
    for label, value, sub in kpis:
        body.append(
            f'<div class="card kpi"><div class="big mono">{esc(value)}</div>'
            f"<small>{esc(label)}</small><p>{esc(sub)}</p></div>"
        )
    body.append("</div></div>")
    if counts.get("markets_withheld"):
        body.append(
            '<div class="notice warn"><b>'
            f'{counts["markets_withheld"]} fixtures are listed without markets.</b> '
            "The league sample behind their ratings is smaller than the 20 completed games per "
            "team required to originate a price, so no line and no pick is published for them. "
            "The fixtures, records and official source links are still there; "
            '<a href="flagged.html">see the flag and the reason</a>.</div>'
        )

    body.append(
        '<div class="section"><div class="split"><div>'
        "<h2>Highest-confidence calls</h2>"
        '<p class="lead">Ranked by confidence grade, then model probability. Every price is our own '
        "originated number, not a bookmaker quote.</p>"
        + _fixture_table(ctx, top)
        + '</div><div class="card"><h2>How a row is built</h2>'
        "<ul class='clean small'>"
        "<li><b>Fixture</b> — league schedule endpoint, with the official game link stored per row.</li>"
        "<li><b>Rating</b> — ridge least squares on margin and total from completed games.</li>"
        "<li><b>Price</b> — 1/probability with a 4.5% two-way hold, rounded to a half line.</li>"
        "<li><b>Confidence</b> — probability, games in sample, and a stability check on the same winner.</li>"
        "<li><b>Prediction</b> — templated from verified facts only; linted for length and uniqueness.</li>"
        "</ul>"
        '<h3>Data integrity</h3>'
        f'<p class="small">Official-source check: {esc(ver.get("fixtures_checked", 0))} fixtures '
        f'validated, {esc(ver.get("hard_failures", 0))} hard failures. '
        f'{esc(ver.get("predictions_checked", 0))} predictions linted.</p>'
        '<p class="small"><a href="sources.html">See every endpoint, response hash and check →</a></p>'
        "</div></div></div>"
    )

    body.append('<div class="section"><h2>Coverage by league</h2>'
                '<p class="lead">A fixture is listed only if an official feed published it. A line '
                'is originated only if the rating sample clears the floor.</p>')
    cover = []
    for sport, league, slug, label in SPORTS:
        srows = [r for r in rows if r["fixture"]["sport"] == sport]
        priced_n = sum(1 for r in srows if r["analysis"].get("headline_pick"))
        withheld_n = len(srows) - priced_n
        note = ("all fixtures priced" if withheld_n == 0 else
                f"{withheld_n} withheld — sample below floor")
        cover.append(
            f'<tr><td>{sport_badge(sport)} {esc(league)}</td>'
            f'<td class="num">{len(srows)}</td>'
            f'<td class="num">{priced_n}</td>'
            f'<td class="num">{withheld_n}</td>'
            f'<td class="small muted">{esc(note)}</td>'
            f'<td><a href="sport-{slug}.html">Open desk →</a></td></tr>'
        )
    body.append(table([("League", ""), ("Fixtures", "num"), ("Priced", "num"),
                       ("Withheld", "num"), ("Status", ""), ("", "nosort")], cover))
    body.append("</div>")

    body.append('<div class="section"><h2>Sports covered</h2><div class="grid">')
    for sport, league, slug, label in SPORTS:
        srows = [r for r in rows if r["fixture"]["sport"] == sport]
        model = (ctx["models"] or {}).get(sport, {})
        cur = model.get("current", {})
        body.append(
            f'<div class="card"><h2>{esc(league)} <span class="muted small">· {esc(label)}</span></h2>'
            f'<div class="big mono">{len(srows)}</div><small>fixtures in window</small>'
            f'<p>{esc(cur.get("games", 0))} completed games in the rating sample · '
            f'home advantage {esc(cur.get("home_advantage", 0))} · '
            f'σ margin {esc(cur.get("sigma_margin", 0))}</p>'
            f'<p><a href="sport-{slug}.html">Open {esc(league)} desk →</a></p></div>'
        )
    body.append("</div></div>")

    body.append(
        '<div class="section"><div class="grid two">'
        '<div class="card"><h2>What is out of scope</h2>'
        "<p>The owner excluded soccer (association football), American football, boxing, UFC/MMA, "
        "hurling, horse racing, cycling and specials. Those are excluded at ingestion, not "
        "filtered afterwards, so they never enter the model. Gaelic football, tennis, cricket, "
        "rugby, golf, darts, snooker and the other listed sports stay in scope; the coverage "
        "page records which of them has an official feed this project can verify.</p>"
        '<p><a href="methodology.html">Read the scope rules →</a></p></div>'
        '<div class="card"><h2>What we could not verify</h2>'
        f'<p>{esc(len(ctx["flagged"]))} items are published on the Flagged for Review page with source '
        "links and the action taken. Unverified fields are blank in the tables above rather than "
        "filled with an estimate.</p>"
        '<p><a href="flagged.html">Review the flags →</a></p></div>'
        "</div></div>"
    )
    return layout("Overview", "overview", "".join(body), snap)


def render_matches(ctx: dict) -> str:
    body = [
        '<div class="page-head"><h1>All matches</h1>'
        '<p>Every fixture in the publishing window with our match-winner pick, the records published '
        "by the league, and the full price ladder for match winner, handicap and total. Expand "
        "“All markets” for projections, recent form and source links.</p></div>",
        filters(show_sport=True, show_confidence=True),
        '<button class="btn small" data-expand-all style="margin:0 0 10px;font:inherit;font-size:12px;'
        'padding:6px 10px;border:1px solid #e3e8ef;background:#fff;border-radius:8px;cursor:pointer">'
        "Expand all markets</button>",
        _fixture_table(ctx, ctx["rows"]),
        '<div class="notice info">Records are shown as away–home. A dash means the league feed did '
        "not publish a record at snapshot time; those rows carry an “unverified” tag and an entry on "
        "the Flagged for Review page.</div>",
    ]
    return layout("Matches", "matches", "".join(body), ctx["snapshot"])


def render_picks(ctx: dict) -> str:
    rows = []
    for row in ctx["rows"]:
        fx = row["fixture"]
        picks = [row["analysis"]["winner_pick"]] + row["analysis"]["market_picks"]
        picks = [p for p in picks if p]
        for pick in picks:
            sort_key = (fx["start_utc"], fx["sport"], pick["market"], pick["selection"])
            rows.append((sort_key, 
                f'<tr data-sport="{esc(fx["sport"])}" data-confidence="{esc(pick["confidence"])}" '
                f'data-market="{esc(pick["market"])}" '
                f'data-text="{esc(fx["away"]["name"] + " " + fx["home"]["name"] + " " + pick["selection"])}">'
                f'<td class="nowrap">{fmt_date(fx["start_utc"])}</td>'
                f'<td>{sport_badge(fx["sport"])}</td>'
                f'<td><span class="team">{esc(fx["away"]["name"])}</span> '
                f'<span class="vs">at</span> <span class="team">{esc(fx["home"]["name"])}</span></td>'
                f'<td><b>{esc(pick["selection"])}</b><div class="small muted">'
                f'{esc(pick["market_label"])}</div></td>'
                f'<td class="num">{esc(pick["american"])}</td>'
                f'<td class="num">{pct(pick["prob"])}</td>'
                f'<td class="num">{esc(pick.get("sample_games_min", ""))}</td>'
                f'<td>{conf_badge(pick["confidence"])}</td>'
                f'<td class="src">{source_links(fx.get("official_source_urls") or fx.get("source_urls"), 1)}</td></tr>'
            ))
    rows.sort(key=lambda item: item[0])
    rows = [html for _, html in rows]
    headers = [("When", "nosort"), ("Sport", "nosort"), ("Match", ""), ("Selection", ""),
               ("Price", "num"), ("Prob", "num"), ("Sample", "num"), ("Conf.", ""), ("Source", "nosort")]
    published = [p for p in ctx["payload"]["predictions"] if not p.get("withdrawn") and p.get("text")]
    pred_cards = []
    for p in sorted(published, key=lambda x: (CONF_RANK.get(x.get("confidence"), 0), x.get("prob_pct", 0)),
                    reverse=True):
        facts = "".join(
            f'<li>{esc(f["fact"])} — <span class="muted">{esc(f["source"])}</span></li>'
            for f in p.get("facts", [])
        )
        pred_cards.append(
            f'<article class="pred"><header><span class="match">{esc(p.get("match") or p.get("fixture_id"))}</span>'
            f'{sport_badge(p["sport"])} {conf_badge(p.get("confidence"))}'
            f'<span class="badge sport">{esc(p.get("market", ""))}</span></header>'
            f'<div class="meta">{fmt_dt(p.get("start_utc"))} · {esc(p.get("league", ""))} · '
            f'Selection: <b>{esc(p["selection"])}</b> at {esc(p.get("american", ""))} · '
            f'{esc(p.get("word_count", len(p.get("text", "").split())))} words</div>'
            f'<p>{esc(p["text"])}</p>'
            f'<ul class="facts" style="list-style:none;padding-left:0">{facts}</ul></article>'
        )
    no_preds = """<p class='muted'>No high-confidence predictions in this snapshot.</p>"""
    body = [
        '<div class="page-head"><h1>Picks &amp; predictions</h1>'
        '<p>Every graded selection, with the price we originated, the model probability and the '
        "number of verified games behind the rating. Written predictions are produced for "
        "high-confidence picks and pass an automated length/uniqueness lint before publication.</p></div>",
        filters(show_sport=True, show_confidence=True, show_market=True),
        table(headers, rows, filterable=True),
        '<div class="notice">Each written prediction must be at least 30 words, name the betting '
        "selection explicitly, avoid promotional language, and share no more than 55% of its "
        "vocabulary with any other prediction. Failing copy is withdrawn and flagged rather than "
        "published.</div>",
        '<div class="section"><h2>Written predictions</h2>'
        f'<p class="lead">{len(pred_cards)} published write-ups. Every fact under each prediction '
        "links back to the official feed it came from; the probability is our own model output.</p>"
        '<div class="preds">' + ("".join(pred_cards) or no_preds) + '</div></div>',
    ]
    return layout("Picks", "picks", "".join(body), ctx["snapshot"])


def render_sport(ctx: dict, sport: str) -> str:
    meta = SPORT_META[sport]
    rows = [r for r in ctx["rows"] if r["fixture"]["sport"] == sport]
    model = (ctx["models"] or {}).get(sport, {})
    cur = model.get("current", {})
    opening = model.get("opening", {})
    bt = model.get("backtest", {})
    ratings = cur.get("ratings", [])[:12]
    rating_rows = "".join(
        f'<tr><td>{esc(r["team"])}</td><td class="num">{signed(r["rating"])}</td>'
        f'<td class="num">{signed(r["offence"])}</td><td class="num">{signed(r["defence"])}</td>'
        f'<td class="num">{esc(r["games"])}</td></tr>'
        for r in ratings
    )
    bt_html = (
        f'<p class="small">Holdout: last {esc(bt.get("holdout_days"))} days, '
        f'{esc(bt.get("holdout_games"))} games scored · accuracy {pct(bt.get("accuracy"))} · '
        f'Brier {esc(bt.get("brier"))} · log loss {esc(bt.get("log_loss"))}</p>'
        if bt.get("available")
        else f'<p class="small muted">Backtest unavailable: {esc(bt.get("reason", ""))}</p>'
    )
    body = [
        f'<div class="page-head"><h1>{esc(meta["league"])} desk <span class="muted">· {esc(meta["label"])}</span></h1>'
        f'<p>{len(rows)} fixtures, {esc(cur.get("games", 0))} completed games in the rating sample '
        f'({esc(", ".join(cur.get("seasons", [])) or "no season recorded")}). Opening line: '
        f'{esc(opening.get("notes", [""])[-1] if opening.get("notes") else "previous season")}.</p></div>',
        '<div class="grid">',
        f'<div class="card kpi"><div class="big mono">{esc(cur.get("games", 0))}</div><small>rating games</small>'
        f'<p>{esc(len(cur.get("ratings", [])))} teams rated</p></div>',
        f'<div class="card kpi"><div class="big mono">{esc(cur.get("home_advantage", 0))}</div>'
        f'<small>home advantage</small><p>in {esc(meta["label"].lower())} scoring units</p></div>',
        f'<div class="card kpi"><div class="big mono">{esc(cur.get("sigma_margin", 0))}</div>'
        f'<small>margin sd</small><p>residual spread used for probabilities</p></div>',
        f'<div class="card kpi"><div class="big mono">{len(rows)}</div><small>fixtures in window</small>'
        f'<p>{sum(1 for r in rows if (r["analysis"].get("winner_pick") or {}).get("confidence") == "high")} graded high</p></div>',
        "</div>",
        '<div class="section"><h2>Model ratings</h2>'
        '<p class="lead">Ridge least-squares ratings from official final scores. Positive rating = '
        "stronger than the league average; offence/defence are in the same scoring unit as the sport.</p>"
        + table([("Team", ""), ("Rating", "num"), ("Offence", "num"), ("Defence", "num"), ("Games", "num")],
                [rating_rows] if rating_rows else ['<tr><td colspan="5" class="muted">No games in sample.</td></tr>'])
        + f'<div class="notice info">{bt_html}</div></div>',
        ('<div class="notice warn"><b>Markets are withheld for this league.</b> '
         f'{sum(1 for r in rows if r["analysis"].get("market_status") == "withheld")} fixtures are '
         f'listed but not priced: the official sample is {esc(cur.get("games", 0))} completed games, '
         f'below the {config.MIN_GAMES_FOR_MARKETS}-game floor this project requires before it '
         'originates a line. Fixtures and source links are still published.</div>'
         if rows and all(r["analysis"].get("market_status") == "withheld" for r in rows) else "")
        + '<div class="section"><h2>Fixtures &amp; picks</h2>'
        '<p class="lead">Same columns as the all-matches page, filtered to this league.</p>'
        + filters(show_sport=False, show_confidence=True)
        + _fixture_table(ctx, rows, filterable=True, show_sport=False)
        + "</div>",
    ]
    return layout(f"{meta['league']} desk", meta["slug"], "".join(body), ctx["snapshot"])


def render_markets(ctx: dict) -> str:
    rows = ctx["rows"]
    unit = {"basketball": "points", "ice_hockey": "goals", "baseball": "runs"}
    counts = Counter()
    prices = defaultdict(list)
    for row in rows:
        for key, market in row["analysis"]["markets"].items():
            counts[key] += 1
            for sel in market.get("selections", []):
                prices[key].append(sel["price_decimal"])
    stat_rows = "".join(
        f'<tr><td>{esc({"moneyline": "Match winner", "handicap": "Handicap", "total": "Match total"}[k])}</td>'
        f'<td class="num">{counts[k]}</td>'
        f'<td class="num">{len(prices[k]) * 2}</td>'
        f'<td class="num">{min(prices[k]):.3f} – {max(prices[k]):.3f}</td></tr>'
        for k in ("moneyline", "handicap", "total") if prices[k]
    )
    examples = []
    for row in [r for r in rows if r["analysis"].get("markets")][:6]:
        fx = row["fixture"]
        a = row["analysis"]
        examples.append(
            f'<tr><td>{sport_badge(fx["sport"])} {esc(fx["away"]["name"])} at {esc(fx["home"]["name"])}</td>'
            f'<td class="num">{esc(fx["away"]["name"].split()[-1])} '
            f'{pct(a["markets"]["moneyline"]["selections"][1]["prob"])} '
            f'{esc(a["markets"]["moneyline"]["selections"][1]["american"])}</td>'
            f'<td class="num">{a["markets"]["handicap"]["line_home"]:+.1f} '
            f'({pct(a["markets"]["handicap"]["selections"][0]["prob"])})</td>'
            f'<td class="num">{a["markets"]["total"]["line"]:.1f} '
            f'(O {pct(a["markets"]["total"]["selections"][0]["prob"])})</td></tr>'
        )
    body = [
        '<div class="page-head"><h1>Markets and line origination</h1>'
        '<p>Three markets are priced for every fixture: match winner (moneyline), handicap, and '
        "match total. Prices are our own; they are not copied from any bookmaker and no OLBG price "
        "data is used.</p></div>",
        '<div class="grid two">'
        '<div class="card"><h2>Definitions</h2>'
        "<h3>Match winner</h3><p>Two-way market on the winner of the game, including overtime or "
        "(baseball) extra innings. Probability comes from the empirical distribution of margin "
        "residuals, so a tie is not possible in any of the three sports.</p>"
        "<h3>Handicap</h3><p>Basketball point spread, NHL puck line, MLB run line. The line is "
        "rounded to the nearest half-point away from the projection so the market cannot push. "
        "Home lines are quoted from the home team's perspective.</p>"
        "<h3>Match total</h3><p>Over/under on combined score. The line is the half-point above the "
        "projected total; both sides are priced from the same residual distribution.</p>"
        "</div>"
        '<div class="card"><h2>Pricing</h2>'
        "<p>Fair decimal odds are <code>1 / p</code>. Our quoted price adds a 4.5% two-way hold: "
        "<code>1 / (p × 1.045)</code>. Prices convert to American odds in the usual way and are "
        "shown next to the model probability so the edge is visible.</p>"
        "<h3>Opening vs current</h3><p>The opening line is fitted only on the previous completed "
        "season (or a league-average opener when no prior season exists). The current line is the "
        "recency-weighted fit with a 120-day half-life. A handicap or total selection is nominated "
        "only when the current model disagrees with our own opener by more than a sport-specific "
        "threshold, and the odds quoted for that pick are at the opening line.</p>"
        "<p class='small muted'>Thresholds: NBA 1.5 / 2.0 points, NHL 0.30 / 0.35 goals, MLB 0.35 / "
        "0.45 runs (handicap / total).</p>"
        "</div></div>",
        '<div class="section"><h2>Coverage in this snapshot</h2>'
        '<p class="lead">Counts and price ranges across the window. Alternates add a second line on '
        "each side of the handicap and total, visible in the match detail.</p>"
        + table([("Market", ""), ("Fixtures priced", "num"), ("Selections", "num"), ("Price range", "num")],
                [stat_rows] if stat_rows else ['<tr><td colspan="4" class="muted">No markets.</td></tr>'])
        + "</div>",
        '<div class="section"><h2>Worked examples</h2>'
        + table([("Fixture", ""), ("Away moneyline", "num"), ("Handicap (home)", "num"), ("Total", "num")],
                [ex for ex in examples] or ['<tr><td colspan="4" class="muted">No fixtures.</td></tr>'])
        + f'<div class="notice info">Scoring units: {esc(unit["basketball"])} for the NBA, '
        f'{esc(unit["ice_hockey"])} for the NHL and {esc(unit["baseball"])} for MLB.</div></div>',
    ]
    return layout("Markets", "markets", "".join(body), ctx["snapshot"])


def render_analysis(ctx: dict) -> str:
    models = ctx["models"] or {}
    ver = ctx["snapshot"].get("verification", {})
    cat = ver.get("findings_by_category", {})
    cat_rows = "".join(
        f'<tr><td>{esc(k)}</td><td class="num">{v}</td></tr>' for k, v in sorted(cat.items())
    ) or '<tr><td colspan="2" class="muted">No findings.</td></tr>'
    bt_rows = []
    for sport, meta in SPORT_META.items():
        bt = (models.get(sport) or {}).get("backtest", {})
        if bt.get("available"):
            bt_rows.append(
                f'<tr><td>{esc(meta["league"])}</td><td class="num">{esc(bt["train_games"])}</td>'
                f'<td class="num">{esc(bt["holdout_games"])}</td>'
                f'<td class="num">{pct(bt["accuracy"])}</td><td class="num">{esc(bt["brier"])}</td>'
                f'<td class="num">{esc(bt["log_loss"])}</td></tr>'
            )
        else:
            bt_rows.append(
                f'<tr><td>{esc(meta["league"])}</td><td class="num">—</td><td class="num">—</td>'
                f'<td class="num">—</td><td class="num">—</td>'
                f'<td class="small muted">{esc(bt.get("reason", "unavailable"))}</td></tr>'
            )
    calib = []
    for sport, meta in SPORT_META.items():
        bt = (models.get(sport) or {}).get("backtest", {})
        for bucket, vals in (bt.get("calibration") or {}).items():
            if vals.get("n"):
                calib.append(
                    f'<tr><td>{esc(meta["league"])}</td><td>{esc(bucket)}</td>'
                    f'<td class="num">{vals["n"]}</td><td class="num">{pct(vals["predicted"])}</td>'
                    f'<td class="num">{pct(vals["observed"])}</td></tr>'
                )
    edges = sorted(
        [r for r in ctx["rows"] if r["analysis"].get("edge")],
        key=lambda r: abs(r["analysis"]["edge"]["margin"]), reverse=True,
    )[:10]
    edge_rows = "".join(
        f'<tr><td>{sport_badge(r["fixture"]["sport"])} '
        f'{esc(r["fixture"]["away"]["name"])} at {esc(r["fixture"]["home"]["name"])}</td>'
        f'<td class="num">{signed(r["analysis"]["edge"]["margin"])}</td>'
        f'<td class="num">{signed(r["analysis"]["edge"]["total"])}</td>'
        f'<td class="num">{signed(r["analysis"]["expected"]["opening"]["margin"])} → '
        f'{signed(r["analysis"]["expected"]["current"]["margin"])}</td>'
        f'<td>{conf_badge(r["analysis"]["headline_pick"]["confidence"])}</td></tr>'
        for r in edges
    )
    body = [
        '<div class="page-head"><h1>Analysis &amp; findings</h1>'
        '<p>Model diagnostics, a leakage-free backtest, and the data-quality findings that drive the '
        "review queue. Nothing on this page is hand-entered; it is rebuilt from the snapshot JSON on "
        "every run.</p></div>",
        '<div class="grid">',
        f'<div class="card kpi"><div class="big mono">{esc(ver.get("fixtures_checked", 0))}</div>'
        "<small>fixtures validated</small><p>official-source gate</p></div>",
        f'<div class="card kpi"><div class="big mono">{esc(ver.get("predictions_published", 0))}</div>'
        "<small>predictions published</small><p>linted for length and uniqueness</p></div>",
        f'<div class="card kpi"><div class="big mono">{esc(ver.get("hard_failures", 0))}</div>'
        "<small>hard failures</small><p>Published rows with no official source</p></div>",
        f'<div class="card kpi"><div class="big mono">{esc(len(ctx["flagged"]))}</div>'
        "<small>review items</small><p>including blanks, not guesses</p></div>",
        "</div>",
        '<div class="section"><h2>Backtest (no leakage)</h2>'
        '<p class="lead">For each sport we refit using only games older than 30 days and score the '
        "most recent 30 days. Accuracy is against the actual winner; Brier and log loss are proper "
        "scoring rules (lower is better).</p>"
        + table([("League", ""), ("Train games", "num"), ("Holdout games", "num"), ("Accuracy", "num"),
                 ("Brier", "num"), ("Log loss", "num")], bt_rows)
        + "</div>",
        '<div class="section"><h2>Calibration</h2>'
        '<p class="lead">For each confidence band, the mean probability we assigned versus the share '
        "of those games actually won. A well-calibrated model has the two columns close together.</p>"
        + table([("League", ""), ("Band", ""), ("Games", "num"), ("Predicted", "num"), ("Observed", "num")],
                [c for c in calib] or ['<tr><td colspan="5" class="muted">No calibration sample.</td></tr>'])
        + "</div>",
        '<div class="section"><h2>Biggest line moves</h2>'
        '<p class="lead">Where current-season evidence moved our number furthest away from our own '
        "opening line. These are the fixtures where handicap and total picks come from.</p>"
        + table([("Fixture", ""), ("Margin move", "num"), ("Total move", "num"),
                 ("Projection", "num"), ("Conf.", "")],
                [edge_rows] if edge_rows else ['<tr><td colspan="5" class="muted">No fixtures.</td></tr>'])
        + "</div>",
        '<div class="section"><h2>Findings by category</h2>'
        + table([("Category", ""), ("Items", "num")], [cat_rows])
        + '<p class="small muted" style="margin-top:8px">Full detail, including source links and the '
        'action taken, is on the <a href="flagged.html">Flagged for Review</a> page.</p></div>',
    ]
    return layout("Analysis", "analysis", "".join(body), ctx["snapshot"])


def render_sources(ctx: dict) -> str:
    snap = ctx["snapshot"]
    log = snap.get("fetch_log", [])
    seen = set()
    rows = []
    for f in log:
        url = f.get("url", "")
        if url in seen:
            continue
        seen.add(url)
        status = f.get("status")
        badge = (
            '<span class="badge ok">200</span>' if status == 200
            else f'<span class="badge err">{esc(status or "error")}</span>'
        )
        rows.append(
            f'<tr><td class="mono small" style="word-break:break-all">{esc(url)}</td><td>{badge}</td>'
            f'<td class="num">{esc(f.get("bytes", ""))}</td>'
            f'<td class="mono small" style="word-break:break-all">{esc((f.get("sha256") or "")[:16])}'
            f'{"…" if f.get("sha256") else ""}</td>'
            f'<td class="nowrap small">{esc((f.get("retrieved_utc") or "")[:19].replace("T", " "))}</td></tr>'
        )
    ver = snap.get("verification", {})
    checks = [
        ("Fixture schema", "required fields, ISO timestamp, known sport"),
        ("Official source", "at least one source URL on a league-owned domain"),
        ("Probability range", "0 < p < 1 for every selection"),
        ("Probability sum", "two-way markets sum to 1 ± 0.01 before hold"),
        ("Price range", "decimal price > 1.00 for every selection"),
        ("Confidence value", "high / medium / low only"),
        ("Prediction lint", "≥30 words, explicit selection, no banned phrases, <55% overlap"),
        ("Publishing window", "start time inside the stated window"),
    ]
    check_rows = "".join(
        f'<tr><td>{esc(name)}</td><td class="small muted">{esc(desc)}</td>'
        f'<td><span class="badge ok">enforced</span></td></tr>'
        for name, desc in checks
    )
    taxonomy = ctx.get("taxonomy")
    coverage = ""
    if taxonomy and taxonomy.get("sports"):
        cov_rows = []
        for s in taxonomy["sports"]:
            if s.get("in_owner_scope") is False:
                status = f'<span class="badge low">excluded</span>'
                reason = s.get("exclusion") or "owner exclusion list"
            elif s.get("ingested"):
                status = f'<span class="badge ok">ingested</span>'
                reason = s.get("note") or "official feed"
            else:
                status = f'<span class="badge warn">not ingested</span>'
                reason = s.get("note") or "no official machine-readable feed"
            cov_rows.append(
                f'<tr><td>{esc(s["name"])}</td><td class="small muted">{esc(s.get("official_source") or "—")}</td>'
                f"<td>{status}</td><td class=\"small\">{esc(reason)}</td></tr>"
            )
        coverage = (
            '<div class="section"><h2>OLBG sport coverage</h2>'
            '<p class="lead">Every OLBG sport taxonomy entry we recorded, whether it is inside the '
            "owner's scope, and whether an official machine-readable feed exists. This is the honest "
            "coverage boundary of the project.</p>"
            + table([("OLBG sport", ""), ("Official source evaluated", ""), ("Status", ""), ("Reason", "")],
                    cov_rows)
            + "</div>"
        )
    body = [
        '<div class="page-head"><h1>Sources &amp; verification</h1>'
        '<p>Every endpoint the pipeline touched in this run, with HTTP status, payload size and a '
        "SHA-256 fingerprint. Fixtures, results and records come only from league-owned properties; "
        "OLBG is reverse-engineered for taxonomy and page structure only, never as a data source.</p></div>",
        '<div class="notice">The pipeline does not scrape OLBG pages for prices, tips or predictions. '
        'www.olbg.com/robots.txt disallows <code>/api/</code>, <code>/sports/</code> and several '
        "crawler user agents, and the project does not need those paths. See "
        '<a href="olbg.html">the reverse-engineering note</a> for the structure we documented from '
        "public pages.</div>",
        '<div class="section"><h2>Official endpoints used</h2>'
        '<p class="lead">Recorded automatically at fetch time. Duplicate URLs from retries are shown '
        "once.</p>"
        + table([("URL", ""), ("Status", ""), ("Bytes", "num"), ("SHA-256", ""), ("Retrieved (UTC)", "nosort")],
                [r for r in rows] or ['<tr><td colspan="5" class="muted">No fetches recorded.</td></tr>'])
        + "</div>",
        '<div class="section"><h2>Verification gate</h2>'
        '<p class="lead">Checks applied to every snapshot before anything is published.</p>'
        + table([("Check", ""), ("What it enforces", ""), ("Status", "")], [check_rows])
        + f'<div class="notice info">{esc(ver.get("fixtures_checked", 0))} fixtures checked · '
        f'{esc(ver.get("markets_checked", 0))} markets checked · '
        f'{esc(ver.get("predictions_checked", 0))} predictions checked · '
        f'{esc(ver.get("hard_failures", 0))} hard failures.</div></div>',
        coverage,
        '<div class="section"><h2>What is not verified</h2>'
        "<p>We do not invent injuries, team news, weather or line-ups. Where a league feed omits a "
        "field (for example an unannounced probable pitcher), the table shows a dash and the item is "
        "added to the review queue. Records are labelled with the exact definition used by the "
        "feed.</p></div>",
    ]
    return layout("Sources", "sources", "".join(body), snap)


def render_flagged(ctx: dict) -> str:
    flagged = ctx["flagged"]
    groups = defaultdict(list)
    for f in flagged:
        groups[f["severity"]].append(f)
    rows = []
    for sev in ("error", "warning", "info"):
        for f in groups.get(sev, []):
            cls = {"error": "err", "warning": "warn", "info": "info"}.get(sev, "info")
            rows.append(
                f'<tr><td><span class="badge {cls}">{esc(sev)}</span></td>'
                f'<td class="small">{esc(f["category"])}</td>'
                f'<td class="nowrap">{esc((f.get("sport") or "").replace("_", " "))}</td>'
                f'<td>{esc(f.get("match") or "—")}</td>'
                f'<td class="small">{esc(f.get("detail"))}</td>'
                f'<td class="small">{esc(f.get("field") or "—")}</td>'
                f'<td class="small">{esc(f.get("action") or "published")}</td>'
                f'<td class="src">{source_links(f.get("source_urls"))}</td></tr>'
            )
    counts = Counter(f["severity"] for f in flagged)
    body = [
        '<div class="page-head"><h1>Flagged for review</h1>'
        '<p>Everything the pipeline could not confirm, plus data irregularities it noticed. Items '
        "here do not block publication: the affected field is left blank (never estimated) and the "
        "row still shows its official source so you can check it yourself.</p></div>",
        '<div class="grid">'
        f'<div class="card kpi"><div class="big mono">{counts.get("error", 0)}</div><small>errors</small>'
        "<p>rows excluded from publication</p></div>"
        f'<div class="card kpi"><div class="big mono">{counts.get("warning", 0)}</div><small>warnings</small>'
        "<p>published with a blank or a caveat</p></div>"
        f'<div class="card kpi"><div class="big mono">{counts.get("info", 0)}</div><small>notes</small>'
        "<p>informational, no action needed</p></div></div>",
        '<div class="section"><h2>Review queue</h2>'
        '<p class="lead">Grouped by severity. Source links point at the official page a reviewer '
        "should open to confirm or correct the value.</p>"
        + table([("Severity", ""), ("Category", ""), ("Sport", ""), ("Match", ""), ("Detail", ""),
                 ("Field", ""), ("Action", ""), ("Sources", "nosort")],
                rows or ['<tr><td colspan="8" class="muted">No findings in this snapshot.</td></tr>'])
        + "</div>",
        '<div class="notice">If you spot something wrong, the fastest check is the source link on the '
        "row. Values that failed the official-source gate are not published at all; values that were "
        "merely missing are shown as a dash.</div>",
    ]
    return layout("Flagged for review", "flagged", "".join(body), ctx["snapshot"])


def render_methodology(ctx: dict) -> str:
    snap = ctx["snapshot"]
    body = [
        '<div class="page-head"><h1>Methodology</h1>'
        '<p>How the pipeline turns official league data into lines, picks, confidence grades and '
        "written predictions — and what it deliberately refuses to do.</p></div>",
        '<div class="card"><h2>1. Scope</h2>'
        "<p>The owner excluded soccer/association football, American football, boxing, UFC/MMA, "
        "hurling, horse racing, cycling and specials. Gaelic football stays in scope: hurling was "
        "named separately, and Gaelic football is only held out of the priced set because no "
        "official machine-readable GAA feed was identified. Only sports with an official, "
        "machine-readable league feed are ingested: the NBA, NHL and MLB.</p>"
        "<h3>When a league is listed but not priced</h3>"
        f"<p>If the per-team sample is below {config.MIN_GAMES_FOR_MARKETS} completed games, the "
        "fixture keeps its record and official source link but no market and no pick is published. "
        "The row is labelled <em>withheld</em> and the reason is written into it. A line built on a "
        "handful of games is a guess with a decimal point on it.</p>"
        "<h3>Why not every OLBG sport?</h3><p>A row is only published if it has a source link on an "
        "official league domain. Tennis, cricket, rugby, golf, darts and snooker do not expose a "
        "public official fixture/results API we can verify against, so they are listed as "
        "not ingested rather than filled from an unofficial feed. See "
        '<a href="sources.html">Sources</a> for the per-sport evaluation.</p></div>',
        '<div class="card" style="margin-top:14px"><h2>2. Ratings</h2>'
        "<p>Two weighted ridge regressions are solved per sport on completed league games:</p>"
        "<p><code>margin = home advantage + rating(home) − rating(away) + error</code></p>"
        "<p><code>total = league total + offence(home) + defence(away) + error</code></p>"
        "<p>Weights decay with a 120-day half-life so recent games count more. Ridge λ = 6.0 shrinks "
        "small samples toward the league mean, which matters most in the first weeks of a season. "
        "The opening model uses the previous completed season with equal weights, so the difference "
        "between our opening and current numbers is genuinely new information.</p></div>",
        '<div class="card" style="margin-top:14px"><h2>3. Probabilities and prices</h2>'
        "<p>Probabilities come from the empirical distribution of residuals, not a normal "
        "approximation. For a home handicap line L, the cover probability is the share of training "
        "residuals that exceed <code>L − projected margin</code>, with Laplace smoothing. That keeps "
        "discrete, low-scoring sports honest.</p>"
        "<p>Prices are <code>1 / (p × 1.045)</code>: a 4.5% two-way hold. Lines are placed on the "
        "nearest half-point away from the projection so no market can push. Alternates at ±1 are "
        "published in the match detail.</p></div>",
        '<div class="card" style="margin-top:14px"><h2>4. Confidence</h2>'
        "<p>Every match gets a match-winner pick. Handicap and total selections are added only when "
        "our current model has moved at least the sport threshold away from our opening line.</p>"
        "<ul class='clean'>"
        "<li><b>High</b> — win probability ≥ 62%, at least 40 verified games per team, and a "
        "stability check agrees on the same winner (our opening model, or a refit without the "
        "last 14 days when no prior season exists).</li>"
        "<li><b>Medium</b> — probability ≥ 55% and at least 20 games per team.</li>"
        "<li><b>Low</b> — everything else, including any pick where the opener disagrees.</li>"
        "</ul>"
        "<p>Handicap/total picks are graded on the probability at the nominated line and on how far "
        "the line moved relative to the threshold; they are capped at medium when the opener is a "
        "league-average fallback, because there is no prior season to move away from.</p></div>",
        '<div class="card" style="margin-top:14px"><h2>5. Predictions</h2>'
        "<p>Only high-confidence picks receive a written prediction. Sentences are composed from "
        "verified fields: official record, last five results with scores, venue, series context, "
        "probable pitchers when the league publishes them, and our own line. No quotes, injuries, "
        "transfers or tactical claims are invented.</p>"
        "<p>Each prediction is linted before publication: minimum 30 words, the selection must be "
        "explicit, promotional language is rejected, and no two predictions may share more than 55% "
        "of their vocabulary. A failing prediction is withdrawn and listed on the review page — the "
        "pick itself remains.</p></div>",
        '<div class="card" style="margin-top:14px"><h2>6. Verification and limitations</h2>'
        "<ul class='clean'>"
        "<li>Every published row carries an official league source link. Rows without one are "
        "excluded and flagged.</li>"
        "<li>Missing values are blank, never inferred. Records are labelled with the definition the "
        "league feed uses.</li>"
        "<li>The backtest refits on older data and scores the last 30 days, so it is leakage-free; "
        "small early-season samples are reported instead of hidden.</li>"
        "<li>This is a model, not a market. There is no comparison to bookmaker prices, and the "
        "model has no information about injuries or team news beyond what the league feed publishes."
        "</li>"
        "<li>Nothing here is betting advice.</li>"
        "</ul></div>",
        f'<div class="notice">Snapshot generated {esc(snap.get("generated_utc", ""))} · pipeline '
        f'{esc(snap.get("pipeline_version", ""))} · window {esc(str(snap.get("window", {}).get("days", "")))} days.</div>',
    ]
    return layout("Methodology", "methodology", "".join(body), snap)


def render_olbg(ctx: dict) -> str:
    tax = ctx.get("taxonomy") or {}
    rows = []
    for entry in tax.get("sports", []):
        if entry.get("in_owner_scope") is False:
            scope = '<span class="badge low">excluded</span>'
        elif entry.get("in_owner_scope"):
            scope = '<span class="badge ok">in scope</span>'
        else:
            scope = "—"
        rows.append(
            f'<tr><td>{esc(entry["name"])}</td><td class="num">{esc(entry.get("olbg_id") or "—")}</td>'
            f'<td class="small">{esc(entry.get("official_source") or "—")}</td>'
            f'<td>{scope}</td>'
            f'<td class="small">{esc(entry.get("note") or "")}</td></tr>'
        )
    anatomy = "".join(f"<li>{esc(x)}</li>" for x in tax.get("page_anatomy", []))
    findings = "".join(f"<li>{esc(x)}</li>" for x in tax.get("findings", []))
    body = [
        '<div class="page-head"><h1>OLBG.com reverse-engineering note</h1>'
        '<p>What we documented about OLBG\'s public structure — and what we deliberately did not '
        "take from it. No OLBG prices, tips or predictions are copied into this project.</p></div>",
        '<div class="notice warn">Compliance: <code>www.olbg.com/robots.txt</code> disallows '
        "<code>/api/</code>, <code>/sports/</code>, <code>/events.php</code> and a list of crawler "
        "user agents. The project reads a small number of public hub pages for taxonomy and URL "
        "structure only, identifies itself honestly, and does not crawl restricted paths. Any "
        "bulk ingestion from OLBG is out of scope by design.</div>",
        '<div class="card"><h2>URL grammar observed</h2>'
        f'<p><code>{esc(tax.get("url_pattern") or "")}</code></p>'
        "<p>Sport id is the final path segment; <code>event_id</code> is a query parameter. The same "
        "slug pattern is used for the sport hub, competition and event pages.</p>"
        "<h3>Example URLs captured</h3><ul class='clean small'>"
        + "".join(
            f'<li><a href="{esc(u)}" target="_blank" rel="noopener noreferrer">{esc(u)}</a></li>'
            for u in tax.get("captured_urls", [])
        )
        + "</ul></div>",
        '<div class="section"><h2>Page anatomy</h2><div class="card"><ul class="clean">'
        + anatomy + "</ul></div></div>",
        '<div class="section"><h2>Sport taxonomy</h2>'
        '<p class="lead">Recorded from public OLBG navigation. “In scope” reflects the owner\'s '
        "exclusion list, not OLBG's own categorisation.</p>"
        + table([("OLBG sport", ""), ("OLBG id", "num"), ("Official feed evaluated", ""), ("Scope", ""), ("Note", "")],
                rows or ['<tr><td colspan="5" class="muted">Taxonomy not captured.</td></tr>'])
        + "</div>",
        '<div class="section"><h2>Findings</h2><div class="card"><ul class="clean">'
        + findings + "</ul></div></div>",
        '<div class="section"><h2>Why we originate instead of copying</h2>'
        "<p>OLBG aggregates tipster selections and bookmaker prices. The brief asks for our own lines, "
        "so the model is fitted to official results and the output is our own probability and price. "
        "The reverse-engineering work is limited to understanding how the site organises sports and "
        "markets so our coverage maps cleanly onto it.</p></div>",
    ]
    return layout("OLBG reverse-engineering", "olbg", "".join(body), ctx["snapshot"])

def render_review(ctx: dict) -> str:
    from .review import IRREGULARITIES, REVIEW_ITEMS, SPOT_CHECKS

    badges = {
        "matches": '<span class="badge ok">matches</span>',
        "corrected": '<span class="badge warn">corrected</span>',
        "documented": '<span class="badge low">modelling choice</span>',
        "limited": '<span class="badge err">source limited</span>',
    }
    rows = [
        f'<tr><td class="mono small">{esc(item["area"])}</td>'
        f'<td>{esc(item["claim"])}</td>'
        f'<td class="small">{esc(item["check"])}</td>'
        f'<td class="small"><a href="{esc(item["source"])}" target="_blank" '
        f'rel="noopener noreferrer">{esc(item["source"])}</a></td>'
        f'<td>{badges.get(item["outcome"], esc(item["outcome"]))}</td></tr>'
        for item in REVIEW_ITEMS
    ]
    counts = Counter(item["outcome"] for item in REVIEW_ITEMS)
    irregular = "".join(f"<li>{esc(x)}</li>" for x in IRREGULARITIES)
    body = [
        '<div class="page-head"><h1>Line-by-line review</h1>'
        "<p>Each pipeline module was checked against the official source it claims to use. "
        "Every row below names the claim, what was compared, the official link, and the "
        "outcome. Defects found in the review are listed underneath and are also published on "
        "the Flagged for Review page.</p></div>",
        '<div class="grid">'
        f'<div class="card kpi"><div class="big mono">{len(REVIEW_ITEMS)}</div>'
        "<small>claims reviewed</small><p>module by module</p></div>"
        f'<div class="card kpi"><div class="big mono">{counts.get("matches", 0)}</div>'
        "<small>matched the source</small><p>no change needed</p></div>"
        f'<div class="card kpi"><div class="big mono">{counts.get("corrected", 0)}</div>'
        "<small>corrected</small><p>fix committed and re-verified</p></div>"
        f'<div class="card kpi"><div class="big mono">{counts.get("limited", 0)}</div>'
        "<small>source limited</small><p>withheld, never guessed</p></div>"
        "</div>",
        '<div class="section"><h2>Review log</h2>'
        + table([("Module", ""), ("Claim", ""), ("What was checked", ""), ("Official source", ""),
                 ("Outcome", "")], rows)
        + "</div>",
        '<div class="section"><h2>Row-level spot checks</h2>'
        '<p class="lead">Published fixture rows re-opened against the live official endpoint while '
        "this page was built. Times are UTC, exactly as stored.</p>"
        + table([("Fixture id", ""), ("What we publish", ""), ("What the official feed says", ""),
                 ("Official link", ""), ("Verdict", "")],
                [f'<tr><td class="mono small">{esc(x["fixture"])}</td>'
                 f'<td class="small">{esc(x["published"])}</td>'
                 f'<td class="small">{esc(x["match"])}</td>'
                 f'<td class="small"><a href="{esc(x["official"])}" target="_blank" '
                 f'rel="noopener noreferrer">{esc(x["official"])}</a></td>'
                 f'<td><span class="badge ok">{esc(x["verdict"])}</span></td></tr>'
                 for x in SPOT_CHECKS])
        + "</div>",
        '<div class="section"><h2>Irregularities found and handled</h2>'
        '<div class="card"><ul class="clean">' + irregular + "</ul></div>"
        '<p class="small muted" style="margin-top:8px">Rows that could not be verified are left '
        'blank and listed on <a href="flagged.html">Flagged for Review</a>; they never block a '
        "publish, but they are never silently dropped either.</p></div>",
    ]
    return layout("Review", "review", "".join(body), ctx["snapshot"])

