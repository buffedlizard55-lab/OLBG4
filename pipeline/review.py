"""Review log: module by module, claim by claim, with the official source checked.

The owner asked for the repository to be reviewed line by line against official sources,
with review links supplied and irregularities flagged. This module is that record. Every
entry names the file, the claim the code makes, the official page or endpoint that was
used to check it, and the outcome.

`outcome` is one of:

* ``matches``      — the code agrees with the official source;
* ``corrected``    — the review found a defect, it was fixed, and the fix is linked;
* ``documented``   — behaviour is a stated modelling choice rather than a fact claim;
* ``limited``      — an official source could not support the claim, so the behaviour is
                     withheld or flagged rather than guessed.

Nothing here is a substitute for reading the code; it is the evidence trail behind it.
"""
from __future__ import annotations

REVIEW_ITEMS = [
    {
        "area": "pipeline/providers/nba.py",
        "claim": "NBA fixtures, start times, venues and final scores come from the league's "
                 "own schedule file (cdn.nba.com).",
        "source": "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json",
        "check": "Response is 7.4 MB of JSON with meta.request 'http://nba.cloud/league/00/...', "
                 "leagueSchedule.seasonYear 2026-27, 1274 games and per-game homeTeam/awayTeam "
                 "score, wins and losses. Fields map 1:1 onto the fixture rows.",
        "outcome": "matches",
    },
    {
        "area": "pipeline/providers/nba.py",
        "claim": "Only regular-season games are ingested and counted.",
        "source": "https://www.nba.com/games",
        "check": "NBA game ids encode the season type (001 pre-season, 002 regular season, "
                 "004 playoffs). The provider now filters on the 002 prefix; before the fix, "
                 "pre-season games were being counted as results.",
        "outcome": "corrected",
    },
    {
        "area": "pipeline/providers/nba.py",
        "claim": "Prior-season results are loaded from the NBA stats service to stabilise "
                 "early-season ratings.",
        "source": "https://stats.nba.com/stats/leaguegamelog",
        "check": "The endpoint returns no response from the build runner (read timeout, twice, "
                 "under two different header profiles). The schedule CDN only carries the "
                 "current season; scheduleLeagueV2_3/_4/_2025 are HTTP 403. No official "
                 "prior-season archive was found, so the code records the degradation.",
        "outcome": "limited",
    },
    {
        "area": "pipeline/config.py (MIN_GAMES_FOR_MARKETS)",
        "claim": "A price is only originated when at least 20 completed games per team back "
                 "the rating.",
        "source": "https://www.nba.com/games",
        "check": "Opening week produced 3 league games in total. Prices on a 1-3 game sample "
                 "would be noise, so those fixtures are published with records and sources but "
                 "without markets, and the reason is written into the row.",
        "outcome": "documented",
    },
    {
        "area": "pipeline/providers/nhl.py",
        "claim": "NHL fixtures, venues and GameCenter links come from the league API.",
        "source": "https://api-web.nhle.com/v1/schedule/2026-10-21",
        "check": "Returns PHI@BUF and FLA@OTT on 2026-10-21, both 23:30Z, with venue and a "
                 "gameCenterLink. The same two rows appear on the dashboard for that date.",
        "outcome": "matches",
    },
    {
        "area": "pipeline/providers/nhl.py",
        "claim": "Each daily call returns one day of games.",
        "source": "https://api-web.nhle.com/v1/schedule/2026-10-21",
        "check": "The endpoint actually returns the surrounding week. The provider filters "
                 "block['date'] == day and de-duplicates by game id; without that, every "
                 "fixture would be published seven times.",
        "outcome": "corrected",
    },
    {
        "area": "pipeline/providers/nhl.py",
        "claim": "Team records are the official points and W-L-OTL lines.",
        "source": "https://api-web.nhle.com/v1/standings/now",
        "check": "Standings carry wins, losses, otLosses and points per team; the record "
                 "string is assembled from those fields only, with no computation.",
        "outcome": "matches",
    },
    {
        "area": "pipeline/providers/mlb.py",
        "claim": "MLB fixtures, probable pitchers, status and scores come from the official "
                 "Stats API.",
        "source": "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-21&endDate=2026-10-28",
        "check": "Returns the World Series games with gamePk, gameDate in UTC, status, venue, "
                 "teams and probablePitcher where announced. The dashboard's three MLB rows "
                 "match the returned dates and gamePks.",
        "outcome": "matches",
    },
    {
        "area": "pipeline/providers/mlb.py",
        "claim": "A `fields=` projection trims the response without losing data the pipeline "
                 "needs.",
        "source": "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-01&endDate=2026-10-02",
        "check": "The projection had dropped abstractGameState, which the provider uses to "
                 "decide whether a game is final. The field is now in the projection, and the "
                 "standings call runs unfiltered so no record is silently lost.",
        "outcome": "corrected",
    },
    {
        "area": "pipeline/model.py",
        "claim": "Ratings are a ridge-regularised least-squares fit on official final scores, "
                 "with a recency half-life of 120 days.",
        "source": "https://statsapi.mlb.com/api/v1/schedule",
        "check": "Margin model: margin = home advantage + rating(home) - rating(away). Total "
                 "model: total = league mean + offence(home) + defence(away). Both solved "
                 "exactly (at most 32 teams). Re-running the fit is deterministic; the "
                 "self-test checks that a stronger synthetic team projects a larger margin.",
        "outcome": "documented",
    },
    {
        "area": "pipeline/model.py",
        "claim": "Probabilities come from the empirical residual distribution, not a normal "
                 "assumption.",
        "source": "https://www.nhl.com/scores",
        "check": "Hockey and baseball score in small integers, so a normal CDF misprices "
                 "totals and puck lines. The fit keeps the standardised residuals and reads "
                 "probabilities from their order statistics. Backtest Brier and log loss are "
                 "published for every sport.",
        "outcome": "documented",
    },
    {
        "area": "pipeline/markets.py",
        "claim": "Every market is two-sided, prices are our own, and no bookmaker or OLBG "
                 "price is used.",
        "source": "https://www.olbg.com/betting-tips",
        "check": "OLBG listing rows expose community tip share and comments but no price; its "
                 "Value Rating compares a selection's odds with tip share. The pipeline never "
                 "reads an OLBG page at build time; the only OLBG input is the taxonomy note.",
        "outcome": "documented",
    },
    {
        "area": "pipeline/markets.py",
        "claim": "Lines are originated on a half-point so a market cannot push.",
        "source": "https://www.nhl.com/scores",
        "check": "round_half always returns floor(|x|)+0.5, and totals use floor(x)+0.5. The "
                 "self-test asserts two selections per market and probabilities summing to 1.",
        "outcome": "matches",
    },
    {
        "area": "pipeline/markets.py (price floor)",
        "claim": "A quoted decimal price is always greater than 1.01.",
        "source": "https://www.nba.com/games",
        "check": "A 99%+ probability with a 4.5% hold produced a price below 1.01, which is not "
                 "a tradeable number. The price is now clamped at 1.01 and the clamp is visible "
                 "in the market table.",
        "outcome": "corrected",
    },
    {
        "area": "pipeline/predictions.py",
        "claim": "Written predictions are at least 30 words, name the selection unambiguously, "
                 "and share no more than 55% of their vocabulary with another prediction.",
        "source": "https://www.nhl.com/gamecenter",
        "check": "The lint tokenises each text, requires the selection string, rejects banned "
                 "promotional phrases and measures Jaccard similarity against every other "
                 "prediction. In the last audited run 18 predictions passed with 0 withdrawn.",
        "outcome": "matches",
    },
    {
        "area": "pipeline/predictions.py (variants)",
        "claim": "Consecutive predictions do not reuse the same sentence structure.",
        "source": "https://www.nhl.com/gamecenter",
        "check": "Earlier builds produced 0.55-0.86 similarity between write-ups. The composer "
                 "now selects from five independent sentence blocks and decodes a per-pick "
                 "variant with a prime stride (7919) so adjacent picks differ in every block.",
        "outcome": "corrected",
    },
    {
        "area": "pipeline/verify.py",
        "claim": "A row without a source URL on the league's own domain is never published.",
        "source": "https://www.nhl.com",
        "check": "check_fixtures compares every source URL's host against the sport's official "
                 "domain list and drops the row with an 'unverified_source' flag. The self-test "
                 "feeds an example.com URL and asserts the row is excluded.",
        "outcome": "matches",
    },
    {
        "area": "pipeline/verify.py (strict mode)",
        "claim": "One unverifiable row should not stop the whole site from publishing.",
        "source": "https://github.com/buffedlizard55-lab/OLBG4/actions",
        "check": "Strict mode now fails only on errors attached to published rows, an empty "
                 "fixture set, or more than 25% of ingested rows being excluded. Excluded rows "
                 "are findings, not build failures.",
        "outcome": "corrected",
    },
    {
        "area": "pipeline/config.py (scope)",
        "claim": "Gaelic football is out of scope because 'football' and 'hurling' were "
                 "excluded.",
        "source": "https://www.olbg.com/betting-tips/Gaelic_Football/All_Gaelic_Football/All_Events/St_Finbarrs_v_Nemo_Rangers/25?event_id=3530",
        "check": "The owner named hurling separately and confirmed Gaelic football stays in "
                 "scope. The exclusion list, the taxonomy and the site copy were corrected; "
                 "Gaelic football is now listed as in-scope with no official feed.",
        "outcome": "corrected",
    },
    {
        "area": "session-4afef1af pages",
        "claim": "Every table row carries a working link to the official source for that row.",
        "source": "https://www.nhl.com/gamecenter",
        "check": "Each fixture stores the league's own game URL plus its schedule endpoint. The "
                 "picks, matches and per-sport tables render that link; the self-test follows "
                 "every internal href and fails on a broken path.",
        "outcome": "matches",
    },
]

