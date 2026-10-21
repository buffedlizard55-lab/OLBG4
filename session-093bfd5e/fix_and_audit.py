#!/usr/bin/env python3
"""Board K (session 093bfd5e) — fix + audit of the root hub `data/matches.json`.

What this does, and nothing more:
1. Classifies every hub row's source domain as OFFICIAL (governing body / league /
   official tour / national federation) or SECONDARY.
2. Downgrades any row still marked `verified` on a SECONDARY source to
   `verified:false, flagged:true` with a written reason (fixes Board J finding F-01).
   Rows are never deleted and no sporting value is inferred or invented.
3. Upgrades rows for which this session re-fetched an OFFICIAL page on 2026-10-21
   and confirmed the fixture (participants + date). Each upgrade cites the exact
   official URL and the evidence seen on it (see SPOT_CHECKS in audit.json).
4. Corrects statuses only where the official page fetched today shows a result
   (NHL, 2026-10-20) or a fixture window that has already closed (CRK06).
5. Audits: JSON shape, excluded sports, High-confidence prediction word count
   (>=30) and uniqueness, official-source coverage. Writes audit.json.

Idempotent: safe to re-run; reasons are appended once.
Official pages were retrieved 2026-10-21 with the agent web-fetch tool (sandbox
shell has no egress to sports sites). Reproduce by opening each URL in SPOT_CHECKS.
"""
import json, re, urllib.parse, pathlib, collections

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "matches.json"
OUT = pathlib.Path(__file__).resolve().parent / "audit.json"
CUT = "2026-10-21"
TAG = "Board K 2026-10-21"

OFFICIAL = {
    "nba.com", "nhl.com", "mlb.com", "atptour.com", "wtatennis.com",
    "pgatour.com", "lpga.com", "cricket.com.au", "icc-cricket.com",
    "euroleaguebasketball.net", "world.rugby", "bwfbadminton.com",
    "bwfworldtour.bwfbadminton.com", "fivb.com", "volleyballworld.com",
    "afl.com.au", "ittf.com", "fftt.com", "ehfcl.eurohandball.com",
    "eurohandball.com", "ihf.info", "lolesports.com", "valorantesports.com",
    "nrl.com", "wst.tv", "pdc.tv", "ehfeuro.eurohandball.com",
}

