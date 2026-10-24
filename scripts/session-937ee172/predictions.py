"""Hand-written write-ups. Every number quoted is copied from data/session-937ee172/official/nhl_2026-10-24.json
(NHL standings API) or the NHL scoreboard API response for 24 Oct 2026, and is re-checked by build.py.
Write-ups are only produced for Medium or High rows. Low rows get no write-up."""

PREDICTIONS = {
 2026020170: {
  "selection": "Boston Bruins moneyline",
  "text": ("Boston's case is built on defence. The Bruins have allowed 22 goals in 11 games, 2.00 per game, the second-lowest "
           "figure in the league behind Dallas, and they have won their last game after an 8-2-1 start. San Jose has scored 33 goals "
           "in 11 games and has won two in a row, but it has allowed 37, which is 3.36 a game. David Pastrnak leads Boston with 6 goals "
           "and 10 assists on the NHL scoreboard. Our own line puts Boston near two-in-three to win. Injury news and starting goalies "
           "were not confirmed for this write-up, so the pick rests on season numbers alone."),
  "sources": ["https://api-web.nhle.com/v1/standings/2026-10-24", "https://api-web.nhle.com/v1/score/2026-10-24",
              "https://www.nhl.com/standings", "https://www.olbg.com/betting-tips/Ice_Hockey/NHL/NHL/SJ_Sharks_@_BOS_Bruins/13?event_id=200007"]},
 2026020174: {
  "selection": "Vegas Golden Knights moneyline",
  "text": ("Vegas is the stronger side on the season so far. The Golden Knights are 8-4-0 with 46 goals scored in 12 games, 3.83 a game, "
           "and they have allowed 36, which is 3.00 a game. Columbus is 3-5-0 and has been outscored 29 to 20 in eight games. Both clubs "
           "have lost their last two, so the form signal is about the season gap rather than a streak. Mark Stone has 8 goals and Jack Eichel "
           "has 13 assists for Vegas, and Kent Johnson has 4 goals for Columbus, all per the NHL scoreboard. Our own line gives Vegas about "
           "a 65 percent chance. Starting goalies and injuries were not confirmed for this write-up."),
  "sources": ["https://api-web.nhle.com/v1/standings/2026-10-24", "https://api-web.nhle.com/v1/score/2026-10-24",
              "https://www.nhl.com/standings", "https://www.olbg.com/betting-tips/Ice_Hockey/NHL/NHL/VGS_Golden_Knights_@_CLB_Blue_Jackets/13?event_id=200001"]},
 2026020178: {
  "selection": "Detroit Red Wings moneyline",
  "text": ("Detroit's edge comes from Calgary's defence. The Flames have allowed 38 goals in nine games, 4.22 a game, the second-highest "
           "per-game figure in the league, and they have scored only 19 times, 2.11 a game. Detroit has 28 goals scored and 30 allowed in "
           "10 games and is on a one-game win streak. Calgary has won its last two, which is the main caution. Alex DeBrincat leads Detroit "
           "with 6 goals and John Gibson has 3 wins, while Devin Cooley has 2 wins for Calgary, per the NHL scoreboard. Our own line gives "
           "Detroit about 63 percent, so this is a Medium pick. Starting goalies and injuries were not confirmed for this write-up."),
  "sources": ["https://api-web.nhle.com/v1/standings/2026-10-24", "https://api-web.nhle.com/v1/score/2026-10-24",
              "https://www.nhl.com/standings", "https://www.olbg.com/betting-tips/Ice_Hockey/NHL/NHL/DET_Red_Wings_@_CGY_Flames/13?event_id=200004"]},
}
