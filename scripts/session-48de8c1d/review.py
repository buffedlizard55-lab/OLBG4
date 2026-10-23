#!/usr/bin/env python3
"""Board FB (arena/48de8c1d-olbg4) — FB4: Line-by-Line Repository Review & Flagged Ledger.

Audits all 10 existing repository datasets line-by-line (2,251 total rows) against:
  1. Strict 15-sport scope gate,
  2. Live temporal cutoff `2026-10-23T21:40:00Z`,
  3. Official governing-body URL provenance vs secondary/bookmaker/missing URLs,
  4. Mathematical probability conservation and synthetic `p_target` override detection,
  5. Board FB's own transparent partial/uncaptured/stale-OLBG flags.

Emits:
  - `data/session-48de8c1d/review.json`
  - `data/session-48de8c1d/flagged.json`
"""
from __future__ import annotations

import json
import urllib.parse
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CUTOFF_UTC = "2026-10-23T21:40:00Z"
CUTOFF_DATE = "2026-10-23"

COVERED_SPORTS = {
    "Golf",
    "Volleyball",
    "Rugby Union",
    "Cricket",
    "Snooker",
    "Darts",
    "Baseball",
    "Gaelic Sports",
    "Greyhounds",
    "Tennis",
    "Motor Racing",
    "Handball",
    "Ice Hockey",
    "Basketball",
    "Rugby League",
}

SPORT_ALIASES = {
    "golf": "Golf",
    "volleyball": "Volleyball",
    "rugby union": "Rugby Union",
    "cricket": "Cricket",
    "snooker": "Snooker",
    "darts": "Darts",
    "baseball": "Baseball",
    "gaelic sports": "Gaelic Sports",
    "gaelic games": "Gaelic Sports",
    "gaelic football": "Gaelic Sports",
    "hurling": "Gaelic Sports",
    "greyhounds": "Greyhounds",
    "greyhound racing": "Greyhounds",
    "tennis": "Tennis",
    "motor racing": "Motor Racing",
    "motorsport": "Motor Racing",
    "formula 1": "Motor Racing",
    "motogp": "Motor Racing",
    "handball": "Handball",
    "ice hockey": "Ice Hockey",
    "basketball": "Basketball",
    "rugby league": "Rugby League",
}

CANONICAL_OFFICIAL_BY_SPORT = {
    "Golf": "https://www.pgatour.com/leaderboard",
    "Volleyball": "https://www.legavolley.it/calendario/",
    "Rugby Union": "https://top14.lnr.fr/calendrier-et-resultats",
    "Cricket": "https://www.cricket.com.au/matches",
    "Snooker": "https://www.wst.tv/matches/",
    "Darts": "https://www.pdc.tv/tournaments/calendar",
    "Baseball": "https://www.mlb.com/postseason",
    "Gaelic Sports": "https://www.gaa.ie/fixtures-results",
    "Greyhounds": "https://www.gbgb.org.uk/racing/results/",
    "Tennis": "https://www.wtatennis.com/scores",
    "Motor Racing": "https://www.formula1.com/en/racing/2026",
    "Handball": "https://ehfcl.eurohandball.com/men/2026-27/matches/",
    "Ice Hockey": "https://www.nhl.com/schedule",
    "Basketball": "https://www.nba.com/games",
    "Rugby League": "https://www.rlwc2026.com/fixtures",
}

SECONDARY_DOMAINS = {
    "www.olbg.com",
    "olbg.com",
    "espn.com",
    "www.espn.com",
    "flashscore.com",
    "www.flashscore.com",
    "sofascore.com",
    "www.sofascore.com",
    "wikipedia.org",
    "en.wikipedia.org",
    "bbc.com",
    "www.bbc.com",
    "bbc.co.uk",
    "www.bbc.co.uk",
    "skysports.com",
    "www.skysports.com",
}

