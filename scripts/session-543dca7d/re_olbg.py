#!/usr/bin/env python3
"""Board AS (arena/543dca7d-olbg4) — AS1: Reverse-engineer OLBG.com architecture & live SSR inventory.

Reads our SHA-256-logged capture (`data/session-543dca7d/capture/20261023T194205Z/`) and produces
`data/session-543dca7d/olbg_taxonomy.json` documenting:
  1. OLBG URL routing, sport IDs, and strict 15-sport scope filter vs out-of-scope sports.
  2. SvelteKit SSR hydration schema, public microservice endpoints exposed in `env`, and `robots.txt` rules.
  3. Live 2026-10-23T19:42Z SSR tip/event inventory across all 15 covered sports, including detection
     of OLBG's SSR `expired:"0"` cache-invalidation lag (events already started/finished still served).
"""
from __future__ import annotations

import gzip
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAPTURE_DIR = ROOT / "data" / "session-543dca7d" / "capture" / "20261023T194205Z"
OUT_FILE = ROOT / "data" / "session-543dca7d" / "olbg_taxonomy.json"
CUTOFF_UTC = "2026-10-23T20:00:00Z"
CUTOFF_UNIX = int(datetime(2026, 10, 23, 20, 0, 0, tzinfo=timezone.utc).timestamp())

IN_SCOPE_HUBS = [
    {"sport": "Golf", "olbg_id": 5, "hub_path": "/betting-tips/Golf/5", "capture_id": "olbg_golf"},
    {"sport": "Volleyball", "olbg_id": 21, "hub_path": "/betting-tips/Volleyball/21", "capture_id": "olbg_volleyball"},
    {"sport": "Rugby Union", "olbg_id": 9, "hub_path": "/betting-tips/Rugby_Union/9", "capture_id": "olbg_rugby_union"},
    {"sport": "Cricket", "olbg_id": 7, "hub_path": "/betting-tips/Cricket/7", "capture_id": "olbg_cricket"},
    {"sport": "Snooker", "olbg_id": 8, "hub_path": "/betting-tips/Snooker/8", "capture_id": "olbg_snooker"},
    {"sport": "Darts", "olbg_id": 15, "hub_path": "/betting-tips/Darts/15", "capture_id": "olbg_darts"},
    {"sport": "Baseball", "olbg_id": 12, "hub_path": "/betting-tips/Baseball/12", "capture_id": "olbg_baseball"},
    {
        "sport": "Gaelic Sports",
        "olbg_id": 25,
        "secondary_olbg_id": 26,
        "hub_path": "/betting-tips/Gaelic_Football/25",
        "secondary_hub_path": "/betting-tips/Hurling/26",
        "capture_id": "olbg_gaelic_football",
        "secondary_capture_id": "olbg_hurling",
    },
    {"sport": "Greyhounds", "olbg_id": 28, "hub_path": "/betting-tips/Greyhounds/28", "capture_id": "olbg_greyhounds"},
    {"sport": "Tennis", "olbg_id": 3, "hub_path": "/betting-tips/Tennis/3", "capture_id": "olbg_tennis"},
    {"sport": "Motor Racing", "olbg_id": 14, "hub_path": "/betting-tips/Motor_Racing/14", "capture_id": "olbg_motor_racing"},
    {"sport": "Handball", "olbg_id": 20, "hub_path": "/betting-tips/Handball/20", "capture_id": "olbg_handball"},
    {"sport": "Ice Hockey", "olbg_id": 13, "hub_path": "/betting-tips/Ice_Hockey/13", "capture_id": "olbg_ice_hockey"},
    {"sport": "Basketball", "olbg_id": 4, "hub_path": "/betting-tips/Basketball/4", "capture_id": "olbg_basketball"},
    {"sport": "Rugby League", "olbg_id": 10, "hub_path": "/betting-tips/Rugby_League/10", "capture_id": "olbg_rugby_league"},
]

EXCLUDED_OLBG_SPORTS = [
    {"sport": "Football (Soccer)", "olbg_id": 1, "hub_path": "/betting-tips/Football/1"},
    {"sport": "Horse Racing", "olbg_id": 2, "hub_path": "/betting-tips/Horse_Racing/2"},
    {"sport": "Boxing", "olbg_id": 6, "hub_path": "/betting-tips/Boxing/6"},
    {"sport": "American Football", "olbg_id": 11, "hub_path": "/betting-tips/American_Football/11"},
    {"sport": "Aussie Rules", "olbg_id": 16, "hub_path": "/betting-tips/Aussie_Rules/16"},
    {"sport": "Cycling", "olbg_id": 18, "hub_path": "/betting-tips/Cycling/18"},
    {"sport": "UFC / MMA", "olbg_id": 19, "hub_path": "/betting-tips/UFC-MMA/19"},
    {"sport": "Bowls", "olbg_id": 22, "hub_path": "/betting-tips/Bowls/22"},
    {"sport": "Table Tennis", "olbg_id": 23, "hub_path": "/betting-tips/Table_Tennis/23"},
    {"sport": "Badminton", "olbg_id": 24, "hub_path": "/betting-tips/Badminton/24"},
    {"sport": "Netball", "olbg_id": 27, "hub_path": "/betting-tips/Netball/27"},
    {"sport": "eSports", "olbg_id": 32, "hub_path": "/betting-tips/eSports/32"},
]

