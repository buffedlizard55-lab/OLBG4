"""NBA provider — official data from NBA.com properties.

Primary endpoint (recorded in data/snapshot.json):
  * https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json
    Official full-season schedule, including final scores for completed games and
    each team's wins/losses.

Prior-season history for the ratings model is requested from the official NBA stats
endpoint (stats.nba.com/stats/leaguegamelog). If that endpoint refuses the request the
pipeline continues with current-season games only and records the degradation in
data/snapshot.json — confidence grades then fall automatically because the sample-size
gate is not met.

Published source link for each game: the official games page for that date,
https://www.nba.com/games?date=YYYY-MM-DD. The game-specific URL is included as a
secondary link.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .. import config, http
from ..records import iso, make_game, make_result, parse_iso

SPORT = "basketball"
LEAGUE = "NBA"
SCHEDULE_URL = "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json"
# One official source, documented. If it becomes unavailable the run reports
# provider_unavailable rather than inventing a schedule from an unofficial feed.
SCHEDULE_CANDIDATES = [
    "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json",
]
BROWSER_HEADERS = config.BROWSER_HEADERS
_SCHEDULE_CACHE: dict = {}


def load_schedule() -> dict:
    """Fetch the official season schedule, trying each known official host once."""
    if "payload" in _SCHEDULE_CACHE:
        return _SCHEDULE_CACHE["payload"]
    errors = []
    for url in SCHEDULE_CANDIDATES:
        try:
            payload = http.fetch_json(url, headers=BROWSER_HEADERS, cache_seconds=900)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{url}: {type(exc).__name__}: {exc}")
            continue
        if _looks_like_schedule(payload):
            _SCHEDULE_CACHE["payload"] = payload
            _SCHEDULE_CACHE["url"] = url
            return payload
        errors.append(f"{url}: response was not a schedule")
    raise RuntimeError("no official NBA schedule source available — " + " | ".join(errors))


def _looks_like_schedule(payload: dict) -> bool:
    return bool((payload.get("leagueSchedule") or {}).get("gameDates"))
STATS_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
    "Accept": "application/json, text/plain, */*",
}


REGULAR_SEASON_PREFIX = "002"


def _is_regular_season(game: dict) -> bool:
    """NBA game ids encode the season type: 001 preseason, 002 regular, 004 playoffs."""
    return str(game.get("gameId") or "").startswith(REGULAR_SEASON_PREFIX)


def _iter_games(payload: dict):
    sched = payload.get("leagueSchedule") or {}
    for block in sched.get("gameDates", []):
        for game in block.get("games", []):
            yield game


def _team(game_side: dict) -> dict:
    city = (game_side.get("teamCity") or "").strip()
    name = (game_side.get("teamName") or "").strip()
    return {
        "id": game_side.get("teamId"),
        "name": f"{city} {name}".strip(),
        "abbr": (game_side.get("teamTricode") or "").strip(),
        "wins": game_side.get("wins"),
        "losses": game_side.get("losses"),
        "score": game_side.get("score"),
    }


def _season_games(payload: dict) -> list[dict]:
    """Completed games from the season file, used for ratings and W-L records."""
    out = []
    for g in _iter_games(payload):
        if g.get("gameStatus") != 3 or not _is_regular_season(g):
            continue
        home, away = _team(g.get("homeTeam") or {}), _team(g.get("awayTeam") or {})
        if None in (home["score"], away["score"], home["id"], away["id"]):
            continue
        date = g.get("gameDateTimeUTC") or g.get("gameDateTimeEst")
        if not date:
            continue
        try:
            iso_date = iso(parse_iso(date))
        except Exception:  # noqa: BLE001
            continue
        out.append(
            make_result(
                sport=SPORT,
                game_id=g.get("gameId"),
                date_utc=iso_date,
                home_id=home["id"],
                away_id=away["id"],
                home_score=int(home["score"]),
                away_score=int(away["score"]),
                season=str((payload.get("leagueSchedule") or {}).get("seasonYear") or ""),
                source_url=f"https://www.nba.com/games?date={iso_date[:10]}",
                home_name=home["name"],
                away_name=away["name"],
            )
        )
    return out


def fetch_fixtures(start: datetime, end: datetime, now: datetime) -> tuple[list[dict], list[str]]:
    payload = load_schedule()
    completed = _season_games(payload)
    records: dict[str, dict] = {}
    for r in completed:
        for team_id, won in ((r["home_id"], r["home_score"] > r["away_score"]),
                             (r["away_id"], r["away_score"] > r["home_score"])):
            rec = records.setdefault(str(team_id), {"w": 0, "l": 0})
            rec["w" if won else "l"] += 1

    fixtures: list[dict] = []
    for g in _iter_games(payload):
        if g.get("gameStatus") != 1 or not _is_regular_season(g):
            continue
        date = g.get("gameDateTimeUTC") or g.get("gameDateTimeEst")
        if not date:
            continue
        try:
            start_dt = parse_iso(date)
        except Exception:  # noqa: BLE001
            continue
        if not (start <= start_dt < end):
            continue
        home, away = _team(g.get("homeTeam") or {}), _team(g.get("awayTeam") or {})
        if not home["id"] or not away["id"]:
            continue
        hr = records.get(str(home["id"]), {"w": 0, "l": 0})
        ar = records.get(str(away["id"]), {"w": 0, "l": 0})
        day = start_dt.strftime("%Y-%m-%d")
        game_url = (
            f"https://www.nba.com/game/{away['abbr'].lower()}-vs-{home['abbr'].lower()}-"
            f"{g.get('gameId')}"
        )
        context = {
            "game_type": "regular_season",
            "season": str((payload.get("leagueSchedule") or {}).get("seasonYear") or ""),
            "home_record_label": "Regular-season record",
            "away_record_label": "Regular-season record",
            "home_wins": hr["w"],
            "home_losses": hr["l"],
            "away_wins": ar["w"],
            "away_losses": ar["l"],
        }
        fixtures.append(
            make_game(
                sport=SPORT,
                league=LEAGUE,
                provider="nba",
                game_id=g.get("gameId"),
                start_utc=iso(start_dt),
                home_id=home["id"],
                home_name=home["name"],
                home_abbr=home["abbr"],
                away_id=away["id"],
                away_name=away["name"],
                away_abbr=away["abbr"],
                venue=g.get("arenaName"),
                status=g.get("gameStatusText") or "Scheduled",
                home_record=f"{hr['w']}-{hr['l']}",
                away_record=f"{ar['w']}-{ar['l']}",
                context=context,
                source_urls=[f"https://www.nba.com/games?date={day}", game_url],
            )
        )
    return fixtures, [_SCHEDULE_CACHE.get("url", SCHEDULE_URL)]


def _league_gamelog(season: str) -> list[dict]:
    url = http.with_query(
        "https://stats.nba.com/stats/leaguegamelog",
        Counter=1000,
        Direction="DESC",
        LeagueID="00",
        PlayerOrTeam="T",
        Season=season,
        SeasonType="Regular Season",
        Sorter="DATE",
    )
    payload = http.fetch_json(url, headers=STATS_HEADERS)
    result_sets = payload.get("resultSets") or []
    if not result_sets:
        raise RuntimeError("leaguegamelog returned no resultSets")
    headers = result_sets[0]["headers"]
    idx = {h: i for i, h in enumerate(headers)}
    rows = result_sets[0]["rowSet"]
    games: dict[str, dict] = {}
    for row in rows:
        gid = str(row[idx["GAME_ID"]])
        matchup = str(row[idx["MATCHUP"]])
        team_id = row[idx["TEAM_ID"]]
        pts = row[idx["PTS"]]
        if pts is None:
            continue
        entry = games.setdefault(
            gid,
            {"game_id": gid, "date": row[idx["GAME_DATE"]], "home": None, "away": None,
             "home_name": None, "away_name": None},
        )
        team_name = row[idx["TEAM_NAME"]] if "TEAM_NAME" in idx else None
        if " vs. " in matchup:
            entry["home"] = (team_id, int(pts))
            entry["home_name"] = team_name
        elif " @ " in matchup:
            entry["away"] = (team_id, int(pts))
            entry["away_name"] = team_name
    out = []
    for gid, e in games.items():
        if not e["home"] or not e["away"]:
            continue
        try:
            dt = datetime.strptime(str(e["date"])[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            date_utc = iso(dt)
        except ValueError:
            date_utc = ""
        out.append(
            make_result(
                sport=SPORT,
                game_id=gid,
                date_utc=date_utc,
                home_id=e["home"][0],
                away_id=e["away"][0],
                home_score=e["home"][1],
                away_score=e["away"][1],
                season=season,
                source_url="https://stats.nba.com/stats/leaguegamelog",
                home_name=e.get("home_name"),
                away_name=e.get("away_name"),
            )
        )
    return [r for r in out if r["date_utc"]]


def fetch_training(start: datetime, end: datetime) -> tuple[list[dict], dict]:
    results: list[dict] = []
    notes: list[str] = []

    # Current season, straight from the official schedule file.
    try:
        payload = load_schedule()
        results.extend(_season_games(payload))
    except Exception as exc:  # noqa: BLE001
        notes.append(f"schedule file unavailable: {exc}")

    # Prior season(s), official stats endpoint, used to stabilise early-season ratings.
    current_year = end.year
    for season_start in (current_year - 1,):
        season = f"{season_start}-{str(season_start + 1)[-2:]}"
        try:
            results.extend(_league_gamelog(season))
            notes.append(f"leaguegamelog {season}: loaded")
        except Exception as exc:  # noqa: BLE001
            notes.append(f"leaguegamelog {season}: {type(exc).__name__}")

    # De-duplicate on game id, first occurrence wins.
    seen: set[str] = set()
    unique: list[dict] = []
    for r in results:
        if not r.get("date_utc"):
            continue
        key = str(r["game_id"])
        if key in seen:
            continue
        try:
            dt = parse_iso(r["date_utc"])
        except Exception:  # noqa: BLE001
            continue
        if not (start <= dt < end):
            continue
        seen.add(key)
        unique.append(r)

    provenance = {
        "training_notes": notes,
        "training_games": len(unique),
        "training_sources": [
            SCHEDULE_URL,
            "https://stats.nba.com/stats/leaguegamelog",
        ],
    }
    return unique, provenance