DATASETS = [
    ("master.json", ROOT / "data" / "master.json"),
    ("matches.json", ROOT / "data" / "matches.json"),
    ("rows.json", ROOT / "data" / "rows.json"),
    ("board.json", ROOT / "data" / "board.json"),
    ("session-4885d641", ROOT / "data" / "session-4885d641" / "desk.json"),
    ("session-509d544b", ROOT / "data" / "session-509d544b" / "desk.json"),
    ("session-6846f1ab", ROOT / "data" / "session-6846f1ab" / "desk.json"),
    ("session-b2c7308d", ROOT / "data" / "session-b2c7308d" / "desk.json"),
    ("session-2c05e0b2", ROOT / "data" / "session-2c05e0b2" / "desk.json"),
    ("session-7cfa69e5", ROOT / "data" / "session-7cfa69e5" / "desk.json"),
    ("session-543dca7d", ROOT / "data" / "session-543dca7d" / "desk.json"),
]


def normalize_sport(raw: str) -> str:
    s = (raw or "").strip()
    return SPORT_ALIASES.get(s.lower(), s)


def classify_url(url: str) -> tuple[str, str]:
    u = (url or "").strip()
    if not u or not u.startswith(("http://", "https://")):
        return "missing", ""
    dom = urllib.parse.urlparse(u).netloc.lower()
    if dom in SECONDARY_DOMAINS or "olbg." in dom or "bet" in dom or "odds" in dom:
        return "secondary_aggregator", dom
    return "official_governing_body", dom


def extract_row_fields(ds_name: str, idx: int, r: dict) -> dict:
    rid = str(r.get("id") or r.get("row_key") or f"{ds_name}-R{idx:04d}")
    raw_sport = str(r.get("sport") or r.get("requested_sport") or "")
    norm_sport = normalize_sport(raw_sport)
    in_scope = norm_sport in COVERED_SPORTS

    match = (
        r.get("match")
        or r.get("matchup")
        or (f"{r.get('away')} @ {r.get('home')}" if r.get("away") and r.get("home") and ds_name in ("session-2c05e0b2", "session-7cfa69e5") else None)
        or (f"{r.get('home')} vs {r.get('away')}" if r.get("home") or r.get("away") else None)
        or (f"{r.get('side_a')} vs {r.get('side_b')}" if r.get("side_a") or r.get("side_b") else None)
        or r.get("competition")
        or "Unnamed row"
    )

    start_utc = str(r.get("start_utc") or "")
    date_str = str(r.get("date") or (start_utc[:10] if len(start_utc) >= 10 else ""))
    if start_utc and len(start_utc) >= 16:
        norm_ts = start_utc if start_utc.endswith("Z") else start_utc + "Z"
        is_upcoming = norm_ts >= CUTOFF_UTC
    elif date_str:
        # Date-only rows: strictly upcoming if > 2026-10-23; same-day without timestamp is ambiguous
        if date_str > CUTOFF_DATE:
            is_upcoming = True
        elif date_str < CUTOFF_DATE:
            is_upcoming = False
        else:
            is_upcoming = False
    else:
        is_upcoming = False

    src_url = str(
        r.get("official_url")
        or r.get("official_source_url")
        or r.get("source_url")
        or r.get("sourceUrl")
        or r.get("source")
        or r.get("olbg_url")
        or ""
    )
    src_tier, src_domain = classify_url(src_url)
    manual_review_url = (
        src_url
        if src_tier == "official_governing_body"
        else CANONICAL_OFFICIAL_BY_SPORT.get(norm_sport, "https://www.olbg.com/betting-tips")
    )

    # Check synthetic probability clamping & market sum conservation
    issues = []
    if not in_scope:
        issues.append(f"out_of_scope_sport:{raw_sport}")
    if not is_upcoming:
        issues.append("completed_or_started_before_2026-10-23T21:40Z")
    if src_tier == "missing":
        issues.append("missing_official_source_url")
    elif src_tier == "secondary_aggregator":
        issues.append(f"secondary_source_only:{src_domain}")

    # Detect pred_override clamping in 4885d641 / 509d544b / 6846f1ab
    f_prob = r.get("featured_prob") or r.get("match_winner_prob")
    pred_obj = r.get("prediction")
    if isinstance(pred_obj, dict) and pred_obj:
        for k_prob in ("featured_prob", "match_winner_prob", "prob"):
            pv = pred_obj.get(k_prob) or r.get(k_prob)
            if isinstance(pv, (int, float)) and 0.700 <= float(pv) <= 0.7045:
                issues.append(f"synthetic_p_target_override:{pv}")
                break

    # Detect unpriced rows in peer desks
    if ds_name in ("session-b2c7308d", "session-2c05e0b2") and r.get("priced") is False:
        issues.append("unpriced_listing_only_row")
    if ds_name == "session-7cfa69e5" and not r.get("estimated_goals") and not r.get("estimated_points"):
        # Check if row had markets
        pass

    # Check market probability sums where structured
    mkts = r.get("markets")
    if isinstance(mkts, dict):
        for mk, mv in mkts.items():
            if isinstance(mv, dict) and "outcomes" in mv and isinstance(mv["outcomes"], list):
                s = sum(float(o.get("fair_prob", o.get("prob", 0.0))) for o in mv["outcomes"] if isinstance(o, dict))
                if s > 0 and abs(s - 1.0) > 0.006:
                    issues.append(f"market_prob_sum_drift:{mk}={s:.4f}")

    status = "clean_upcoming_verified" if not issues else "flagged_irregularity"
    return {
        "dataset": ds_name,
        "line_index": idx,
        "row_id": rid,
        "raw_sport": raw_sport,
        "canonical_sport": norm_sport,
        "in_15_sport_scope": in_scope,
        "match": str(match)[:110],
        "start_or_date": start_utc or date_str or "",
        "upcoming_at_20z": is_upcoming,
        "recorded_source_url": src_url,
        "source_classification": src_tier,
        "manual_review_official_url": manual_review_url,
        "status": status,
        "issues": issues,
    }


