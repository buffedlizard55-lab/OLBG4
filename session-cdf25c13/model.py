"""Board T line-origination model.

Design rules
------------
* Every input is an official league figure (see data.py). No bookmaker or OLBG price is
  read, stored or used anywhere in this file.
* Prices are FAIR odds (1/p). We apply no betting margin, because Board T is originating a
  line for comparison, not acting as a bookmaker; adding vig would silently move every
  price and is therefore disclosed rather than applied.
* All probabilities are computed from the published league tables. Where a table does not
  publish a quantity the market is not originated and the reason is recorded.

Markets
-------
match_winner   moneyline (NHL: incl. OT/SO; URC: 3-way; NBA/MLB: 2-way)
handicap       NHL puck line +/-1.5, NBA spread, URC handicap, MLB run line +/-1.5
total          match total (over/under)
"""
from __future__ import annotations

import math

FAIR = True          # fair odds, no margin
K_NHL = 6.0          # shrinkage games toward league average
K_URC = 3.0
K_NBA = 10.0
K_MLB = 40.0


# --------------------------------------------------------------------- maths
def phi(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def pois(k: int, lam: float) -> float:
    return math.exp(-lam) * lam ** k / math.factorial(k)


def joint(lh: float, la: float, mx: int = 22):
    out = {}
    for h in range(mx + 1):
        for a in range(mx + 1):
            out[(h, a)] = pois(h, lh) * pois(a, la)
    return out


def dec(prob: float) -> float:
    """Fair decimal price, 2dp, floored at 1.01."""
    if prob <= 0:
        return 0.0
    return round(max(1.01, 1.0 / prob), 2)


def american(price: float) -> str:
    if price <= 0:
        return ""
    if price >= 2.0:
        return f"+{round((price - 1.0) * 100)}"
    return f"-{round(100.0 / (price - 1.0))}"


def price(prob: float) -> dict:
    d = dec(prob)
    return {"prob": round(prob, 4), "decimal": d, "american": american(d)}


def window_ok(price_decimal: float) -> bool:
    """The requested focus range: -250 to +10,000 American == 1.40 to 101.00 decimal."""
    return 1.40 <= price_decimal <= 101.00


# --------------------------------------------------------------------- NHL
def nhl_league_average():
    tot_gf, tot_gp = 0, 0
    for name, gp, w, l, ot, pts, gf, ga, l10, st in _nhl_rows():
        tot_gf += gf
        tot_gp += gp
    return tot_gf / tot_gp, tot_gp


def _nhl_rows():
    from . import data  # type: ignore
    for abbr, t in data.NHL_TEAMS.items():
        if t[1] is None:
            continue
        yield (abbr, t[1], t[2], t[3], t[4], t[5], t[6], t[7], t[8], t[9])


def nhl_ratings():
    from . import data  # type: ignore
    L, _ = nhl_league_average()
    out = {}
    for abbr, t in data.NHL_TEAMS.items():
        name, gp, w, l, ot, pts, gf, ga, l10, st = t
        if gp is None:
            out[abbr] = {"name": name, "attack": 1.0, "defence": 1.0,
                         "gp": None, "note": "no row in the standings table read"}
            continue
        att = ((gf + K_NHL * L * 1.0) / (gp + K_NHL)) / L
        dfn = ((ga + K_NHL * L * 1.0) / (gp + K_NHL)) / L
        out[abbr] = {"name": name, "attack": round(att, 4), "defence": round(dfn, 4),
                     "gp": gp, "gf": gf, "ga": ga, "pts": pts, "l10": l10, "streak": st,
                     "w": w, "l": l, "ot": ot}
    return out, L


HFA_NHL = 1.035   # documented model assumption: home ice multiplier on expected goals


def nhl_markets(home: str, away: str):
    from . import data  # type: ignore
    r, L = nhl_ratings()
    h, a = r[home], r[away]
    lh = L * h["attack"] * a["defence"] * HFA_NHL
    la = L * a["attack"] * h["defence"] / HFA_NHL
    jd = joint(lh, la)
    ph = sum(p for (x, y), p in jd.items() if x > y)
    pd = sum(p for (x, y), p in jd.items() if x == y)
    pa = sum(p for (x, y), p in jd.items() if x < y)
    # NHL games cannot end level: overtime/shootout split the regulation draw 50/50.
    ml_home, ml_away = ph + pd / 2, pa + pd / 2
    pl_home_minus = sum(p for (x, y), p in jd.items() if x - y >= 2)   # -1.5 covers
    pl_away_plus = 1 - pl_home_minus
    pl_home_plus = sum(p for (x, y), p in jd.items() if x - y >= -1)
    pl_away_minus = 1 - pl_home_plus
    exp_total = lh + la
    base = 5.5 if exp_total < 6.0 else 6.5
    line = base
    over = sum(p for (x, y), p in jd.items() if x + y > line)
    alternates = {}
    for ln in (base - 1.0, base + 1.0):
        po = sum(p for (x, y), p in jd.items() if x + y > ln)
        alternates[f"Over {ln}"] = price(po)
        alternates[f"Under {ln}"] = price(1 - po)
    return {
        "lambda_home": round(lh, 3), "lambda_away": round(la, 3),
        "exp_total": round(exp_total, 2),
        "markets": {
            "match_winner": {
                f"{h['name']} (ML)": price(ml_home),
                f"{a['name']} (ML)": price(ml_away),
            },
            "handicap": {
                f"{h['name']} -1.5": price(pl_home_minus),
                f"{a['name']} +1.5": price(pl_away_plus),
            },
            "total": {f"Over {line}": price(over), f"Under {line}": price(1 - over)},
        },
        "alternates": alternates,
        "lines": {"handicap": f"{h['name']} -1.5 / {a['name']} +1.5", "total": str(line)},
        "sample": min(h["gp"] or 0, a["gp"] or 0),
        "facts": {"home": h, "away": a, "league_goals": round(L, 3)},
    }


# --------------------------------------------------------------------- NBA
def nba_pct(rec):
    import math as _m
    w, l = rec
    gp = w + l
    return (w + K_NBA * 0.5) / (gp + K_NBA)


def nba_markets(home: str, away: str):
    from . import data  # type: ignore
    hn, hw, hl = data.NBA_TEAMS[home]
    an, aw, al = data.NBA_TEAMS[away]
    ph, pa = nba_pct((hw, hl)), nba_pct((aw, al))
    # log5
    p = (ph - ph * pa) / (ph + pa - 2 * ph * pa)
    p = min(0.95, max(0.05, p + 0.03))     # documented home-court adjustment
    return {
        "lambda_home": None, "lambda_away": None, "exp_total": None,
        "markets": {"match_winner": {f"{hn} (ML)": price(p), f"{an} (ML)": price(1 - p)}},
        "alternates": {},
        "lines": {"handicap": "not originated", "total": "not originated"},
        "sample": min(hw + hl, aw + al),
        "facts": {"home": {"name": hn, "w": hw, "l": hl, "pct": round(ph, 4)},
                  "away": {"name": an, "w": aw, "l": al, "pct": round(pa, 4)}},
        "blank_reason": ("The official standings view read this session publishes W-L only, "
                         "not points for/against, so a spread or total cannot be originated "
                         "without inventing an input."),
    }


# --------------------------------------------------------------------- MLB
def mlb_markets(home: str, away: str, home_field=True):
    from . import data  # type: ignore
    H, A = data.MLB_TEAMS[home], data.MLB_TEAMS[away]
    h_rs, h_ra = H["rs"] / H["gp"], H["ra"] / H["gp"]
    a_rs, a_ra = A["rs"] / A["gp"], A["ra"] / A["gp"]
    # blend each offence with the opponent's defence; shrink both toward each other
    lh = ((h_rs + a_ra) / 2) * 1.02 if home_field else ((h_rs + a_ra) / 2) * 0.99
    la = ((a_rs + h_ra) / 2) * 0.99 if home_field else ((a_rs + h_ra) / 2) * 1.02
    margin, sd_m = lh - la, 3.3
    ph = phi(margin / sd_m)
    total = lh + la
    line = math.floor(total) + 0.5
    over = 1 - phi((line - total) / 4.2)
    alternates = {}
    for ln in (line - 1.0, line + 1.0):
        po = 1 - phi((ln - total) / 4.2)
        alternates[f"Over {ln}"] = price(po)
        alternates[f"Under {ln}"] = price(1 - po)
    rl_home = 1 - phi((1.5 - margin) / sd_m)   # home -1.5
    rl_away = 1 - phi((1.5 + margin) / sd_m)   # away -1.5
    return {
        "lambda_home": round(lh, 3), "lambda_away": round(la, 3), "exp_total": round(total, 2),
        "markets": {
            "match_winner": {f"{H['name']} (ML)": price(ph), f"{A['name']} (ML)": price(1 - ph)},
            "handicap": {f"{H['name']} -1.5": price(rl_home), f"{A['name']} -1.5": price(rl_away)},
            "total": {f"Over {line}": price(over), f"Under {line}": price(1 - over)},
        },
        "alternates": alternates,
        "lines": {"handicap": "-1.5 (both sides)", "total": str(line)},
        "sample": min(H["gp"], A["gp"]),
        "facts": {"home": H, "away": A},
    }


# --------------------------------------------------------------------- URC
def urc_league_average():
    from . import data  # type: ignore
    tot, gp = 0.0, 0
    for k, t in data.URC_TEAMS.items():
        tot += t[5]
        gp += t[1]
    return tot / gp, gp


HFA_URC = 1.03
SD_URC_MARGIN = 13.0
SD_URC_TOTAL = 12.0


def urc_markets(home: str, away: str):
    from . import data  # type: ignore
    L, _ = urc_league_average()
    H, A = data.URC_TEAMS[home], data.URC_TEAMS[away]
    def rates(t):
        pl, pf, pa = t[1], t[5], t[6]
        att = ((pf + K_URC * L) / (pl + K_URC)) / L
        dfn = ((pa + K_URC * L) / (pl + K_URC)) / L
        return att, dfn
    ha, hd = rates(H)
    aa, ad = rates(A)
    lh = L * ha * ad * HFA_URC
    la = L * aa * hd / HFA_URC
    m = lh - la
    total = lh + la
    ph = phi((m - 0.5) / SD_URC_MARGIN)
    pdraw = phi((0.5 - m) / SD_URC_MARGIN) - phi((-0.5 - m) / SD_URC_MARGIN)
    pa = 1 - ph - pdraw
    line = round(m * 2) / -2.0
    if line == 0:
        line = -0.5
    cover = 1 - phi((abs(line) - m * (1 if line < 0 else -1)) / SD_URC_MARGIN) if False else None
    # handicap: home line `line`; home covers if margin + line > 0
    p_home_cover = 1 - phi((-line - m) / SD_URC_MARGIN)
    tline = math.floor(total) + 0.5
    over = 1 - phi((tline - total) / SD_URC_TOTAL)
    alternates = {}
    for ln in (tline - 3.0, tline + 3.0):
        po = 1 - phi((ln - total) / SD_URC_TOTAL)
        alternates[f"Over {ln}"] = price(po)
        alternates[f"Under {ln}"] = price(1 - po)
    return {
        "lambda_home": round(lh, 2), "lambda_away": round(la, 2), "exp_total": round(total, 2),
        "markets": {
            "match_winner": {"Home": price(ph), "Draw": price(pdraw), "Away": price(pa)},
            "handicap": {f"{H[0]} {line:+.1f}": price(p_home_cover),
                         f"{A[0]} {-line:+.1f}": price(1 - p_home_cover)},
            "total": {f"Over {tline}": price(over), f"Under {tline}": price(1 - over)},
        },
        "alternates": alternates,
        "lines": {"handicap": f"{line:+.1f} / {-line:+.1f}", "total": str(tline)},
        "sample": min(H[1], A[1]),
        "facts": {"home": {"name": H[0], "pl": H[1], "pf": H[5], "pa": H[6], "pts": H[7],
                           "form": H[8]},
                  "away": {"name": A[0], "pl": A[1], "pf": A[5], "pa": A[6], "pts": A[7],
                           "form": A[8]}},
    }