# Fixtures re-confirmed TODAY on an official page (participants + date seen there).
UPGRADES = {
    "EL01": ("https://www.euroleaguebasketball.net/en/euroleague/news/the-2026-27-euroleague-schedule-is-official/",
             "EuroLeague (official) — 2026-27 schedule release",
             "EuroLeague official schedule release states Round 7 on Oct 22 features Partizan v Crvena Zvezda (first Serbian derby)."),
    "EL02": ("https://www.euroleaguebasketball.net/en/euroleague/news/the-2026-27-euroleague-schedule-is-official/",
             "EuroLeague (official) — 2026-27 schedule release",
             "Same official release states Round 7 on Oct 22 features Anadolu Efes facing Besiktas (first Turkish derby)."),
    "NHL01": ("https://www.nhl.com/schedule/2026-10-20", "NHL.com — Schedule 2026-10-20",
              "NHL.com lists Sharks @ Canadiens, Oct 20, result SJS 4, MTL 3 (OT). Hub pick (Montreal) lost."),
    "NHL02": ("https://www.nhl.com/schedule/2026-10-20", "NHL.com — Schedule 2026-10-20",
              "NHL.com lists Avalanche @ Devils, Oct 20, result NJD 4, COL 3. Hub pick (Colorado) lost."),
    "NHL03": ("https://www.nhl.com/schedule/2026-10-20", "NHL.com — Schedule 2026-10-20",
              "NHL.com lists Ducks @ Islanders, Oct 20, result NYI 3, ANA 2. Hub pick (Islanders) won."),
    "NHL04": ("https://www.nhl.com/schedule/2026-10-20", "NHL.com — Schedule 2026-10-20",
              "NHL.com lists Maple Leafs @ Blue Jackets, Oct 20, result TOR 6, CBJ 2. Hub pick (Columbus) lost."),
    "NHL05": ("https://www.nhl.com/schedule/2026-10-20", "NHL.com — Schedule 2026-10-20/21",
              "NHL.com lists Flyers @ Sabres, Wed Oct 21, 7:30 PM EDT (upcoming at fetch time)."),
    "NHL06": ("https://www.nhl.com/schedule/2026-10-20", "NHL.com — Schedule 2026-10-20",
              "NHL.com lists Bruins @ Stars, Oct 20, result DAL 3, BOS 2 (OT). Hub moneyline pick (Dallas) won; -1.5 puck line did not cover (1-goal OT win)."),
    "NHL07": ("https://www.nhl.com/schedule/2026-10-20", "NHL.com — Schedule 2026-10-20/21",
              "NHL.com lists Panthers @ Senators, Wed Oct 21, 7:30 PM EDT (upcoming at fetch time)."),
    "RUG01": ("https://www.world.rugby/beta/en/match/1e74b48e-25fe-4ebe-beea-abb6cea010a0",
              "World Rugby (official) — Nations Championship 2026 match page",
              "World Rugby match page: Ireland v Argentina, Nations Championship 2026, Aviva Stadium Dublin, Friday 06 November 2026."),
    "RUG02": ("https://www.world.rugby/beta/en/match/54780758-13bb-414b-94d6-2095f217459c",
              "World Rugby (official) — Nations Championship 2026 match page",
              "World Rugby tournament page lists Italy v South Africa, Sat 7 Nov 2026, Allianz Stadium, Turin."),
    "RUG03": ("https://www.world.rugby/beta/en/match/db7d80ff-3fa4-4b76-8b84-f615725dd62b",
              "World Rugby (official) — Nations Championship 2026 match page",
              "World Rugby tournament page lists Scotland v New Zealand, Sat 7 Nov 2026, Murrayfield, Edinburgh."),
    "RUG04": ("https://www.world.rugby/beta/en/match/20078fb5-fab3-4d28-ad54-d550b01b472d",
              "World Rugby (official) — Nations Championship 2026 match page",
              "World Rugby tournament page lists Wales v Japan, Sat 7 Nov 2026, Principality Stadium, Cardiff."),
    "RUG05": ("https://www.world.rugby/beta/en/match/d21f7bed-f2f9-45bd-be33-3a0fc9beec42",
              "World Rugby (official) — Nations Championship 2026 match page",
              "World Rugby tournament page lists England v Australia, Sun 8 Nov 2026, Allianz Stadium, London."),
    "RUG06": ("https://www.world.rugby/beta/en/match/267608f1-90cc-4c93-ac68-b0f0fa3bbf9e",
              "World Rugby (official) — Nations Championship 2026 match page",
              "World Rugby match page: France v Fiji, Nations Championship 2026, Groupama Stadium Lyon, Saturday 07 November 2026."),
    "BDM02": ("https://bwfworldtour.bwfbadminton.com/tournament/5272/yonex-french-open-2026/overview",
              "BWF World Tour (official) — YONEX French Open 2026",
              "BWF official tournament page: YONEX French Open 2026, 20-25 October, Arena Grand Paris, USD 950,000; An Se-young listed in women's singles (top seed / defending champion per BWF)."),
}

# Status corrections proven by the official page fetched today. No other values touched.
STATUS_FIX = {
    "NHL01": "Completed — SJS 4, MTL 3 (OT) on 2026-10-20 (NHL.com)",
    "NHL02": "Completed — NJD 4, COL 3 on 2026-10-20 (NHL.com)",
    "NHL03": "Completed — NYI 3, ANA 2 on 2026-10-20 (NHL.com)",
    "NHL04": "Completed — TOR 6, CBJ 2 on 2026-10-20 (NHL.com)",
    "NHL06": "Completed — DAL 3, BOS 2 (OT) on 2026-10-20 (NHL.com)",
    "CRK06": "Completed window — 3 ODIs 9/11/14 Oct 2026 at Allan Border Field confirmed on cricket.com.au; series result not re-checked in this pass",
}