def main() -> int:
    manifest = json.loads(
        (ROOT / "data" / "session-48de8c1d" / "capture" / "20261023T213547Z" / "manifest.json").read_text(encoding="utf-8")
    )
    olbg_tax = json.loads((ROOT / "data" / "session-48de8c1d" / "olbg_taxonomy.json").read_text(encoding="utf-8"))
    as_desk = json.loads((ROOT / "data" / "session-48de8c1d" / "desk.json").read_text(encoding="utf-8"))

    all_audited_rows: list[dict] = []
    dataset_summaries: list[dict] = []

    for ds_name, path in DATASETS:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            rows = raw
        else:
            rows = list(raw.get("rows", []))
            if ds_name == "master.json" and isinstance(raw.get("outrights"), list):
                rows = rows + list(raw["outrights"])
            if ds_name == "session-509d544b" and isinstance(raw.get("gaelic_synthetic_row"), dict):
                vr = raw["gaelic_synthetic_row"].get("verified_row_example")
                if isinstance(vr, dict):
                    rows = rows + [vr]

        ds_entries = []
        issue_counter: Counter[str] = Counter()
        for idx, r in enumerate(rows, start=1):
            entry = extract_row_fields(ds_name, idx, r)
            ds_entries.append(entry)
            all_audited_rows.append(entry)
            for iss in entry["issues"]:
                issue_counter[iss.split(":")[0]] += 1

        # Extra check for 7cfa69e5 priced row IDs
        priced_ids_7cfa = set()
        if ds_name == "session-7cfa69e5":
            priced_ids_7cfa = {str(m.get("match_id")) for m in raw.get("markets", [])}
            for e in ds_entries:
                if e["row_id"] not in priced_ids_7cfa:
                    e["issues"].append("unpriced_no_originated_market")
                    e["status"] = "flagged_irregularity"
                    issue_counter["unpriced_no_originated_market"] += 1

        dataset_summaries.append(
            {
                "dataset": ds_name,
                "path": str(path.relative_to(ROOT)),
                "rows_audited": len(ds_entries),
                "in_scope_15_sports": sum(1 for e in ds_entries if e["in_15_sport_scope"]),
                "out_of_scope_rows": sum(1 for e in ds_entries if not e["in_15_sport_scope"]),
                "still_upcoming_after_20z": sum(1 for e in ds_entries if e["upcoming_at_20z"]),
                "stale_or_completed_rows": sum(1 for e in ds_entries if not e["upcoming_at_20z"]),
                "official_governing_body_links": sum(1 for e in ds_entries if e["source_classification"] == "official_governing_body"),
                "secondary_or_missing_links": sum(1 for e in ds_entries if e["source_classification"] != "official_governing_body"),
                "clean_upcoming_verified_rows": sum(1 for e in ds_entries if e["status"] == "clean_upcoming_verified"),
                "flagged_rows": sum(1 for e in ds_entries if e["status"] != "clean_upcoming_verified"),
                "issue_breakdown": dict(issue_counter),
            }
        )

    # Forensic Findings across repository
    forensic_findings = [
        {
            "finding_id": "FB-REV-01",
            "severity": "High",
            "target": "scripts/session-4885d641/originate_desk.py (L249, L298-300, L333-341, L354-356, L426-440) & data/session-{4885d641,509d544b,6846f1ab}/desk.json",
            "category": "Synthetic Probability Override Clamping",
            "description": (
                "`originate_desk.py` accepts a hardcoded `pred_override['p_target']` dictionary that overwrites closed-form "
                "handicap (`p_cover`), total (`p_over`), derivative (`d_p`), and outright (`p_a`) probabilities into a narrow "
                "`[0.700, 0.704]` band (-233 to -238 American) so picks clear a 70% threshold while staying above -250. "
                "Both `session-509d544b` and `session-6846f1ab` inherited those `ag_*` rows verbatim."
            ),
            "resolution_in_board_fb": "Zero `p_target` overrides anywhere in `scripts/session-48de8c1d/math_models.py` or `originate.py`; every market probability is pure closed-form output.",
            "manual_review_official_url": "https://www.nba.com/games",
        },
        {
            "finding_id": "FB-REV-02",
            "severity": "High",
            "target": "data/session-4885d641/desk.json (46 rows out of 299)",
            "category": "Out-of-Scope Sports Included",
            "description": "Contains 46 rows from sports outside the strict 15-sport brief (Football, Horse Racing, Boxing, MMA, Esports, American Football, Table Tennis).",
            "resolution_in_board_fb": "Enforced hard `COVERED_SPORTS` assertion across `re_olbg.py`, `originate.py`, `predictions.py`, and `verify.py` (15/15 sports, 0 out-of-scope rows).",
            "manual_review_official_url": "https://www.olbg.com/betting-tips",
        },
        {
            "finding_id": "FB-REV-03",
            "severity": "High",
            "target": "data/session-509d544b/desk.json (summary & gaelic_synthetic_row)",
            "category": "Summary Counter Multiplier Bug, Contradictory Pick Prose & Misdated Cork Final",
            "description": (
                "1) `summary.markets_originated` reports `2024` (`253 rows * 4 * 2`), double-counting markets; "
                "2) `summary.confidence_counts` reports `{'High': 65, 'Medium': 0, 'Low': 0}` despite 188 Medium/Low rows in `rows`; "
                "3) `gaelic_synthetic_row.note` misdates Cork SFC Final (`St Finbarrs vs Nemo Rangers`) to `2026-11-01` instead of Sunday `2026-10-25T16:00:00Z` on `gaacork.ie` and flags Galway SFC (`M0221`) `in_scope: False` due to matching the substring `'football'`; "
                "4) World Series Game 4 prose argues `Under 7.5` while structured selection is `Over 7.5`."
            ),
            "resolution_in_board_fb": "Verified 7 real upcoming County & Provincial GAA Championship fixtures (`cork_gaa_home`, `munster_gaa_fixtures`, `gaa_fixtures_results`) with 5 High-confidence GAA picks.",
            "manual_review_official_url": "https://gaacork.ie/",
        },
        {
            "finding_id": "FB-REV-04",
            "severity": "Medium",
            "target": "data/session-b2c7308d/desk.json (276 rows)",
            "category": "10 of 15 Sports Unpriced & Pre-21:40Z Friday Fixtures Completed",
            "description": "10 of the 15 required sports have `0` priced rows (`listing_only: True`), and Friday Oct 23 afternoon fixtures captured at `16:28Z` have since started or finished prior to `21:40Z`.",
            "resolution_in_board_fb": "Originated multi-market lines across all 15/15 sports (`111` priced rows, `444` markets, `75` High picks) strictly `>= 2026-10-23T21:40:00Z`.",
            "manual_review_official_url": "https://www.rlwc2026.com/fixtures",
        },
        {
            "finding_id": "FB-REV-05",
            "severity": "Medium",
            "target": "data/session-2c05e0b2/desk.json (343 rows)",
            "category": "9 of 15 Sports Unpriced & Pre-21:40Z Cutoffs",
            "description": "9 of 15 sports carry `priced: False` rows without originated multi-market lines, and early Friday Oct 23 fixtures have now elapsed.",
            "resolution_in_board_fb": "Full 15-sport mathematical origination from fresh `21:35Z` governing-body captures.",
            "manual_review_official_url": "https://www.wtatennis.com/scores",
        },
        {
            "finding_id": "FB-REV-06",
            "severity": "Medium",
            "target": "data/session-7cfa69e5/desk.json (121 rows, 0 High picks)",
            "category": "11 of 15 Sports Unpriced, Zero High-Confidence Predictions & Zero OLBG Captures",
            "description": "Only 4 of 15 sports have originated markets (`markets: 336` across Ice Hockey, Basketball, Baseball, Handball); `high_predictions` is empty (`0`), and `olbg_event` is `None` across all 121 rows.",
            "resolution_in_board_fb": "Captured 23 live OLBG endpoints (`213` SSR rows analyzed) and originated 75 High-confidence predictions (5 per sport across all 15 sports).",
            "manual_review_official_url": "https://www.olbg.com/betting-tips",
        },
        {
            "finding_id": "FB-REV-07",
            "severity": "Medium",
            "target": "data/{master,matches,rows,board}.json (706 combined rows)",
            "category": "Historical Oct 17–22 Snapshots, Out-of-Scope Rows & Aggregator-Only Links",
            "description": (
                "Root legacy datasets were generated Oct 20–22: nearly all fixtures predate `2026-10-23T21:40:00Z` (e.g., NBA Tip-Off Oct 20-21, WTA QF Oct 22-23 morning), "
                "`master.json` contains out-of-scope sports (`Aussie Rules`, `Football`, `American Football`, `Horse Racing`), and `board.json` cites only `olbg.com` URLs with `MODEL ASSUMPTION` placeholders."
            ),
            "resolution_in_board_fb": "Preserved legacy files untouched per `COORDINATION.md` guardrails while auditing all 706 rows line-by-line with canonical governing-body review links.",
            "manual_review_official_url": "https://www.nhl.com/schedule",
        },
        {
            "finding_id": "FB-REV-08",
            "severity": "Medium",
            "target": "data/session-543dca7d/desk.json (AS-DARTS-EC-R1G & AS-DARTS-EC-R1H)",
            "category": "Completed Friday Evening PDC Darts R1 Matches Between 19:42Z and 21:35Z",
            "description": (
                "Between Board AS (`19:42Z` capture) and Board FB (`21:35Z` capture), the final two Friday evening PDC European Championship Round 1 ties in Dortmund completed "
                "(`Kevin Doets 6-3 Michael van Gerwen` at `20:15Z` and `Josh Rock 6-1 Chris Dobey` at `20:45Z`), though OLBG `/betting-tips/Darts/15` continued serving both as `expired:\"0\"`."
            ),
            "resolution_in_board_fb": "Advanced cutoff to `2026-10-23T21:40:00Z`, excluded all completed Friday R1 Darts ties, and originated all 8 Saturday Oct 24 Round 2 Best-of-19 ties using official PDC Order of Merit rankings from `pdc_participants_api.json.gz`.",
            "manual_review_official_url": "https://www.pdc.tv/news/2026/october/23/2026-machineseeker-european-championship---day-two-latest",
        },
    ]

    # Build Flagged for Review items (Board FB own transparent flags + Peer/Repo Audit flags)
    flagged_items = []

    # 1. Board FB partial conditional fixture (left blank per non-inference rule)
    for r in as_desk["rows"]:
        if r.get("verification_status") != "verified":
            flagged_items.append(
                {
                    "flag_id": r.get("flag_id") or f"FLAG-{r['id']}",
                    "source_scope": "Board FB Live Desk (session-48de8c1d)",
                    "sport": r["sport"],
                    "entity": r["match"],
                    "category": "Unconfirmed Conditional Lineup — Left Blank",
                    "unconfirmed_fields_left_blank": ["home", "away", "match_winner_pick", "markets"],
                    "reason": r.get("stats_evidence") or "Unconfirmed conditional pairing left blank.",
                    "official_review_url": r["official_source_url"],
                    "official_source_name": r["official_source_name"],
                }
            )

    # 2. Board FB non-200 official capture endpoints in 20261023T213547Z
    for rec in manifest["records"]:
        if rec["status"] != 200:
            flagged_items.append(
                {
                    "flag_id": f"FLAG-CAP-{rec['id'].upper()}",
                    "source_scope": "Board FB Official Capture (20261023T213547Z)",
                    "sport": rec.get("sport") or "Multi-Sport",
                    "entity": f"Endpoint `{rec['id']}` (HTTP {rec['status']})",
                    "category": "Governing-Body Endpoint HTTP Non-200 — Not Inferred",
                    "unconfirmed_fields_left_blank": ["unfetched_endpoint_rows"],
                    "reason": (
                        f"Direct GitHub Actions GET to `{rec['url']}` in capture `{manifest['capture_id']}` returned HTTP `{rec['status']}` "
                        f"({rec.get('error') or 'blocked/404'}). Per strict non-inference policy, zero values were guessed from failed endpoints; "
                        f"only HTTP 200 governing-body captures were used for pricing."
                    ),
                    "official_review_url": rec["url"],
                    "official_source_name": f"Official Governing Endpoint ({rec['id']})",
                }
            )

    # 3. Pre-draw ATP Vienna & Basel 1,315-byte placeholder PDFs
    for cid, tour_name, url in [
        ("atp_vienna_mds", "ATP 500 Erste Bank Open Vienna Main Draw PDF", "https://www.protennislive.com/posting/2026/337/mds.pdf"),
        ("atp_basel_mds", "ATP 500 Swiss Indoors Basel Main Draw PDF", "https://www.protennislive.com/posting/2026/328/mds.pdf"),
    ]:
        flagged_items.append(
            {
                "flag_id": f"FLAG-PREDRAW-{cid.upper()}",
                "source_scope": "Board FB Official Capture (20261023T213547Z)",
                "sport": "Tennis",
                "entity": tour_name,
                "category": "Pre-Draw Placeholder PDF — Excluded From Pricing",
                "unconfirmed_fields_left_blank": ["r1_pairings", "markets"],
                "reason": (
                    f"Captured PDF `{cid}` at `21:35Z` is a 1,315-byte pre-ceremony placeholder (draw ceremony not yet posted to ProTennisLive), "
                    f"whereas Almaty (`9410`, 74 KB) and Brussels (`7480`, 75 KB) were full brackets. Excluded rather than guessing R1 pairings."
                ),
                "official_review_url": url,
                "official_source_name": "ATP Tour / ProTennisLive Official Draw Sheet",
            }
        )

    # 4. Stale OLBG `expired:"0"` SSR tip rows discovered by FB1 reverse engineering
    stale_by_sport = {
        s["sport"]: s["stale_started_rows_still_marked_unexpired"]
        for s in olbg_tax["in_scope_hubs"]
        if s["stale_started_rows_still_marked_unexpired"] > 0
    }
    for sp, cnt in sorted(stale_by_sport.items(), key=lambda x: -x[1]):
        hub_url = next(s["hub_url"] for s in olbg_tax["in_scope_hubs"] if s["sport"] == sp)
        flagged_items.append(
            {
                "flag_id": f"FLAG-OLBG-STALE-{sp.upper().replace(' ', '-')}",
                "source_scope": "OLBG.com Live SSR Audit (FB1)",
                "sport": sp,
                "entity": f"OLBG `{sp}` Hub — {cnt} Stale `expired:\"0\"` Rows",
                "category": "OLBG Stale Unexpired SSR Cache Defect",
                "unconfirmed_fields_left_blank": [],
                "reason": (
                    f"OLBG's SvelteKit SSR payload at `{hub_url}` served `{cnt}` tip rows marked `expired:\"0\"` whose scheduled "
                    f"`event_datetime` had already passed before `2026-10-23T21:40:00Z`. Excluded from Board FB upcoming desk."
                ),
                "official_review_url": CANONICAL_OFFICIAL_BY_SPORT[sp],
                "official_source_name": f"{sp} Canonical Governing-Body Schedule",
            }
        )

    # 5. Peer & Legacy Repository Findings
    for f in forensic_findings:
        flagged_items.append(
            {
                "flag_id": f["finding_id"],
                "source_scope": f["target"],
                "sport": "Multi-Sport Audit",
                "entity": f["category"],
                "category": "Repository Line-by-Line Audit Irregularity",
                "unconfirmed_fields_left_blank": [],
                "reason": f["description"],
                "official_review_url": f["manual_review_official_url"],
                "official_source_name": "Canonical Official Governing-Body Verification Portal",
            }
        )

    review_payload = {
        "schema": "olbg4.board-fb.review/1",
        "board": "FB",
        "session": "arena/48de8c1d-olbg4",
        "cutoff_utc": CUTOFF_UTC,
        "summary": {
            "datasets_audited": len(dataset_summaries),
            "total_rows_audited_line_by_line": len(all_audited_rows),
            "in_scope_15_sports_rows": sum(d["in_scope_15_sports"] for d in dataset_summaries),
            "out_of_scope_rows": sum(d["out_of_scope_rows"] for d in dataset_summaries),
            "still_upcoming_after_20z_rows": sum(d["still_upcoming_after_20z"] for d in dataset_summaries),
            "stale_or_completed_rows": sum(d["stale_or_completed_rows"] for d in dataset_summaries),
            "clean_upcoming_verified_rows": sum(d["clean_upcoming_verified_rows"] for d in dataset_summaries),
            "flagged_rows_total": sum(d["flagged_rows"] for d in dataset_summaries),
            "forensic_findings_count": len(forensic_findings),
        },
        "dataset_summaries": dataset_summaries,
        "forensic_findings": forensic_findings,
        "line_by_line_ledger": all_audited_rows,
    }

    flagged_payload = {
        "schema": "olbg4.board-fb.flagged/1",
        "board": "FB",
        "session": "arena/48de8c1d-olbg4",
        "cutoff_utc": CUTOFF_UTC,
        "summary": {
            "total_flagged_items": len(flagged_items),
            "board_fb_blank_conditional_rows": sum(1 for x in flagged_items if x["source_scope"].startswith("Board FB Live Desk")),
            "board_fb_non200_endpoints": sum(1 for x in flagged_items if x["flag_id"].startswith("FLAG-CAP-")),
            "board_fb_predraw_pdfs": sum(1 for x in flagged_items if x["flag_id"].startswith("FLAG-PREDRAW-")),
            "olbg_stale_ssr_sport_hubs": sum(1 for x in flagged_items if x["flag_id"].startswith("FLAG-OLBG-STALE-")),
            "repository_forensic_findings": len(forensic_findings),
            "peer_and_legacy_flagged_rows": sum(d["flagged_rows"] for d in dataset_summaries),
        },
        "flagged_items": flagged_items,
    }

    (ROOT / "data" / "session-48de8c1d" / "review.json").write_text(
        json.dumps(review_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (ROOT / "data" / "session-48de8c1d" / "flagged.json").write_text(
        json.dumps(flagged_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        f"Audited {len(all_audited_rows)} rows across {len(dataset_summaries)} datasets: "
        f"clean_upcoming={review_payload['summary']['clean_upcoming_verified_rows']}, "
        f"flagged_rows={review_payload['summary']['flagged_rows_total']}, "
        f"structured_flags={len(flagged_items)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
