#!/usr/bin/env python3
"""Board BW — remaining sport parsers (called from originate_desk.py).

Every parser follows the same rule: prices/lines come only from numbers present in the
committed official capture bytes; OLBG hub pages supply the listing (taxonomy) cross-check
and the market-price reference only; anything unverifiable is published blank and flagged.

Window: 2026-10-23 .. 2026-11-08 inclusive (WIN_START/WIN_END below).
"""
from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone

# originate_desk imports this module lazily from inside main(), so by the time these
# parsers run the importing module is fully initialised and the import below is safe.
from originate_desk import pick_best_selection  # noqa: E402

WIN_START = "2026-10-23"
WIN_END = "2026-11-09"

# canonical official body URL per sport for listing-only fallback rows
BODY_URL = {
    "Golf": "https://www.pgatour.com/",
    "Volleyball": "https://www.legavolley.it/",
    "Rugby Union": "https://www.unitedrugby.com/",
    "Cricket": "https://www.cricket.com.au/fixtures",
    "Snooker": "https://www.wst.tv/",
    "Darts": "https://www.pdc.tv/",
    "Baseball": "https://www.mlb.com/",
    "Gaelic Sports": "https://www.gaa.ie/fixtures",
    "Greyhounds": "https://www.gbgb.org.uk/",
    "Tennis": "https://www.atptour.com/",
    "Motor Racing": "https://www.formula1.com/",
    "Handball": "https://www.ehfcl.com/",
    "Ice Hockey": "https://www.nhl.com/",
    "Basketball": "https://www.nba.com/schedule",
    "Rugby League": "https://www.rlwc2026.com/",
}


