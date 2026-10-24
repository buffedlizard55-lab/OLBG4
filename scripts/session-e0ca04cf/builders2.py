#!/usr/bin/env python3
"""Board EC: builders for the sports that need their own feed shape.

Everything here takes the desk module ``D`` as its first argument instead of
importing it, so ``desk.py`` stays the single place that defines the row schema,
the price window and the pick rules.

Each builder follows the same contract as the ones in ``desk.py``:

* home side in ``side_b``, away side in ``side_a`` (the official feeds list the
  visiting side first);
* ``row["inputs"]`` holds only scalars copied from, or derived from, the official
  payload named in ``row["source_url"]``;
* a row without a usable strength input is appended *unpriced* with a flag that
  says exactly which number was missing.
"""
from __future__ import annotations

import html as _html
import math
import re
from datetime import datetime, timedelta, timezone

# --------------------------------------------------------------------- helpers


def _iso(date_s: str, time_s: str, year: int) -> str:
    """'24/10' + '21h05' -> '2026-10-24T21:05:00Z' (CEST->UTC handled coarsely)."""
    try:
        d, m = [int(x) for x in date_s.split("/")]
        hh, mm = time_s.replace("h", ":").split(":")
        y = year if m >= 7 else year + 1
        dt = datetime(y, m, d, int(hh), int(mm), tzinfo=timezone(timedelta(hours=2)))
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:  # noqa: BLE001
        return ""


def _line(mu: float, step: float) -> float:
    """A market line: the half-step above the step floor of the expectation."""
    return math.floor(mu / step) * step + step / 2.0


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


# ------------------------------------------------------------------ ice hockey
def build_liiga(D, cap, rows):
    """Finnish Liiga: teams and fixtures from the official Liiga stats API."""
    tid = "liiga_schedule_json" if cap.exists("liiga_schedule_json") else (
        "liiga_games" if cap.exists("liiga_games") else None)
    if not tid:
        return
    try:
        games = cap.json(tid)
    except Exception:  # noqa: BLE001
        return
    if isinstance(games, dict):
        games = games.get("games") or games.get("data") or []
    if not isinstance(games, list):
        return

    table, fixtures = {}, []
    for g in games:
        h, a = (g.get("homeTeam") or {}), (g.get("awayTeam") or {})
        hn, an = h.get("teamName"), a.get("teamName")
        if not hn or not an:
            continue
        start = (g.get("start") or "")[:19]
        ended = bool(g.get("ended")) or (g.get("finishedType") or "").startswith(("ENDED", "OVERTIME", "WINNING"))
        hg, ag = h.get("goals"), a.get("goals")
        if ended and isinstance(hg, int) and isinstance(ag, int):
            for nm, gf, ga in ((hn, hg, ag), (an, ag, hg)):
                s = table.setdefault(nm, {"gp": 0, "gf": 0, "ga": 0, "w": 0, "l": 0})
                s["gp"] += 1
                s["gf"] += gf
                s["ga"] += ga
                s["w" if gf > ga else "l"] += 1
        elif not ended and start:
            fixtures.append({"start": start, "home": hn, "away": an,
                             "venue": ((g.get("iceRink") or {}).get("name") or "")})
    if not table:
        return
    total_gp = sum(t["gp"] for t in table.values()) or 1
    league = sum(t["gf"] for t in table.values()) / total_gp
    ad = {}
    for nm, t in table.items():
        if not t["gp"]:
            continue
        ad[nm] = {"for_pg": round(t["gf"] / t["gp"], 2), "against_pg": round(t["ga"] / t["gp"], 2),
                  "gp": t["gp"], "att": (t["gf"] / t["gp"]) / league if league else 1.0,
                  "def": (t["ga"] / t["gp"]) / league if league else 1.0}
    for f in fixtures:
        start_utc = D.utc(f["start"]) if not f["start"].endswith("Z") else f["start"] + "Z"
        if not D.in_window(start_utc):
            continue
        a, b = ad.get(f["away"]), ad.get(f["home"])
        row = D.blank_row(id="fx_liiga_" + re.sub(r"\W+", "_", f["start"] + "_" + f["home"] + "_" + f["away"]),
                          sport="Ice Hockey", sport_slug="ice-hockey",
                          competition="Liiga 2026-27 (Finland)", start_utc=start_utc,
                          date=start_utc[:10], venue=f.get("venue", ""),
                          side_a=f["away"], side_b=f["home"],
                          source_url=cap.url(tid),
                          source_name="Liiga official games feed (liiga.fi)",
                          source_id=tid)
        if not a or not b or a["gp"] < 3 or b["gp"] < 3:
            row["flags"].append("fewer than three completed Liiga games for one club - no line originated")
            rows.append(row)
            continue
        lam_h = league * b["att"] * a["def"] * 1.06
        lam_a = league * a["att"] * b["def"]
        row["inputs"] = {"method": "Poisson on Liiga goals for/against per game, home factor 1.06",
                         "home_gf_pg": b["for_pg"], "home_ga_pg": b["against_pg"],
                         "away_gf_pg": a["for_pg"], "away_ga_pg": a["against_pg"],
                         "home_gp": b["gp"], "away_gp": a["gp"], "sample_games": min(a["gp"], b["gp"])}
        puck = -1.5 if lam_h > lam_a else 1.5
        D.goal_markets(row, lam_h, lam_a, False, 5.5 if lam_h + lam_a < 6.3 else 6.5, puck,
                       "Puck line/goals")
        D.choose_pick(row)
        rows.append(row)