# Extra flags (reason appended once). Fixture may be verified; the flag is about the pick/text.
EXTRA_FLAGS = {
    "NBA01": "Game dated 2026-10-20 is now past; hub status said 'Scheduled' and the result / pick outcome was not re-verified on NBA.com in this pass.",
    "NBA02": "Game dated 2026-10-20 is now past; hub status said 'Scheduled' and the result / pick outcome was not re-verified on NBA.com in this pass. Fixture itself (PHI @ NYK, Oct 20, 7pm ET) confirmed on NBA.com schedule release.",
    "NBA03": "Game dated 2026-10-20 is now past; hub status said 'Scheduled' and the result / pick outcome was not re-verified on NBA.com in this pass. Fixture itself (OKC @ SAS at Frost Bank Center, Oct 20, 9:30pm ET) confirmed on NBA.com schedule release.",
    "NHL01": "Pick settled and lost: NHL.com result SJS 4, MTL 3 (OT) contradicts the Montreal moneyline / -1.5 puck-line pick. Kept for manual review.",
    "NHL02": "Pick settled and lost: NHL.com result NJD 4, COL 3 contradicts the Colorado pick. Kept for manual review.",
    "NHL04": "Pick settled and lost: NHL.com result TOR 6, CBJ 2 contradicts the Columbus pick. Prediction text also contains an editorial artifact ('Actually Toronto rested; but…'). Kept for manual review.",
    "NHL06": "Moneyline pick won (DAL 3, BOS 2 OT on NHL.com) but the originated DAL -1.5 puck line did not cover in a 1-goal OT game. Handicap leg flagged; moneyline result confirmed.",
    "EL02": "Prediction text contains an editorial artifact ('89-66 blowout of Efes? Actually Efes beat Bayern 101-93… Verify tip via…') — form claims inside that text were not re-verified in this pass. Fixture confirmed on EuroLeague official release.",
    "CRK06": "Series window (9-14 Oct) had already closed at the 2026-10-21 cut-off yet hub status said 'Scheduled'; the 3-0 pick outcome is unverified in this pass (fixtures/dates/venue confirmed on cricket.com.au only).",
}

SPOT_CHECKS = [
    {"id": "NBA01/NBA02/NBA03", "official_url": "https://www.nba.com/news/2026-27-nba-regular-season-schedule",
     "evidence": "NBA.com: Tip-Off Oct 20 NBC/Peacock tripleheader — Boston Celtics visit Detroit Pistons (3 p.m. ET); defending champion New York Knicks host Philadelphia 76ers (7 p.m. ET); San Antonio Spurs meet Oklahoma City Thunder at Frost Bank Center (9:30 p.m. ET).",
     "outcome": "Fixtures CONFIRMED (teams, date, venue city, times match hub). Status/pick outcomes NOT re-verified -> flagged."},
    {"id": "MLB01", "official_url": "https://www.mlb.com/news/2026-mlb-playoff-and-world-series-schedule",
     "evidence": "MLB.com: 'World Series will begin with the NL champion Milwaukee Brewers hosting the AL champion Tampa Bay Rays, Game 1 at American Family Field on Friday, Oct. 23' (8 p.m. ET FOX).",
     "outcome": "CONFIRMED — hub match, date, venue and Game 1 pick framing match. Verified stays."},
    {"id": "CRK01", "official_url": "https://www.cricket.com.au/news/4425772/mark-your-calendar-2026-australia-cricket-schedule-fixtures-dates-tours-wtc-top-end-tests-south-africa-bangladesh-new-zealand-england-india-t20-world-cup",
     "evidence": "Cricket Australia (official): 'October 18-23: Second Test v South Africa, St George's Park, Gqeberha' (1st Test Oct 9-14 Kingsmead).",
     "outcome": "CONFIRMED — hub venue/dates match. In-progress pick left as published."},
    {"id": "CRK06", "official_url": "https://www.cricket.com.au/news/4425772/mark-your-calendar-2026-australia-cricket-schedule-fixtures-dates-tours-wtc-top-end-tests-south-africa-bangladesh-new-zealand-england-india-t20-world-cup",
     "evidence": "Cricket Australia (official): Australia Women ODIs v Bangladesh — Oct 9, Oct 11, Oct 14, Allan Border Field, Brisbane (D/N).",
     "outcome": "Fixtures CONFIRMED; hub 'Scheduled' status stale (window closed) and 3-0 outcome unverified -> status corrected, flagged."},
    {"id": "EL01/EL02", "official_url": "https://www.euroleaguebasketball.net/en/euroleague/news/the-2026-27-euroleague-schedule-is-official/",
     "evidence": "EuroLeague official: 'Round 7 on October 22 features both the first Turkish derby of the season, with Anadolu Efes facing Besiktas, and the first Serbian derby between Partizan and Crvena Zvezda.'",
     "outcome": "CONFIRMED — both hub fixtures upgraded from Olympics/Wikipedia to the official EuroLeague source; EL02 text artifact flagged separately."},
    {"id": "NHL01-NHL07", "official_url": "https://www.nhl.com/schedule/2026-10-20",
     "evidence": "NHL.com Oct 20 results: SJS 4 @ MTL 3 (OT); COL 3 @ NJD 4; ANA 2 @ NYI 3; TOR 6 @ CBJ 2; BOS 2 @ DAL 3 (OT). Oct 21 upcoming: PHI @ BUF and FLA @ OTT, 7:30 PM EDT.",
     "outcome": "CONFIRMED fixtures + results. ESPN sources replaced with NHL.com; lost picks (NHL01, NHL02, NHL04) and NHL06 handicap leg flagged; statuses corrected to Completed."},
    {"id": "RUG01/RUG02/RUG03/RUG04/RUG05/RUG06", "official_url": "https://www.world.rugby/beta/en/tournaments/nations-championship/2026",
     "evidence": "World Rugby Nations Championship 2026: Fri 6 Nov Ireland v Argentina (Aviva, Dublin); Sat 7 Nov Italy v South Africa (Allianz Stadium, Turin), Scotland v New Zealand (Murrayfield), Wales v Japan (Principality, Cardiff), France v Fiji (Groupama, Lyon); Sun 8 Nov England v Australia (Allianz Stadium, London). Per-match official pages linked per row.",
     "outcome": "CONFIRMED — all six hub fixtures upgraded from BBC/findmygroup to official World Rugby match pages; previously flagged RUG01/02/05/06 un-flagged on fixture evidence (form claims in prediction text not re-verified)."},
    {"id": "BDM02", "official_url": "https://bwfworldtour.bwfbadminton.com/tournament/5272/yonex-french-open-2026/overview",
     "evidence": "BWF World Tour official: YONEX French Open 2026, 20-25 October, Arena Grand Paris, prize money USD 950,000; An Se-young in women's singles field.",
     "outcome": "CONFIRMED — tournament/dates/venue/pick subject upgraded from Wikipedia to BWF official; un-flagged on fixture evidence."},
]

