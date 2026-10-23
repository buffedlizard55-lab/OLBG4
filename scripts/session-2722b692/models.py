#!/usr/bin/env python3
"""Board AJ — capture reader and transparent own-line models.

Every probability published by this desk comes from one of the functions below, fed only by
values read out of the committed official capture. No market price is ever copied into a
published probability, and no probability is adjusted to fit a desired confidence label.

Model families (all documented in METHODOLOGY.md and data/session-2722b692/model.json):
  goals_pair()      Poisson goal model for hockey / football-type scoring (regulation time)
  runs_pair()       Poisson run model for baseball
  points_pair()     Normal margin model for basketball / handball / rugby (continuous scoring)
  sets_pair()       Best-of-N set model for volleyball / tennis (set win prob from rating gap)
  race_win()        Field-normalised outright model for motor racing / golf / greyhounds
"""
from __future__ import annotations

import glob
import gzip
import json
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAPTURE_ROOT = ROOT / "data" / "session-2722b692" / "capture"

# Fixed constants of the scoring models. Each is a stated assumption, not a fitted parameter
# chosen to move a pick: they are documented on the methodology page and listed in model.json.
CONST = {
    "nhl_margin_sd": 1.95,
    "nhl_home_goals": 0.16,
    "nhl_total_shrink": 0.88,
    "mlb_run_sd": 3.3,
    "mlb_home_factor": 1.02,
    "basket_margin_sd": 11.5,
    "basket_home_edge": 2.4,
    "handball_margin_sd": 8.0,
    "handball_home_edge": 1.6,
    "rugby_margin_sd": 12.0,
    "rugby_home_edge": 3.0,
    "league_margin_sd": 14.0,
    "league_home_edge": 4.0,
    "volley_set_slope": 0.055,
    "tennis_set_slope": 0.085,
    "tennis_total_games": 21.0,
}


def latest_capture() -> Path:
    dirs = sorted(p for p in CAPTURE_ROOT.glob("*") if (p / "manifest.json").exists())
    if not dirs:
        raise SystemExit("no capture manifest found")
    return dirs[-1]


class Capture:
    def __init__(self, path: Path | None = None):
        self.path = path or latest_capture()
        self.manifest = json.loads((self.path / "manifest.json").read_text())
        self.by_id = {r["id"]: r for r in self.manifest["records"]}

    def raw(self, tid: str) -> bytes | None:
        rec = self.by_id.get(tid)
        if not rec or not rec.get("file"):
            return None
        return gzip.decompress((self.path / rec["file"]).read_bytes())

    def text(self, tid: str) -> str | None:
        raw = self.raw(tid)
        return raw.decode("utf-8", "replace") if raw is not None else None

    def json(self, tid: str):
        raw = self.raw(tid)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def url(self, tid: str) -> str:
        rec = self.by_id.get(tid)
        return (rec or {}).get("url", "")

    def sha(self, tid: str) -> str:
        rec = self.by_id.get(tid)
        return (rec or {}).get("sha256", "")

    def status(self, tid: str) -> int | None:
        rec = self.by_id.get(tid)
        return (rec or {}).get("status")


# --------------------------------------------------------------------------- probability helpers
def poisson_pmf(k: int, mu: float) -> float:
    if mu <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-mu) * mu ** k / math.factorial(k)


def poisson_grid(mu_a: float, mu_b: float, limit: int = 16) -> list[list[float]]:
    pa = [poisson_pmf(i, mu_a) for i in range(limit)]
    pb = [poisson_pmf(i, mu_b) for i in range(limit)]
    total = sum(pa) * sum(pb)
    return [[pa[i] * pb[j] / total for j in range(limit)] for i in range(limit)]


def goals_pair(mu_home: float, mu_away: float, limit: int = 14) -> dict:
    """Regulation-time goal model. Returns home win / draw / away win and the PDO grid."""
    grid = poisson_grid(mu_home, mu_away, limit)
    home = sum(grid[i][j] for i in range(limit) for j in range(limit) if i > j)
    draw = sum(grid[i][i] for i in range(limit))
    away = sum(grid[i][j] for i in range(limit) for j in range(limit) if i < j)
    return {"home": home, "draw": draw, "away": away, "grid": grid,
            "mu_home": mu_home, "mu_away": mu_away}


def runs_pair(mu_home: float, mu_away: float, limit: int = 20) -> dict:
    """Baseball run model (no draws: extra innings resolved inside the same expectation)."""
    grid = poisson_grid(mu_home, mu_away, limit)
    home = sum(grid[i][j] for i in range(limit) for j in range(limit) if i > j)
    away = sum(grid[i][j] for i in range(limit) for j in range(limit) if i < j)
    tie = sum(grid[i][i] for i in range(limit))
    # A tied nine-inning game is decided in extras; assigning those games 50/50 to the two
    # sides is the stated convention, not a team-specific edge.
    return {"home": home + 0.5 * tie, "away": away + 0.5 * tie, "tie": tie,
            "grid": grid, "mu_home": mu_home, "mu_away": mu_away}