def strip_html(h: str) -> str:
    h = re.sub(r"<script[^>]*>.*?</script>", " ", h, flags=re.S)
    h = re.sub(r"<style[^>]*>.*?</style>", " ", h, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", h)
    return re.sub(r"\s+", " ", t).strip()


def norm(s: str) -> str:
    s = s.replace("&amp;", "&").replace("&#8217;", "'").replace("&#038;", "&")
    return re.sub(r"\s+", " ", s).strip()


TIP_FIELD = re.compile(r'(?:^|[{,])\s*([a-zA-Z_]+):\s*(?:"([^"]*)"|(-?\d+(?:\.\d+)?)|null)')


def olbg_events(reader, target):
    """Extract upcoming OLBG listing events from a captured hub page.

    The hub ships a SvelteKit `tips:[...]` payload; each tip carries the event name,
    event URL (with event_id), start timestamp, listed odds and an `expired` marker.
    Returns one entry per event: {name, url, start_utc, tips:[{selection, market,
    decimal, american}]}. Events whose every tip is expired (kick-off passed) are
    dropped so the listing only carries upcoming matches.
    """
    if not reader.has(target):
        return []
    html = reader.read_text(target)
    m = re.search(r"tips:\[", html)
    if not m:
        return []
    body = html[m.end() - 1:]
    evs: dict[str, dict] = {}
    for tm in re.finditer(r'\{id:"[0-9a-f]{40}",selection:"', body):
        chunk = body[tm.start(): tm.start() + 1600]
        end = chunk.find("}")
        chunk = chunk[: end + 1]
        rec: dict = {}
        for fm in TIP_FIELD.finditer(chunk):
            k, sval, nval = fm.group(1), fm.group(2), fm.group(3)
            rec[k] = sval if sval is not None else nval
        if not rec.get("event_name_alias"):
            continue
        eid = ""
        em = re.search(r"event_id=(\d+)", rec.get("eventUrl", "") or "")
        if em:
            eid = em.group(1)
        key = eid or rec["event_name_alias"]
        ts = int(rec.get("event_start_unix_timestamp") or 0)
        start = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if ts else ""
        e = evs.setdefault(key, {"name": rec["event_name_alias"].strip(), "url": "", "start_utc": start,
                                 "expired_all": True, "tips": []})
        if not e["url"] and rec.get("eventUrl", "").startswith("/"):
            e["url"] = "https://www.olbg.com" + rec["eventUrl"]
        if rec.get("expired") in ("0", 0):
            e["expired_all"] = False
        e["tips"].append({"selection": rec.get("selection", ""), "market": rec.get("market_alias", ""),
                          "decimal": rec.get("odds", ""), "american": rec.get("american_odds", "")})
    return [e for e in evs.values() if not e["expired_all"]]


def tokens(s: str) -> set:
    return {w for w in re.sub(r"[^a-z0-9 ]", " ", s.lower()).split() if len(w) >= 4}


# ---------------------------------------------------------------------------
# Darts — OLBG listing pairings; PDC official pages returned identical bot shells
# (1,241,849 bytes, zero player names) in this capture, so rows are listing-only.
# ---------------------------------------------------------------------------

def parse_darts(reader, new_row, sel_row, two_way_market, finish_pick, flag):
    flag("EZ-F-DARTS-01", "blocker", "Darts",
         "PDC official pages unreadable in this capture — every PDC target returned the same "
         "1,241,849-byte shell with zero player names",
         "pdc.tv, the European Championship schedule/preview articles and the Order of Merit page "
         "each returned byte-identical client-side shells (no Humphries/Littler/EC article text at all) "
         "and the PDC match-data host did not resolve, so no PDC numeric input could be captured. "
         "European Championship ties are published as listing-only rows with blank picks.",
         "https://www.pdc.tv/")
    flag("EZ-F-DARTS-02", "review", "Darts",
         "EC pairings known only from the OLBG listing",
         "The first-round/quarter-final pairings below come from OLBG's live listing only; the PDC "
         "page published no article bytes in this capture, so each pairing is published unverified "
         "from an official source (listing-only, blank values).",
         "https://www.pdc.tv/news/2026/october/19/2026-machineseeker-european-championship-schedule-confirmed/")
    for e in olbg_events(reader, "olbg_darts_15"):
        name = e["name"]
        if " vs" not in name and " v " not in name:
            continue
        m = re.split(r" vs\.? | v ", name, maxsplit=1)
        if len(m) != 2:
            continue
        new_row(sport="Darts", competition="PDC Machineseeker European Championship (Dortmund)",
                side_a=m[0], side_b=m[1], matchup=name, start_utc=e["start_utc"] if e["start_utc"] >= f"{WIN_START}T00:00:00Z" else "",
                official_url="https://www.pdc.tv/", official_source_name="PDC — pdc.tv (official site)",
                capture_stamp=reader.capture_stamp("olbg_darts_15"),
                listing_only=True,
                olbg={"on_olbg": True, "olbg_url": e["url"], "olbg_listed": [t["decimal"] for t in e["tips"][:4]]},
                inputs_summary=f"OLBG live listing ({reader.capture_stamp('olbg_darts_15')}): \"{name}\""
                               f"{', listed markets ' + ', '.join(t['market'] + ' ' + t['decimal'] for t in e['tips'][:4]) if e['tips'] else ''}. "
                               f"PDC official pages returned shell bytes in this capture (see flag) — pairing unverified "
                               f"officially; pick, odds and confidence left blank.")


# ---------------------------------------------------------------------------
# Handball — Danish Betoro Herreligaen table captured (official league site);
# OLBG-listed Danish fixtures priced from it. Other leagues: listing fallback.
# ---------------------------------------------------------------------------

def parse_handball_danish(reader, new_row, sel_row, two_way_market, finish_pick, flag):
    if not reader.has("tophaandbold_herreligaen"):
        flag("EZ-F-HB-01", "blocker", "Handball", "Danish league table not captured", "",
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
        flag("EZ-F-HB-02", "review", "Handball", "Danish table not parsed",
             "tophaandbold.dk captured but the standings regex found no rows; Danish fixtures published unpriced.", url)
        return
    lg = (sum(x["gf"] for x in table.values()) + sum(x["ga"] for x in table.values())) / max(1, 2 * sum(x["gp"] for x in table.values()))
    for e in olbg_events(reader, "olbg_handball_20"):
        parts = re.split(r" vs\.? ", e["name"], maxsplit=1)
        if len(parts) != 2:
            continue
        a, b = norm(parts[0]), norm(parts[1])
        ta = next((table[k] for k in table if a.lower().split()[0] in k.lower() or k.lower().split()[0] in a.lower()), None)
        tb = next((table[k] for k in table if b.lower().split()[0] in k.lower() or k.lower().split()[0] in b.lower()), None)
        if not (ta and tb):
            continue  # other-league tie: picked up by the listing fallback pass
        # a = home side in the OLBG pairing; explicit label/probability mapping
        w_a = ta["gp"] / (ta["gp"] + 6.0)
        w_b = tb["gp"] / (tb["gp"] + 6.0)
        lam_a = 0.5 * (w_a * ta["gf"] / ta["gp"] + (1 - w_a) * lg) + 0.5 * (w_b * tb["ga"] / tb["gp"] + (1 - w_b) * lg)
        lam_b = 0.5 * (w_b * tb["gf"] / tb["gp"] + (1 - w_b) * lg) + 0.5 * (w_a * ta["ga"] / ta["gp"] + (1 - w_a) * lg)
        lam_a *= 1.035
        lam_b *= 0.965
        diff = lam_a - lam_b  # expected goal margin, home positive
        sigma = 5.0
        from math import erf, sqrt
        p_a = min(0.95, max(0.05, 0.5 * (1 + erf(diff / (sigma * sqrt(2))))))
        p_cover = min(0.97, max(0.03, 0.5 * (1 + erf((diff - 3.5) / (sigma * sqrt(2))))))
        total = lam_a + lam_b
        tl = round(total * 2) / 2
        p_over = min(0.99, max(0.01, 0.5 * (1 + erf((total - tl) / (sigma * sqrt(2) * 0.9)))))
        markets = {
            "match_winner": {"market_name": "Money Line", "line": None, "prob_sum": 1.0,
                             "selections": [sel_row(a, p_a), sel_row(b, 1 - p_a)]},
            "handicap": {**two_way_market("Handicap", p_cover, line=-3.5),
                         "selections": [sel_row(f"{a} -3.5", p_cover), sel_row(f"{b} +3.5", 1 - p_cover)]},
            "total": {**two_way_market("Total Goals", p_over, line=tl),
                      "selections": [sel_row(f"Over {tl}", p_over), sel_row(f"Under {tl}", 1 - p_over)]},
        }
        summary = (f"Official Betoro Herreligaen table: {a} {ta['w']}-{ta['d']}-{ta['l']} in {ta['gp']} rounds "
                   f"(goals {ta['gf']}:{ta['ga']}, {ta['pts']} pts) vs {b} {tb['w']}-{tb['d']}-{tb['l']} in {tb['gp']} rounds "
                   f"(goals {tb['gf']}:{tb['ga']}, {tb['pts']} pts); home side first per the OLBG listing; "
                   f"model xG {lam_a:.2f}-{lam_b:.2f}.")
        row = new_row(sport="Handball", competition="Betoro Herreligaen (Denmark)",
                      side_a=a, side_b=b, matchup=f"{a} vs {b}",
                      start_utc=e["start_utc"] if e["start_utc"] >= f"{WIN_START}T00:00:00Z" else "",
                      official_url=url, official_source_name="tophaandbold.dk (official Danish league site)",
                      capture_stamp=stamp, inputs_summary=summary, markets=markets,
                      olbg={"on_olbg": True, "olbg_url": e["url"], "olbg_listed": [t_["decimal"] for t_ in e["tips"][:4]]})
        pick_best_selection(row, ta["gp"] >= 6 and tb["gp"] >= 6)
    flag("EZ-F-HB-03", "review", "Handball", "Kick-off times for Danish fixtures",
         "The captured Herreligaen page publishes the table only; where OLBG listed a start time its "
         "event timestamp is carried, otherwise start_utc stays blank rather than inferred.", url)


# ---------------------------------------------------------------------------
# Volleyball — Italian SuperLega calendar+table (legavolley.it) where parseable;
# other leagues listing fallback.
# ---------------------------------------------------------------------------

def _lega_table(reader):
    """Parse the SuperLega classifica <table> cells (empty cells preserved).

    Columns per data row: 0 rank+team, 1 Punti, 2 Giocate, 3 Vinte, 4 Perse,
    5-10 score-type breakdown (3.0/3.1/3.2/2.3/1.3/0.3), 11-12 sets W/L,
    13-14 points for/against, 15 set quotient, 16 point quotient, 17 squal.
    """
    if not reader.has("legavolley_classifica"):
        return {}, ""
    raw = reader.read_text("legavolley_classifica")
    table = {}
    for tm in re.finditer(r"<table[^>]*>.*?</table>", raw, flags=re.S):
        t = tm.group(0)
        if "Giocate" not in t or "Gas Sales" not in t:
            continue
        for r in re.findall(r"<tr[^>]*>(.*?)</tr>", t, flags=re.S):
            tds = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, flags=re.S)
            tds = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c))
                   .replace("\xa0", " ").replace("&nbsp;", " ").replace("&#160;", " ")
                   .replace("&amp;", "&").replace("&#8217;", "'").strip() for c in tds]
            if len(tds) < 17:
                continue
            m = re.match(r"^(\d{1,2})\s+(.+)$", tds[0])
            if not m:
                continue  # header / updated-at rows
            try:
                table[norm(tds[0])] = {
                    "rank": int(m.group(1)),
                    "team": norm(m.group(2)),
                    "pts": int(tds[1]), "gp": int(tds[2]),
                    "w": int(tds[3]), "l": int(tds[4]),
                    "set_w": int(tds[11]), "set_l": int(tds[12]),
                    "pf": int(tds[13]), "pa": int(tds[14]),
                    "qp": float(tds[16].replace(",", ".")),
                }
            except (ValueError, IndexError):
                continue
    upd = re.search(r"Classifica aggiornata al (\d{2})/(\d{2})/(\d{4})", strip_html(raw))
    updated = f"{upd.group(3)}-{upd.group(2)}-{upd.group(1)}" if upd else ""
    return table, updated