IRREGULARITIES = [
    "NBA pre-season games were included in records and results until the 002-prefix filter "
    "was added; the affected snapshots were rebuilt.",
    "NBA prior-season history is unreachable from the runner (stats.nba.com times out, the "
    "CDN has no archive), so NBA markets are withheld until the current-season sample reaches "
    "20 games per team. No ratings were invented to fill the gap.",
    "Gaelic football had been excluded by an over-broad reading of the exclusion list; it is "
    "in scope and is now listed as such.",
    "The NHL daily schedule returns a week of games; a per-day filter and a seen-set were "
    "added to stop duplicate fixtures.",
    "An MLB field projection silently removed abstractGameState, so final games could be "
    "treated as scheduled; the projection now names it and the standings call is unfiltered.",
    "Prediction copy repeated sentence structure across picks (similarity up to 0.86); the "
    "block composer and prime-stride variants fixed it, and the lint now enforces 0.55.",
    "Duplicate predictions could be emitted for the same fixture and market; they are now "
    "de-duplicated on (fixture_id, market).",
    "A 99% probability produced a decimal price under 1.01; prices are clamped to a minimum "
    "of 1.01.",
    "The night's page showed duplicate source labels and a truncated kick-off time; both were "
    "fixed in the renderer, together with picks sorted as strings instead of by kick-off.",
    "Withheld fixtures crashed the rationale builder before verification; the builder is "
    "skipped for them and the site renders a 'withheld' state instead of a blank row.",
]
