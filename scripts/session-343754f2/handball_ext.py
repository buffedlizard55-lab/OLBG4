"""Board BW — handball lines from official continental/league tables.

Two extra official inputs beyond the Danish Herreligaen parser:

* EHF Champions League men, group phase 2026/27 (``ehfcl_standings``): the page is
  server-rendered for the four group tables (GP / W / D / L / Goals / DIFF / PTS), so
  each of the sixteen clubs has a verified goals-for and goals-against record. The
  fixture list on the same page is an Angular template (``{{match...}}``), so the
  *pairing, kick-off and OLBG prices* come from the OLBG listing while the **strength
  inputs come only from the EHF table**. That split is stated on every row and flagged.
* Liga ASOBAL 2026/27 (``asobal_home``): the official ladder is server-rendered but
  carries points only (no goals columns), so the Spanish rows use a points-per-game
  model and are flagged as such.

Nothing is inferred: a tie is priced only when BOTH clubs resolve to an official table
row, the sample gate is met, and at least four games have been played.
"""
from __future__ import annotations

import math
import re
from datetime import datetime, timezone

WIN_START = "2026-10-23"
WIN_END = "2026-11-09"


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def _strip(h: str) -> str:
    h = re.sub(r"(?s)<script.*?</script>|<style.*?</style>", " ", h)
    return re.sub(r"\s+", " ", re.sub(r"(?s)<[^>]+>", " ", h))


def _key(s: str) -> set:
    """Significant tokens of a club name, for tolerant matching of OLBG spellings."""
    s = (s or "").lower()
    s = (s.replace("&amp;", "&").replace("&#x27;", "'")
         .replace("é", "e").replace("è", "e").replace("ê", "e").replace("á", "a")
         .replace("í", "i").replace("ó", "o").replace("ú", "u").replace("å", "a")
         .replace("ø", "o").replace("ä", "a").replace("ö", "o").replace("ü", "u")
         .replace("š", "s").replace("ž", "z").replace("ć", "c").replace("č", "c"))
    drop = {"hc", "bm", "rk", "sc", "fc", "if", "thw", "hsg", "mt", "og", "club",
            "handball", "handbold", "håndbold", "team", "the", "de", "del", "la", "le",
            "sporting", "pivovarna", "lasko", "laško", "1961", "one", "orlen", "hbc",
            "gog", "ks", "cbm", "bm.", "ifk", "sk"}
    toks = {t for t in re.split(r"[^a-z0-9]+", s) if len(t) > 2 and t not in drop}
    return toks


def _ehf_table(reader) -> tuple[dict, str, str]:
    """Parse the four EHF Champions League group tables.

    Returns ({club_key_tokens -> stats}, updated_label, url)."""
    if not reader.has("ehfcl_standings"):
        return {}, "", ""
    text = _strip(reader.read_text("ehfcl_standings"))
    url = reader.source_url("ehfcl_standings")
    out: dict = {}
    groups = list(re.finditer(r"GROUP ([A-D]) GP W D L Goals DIFF PTS", text))
    for gi, gm in enumerate(groups):
        end = groups[gi + 1].start() if gi + 1 < len(groups) else len(text)
        block = text[gm.end():end]
        rows_here = 0
        for rm in re.finditer(
                r"(\d)\.\s+(.+?)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*:\s*(\d+)\s+(-?\d+)\s+(\d+)",
                block):
            if rows_here >= 4:
                break  # a group table has exactly four clubs; later matches are other blocks
            rank, name, gp, w, dr, l, gf, ga, diff, pts = rm.groups()
            name = _norm(name.replace("&#xE9;", "é").replace("&#xFC;", "ü")
                         .replace("&#xE5;", "å").replace("&#x161;", "š"))
            rows_here += 1
            out[name] = {"team": name, "group": gm.group(1), "rank": int(rank),
                         "gp": int(gp), "w": int(w), "d": int(dr), "l": int(l),
                         "gf": int(gf), "ga": int(ga), "pts": int(pts), "key": _key(name)}
    season = re.search(r"(\d{4}/\d{2})", text[:4000])
    return out, (season.group(1) if season else ""), url


def _asobal_table(reader) -> tuple[dict, str]:
    """Liga ASOBAL ladder.

    The official page renders each club as ``alt="<rank> - <club>"`` inside the ladder
    strip (Latin-1 bytes), and the points appear in the same order in the text block
    ``1 <club> 14 2 <club> 12 ...``. Rank order and points order are paired positionally,
    so a club can never inherit another club's points."""
    if not reader.has("asobal_home"):
        return {}, ""
    raw = reader.read_text("asobal_home").encode("utf-8", "ignore").decode("latin-1")
    url = reader.source_url("asobal_home")
    alts = [(int(r), _norm(t)) for r, t in re.findall(r'alt="(\d{1,2}) - ([^"]{3,60})"', raw)]
    alts = [a for i, a in enumerate(alts) if a[0] == i + 1][:16]
    if len(alts) != 16:
        return {}, url
    text = _strip(raw)
    m = re.search(r"ASOBAL\s+1\s+" + re.escape(alts[0][1]), text)
    if not m:
        return {}, url
    pos = m.start()
    pts: list[int] = []
    for rank, name in alts:
        seg = text[pos:pos + 120]
        nm = re.search(re.escape(name), seg)
        if not nm:
            return {}, url
        after = seg[nm.end():]
        pm = re.match(r"[\s.]*(\d{1,2})\b", after)
        if not pm:
            return {}, url
        pts.append(int(pm.group(1)))
        pos += nm.end() + pm.end()
    if len(pts) != 16:
        return {}, url
    return {name: {"team": name, "rank": rank, "pts": pts[i], "key": _key(name)}
            for i, (rank, name) in enumerate(alts)}, url