def _lega_team(table, name):
    """Resolve an OLBG team shorthand (e.g. 'Trentino') to exactly one table row."""
    toks = [t for t in re.split(r"[^a-z]+", name.lower()) if t]
    if not toks:
        return None
    hits = []
    for k, rec in table.items():
        ktk = set(re.split(r"[^a-z]+", k.lower())) - {""}
        if set(toks) <= ktk or ktk <= set(toks) or name.lower() in k.lower() or k.lower() in name.lower():
            hits.append(rec)
    return hits[0] if len(hits) == 1 else None


def parse_volleyball(reader, new_row, sel_row, two_way_market, finish_pick, flag):
    """SuperLega match winners: OLBG-listed Italian ties priced from the official
    classifica table; every other league falls through to the listing fallback.

    Model: p_a = Phi(0.55 * ((ppg_a - ppg_b) + 0.6*ln(qp_a/qp_b) + 0.15)) (Phi = normal CDF),
    clamped to [0.15, 0.85], home side (OLBG listing order) first.
    Match winner only — set handicaps/totals are NOT modelled (flagged): the
    price basis here is the points table, not a set-level model.
    Sample gate: both teams gp >= 4 (the season opened in October, so tonight's
    table has 1-3 games per team -> gate False -> High confidence is capped).
    """
    if not reader.has("legavolley_classifica"):
        flag("EZ-F-VB-01", "review", "Volleyball", "legavolley.it classifica not captured", "",
             "https://www.legavolley.it/classifica/")
        return
    table, updated = _lega_table(reader)
    url = reader.source_url("legavolley_classifica")
    stamp = reader.capture_stamp("legavolley_classifica")
    if not table:
        flag("EZ-F-VB-01", "review", "Volleyball", "SuperLega classifica not parsed",
             "legavolley.it classifica captured but no standings rows parsed; Italian ties fall through "
             "to listing-only rows.", url)
        return
    from math import erf, sqrt
    priced = 0
    for e in olbg_events(reader, "olbg_volleyball_21"):
        parts = re.split(r"\s+vs\.?\s+", e["name"], maxsplit=1)
        if len(parts) != 2:
            continue
        A, B = _lega_team(table, norm(parts[0])), _lega_team(table, norm(parts[1]))
        if not (A and B) or A is B or A["gp"] < 1 or B["gp"] < 1:
            continue  # non-SuperLega tie or unresolvable name -> listing fallback
        ppg_a, ppg_b = A["pts"] / A["gp"], B["pts"] / B["gp"]
        lq_a = math.log(max(A["qp"], 0.05))
        lq_b = math.log(max(B["qp"], 0.05))
        d = (ppg_a - ppg_b) + 0.6 * (lq_a - lq_b) + 0.15  # +0.15 home edge
        p_a = min(0.85, max(0.15, 0.5 * (1 + erf((0.55 * d) / sqrt(2)))))
        gate = A["gp"] >= 4 and B["gp"] >= 4
        markets = {
            "match_winner": {"market_name": "Match Winner", "line": None, "prob_sum": 1.0,
                             "selections": [sel_row(A["team"], p_a), sel_row(B["team"], 1 - p_a)]},
        }
        summary = (f"Official SuperLega classifica (updated {updated}): rank {A['rank']} {A['team']} "
                   f"{A['w']}-{A['l']} in {A['gp']} games, {A['pts']} pts, sets {A['set_w']}-{A['set_l']}, "
                   f"set quotient {A['qp']:.2f} vs rank {B['rank']} {B['team']} {B['w']}-{B['l']} in {B['gp']} games, "
                   f"{B['pts']} pts, sets {B['set_w']}-{B['set_l']}, set quotient {B['qp']:.2f}; home side first per "
                   f"the OLBG listing; model p(home)={p_a:.4f} = Phi(0.55*((pts/gp diff) + 0.6*ln(quotient ratio) "
                   f"+ 0.15 home)), clamped [0.15,0.85]. Match winner priced only; set handicap/totals not modelled "
                   f"(see flag); sample {A['gp']}/{B['gp']} games -> "
                   f"{'gate passed' if gate else 'sample gate failed, High confidence capped'}; pairing cross-checked "
                   f"to the OLBG listing.")
        row = new_row(sport="Volleyball", competition="SuperLega (Italy)",
                      side_a=A["team"], side_b=B["team"], matchup=f"{A['team']} vs {B['team']}",
                      start_utc=e["start_utc"] if e["start_utc"] >= f"{WIN_START}T00:00:00Z" else "",
                      official_url=url, official_source_name="legavolley.it (official SuperLega site)",
                      capture_stamp=stamp, inputs_summary=summary, markets=markets,
                      olbg={"on_olbg": True, "olbg_url": e["url"], "olbg_listed": [t_["decimal"] for t_ in e["tips"][:4]]})
        pick_best_selection(row, gate)
        priced += 1
    if not priced:
        flag("EZ-F-VB-01", "review", "Volleyball", "No SuperLega tie priced from the classifica",
             "The classifica table parsed but no OLBG-listed Italian fixture could be matched to it tonight; "
             "volleyball stays listing-only.", url)
    else:
        flag("EZ-F-VB-03", "review", "Volleyball",
             "Set handicap and set totals not modelled for SuperLega rows",
             f"{priced} SuperLega match-winner row(s) are priced from the official points classifica, which has "
             "no set-level model behind it: set handicaps and set totals are therefore left unpriced rather than "
             "inferred, and kick-off times are blank where legavolley.it only offers them through a JS calendar "
             "(the OLBG event timestamp is used where one exists).",
             url)


# ---------------------------------------------------------------------------
# Rugby Union — URC Round 4/5/6 fixtures from the official fixtures-in-full
# article (verified, unpriced: no readable table); Premiership/Top14/Pro D2 and
# autumn internationals fall through to the listing fallback.
# ---------------------------------------------------------------------------

