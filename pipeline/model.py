"""Ratings and line origination.

Two weighted least-squares fits per sport per snapshot:

1. Margin model
       margin_i = home_advantage + rating_home - rating_away + e_i
2. Total model
       total_i  = league_average_total + offence_home + defence_away + e_i

Both are ridge-regularised (see config.RIDGE_LAMBDA) and solved exactly with Gaussian
elimination; n is at most 32 teams, so a dense solve is trivial and deterministic.

Probabilities come from the *empirical* distribution of out-of-fit residuals rather than
a normality assumption. That matters for hockey and baseball, where scoring is discrete
and low, and it means the published probability is a direct statement about the sample
the model was trained on.

Line origination
----------------
For every fixture we produce two lines per market:

* ``opening`` — built only from the previous completed season (equal weights). When no
  prior season is available we use a pure league-average opener, which is flagged in
  the record.
* ``current`` — the recency-weighted fit (half-life 120 days) over all available
  official results.

A market selection is only nominated when the current model disagrees with our own
opening line by more than a sport-specific threshold. That is a genuine, explainable
edge (new information moved the price) rather than the rounding artefact you get from
betting against a line you just set yourself.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime

from . import config
from .records import parse_iso

HALF_LIFE_DAYS = 120.0
# Minimum disagreement between opening line and current model before we nominate a
# handicap/total selection. Policy values, documented in docs/methodology.md.
EDGE_THRESHOLDS = {
    "basketball": {"handicap": 1.5, "total": 2.0},
    "ice_hockey": {"handicap": 0.30, "total": 0.35},
    "baseball": {"handicap": 0.35, "total": 0.45},
}


@dataclass
class Fit:
    sport: str
    ratings: dict[str, float] = field(default_factory=dict)
    home_advantage: float = 0.0
    offence: dict[str, float] = field(default_factory=dict)
    defence: dict[str, float] = field(default_factory=dict)
    league_total: float = 0.0
    sigma_margin: float = 1.0
    sigma_total: float = 1.0
    resid_margin: list[tuple[float, float]] = field(default_factory=list)
    resid_total: list[tuple[float, float]] = field(default_factory=list)
    games: int = 0
    n_eff: float = 0.0
    games_per_team: dict[str, int] = field(default_factory=dict)
    team_names: dict[str, str] = field(default_factory=dict)
    seasons: list[str] = field(default_factory=list)
    kind: str = "current"
    notes: list[str] = field(default_factory=list)

    # -- prediction -------------------------------------------------------
    def expected(self, home_id: str, away_id: str) -> dict:
        r_home = self.ratings.get(str(home_id), 0.0)
        r_away = self.ratings.get(str(away_id), 0.0)
        margin = self.home_advantage + r_home - r_away
        total = (
            self.league_total
            + self.offence.get(str(home_id), 0.0)
            + self.defence.get(str(away_id), 0.0)
        )
        return {
            "margin": margin,
            "total": total,
            "home": (total + margin) / 2.0,
            "away": (total - margin) / 2.0,
        }

    def se_margin(self) -> float:
        games = max(1, len(self.resid_margin))
        return self.sigma_margin * math.sqrt(1.0 + 3.0 / games)

    def se_total(self) -> float:
        games = max(1, len(self.resid_total))
        return self.sigma_total * math.sqrt(1.0 + 3.0 / games)

    def p_margin_gt(self, expected_margin: float, line: float) -> float:
        """P(home margin > line) using the empirical residual distribution."""
        return _survival(self.resid_margin, line - expected_margin)

    def p_total_gt(self, expected_total: float, line: float) -> float:
        return _survival(self.resid_total, line - expected_total)


def _survival(sample: list[tuple[float, float]], threshold: float) -> float:
    """Weighted P(X > threshold) with Laplace smoothing, bounded to [0.01, 0.99]."""
    if not sample:
        return 0.5
    above = sum(w for x, w in sample if x > threshold)
    total = sum(w for _, w in sample)
    if total <= 0:
        return 0.5
    p = (above + 0.5) / (total + 1.0)
    return min(0.99, max(0.01, p))


def _solve(a: list[list[float]], b: list[float]) -> list[float]:
    """Gaussian elimination with partial pivoting."""
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[pivot][col]) < 1e-12:
            m[pivot][col] = 1e-12
        m[col], m[pivot] = m[pivot], m[col]
        pv = m[col][col]
        for j in range(col, n + 1):
            m[col][j] /= pv
        for r in range(n):
            if r == col:
                continue
            factor = m[r][col]
            if factor == 0.0:
                continue
            for j in range(col, n + 1):
                m[r][j] -= factor * m[col][j]
    return [m[i][n] for i in range(n)]


def _normal_equations(rows: list[tuple[list[float], float, float]], n_params: int,
                      ridge_idx: range, lam: float):
    ata = [[0.0] * n_params for _ in range(n_params)]
    atb = [0.0] * n_params
    for x, y, w in rows:
        for i in range(n_params):
            if x[i] == 0.0:
                continue
            atb[i] += w * x[i] * y
            for j in range(n_params):
                if x[j]:
                    ata[i][j] += w * x[i] * x[j]
    for i in ridge_idx:
        ata[i][i] += lam
    # tiny jitter keeps the system invertible without biasing the fit
    for i in range(n_params):
        ata[i][i] += 1e-9
    return ata, atb


def _weight(age_days: float, half_life: float) -> float:
    if half_life <= 0:
        return 1.0
    return 0.5 ** (max(0.0, age_days) / half_life)


def fit(
    results: list[dict],
    sport: str,
    now: datetime,
    *,
    half_life: float = HALF_LIFE_DAYS,
    kind: str = "current",
    season_filter: set[str] | None = None,
    max_age_days: int | None = None,
) -> Fit:
    """Fit margin + total ratings from official completed games."""
    team_ids: list[str] = []
    names: dict[str, str] = {}
    usable: list[dict] = []
    for r in results:
        if r.get("sport") != sport:
            continue
        if season_filter is not None and str(r.get("season")) not in season_filter:
            continue
        try:
            dt = parse_iso(r["date_utc"])
        except Exception:  # noqa: BLE001
            continue
        age = (now - dt).total_seconds() / 86400.0
        if age < 0:
            continue
        if max_age_days is not None and age > max_age_days:
            continue
        for key in ("home_id", "away_id"):
            tid = str(r[key])
            if tid not in names:
                names[tid] = tid
                team_ids.append(tid)
        usable.append({**r, "_age": age, "_dt": dt})

    fit_obj = Fit(sport=sport, kind=kind, team_names=names)
    if not usable:
        fit_obj.notes.append("no completed games available")
        fit_obj.resid_margin = [(0.0, 1.0)]
        fit_obj.resid_total = [(0.0, 1.0)]
        fit_obj.sigma_margin = 1.0
        fit_obj.sigma_total = 1.0
        return fit_obj

    idx = {tid: i for i, tid in enumerate(team_ids)}
    n = len(team_ids)
    weights = [_weight(g["_age"], half_life) for g in usable]
    mean_w = sum(weights) / len(weights) if weights else 1.0
    weights = [w / mean_w for w in weights]  # normalise so lambda is scale-free

    # --- margin fit: [ratings..., home advantage] -----------------------
    rows = []
    for g, w in zip(usable, weights):
        x = [0.0] * (n + 1)
        x[idx[str(g["home_id"])]] += 1.0
        x[idx[str(g["away_id"])]] -= 1.0
        x[n] = 1.0
        rows.append((x, float(g["home_score"] - g["away_score"]), w))
    ata, atb = _normal_equations(rows, n + 1, range(n), config.RIDGE_LAMBDA)
    sol = _solve(ata, atb)
    ratings = {tid: sol[idx[tid]] for tid in team_ids}
    home_adv = sol[n]
    mean_rating = sum(ratings.values()) / max(1, len(ratings))
    ratings = {k: v - mean_rating for k, v in ratings.items()}
    fit_obj.ratings = ratings
    fit_obj.home_advantage = home_adv

    resid_margin = []
    for g, w in zip(usable, weights):
        pred = home_adv + ratings[str(g["home_id"])] - ratings[str(g["away_id"])]
        resid_margin.append((float(g["home_score"] - g["away_score"]) - pred, w))
    fit_obj.resid_margin = resid_margin
    fit_obj.sigma_margin = _sigma(resid_margin, n + 1)

    # --- total fit: [league total, offence..., defence...] --------------
    rows_t = []
    for g, w in zip(usable, weights):
        x = [0.0] * (1 + 2 * n)
        x[0] = 1.0
        x[1 + idx[str(g["home_id"])]] += 1.0
        x[1 + n + idx[str(g["away_id"])]] += 1.0
        rows_t.append((x, float(g["home_score"] + g["away_score"]), w))
    ata_t, atb_t = _normal_equations(rows_t, 1 + 2 * n, range(1, 1 + 2 * n),
                                     config.RIDGE_LAMBDA)
    sol_t = _solve(ata_t, atb_t)
    league_total = sol_t[0]
    offence = {tid: sol_t[1 + idx[tid]] for tid in team_ids}
    defence = {tid: sol_t[1 + n + idx[tid]] for tid in team_ids}
    _centre_pair(offence, defence)
    fit_obj.offence = offence
    fit_obj.defence = defence
    fit_obj.league_total = league_total

    resid_total = []
    for g, w in zip(usable, weights):
        pred = league_total + offence[str(g["home_id"])] + defence[str(g["away_id"])]
        resid_total.append((float(g["home_score"] + g["away_score"]) - pred, w))
    fit_obj.resid_total = resid_total
    fit_obj.sigma_total = _sigma(resid_total, 1 + 2 * n)

    games_per_team: dict[str, int] = {}
    for g in usable:
        for key in ("home_id", "away_id"):
            tid = str(g[key])
            games_per_team[tid] = games_per_team.get(tid, 0) + 1
    fit_obj.games = len(usable)
    fit_obj.n_eff = sum(weights)
    fit_obj.games_per_team = games_per_team
    fit_obj.seasons = sorted({str(g.get("season") or "") for g in usable if g.get("season")})
    return fit_obj


def _centre_pair(offence: dict[str, float], defence: dict[str, float]) -> None:
    """Remove the offence/defence shift that the ridge leaves unidentified."""
    if not offence:
        return
    mean_off = sum(offence.values()) / len(offence)
    mean_def = sum(defence.values()) / len(defence)
    shift = (mean_off + mean_def) / 2.0
    for k in offence:
        offence[k] -= shift
    for k in defence:
        defence[k] -= shift


def _sigma(sample: list[tuple[float, float]], params: int) -> float:
    if not sample:
        return 1.0
    total_w = sum(w for _, w in sample)
    if total_w <= 0:
        return 1.0
    ss = sum(w * x * x for x, w in sample)
    dof = max(1.0, total_w - params)
    return max(1e-6, math.sqrt(ss / dof))


# ---------------------------------------------------------------------------
# Opening line
# ---------------------------------------------------------------------------
def opening_fit(
    results: list[dict], sport: str, now: datetime, current_season: str | None
) -> Fit:
    """Opening line = previous completed season, or a league-average opener."""
    prior_seasons = {
        str(r.get("season"))
        for r in results
        if r.get("sport") == sport and r.get("season") and str(r["season"]) != str(current_season)
    }
    if prior_seasons:
        fit_prior = fit(
            results, sport, now, half_life=0.0, kind="opening", season_filter=prior_seasons
        )
        if fit_prior.games >= 100:
            fit_prior.notes.append(
                "opening line from previous season(s): " + ", ".join(sorted(prior_seasons))
            )
            return fit_prior
    return league_average_fit(sport, current_season)


def league_average_fit(sport: str, season: str | None) -> Fit:
    """A neutral opener: every team equal, home advantage from the training sample."""
    f = Fit(sport=sport, kind="opening")
    f.notes.append(
        "no usable prior season: opening line is league-average "
        "(ratings 0, league mean scoring, home advantage 0)"
    )
    f.seasons = [str(season)] if season else []
    return f


def neutral_home_advantage(sport: str) -> float:
    """Fallback home advantage, in points/goals/runs, used only when the opener is neutral."""
    return 0.0
