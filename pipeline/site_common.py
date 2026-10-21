"""Shared rendering helpers for the static dashboard."""
from __future__ import annotations

import html
from datetime import datetime

from .records import parse_iso

SPORTS = [
    ("basketball", "NBA", "nba", "Basketball"),
    ("ice_hockey", "NHL", "nhl", "Ice Hockey"),
    ("baseball", "MLB", "mlb", "Baseball"),
]
SPORT_META = {key: {"league": lg, "slug": slug, "label": lab} for key, lg, slug, lab in SPORTS}

NAV = [
    ("index.html", "Overview", "overview"),
    ("matches.html", "Matches", "matches"),
    ("picks.html", "Picks", "picks"),
    ("analysis.html", "Analysis", "analysis"),
    ("sport-nba.html", "NBA", "nba"),
    ("sport-nhl.html", "NHL", "nhl"),
    ("sport-mlb.html", "MLB", "mlb"),
    ("markets.html", "Markets", "markets"),
    ("sources.html", "Sources", "sources"),
]


def esc(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def fmt_dt(iso_value: str | None) -> str:
    if not iso_value:
        return ""
    try:
        dt = parse_iso(iso_value)
    except Exception:  # noqa: BLE001
        return esc(iso_value)
    return dt.strftime("%a %d %b, %H:%M UTC")


def fmt_time(iso_value: str | None) -> str:
    if not iso_value:
        return ""
    try:
        return parse_iso(iso_value).strftime("%H:%M UTC")
    except Exception:  # noqa: BLE001
        return ""


def fmt_date(iso_value: str | None) -> str:
    if not iso_value:
        return ""
    try:
        return parse_iso(iso_value).strftime("%d %b")
    except Exception:  # noqa: BLE001
        return esc(iso_value)


def pct(value, digits: int = 1) -> str:
    if value is None:
        return ""
    return f"{value * 100:.{digits}f}%".replace(".0%", "%")


def signed(value, digits: int = 2) -> str:
    if value is None:
        return ""
    return f"{value:+.{digits}f}"


def conf_badge(conf: str | None) -> str:
    if not conf:
        return ""
    return f'<span class="badge {esc(conf)}">{esc(conf)}</span>'


def sport_badge(sport: str) -> str:
    meta = SPORT_META.get(sport, {"league": sport.upper()})
    return f'<span class="badge sport">{esc(meta["league"])}</span>'


def layout(title: str, active: str, body: str, snapshot: dict, subtitle: str = "") -> str:
    flagged = len((snapshot or {}).get("_flagged_count", []) or [])
    nav_html = []
    for href, label, key in NAV:
        cls = "active" if key == active else ""
        nav_html.append(f'<a href="{href}" class="{cls}">{esc(label)}</a>')
    flag_cls = "active" if active == "flagged" else ""
    nav_html.append(
        f'<a href="flagged.html" class="flag {flag_cls}">Flagged'
        f'<span class="pill-count">{flagged}</span></a>'
    )
    generated = (snapshot or {}).get("generated_utc", "")
    window = (snapshot or {}).get("window", {})
    window_txt = ""
    if window:
        try:
            window_txt = (
                f'{parse_iso(window["start"]).strftime("%d %b %Y")}'
                f' – {parse_iso(window["end"]).strftime("%d %b %Y")}'
            )
        except Exception:  # noqa: BLE001
            window_txt = ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · OLBG4</title>
<meta name="description" content="Automated multi-sport line origination, picks and verification dashboard built from official league data.">
<link rel="stylesheet" href="assets/site.css">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='8' fill='%230f766e'/><text x='16' y='22' font-family='Arial' font-size='14' font-weight='700' fill='white' text-anchor='middle'>O4</text></svg>">
</head>
<body>
<header class="site">
  <div class="wrap head">
    <a class="brand" href="index.html"><span class="mark">O4</span>
      <span>OLBG4 <small>Line origination &amp; picks desk</small></span></a>
    <nav class="main">{''.join(nav_html)}</nav>
  </div>
</header>
<main>
  <div class="wrap">
    {f'<div class="crumb">{esc(subtitle)}</div>' if subtitle else ''}
    {body}
  </div>
</main>
<footer class="site">
  <div class="wrap">
    <span>Snapshot {esc(generated[:16].replace('T', ' '))} UTC · window {esc(window_txt)}</span>
    <span class="spacer"></span>
    <a href="../index.html">← All dashboards</a>
    <a href="methodology.html">Methodology</a>
    <a href="sources.html">Sources</a>
    <a href="olbg.html">OLBG reverse-engineering</a>
    <a href="flagged.html">Flagged for review</a>
    <a href="https://github.com/buffedlizard55-lab/OLBG4">GitHub</a>
  </div>
  <div class="wrap" style="margin-top:8px">
    <span>Model output for research and review. Not betting advice. Odds are our own originated prices, not a bookmaker's. 18+.</span>
  </div>
</footer>
<script src="assets/site.js"></script>
</body>
</html>"""


def table(headers: list[tuple[str, str]], rows: list[str], *, filterable: bool = False,
          table_id: str = "") -> str:
    """headers: list of (label, css_class); rows already rendered."""
    ths = []
    for label, cls in headers:
        sortable = "data-sortable" if "nosort" not in cls else ""
        ths.append(f'<th class="{cls}" {sortable}>{esc(label)}</th>')
    attrs = 'data-filterable="1"' if filterable else ""
    if table_id:
        attrs += f' id="{esc(table_id)}"'
    return (
        f'<div class="table-wrap"><table {attrs}><thead><tr>{"".join(ths)}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>'
    )


def filters(show_sport: bool = True, show_confidence: bool = True, show_market: bool = False) -> str:
    parts = ['<div class="filters">',
             '<input type="search" data-filter="search" placeholder="Search team, pick or venue…" '
             'aria-label="Search">']
    if show_sport:
        parts.append(
            '<select data-filter="sport" aria-label="Sport"><option value="">All sports</option>'
            + "".join(f'<option value="{k}">{esc(v["league"])}</option>' for k, v in SPORT_META.items())
            + "</select>"
        )
    if show_confidence:
        parts.append(
            '<select data-filter="confidence" aria-label="Confidence">'
            '<option value="">All confidence</option>'
            '<option value="high">High</option><option value="medium">Medium</option>'
            '<option value="low">Low</option></select>'
        )
    if show_market:
        parts.append(
            '<select data-filter="market" aria-label="Market"><option value="">All markets</option>'
            '<option value="moneyline">Match winner</option>'
            '<option value="handicap">Handicap</option>'
            '<option value="total">Total</option></select>'
        )
    parts.append('<span class="count" data-count></span></div>')
    return "".join(parts)


def market_rows(market_key: str, market: dict, unit: str) -> str:
    """Render one market's full price ladder as a small table."""
    name = market.get("name") or market.get("label") or market_key
    extra = ""
    if market_key == "handicap":
        extra = f'Current line {market["line_home"]:+.1f} / {market["line_away"]:+.1f} · opener {market["opening_line_home"]:+.1f}'
    elif market_key == "total":
        extra = f'Current line {market["line"]:.1f} · opener {market["opening_line"]:.1f}'
    rows = "".join(
        f'<tr><td>{esc(s["name"])}</td><td class="num">{pct(s["prob"])}</td>'
        f'<td class="num">{s["price_decimal"]:.3f}</td><td class="num">{esc(s["american"])}</td>'
        f'<td class="num muted">{s["fair_decimal"]:.3f}</td></tr>'
        for s in market.get("selections", [])
    )
    alt = ""
    for a in market.get("alternates", []):
        alt += "".join(
            f'<tr><td>{esc(s["name"])}</td><td class="num">{pct(s["prob"])}</td>'
            f'<td class="num">{s["price_decimal"]:.3f}</td><td class="num">{esc(s["american"])}</td>'
            f'<td class="num muted">alt</td></tr>'
            for s in a.get("selections", [])
        )
    return f"""<div class="subtable"><table>
<thead><tr><th>{esc(name)}</th><th class="num">Model prob</th><th class="num">Our price</th>
<th class="num">American</th><th class="num">Fair</th></tr></thead>
<tbody>{rows}{alt}</tbody></table></div>
<p class="small muted" style="margin:2px 0 10px">{esc(extra)}</p>"""


def confidence_summary(snapshot: dict) -> str:
    c = (snapshot or {}).get("counts", {})
    return (
        f'href="picks.html" · <span class="badge high">high {c.get("high_picks", 0)}</span> '
        f'<span class="badge medium">medium {c.get("medium_picks", 0)}</span> '
        f'<span class="badge low">low {c.get("low_picks", 0)}</span>'
    )