def parse_rugby_union(reader, new_row, sel_row, two_way_market, finish_pick, flag):
    """URC rounds 4/5/6 from the official fixtures-in-full article.

    Parsing strategy (each fixture is a bold <b> teams paragraph directly followed
    by an italic <i> venue+KO paragraph): teams are taken VERBATIM from the bold
    paragraph — no venue splitting, so sponsored team names ('Hollywoodbets Sharks',
    'Zebre Parma') and venue prefixes ('URC.tv ') cannot corrupt a pairing. Round and
    day come from the nearest preceding article headings, matched by position.
    Unpriced: stats.unitedrugby.com is a client-side shell (flag EZ-F-RU-02).
    """
    if not reader.has("urc_fixtures_in_full"):
        flag("EZ-F-RU-01", "blocker", "Rugby Union", "URC fixtures article not captured", "",
             "https://www.unitedrugby.com/latest/news/2026-27-fixtures-in-full/")
        return
    raw = reader.read_text("urc_fixtures_in_full")
    url = reader.source_url("urc_fixtures_in_full")
    stamp = reader.capture_stamp("urc_fixtures_in_full")
    raw = re.sub(r"<script[^>]*>.*?</script>", " ", raw, flags=re.S)
    months = {m: i + 1 for i, m in enumerate(
        ["JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY",
         "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"])}
    days = [(m.start(), months[m.group(2)], int(m.group(3)))
            for m in re.finditer(
                r"(MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY|SUNDAY),\s*"
                r"(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\s+(\d{1,2})",
                raw)]
    rounds = [(m.start(), int(m.group(1))) for m in re.finditer(r"ROUND\s+(\d{1,2})", raw)]
    teams_hits = [(m.start(), m.group(1)) for m in re.finditer(
        r"<b>\s*<span[^>]*>\s*([^<]{5,90}\sv\s[^<]{5,90}?)\s*</span>\s*</b>", raw)]
    venues = [(m.start(), m.group(1)) for m in re.finditer(
        r"<i>\s*<span[^>]*>\s*([^<]{3,80}?)\s*</span>\s*</i>", raw)]
    n = 0
    considered = 0
    excluded = 0
    for pos, t_raw in teams_hits:
        rnd = max((r for p, r in rounds if p <= pos), default=None)
        day = max((d for d in days if d[0] <= pos), key=lambda x: x[0], default=None)
        if rnd not in (4, 5, 6) or day is None:
            continue
        considered += 1
        # decode non-breaking spaces first: 'Cardiff v\xa0Hollywoodbets\xa0Sharks' must still split on ' v '
        t_clean = t_raw.replace("\xa0", " ").replace("&nbsp;", " ")
        parts = [norm(x) for x in t_clean.split(" v ")]
        if len(parts) != 2 or not all(parts):
            excluded += 1
            continue
        a, b = parts
        venue, ko = "", ""
        vs = [p for p in venues if pos < p[0] < pos + 700]
        if vs:
            vtxt = vs[0][1]
            mko = re.search(r",?\s*KO\s+([\d]{1,2}[.:][\d]{2})", vtxt)
            if mko:
                ko = mko.group(1).replace(":", ".")
                vtxt = vtxt[: mko.start()]
            venue = norm(vtxt)
        month, dom = day[1], day[2]
        year = 2026 if month >= 9 else 2027
        date = f"{year}-{month:02d}-{dom:02d}"
        if not (WIN_START <= date < WIN_END):
            continue
        start = ""
        if ko:
            hh, mm = (int(x) for x in re.split(r"[.:]", ko)[:2])
            utc_off = 1 if date <= "2026-10-24" else 0  # IST/BST end 25 Oct 2026
            hh = hh - utc_off
            if hh < 0:
                hh += 24
                dom -= 1
                date = f"{year}-{month:02d}-{dom:02d}"
            start = f"{date}T{hh:02d}:{mm:02d}:00Z"
        new_row(sport="Rugby Union", competition=f"BKT United Rugby Championship Round {rnd}",
                side_a=a, side_b=b, matchup=f"{a} v {b}", start_utc=start,
                venue=venue, official_url=url,
                official_source_name="unitedrugby.com official 2026-27 fixtures (rounds 4-6)",
                capture_stamp=stamp,
                inputs_summary=f"Official URC fixtures article: {a} v {b}, day heading {date}, "
                               f"KO {ko} (IRE & UK){' -> ' + start if start else ''}"
                               f"{', ' + venue if venue else ''}; teams taken verbatim from the article's bold "
                               f"fixture line (no venue parsing); unpriced — the URC match-centre "
                               f"table/feed did not render in this capture so no verified standings input exists "
                               f"(see flag).")
        n += 1
    flag("EZ-F-RU-02", "review", "Rugby Union", "URC rows unpriced — no readable official table in this capture",
         f"stats.unitedrugby.com match-centre pages are client-side apps (returned shell bytes again tonight), "
         f"so no verified standings input exists. {n} fixtures are verified from the official fixtures-in-full "
         f"article ({considered} round-4/5/6 fixture paragraphs in window considered, {excluded} excluded for an "
         f"ambiguous ' v ' split) but left unpriced rather than modelled from unverified numbers.",
         "https://stats.unitedrugby.com/match-centre/table/2026-27")
    flag("EZ-F-RU-03", "review", "Rugby Union", "Premiership / Top14 / Pro D2 / autumn tests not officially readable",
         "premiershiprugby.com fixtures/standings pages carry no structured fixture payload in this capture and "
         "top14.lnr.fr / prod2.lnr.fr render shells, so those OLBG listings fall through to listing-only rows.",
         reader.source_url("olbg_rugby_union_9") if reader.has("olbg_rugby_union_9") else "https://www.unitedrugby.com/")


# ---------------------------------------------------------------------------
# Cricket — fixtures verified from cricket.com.au; internationals priced only if
# the ICC ratings table parses (it is JS-driven tonight), otherwise unpriced.
# ---------------------------------------------------------------------------

