#!/usr/bin/env python3
"""Board AF — build coverage.json and flagged.json from the desk."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "session-ddbcc895"
SPORTS = [
    ("Tennis", "tennis", "https://www.olbg.com/betting-tips/Tennis/3"),
    ("Basketball", "basketball", "https://www.olbg.com/betting-tips/Basketball/4"),
    ("Baseball", "baseball", "https://www.olbg.com/betting-tips/Baseball/12"),
    ("Ice Hockey", "ice-hockey", "https://www.olbg.com/betting-tips/Ice_Hockey/13"),
    ("Darts", "darts", "https://www.olbg.com/betting-tips/Darts/15"),
    ("Snooker", "snooker", "https://www.olbg.com/betting-tips/Snooker/8"),
    ("Handball", "handball", "https://www.olbg.com/betting-tips/Handball/20"),
    ("Volleyball", "volleyball", "https://www.olbg.com/betting-tips/Volleyball/21"),
    ("Rugby Union", "rugby-union", "https://www.olbg.com/betting-tips/Rugby_Union/9"),
    ("Rugby League", "rugby-league", "https://www.olbg.com/betting-tips/Rugby_League/10"),
    ("Cricket", "cricket", "https://www.olbg.com/betting-tips/Cricket/7"),
    ("eSports", "esports", "https://www.olbg.com/betting-tips/eSports/23"),
    ("Badminton", "badminton", "https://www.olbg.com/betting-tips/Badminton/18"),
    ("Table Tennis", "table-tennis", "https://www.olbg.com/betting-tips/Table_Tennis/24"),
    ("Aussie Rules", "aussie-rules", "https://www.olbg.com/betting-tips/Aussie_Rules/22"),
    ("Golf", "golf", "https://www.olbg.com/betting-tips/Golf/5"),
    ("Motor Racing", "motor-racing", "https://www.olbg.com/betting-tips/Motor_Racing/14"),
    ("Greyhounds", "greyhounds", "https://www.olbg.com/betting-tips/Greyhounds/28"),
]

NOTES = {
    "Tennis": "WTA QFs on 23 Oct came from the official WTA match API; ATP QFs came from the official ATP order-of-play PDFs. WTA rows stamped 23:59 local are the tour's unscheduled placeholder, not a confirmed start time.",
    "Basketball": "EuroLeague and EuroCup games come from the official EuroLeague games API. NBA fixtures come from the committed NBA.com capture of 22 Oct 17:08Z because nba.com returned HTTP 403 to the evening runner; NBA rows carry that capture time.",
    "Baseball": "All seven World Series games are in the official MLB Stats API schedule (24 Oct – 1 Nov). Only Games 1–2 have probable pitchers published; later games are unpriced on the pitcher input but the series total is priced.",
    "Ice Hockey": "NHL schedule and standings are the official NHL API; Liiga fixtures and table are the official Liiga API. Both are machine-readable and were re-read on 22 Oct 2026.",
    "Darts": "PDC European Championship pairings and seeds are from the official PDC Europe draw page. Start times come from the OLBG listing; the official page confirms the Friday session.",
    "Snooker": "The WST site and its match service returned a JavaScript shell / 'Unauthorized' from the capture runner. No official draw could be read, so no Snooker fixture is published as verified.",
    "Handball": "Betoro Herreligaen fixtures and table are the official Tophåndbold pages. EHF Champions League and the French/German/Spanish leagues returned JavaScript shells, so their fixtures are not published.",
    "Volleyball": "PlusLiga fixtures are verified from the official PlusLiga schedule, but the men's table could not be read (the captured table URL served the women's 2024/25 page), so no line is originated.",
    "Rugby Union": "Top 14 and Pro D2 fixtures and tables are official LNR pages. URC Round 4 is the official URC fixtures article; the URC table page is a JavaScript shell and the World Rugby ranking page carried news rather than a table, so URC rows are unpriced.",
    "Rugby League": "RLWC fixtures are from the official RLWC 2026 draw payload; men's strength uses the IRL World Rankings percentages. The women's IRL table was not rendered in the capture, so women's fixtures are unpriced.",
    "Cricket": "Fixtures are the official Cricket Australia match list. Strength uses the ICC Men's ODI and Men's/Women's T20I annual-update releases (May 2026). Women's ODI rankings were not available, and domestic One-Day Cup matches have no international rating.",
    "eSports": "Worlds Swiss fixtures and Riot team GPR Elo come from the official lolesports.com schedule page. Every Swiss match in this window is a best-of-one, so only the match-winner market is originated.",
    "Badminton": "The BWF results pages are a JavaScript shell and the match centre did not expose an unauthenticated endpoint to the runner. No official draw could be read.",
    "Table Tennis": "The WTT event pages returned a 6.4 KB shell and no official draw could be read.",
    "Aussie Rules": "The AFLW fixture page is a JavaScript shell; the official AFL API returned HTTP 403/404. No fixture could be verified.",
    "Golf": "PGA Tour and DP World Tour pages are leaderboards, not head-to-head fixtures; no match market exists and no official field-strength table could be read from the runner.",
    "Motor Racing": "Formula 1 and MotoGP publish race entry lists and results rather than match fixtures; no official rating table was readable, so no outright line is originated.",
    "Greyhounds": "GBGB publishes results and open-race schedules, not a machine-readable fixture feed; no upcoming race could be verified.",
}


def main() -> int:
    desk = json.loads((DATA / "desk.json").read_text(encoding="utf-8"))
    preds = json.loads((DATA / "predictions.json").read_text(encoding="utf-8"))
    rows = desk["rows"]
    by_sport = defaultdict(list)
    for r in rows:
        by_sport[r["sport"]].append(r)
    coverage = []
    for sport, slug, olbg in SPORTS:
        rs = by_sport.get(sport, [])
        priced = [r for r in rs if r["priced"]]
        high = [r for r in priced if r["confidence"] == "High"]
        high_in = [r for r in high if r["in_window"]]
        coverage.append({
            "sport": sport, "slug": slug, "olbg_url": olbg,
            "fixtures": len(rs), "priced": len(priced),
            "high": len(high), "high_in_window": len(high_in),
            "medium": sum(1 for r in priced if r["confidence"] == "Medium"),
            "low": sum(1 for r in priced if r["confidence"] == "Low"),
            "markets": sum(len(r["markets"]) for r in priced),
            "predictions": sum(1 for p in preds["predictions"] if p["sport"] == sport),
            "status": "priced" if priced else ("listed" if rs else "no verified fixture"),
            "note": NOTES.get(sport, ""),
        })
    (DATA / "coverage.json").write_text(json.dumps({"schema": "olbg4.board-af.coverage/1", "sports": coverage},
                                                   indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    flags = []
    fid = 1

    def flag(sport, category, detail, source="", examples=None, severity="review"):
        nonlocal fid
        flags.append({"id": f"AF-F{fid:03d}", "sport": sport, "category": category, "detail": detail,
                      "source": source, "examples": examples or [], "severity": severity})
        fid += 1

    for sport, slug, olbg in SPORTS:
        rs = by_sport.get(sport, [])
        unpriced = [r for r in rs if not r["priced"]]
        if rs and not unpriced:
            continue
        if unpriced:
            reasons = Counter(r.get("reason_unpriced") or "not priced" for r in unpriced)
            flag(sport, "fixtures published without a line",
                 f"{len(unpriced)} of {len(rs)} verified fixtures carry no pick, no price and no confidence. "
                 f"Reasons recorded: {'; '.join(f'{v} x {k}' for k, v in reasons.items())}.",
                 examples=[{"id": r["id"], "fixture": f'{r["side_a"]} vs {r["side_b"]}', "start_utc": r["start_utc"],
                            "source": r["source_url"], "reason": r.get("reason_unpriced")} for r in unpriced[:8]])
        if not rs:
            flag(sport, "no verified upcoming fixture",
                 NOTES.get(sport, "No official fixture could be read for this sport in the 22 Oct 2026 capture."),
                 source=olbg, severity="gap")

    out_of_window = [r for r in rows if r["priced"] and r["confidence"] == "High" and not r["in_window"]]
    flag("All sports", "High-confidence picks shorter than -250",
         f"{len(out_of_window)} High-confidence selections price at shorter than -250 American. "
         "They are published with the band flag rather than being hidden or relabelled: a >=70% probability "
         "implies fair odds of -233 or shorter, so only probabilities between 0.700 and 0.714 can satisfy both "
         "the confidence rule and the -250..+10,000 band at once.",
         examples=[{"id": r["id"], "sport": r["sport"], "selection": r["pick_label"],
                    "probability": r["pick_prob"], "fair_american": r["pick_fair_american"],
                    "source": r["source_url"]} for r in out_of_window[:10]])
    small = [r for r in rows if r["priced"] and r["sport"] == "Basketball" and r["competition"] == "NBA"]
    flag("Basketball", "NBA sample is two games or fewer",
         f"{len(small)} NBA fixtures are priced from the committed 22 Oct 17:08Z NBA.com capture. "
         "With one or two games played per team the sample gate fails, so no NBA row can be High; the rows are "
         "published as Medium or Low and the fixture, not the line, is the verified value.",
         source="https://www.nba.com/schedule",
         examples=[{"id": r["id"], "fixture": f'{r["side_a"]} vs {r["side_b"]}', "confidence": r["confidence"]} for r in small[:5]])
    flag("Cricket", "ICC ratings are the May 2026 annual update",
         "The ICC rankings pages render client-side, so the strength inputs are the last published annual-update "
         "releases (Men's ODI 11 May 2026; Men's and Women's T20I 5 May 2026). The release date is printed on every row.",
         source="https://www.icc-cricket.com/news/india-retain-top-position-in-men-s-odi-team-rankings-after-annual-update")
    flag("Rugby League", "Women's IRL rankings unavailable",
         "The IRL World Rankings page rendered only the men's table in the capture. Women's World Cup fixtures are "
         "published with no line and are listed here for review.",
         source="https://www.intrl.sport/world-rankings",
         examples=[{"id": r["id"], "fixture": f'{r["side_a"]} vs {r["side_b"]}', "start_utc": r["start_utc"]}
                   for r in rows if r["sport"] == "Rugby League" and "(Women)" in r["competition"]][:8])
    flag("Cricket and Rugby League", "Total lines use a model assumption",
         "No official scoring mean was captured for these competitions, so the match-total line is a stated model "
         "assumption (268.5 runs for ODIs, 165.5 for T20Is, 44.5 points for RLWC). The handicap and match-winner "
         "markets are driven by the official rating table.",
         source="https://www.icc-cricket.com/news/india-retain-top-position-in-men-s-odi-team-rankings-after-annual-update")
    flag("Tennis", "WTA order-of-play placeholders",
         "Four WTA rows carry the tour's 23:59 local placeholder because the order of play had not been published at "
         "capture time; the date is confirmed, the start time is not.",
         source="https://www.wtatennis.com/",
         examples=[{"id": r["id"], "fixture": f'{r["side_a"]} vs {r["side_b"]}', "start_utc": r["start_utc"]}
                   for r in rows if r["sport"] == "Tennis" and r["start_utc"][11:16] in ("14:59", "15:59")][:8])
    flag("Tennis", "ATP start times are 'not before' times",
         "ATP fixtures and start times come from the official order-of-play PDF; the PDF states that any match may be "
         "moved, so times are the published session times, not guaranteed.",
         source="https://www.protennislive.com/posting/2026/9410/op.pdf")
    flag("All sports", "Gaelic football treated as out of scope",
         "The brief excludes 'football' and 'hurling'. OLBG separates Gaelic football from association football. "
         "Board AF publishes no Gaelic football rows; earlier boards disagree (some include it), so the scope call "
         "is flagged rather than silently resolved.",
         source="https://www.olbg.com/betting-tips/Gaelic_Football/25", severity="scope")
    flag("All sports", "Capture filename collision (WST/PDC match services)",
         "Two targets in the second, third and fourth capture passes shared an id (one web host, one admin host). "
         "The later request overwrote the earlier file, so the 200 body from matches.snooker.web.gc.wstservices.co.uk "
         "was not retained; the manifest now records it with file=null and the collision is disclosed here. Neither "
         "service is the source of a published row, so no published value depends on the lost bytes.",
         source="https://participants.snooker.web.gc.wstservices.co.uk/v2/?page.size=100", severity="review")
    flag("All sports", "Darts strength model uses official seeds only",
         "The PDC order-of-merit page rendered no table to the runner. Darts probabilities are therefore a function "
         "of the official European Tour seedings, not of prize-money or form; the basis is printed on every row.",
         source="https://www.pdc-europe.tv/turniere/european-championship-2026")
    (DATA / "flagged.json").write_text(json.dumps({"schema": "olbg4.board-af.flagged/1", "count": len(flags),
                                                   "items": flags}, indent=1, ensure_ascii=False) + "\n",
                                       encoding="utf-8")
    print("coverage", len(coverage), "flags", len(flags))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