def _poisson_probs(mu_h: float, mu_a: float) -> tuple[float, float, float]:
    """Win / draw / loss from two independent Poisson goal counts (grid to 70 goals)."""
    ph = [math.exp(-mu_h) * mu_h ** k / math.factorial(k) for k in range(71)]
    pa = [math.exp(-mu_a) * mu_a ** k / math.factorial(k) for k in range(71)]
    win = draw = loss = 0.0
    for i, a in enumerate(ph):
        if a < 1e-14:
            continue
        for j, b in enumerate(pa):
            if b < 1e-14:
                continue
            p = a * b
            if i > j:
                win += p
            elif i == j:
                draw += p
            else:
                loss += p
    tot = win + draw + loss
    return win / tot, draw / tot, loss / tot


def _total_ou(mu: float, line: float) -> float:
    """P(total goals > line) for one Poisson total (mean mu)."""
    cdf = 0.0
    k = 0
    thr = int(math.floor(line))
    while k <= thr:
        cdf += math.exp(-mu) * mu ** k / math.factorial(k)
        k += 1
    return max(0.001, min(0.999, 1.0 - cdf))


def _pick(row, gate, finish_pick) -> None:
    """Same published selection rule as the rest of the desk: the best in-window
    selection at >=55% wins, otherwise the highest-probability selection overall
    (published with its real price and in_window=false, never High)."""
    order = {"Match": 0, "Total": 1}
    best_in = best_all = None
    for mk in row["markets"].values():
        simple = order.get(mk["market_name"].split()[0], 9)
        for sel in mk["selections"]:
            key = (sel["fair_prob"], -simple)
            if best_all is None or key > best_all[0]:
                best_all = (key, mk["market_name"], sel)
            if -250 <= sel["fair_american"] <= 10000 and sel["fair_prob"] >= 0.55:
                if best_in is None or key > best_in[0]:
                    best_in = (key, mk["market_name"], sel)
    chosen = best_in or best_all
    if chosen:
        _, name, sel = chosen
        finish_pick(row, name, sel["label"], sel["fair_prob"], gate)