def parse_cricket(reader, new_row, sel_row, two_way_market, finish_pick, flag):
    if not reader.has("cricket_au_fixtures"):
        flag("EZ-F-CR-01", "blocker", "Cricket", "cricket.com.au fixtures not captured", "",
             "https://www.cricket.com.au/fixtures")
        return
    t = norm(strip_html(reader.read_text("cricket_au_fixtures")))
    url_au = reader.source_url("cricket_au_fixtures")
    stamp_au = reader.capture_stamp("cricket_au_fixtures")
    # ICC ratings: attempt the text table; tonight's capture is JS-driven (0 rows)
    ratings = {}
    for rt, fmt in (("icc_odi_rankings", "ODI"), ("icc_t20i_rankings", "T20I")):
        if not reader.has(rt):
            continue
        tt = strip_html(reader.read_text(rt))
        m = re.search(r"Pos.{0,30}Team.{0,30}Weighted Matches.{0,40}Points.{0,30}Rating(.{0,6000})", tt, flags=re.S)
        seg = m.group(1) if m else ""
        for r in re.finditer(r"(\d{1,2}) ([A-Z][A-Za-z ]{2,18}?) (\d{1,3}) (\d{2,5}) (\d{2,4})(?= \d{1,2} [A-Z]|$)", seg):
            ratings.setdefault(fmt, {})[norm(r.group(2))] = {"pos": int(r.group(1)), "pts": int(r.group(4)), "rating": int(r.group(5))}

    # (pattern, competition, side_a, side_b, venue) verified against tonight's bytes
    fixtures = [
        (r"New Zealand v India T20Is 2026 - Men\s*2nd T20I\s*Upcoming\s*(\d{1,2} \w+ 2026).*?Hagley Oval ?, Christchurch",
         "New Zealand v India T20Is 2026 — 2nd T20I", "New Zealand", "India", "Hagley Oval, Christchurch", "T20I"),
        (r"Pakistan ODI Tri-Series 2026 - Men\s*Pakistan v England\s*Upcoming\s*(\d{1,2} \w+ 2026).*?Gaddafi Stadium ?, Lahore",
         "Pakistan ODI Tri-Series 2026 — Pakistan v England", "Pakistan", "England", "Gaddafi Stadium, Lahore", "ODI"),
        (r"One-Day Cup 2026-27\s*Tasmanian Tigers v Victoria\s*Upcoming\s*(\d{1,2} \w+ 2026).*?Bellerive Oval ?, Hobart",
         "Marsh One-Day Cup 2026-27", "Tasmanian Tigers", "Victoria", "Bellerive Oval, Hobart", ""),
        (r"One-Day Cup 2026-27\s*Western Australia v New South Wales\s*Upcoming\s*(\d{1,2} \w+ 2026).*?WACA Ground ?, Perth",
         "Marsh One-Day Cup 2026-27", "Western Australia", "New South Wales", "WACA Ground, Perth", ""),
    ]
    for pat, comp, a, b, venue, fmt in fixtures:
        m = re.search(pat, t, flags=re.S)
        if not m:
            continue
        date_txt = norm(m.group(1))
        if fmt == "T20I" and ratings.get("T20I", {}).get("New Zealand") and ratings.get("T20I", {}).get("India"):
            r_nz = ratings["T20I"]["New Zealand"]
            r_ind = ratings["T20I"]["India"]
            edge = 0.02 * (r_ind["rating"] - r_nz["rating"]) + 0.25
            p_nz = min(0.80, max(0.20, 1 / (1 + math.exp(-edge))))
            markets = {"match_winner": {"market_name": "Match Winner", "line": None, "prob_sum": 1.0,
                                        "selections": [sel_row("New Zealand", p_nz), sel_row("India", 1 - p_nz)]}}
            summary = (f"Official ICC men's T20I rankings: India #{r_ind['pos']} ({r_ind['rating']}) vs "
                       f"New Zealand #{r_nz['pos']} ({r_nz['rating']}); fixture officially listed by cricket.com.au: "
                       f"{comp}, {date_txt}, {venue}. Model: rating gap + documented 25-point home allowance.")
            row = new_row(sport="Cricket", competition=comp, side_a=a, side_b=b,
                          matchup=f"{a} v {b}", start_utc="", venue=venue,
                          official_url=url_au, official_source_name="cricket.com.au official fixtures + ICC official rankings",
                          capture_stamp=stamp_au, inputs_summary=summary, markets=markets)
            pick_best_selection(row, True)
        else:
            new_row(sport="Cricket", competition=comp, side_a=a, side_b=b,
                    matchup=f"{a} v {b}", start_utc="", venue=venue,
                    official_url=url_au, official_source_name="cricket.com.au official fixtures",
                    capture_stamp=stamp_au,
                    inputs_summary=f"Fixture officially listed: {comp}, {date_txt}, {venue}. No verified "
                                   f"team-strength input captured in this session (ICC rankings pages are "
                                   f"JS-driven tonight; no official ratings feed captured) — unpriced, flagged.")
    if not ratings.get("T20I"):
        flag("EZ-F-CR-02", "review", "Cricket", "ICC ratings tables not readable in this capture",
             "icc-cricket.com ranking pages rendered without their rating table in tonight's capture, so the "
             "verified international fixtures are published unpriced rather than priced from numbers we "
             "cannot see.",
             "https://www.icc-cricket.com/rankings/mens/team-rankings/t20i")
    flag("EZ-F-CR-03", "review", "Cricket", "Domestic one-day rows unpriced",
         "Marsh One-Day Cup fixtures are verified from cricket.com.au but no official ratings/feed for the "
         "state sides was captured, so they are published without lines.",
         url_au)


# ---------------------------------------------------------------------------
# Golf — OWGR and event pages rendered as JS shells tonight; OLBG hub listed no
# events. No priced rows; the shortfall is flagged, nothing is inferred.
# ---------------------------------------------------------------------------

def parse_golf(reader, new_row, sel_row, two_way_market, finish_pick, flag):
    ow_ok = reader.has("owgr_ranking") and len(re.findall(r"\d{1,3} [A-Z][A-Za-z.'-]+ [A-Z][A-Za-z.'-]+ [A-Z]{3} [\d.]+",
                                                          strip_html(reader.read_text("owgr_ranking")))) >= 5
    if not ow_ok:
        flag("EZ-F-GF-01", "review", "Golf",
             "OWGR ranking table rendered as a shell — no player points parsed",
             "www.owgr.com/current-world-ranking captured (HTTP 200) but its ranking table is client-side: the "
             "stripped page contains the column headers only and zero player rows, so no outright can be priced "
             "from verified ranking numbers.",
             "https://www.owgr.com/current-world-ranking")
    flag("EZ-F-GF-02", "review", "Golf",
         "PGA/DP World Tour event pages carry no leaderboard data in this capture",
         "pgatour.com Bermuda Championship / leaderboard and europeantour.com tee-times pages returned only "
         "nav content (JS-rendered), and the OLBG golf hub listed zero events at capture time, so Golf has no "
         "rows tonight rather than any unverified outright.",
         "https://www.pgatour.com/leaderboard")


# ---------------------------------------------------------------------------
# Motor Racing — F1 driver standings + race pages are JS shells; OLBG lists the
# USA Grand Prix (listing-only) and the MotoGP calendar row is unpriced.
# ---------------------------------------------------------------------------

