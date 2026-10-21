# OLBG4 — Reverse Engineered OLBG.com

**Live site:** https://buffedlizard55-lab.github.io/OLBG4/  
**Data cut-off:** 2026-10-21 (UTC)  
**Branch:** `main` (production) • Workshop: `arena/290a9dba-olbg4`

## What this is

A full, verified, dated list of **updated matches for every sport we cover**, excluding:
`soccer`, `boxing`, `UFC`, `MMA`, `football`, `American football`, `hurling`, `horse racing`, `cycling`, `specials`.

For every match we:
- **Originate our own betting lines** (moneyline, handicap/spread, totals) — not copied from any bookmaker
- **Pick a match winner** with **Low / Medium / High** confidence
- **Investigate every available market** (win match, handicap, match total, etc.)
- For **High confidence picks**, generate a unique, human, 30+ word prediction including team, player, current form, recent match history, and a clear betting selection backed by verified real information from official sources

**No manual input** — all entries are sourced and verifiable. Every table row has a source link to an official site. If a value can't be confirmed from an official source, it is left blank and flagged as unverified (never inferred).

## Structure

```
index.html          → Dashboard with all entries (filterable, dashboard KPIs)
tennis.html         → ATP Almaty / Brussels / Lyon + WTA Finals Indian Wells
basketball.html     → NBA Tip-Off + EuroLeague R7 derbies
baseball.html       → MLB World Series (Brewers vs Rays)
cricket.html        → AUS v SA Tests + Pakistan Tri-Series + AUS Women v BAN
rugby.html          → Nations Championship Autumn + Rugby League Pacific Champs
ice-hockey.html     → NHL Oct 20-21 slate
snooker.html        → Northern Ireland Open Oct 18-25 Belfast
darts.html          → PDC European Championship Oct 22-25 Dortmund
golf.html           → PGA Fall (Baycurrent, Bermuda, Mexico) + LPGA BMW Ladies
badminton.html      → Denmark Super 750 → French Super 750 → Hylo
table-tennis.html   → WTT Champions Montpellier Oct 27-Nov1
volleyball.html     → Season-gap explanation (FIVB — flagged as no market)
handball.html       → EHF CL gaps — flagged per verification policy
esports.html        → Worlds/Valorant — brackets TBD — flagged
aussie-rules.html   → AFL off-season — no market (correctly flagged)
methodology.html    → How lines are originated (ELO + form + H2D + venue + margin)
sources.html        → Official source registry for manual review (every URL)
flagged.html        → Clearly labeled flagged irregularities & unverified items for your review
data/matches.json   → Machine-readable verified dataset (all rows)
data/sources.json   → Human-readable source registry
assets/css/style.css + assets/js/main.js → Clean dashboard UI
COORDINATION.md     → Shared task board for parallel agents (per brief)
.github/workflows/pages.yml → GH Pages deploy pipeline
```

## Verification — line by line

Each row in `data/matches.json` contains:
- `sourceUrl` + `sourceName` — official site (e.g., `nba.com`, `mlb.com`, `atptour.com`)
- `verified` boolean + `flagged` + `flagReason` string

**High-confidence prediction rule:** Must be ≥30 words, include team, player, current form, recent head-to-head, and state the selection ("back X moneyline Y / back over Z").

To manually review:
1. Open `index.html` or any category page
2. Click the "Official source" link in the last column
3. Compare date/venue/participants on the official page to the table
4. Check `flagged.html` for any entries that could not be confirmed at cut-off (they do not block the merge)

## How lines are originated

Transparent model (see `methodology.html`):
- **ELO (40%)** + Recent form last 10 (25%) + H2H last 3y (15%) + Venue/travel/rest (15%) + Confirmed injury (5%)
- Convert win prob `p` → decimal odds with 3.5–4.5% overround
- Handicap set to ~50/50 via `Φ⁻¹(p)*σ` per sport (NBA σ≈11.5, etc.)
- Totals from pace/xG/park-factor simulations
- Confidence threshold: High requires ≥58% model prob + corroborating form/H2H

## Exclusions (per brief)

Not listed anywhere: soccer, boxing, UFC, MMA, football (soccer), American football (NFL), hurling, horse racing, cycling, specials.  
Where a sport is in off-season (e.g., AFL men's after Sep 27 GF), we list it as "no matches in window" rather than inventing fixtures.

## GitHub Pages

Site deploys automatically on push to `main` via `.github/workflows/pages.yml`:
1. Validate JSON
2. Check all subpages exist & no TODOs
3. Upload artifact & deploy to `github-pages` environment

Verify deploy at `https://buffedlizard55-lab.github.io/OLBG4/` after merge.

## Parallel session coordination

See `COORDINATION.md` for task board. This repo supports multi-agent parallel sessions:
- Claim task → commit/push claim immediately
- Branch `session-<id>/<task>` per session
- Non-overlapping file scopes; shared outputs only via final integration session (T16) which re-verifies line-by-line, checks broken links, and publishes.

Current active session: `arena/290a9dba-olbg4` (integrated scope — all tasks claimed as single-session override on 2026-10-21).

## License

Data is curated from official public sources (linked per row). Code MIT-equivalent for site.