# --------------------------------------------------------------------- snooker
def _wst_elo(matches):
    """Elo per player from completed WST matches, in date order."""
    rating, stats = {}, {}
    for dt, wid, lid, wf, lf in matches:
        rw, rl = rating.get(wid, 1500.0), rating.get(lid, 1500.0)
        exp_w = 1.0 / (1.0 + 10 ** (-(rw - rl) / 400.0))
        k = 24.0
        rating[wid] = rw + k * (1.0 - exp_w)
        rating[lid] = rl - k * (1.0 - exp_w)
        for pid, won, ff, fa in ((wid, 1, wf, lf), (lid, 0, lf, wf)):
            s = stats.setdefault(pid, {"w": 0, "l": 0, "ff": 0, "fa": 0})
            s["w" if won else "l"] += 1
            s["ff"] += ff
            s["fa"] += fa
    return rating, stats


def _best_of_series(p, frames):
    """Distribution of the final frame score in a best-of-N match.

    ``p`` is the per-frame probability for side A.  Returns {(A frames, B frames):
    probability} over the possible final scores, which is all the winner market,
    a frames handicap and a total-frames market need.
    """
    need = frames // 2 + 1
    scores = {}
    for b in range(0, need):
        scores[(need, b)] = math.comb(need - 1 + b, b) * p ** need * (1 - p) ** b
    for a in range(0, need):
        scores[(a, need)] = math.comb(need - 1 + a, a) * (1 - p) ** need * p ** a
    tot = sum(scores.values()) or 1.0
    return {k: v / tot for k, v in scores.items()}