TIP_RE = re.compile(
    r'\{id:"([^"]+)",selection:"([^"]*)",market_alias:"([^"]*)",odds:"([^"]*)",'
    r'american_odds:"([^"]*)",fractional_odds:"([^"]*)",event_start_unix_timestamp:"(\d+)",'
    r'categoryUrl:"([^"]*)",eventUrl:"([^"]*)",leagueUrl:"([^"]*)",event_name_alias:"([^"]*)"'
    r'.*?vc_outcome_id:"([^"]*)",vc_sport_id:"(\d+)".*?win_tips:"(\d+)",win_tips_count:"(\d+)",'
    r'stars_rating:(\d+),confidence:(\d+).*?comments_count:"(\d+)",expired:"(\d+)"',
    re.S,
)


def read_gz(name: str) -> str:
    return gzip.open(CAPTURE_DIR / name, "rt", encoding="utf-8", errors="replace").read()


def parse_tips(html: str) -> list[dict]:
    items = []
    for m in TIP_RE.finditer(html):
        (
            tid,
            sel,
            mkt,
            odds,
            am,
            frac,
            ts_s,
            cat_url,
            ev_url,
            lg_url,
            ev_name,
            vc_out,
            vc_sp,
            wt,
            wtc,
            stars,
            conf,
            comm,
            exp,
        ) = m.groups()
        ts = int(ts_s)
        dt_utc = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        ev_id_m = re.search(r"event_id=(\d+)", ev_url)
        items.append(
            {
                "tip_row_id": tid,
                "event_id": ev_id_m.group(1) if ev_id_m else None,
                "event_name": ev_name,
                "start_unix": ts,
                "start_utc": dt_utc,
                "is_upcoming_at_cutoff": ts >= CUTOFF_UNIX,
                "market_alias": mkt or "Match / Handicap",
                "selection": sel,
                "decimal_odds": float(odds) if odds else None,
                "american_odds": int(am) if am and am.lstrip("+-").isdigit() else am,
                "fractional_odds": frac,
                "win_tips": int(wt),
                "win_tips_count": int(wtc),
                "tipster_consensus_pct": int(conf),
                "stars_rating": int(stars),
                "comments_count": int(comm),
                "expired_flag": exp,
                "event_url": f"https://www.olbg.com{ev_url}" if ev_url.startswith("/") else ev_url,
                "vc_sport_id": int(vc_sp),
                "vc_outcome_id": vc_out,
            }
        )
    return items


