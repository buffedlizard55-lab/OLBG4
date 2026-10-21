"""MLB provider — official data from statsapi.mlb.com (Major League Baseball).

Endpoints used (recorded in data/snapshot.json):
  * schedule:  https://statsapi.mlb.com/api/v1/schedule
  * standings: https://statsapi.mlb.com/api/v1/standings

The published per-game source link is the official MLB Gameday page,
https://www.mlb.com/gameday/<gamePk>, which is derived from the `gamePk` that the
schedule endpoint returns.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta

from .. import http
from ..records import iso, make_game, make_result, parse_iso

SPORT = "baseball"
LEAGUE = "MLB"
BASE = "https://statsapi.mlb.com/api/v1"
# Regular season + postseason; spring training (S) and exhibition (E) are excluded.
GAME_TYPES = "R,F,D,L,W"


def _schedule(start: datetime, end: datetime, hydrate: str = "probablePitcher") -> dict:
    url = http.with_query(
        f"{BASE}/schedule",
        sportId=1,
        startDate=start.strftime("%Y-%m-%d"),
        endDate=end.strftime("%Y-%m-%d"),
        gameType=GAME_TYPES,
        hydrate=hydrate,
        fields=(
            "dates,date,games,gamePk,gameDate,gameType,season,status,detailedState,"
            "teams,home,away,team,id,name,score,probablePitcher,fullName,venue,"
            "doubleHeader,gameNumber,seriesStatus,description,seriesGameNumber,gamesInSeries"
        ),
    )
    return http.fetch_json(url, cache_seconds=900)


def _team_records(season: int) -> dict[int, str]:
    """Official regular-season W-L by team id, from the standings endpoint."""
    try:
        # No `fields` filter here: the standings payload is small, and a rejected filter
        # would silently cost every MLB row its official record.
        payload = http.fetch_json(
            http.with_query(
                f"{BASE}/standings",
                leagueId="103,104",
                season=season,
                standingsTypes="regularSeason",
            ),
            cache_seconds=3600,
        )
    except Exception:  # noqa: BLE001 - records are context only, never a model input
        return {}
    out: dict[int, str] = {}
    for block in payload.get("records", []):
        for rec in block.get("teamRecords", []):
            try:
                tid = rec["team"]["id"]
                lr = rec.get("leagueRecord") or {}
                wins, losses = lr.get("wins"), lr.get("losses")
                if wins is not None and losses is not None:
                    out[tid] = f"{wins}-{losses}"
            except (KeyError, TypeError):
                continue
    return out


def fetch_fixtures(start: datetime, end: datetime, now: datetime) -> tuple[list[dict], list[str]]:
    payload = _schedule(start, end)
    season = max([d.get("season") for d in payload.get("dates", []) if d.get("season")] or [start.year])
    records = _team_records(season)
    fixtures: list[dict] = []
    for block in payload.get("dates", []):
        for g in block.get("games", []):
            if not g.get("gamePk"):
                continue
            status = (g.get("status") or {}).get("detailedState", "Unknown")
            if (g.get("status") or {}).get("abstractGameState") not in (None, "Preview"):
                continue
            start_dt = parse_iso(g["gameDate"])
            if not (start <= start_dt < end):
                continue
            home, away = g["teams"]["home"], g["teams"]["away"]
            home_id, away_id = home["team"]["id"], away["team"]["id"]
            context = {
                "game_type": g.get("gameType"),
                "season": str(g.get("season") or ""),
                "home_record_label": "Regular-season record",
                "away_record_label": "Regular-season record",
                "series": (g.get("seriesStatus") or {}).get("description") or g.get("description"),
                "series_game_number": g.get("seriesGameNumber"),
                "games_in_series": g.get("gamesInSeries"),
                "double_header": g.get("doubleHeader") not in (None, "N"),
                "game_number": g.get("gameNumber"),
                "home_probable_pitcher": (home.get("probablePitcher") or {}).get("fullName"),
                "away_probable_pitcher": (away.get("probablePitcher") or {}).get("fullName"),
            }
            fixtures.append(
                make_game(
                    sport=SPORT,
                    league=LEAGUE,
                    provider="mlb",
                    game_id=g["gamePk"],
                    start_utc=iso(start_dt),
                    home_id=home_id,
                    home_name=home["team"].get("name", ""),
                    home_abbr=_abbr(home["team"].get("name", "")),
                    away_id=away_id,
                    away_name=away["team"].get("name", ""),
                    away_abbr=_abbr(away["team"].get("name", "")),
                    venue=(g.get("venue") or {}).get("name"),
                    status=status,
                    home_record=records.get(home_id),
                    away_record=records.get(away_id),
                    context=context,
                    source_urls=[
                        f"https://www.mlb.com/gameday/{g['gamePk']}",
                        f"{BASE}/schedule?sportId=1&gamePk={g['gamePk']}",
                    ],
                )
            )
    return fixtures, [
        f"{BASE}/schedule (startDate={start:%Y-%m-%d}&endDate={end:%Y-%m-%d}&gameType={GAME_TYPES})",
        f"{BASE}/standings (season={season})",
    ]


def fetch_training(start: datetime, end: datetime) -> tuple[list[dict], dict]:
    """Completed games with final scores, used only to fit the ratings model."""
    results: list[dict] = []
    deadline = time.monotonic() + 240
    cursor = start
    while cursor < end:
        if time.monotonic() > deadline:
            break
        chunk_end = min(cursor + timedelta(days=45), end)
        payload = _schedule(cursor, chunk_end, hydrate="probablePitcher")
        for block in payload.get("dates", []):
            for g in block.get("games", []):
                state = (g.get("status") or {}).get("abstractGameState")
                if state != "Final":
                    continue
                try:
                    home, away = g["teams"]["home"], g["teams"]["away"]
                    results.append(
                        make_result(
                            sport=SPORT,
                            game_id=g["gamePk"],
                            date_utc=g["gameDate"],
                            home_id=home["team"]["id"],
                            away_id=away["team"]["id"],
                            home_score=int(home["score"]),
                            away_score=int(away["score"]),
                            season=str(g.get("season") or ""),
                            source_url=f"https://www.mlb.com/gameday/{g['gamePk']}",
                            home_name=home["team"].get("name"),
                            away_name=away["team"].get("name"),
                        )
                    )
                except (KeyError, TypeError, ValueError):
                    continue
        cursor = chunk_end + timedelta(days=1)
    return results, {
        "training_games": len(results),
        "training_sources": [f"{BASE}/schedule (gameType={GAME_TYPES})"],
        "training_notes": [],
    }


_ABBR = {
    "Arizona Diamondbacks": "ARI", "Athletics": "ATH", "Atlanta Braves": "ATL",
    "Baltimore Orioles": "BAL", "Boston Red Sox": "BOS", "Chicago Cubs": "CHC",
    "Chicago White Sox": "CWS", "Cincinnati Reds": "CIN", "Cleveland Guardians": "CLE",
    "Colorado Rockies": "COL", "Detroit Tigers": "DET", "Houston Astros": "HOU",
    "Kansas City Royals": "KC", "Los Angeles Angels": "LAA", "Los Angeles Dodgers": "LAD",
    "Miami Marlins": "MIA", "Milwaukee Brewers": "MIL", "Minnesota Twins": "MIN",
    "New York Mets": "NYM", "New York Yankees": "NYY", "Philadelphia Phillies": "PHI",
    "Pittsburgh Pirates": "PIT", "San Diego Padres": "SD", "San Francisco Giants": "SF",
    "Seattle Mariners": "SEA", "St. Louis Cardinals": "STL", "Tampa Bay Rays": "TB",
    "Texas Rangers": "TEX", "Toronto Blue Jays": "TOR", "Washington Nationals": "WSH",
}


def _abbr(name: str) -> str:
    return _ABBR.get(name, "".join(w[0] for w in name.replace(".", "").split())[:3].upper())