def normal_cdf(x: float, mu: float = 0.0, sd: float = 1.0) -> float:
    return 0.5 * (1.0 + math.erf((x - mu) / (sd * math.sqrt(2.0))))


def points_pair(margin: float, sd: float, total: float) -> dict:
    """Continuous-scoring model: margin ~ Normal(margin, sd). Used for basketball/handball/rugby."""
    p_home = normal_cdf(0.0, -margin, sd)  # P(home margin > 0)
    return {"home": p_home, "away": 1.0 - p_home, "margin": margin, "sd": sd, "total": total,
            "p_home_by": {k: 1.0 - normal_cdf(k - 0.5, margin, sd) for k in (1, 2, 3, 6, 7, 10)},
            "p_over": lambda line: 1.0 - normal_cdf(line, total, sd * 1.35)}


def logistic(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def set_match_prob(p_set: float, best_of: int) -> float:
    """Probability of winning a best-of-N set match given an independent set win probability."""
    need = best_of // 2 + 1
    total = 0.0
    for losses in range(need):
        # match ends as soon as `need` sets are won; count orders with exactly `losses` losses
        ways = math.comb(need + losses - 1, losses)
        total += ways * (p_set ** need) * ((1 - p_set) ** losses)
    return total


def sets_pair(rating_gap: float, best_of: int = 5, slope: float = 0.055) -> dict:
    p_set = logistic(slope * rating_gap)
    return {"p_set": p_set, "home": set_match_prob(p_set, best_of),
            "away": 1.0 - set_match_prob(p_set, best_of)}


def shrink(rate: float, sample: int, k: float, prior: float) -> float:
    """Empirical-Bayes shrinkage of a per-game rate toward the league prior.

    weight = sample / (sample + k). With few official games the estimate stays close to the
    league average, which keeps an early-season mismatch from producing a false 90% pick.
    """
    if sample <= 0:
        return prior
    w = sample / (sample + k)
    return w * rate + (1 - w) * prior


def p_win_by(p_set: float, best_of: int, margin: int) -> float:
    """Exact P(A wins the match by at least `margin` sets) for independent set outcomes.

    A wins the match at score (need, b) with b < need; the ways to reach that score with the
    last set going to A are C(need+b-1, b), and the set margin is need-b.
    """
    need = best_of // 2 + 1
    total = 0.0
    for b in range(0, need):
        if need - b < margin:
            continue
        ways = math.comb(need + b - 1, b)
        total += ways * (p_set ** need) * ((1 - p_set) ** b)
    return min(total, 1.0)


def sets_handicap(p_set: float, best_of: int, line: float) -> float:
    """P(home covers a set handicap). line=-1.5 means home must win by two or more sets."""
    margin = int(abs(line)) + (1 if abs(line) % 1 else 0)
    if line < 0:
        return p_win_by(p_set, best_of, margin)
    return 1.0 - p_win_by(1 - p_set, best_of, margin)


def race_win(strengths: list[float]) -> list[float]:
    """Normalise positive strength scores into a win-probability distribution."""
    s = sum(strengths)
    return [x / s for x in strengths] if s > 0 else [1 / len(strengths)] * len(strengths)


# --------------------------------------------------------------------------- price maths
def american_from_prob(p: float) -> tuple[str, float]:
    """Fair American price and fair decimal price for a probability (no margin)."""
    if p <= 0 or p >= 1:
        return "", 0.0
    dec = 1.0 / p
    if p >= 0.5:
        am = -100.0 * p / (1.0 - p)
    else:
        am = 100.0 * (1.0 - p) / p
    am_s = f"{int(round(am)):+d}" if am > 0 else f"{int(round(am))}"
    return am_s, round(dec, 3)


def implied_from_american(american: str) -> float:
    try:
        a = int(str(american).replace("+", ""))
    except (TypeError, ValueError):
        return 0.0
    if a == 0:
        return 0.0
    return 100.0 / (a + 100.0) if a > 0 else -a / (-a + 100.0)


def in_odds_window(american: str) -> bool:
    """The brief's window: -250 (inclusive) to +10,000 (inclusive)."""
    try:
        a = int(str(american).replace("+", ""))
    except (TypeError, ValueError):
        return False
    return -250 <= a <= 10000


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def parse_iso(value: str) -> datetime | None:
    if not value:
        return None
    v = value.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(v)
    except ValueError:
        try:
            dt = datetime.strptime(v[:19], "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