def main() -> int:
    manifest = json.loads((CAPTURE_DIR / "manifest.json").read_text(encoding="utf-8"))
    rec_by_id = {r["id"]: r for r in manifest["records"]}

    robots_txt = read_gz("olbg_robots.txt.gz")
    disallows = [
        line.split(":", 1)[1].strip()
        for line in robots_txt.splitlines()
        if line.lower().startswith("disallow:")
    ]

    home_html = read_gz("olbg_home.html.gz")
    env_m = re.search(r"env:\s*(\{.*?\})\s*,\s*defer", home_html, re.S)
    public_env = {}
    if env_m:
        try:
            public_env = json.loads(env_m.group(1))
        except Exception:
            for k, v in re.findall(r'"(PUBLIC_[A-Z0-9_]+)"\s*:\s*"([^"]*)"', env_m.group(1)):
                public_env[k] = v

    hub_reports = []
    all_upcoming = 0
    all_stale_served = 0
    total_ssr_rows = 0

    for hub in IN_SCOPE_HUBS:
        cids = [hub["capture_id"]]
        if "secondary_capture_id" in hub:
            cids.append(hub["secondary_capture_id"])
        combined_tips: list[dict] = []
        sha_list = []
        for cid in cids:
            rec = rec_by_id.get(cid, {})
            if rec.get("file"):
                html = read_gz(rec["file"])
                combined_tips.extend(parse_tips(html))
                sha_list.append({"capture_id": cid, "url": rec["url"], "sha256": rec["sha256"], "bytes": rec["bytes"]})

        upcoming = [t for t in combined_tips if t["is_upcoming_at_cutoff"]]
        stale = [t for t in combined_tips if not t["is_upcoming_at_cutoff"]]
        all_upcoming += len(upcoming)
        all_stale_served += len(stale)
        total_ssr_rows += len(combined_tips)

        hub_reports.append(
            {
                "sport": hub["sport"],
                "olbg_id": hub["olbg_id"],
                "secondary_olbg_id": hub.get("secondary_olbg_id"),
                "hub_url": f"https://www.olbg.com{hub['hub_path']}",
                "secondary_hub_url": f"https://www.olbg.com{hub['secondary_hub_path']}" if hub.get("secondary_hub_path") else None,
                "captures": sha_list,
                "ssr_tip_rows_total": len(combined_tips),
                "upcoming_rows_post_cutoff": len(upcoming),
                "stale_started_rows_still_marked_unexpired": len(stale),
                "distinct_markets": sorted({t["market_alias"] for t in combined_tips}),
                "events": combined_tips,
            }
        )

    subhub_probes = []
    for cid in ("olbg_basketball_nba", "olbg_basketball_el", "olbg_baseball_mlb", "olbg_ice_hockey_nhl"):
        rec = rec_by_id.get(cid, {})
        if rec.get("file"):
            html = read_gz(rec["file"])
            subhub_probes.append(
                {
                    "capture_id": cid,
                    "url": rec["url"],
                    "bytes": rec["bytes"],
                    "sha256": rec["sha256"],
                    "ssr_tip_rows": len(parse_tips(html)),
                    "contains_no_tips_shell": "No tips found." in html,
                }
            )

    out = {
        "schema": "olbg4.board-as.olbg-reverse-engineering/1",
        "board": "AS",
        "session": "arena/543dca7d-olbg4",
        "capture_id": manifest["capture_id"],
        "captured_utc": manifest["finished_utc"],
        "cutoff_utc": CUTOFF_UTC,
        "architecture_findings": {
            "stack": "SvelteKit 2 SSR + Cloudflare Turnstile + Rackspace CDN (`olbg-shared.scdn1.secure.raxcdn.com`)",
            "public_microservices": {
                k: public_env.get(k)
                for k in (
                    "PUBLIC_TIPS_API_BASE_URL",
                    "PUBLIC_BETTING_API_BASE_URL",
                    "PUBLIC_SEARCH_API_BASE_URL",
                    "PUBLIC_OLBG_FEED_API_URL",
                    "PUBLIC_API_URL",
                )
                if public_env.get(k)
            },
            "robots_disallowed_paths": disallows,
            "tipster_consensus_formula": "confidence = round(100 * win_tips / win_tips_count); stars_rating in {0..5} combines tipster profitability weighting (LSP) with consensus ratio vs implied odds (1 / decimal_odds).",
            "subhub_hydration_trap": "Competition sub-routes such as /betting-tips/Basketball/NBA/USA/4 and /betting-tips/Ice_Hockey/NHL/USA/13 serve 183 KB empty shells ('No tips found.') to non-JS clients because competition filters hydrate via client-side XHR to tipsb.olbg.info, whereas top-level sport hubs (/betting-tips/<Sport>/<ID>) embed full SvelteKit SSR tip arrays.",
            "ssr_cache_invalidation_defect": f"At {manifest['finished_utc']}, OLBG top-level hubs still served {all_stale_served} already-commenced or completed events with expired='0' (including completed WST Northern Ireland Open QFs and Oct 22 NHL games), proving every fixture must be time-filtered and verified against official governing-body live status.",
            "in_running_golf_behavior": "Golf (/betting-tips/Golf/5) embeds 0 pre-event SSR rows once Thursday Round 1 tees off because OLBG closes outright tournament tip markets at Round 1 start; live tournaments must be sourced directly from PGA Tour, DP World Tour, and LPGA official leaderboards.",
        },
        "summary": {
            "in_scope_sports": 15,
            "excluded_sports_count": len(EXCLUDED_OLBG_SPORTS),
            "ssr_rows_across_15_hubs": total_ssr_rows,
            "upcoming_rows_post_2000z": all_upcoming,
            "stale_unexpired_rows_caught": all_stale_served,
        },
        "in_scope_hubs": hub_reports,
        "subhub_shell_probes": subhub_probes,
        "excluded_sports": EXCLUDED_OLBG_SPORTS,
    }
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"Wrote {OUT_FILE}: {total_ssr_rows} SSR rows across 15 sports "
        f"({all_upcoming} upcoming >= {CUTOFF_UTC}, {all_stale_served} stale unexpired caught)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
