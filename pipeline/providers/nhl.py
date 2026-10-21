"""NHL provider — official data from api-web.nhle.com (National Hockey League).

Endpoints used (recorded in data/snapshot.json):
  * daily schedule:     https://api-web.nhle.com/v1/schedule/<YYYY-MM-DD>
  * club season games:  https://api-web.nhle.com/v1/club-schedule-season/<ABBR>/<SEASON>
  * standings:          https://api-web.nhle.com/v1/standings/now

Per-game source link: the official GameCenter URL returned by the API
(https://www.nhl.com + gameCenterLink).
"""
from __future__ import annotations

from datetime import datetime, timedelta

from .. import http
from ..records import iso, make_game, make_result, parse_iso

SPORT = "ice_hockey"
LEAGUE = "NHL"
BASE = "https://api-web.nhle.com/v1"
REGULAR_SEASON = 2


def _team_name(team: dict) -> str:
    place = (team.get("placeName") or {}).get("default", "")
    common = (team.get("commonName") or {}).get("default", "")
    return f"{place} {common}".strip()


def _game_center_link(game: dict) -> str:
    link = game.get("gameCenterLink")
    if link:
        return "https://www.nhl.com" + link if link.startswith("/") else link
    return f"https://www.nhl.com/gamecenter/{game.get('id')}"


def _standings() -> dict[str, dict]:
    try:
        payload = http.fetch_json(f"{BASE}/standings/now", cache_seconds=1800)
    except Exception:  # noqa: BLE001 - context only
        return {}
    out: dict[str, dict] = {}
    for row in payload.get("standings", []):
        abbr = row.get("teamAbbrev", {}).get("default")
        if not abbr:
            continue
        out[abbr] = {
            "wins": row.get("wins"),
            "losses": row.get("losses"),
            "ot_losses": row.get("otLosses"),
            "points": row.get("points"),
            "record": f"{row.get('wins')}-{row.get('losses')}-{row.get('otLosses')}"
            if row.get("wins") is not None
            else None,
            "points_pct": row.get("pointPctg"),
        }
    return out


def fetch_fixtures(start: datetime, end: datetime, now: datetime) -> tuple[list[dict], list[str]]:
    standings = _standings()
    fixtures: list[dict] = []
    day = start.date()
    end_day = (end - timedelta(seconds=1)).date()
    while day <= end_day:
        payload = http.fetch_json(f"{BASE}/schedule/{day.isoformat()}", cache_seconds=900)
        for block in payload.get("gameWeek", []):
            for g in block.get("games", []):
                if g.get("gameType") != REGULAR_SEASON:
                    continue
                start_dt = parse_iso(g["startTimeUTC"])
                if not (start <= start_dt < end):
                    continue
                home, away = g["homeTeam"], g["awayTeam"]
                home_abbr, away_abbr = home.get("abbrev"), away.get("abbrev")
                home_st, away_st = standings.get(home_abbr, {}), standings.get(away_abbr, {})
                context = {
                    "game_type": g.get("gameType"),
                    "season": str(g.get("season") or ""),
                    "home_record_label": "Record (W-L-OTL)",
                    "away_record_label": "Record (W-L-OTL)",
                    "home_points": home_st.get("points"),
                    "away_points": away_st.get("points"),
                    "home_points_pct": home_st.get("points_pct"),
                    "away_points_pct": away_st.get("points_pct"),
                    "tv": ", ".join(
                        sorted(
                            {
                                b.get("network", "")
                                for b in (g.get("tvBroadcasts") or [])
                                if b.get("network")
                            }
                        )
                    )
                    or None,
                }
                fixtures.append(
                    make_game(
                        sport=SPORT,
                        league=LEAGUE,
                        provider="nhl",
                        game_id=g["id"],
                        start_utc=iso(start_dt),
                        home_id=home.get("id"),
                        home_name=_team_name(home),
                        home_abbr=home_abbr,
                        away_id=away.get("id"),
                        away_name=_team_name(away),
                        away_abbr=away_abbr,
                        venue=(g.get("venue") or {}).get("default"),
                        status=g.get("gameState", "FUT"),
                        home_record=home_st.get("record"),
                        away_record=away_st.get("record"),
                        context=context,
                        source_urls=[
                            _game_center_link(g),
                            f"{BASE}/schedule/{day.isoformat()}",
                        ],
                        extra_sources=[f"https://www.nhl.com/scores/{day.isoformat()}"],
                    )
                )
        day += timedelta(days=1)
    return fixtures, [
        f"{BASE}/schedule/<date> (daily schedule for {start:%Y-%m-%d} .. {end:%Y-%m-%d})",
        f"{BASE}/standings/now",
    ]


def fetch_training(start: datetime, end: datetime) -> tuple[list[dict], dict]:
    """All completed regular-season games for every club in the lookback window."""
    try:
        teams_payload = http.fetch_json(f"{BASE}/standings/now", cache_seconds=3600)
        abbrs = sorted(
            {
                row.get("teamAbbrev", {}).get("default")
                for row in teams_payload.get("standings", [])
                if row.get("teamAbbrev", {}).get("default")
            }
        )
    except Exception:  # noqa: BLE001
        abbrs = []
    seasons = {f"{start.year}{start.year + 1}", f"{end.year}{end.year + 1}"}
    seasons |= {f"{y}{y + 1}" for y in range(start.year, end.year + 1)}
    results: list[dict] = []
    seen: set[str] = set()
    for abbr in abbrs:
        for season in sorted(seasons):
            try:
                payload = http.fetch_json(
                    f"{BASE}/club-schedule-season/{abbr}/{season}", cache_seconds=3600
                )
            except Exception:  # noqa: BLE001 - a club/season may simply not exist
                continue
            for g in payload.get("games", []):
                if g.get("gameType") != REGULAR_SEASON:
                    continue
                if g.get("gameState") not in ("OFF", "FINAL", "Official"):
                    continue
                gid = str(g.get("id"))
                if gid in seen:
                    continue
                try:
                    start_dt = parse_iso(g["startTimeUTC"])
                    home, away = g["homeTeam"], g["awayTeam"]
                    home_score, away_score = home.get("score"), away.get("score")
                    if home_score is None or away_score is None:
                        continue
                    if not (start <= start_dt < end):
                        continue
                    seen.add(gid)
                    results.append(
                        make_result(
                            sport=SPORT,
                            game_id=gid,
                            date_utc=g["startTimeUTC"],
                            home_id=home.get("id"),
                            away_id=away.get("id"),
                            home_score=int(home_score),
                            away_score=int(away_score),
                            season=season,
                            source_url=_game_center_link(g),
                            home_name=_team_name(home),
                            away_name=_team_name(away),
                        )
                    )
                except (KeyError, TypeError, ValueError):
                    continue
    return results, {
        "training_games": len(results),
        "training_sources": [f"{BASE}/club-schedule-season/<ABBR>/<SEASON>", f"{BASE}/standings/now"],
        "training_notes": [] if results else ["no completed games returned"],
    }
