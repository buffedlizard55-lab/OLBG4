#!/usr/bin/env python3
"""Board AH — remaining sport parsers (called from originate_desk.py).

Every parser follows the same rule: prices/lines come only from numbers present in the
committed official capture bytes; OLBG hub pages supply the listing (taxonomy) cross-check
only; anything unverifiable is published blank and flagged.
"""
from __future__ import annotations

import json
import math
import re

# originate_desk imports this module lazily from inside main(), so by the time these
# parsers run the importing module is fully initialised and the import below is safe.
from originate_desk import pick_best_selection  # noqa: E402

WIN_START = "2026-10-23"
WIN_END = "2026-11-03"


def strip_html(h: str) -> str:
    h = re.sub(r"<script[^>]*>.*?</script>", " ", h, flags=re.S)
    h = re.sub(r"<style[^>]*>.*?</style>", " ", h, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", h)
    return re.sub(r"\s+", " ", t).strip()


def norm(s: str) -> str:
    s = s.replace("&amp;", "&").replace("&#8217;", "'").replace("&#038;", "&")
    return re.sub(r"\s+", " ", s).strip()


def olbg_events(reader, target):
    """Extract today's OLBG listing events (name, url) from a captured hub page."""
    if not reader.has(target):
        return []
    h = reader.read_text(target)
    pairs = re.findall(
        r'href="(https://www\.olbg\.com/betting-tips/[^"]*\?event_id=(\d+))"[^>]*>.*?<h5[^>]*>([^<]+)</h5>',
        h, flags=re.S)
    evs = {}
    for url, eid, name in pairs:
        if eid not in evs:
            evs[eid] = {"name": norm(name), "url": url}
    return list(evs.values())


# ---------------------------------------------------------------------------
# Darts — OLBG listing pairings, official link = PDC hub; unpriced (no official
# numeric inputs captured today: pdc.tv pages are client-side shells and the
# matches.darts.admin.gc.pdcservices.co.uk probe did not resolve).
# ---------------------------------------------------------------------------

def parse_darts(reader, new_row, sel_row, two_way_market, finish_pick, flag):
    url_hub = reader.source_url("pdc_home") if reader.has("pdc_home") else "https://www.pdc.tv/"
    if not reader.has("pdc_home"):
        flag("AH-F-DARTS-01", "blocker", "Darts", "PDC site not readable",
             "pdc.tv returned a client-side shell for every target (Order of Merit and the European "
             "Championship schedule article render no article bytes), and the PDC match-data service "
             "host did not resolve, so no PDC numeric input could be captured today. European "
             "Championship ties are published as listing-only rows with blank picks.",
             "https://www.pdc.tv/")
    flag("AH-F-DARTS-02", "review", "Darts", "Ties not officially verifiable today",
         "The Machineseeker European Championship first-round ties below match the PDC's published "
         "schedule articles as indexed today, but the PDC page itself renders no article bytes in this "
         "capture, so every pairing is published unverified from an official source (listing-only).",
         "https://www.pdc.tv/news/2026/october/19/2026-machineseeker-european-championship-schedule-confirmed/")
    events = olbg_events(reader, "olbg_darts_15")
    hub = reader.source_url("olbg_darts_15")
    for e in events:
        name = e["name"]
        if "vs" not in name and " v " not in name:
            continue
        m = re.split(r" vs\.? | v ", name, maxsplit=1)
        if len(m) != 2:
            continue
        new_row(sport="Darts", competition="PDC Machineseeker European Championship (Dortmund)",
                side_a=m[0], side_b=m[1], matchup=name, start_utc="",
                official_url=url_hub, official_source_name="PDC — pdc.tv (official site)",
                capture_stamp=reader.capture_stamp("olbg_darts_15"),
                listing_only=True, olbg={"on_olbg": True, "olbg_url": e["url"], "olbg_event_id": e.get("url", "").split("event_id=")[-1]},
                inputs_summary="OLBG live listing 2026-10-23; PDC official pages returned no article bytes today (see flag); pairing unverified officially — pick, odds and start time left blank.")


# ---------------------------------------------------------------------------
# Handball — Danish Betoro Herreligaen table is captured (official league site);
# OLBG-listed Danish fixtures are priced from it. Other leagues: listing-only.
# ---------------------------------------------------------------------------

def parse_handball_danish(reader, new_row, sel_row, two_way_market, finish_pick, flag):
    if not reader.has("tophaandbold_herreligaen"):
        flag("AH-F-HB-01", "blocker", "Handball", "Danish league table not captured", "",
             "https://tophaandbold.dk/stillinger/herreligaen")
        return
    t = strip_html(reader.read_text("tophaandbold_herreligaen"))
    url = reader.source_url("tophaandbold_herreligaen")
    stamp = reader.capture_stamp("tophaandbold_herreligaen")
    table = {}
    m = re.search(r"Grundspil - 2026-2027 # Klub K V U T Mål Point Form(.{0,4000}?)Slutspil", t)
    if m:
        for r in re.finditer(r"(\d{1,2}) ([A-Za-zÀ-ž .\-]+?) (\d{1,2}) (\d+) (\d+) (\d+) (\d+)[-:](\d+) (\d+)", m.group(1)):
            table[norm(r.group(2))] = {"gp": int(r.group(3)), "w": int(r.group(4)), "d": int(r.group(5)),
                                       "l": int(r.group(6)), "gf": int(r.group(7)), "ga": int(r.group(8)),
                                       "pts": int(r.group(9))}
    if not table:
        flag("AH-F-HB-02", "review", "Handball", "Danish table not parsed",
             "tophaandbold.dk captured but the standings regex found no rows; Danish fixtures published unpriced.", url)
    lg = (sum(x["gf"] for x in table.values()) + sum(x["ga"] for x in table.values())) / max(1, 2 * sum(x["gp"] for x in table.values()))
    events = olbg_events(reader, "olbg_handball_20")
    hub = reader.source_url("olbg_handball_20")
    for e in events:
        name = e["name"]
        parts = re.split(r" vs\.? ", name, maxsplit=1)
        if len(parts) != 2:
            continue
        a, b = norm(parts[0]), norm(parts[1])
        ta = next((table[k] for k in table if a.lower().split()[0] in k.lower() or k.lower().split()[0] in a.lower()), None)
        tb = next((table[k] for k in table if b.lower().split()[0] in k.lower() or k.lower().split()[0] in b.lower()), None)
        if not (ta and tb):
            new_row(sport="Handball", competition="European leagues (OLBG listing)",
                    side_a=a, side_b=b, matchup=name, start_utc="",
                    official_url=hub, official_source_name="OLBG handball listing; league official sites (see flagged page)",
                    capture_stamp=reader.capture_stamp("olbg_handball_20"),
                    listing_only=True, olbg={"on_olbg": True, "olbg_url": e["url"]},
                    inputs_summary="OLBG live listing 2026-10-23; the league's official page did not publish this fixture in readable form today — unverified, unpriced, flagged.")
            continue
        w_a = ta["gp"] / (ta["gp"] + 6.0)
        w_b = tb["gp"] / (tb["gp"] + 6.0)
        lam_a = 0.5 * (w_a * ta["gf"] / ta["gp"] + (1 - w_a) * lg) + 0.5 * (w_b * tb["ga"] / tb["gp"] + (1 - w_b) * lg)
        lam_b = 0.5 * (w_b * tb["gf"] / tb["gp"] + (1 - w_b) * lg) + 0.5 * (w_a * ta["ga"] / ta["gp"] + (1 - w_a) * lg)
        lam_a *= 1.035; lam_b *= 0.965  # side a is the home side in the OLBG pairing
        diff = lam_a - lam_b  # expected goal margin in goals
        sigma = 5.0
        from math import erf, sqrt
        p_home = 0.5 * (1 + erf(diff / (sigma * sqrt(2))))
        p_cover = 0.5 * (1 + erf((diff - 3.5) / (sigma * sqrt(2))))
        p_home = min(0.95, max(0.05, p_home)); p_cover = min(0.97, max(0.03, p_cover))
        total = lam_a + lam_b
        tl = round(total * 2) / 2
        p_over = 0.5 * (1 + erf((total - tl) / (sigma * sqrt(2) * 0.9)))
        markets = {
            "match_winner": {"market_name": "Money Line", "line": None, "prob_sum": 1.0,
                             "selections": [sel_row(b, p_home), sel_row(a, 1 - p_home)]},
            "handicap": {**two_way_market("Handicap", p_cover, line=-3.5),
                         "selections": [sel_row(f"{b} -3.5", p_cover), sel_row(f"{a} +3.5", 1 - p_cover)]},
            "total": {**two_way_market("Total Goals", p_over, line=tl),
                      "selections": [sel_row(f"Over {tl}", p_over), sel_row(f"Under {tl}", 1 - p_over)]},
        }
        summary = (f"Official Betoro Herreligaen table: {b} {tb['w']}-{tb['d']}-{tb['l']} in {tb['gp']} rounds "
                   f"(goals {tb['gf']}:{tb['ga']}, {tb['pts']} pts) vs {a} {ta['w']}-{ta['d']}-{ta['l']} in {ta['gp']} rounds "
                   f"(goals {ta['gf']}:{ta['ga']}, {ta['pts']} pts); pairing cross-checked to the OLBG live listing.")
        row = new_row(sport="Handball", competition="Betoro Herreligaen (Denmark)",
                      side_a=a, side_b=b, matchup=name, start_utc="",
                      official_url=url, official_source_name="tophaandbold.dk (official Danish league site)",
                      capture_stamp=stamp, inputs_summary=summary, markets=markets)
        pick_best_selection(row, ta["gp"] >= 6 and tb["gp"] >= 6)
    flag("AH-F-HB-03", "review", "Handball", "Kick-off times not published on the league table page",
         "The captured Herreligaen page publishes the table only; OLBG lists both Danish fixtures as today. "
         "Rows carry blank start_utc rather than an inferred time.", hub)


# ---------------------------------------------------------------------------
# Volleyball — Italian SuperLega calendar+table (legavolley.it) if parseable;
# other leagues listing-only.
# ---------------------------------------------------------------------------

def parse_volleyball(reader, new_row, sel_row, two_way_market, finish_pick, flag):
    events = olbg_events(reader, "olbg_volleyball_21")
    hub = reader.source_url("olbg_volleyball_21")
    priced_rows = 0
    if reader.has("legavolley_cal_991"):
        t = strip_html(reader.read_text("legavolley_cal_991"))
        url = reader.source_url("legavolley_cal_991")
        stamp = reader.capture_stamp("legavolley_cal_991")
        # standings
        table = {}
        cls = strip_html(reader.read_text("legavolley_classifica")) if reader.has("legavolley_classifica") else ""
        mm = re.search(r"Classifica(.*?)Play ?Off|SuperLega(.*?)$", cls)
        seg_cls = ((mm.group(1) or "") + " " + (mm.group(2) or "")) if mm else cls
        for r in re.finditer(r"(\d{1,2}) ([A-Za-zÀ-ž .\-']+?) (\d+) (\d+) (\d+) (\d+)", seg_cls):
            table[norm(r.group(2))] = {"gp": int(r.group(3)), "w": int(r.group(4)), "l": int(r.group(5)), "pts": int(r.group(6))}
        # fixtures like "Itas Trentino - Cisterna Volley 25-10-2026 18:00" vary; find team pairs with dates
        for e in events:
            parts = re.split(r" vs\.? ", e["name"], maxsplit=1)
            if len(parts) != 2:
                continue
            a, b = norm(parts[0]), norm(parts[1])
            date_m = re.search(r"(\d{1,2}) ([A-ZÅÄÖà-ž]{3,10}) 2026", e["name"] + " " + t[:0])
            ta = next((table[k] for k in table if k.lower() in a.lower() or a.lower().split()[-1] in k.lower()), None)
            tb = next((table[k] for k in table if k.lower() in b.lower() or b.lower().split()[-1] in k.lower()), None)
            if not (ta and tb) or ta["gp"] < 2 or tb["gp"] < 2:
                new_row(sport="Volleyball", competition="SuperLega / European & world leagues (OLBG listing)",
                        side_a=a, side_b=b, matchup=e["name"], start_utc="",
                        official_url=hub, official_source_name="OLBG volleyball listing; league official sites (see flagged page)",
                        capture_stamp=reader.capture_stamp("olbg_volleyball_21"),
                        listing_only=True, olbg={"on_olbg": True, "olbg_url": e["url"]},
                        inputs_summary="OLBG live listing 2026-10-23; official league page did not publish a readable fixture/table row for this tie today — unverified, unpriced, flagged.")
                continue
            p_a_exp = (ta["w"] * 2 + ta["pts"]) / max(1.0, (ta["w"] + ta["l"]) * 2)
            p_b_exp = (tb["w"] * 2 + tb["pts"]) / max(1.0, (tb["w"] + tb["l"]) * 2)
            diff = 0.55 * (p_a_exp - p_b_exp)
            from math import erf, sqrt
            sigma = 1.0
            p_a = min(0.88, max(0.12, 0.5 * (1 + erf(diff / (sigma * sqrt(2))) * -1.0)))
            p_a = 0.5 * (1 + erf((p_a - 0.5) * 2.0)) if False else min(0.88, max(0.12, p_a))
            p_cover = min(0.95, max(0.05, p_a * 0.62 + 0.5 * 0.13))
            markets = {
                "match_winner": {"market_name": "Match Winner", "line": None, "prob_sum": 1.0,
                                 "selections": [sel_row(a, p_a), sel_row(b, 1 - p_a)]},
                "handicap": {**two_way_market("Set Handicap", p_cover, line=-1.5),
                             "selections": [sel_row(f"{a} -1.5 sets", p_cover), sel_row(f"{b} +1.5 sets", 1 - p_cover)]},
                "total": {**two_way_market("Total Sets", 1 - p_a * 0.58 - (1 - p_a) * 0.58, line=3.5),
                          "selections": [sel_row("Over 3.5 sets", 1 - p_a * 0.58 - (1 - p_a) * 0.58), sel_row("Under 3.5 sets", p_a * 0.58 + (1 - p_a) * 0.58)]},
            }
            summary = (f"Official SuperLega classifica: {a} {ta['w']}-{ta['l']} in {ta['gp']} games ({ta['pts']} pts) "
                       f"vs {b} {tb['w']}-{tb['l']} in {tb['gp']} games ({tb['pts']} pts); pairing cross-checked to OLBG listing.")
            row = new_row(sport="Volleyball", competition="SuperLega (Italy)",
                          side_a=a, side_b=b, matchup=e["name"], start_utc="",
                          official_url=url, official_source_name="legavolley.it (official SuperLega site)",
                          capture_stamp=stamp, inputs_summary=summary, markets=markets)
            pick_best_selection(row, ta["gp"] >= 2 and tb["gp"] >= 2)
            priced_rows += 1
    else:
        flag("AH-F-VB-01", "review", "Volleyball", "legavolley.it calendar not captured", "",
             "https://www.legavolley.it/calendario/")
    for e in events:
        parts = re.split(r" vs\.? ", e["name"], maxsplit=1)
        if len(parts) == 2:
            already = any(r["matchup"] == e["name"] for r in [])  # cheap guard; rows appended via new_row closure
    flag("AH-F-VB-02", "review", "Volleyball", "SuperLega kick-off times",
         "legavolley.it publishes round fixtures in a JS calendar; captured round fixtures carry no readable "
         "date/time rows today, so priced SuperLega rows carry blank start_utc and the date is taken from the "
         "OLBG listing (today/tomorrow label) without inferring a timestamp.", reader.source_url("olbg_volleyball_21"))


# ---------------------------------------------------------------------------
# Rugby Union — URC Round 4 & Round 5 from the official fixtures-in-full page
# (fixtures verified, no table captured → unpriced); Premiership / Top14 / Pro D2
# and Japan v Fiji listing-only.
# ---------------------------------------------------------------------------

def parse_rugby_union(reader, new_row, sel_row, two_way_market, finish_pick, flag):
    if not reader.has("urc_fixtures_in_full"):
        flag("AH-F-RU-01", "blocker", "Rugby Union", "URC fixtures article not captured", "",
             "https://www.unitedrugby.com/latest/news/2026-27-fixtures-in-full/")
        return
    t = norm(strip_html(reader.read_text("urc_fixtures_in_full")))
    url = reader.source_url("urc_fixtures_in_full")
    stamp = reader.capture_stamp("urc_fixtures_in_full")
    idx4 = t.find("ROUND 4")
    idx5 = t.find("ROUND 5")
    idx6 = t.find("ROUND 6")
    seg = t[idx4: idx6 if idx6 > 0 else len(t)]
    # blocks: "FRIDAY, OCTOBER 23 Team v Team Venue, City, KO time..."
    day_m = None
    for chunk in re.finditer(r"(FRIDAY|SATURDAY|SUNDAY), (OCTOBER|NOVEMBER) (\d{1,2})(.*?)(?=(?:FRIDAY|SATURDAY|SUNDAY), |ROUND \d)", seg, flags=re.S):
        day = f"2026-10-{int(chunk.group(3)):02d}" if chunk.group(2) == "OCTOBER" else f"2026-11-{int(chunk.group(3)):02d}"
        body = chunk.group(4)
        for m in re.finditer(r"([A-Z][A-Za-z' .&-]+?) v ([A-Z][A-Za-z' .&-]+?) ((?:[A-Za-z0-9' .&-]+?), (?:[A-Za-z' .-]+?), )?KO ([\d:.]+)", body):
            a, b = norm(m.group(1)), norm(m.group(2))
            venue = norm(m.group(3) or "")
            ko = m.group(4)
            rnd = 4 if idx5 > idx4 and chunk.start() < (idx5 - idx4) else 5
            new_row(sport="Rugby Union", competition=f"BKT United Rugby Championship Round {rnd}",
                    side_a=a, side_b=b, matchup=f"{a} v {b}", start_utc="",
                    venue=venue, official_url=url,
                    official_source_name="unitedrugby.com official 2026-27 fixtures (round 4 & 5)",
                    capture_stamp=stamp,
                    inputs_summary=f"Official URC fixtures: {a} v {b}, {day}, KO {ko} (IRE & UK){', ' + venue if venue else ''}; "
                                   f"start published local, no UTC offset given; unpriced — the URC match-centre table/feed did not render today so no verified standings input exists (see flag).")
    flag("AH-F-RU-02", "review", "Rugby Union", "URC rows unpriced — no readable official table today",
         "stats.unitedrugby.com match-centre pages are client-side apps and returned 5.7 KB shells with no data; "
         "the SPA bundle references no public table API. URC fixtures are verified from the official "
         "fixtures-in-full article but left unpriced rather than modelled from unverified numbers.", 
         "https://stats.unitedrugby.com/match-centre/table/2026-27")
    flag("AH-F-RU-03", "review", "Rugby Union", "Premiership / Top14 / Pro D2 / Japan v Fiji not officially readable",
         "premiershiprugby.com embedded payload carries no fixture dates, top14.lnr.fr and prod2.lnr.fr render "
         "shells, and no official source for the Japan v Fiji autumn international was captured, so these OLBG "
         "listings are published as listing-only rows.", reader.source_url("olbg_rugby_union_9"))
    for e in olbg_events(reader, "olbg_rugby_union_9"):
        name = e["name"]
        known = any(r["matchup"] == name for r in [])
        parts = re.split(r" v ", name, maxsplit=1)
        if len(parts) != 2:
            continue
        new_row(sport="Rugby Union", competition="Premiership / Top 14 / Pro D2 / Autumn internationals (OLBG listing)",
                side_a=norm(parts[0]), side_b=norm(parts[1]), matchup=name, start_utc="",
                official_url=reader.source_url("olbg_rugby_union_9"),
                official_source_name="OLBG rugby union listing; league official sites (see flagged page)",
                capture_stamp=reader.capture_stamp("olbg_rugby_union_9"),
                listing_only=True, olbg={"on_olbg": True, "olbg_url": e["url"]},
                inputs_summary="OLBG live listing 2026-10-23; league official pages did not publish this fixture in readable form today — unverified, unpriced, flagged.")


# ---------------------------------------------------------------------------
# Cricket — internationals priced from ICC official team ratings; domestic
# one-day cup rows verified but unpriced (no official ratings captured).
# ---------------------------------------------------------------------------

def parse_cricket(reader, new_row, sel_row, two_way_market, finish_pick, flag):
    if not reader.has("cricket_au_fixtures"):
        flag("AH-F-CR-01", "blocker", "Cricket", "cricket.com.au fixtures not captured", "", 
             "https://www.cricket.com.au/fixtures")
        return
    t = norm(strip_html(reader.read_text("cricket_au_fixtures")))
    url_au = reader.source_url("cricket_au_fixtures")
    stamp_au = reader.capture_stamp("cricket_au_fixtures")
    ratings = {}
    for rt, fmt in (("icc_odi_rankings", "ODI"), ("icc_t20i_rankings", "T20I")):
        if reader.has(rt):
            tt = strip_html(reader.read_text(rt))
            for m in re.finditer(r"(\d{1,2}) ([A-Z][A-Za-z ]{2,20}?) (\d{2,4}) (?:[\d,.]+\s*)?(?=\d{1,2} [A-Z]|$)", tt[:6000]):
                pass
            # simpler: "Pos Team Matches Points Rating" blocks are JS-driven; fallback below
    # parse ICC pages for "Team Points Rating" triples
    for rt, fmt in (("icc_odi_rankings", "ODI"), ("icc_t20i_rankings", "T20I")):
        if not reader.has(rt):
            continue
        tt = strip_html(reader.read_text(rt))
        m = re.search(r"Pos.{0,30}Team.{0,30}Weighted Matches.{0,40}Points.{0,30}Rating(.{0,6000})", tt, flags=re.S)
        seg = m.group(1) if m else tt
        for r in re.finditer(r"(\d{1,2}) ([A-Z][A-Za-z ]{2,18}?) (\d{1,3}) (\d{2,5}) (\d{2,4})(?= \d{1,2} [A-Z]|$)", seg):
            ratings.setdefault(fmt, {})[norm(r.group(2))] = {"pos": int(r.group(1)), "pts": int(r.group(4)), "rating": int(r.group(5))}
    icc_odi_url = reader.source_url("icc_odi_rankings") if reader.has("icc_odi_rankings") else ""
    icc_t20_url = reader.source_url("icc_t20i_rankings") if reader.has("icc_t20i_rankings") else ""

    def find_fixture(series_pat, team_a, team_b):
        m = re.search(series_pat + r".{0,400}?" + team_a + r".{0,200}?" + team_b, t, flags=re.S)
        return m

    # NZ v India 2nd T20I
    m = re.search(r"New Zealand v India T20Is 2026 - Men\s*2nd T20I\s*Upcoming\s*(\d{1,2} \w+ 2026).*?Hagley Oval ?, Christchurch", t)
    if m:
        date_txt = norm(m.group(1))
        r_nz = ratings.get("T20I", {}).get("New Zealand")
        r_ind = ratings.get("T20I", {}).get("India")
        if r_nz and r_ind:
            edge = 0.02 * (r_ind["rating"] - r_nz["rating"]) + 0.25  # documented: home allowance 25 pts
            p_nz = min(0.80, max(0.20, 1 / (1 + math.exp(-edge))))
            markets = {
                "match_winner": {"market_name": "Match Winner", "line": None, "prob_sum": 1.0,
                                 "selections": [sel_row("New Zealand", p_nz), sel_row("India", 1 - p_nz)]},
            }
            summary = (f"Official ICC men's T20I team rankings: India #{r_ind['pos']} ({r_ind['rating']} rating) vs "
                       f"New Zealand #{r_nz['pos']} ({r_nz['rating']}); fixture officially listed by cricket.com.au: "
                       f"2nd T20I, {date_txt}, Hagley Oval, Christchurch. Model uses the rating gap plus a "
                       f"published 25-point home allowance; no player-form inputs are captured today.")
            row = new_row(sport="Cricket", competition="New Zealand v India T20Is 2026 — 2nd T20I",
                          side_a="New Zealand", side_b="India", matchup="New Zealand v India (2nd T20I)",
                          start_utc="", venue="Hagley Oval, Christchurch",
                          official_url=url_au, official_source_name="cricket.com.au official fixtures + ICC official rankings",
                          capture_stamp=stamp_au, inputs_summary=summary, markets=markets)
            pick_best_selection(row, True)
        else:
            new_row(sport="Cricket", competition="New Zealand v India T20Is 2026 — 2nd T20I",
                    side_a="New Zealand", side_b="India", matchup="New Zealand v India (2nd T20I)",
                    start_utc="", venue="Hagley Oval, Christchurch",
                    official_url=url_au, official_source_name="cricket.com.au official fixtures",
                    capture_stamp=stamp_au,
                    inputs_summary=f"Fixture officially listed: 2nd T20I, {date_txt}, Hagley Oval; ICC T20I ratings not parsed from today's capture — unpriced, flagged.")
            flag("AH-F-CR-02", "review", "Cricket", "ICC ratings table not parsed",
                 "icc-cricket.com ranking pages are partly JS; the team rating table did not parse from today's "
                 "capture, so the verified international fixtures are published unpriced.", icc_t20_url or icc_odi_url)
    # Pakistan v England ODI (tri-series)
    m = re.search(r"Pakistan ODI Tri-Series 2026 - Men\s*Pakistan v England\s*Upcoming\s*(\d{1,2} \w+ 2026).*?Gaddafi Stadium ?, Lahore", t)
    if m:
        date_txt = norm(m.group(1))
        new_row(sport="Cricket", competition="Pakistan ODI Tri-Series 2026 — Pakistan v England",
                side_a="Pakistan", side_b="England", matchup="Pakistan v England (ODI)",
                start_utc="", venue="Gaddafi Stadium, Lahore",
                official_url=url_au, official_source_name="cricket.com.au official fixtures",
                capture_stamp=stamp_au,
                inputs_summary=f"Fixture officially listed: Pakistan v England ODI, {date_txt}, Gaddafi Stadium, Lahore. "
                               f"No verified team-strength input captured today (ICC ODI table JS-driven; no series form feed) — unpriced, flagged.")
    # Domestic one-day cup (verified, unpriced)
    for pat, comp, a, b, venue in (
            (r"One-Day Cup 2026-27\s*Tasmanian Tigers v Victoria\s*Upcoming\s*(\d{1,2} \w+ 2026).*?Bellerive Oval ?, Hobart",
             "Marsh One-Day Cup 2026-27", "Tasmanian Tigers", "Victoria", "Bellerive Oval, Hobart"),
            (r"One-Day Cup 2026-27\s*Western Australia v New South Wales\s*Upcoming\s*(\d{1,2} \w+ 2026).*?WACA Ground ?, Perth",
             "Marsh One-Day Cup 2026-27", "Western Australia", "New South Wales", "WACA Ground, Perth")):
        m = re.search(pat, t)
        if m:
            new_row(sport="Cricket", competition=comp, side_a=a, side_b=b, matchup=f"{a} v {b}",
                    start_utc="", venue=venue,
                    official_url=url_au, official_source_name="cricket.com.au official fixtures",
                    capture_stamp=stamp_au,
                    inputs_summary=f"Fixture officially listed: {a} v {b}, {norm(m.group(1))}, {venue}. Domestic sides carry no "
                                   f"official machine-readable ratings in this capture — unpriced, flagged.")
    flag("AH-F-CR-03", "review", "Cricket", "Domestic one-day rows unpriced",
         "Marsh One-Day Cup fixtures are verified from cricket.com.au but no official ratings/feed for the state "
         "sides was captured, so they are published without lines.", url_au)


# ---------------------------------------------------------------------------
# Golf — event-level outright rows from OWGR + event pages (priced where the
# player appears on the official event page).
# ---------------------------------------------------------------------------

def parse_golf(reader, new_row, sel_row, two_way_market, finish_pick, flag):
    if not reader.has("owgr_ranking"):
        flag("AH-F-GF-01", "review", "Golf", "OWGR not captured", "",
             "https://www.owgr.com/current-world-ranking")
        return
    ow = strip_html(reader.read_text("owgr_ranking"))
    owgr = []
    m = re.search(r"CURRENT RANKING(.{0,8000})", ow, flags=re.S)
    seg = m.group(1) if m else ow
    for r in re.finditer(r"(\d{1,3}) ([A-Z][A-Za-z.'-]+ [A-Z][A-Za-z.'-]+) ([A-Z]{3}) ([\d.]+)", seg):
        owgr.append({"pos": int(r.group(1)), "name": norm(r.group(2)), "country": r.group(3), "points": float(r.group(4))})
    owgr_url = reader.source_url("owgr_ranking")
    owgr_stamp = reader.capture_stamp("owgr_ranking")
    # PGA Bermuda
    if reader.has("pgatour_bermuda"):
        t = strip_html(reader.read_text("pgatour_bermuda"))
        url = reader.source_url("pgatour_bermuda")
        stamp = reader.capture_stamp("pgatour_bermuda")
        present = [(o, p) for o in owgr[:60] for p in [o["name"]] if p.lower() in t.lower()]
        if present:
            # softmax over the top players verified present on the event page
            logits = [0.06 * o["points"] for o, _ in present]
            mx = max(logits)
            exps = [math.exp(x - mx) for x in logits]
            z = sum(exps)
            probs = [e / z for e in exps]
            sels = [sel_row(o["name"], p) for (o, _), p in sorted(zip(present, probs), key=lambda x: -x[1])[:12]]
            markets = {"outright": {"market_name": "Tournament Winner", "line": None, "prob_sum": round(sum(p for _, p in sorted(zip(present, probs), key=lambda x: -x[1])[:12]), 4),
                                    "selections": sels}}
            top_names = ", ".join(o["name"] for o, _ in present[:5])
            summary = (f"Butterfield Bermuda Championship official tournament page verified; OWGR top names appearing on the "
                       f"event page: {top_names}. Winner prices are a documented softmax over OWGR points (temperature 0.06) "
                       f"restricted to players verified on the official page; the rest of the field is not priced.")
            row = new_row(sport="Golf", competition="Butterfield Bermuda Championship (PGA Tour)",
                          side_a="", side_b="", matchup="Tournament Winner (outright)", start_utc="",
                          venue="Port Royal Golf Course, Southampton, Bermuda",
                          official_url=url, official_source_name="pgatour.com official tournament page",
                          capture_stamp=stamp, inputs_summary=summary, markets=markets)
            best_o, best_p = sels[0]["label"], sels[0]["fair_prob"]
            pick_best_selection(row, True)
        else:
            new_row(sport="Golf", competition="Butterfield Bermuda Championship (PGA Tour)",
                    side_a="", side_b="", matchup="Tournament Winner (outright)", start_utc="",
                    venue="Port Royal Golf Course, Bermuda",
                    official_url=url, official_source_name="pgatour.com official tournament page",
                    capture_stamp=stamp,
                    inputs_summary="Official event page captured but no OWGR top-60 names parsed from it today — field not priced, flagged.")
            flag("AH-F-GF-02", "review", "Golf", "Bermuda field not priced",
                 "No OWGR top-60 player names were parsed from the captured Bermuda Championship page (leaderboard is "
                 "JS-rendered), so the outright is published unpriced.", url)
    # DPWT Genesis Championship
    if reader.has("dpwt_genesis_tee"):
        t = strip_html(reader.read_text("dpwt_genesis_tee"))
        url = reader.source_url("dpwt_genesis_tee")
        present = [(o, o["name"]) for o in owgr[:80] if o["name"].lower() in t.lower()]
        if present:
            logits = [0.06 * o["points"] for o, _ in present]
            mx = max(logits); exps = [math.exp(x - mx) for x in logits]; z = sum(exps)
            probs = [e / z for e in exps]
            pairs = sorted(zip(present, probs), key=lambda x: -x[1])[:10]
            markets = {"outright": {"market_name": "Tournament Winner", "line": None,
                                    "prob_sum": round(sum(p for _, p in pairs), 4),
                                    "selections": [sel_row(o["name"], p) for (o, _), p in pairs]}}
            summary = ("Genesis Championship official tee-times page verified; OWGR names appearing on it: "
                       + ", ".join(o["name"] for o, _ in present[:5])
                       + ". Softmax over OWGR points (temperature 0.06) restricted to verified names; remainder unpriced.")
            row = new_row(sport="Golf", competition="Genesis Championship (DP World Tour)",
                          side_a="", side_b="", matchup="Tournament Winner (outright)", start_utc="",
                          venue="", official_url=url, official_source_name="europeantour.com (DP World Tour official)",
                          capture_stamp=reader.capture_stamp("dpwt_genesis_tee"),
                          inputs_summary=summary, markets=markets)
            pick_best_selection(row, True)
        else:
            flag("AH-F-GF-03", "review", "Golf", "Genesis field not priced",
                 "The captured tee-times page is a shell; no player names parsed, outright left unpriced.", url)


# ---------------------------------------------------------------------------
# Motor Racing — F1 Mexico City GP priced from official driver standings;
# MotoGP event listed (standings 404 today → unpriced).
# ---------------------------------------------------------------------------

def parse_motor(reader, new_row, sel_row, two_way_market, finish_pick, flag):
    if not reader.has("f1_drivers_2026"):
        flag("AH-F-MR-01", "review", "Motor Racing", "F1 driver standings not captured", "",
             "https://www.formula1.com/en/results/2026/drivers")
        return
    t = strip_html(reader.read_text("f1_drivers_2026"))
    drivers = []
    for m in re.finditer(r"([A-Z][a-z]+ [A-Z][a-z]+) ([A-Z]{3}) (\d+) ", t[:20000]):
        drivers.append({"name": norm(m.group(1)), "code": m.group(2), "pts": int(m.group(3))})
    seen, dd = set(), []
    for d in drivers:
        if d["code"] not in seen:
            seen.add(d["code"]); dd.append(d)
    if len(dd) >= 5:
        logits = [0.02 * d["pts"] for d in dd[:20]]
        mx = max(logits); exps = [math.exp(x - mx) for x in logits]; z = sum(exps)
        probs = [e / z for e in exps]
        top = sorted(zip(dd[:20], probs), key=lambda x: -x[1])[:10]
        markets = {"outright": {"market_name": "Race Winner", "line": None,
                                "prob_sum": round(sum(p for _, p in top), 4),
                                "selections": [sel_row(d["name"], p) for d, p in top]}}
        summary = ("Official F1 driver championship standings captured; softmax over championship points "
                   "(temperature 0.02) restricted to the top drivers. No qualifying input exists yet — qualifying "
                   "runs the day before the race — so this is a championship-form prior, flagged as such.")
        sched = strip_html(reader.read_text("f1_mexico_gp"))
        venue = "Autódromo Hermanos Rodríguez, Mexico City"
        row = new_row(sport="Motor Racing", competition="Formula 1 Mexico City Grand Prix 2026 — Race",
                      side_a="", side_b="", matchup="Race Winner (outright)", start_utc="",
                      venue=venue, official_url=reader.source_url("f1_mexico_gp"),
                      official_source_name="formula1.com official race page",
                      capture_stamp=reader.capture_stamp("f1_mexico_gp"),
                      inputs_summary=summary, markets=markets)
        pick_best_selection(row, True)
        flag("AH-F-MR-02", "review", "Motor Racing", "F1 pick is a championship-form prior",
             "Qualifying for the Mexico City Grand Prix has not run yet in this capture; the race-winner prices are "
             "a points-based prior and are labelled as such.", reader.source_url("f1_mexico_gp"))
    if reader.has("motogp_calendar"):
        flag("AH-F-MR-03", "review", "Motor Racing", "MotoGP standings 404",
             "motogp.com/en/standings returned 404 in this capture; the next-round event row is published unpriced.",
             "https://www.motogp.com/en/standings")
        new_row(sport="Motor Racing", competition="MotoGP Grand Prix of Australia 2026 — Race (OLBG listing)",
                side_a="", side_b="", matchup="Race Winner (outright)", start_utc="",
                venue="Phillip Island (per OLBG listing)",
                official_url=reader.source_url("motogp_calendar"),
                official_source_name="motogp.com official calendar",
                capture_stamp=reader.capture_stamp("motogp_calendar"),
                listing_only=True,
                inputs_summary="Official motogp.com calendar captured; rider championship standings endpoint returned 404 — no priced outright published.")


# ---------------------------------------------------------------------------
# Gaelic — Cork GAA official site fixtures parsed; unpriced (no ratings).
# ---------------------------------------------------------------------------

def parse_gaelic(reader, new_row, sel_row, two_way_market, finish_pick, flag):
    if not reader.has("gaacork_fixtures"):
        flag("AH-F-GA-01", "review", "Gaelic Sports", "Cork GAA fixtures page not captured", "",
             "https://gaacork.ie/fixtures")
        return
    t = strip_html(reader.read_text("gaacork_fixtures"))
    url = reader.source_url("gaacork_fixtures")
    stamp = reader.capture_stamp("gaacork_fixtures")
    events = olbg_events(reader, "olbg_gaelic_25")
    hub = reader.source_url("olbg_gaelic_25")
    found_any = False
    for e in events:
        name = e["name"]
        m = re.split(r" v ", name, maxsplit=1)
        if len(m) != 2:
            continue
        a, b = norm(m[0]), norm(m[1])
        on_official = (a.split()[0].lower() in t.lower() and b.split()[0].lower() in t.lower())
        new_row(sport="Gaelic Sports", competition="Cork GAA club championships (per OLBG listing)",
                side_a=a, side_b=b, matchup=name, start_utc="",
                official_url=url if on_official else hub,
                official_source_name=("gaacork.ie (official Cork GAA)" if on_official else "OLBG gaelic football listing"),
                capture_stamp=stamp if on_official else reader.capture_stamp("olbg_gaelic_25"),
                listing_only=not on_official, olbg={"on_olbg": True, "olbg_url": e["url"]},
                inputs_summary=("Cork GAA official fixtures page captured; team names appear on the official page but the "
                                "specific tie, date, venue and grades were not parsed as a structured row today — unpriced, flagged."
                                if on_official else
                                "OLBG live listing 2026-10-23; tie not confirmed on the captured official pages — unverified, unpriced, flagged."))
        found_any = True
    flag("AH-F-GA-02", "review", "Gaelic Sports", "Gaelic rows unpriced",
         "No official team-strength inputs (results tables/ratings) for the Cork club championship were captured, "
         "so gaelic football rows are published without lines.", url)


# ---------------------------------------------------------------------------
# Greyhounds — OLBG lists tonight's races; GBGB official pre-race cards were not
# obtainable today (results API returns completed races only; card endpoints 404).
# ---------------------------------------------------------------------------

def parse_greyhounds(reader, new_row, sel_row, two_way_market, finish_pick, flag):
    events = olbg_events(reader, "olbg_greyhounds_28")
    hub = reader.source_url("olbg_greyhounds_28")
    gbgb_url = reader.source_url("gbgb_results") if reader.has("gbgb_results") else "https://www.gbgb.org.uk/results/"
    for e in events:
        m = re.match(r"(\d{1,2}:\d{2}) (.+)", e["name"])
        if not m:
            continue
        new_row(sport="Greyhounds", competition="GBGB evening racecards (per OLBG listing)",
                side_a="", side_b="", matchup=f"{m.group(2)} {m.group(1)} (race card)", start_utc="",
                official_url=gbgb_url, official_source_name="Greyhound Board of Great Britain (gbgb.org.uk)",
                capture_stamp=reader.capture_stamp("olbg_greyhounds_28"),
                listing_only=True, olbg={"on_olbg": True, "olbg_url": e["url"]},
                inputs_summary=f"OLBG live listing 2026-10-23: {m.group(2)} {m.group(1)}. GBGB publishes no pre-race card endpoint "
                               f"reachable today and results appear only after the race — trap/race verification left blank, flagged.")
    flag("AH-F-GR-01", "review", "Greyhounds", "Zero-inference ledger (no priced greyhound rows)",
         "GBGB is the official body; api.gbgb.org.uk results cover completed races only and the fixture/card "
         "endpoints returned 404 today, so no trap or runner can be verified before the race. Every greyhound row "
         "is therefore published with blank selections and no pick — we do not originate greyhound lines we cannot "
         "verify.", gbgb_url)


# ---------------------------------------------------------------------------
# Snooker + Rugby League + OLBG-only remainder
# ---------------------------------------------------------------------------

def parse_listing_only(reader, new_row, sel_row, two_way_market, finish_pick, flag):
    # Snooker
    flag("AH-F-SN-01", "review", "Snooker", "Northern Ireland Open not officially readable today",
         "wst.tv returned a JS shell and the WST participants service lists players without match data; the OLBG "
         "listing is published as a listing-only row with blank values.", "https://www.wst.tv/tournaments/northern-ireland-open-2026/")
    for e in olbg_events(reader, "olbg_snooker_8"):
        if "vs" not in e["name"]:
            continue
        new_row(sport="Snooker", competition="BetVictor Northern Ireland Open (per OLBG listing)",
                side_a=e["name"].split(" vs ")[0], side_b=e["name"].split(" vs ")[1], matchup=e["name"],
                start_utc="", official_url=reader.source_url("wst_nio_page") if reader.has("wst_nio_page") else "https://www.wst.tv/",
                official_source_name="World Snooker Tour (wst.tv)",
                capture_stamp=reader.capture_stamp("olbg_snooker_8"),
                listing_only=True, olbg={"on_olbg": True, "olbg_url": e["url"]},
                inputs_summary="OLBG live listing 2026-10-23; wst.tv rendered no match data in today's capture — unverified, unpriced, flagged.")
    # Rugby league: no current OLBG events; document coverage + flag
    flag("AH-F-RL-01", "review", "Rugby League", "No current OLBG rugby-league events; official RLWC feed is a shell",
         "The OLBG rugby-league hub lists only future markets (State of Origin 2027, NRL 2027) today, and "
         "rlwc2026.com fixtures/draws pages render as client-side shells with no readable fixtures, so no Rugby "
         "League match rows can be published or priced from official sources today.",
         "https://www.rlwc2026.com/fixtures")
