# Source register — build D

Every value on the dashboard is either (a) read from one of the official endpoints below, or
(b) computed by `pipeline/` from those values and labelled as model output. Nothing is hand-entered
and no OLBG price, tip or prediction is copied.

## Official endpoints used

| Endpoint | Sport | What we take | Why it is official |
|---|---|---|---|
| `https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json` | NBA | Full-season schedule, game status, final scores, team win-loss records, arena | `cdn.nba.com` is the NBA's own content delivery host, referenced by NBA.com |
| `https://stats.nba.com/stats/leaguegamelog` | NBA | Prior-season completed games for the opening/current model | `stats.nba.com` is the NBA's official stats service |
| `https://api-web.nhle.com/v1/schedule/<YYYY-MM-DD>` | NHL | Daily schedule, start time in UTC, venue, game state, broadcasters, GameCenter link | `api-web.nhle.com` is the NHL's public API used by NHL.com |
| `https://api-web.nhle.com/v1/club-schedule-season/<ABBR>/<SEASON>` | NHL | Completed regular-season games with final scores | same |
| `https://api-web.nhle.com/v1/standings/now` | NHL | Points, W-L-OTL records, points percentage | same |
| `https://statsapi.mlb.com/api/v1/schedule` | MLB | Schedule, probable pitchers, status, final scores, series context | `statsapi.mlb.com` is MLB's official Stats API |
| `https://statsapi.mlb.com/api/v1/standings` | MLB | Regular-season win-loss records | same |

Per-row source links:

* **NBA** — `https://www.nba.com/games?date=YYYY-MM-DD` (primary, guaranteed valid) and the
  game-specific `https://www.nba.com/game/<away>-vs-<home>-<gameId>` (secondary).
* **NHL** — the GameCenter URL returned by the API (`https://www.nhl.com/gamecenter/…`), plus the
  daily schedule endpoint.
* **MLB** — `https://www.mlb.com/gameday/<gamePk>` and the schedule endpoint for that game.

## What is deliberately not used

| Source | Status | Reason |
|---|---|---|
| OLBG prices, tips, community percentages | **not used as data** | The brief requires our own lines. Copying tipster selections or bookmaker prices would not be origination. |
| OLBG `/api/`, `/sports/`, `/events.php` | **not requested** | Disallowed by `robots.txt`; the pipeline never crawls OLBG. |
| ESPN, SofaScore, FlashScore, odds portals | **not used** | Not league-owned, so a row sourced from them would fail the official-source gate. |
| Bookmaker odds | **not used** | No market comparison is made anywhere in the pipeline. |
| Social media, news reports | **not used** | Not machine-verifiable, and including them risks inventing injuries or team news. |

## Verification performed per run

1. `python -m pipeline.selftest` — offline checks of model, markets, prediction writer, verification
   gate and site builder (runs before any network call in CI).
2. `python -m pipeline.run --strict` — full ingest, then the gate in `docs/methodology.md` §10.
3. Snapshot audit — every HTTP response recorded with status, byte count and SHA-256 in
   `session-4afef1af/data/snapshot.json`, and rendered on the Sources page.
4. Internal link check — the self-test resolves every relative `href` in the generated site.

## Coverage boundary

| Sport | Owner scope | Official machine-readable feed | Ingested |
|---|---|---|---|
| Basketball (NBA) | in | yes — cdn.nba.com | **yes** |
| Ice Hockey (NHL) | in | yes — api-web.nhle.com | **yes** |
| Baseball (MLB) | in | yes — statsapi.mlb.com | **yes** |
| Tennis, Cricket, Rugby Union, Rugby League, Golf, Darts, Snooker, Handball, Volleyball, Greyhounds, Motor Sports, Esports | in | none identified that this pipeline can verify | no |
| Gaelic Football | in | none identified (GAA pages are HTML) | no — listed as in scope, not priced |
| Soccer/Football, American Football, Boxing, UFC/MMA, Hurling, Horse Racing, Cycling, Specials | out | — | no (excluded at ingestion) |

"None identified" is a statement about this pipeline's verified integrations, not a claim that no
such API exists. Those sports are marked *not ingested* on the dashboard rather than filled from an
unofficial feed. Hand-verified builds for several of them exist in the other dashboards in this
repository (see the portal page).

## Reproducing the snapshot

```bash
python -m pipeline.selftest        # offline, no network
python -m pipeline.run --strict    # ingest + verify + build (needs internet)
```
GitHub Actions runs the same two commands every six hours (`.github/workflows/olbg.yml`).