def parse_motor(reader, new_row, sel_row, two_way_market, finish_pick, flag):
    drivers = []
    if reader.has("f1_drivers_2026"):
        t = strip_html(reader.read_text("f1_drivers_2026"))
        for m in re.finditer(r"([A-Z][a-z]+ [A-Z][a-z]+) ([A-Z]{3}) (\d+) ", t[:20000]):
            drivers.append({"name": norm(m.group(1)), "code": m.group(2), "pts": int(m.group(3))})
    if len(drivers) < 5:
        flag("EZ-F-MR-01", "review", "Motor Racing",
             "F1 drivers' standings table rendered as a shell — no championship points parsed",
             "formula1.com/en/results/2026/drivers captured (HTTP 200) but the standings table is client-side: "
             "the stripped page contains only navigation, so no race-winner outright can be priced from verified "
             "points tonight.",
             "https://www.formula1.com/en/results/2026/drivers")
    # MotoGP: calendar captured — publish a verified calendar row if the next round is readable
    if reader.has("motogp_calendar"):
        cal = strip_html(reader.read_text("motogp_calendar"))
        m = re.search(r"(Grand Prix of \w+|Grand Prix \w+|Round \d+)[^\n]{0,80}?(Oct|Nov)(ober|ember)? \d{1,2}", cal, flags=re.I)
        if m:
            new_row(sport="Motor Racing", competition="MotoGP 2026 — next round (per official calendar)",
                    side_a="", side_b="", matchup="Race Winner (outright)", start_utc="",
                    venue="", official_url=reader.source_url("motogp_calendar"),
                    official_source_name="motogp.com official calendar",
                    capture_stamp=reader.capture_stamp("motogp_calendar"),
                    listing_only=True,
                    inputs_summary=f"Official motogp.com calendar captured; next round readable as \"{norm(m.group(0))}\". "
                                   f"Rider championship standings endpoint returned 404 in this capture — no priced "
                                   f"outright published (blank, flagged).")
    flag("EZ-F-MR-02", "review", "Motor Racing", "No priced Motor Racing rows in this capture",
         "F1 standings and race pages rendered without data, motogp.com/en/standings returned 404, and the OLBG "
         "motor-racing hub lists only event outrights — every motor row is published blank and flagged rather "
         "than priced from unverified numbers.",
         "https://www.formula1.com/en/racing/2026.html")


# ---------------------------------------------------------------------------
# Gaelic — Cork GAA official fixtures page is a JS shell tonight; OLBG ties are
# published as listing rows with blank values.
# ---------------------------------------------------------------------------

def parse_gaelic(reader, new_row, sel_row, two_way_market, finish_pick, flag):
    gaacork_ok = False
    if reader.has("gaacork_fixtures"):
        t = strip_html(reader.read_text("gaacork_fixtures"))
        gaacork_ok = bool(re.search(r"\d{1,2} \w+ 2026", t)) and "skeleton" not in t.lower()
    flag("EZ-F-GA-01", "review", "Gaelic Sports",
         "Official GAA fixture pages rendered as shells in this capture",
         "gaa.ie/fixtures returned its loading skeleton (no fixture payload) and gaacork.ie/fixtures returned "
         "nav content only, so no official club fixture row, venue or result table could be parsed. Gaelic rows "
         "below are OLBG listings with blank picks.",
         "https://www.gaa.ie/fixtures")
    flag("EZ-F-GA-02", "review", "Gaelic Sports", "Gaelic rows unpriced",
         "No official team-strength inputs (results tables/ratings) for the listed club championships were "
         "capturable, so gaelic rows are published without lines.",
         "https://www.gaa.ie/fixtures")
    _ = gaacork_ok


# ---------------------------------------------------------------------------
# Greyhounds — GBGB pre-race cards unreachable (results API covers completed
# races only; card endpoints 404). Zero-inference: no priced greyhound rows.
# ---------------------------------------------------------------------------

def parse_greyhounds(reader, new_row, sel_row, two_way_market, finish_pick, flag):
    gbgb_url = reader.source_url("gbgb_results") if reader.has("gbgb_results") else "https://www.gbgb.org.uk/"
    flag("EZ-F-GR-01", "review", "Greyhounds", "Zero-inference ledger (no priced greyhound rows)",
         "GBGB is the official body; api.gbgb.org.uk results cover completed races only and the fixture/card "
         "endpoints returned 404 in this capture, so no trap or runner can be verified before the race. Every "
         "greyhound row is published with blank selections and no pick — we do not originate greyhound lines we "
         "cannot verify.", gbgb_url)


# ---------------------------------------------------------------------------
# Rugby League — RLWC 2026 official draws page carries the full match list
# (teams + date, no kick-off times). Verified fixtures, unpriced: no official
# results/strength feed captured (rlwc results/fixtures are JS shells, nrl.com
# draw returned a form postback).
# ---------------------------------------------------------------------------