def build_snooker(D, cap, rows):
    """World Snooker Tour: fixtures and results from the official match API."""
    if not cap.exists("wst_matches_api"):
        return
    try:
        data = cap.json("wst_matches_api").get("data", [])
    except Exception:  # noqa: BLE001
        return

    played, by_id, by_name = [], {}, {}
    for m in data:
        a = m.get("attributes") or {}
        hp, ap = a.get("homePlayer") or {}, a.get("awayPlayer") or {}
        pid_h, pid_a = a.get("homePlayerID") or hp.get("playerID"), a.get("awayPlayerID") or ap.get("playerID")
        if not pid_h or not pid_a:
            continue
        name_h = _clean(f"{hp.get('firstName','')} {hp.get('surname','')}") or pid_h
        name_a = _clean(f"{ap.get('firstName','')} {ap.get('surname','')}") or pid_a
        by_id[pid_h], by_id[pid_a] = name_h, name_a
        by_name[name_h.lower()], by_name[name_a.lower()] = pid_h, pid_a
        hs, as_ = a.get("homePlayerScore") or 0, a.get("awayPlayerScore") or 0
        if (a.get("status") or "") != "Completed" or hs == as_ or (not hs and not as_):
            continue
        if hs > as_:
            played.append((a.get("startDateTime") or "", pid_h, pid_a, hs, as_))
        else:
            played.append((a.get("startDateTime") or "", pid_a, pid_h, as_, hs))
    if not played:
        return
    played.sort(key=lambda x: x[0])
    rating, stats = _wst_elo(played)

    fixtures, _ranks = D.P.read_wst(cap)
    for f in fixtures:
        if not D.in_window(f["start_utc"]):
            continue
        if re.search(r"wildcard|winner of|tbd|match \d+|qualifier", f["side_a"] + " " + f["side_b"], re.I):
            continue  # placeholders are not players yet
        extra = f.get("extra") or {}
        na = _clean(f["side_a"]).lower()
        nb = _clean(f["side_b"]).lower()
        pa, pb = by_name.get(na), by_name.get(nb)
        row = D.blank_row(id=f["id"], sport="Snooker", sport_slug="snooker",
                          competition=f.get("competition") or "World Snooker Tour",
                          start_utc=f["start_utc"], date=f["start_utc"][:10],
                          side_a=f["side_a"], side_b=f["side_b"],
                          source_url=f["source_url"], source_name=f["source_name"],
                          source_id=f["source_id"])
        row["inputs"] = {"round": extra.get("round", ""), "best_of": extra.get("best_of"),
                         "method": "Elo from completed WST frames, converted to a best-of-N series"}
        if not pa or not pb:
            row["flags"].append("player is missing from the completed-match record - no line originated")
            rows.append(row)
            continue
        frames = int(extra.get("best_of") or 0)
        if frames < 3:
            row["flags"].append("match length (numberOfFrames) missing from the API row - no line originated")
            rows.append(row)
            continue
        ra, rb = rating.get(pa, 1500.0), rating.get(pb, 1500.0)
        sa0, sb0 = stats.get(pa, {}), stats.get(pb, {})
        fa = (sa0.get("ff", 0) + 7.5) / (sa0.get("ff", 0) + sa0.get("fa", 0) + 15.0)
        fb = (sb0.get("ff", 0) + 7.5) / (sb0.get("ff", 0) + sb0.get("fa", 0) + 15.0)
        p_frame = (fa * (1 - fb)) / (fa * (1 - fb) + fb * (1 - fa))
        p_frame = min(0.80, max(0.20, p_frame))
        series = _best_of_series(p_frame, frames)
        p_a = sum(v for (x, _y), v in series.items() if x == frames // 2 + 1)
        p_a = min(1.0, p_a)
        sa, sb = stats.get(pa, {}), stats.get(pb, {})
        row["inputs"].update({
            "elo_a": round(ra), "elo_b": round(rb), "p_frame": round(p_frame, 4),
            "frame_rate_a": round(fa, 4), "frame_rate_b": round(fb, 4),
            "matches_a": sa.get("w", 0) + sa.get("l", 0), "matches_b": sb.get("w", 0) + sb.get("l", 0),
            "frames_won_a": sa.get("w", 0), "frames_lost_a": sa.get("l", 0),
            "frames_won_b": sb.get("w", 0), "frames_lost_b": sb.get("l", 0),
            "sample_games": min(sa.get("w", 0) + sa.get("l", 0), sb.get("w", 0) + sb.get("l", 0)),
        })
        # frames markets: handicap of 1.5 frames and a total around the bo-N middle
        line_frames = frames - 1.5
        p_over = sum(v for (x, y), v in series.items() if x + y > line_frames)
        # home side is side_b, so it is favourite (and lays -1.5) when p_a < 0.5
        margin = -1.5 if p_a < 0.5 else 1.5
        p_covers = sum(v for (x, y), v in series.items()
                       if (y - x) > 1.5) if margin < 0 else sum(v for (x, y), v in series.items()
                                                                if (x - y) > 1.5)
        row["markets"] = {
            "match_winner": D.market("Match Winner", None,
                                     [(row["side_a"], p_a), (row["side_b"], 1 - p_a)], "2-way"),
            "handicap": D.market("Frames Handicap", margin,
                                 [(f"{row['side_b']} {margin:+.1f}", p_covers),
                                  (f"{row['side_a']} {-margin:+.1f}", 1 - p_covers)], "frames"),
            "total": D.market("Total Frames", line_frames,
                              [(f"Over {line_frames}", p_over), (f"Under {line_frames}", 1 - p_over)],
                              "frames"),
        }
        D.choose_pick(row)
        rows.append(row)


# ------------------------------------------------------------------ rugby union
_RX_LNR = re.compile(r'\{"id":(\d+),"week_id":(\d+),"hosting_club":\{[^{}]*?"name":"([^"]+)"')


def _lnr_matches(html: str, year: int):
    """Top 14 calendar rows out of the LNR page's embedded JSON."""
    u = html.replace("\\/", "/").replace('\\"', '"')
    out = []
    for m in _RX_LNR.finditer(u):
        seg = u[m.start():m.start() + 6000]
        vn = re.search(r'"visiting_club":\{"id":\d+,"name":"([^"]+)"', seg)
        dt = re.search(r'"date":"(\d{2}/\d{2})"', seg)
        tm = re.search(r'"time":"(\d{1,2}h\d{2})"', seg)
        st = re.search(r'"status":"(\w+)"', seg)
        sc = re.search(r'"score":\[(\d+),(\d+)\]', seg)
        if not (vn and dt and st):
            continue
        out.append({"home": _clean(m.group(3)), "away": _clean(vn.group(1)),
                    "start_utc": _iso(dt.group(1), tm.group(1) if tm else "00h00", year),
                    "status": st.group(1),
                    "score": (int(sc.group(1)), int(sc.group(2))) if sc else None,
                    "week": m.group(2)})
    return out


def build_rugby_union(D, cap, rows):
    """Top 14: fixtures and results from the official LNR calendar + table."""
    pages = [t for t in ("top14_cal", "top14_j1", "top14_j2", "top14_j3", "top14_j4",
                         "top14_j5", "top14_j6", "top14_j7", "top14_j8", "top14_j9",
                         "top14_j10") if cap.exists(t)]
    if not pages:
        return
    year = 2026
    seen, matches = set(), []
    for tid in pages:
        html = cap.text(tid)
        for m in _lnr_matches(html, year):
            key = (m["home"], m["away"], m["start_utc"])
            if key in seen:
                continue
            seen.add(key)
            m["source_id"] = tid
            matches.append(m)
    if not matches:
        return

    table = {}
    for m in matches:
        if m["status"] != "finished" or not m["score"]:
            continue
        (hs, as_) = m["score"]
        for nm, pf, pa in ((m["home"], hs, as_), (m["away"], as_, hs)):
            t = table.setdefault(nm, {"gp": 0, "pf": 0, "pa": 0, "w": 0, "l": 0, "d": 0})
            t["gp"] += 1
            t["pf"] += pf
            t["pa"] += pa
            if pf > pa:
                t["w"] += 1
            elif pf < pa:
                t["l"] += 1
            else:
                t["d"] += 1
    if not table:
        return
    gp = sum(t["gp"] for t in table.values()) or 1
    lg_pf = sum(t["pf"] for t in table.values()) / gp
    lg_pa = sum(t["pa"] for t in table.values()) / gp
    ad = {}
    for nm, t in table.items():
        if t["gp"] < 2:
            continue
        ad[nm] = {"for_pg": round(t["pf"] / t["gp"], 1), "against_pg": round(t["pa"] / t["gp"], 1),
                  "gp": t["gp"], "att": (t["pf"] / t["gp"]) / lg_pf if lg_pf else 1.0,
                  "def": (t["pa"] / t["gp"]) / lg_pa if lg_pa else 1.0}

    for m in matches:
        if m["status"] == "finished" or not D.in_window(m["start_utc"]):
            continue
        a, b = ad.get(m["away"]), ad.get(m["home"])
        row = D.blank_row(id="fx_t14_" + re.sub(r"\W+", "_", m["home"] + "_" + m["away"] + "_" + m["start_utc"][:10]),
                          sport="Rugby Union", sport_slug="rugby-union",
                          competition="Top 14 2026-27 (France)", start_utc=m["start_utc"],
                          date=m["start_utc"][:10], side_a=m["away"], side_b=m["home"],
                          source_url=cap.url(m["source_id"]),
                          source_name="Top 14 official calendar (top14.lnr.fr)",
                          source_id=m["source_id"])
        row["inputs"] = {"method": "Normal margin on Top 14 points for/against per match, home +3.5",
                         "rounds_captured": len(pages)}
        if not a or not b:
            row["flags"].append("fewer than two completed Top 14 matches for one club in the capture - no line originated")
            rows.append(row)
            continue
        pf_h = lg_pf * b["att"] * a["def"]
        pf_a = lg_pf * a["att"] * b["def"]
        margin = pf_h - pf_a + 3.5
        sd = 13.5
        total = pf_h + pf_a
        line = D.spread_near(margin, 3.0)
        row["inputs"].update({"home_pts_pg": b["for_pg"], "home_conceded_pg": b["against_pg"],
                              "away_pts_pg": a["for_pg"], "away_conceded_pg": a["against_pg"],
                              "home_gp": b["gp"], "away_gp": a["gp"],
                              "sample_games": min(a["gp"], b["gp"])})
        D.margin_markets(row, margin, sd, line, total, 14.0, _line(total, 3.0), "Points")
        D.choose_pick(row)
        rows.append(row)


# ------------------------------------------------------------------ handball
_RX_EHF = re.compile(
    r"(\d+)\.\s+([A-Za-zÀ-ž0-9'’.\- ]+?)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*:\s*(\d+)\s+(-?\d+)\s+(\d+)")


def _handball_markets(D, row, lam_h, lam_a):
    """3-way handball prices from a normal margin (a Poisson grid truncates at 22 goals)."""
    mu, sd, sd_t = lam_h - lam_a, 9.5, 8.5
    p_home = 1.0 - D.M.norm_cdf((0.5 - mu) / sd)
    p_away = D.M.norm_cdf((-0.5 - mu) / sd)
    p_draw = max(0.0, 1.0 - p_home - p_away)
    total = lam_h + lam_a
    line_t = _line(total, 1.0)
    line_h = D.spread_near(mu, 1.0)
    p_over = 1.0 - D.M.norm_cdf((line_t - total) / sd_t)
    p_covers = 1.0 - D.M.norm_cdf((abs(line_h) - mu) / sd) if line_h < 0 else \
        D.M.norm_cdf((abs(line_h) + mu) / sd)
    D.emit_markets(row, p_home=p_home, p_away=p_away, p_draw=p_draw, spread=line_h,
                   p_home_covers=p_covers, total_line=line_t, p_over=p_over, label="Goals")
    row["inputs"].update({"exp_home": round(lam_h, 2), "exp_away": round(lam_a, 2),
                          "exp_total": round(total, 2), "sd_margin": sd, "total_line": line_t,
                          "handicap_line": line_h})


def build_handball_ehf(D, cap, rows, olbg_events):
    """EHF Champions League group tables, matched to the handball card rows."""
    if not cap.exists("ehfcl_m_standings"):
        return
    html = cap.text("ehfcl_m_standings")
    txt = _html.unescape(re.sub(r"<[^>]+>", " ", html))
    txt = re.sub(r"\s+", " ", txt)
    table = {}
    for m in _RX_EHF.finditer(txt):
        name = _clean(m.group(2))
        if len(name) < 3:
            continue
        gp, _w, _d, _l, gf, ga = (int(m.group(i)) for i in (3, 4, 5, 6, 7, 8))
        if gp < 1:
            continue
        table[name] = {"gp": gp, "gf": gf, "ga": ga}
    if not table:
        return
    gp_all = sum(t["gp"] for t in table.values()) or 1
    lg = sum(t["gf"] for t in table.values()) / gp_all
    ad = {}
    for nm, t in table.items():
        ad[nm] = {"for_pg": round(t["gf"] / t["gp"], 1), "against_pg": round(t["ga"] / t["gp"], 1),
                  "gp": t["gp"], "att": (t["gf"] / t["gp"]) / lg, "def": (t["ga"] / t["gp"]) / lg}

    for ev in olbg_events:
        if ev["sport"] != "Handball" or not D.in_window(ev["start_utc"]):
            continue
        parts = re.split(r"\s+vs\s+", ev["event"])
        if len(parts) != 2:
            continue
        kh = D.match_name(parts[0], ad)
        ka = D.match_name(parts[1], ad)
        if not kh or not ka:
            continue  # the Danish/Swedish/Spanish cards cannot be priced off the EHF table
        b, a = ad[kh], ad[ka]
        row = D.blank_row(id="fx_ehf_" + ev["event_id"], sport="Handball", sport_slug="handball",
                          competition="EHF Champions League Men 2026-27",
                          start_utc=ev["start_utc"], date=ev["start_utc"][:10],
                          side_a=parts[1].strip(), side_b=parts[0].strip(),
                          source_url=cap.url("ehfcl_m_standings"),
                          source_name="EHF Champions League official standings (eurohandball.com)",
                          source_id="ehfcl_m_standings")
        row["olbg"] = {"event": ev["event"], "event_url": ev["event_url"], "hub_url": ev["hub_url"],
                       "event_id": ev["event_id"], "tips": ev["tips"]}
        row["flags"].append("fixture date/time taken from the OLBG listing; strength inputs from the EHF group table")
        lam_h = lg * b["att"] * a["def"] * 1.06
        lam_a = lg * a["att"] * b["def"]
        row["inputs"] = {"method": "Poisson on EHF Champions League goals for/against per game, home factor 1.06",
                         "home_gf_pg": b["for_pg"], "home_ga_pg": b["against_pg"],
                         "away_gf_pg": a["for_pg"], "away_ga_pg": a["against_pg"],
                         "home_gp": b["gp"], "away_gp": a["gp"], "sample_games": min(a["gp"], b["gp"])}
        _handball_markets(D, row, lam_h, lam_a)
        D.choose_pick(row)
        rows.append(row)