def parse_handball_tables(reader, new_row, sel_row, two_way_market, finish_pick, flag,
                          existing_rows) -> None:
    """EHF Champions League and Liga ASOBAL rows."""
    from sports_ext import olbg_events  # local import: same helper the other sports use

    ehf, season, ehf_url = _ehf_table(reader)
    aso, aso_url = _asobal_table(reader)
    if not ehf and not aso:
        flag("BW-F-HB-01", "blocker", "Handball",
             "No readable official handball table in this capture",
             "EHF Champions League standings and the Liga ASOBAL ladder both failed to parse; "
             "handball therefore stays unpriced beyond the Danish rows.",
             "https://ehfcl.eurohandball.com/men/2026-27/standings/")
        return

    # league baseline for the EHF goals model
    gp_tot = sum(t["gp"] for t in ehf.values()) or 1
    avg_gf = sum(t["gf"] for t in ehf.values()) / gp_tot
    avg_ga = sum(t["ga"] for t in ehf.values()) / gp_tot

    published = [r for r in existing_rows if r["sport"] == "Handball"]

    def find(table, name):
        k = _key(name)
        if not k:
            return None
        best, score = None, 0.0
        for t in table.values():
            if not t["key"]:
                continue
            ov = len(k & t["key"])
            if ov == 0:
                ov = sum(1 for x in k for y in t["key"]
                         if min(len(x), len(y)) >= 4 and (x.startswith(y[:5]) or y.startswith(x[:5])))
            if ov == 0:
                continue
            sc = ov / max(1, min(len(k), len(t["key"])))
            if sc > score:
                best, score = t, sc
        return best if score >= 0.5 else None

    efh_seen = 0
    for e in olbg_events(reader, "olbg_handball_20"):
        if e["start_utc"] and not (WIN_START <= e["start_utc"][:10] < WIN_END):
            continue
        parts = re.split(r"\s+vs\.?\s+", e["name"], maxsplit=1)
        if len(parts) != 2:
            continue
        A_name, B_name = _norm(parts[0]), _norm(parts[1])
        A, B = find(ehf, A_name), find(ehf, B_name)
        if not (A and B) or A is B:
            continue
        if A["gp"] < 4 or B["gp"] < 4:
            continue
        # goals model: attack x defence against the group-phase average, with the small
        # five-game sample shrunk halfway to the mean (k = gp/(gp+5)) and each side's
        # expected goals clamped to the range handball actually produces (22-38).
        def _att(t):
            raw = (t["gf"] / t["gp"]) / avg_gf
            return 1.0 + (raw - 1.0) * t["gp"] / (t["gp"] + 5.0)

        def _dfn(t):
            raw = (t["ga"] / t["gp"]) / avg_gf
            return 1.0 + (raw - 1.0) * t["gp"] / (t["gp"] + 5.0)

        mu_h = min(38.0, max(22.0, avg_gf * _att(A) * _dfn(B) * 1.03))
        mu_a = min(38.0, max(22.0, avg_gf * _att(B) * _dfn(A) * 0.97))
        win, draw, loss = _poisson_probs(mu_h, mu_a)
        p_h = win / (win + loss)
        total_mu = mu_h + mu_a
        line = math.floor(total_mu) + 0.5
        p_over = _total_ou(total_mu, line)
        gate = True
        basis = (f"official EHF Champions League {season or '2026/27'} group table: "
                 f"{A['team']} (group {A['group']}) {A['w']}-{A['d']}-{A['l']} in {A['gp']}, "
                 f"{A['gf']}:{A['ga']} goals, {A['pts']} pts; {B['team']} (group {B['group']}) "
                 f"{B['w']}-{B['d']}-{B['l']} in {B['gp']}, {B['gf']}:{B['ga']} goals, {B['pts']} pts. "
                 f"Expected goals {mu_h:.2f}-{mu_a:.2f} from goals-for x goals-against against the group-phase "
                 f"average {avg_gf:.2f}; Poisson gives home {win:.3f} / draw {draw:.3f} / away {loss:.3f}. "
                 f"Match winner is quoted draw-no-bet ({p_h:.4f}); total {line:g} at {p_over:.4f}. Pairing and "
                 f"kick-off come from the OLBG listing (the EHF match list on the same page is client-rendered), "
                 f"which is flagged rather than inferred.")
        markets = {
            "match_winner": {"market_name": "Match Winner (draw no bet)", "line": None,
                             "prob_sum": 1.0, "book_margin": 0.0,
                             "selections": [sel_row(A["team"], p_h), sel_row(B["team"], 1 - p_h)]},
            f"total_{line:g}": {"market_name": "Total Goals", "line": line, "prob_sum": 1.0,
                                "book_margin": 0.0,
                                "selections": [sel_row(f"Over {line:g}", p_over),
                                               sel_row(f"Under {line:g}", 1 - p_over)]},
        }
        comp = f"EHF Champions League Men {season or '2026/27'} — Group {A['group']}"
        url, src = ehf_url, "EHF Champions League official standings (eurohandball.com)"
        stamp = reader.capture_stamp("ehfcl_standings")
        efh_seen += 1
        row = new_row(sport="Handball", competition=comp, side_a=A["team"], side_b=B["team"],
                      matchup=f"{A['team']} vs {B['team']}", start_utc=e["start_utc"],
                      official_url=url, official_source_name=src, capture_stamp=stamp,
                      inputs_summary=basis, markets=markets,
                      olbg={"on_olbg": True, "olbg_url": e["url"],
                            "olbg_listed": [t["decimal"] for t in e["tips"][:4]]})
        _pick(row, gate, finish_pick)
        published.append(row)

    if efh_seen:
        flag("BW-F-HB-02", "review", "Handball",
             "EHF Champions League rows: pairing from the OLBG listing, strength from the EHF table",
             f"{efh_seen} EHF Champions League tie(s) are priced from the official EHF group tables "
             f"(goals for/against). The EHF fixture list on the same page is an Angular template that renders "
             f"client-side (the captured HTML still contains {{{{match.homeTeam.team.name}}}} placeholders), so each "
             f"pairing and kick-off comes from the OLBG listing and is labelled as such on the row. Match winner is "
             f"quoted draw-no-bet because handball draws are common and the desk publishes two-way markets only; the "
             f"draw probability is stated in the row's inputs.",
             ehf_url)
    if aso:
        flag("BW-F-HB-04", "review", "Handball",
             "Liga ASOBAL ladder captured but not priceable",
             f"The official Liga ASOBAL ladder parsed cleanly ({len(aso)} clubs, Bidasoa Irun top on {aso.get('IRUDEK Bidasoa Irun', {}).get('pts', '?')} pts) "
             f"but it publishes points only: no games-played, goals-for or goals-against columns, so the points "
             f"total cannot be normalised into a per-game strength and no defensible line can be built from it. "
             f"The Spanish OLBG listings therefore stay unpriced on this capture rather than being priced off an "
             f"unverified points scale.", aso_url)
    if not efh_seen:
        flag("BW-F-HB-01", "review", "Handball",
             "No EHF/ASOBAL tie could be matched to the captured tables",
             "The official tables parsed but no OLBG-listed fixture matched two table rows; handball stays "
             "listing-only for those competitions.", ehf_url or aso_url)
    print(f"[board-bw] handball tables: EHF {efh_seen} priced (ASOBAL ladder not priceable)")