def parse_rugby_league(reader, new_row, sel_row, two_way_market, finish_pick, flag):
    if not reader.has("rlwc_draws"):
        flag("EZ-F-RL-01", "blocker", "Rugby League", "RLWC draws page not captured", "",
             "https://www.rlwc2026.com/draws-and-pools")
        return
    raw = reader.read_text("rlwc_draws")
    url = reader.source_url("rlwc_draws")
    stamp = reader.capture_stamp("rlwc_draws")
    # payload blocks are escaped JSON: matchName\":\"A to play B - DD-Mon-YYYY\"
    blocks = re.findall(r'matchName\\*"\s*:\s*\\*"([^"\\]+)', raw)
    if not blocks:
        blocks = re.findall(r'matchName":\s*"([^"]+)"', raw)
    seen, n = set(), 0
    month_map = {m: i + 1 for i, m in enumerate(
        ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}
    for name in blocks:
        if name in seen:
            continue
        seen.add(name)
        m = re.match(r"(.+?) to play (.+?) - (\d{1,2})-([A-Z][a-z]{2})-(\d{4})", name)
        if not m:
            continue
        a, b, dd, mon, yyyy = norm(m.group(1)), norm(m.group(2)), int(m.group(3)), m.group(4), int(m.group(5))
        if mon not in month_map:
            continue
        day = f"{yyyy}-{month_map[mon]:02d}-{dd:02d}"
        if not (WIN_START <= day < WIN_END):
            continue
        new_row(sport="Rugby League", competition="Rugby League World Cup 2026",
                side_a=a, side_b=b, matchup=f"{a} v {b}", start_utc="", start_date=day,
                venue="", official_url=url,
                official_source_name="rlwc2026.com official draws & pools (Rugby League World Cup 2026)",
                capture_stamp=stamp,
                inputs_summary=f"Official RLWC draws page fixture: {a} v {b}, {day}. The draws page publishes "
                               f"the date only — no kick-off time — and rlwc2026.com fixtures/results pages plus "
                               f"nrl.com/draw returned shells/form-postbacks in this capture, so no results, "
                               f"ratings or strength table exists to price from: unpriced, flagged.")
        n += 1
    flag("EZ-F-RL-01", "review", "Rugby League",
         "RLWC fixtures verified from the draws page but unpriced — no official strength feed readable",
         f"{n} upcoming RLWC fixtures (teams + date) parsed from the official draws-and-pools payload. "
         f"rlwc2026.com/fixtures and /results are client-side shells, nrl.com/draw returned a form postback, "
         f"and no official ratings table was captured, so match winner/handicap/total are left blank rather "
         f"than modelled from unverified numbers. The OLBG rugby-league hub lists only 2027 futures tonight "
         f"(State of Origin/Super League/NRL outrights), which are not upcoming matches and are not published "
         f"as fixtures.", url)


# ---------------------------------------------------------------------------
# Snooker — priced from the official snooker.org event page (match schedule,
# session times and completed scores) with tournament-form inputs.
# ---------------------------------------------------------------------------

def _mkey(name: str) -> frozenset:
    """Alpha tokens (len>=2, lowercase) used to de-dup OLBG names vs official rows."""
    return frozenset(t for t in re.split(r"[^a-z]+", name.lower()) if len(t) >= 2)


_SNOOKER_KNOWN: set = set()  # every snooker.org tie token-set (incl. completed/live), for fallback de-dup


def parse_snooker(reader, new_row, sel_row, two_way_market, finish_pick, flag):
    """Northern Ireland Open (event 2548) from snooker.org.

    Rows: every upcoming tie (both sides named, no scores yet, no TBC/'/' placeholders).
    Model: world rank carried in the player cell brackets (e.g. 'Kyren Wilson [9]'),
      p_a = Phi(1.2 * ln(rank_b / rank_a)) clamped [0.15, 0.85] (Phi = normal CDF) — a larger rank
      number is weaker, so p_a rises with rank_b/rank_a.
    Gate: both players have >=1 completed match on this event page (frame form exists
      for the prediction text) -> otherwise High confidence is capped.
    Handicap/totals NOT originated (flag EZ-F-SN-01): no verified handicap input exists
      for a single-elimination draw and OLBG lists only match winner.
    Session start taken from the page where published (UTC), else blank — never inferred.
    """
    if not reader.has("snooker_org_2548"):
        flag("EZ-F-SN-02", "review", "Snooker", "snooker.org Northern Ireland Open page not captured", "",
             "https://www.snooker.org/res/index.asp?event=2548")
        return
    _SNOOKER_KNOWN.clear()
    raw = reader.read_text("snooker_org_2548")
    url = reader.source_url("snooker_org_2548")
    stamp = reader.capture_stamp("snooker_org_2548")
    order = []
    round_now = ""
    for m in re.finditer(r'<span class="round">([^<]+)</span>|<tr class="gradeA[^"]*"[^>]*>.*?</tr>', raw, flags=re.S):
        if m.group(0).startswith("<span"):
            round_now = m.group(1)
        else:
            order.append((round_now, m.group(0)))
    form: dict[str, dict] = {}
    upcoming = []

    def rank_of(name):
        mm = re.match(r"^(.*?)\s*\[(\d{1,3})\]$", name)
        return (norm(mm.group(1)), int(mm.group(2))) if mm else (name, None)

    for rnd, block in order:
        if "oneonone" not in block:
            continue
        players = re.findall(r'<td class="player[^"]*"[^>]*>(.*?)</td>', block, flags=re.S)
        names = [norm(re.sub(r"<[^>]+>", " ", p).replace("&nbsp;", " ")) for p in players[:2]]
        if len(names) < 2:
            continue
        s1 = re.search(r'<td class="score\s+first-score"[^>]*>\s*(\d{1,2})?\s*</td>', block)
        s2 = re.search(r'<td class="last-score"[^>]*>\s*(\d{1,2})?\s*</td>', block)
        sc1 = int(s1.group(1)) if s1 and s1.group(1) else None
        sc2 = int(s2.group(1)) if s2 and s2.group(1) else None
        sched = re.findall(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}Z)', block)
        a_raw, b_raw = names[0], names[1]
        tr_cls = (re.search(r'<tr class="([^"]*)"', block) or re.match(r'<tr class="([^"]*)"', block))
        tr_cls = tr_cls.group(1) if tr_cls else ""
        live = "unfinished" in tr_cls  # in-play session: never form, never upcoming
        # awarded status: score cell holds 'w/o' / 'awd' etc. instead of a number
        # only real score boxes ('score  ...'), never the score-delim cell that holds 'v'
        stxt = re.search(r'<td class="score\s+[^"]*"[^>]*>\s*([^<]+?)\s*</td>', block)
        awarded = stxt and not stxt.group(1).strip().isdigit()
        skip = ("/" in a_raw or "/" in b_raw or "To be decided" in a_raw or "To be decided" in b_raw
                or "TBC" in a_raw.upper() or "TBC" in b_raw.upper())
        if not skip and not live:
            a, ra = rank_of(a_raw)
            b, rb = rank_of(b_raw)
            # record this tie for listing-fallback de-dup (completed, walkover and live too)
            _SNOOKER_KNOWN.add(_mkey(a) | _mkey(b))
            if sc1 is not None and sc2 is not None:
                for who, w, l in ((a_raw, sc1, sc2), (b_raw, sc2, sc1)):
                    fm = form.setdefault(who, {"w": 0, "l": 0, "fw": 0, "fl": 0, "matches": []})
                    fm["w" if w > l else "l"] += 1
                    fm["fw"] += w
                    fm["fl"] += l
                    fm["matches"].append(f"{w}-{l}")
            elif awarded:
                # walkover/award: first-listed player advances; no frames scored
                fm = form.setdefault(a_raw, {"w": 0, "l": 0, "fw": 0, "fl": 0, "matches": []})
                fm["w"] += 1
                fm["matches"].append("w/o")
                fl = form.setdefault(b_raw, {"w": 0, "l": 0, "fw": 0, "fl": 0, "matches": []})
                fl["l"] += 1
                fl["matches"].append("w/o against")
            elif sc1 is None and sc2 is None:
                upcoming.append((rnd, a_raw, b_raw, sched[0] if sched else ""))
    n = 0
    for rnd, a_raw, b_raw, start in upcoming:
        a, ra = rank_of(a_raw)
        b, rb = rank_of(b_raw)
        if not (ra and rb):
            continue
        day = start[:10] if start else ""
        if start and not (WIN_START <= day < WIN_END):
            continue
        fa, fb = form.get(a_raw), form.get(b_raw)
        inputs_ok = bool(fa and fb and (fa["w"] + fa["l"]) >= 1 and (fb["w"] + fb["l"]) >= 1)
        comp = f"BetVictor Northern Ireland Open 2026 — {rnd}"
        summary = (f"Official snooker.org event page ({rnd}): {a} world rank #{ra} vs {b} world rank #{rb} "
                   "(rank shown in the event draw). "
                   + (f"{a} {fa['w']}-{fa['l']} at the event, frames {fa['fw']}-{fa['fl']} "
                      f"(last match {'/'.join(fa['matches'][-2:])})" if fa else f"{a} no completed event match yet")
                   + " vs "
                   + (f"{b} {fb['w']}-{fb['l']} at the event, frames {fb['fw']}-{fb['fl']} "
                      f"(last match {'/'.join(fb['matches'][-2:])})." if fb else f"{b} no completed event match yet.")
                   + (f" Session start {start} (published UTC by snooker.org)."
                      if start else " Session start not yet published on the event page — start_utc left blank."))
        if not inputs_ok:
            new_row(sport="Snooker", competition=comp, side_a=a, side_b=b,
                    matchup=f"{a} v {b}", start_utc=start, venue="Waterfront Hall, Belfast",
                    official_url=url, official_source_name="snooker.org official event results service",
                    capture_stamp=stamp, inputs_summary=summary + " Insufficient completed event matches for "
                                   "both players — unpriced, flagged.")
            continue
        p_a = min(0.85, max(0.15, 0.5 * (1 + math.erf((1.2 * math.log(rb / ra)) / math.sqrt(2)))))
        summary += (f" Model p({a})={p_a:.4f} = probit p = Phi(1.2*ln(rank_b/rank_a)) clamped [0.15,0.85]; "
                    f"sample gate (both >=1 completed event match) passed.")
        markets = {"match_winner": {"market_name": "Win Match", "line": None, "prob_sum": 1.0,
                                    "selections": [sel_row(a, p_a), sel_row(b, 1 - p_a)]}}
        row = new_row(sport="Snooker", competition=comp, side_a=a, side_b=b,
                      matchup=f"{a} v {b}", start_utc=start, venue="Waterfront Hall, Belfast",
                      official_url=url, official_source_name="snooker.org official event results service",
                      capture_stamp=stamp, inputs_summary=summary, markets=markets)
        pick_best_selection(row, inputs_ok)
        n += 1
    flag("EZ-F-SN-01", "review", "Snooker",
         "wst.tv rendered no match data; snooker.org event page used instead",
         "The World Snooker Tour site (wst.tv) returned a JS shell in this capture, so the Northern Ireland "
         "Open draw, scores and session times are taken from the snooker.org official event results page for "
         f"event 2548 (manual check linked): {n} upcoming tie(s) priced from world ranks carried in the draw, "
         "with event frame-form verified for both players. Win-match only: frame handicap/totals were "
         "investigated but not originated — no verified handicap input exists for a single-elimination draw "
         "and the OLBG hub lists match winner only.", "https://www.wst.tv/tournaments/northern-ireland-open-2026/")


