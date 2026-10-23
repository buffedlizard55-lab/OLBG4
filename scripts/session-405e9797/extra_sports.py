#!/usr/bin/env python3
"""Board AR — extra sport parsers that read the official JSON services captured today.

Installed into originate.py at run time (see `install`) so the shared maths helpers are
used unchanged. Every parser follows the desk rule: a row is priced only when the numbers
behind it come from an official page captured in this run; anything the official page does
not publish is left blank and flagged.
"""
from __future__ import annotations

import json
import math
import re


def install(ns):
    flag, market, outright = ns["flag"], ns["market"], ns["outright"]
    add_row, choose_pick, norm = ns["add_row"], ns["choose_pick"], ns["norm"]
    ncdf, hcp_ladder, total_ladder = ns["ncdf"], ns["hcp_ladder"], ns["total_ladder"]
    fair, pois, SPORTS = ns["fair"], ns["pois"], ns["SPORTS"]
    in_window, confidence = ns["in_window"], ns["confidence"]

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _json_all(reader, prefix):
        out = []
        for tid in sorted(reader.map):
            if tid.startswith(prefix):
                try:
                    out.append((tid, reader.json(tid)))
                except Exception:
                    continue
        return out

    def _wst_players(reader):
        ppl = {}
        for _, payload in _json_all(reader, "wst_participants"):
            for row in payload.get("data", []):
                a = row.get("attributes") or {}
                name = f"{a.get('firstName','')} {a.get('surname','')}".strip()
                if a.get("id") or row.get("id"):
                    ppl[row.get("id") or a.get("id")] = name
        return ppl

    def _wst_ranks(reader, players):
        for _, payload in _json_all(reader, "wst_rankings"):
            if not isinstance(payload, dict):
                continue
            for rk in payload.get("data", []):
                if not isinstance(rk, dict):
                    continue
                a = rk.get("attributes") or {}
                if not a.get("positions"):
                    continue
                table = {}
                for p in a["positions"]:
                    nm = players.get(p.get("playerID"))
                    if nm:
                        table[norm(nm)] = {"pos": p.get("position"), "prize": p.get("prizeMoney") or 0,
                                           "name": nm}
                if table:
                    return table, rk.get("id")
        return {}, None

    def _wst_matches(reader):
        for tid, payload in _json_all(reader, "wst_matches"):
            if isinstance(payload, dict) and payload.get("data"):
                for m in payload["data"]:
                    yield tid, m

    # ------------------------------------------------------------------
    # Snooker — WST match feed + official world ranking (prize money)
    # ------------------------------------------------------------------
    def snooker(reader, rendered, inventory):
        players = _wst_players(reader)
        ranks, rank_id = _wst_ranks(reader, players)
        if not ranks:
            flag("AR-F-SNOOK-01", "blocker", "Snooker", "WST ranking table not parsed",
                 "The official WST ranking service was captured but no ranking positions could be joined to "
                 "player names, so no snooker line was originated today.",
                 "https://www.wst.tv/rankings/")
            return
        # find the Northern Ireland Open ties in the official match feed
        found = {}
        for tid, m in _wst_matches(reader):
            a = m.get("attributes") or {}
            tour = (a.get("tournament") or {}).get("name") or ""
            if "Northern Ireland" not in tour:
                continue
            start = (a.get("startDateTime") or "").replace(" ", "T") + "Z"
            if not start.startswith(("2026-10-23", "2026-10-24", "2026-10-25")):
                continue
            hp, ap = a.get("homePlayer") or {}, a.get("awayPlayer") or {}
            h = f"{hp.get('firstName','')} {hp.get('surname','')}".strip()
            aw = f"{ap.get('firstName','')} {ap.get('surname','')}".strip()
            if not h or not aw:
                continue
            found[norm(h) + "|" + norm(aw)] = {
                "a": h, "b": aw, "start": start, "round": a.get("round") or "",
                "frames": a.get("numberOfFrames") or 7, "url": reader.url(tid),
                "evidence": reader.ev(tid), "tour": tour,
                "venue": (a.get("tournament") or {}).get("venue") or "",
                "city": (a.get("tournament") or {}).get("city") or "",
            }
        if not found:
            flag("AR-F-SNOOK-02", "review", "Snooker",
                 "Northern Ireland Open ties not present in the captured match-feed page",
                 "The WST match service is paginated newest-first; the pages captured today did not reach the "
                 "23–25 October Northern Ireland Open ties, so those OLBG rows stay listing-only.",
                 "https://www.wst.tv/tournaments/northern-ireland-open-2026/matches")
            return
        url_r = reader.url(next(t for t in reader.map if t.startswith("wst_rankings")))
        used = set()
        for e in inventory["sports"].get("Snooker", {}).get("events", []):
            parts = re.split(r"\s+v(?:s)?\s+", e["event"], maxsplit=1)
            if len(parts) != 2:
                continue
            key = norm(parts[0]) + "|" + norm(parts[1])
            fx = found.get(key)
            if not fx:
                # tolerate surname-only listing names
                for k, v in found.items():
                    if norm(parts[0]) in k and norm(parts[1]) in k:
                        fx = v
                        key = k
                        break
            if not fx:
                continue
            ra = ranks.get(norm(fx["a"])) or ranks.get(norm(fx["a"].split()[-1]))
            rb = ranks.get(norm(fx["b"])) or ranks.get(norm(fx["b"].split()[-1]))
            if not ra or not rb:
                continue
            la, lb = math.log(1 + ra["prize"]), math.log(1 + rb["prize"])
            p_frame = 1 / (1 + math.exp(-0.55 * (la - lb)))
            n = int(fx["frames"] or 7)
            need = n // 2 + 1
            p_win = sum(math.comb(n, k) * p_frame ** k * (1 - p_frame) ** (n - k) for k in range(need, n + 1))
            mk = [market("Match Winner", None, fx["a"], p_win, fx["b"], 1 - p_win)]
            # frame handicap around the expected frame margin
            mu = n * (2 * p_frame - 1)
            for line in (1.5, 2.5):
                pa = 1 - ncdf(line, mu, 1.9)
                mk.append(market("Frame Handicap", -line, f"{fx['a']} -{line} frames",
                                 pa, f"{fx['b']} +{line} frames", 1 - pa))
            for tl in (n - 0.5, n + 0.5):
                pu = ncdf(tl, n * (1 - (1 - p_frame) ** 2) + 0.0, 1.6)
                mk.append(market("Total Frames", tl, f"Under {tl}", pu, f"Over {tl}", 1 - pu))
            row = add_row(
                sport="Snooker", competition=f"{fx['tour']} (WST)", round=fx["round"],
                side_a=fx["a"], side_b=fx["b"], start_utc=fx["start"],
                venue=fx["venue"] or fx["city"],
                official_url=fx["url"], official_source_name="WST official match feed (wstservices.co.uk)",
                evidence=fx["evidence"],
                inputs_summary=(f"Official WST world ranking: {fx['a']} #{ra['pos']} (£{ra['prize']:,}) vs "
                                f"{fx['b']} #{rb['pos']} (£{rb['prize']:,}); {fx['round']}, best of {n} frames, "
                                f"official start {fx['start']}."),
                markets=mk)
            choose_pick(row, True)
            used.add(key)
            # attach listing for reference
            mk0 = e["markets"][0]
            row["olbg"] = {"event": e["event"], "event_url": e.get("event_url", ""),
                           "market": mk0.get("market", ""), "selection": mk0.get("selection", ""),
                           "decimal": mk0.get("decimal", ""), "american": mk0.get("american", ""),
                           "implied_prob": round(1 / float(mk0["decimal"]), 4) if mk0.get("decimal") else None}
        flag("AR-F-SNOOK-03", "review", "Snooker",
             "Frame-level model calibrated on official prize-money ranking only",
             "The WST ranking list is the only official numeric input captured for these ties; no frame-level "
             "season statistics are published in the feed, so frame probabilities come from the log prize-money gap.",
             url_r)

    # ------------------------------------------------------------------
    # Darts — PDC participant service + ranking tables
    # ------------------------------------------------------------------
    def darts(reader, rendered, inventory):
        ranks = {}
        for tid, payload in _json_all(reader, "pdc_rankings"):
            if not isinstance(payload, dict):
                continue
            for rk in payload.get("data", []):
                if not isinstance(rk, dict):
                    continue
                a = rk.get("attributes") or {}
                for pos in a.get("positions") or []:
                    nm = f"{pos.get('firstName','')} {pos.get('lastName','')}".strip()
                    if nm:
                        ranks[norm(nm)] = {"prize": pos.get("prizeMoney") or 0, "pos": pos.get("position")}
        if not ranks:
            flag("AR-F-DARTS-01", "blocker", "Darts",
                 "PDC ranking positions not captured",
                 "pdc.tv renders client-side and the PDC match host did not resolve from the runner; the ranking "
                 "service returned only the ranking list metadata, so no darts line was originated.",
                 "https://www.pdc.tv/order-of-merit/pdc-order-of-merit")
            return
        hub = "https://www.pdc.tv/order-of-merit/pdc-order-of-merit"
        n = 0
        for e in inventory["sports"].get("Darts", {}).get("events", []):
            parts = re.split(r"\s+vs\s+", e["event"], maxsplit=1)
            if len(parts) != 2:
                continue
            pa = next((v for k, v in ranks.items() if norm(parts[0]) and norm(parts[0]) in k), None)
            pb = next((v for k, v in ranks.items() if norm(parts[1]) and norm(parts[1]) in k), None)
            if not (pa and pb):
                continue
            la, lb = math.log(1 + pa["prize"]), math.log(1 + pb["prize"])
            p_leg = 1 / (1 + math.exp(-0.5 * (la - lb)))
            # European Championship first round is best of 11 legs
            need, total = 6, 11
            p_win = sum(math.comb(total, k) * p_leg ** k * (1 - p_leg) ** (total - k) for k in range(need, total + 1))
            mu = total * (2 * p_leg - 1)
            mk = [market("Match Winner", None, parts[0], p_win, parts[1], 1 - p_win)]
            for line in (1.5, 2.5):
                pa_ = 1 - ncdf(line, mu, 2.6)
                mk.append(market("Leg Handicap", -line, f"{parts[0]} -{line} legs", pa_,
                                 f"{parts[1]} +{line} legs", 1 - pa_))
            for tl in (8.5, 9.5):
                pu = ncdf(tl, 10.2, 2.2)
                mk.append(market("Total Legs", tl, f"Under {tl}", pu, f"Over {tl}", 1 - pu))
            row = add_row(sport="Darts", competition="Machineseeker European Championship 2026 (Dortmund)",
                          round="First round", side_a=parts[0], side_b=parts[1],
                          start_utc=e.get("start_utc", ""), venue="Westfalenhalle",
                          official_url=hub, official_source_name="PDC ranking service (pdcservices.co.uk)",
                          evidence="",
                          inputs_summary=(f"Official PDC ranking: {parts[0]} #{pa['pos']} (£{pa['prize']:,}) vs "
                                          f"{parts[1]} #{pb['pos']} (£{pb['prize']:,}); best of 11 legs. The tie and "
                                          f"throw-on time come from the OLBG listing because the PDC match host did "
                                          f"not resolve in this capture."),
                          markets=mk)
            choose_pick(row, True)
            mk0 = e["markets"][0]
            row["olbg"] = {"event": e["event"], "event_url": e.get("event_url", ""),
                           "market": mk0.get("market", ""), "selection": mk0.get("selection", ""),
                           "decimal": mk0.get("decimal", ""), "american": mk0.get("american", ""),
                           "implied_prob": round(1 / float(mk0["decimal"]), 4) if mk0.get("decimal") else None}
            n += 1
        if n:
            flag("AR-F-DARTS-02", "review", "Darts",
                 "Darts tie list and throw-on times are listing-sourced",
                 "PDC's match service host did not resolve from the runner, so the pairings and times shown are the "
                 "OLBG listing values; the ranking numbers used for the prices are from the PDC ranking service.",
                 hub)

    # ------------------------------------------------------------------
    # Motor racing — Formula 1 drivers' championship table (server-rendered)
    # ------------------------------------------------------------------
    def motor(reader, rendered, inventory):
        if not reader.has("f1_standings_drivers"):
            return
        html = reader.text("f1_standings_drivers")
        txt = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
        txt = re.sub(r"(?s)<[^>]+>", "\n", txt)
        import html as htmlmod
        lines = [l.strip() for l in htmlmod.unescape(txt).splitlines() if l.strip()]
        # table rows read: first name, last name, code, nationality, team, points
        drivers = []
        for i in range(len(lines) - 5):
            if re.fullmatch(r"[A-Z]{3}", lines[i + 2]) and re.fullmatch(r"[A-Z]{3}", lines[i + 3]) \
                    and lines[i + 4].replace(" ", "").isalpha() and re.fullmatch(r"\d+", lines[i + 5] or ""):
                drivers.append({"name": f"{lines[i]} {lines[i + 1]}", "team": lines[i + 4],
                                "points": int(lines[i + 5])})
        if len(drivers) < 15:
            flag("AR-F-MOT-01", "review", "Motor Racing", "F1 standings table not parsed",
                 "formula1.com returned the drivers' standings but the row pattern was not recognised, so the "
                 "USA Grand Prix outright is published unpriced.",
                 "https://www.formula1.com/en/results/2026/drivers")
            return
        for e in inventory["sports"].get("Motor Racing", {}).get("events", []):
            if "Grand Prix" not in e["event"]:
                continue
            tot = sum(d["points"] for d in drivers) or 1
            probs = [(d["name"], (d["points"] + 6) / (tot + 6 * len(drivers))) for d in drivers]
            mk = [outright("Race Winner", probs)]
            row = add_row(sport="Motor Racing", competition="FIA Formula One World Championship 2026",
                          round="United States Grand Prix", side_a=e["event"], side_b="",
                          matchup=e["event"], start_utc=e.get("start_utc", ""), venue="Circuit of the Americas",
                          official_url=reader.url("f1_standings_drivers"),
                          official_source_name="Formula 1 official drivers' standings (formula1.com)",
                          evidence=reader.ev("f1_standings_drivers"),
                          inputs_summary=(f"Official F1 drivers' standings after the season's completed rounds: "
                                          f"{drivers[0]['name']} leads on {drivers[0]['points']} points, "
                                          f"{drivers[1]['name']} has {drivers[1]['points']}. The outright is a softmax "
                                          f"over championship points; no grid or qualifying data is published yet."),
                          markets=mk)
            top = mk[0]["selections"][0]
            conf = confidence(top["prob"], False)[0]
            row["winner"] = {"market": "Race Winner", "selection": top["label"], "prob": top["prob"],
                             "decimal": top["decimal"], "american": top["american"], "confidence": conf}
            row["pick"] = {"market": "Race Winner", "line": None, "selection": top["label"],
                           "prob": top["prob"], "decimal": top["decimal"], "american": top["american"],
                           "confidence": conf, "in_window": in_window(top["american"])}
            mk0 = e["markets"][0]
            row["olbg"] = {"event": e["event"], "event_url": e.get("event_url", ""),
                           "market": mk0.get("market", ""), "selection": mk0.get("selection", ""),
                           "decimal": mk0.get("decimal", ""), "american": mk0.get("american", ""),
                           "implied_prob": round(1 / float(mk0["decimal"]), 4) if mk0.get("decimal") else None}
            flag("AR-F-MOT-02", "review", "Motor Racing",
                 "Race outright priced from championship points only",
                 "The F1 standings table is the only official numeric input captured for the USA Grand Prix; no "
                 "grid, qualifying or practice classification was available, so confidence is capped at Medium.",
                 reader.url("f1_standings_drivers"))

    # ------------------------------------------------------------------
    # Volleyball — Italian SuperLega official table
    # ------------------------------------------------------------------
    def volleyball(reader, rendered, inventory):
        if not reader.has("legavolley_classifica"):
            return
        raw = reader.text("legavolley_classifica")
        txt = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
        txt = re.sub(r"(?s)<[^>]+>", "\n", txt)
        import html as htmlmod
        lines = [l.strip() for l in htmlmod.unescape(txt).splitlines() if l.strip()]
        teams = ["Acqua Sant’Anna Cuneo", "Allianz Milano", "Cisterna Volley", "Cucine Lube Civitanova",
                 "Gas Sales Bluenergy Piacenza", "Itas Trentino", "Pallavolo Padova", "Rana Verona",
                 "Sir Susa Scai Perugia", "Tinet Prata di Pordenone", "Valsa Group Modena", "Vero Volley Monza"]
        table = {}
        start = next((n for n, l in enumerate(lines) if "Classifica aggiornata al" in l), 0)
        for tm in teams:
            try:
                i = lines.index(tm, start)
            except ValueError:
                continue
            tail = lines[i + 1:i + 20]
            nums = []
            for t in tail:
                if re.fullmatch(r"\d+", t):
                    nums.append(int(t))
                elif t == "-":
                    break
            if len(nums) >= 13:
                table[norm(tm)] = {"team": tm, "pos": nums[0], "pts": nums[1], "gp": nums[2],
                                   "w": nums[3], "l": nums[4], "sw": nums[5 + 8] if len(nums) > 13 else None,
                                   "sa": None, "pf": nums[13] if len(nums) > 13 else None,
                                   "pa": nums[14] if len(nums) > 14 else None}
        if not table:
            return
        # simple, deliberately low-confidence set-margin read on a one-round sample
        for e in inventory["sports"].get("Volleyball", {}).get("events", []):
            parts = re.split(r"\s+vs\s+", e["event"], maxsplit=1)
            if len(parts) != 2:
                continue
            ta = next((v for k, v in table.items() if norm(parts[0]) and norm(parts[0]).split()[0] in k), None)
            tb = next((v for k, v in table.items() if norm(parts[1]) and norm(parts[1]).split()[0] in k), None)
            if not (ta and tb):
                continue
            diff = (ta["pts"] - ta["gp"] * 1.5) - (tb["pts"] - tb["gp"] * 1.5)
            diff = max(-1.2, min(1.2, diff * 0.6))
            p_a = 1 / (1 + math.exp(-diff))
            mk = [market("Match Winner", None, parts[0], p_a, parts[1], 1 - p_a)]
            for line in (1.5, 2.5):
                pa_ = 1 - ncdf(line, diff * 1.4, 1.5)
                mk.append(market("Set Handicap", -line, f"{parts[0]} -{line} sets",
                                 pa_, f"{parts[1]} +{line} sets", 1 - pa_))
            row = add_row(sport="Volleyball", competition="SuperLega Credem Banca (Italy)",
                          side_a=parts[0], side_b=parts[1], start_utc=e.get("start_utc", ""),
                          official_url=reader.url("legavolley_classifica"),
                          official_source_name="Lega Pallavolo Serie A official standings (legavolley.it)",
                          evidence=reader.ev("legavolley_classifica"),
                          inputs_summary=(f"Official SuperLega table (after the first round): {ta['team']} {ta['w']}-{ta['l']} "
                                          f"on {ta['pts']} points vs {tb['team']} {tb['w']}-{tb['l']} on {tb['pts']} points. "
                                          f"The sample is one match per side, so confidence is capped."),
                          markets=mk)
            choose_pick(row, False)
            mk0 = e["markets"][0]
            row["olbg"] = {"event": e["event"], "event_url": e.get("event_url", ""),
                           "market": mk0.get("market", ""), "selection": mk0.get("selection", ""),
                           "decimal": mk0.get("decimal", ""), "american": mk0.get("american", ""),
                           "implied_prob": round(1 / float(mk0["decimal"]), 4) if mk0.get("decimal") else None}
        flag("AR-F-VB-01", "review", "Volleyball",
             "Italian prices rest on a single completed round",
             "The SuperLega table published after round one is the only official numeric input captured; set "
             "handicaps are therefore wide and confidence is capped below High.",
             reader.url("legavolley_classifica"))


    # ------------------------------------------------------------------
    # EHF Champions League — official 2026-27 group tables + match list
    # ------------------------------------------------------------------
    def ehf(reader, rendered, inventory):
        if not (rendered.has("ehfcl_standings") and rendered.has("ehfcl_matches")):
            flag("AR-F-EHF-01", "review", "Handball", "EHF Champions League pages not rendered",
                 "The official EHF pages were captured as client-side shells; the headless render did not "
                 "produce readable text, so the group-phase fixtures are listing-only.",
                 "https://ehfcl.eurohandball.com/men/2026-27/standings/")
            return
        st = rendered.text("ehfcl_standings")
        table = {}
        cur_group = ""
        for line in st.splitlines():
            line = line.strip()
            m = re.match(r"^GROUP ([A-D])", line)
            if m:
                cur_group = m.group(1)
                continue
            m = re.match(r"^(\d+)\.\s+(.+?)\t(\d+)\t(\d+)\t(\d+)\t(\d+)\t(\d+) : (\d+)\t(-?\d+)\t(\d+)$", line)
            if m:
                table[norm(m.group(2))] = {
                    "team": m.group(2), "pos": int(m.group(1)), "gp": int(m.group(3)),
                    "w": int(m.group(4)), "d": int(m.group(5)), "l": int(m.group(6)),
                    "gf": int(m.group(7)), "ga": int(m.group(8)),
                    "gd": int(m.group(9)), "pts": int(m.group(10)), "group": cur_group,
                }
        if len(table) < 16:
            flag("AR-F-EHF-02", "review", "Handball", "EHF tables parsed incompletely",
                 f"Only {len(table)} of the 16 group-phase clubs were matched in the rendered standings page; "
                 f"the affected fixtures are published unpriced.",
                 "https://ehfcl.eurohandball.com/men/2026-27/standings/")
            return
        fx = []
        lines = [l.strip() for l in rendered.text("ehfcl_matches").splitlines() if l.strip()]
        mon = {m: i for i, m in enumerate(
            ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
        i = 0
        while i < len(lines):
            m = re.match(r"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun) (\w{3}) (\d+), (\d{4})$", lines[i])
            if m and i + 5 < len(lines):
                date = f"{m.group(4)}-{mon.get(m.group(2),1):02d}-{int(m.group(3)):02d}"
                tm = re.match(r"^(\d{2}):(\d{2}) \(CET\) - (.*)$", lines[i + 1])
                if tm and i + 6 < len(lines):
                    home, away = lines[i + 2], lines[i + 5]
                    if lines[i + 3] == "0" and lines[i + 4] == "vs" and lines[i + 6] == "0":
                        fx.append({"date": date, "time": f"{tm.group(1)}:{tm.group(2)}",
                                   "venue": tm.group(3), "a": home, "b": away})
                        i += 7
                        continue
            i += 1
        url_s = rendered.url("ehfcl_standings")
        n = 0
        for f in fx:
            ta, tb = table.get(norm(f["a"])), table.get(norm(f["b"]))
            if not (ta and tb):
                continue
            lg = sum(t["gf"] for t in table.values()) / sum(t["gp"] for t in table.values())
            wa, wb = ta["gp"] / (ta["gp"] + 5), tb["gp"] / (tb["gp"] + 5)
            lam_a = (0.5 * (wa * ta["gf"] / ta["gp"] + (1 - wa) * lg) + 0.5 * (wb * tb["ga"] / tb["gp"] + (1 - wb) * lg)) + 1.0
            lam_b = (0.5 * (wb * tb["gf"] / tb["gp"] + (1 - wb) * lg) + 0.5 * (wa * ta["ga"] / ta["gp"] + (1 - wa) * lg)) - 0.2
            diff = (lam_a - lam_b) * 0.9 + 0.6 * ((ta["gd"] - tb["gd"]) / ta["gp"]) + 0.35 * ((ta["pts"] - tb["pts"]) / ta["gp"])
            p_a = min(0.95, max(0.05, ncdf(diff, 0, 5.4)))
            tot = lam_a + lam_b
            line = round(tot * 2) / 2
            mk = [market("Money Line", None, ta["team"], p_a, tb["team"], 1 - p_a)]
            mk += ns["hcp_ladder"](diff, 5.4, ta["team"], tb["team"], (2.5, 4.5, 6.5, 8.5))
            mk += ns["total_ladder"](tot, [line - 4.5, line, line + 4.5], poisson=False, sd=7.6)
            start = f"{f['date']}T{(int(f['time'][:2]) - 1):02d}:{f['time'][3:]}:00Z"
            row = add_row(sport="Handball", competition="EHF Champions League Men 2026-27",
                          round="Group Phase", side_a=ta["team"], side_b=tb["team"], start_utc=start,
                          venue=f["venue"],
                          official_url=url_s,
                          official_source_name="EHF Champions League official standings + match list (ehfcl.eurohandball.com)",
                          evidence=rendered._get("ehfcl_standings", "innertext.txt")[:0] + "render",
                          inputs_summary=(f"Official EHF group table (5 rounds): {ta['team']} {ta['w']}-{ta['d']}-{ta['l']} "
                                          f"({ta['gf']}:{ta['ga']}, {ta['pts']} pts, group {ta['group']}) vs {tb['team']} "
                                          f"{tb['w']}-{tb['d']}-{tb['l']} ({tb['gf']}:{tb['ga']}, {tb['pts']} pts, group {tb['group']}); "
                                          f"EHF lists the match for {f['date']} {f['time']} CET."),
                          markets=mk)
            choose_pick(row, ta["gp"] >= 4 and tb["gp"] >= 4)
            for ev0 in inventory["sports"].get("Handball", {}).get("events", []):
                if norm(ta["team"]).split()[0] in norm(ev0["event"]) and norm(tb["team"]).split()[0] in norm(ev0["event"]):
                    mk0 = ev0["markets"][0]
                    row["olbg"] = {"event": ev0["event"], "event_url": ev0.get("event_url", ""),
                                   "market": mk0.get("market", ""), "selection": mk0.get("selection", ""),
                                   "decimal": mk0.get("decimal", ""), "american": mk0.get("american", ""),
                                   "implied_prob": round(1 / float(mk0["decimal"]), 4) if mk0.get("decimal") else None}
                    break
            n += 1
        if n:
            flag("AR-F-EHF-03", "review", "Handball",
                 "EHF prices come only from the group tables",
                 "No squad, injury or venue-specific data is published on the EHF standings feed; the lines use "
                 "the official group records and goal differences, with kick-off times converted from CET.",
                 url_s)

    # ------------------------------------------------------------------
    # Cricket — ICC official team rankings
    # ------------------------------------------------------------------
    def cricket(reader, rendered, inventory):
        tables = {}
        for tid, fmt in (("icc_t20i_rankings", "T20I"), ("icc_odi_rankings", "ODI")):
            if not rendered.has(tid):
                continue
            t = rendered.text(tid)
            rows = re.findall(r"^(\d{2})\n\t\n([A-Z][A-Za-z \-]+)\n\t\n(\d+)\n\t\n(\d+)\n\t\n(\d+)$",
                              t, flags=re.M)
            if rows:
                tables[fmt] = {r[1].strip().upper(): {"pos": int(r[0]), "matches": int(r[2]),
                                                      "pts": int(r[3]), "rating": int(r[4])} for r in rows}
        if not tables:
            flag("AR-F-CRIC-01", "review", "Cricket", "ICC team rankings not parsed",
                 "The ICC ranking pages rendered but the table pattern was not recognised, so international "
                 "cricket rows stay listing-only.", "https://www.icc-cricket.com/rankings/mens/team-rankings/t20i")
            return
        url = rendered.url("icc_t20i_rankings")
        n = 0
        for e in inventory["sports"].get("Cricket", {}).get("events", []):
            ev = e["event"]
            parts = re.split(r"\s+vs\s+", ev)
            if len(parts) != 2:
                continue
            parts = [re.sub(r"\s+(One Day Match|One Day|T20 Match|T20I|ODI|Test Match|Test)$", "", p).strip() for p in parts]
            parts = [re.sub(r"\s+\d+(?:st|nd|rd|th)?\s*$", "", p).strip() for p in parts]
            fmt = "T20I" if "T20" in ev else ("ODI" if ("One Day" in ev or "ODI" in ev) else "TEST")
            tab = tables.get(fmt)
            if not tab:
                continue
            a = next((tab[k] for k in tab if norm(k).upper() in norm(parts[0]).upper()), None)
            b = next((tab[k] for k in tab if norm(k).upper() in norm(parts[1]).upper()), None)
            if not (a and b):
                continue
            p_a = 1 / (1 + math.exp(-((a["rating"] - b["rating"]) / 18.0 + 0.18)))
            mk = [market("Match Winner", None, parts[0], p_a, parts[1], 1 - p_a)]
            row = add_row(sport="Cricket", competition=ev,
                          side_a=parts[0], side_b=parts[1], start_utc=e.get("start_utc", ""),
                          official_url=url,
                          official_source_name="ICC official men's team rankings (icc-cricket.com)",
                          evidence="render:icc_t20i_rankings",
                          inputs_summary=(f"Official ICC {fmt} team ranking, 23 October 2026: {parts[0]} "
                                          f"rating {a['rating']} (#{a['pos']}) vs {parts[1]} rating {b['rating']} "
                                          f"(#{b['pos']}); home advantage priced as +3 rating points."),
                          markets=mk)
            choose_pick(row, False)
            mk0 = e["markets"][0]
            row["olbg"] = {"event": ev, "event_url": e.get("event_url", ""),
                           "market": mk0.get("market", ""), "selection": mk0.get("selection", ""),
                           "decimal": mk0.get("decimal", ""), "american": mk0.get("american", ""),
                           "implied_prob": round(1 / float(mk0["decimal"]), 4) if mk0.get("decimal") else None}
            n += 1
        if n:
            flag("AR-F-CRIC-02", "review", "Cricket",
                 "Cricket prices rest on the ICC team rating only",
                 "ICC ratings are the only official numeric input captured for these internationals; no lineup, "
                 "weather or pitch data was published, so confidence is capped below High.",
                 url)


    ns.update({"snooker": snooker, "darts": darts, "motor": motor, "volleyball": volleyball,
               "ehf": ehf, "cricket": cricket})
