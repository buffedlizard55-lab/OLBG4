"""Shared fixture/training-game record helpers and validation."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def parse_iso(value: str) -> datetime:
    """Parse the ISO-8601 timestamps used by the three providers."""
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_game(
    *,
    sport: str,
    league: str,
    provider: str,
    game_id: str,
    start_utc: str,
    home_id: str,
    home_name: str,
    home_abbr: str,
    away_id: str,
    away_name: str,
    away_abbr: str,
    venue: str | None,
    source_urls: list[str],
    status: str = "Scheduled",
    home_score: int | None = None,
    away_score: int | None = None,
    home_record: str | None = None,
    away_record: str | None = None,
    context: dict[str, Any] | None = None,
    extra_sources: list[str] | None = None,
) -> dict:
    return {
        "id": f"{provider}-{game_id}",
        "sport": sport,
        "league": league,
        "provider": provider,
        "provider_game_id": str(game_id),
        "start_utc": start_utc,
        "status": status,
        "status_verified_utc": None,  # filled by run.py
        "home": {
            "id": str(home_id),
            "name": home_name,
            "abbr": home_abbr,
            "record": home_record,
            "score": home_score,
        },
        "away": {
            "id": str(away_id),
            "name": away_name,
            "abbr": away_abbr,
            "record": away_record,
            "score": away_score,
        },
        "venue": venue,
        "source_urls": source_urls,
        "extra_sources": extra_sources or [],
        "context": context or {},
    }


def make_result(
    *,
    sport: str,
    game_id: str,
    date_utc: str,
    home_id: str,
    away_id: str,
    home_score: int,
    away_score: int,
    season: str | None = None,
    source_url: str | None = None,
    home_name: str | None = None,
    away_name: str | None = None,
) -> dict:
    """A completed game used only as a model input (never published as a fixture)."""
    return {
        "sport": sport,
        "game_id": str(game_id),
        "date_utc": date_utc,
        "home_id": str(home_id),
        "away_id": str(away_id),
        "home_score": int(home_score),
        "away_score": int(away_score),
        "season": season,
        "source_url": source_url,
        "home_name": home_name,
        "away_name": away_name,
    }


def validate_game(game: dict) -> list[str]:
    """Return a list of problems; empty means the record is structurally sound."""
    problems: list[str] = []
    for key in ("id", "sport", "league", "provider", "start_utc", "home", "away",
                "source_urls", "status"):
        if key not in game:
            problems.append(f"missing field {key}")
    if game.get("sport") not in ("basketball", "ice_hockey", "baseball"):
        problems.append(f"unknown sport {game.get('sport')!r}")
    for side in ("home", "away"):
        team = game.get(side) or {}
        if not team.get("id") or not team.get("name"):
            problems.append(f"{side} team incomplete")
    if not game.get("source_urls"):
        problems.append("no source_urls")
    try:
        parse_iso(game.get("start_utc", ""))
    except Exception:  # noqa: BLE001
        problems.append("start_utc not ISO-8601")
    return problems
