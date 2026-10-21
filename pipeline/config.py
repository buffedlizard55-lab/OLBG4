"""Central configuration: scope, sports registry, provenance rules.

All values here are policy, not data. Data is always fetched at build time from the
official league endpoints listed in `PROVIDERS` and recorded in data/snapshot.json.
"""
from __future__ import annotations

import os
from datetime import timedelta, timezone, datetime

# ---------------------------------------------------------------------------
# Scope
# ---------------------------------------------------------------------------
# The owner excluded these OLBG sports from the deliverable. "football" in OLBG's
# taxonomy means association football (soccer); the owner listed it explicitly along
# with "soccer", "american football", hurling, horse racing, cycling, boxing, UFC/MMA
# and "specials". Gaelic football is treated as out of scope because the owner
# excluded "football" and "hurling" (both GAA codes are football/hurling family).
EXCLUDED_SPORTS = [
    "Soccer",
    "Football (association)",
    "American Football (NFL / NCAA)",
    "Boxing",
    "UFC",
    "MMA",
    "Hurling",
    "Gaelic Football",
    "Horse Racing",
    "Cycling",
    "Specials",
]

# Sports we ingest. Only sports with an official, machine-readable league feed are
# eligible; see docs/sources.md for the evaluation of every OLBG sport.
SPORTS = {
    "basketball": {
        "label": "Basketball",
        "league": "NBA",
        "provider": "nba",
        "official_domains": ["nba.com", "www.nba.com", "cdn.nba.com", "stats.nba.com"],
        "home_advantage_in_model": True,
        "scoring_unit": "points",
    },
    "ice_hockey": {
        "label": "Ice Hockey",
        "league": "NHL",
        "provider": "nhl",
        "official_domains": ["nhl.com", "www.nhl.com", "api-web.nhle.com", "api.nhle.com"],
        "home_advantage_in_model": True,
        "scoring_unit": "goals",
    },
    "baseball": {
        "label": "Baseball",
        "league": "MLB",
        "provider": "mlb",
        "official_domains": ["mlb.com", "www.mlb.com", "statsapi.mlb.com"],
        "home_advantage_in_model": True,
        "scoring_unit": "runs",
    },
}

# ---------------------------------------------------------------------------
# Coverage window
# ---------------------------------------------------------------------------
# Fixtures are published for a rolling window. Default 7 days; overridable for tests.
WINDOW_DAYS = int(os.environ.get("OLBG_WINDOW_DAYS", "7"))

# Training lookback: how far back to pull completed games for ratings.
TRAINING_LOOKBACK_DAYS = {
    "basketball": 420,
    "ice_hockey": 420,
    "baseball": 240,
}

# ---------------------------------------------------------------------------
# Book-building parameters (documented in docs/methodology.md)
# ---------------------------------------------------------------------------
RIDGE_LAMBDA = 6.0          # shrinkage on team ratings, in squared scoring units per game
THEORETICAL_HOLD = 0.045    # 4.5% overround across both sides of a market
MIN_GAMES_FOR_HIGH = 40     # per-team games in the training sample
MIN_GAMES_FOR_MEDIUM = 20

# Confidence rule (must stay in sync with pipeline/predictions.py and the docs)
CONFIDENCE = {
    "high": {"min_prob": 0.60, "min_z": 2.0, "min_games": MIN_GAMES_FOR_HIGH},
    "medium": {"min_prob": 0.55, "min_z": 1.0, "min_games": MIN_GAMES_FOR_MEDIUM},
}

USER_AGENT = (
    "Mozilla/5.0 (compatible; OLBG4-research-pipeline/1.0; "
    "+https://github.com/buffedlizard55-lab/OLBG4)"
)

# ---------------------------------------------------------------------------
# Provenance rules enforced by pipeline/verify.py
# ---------------------------------------------------------------------------
# A fixture row may only be published if at least one of its source URLs is on the
# official domain list for its sport. Anything else is dropped and flagged.
REQUIRE_OFFICIAL_SOURCE = True

HTTP_TIMEOUT = 25
HTTP_RETRIES = 2
CACHE_DIR = os.environ.get("OLBG_CACHE_DIR", ".cache/http")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def window(now: datetime | None = None) -> tuple[datetime, datetime]:
    """Publishing window: start of today (UTC) through WINDOW_DAYS later."""
    now = now or utc_now()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=WINDOW_DAYS)


def training_start(sport: str, now: datetime | None = None) -> datetime:
    now = now or utc_now()
    return (now - timedelta(days=TRAINING_LOOKBACK_DAYS[sport])).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
