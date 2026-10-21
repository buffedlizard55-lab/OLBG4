"""Probe which official sport endpoints are reachable from the build runner.

Cloud runners are sometimes refused by league CDNs even when the endpoint is public.
This module records, for a short list of league-owned URLs and header profiles, the HTTP
status, content type and first bytes of the response. The output is committed with the
snapshot (`session-4afef1af/data/probe.json`) so a reviewer can see exactly what the
runner could reach, and so a failing provider can be diagnosed without guessing.

Run:  python -m pipeline.probe
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from . import config

OUT = Path(__file__).resolve().parent.parent / "session-4afef1af" / "data" / "probe.json"

BROWSER = config.BROWSER_HEADERS
NAIVE = {"User-Agent": config.USER_AGENT}

TARGETS = [
    ("https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json", "nba"),
    ("https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json", "nba"),
    ("https://stats.nba.com/stats/scheduleleaguev2?LeagueID=00&Season=2026-27", "nba"),
    ("https://www.nba.com/games?date=2026-10-21", "nba"),
    ("https://api-web.nhle.com/v1/schedule/2026-10-21", "nhl"),
    ("https://statsapi.mlb.com/api/v1/schedule?sportId=1&date=2026-10-21", "mlb"),
]


def probe_one(url: str, headers: dict) -> dict:
    req = urllib.request.Request(url, headers={**headers})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read(400)
            return {
                "status": resp.status,
                "content_type": resp.headers.get("Content-Type"),
                "bytes_sampled": len(body),
                "starts_with": body[:90].decode("utf-8", "replace"),
            }
    except urllib.error.HTTPError as exc:
        return {"status": exc.code, "error": f"HTTPError {exc.code} {exc.reason}"}
    except Exception as exc:  # noqa: BLE001
        return {"status": None, "error": f"{type(exc).__name__}: {exc}"}


def main() -> int:
    results = []
    for url, sport in TARGETS:
        for profile_name, headers in (("browser", BROWSER), ("naive", NAIVE)):
            outcome = probe_one(url, headers)
            results.append({"url": url, "sport": sport, "profile": profile_name, **outcome})
            print(f"{outcome.get('status')}  {profile_name:7s} {url}")
    payload = {
        "probed_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "results": results,
        "note": "Diagnostic only. A 403/000 here means the runner could not reach that "
                "official endpoint; the pipeline then reports the provider as unavailable "
                "instead of substituting an unofficial source.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