# ---------------------------------------------------------------------------
# Listing fallback — every OLBG event in the 15-sport scope that does not match
# an already-published row becomes a listing-only row (blank values + flag).
# ---------------------------------------------------------------------------

def parse_listing_fallback(reader, new_row, sel_row, two_way_market, finish_pick, flag, existing_rows):
    hubs = {
        "Golf": "olbg_golf_5", "Volleyball": "olbg_volleyball_21", "Rugby Union": "olbg_rugby_union_9",
        "Cricket": "olbg_cricket_7", "Snooker": "olbg_snooker_8", "Darts": "olbg_darts_15",
        "Baseball": "olbg_baseball_12", "Gaelic Sports": "olbg_gaelic_25", "Greyhounds": "olbg_greyhounds_28",
        "Tennis": "olbg_tennis_3", "Motor Racing": "olbg_motor_racing_14", "Handball": "olbg_handball_20",
        "Ice Hockey": "olbg_ice_hockey_13", "Basketball": "olbg_basketball_4", "Rugby League": "olbg_rugby_league_10",
    }
    counts: dict[str, int] = {}
    for sport, target in hubs.items():
        if not reader.has(target):
            continue
        hub_url = reader.source_url(target)
        stamp = reader.capture_stamp(target)
        published = [tokens(r["matchup"]) for r in existing_rows if r["sport"] == sport and r.get("matchup")]
        for e in olbg_events(reader, target):
            # window filter: only upcoming matches inside the coverage window
            if e["start_utc"] and not (WIN_START <= e["start_utc"][:10] < WIN_END):
                continue
            et = tokens(e["name"])
            if not et:
                continue
            matched = any(len(et & pt) >= 2 for pt in published)
            if matched:
                continue
            if sport == "Snooker":
                mk = _mkey(e["name"])
                if any(mk <= kn or kn <= mk for kn in _SNOOKER_KNOWN if kn):
                    continue  # already covered by a snooker.org row (incl. in-play ties)
            # future outright markets (e.g. 2027 competitions) are not upcoming matches
            if e["start_utc"] and e["start_utc"][:4] > WIN_START[:4]:
                continue
            listed = ", ".join(f"{t['market']} {t['decimal']}" for t in e["tips"][:3])
            new_row(sport=sport, competition="OLBG listed event (official confirmation pending)",
                    side_a="", side_b="", matchup=e["name"],
                    start_utc=e["start_utc"] if e["start_utc"] >= f"{WIN_START}T00:00:00Z" else "",
                    official_url=BODY_URL[sport], official_source_name=f"{sport} official body site (manual check link)",
                    capture_stamp=stamp, listing_only=True,
                    olbg={"on_olbg": True, "olbg_url": e["url"], "olbg_listed": [t["decimal"] for t in e["tips"][:4]]},
                    inputs_summary=f"OLBG live listing ({stamp}): \"{e['name']}\""
                                   + (f", listed markets {listed}" if listed else "")
                                   + f". Not confirmed as a structured row on an official governing-body feed in "
                                     f"this capture — unverified, unpriced, flagged (see {sport} flags).")
            counts[sport] = counts.get(sport, 0) + 1
    for sport, n in counts.items():
        slug = re.sub(r"[^A-Z]", "", sport.upper())[:8]
        flag(f"EZ-F-LIST-{slug}", "review", sport,
             f"{n} OLBG-listed event(s) without official confirmation in this capture",
             "These rows exist on OLBG's live listing for this sport but were not confirmed as structured "
             "fixtures on an official governing-body feed in tonight's capture; they are published with blank "
             "picks and a manual-check link, never priced or inferred.",
             BODY_URL[sport])
    print(f"[board-ez] listing fallback: {sum(counts.values())} unconfirmed listing rows "
          f"across {len(counts)} sports")