EXCLUDED = {"soccer", "football", "boxing", "ufc", "mma", "american football",
            "hurling", "horse racing", "cycling", "specials"}

def domain(url):
    return urllib.parse.urlparse(url or "").netloc.lower().removeprefix("www.")

def main():
    rows = json.loads(DATA.read_text())
    assert isinstance(rows, list) and rows, "matches.json must be a non-empty list"
    changed = []
    for r in rows:
        rid = r["id"]
        # 1) official upgrades proven today
        if rid in UPGRADES:
            url, name, _note = UPGRADES[rid]
            if r.get("sourceUrl") != url:
                r["sourceUrl"], r["sourceName"] = url, name
                r["verified"] = True
                # un-flag only where the previous flag was purely the non-official source
                if rid in ("EL01", "EL02", "RUG01", "RUG02", "RUG03", "RUG04", "RUG05", "RUG06", "BDM02", "NHL03", "NHL05", "NHL07"):
                    r["flagged"] = False
                    r["flagReason"] = None
                changed.append(f"{rid}: source upgraded to official {domain(url)}")
        # 2) status corrections proven today
        if rid in STATUS_FIX and r.get("status") != STATUS_FIX[rid]:
            r["status"] = STATUS_FIX[rid]
            changed.append(f"{rid}: status corrected")
        # 3) extra flags
        if rid in EXTRA_FLAGS:
            reason = f"{TAG}: {EXTRA_FLAGS[rid]}"
            if reason not in (r.get("flagReason") or ""):
                r["flagReason"] = ((r.get("flagReason") or "").rstrip() + " " + reason).strip()
                r["flagged"] = True
                changed.append(f"{rid}: extra flag added")
        # 4) downgrade verified-on-secondary (Board J F-01)
        d = domain(r.get("sourceUrl"))
        if r.get("verified") and d not in OFFICIAL:
            r["verified"] = False
            r["flagged"] = True
            reason = (f"{TAG}: source domain '{d}' is not an official governing-body/league/tour site; "
                      "fixture not re-confirmed on an official site in this pass — marked unverified, kept with its source link for manual review. No values inferred.")
            if reason not in (r.get("flagReason") or ""):
                r["flagReason"] = ((r.get("flagReason") or "").rstrip() + " " + reason).strip()
            changed.append(f"{rid}: downgraded verified (secondary source {d})")

    DATA.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n")

    # ---- audit (on the corrected data) ----
    audit_rows, highs, seen_pred = [], [], {}
    dup_pred = []
    for r in rows:
        d = domain(r.get("sourceUrl"))
        words = len((r.get("prediction") or "").split())
        if r.get("confidence") == "High":
            highs.append(r["id"])
            key = re.sub(r"\s+", " ", (r.get("prediction") or "").strip().lower())
            if key in seen_pred:
                dup_pred.append([seen_pred[key], r["id"]])
            seen_pred[key] = r["id"]
        audit_rows.append({
            "id": r["id"], "sport": r.get("sport"), "date": r.get("date"),
            "match": r.get("match"), "confidence": r.get("confidence"),
            "source_domain": d, "source_class": "official" if d in OFFICIAL else "secondary",
            "sourceUrl": r.get("sourceUrl"), "verified": bool(r.get("verified")),
            "flagged": bool(r.get("flagged")), "flagReason": r.get("flagReason"),
            "prediction_words": words if r.get("confidence") == "High" else None,
            "status": r.get("status"), "pick": r.get("pick"),
        })
    excluded_hits = [r["id"] for r in rows
                     if (r.get("sport") or "").strip().lower() in EXCLUDED
                     or (r.get("category") or "").strip().lower() in EXCLUDED]
    high_word_fail = [r["id"] for r in audit_rows
                      if r["confidence"] == "High" and (r["prediction_words"] or 0) < 30]
    audit = {
        "board": "K", "session": "arena/093bfd5e-olbg4", "cut_off": CUT,
        "scope": "Root hub data/matches.json only (Board D dataset). Other builds untouched.",
        "changes_applied": changed,
        "spot_checks": SPOT_CHECKS,
        "summary": {
            "rows": len(rows),
            "official_source_rows": sum(1 for r in audit_rows if r["source_class"] == "official"),
            "secondary_source_rows": sum(1 for r in audit_rows if r["source_class"] == "secondary"),
            "verified_rows": sum(1 for r in audit_rows if r["verified"] and not r["flagged"]),
            "flagged_rows": sum(1 for r in audit_rows if r["flagged"] or not r["verified"]),
            "high_confidence": len(highs),
            "high_prediction_min_words": min((r["prediction_words"] for r in audit_rows if r["confidence"] == "High"), default=0),
            "high_prediction_word_failures": high_word_fail,
            "duplicate_high_predictions": dup_pred,
            "excluded_sport_rows": excluded_hits,
            "by_confidence": dict(collections.Counter(r["confidence"] for r in audit_rows)),
        },
        "rows": audit_rows,
        "irregularities": [
            "F-01 (Board J) fixed for the hub: every row still marked verified now sits on an official domain, or was downgraded to unverified+flagged with its link kept.",
            "NHL01/NHL02/NHL04 high/medium picks had already lost on 2026-10-20 (NHL.com results) while the hub still showed 'Scheduled' — statuses corrected, picks flagged as settled/lost, nothing deleted.",
            "NHL06 moneyline won in OT but the originated -1.5 puck line could not cover a 1-goal OT game — handicap leg flagged.",
            "NBA01-NBA03 (Oct 20) and CRK06 (Oct 9-14) were still labelled 'Scheduled' after their dates passed — flagged; results not re-verified in this pass, so no outcome is asserted.",
            "EL02 and NHL04 prediction texts contain editorial artifacts ('Actually…', 'Verify tip via…') — flagged verbatim, not rewritten, so the user can see the original defect.",
            "Rows downgraded in this pass keep their original (secondary) source link for manual review; per brief they stay published on Flagged for Review and do not block merge.",
            "This pass re-checked fixtures/results only. Form/history claims inside prediction texts were NOT re-verified except where an official page fetched today happened to state them, and are not asserted as verified here.",
        ],
        "method_note": "Originated lines/picks in data/matches.json are the hub build's own model outputs (see methodology.html); Board K did not re-originate or alter any line, pick or prediction text.",
    }
    OUT.write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n")
    print(f"rows={len(rows)} changed={len(changed)}")
    for c in changed: print(" -", c)
    print(json.dumps(audit["summary"], indent=1))

if __name__ == "__main__":
    main()
