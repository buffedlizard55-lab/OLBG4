#!/usr/bin/env python3
"""Board K — rebuild the root hub from a frozen base snapshot plus recorded evidence.

Nothing here invents a value. Every output value is either
  (a) copied from `data/board_k/base_matches.json` (the archived pre-remediation data), or
  (b) copied from `data/board_k/evidence.json`, which records what an official source
      actually returned when this session read it on 2026-10-21, or
  (c) blank, when neither of the above applies.

Run:  python3 scripts/board_k/build_hub.py
Writes: data/matches.json, data/board_k/verification.json, data/board_k/withdrawn_predictions.json,
        verification.html, flagged.html
"""
from __future__ import annotations

import html
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "data" / "board_k" / "base_matches.json"
EVIDENCE = ROOT / "data" / "board_k" / "evidence.json"

UNVERIFIED_BY_SPORT = {
    "Ice Hockey": "Not re-checked on an official NHL source during the 2026-10-21 verification cycle: participants, start time and venue could not be confirmed, so time and venue are blank and no prediction is published.",
    "Basketball": "Not re-checked on an official league source during the 2026-10-21 verification cycle: the fixture, its start time and venue could not be confirmed, so time and venue are blank and no prediction is published.",
    "Baseball": "Not re-checked on an official MLB source during the 2026-10-21 verification cycle: the fixture could not be confirmed, so time and venue are blank and no prediction is published.",
    "Cricket": "Not re-checked on an official governing-body source during the 2026-10-21 verification cycle: the fixture, start time and venue could not be confirmed, so they are blank and no prediction is published.",
    "Rugby Union": "Not re-checked on an official World Rugby or union source during the 2026-10-21 verification cycle: the fixture, kick-off time and venue could not be confirmed, so they are blank and no prediction is published.",
    "Tennis": "Tournament-level entry, not a single match, and the ATP/WTA page for this event could not be read back during this cycle: no date, court, time or opponent could be confirmed, so those fields are blank and no prediction is published.",
    "Snooker": "Not re-checked on World Snooker Tour during the 2026-10-21 verification cycle: the session date, table and time could not be confirmed, so they are blank and no prediction is published.",
    "Darts": "Not re-checked on PDC during the 2026-10-21 verification cycle (the PDC tournament page sits behind a cookie-consent wall that returned no fixture table): session times and venue are blank and no prediction is published.",
    "Golf": "Tournament-level entry rather than a head-to-head match; entry list, course and tee times were not read back from the official tour during this cycle, so they are blank and no match prediction is published.",
    "Badminton": "Not re-checked on BWF during the 2026-10-21 verification cycle: draw, court and session time could not be confirmed, so they are blank and no prediction is published.",
    "Table Tennis": "Not re-checked on ITTF/World Table Tennis during the 2026-10-21 verification cycle: draw, session time and venue could not be confirmed, so they are blank and no prediction is published.",
    "Volleyball": "Not re-checked on FIVB/Volleyball World during the 2026-10-21 verification cycle: this entry is a qualification or squad note rather than a scheduled fixture, so no date, time or venue is published.",
    "Handball": "Not re-checked on EHF/IHF during the 2026-10-21 verification cycle: the round-7 pairings and throw-off times could not be read from the official match centre, so they are blank and no prediction is published.",
    "Esports": "Not re-checked on the official Riot/Valorant schedule during the 2026-10-21 verification cycle: the bracket did not name these match-ups on the page read, so teams, times and venues are unpublished.",
    "Aussie Rules": "Off-season note rather than a fixture: the AFL fixture page could not be read back during this cycle, so no match, time or venue is published.",
    "Rugby League": "Not re-checked on NRL.com during the 2026-10-21 verification cycle. The NRL Pacific Championships page currently serves the 2025 season draw, so the claimed 2026 fixture could not be confirmed and is not published as a match.",
}

TOURNAMENT_SPORTS = {"Tennis", "Golf", "Badminton", "Table Tennis", "Darts", "Snooker",
                     "Volleyball", "Esports", "Aussie Rules", "Rugby League"}

FIELD_ORDER = [
    "id", "sport", "category", "competition", "date", "time", "venue", "match",
    "teamA", "teamB", "status", "originatedMoneyline", "originatedSpread",
    "originatedTotal", "marketFocus", "pick", "confidence", "prediction",
    "formNotes", "result", "grade", "sourceUrl", "sourceName", "priorSourceUrl",
    "priorSourceName", "verified",
    "flagged", "flagReason", "verification", "facts",
]


def load(path: Path):
    return json.loads(path.read_text())


def blank(value):
    return value is None or value == ""


def build():
    base = load(BASE)
    ev = load(EVIDENCE)
    rows_ev = ev["rows"]
    new_ev = ev["newRowEvidence"]
    preds = ev["predictions"]
    checked = ev["checkedAt"]

    out, register, withdrawn = [], [], []

    def apply(row, evidence, is_new=False):
        r = dict(row)
        corrections = evidence.get("corrections", {}) if evidence else {}
        status = evidence.get("status") if evidence else "unverified"

        # Retire anything the previous build asserted but this cycle could not verify.
        if status in ("unverified", "partial"):
            if status == "unverified":
                r["time"] = ""
                r["venue"] = ""
            r["prediction"] = ""
            r["confidence"] = "Low"

        for key, value in corrections.items():
            r[key] = value

        pred = preds.get(r["id"])
        if pred:
            r["prediction"] = pred["text"]
            r["confidence"] = pred["confidence"]
            r["pick"] = pred["pick"]
        else:
            # No published prediction means no claim above the base rate is being made.
            # A confirmed fixture with at least one quoted form fact may carry MEDIUM;
            # everything else drops to LOW.
            r["prediction"] = ""
            r["confidence"] = "Medium" if (status == "confirmed" and len((evidence or {}).get("facts", [])) >= 1) else "Low"

        if status == "confirmed":
            r["verified"] = True
            r["flagged"] = False
            r["flagReason"] = None
            r["sourceUrl"] = evidence["source"]["url"]
            r["sourceName"] = evidence["source"]["name"]
        else:
            if status == "unverified":
                # Keep the earlier link only as provenance; it is not evidence for any value.
                r["priorSourceUrl"] = row.get("sourceUrl", "")
                r["priorSourceName"] = row.get("sourceName", "")
                r["sourceUrl"] = ""
                r["sourceName"] = ""
            else:
                r["sourceUrl"] = evidence["source"]["url"]
                r["sourceName"] = evidence["source"]["name"]
            r["verified"] = False
            r["flagged"] = True
            r["flagReason"] = evidence.get("note") if evidence and evidence.get("note") else UNVERIFIED_BY_SPORT.get(r["sport"], "Could not be confirmed on an official source during the 2026-10-21 cycle; fields left blank rather than inferred.")

        r["verification"] = {
            "status": status,
            "checkedAt": checked,
            "officialUrl": (evidence or {}).get("source", {}).get("url", ""),
            "officialSource": (evidence or {}).get("source", {}).get("name", ""),
            "evidence": (evidence or {}).get("evidence", []),
            "correctedFields": sorted(corrections.keys()),
            "note": (evidence or {}).get("note") or (evidence or {}).get("correctionNote", ""),
            "session": ev["session"],
        }
        r["facts"] = (evidence or {}).get("facts", [])

        # Any original prose that is not republished verbatim is archived with its reason.
        if row.get("prediction") and row["prediction"] != r.get("prediction"):
            withdrawn.append({
                "id": r["id"], "sport": r["sport"], "match": r["match"],
                "text": row["prediction"],
                "stated_confidence": row.get("confidence"),
                "reason": ev["withdrawn"]["reason_not_a_match"] if r["sport"] in TOURNAMENT_SPORTS
                else ev["withdrawn"]["reason_unverifiable"],
            })

        # Published prose is regenerated, never inherited: only quoted official facts survive.
        facts = r["facts"]
        if facts:
            r["formNotes"] = "Verified on " + (evidence["source"]["name"]) + ": " + "; ".join(
                f"{f['claim']} — {f['value']}" for f in facts) + "."
        else:
            r["formNotes"] = ""

        # A fixture whose date has already passed is not "Scheduled"; say what is known.
        if str(r.get("status", "")).lower() != "completed" and str(r.get("date", ""))[:10] < checked:
            r["status"] = "Date passed — result not retrieved"

        # Only keep keys we define, in a stable order, then anything else that survived.
        ordered = {k: r[k] for k in FIELD_ORDER if k in r}
        for k, v in r.items():
            if k not in ordered:
                ordered[k] = v

        register.append({
            "id": ordered["id"],
            "sport": ordered["sport"],
            "match": ordered.get("match", ""),
            "date": ordered.get("date", ""),
            "dateStatus": "confirmed" if status == "confirmed" else "unverified",
            "verdict": status,
            "fieldsCorrected": sorted(corrections.keys()),
            "pick": ordered.get("pick", ""),
            "confidence": ordered.get("confidence", ""),
            "hasPrediction": bool(ordered.get("prediction")),
            "officialUrl": ordered["verification"]["officialUrl"],
            "officialSource": ordered["verification"]["officialSource"],
            "evidence": ordered["verification"]["evidence"],
            "note": ordered["verification"]["note"],
        })
        return ordered

    for row in base:
        out.append(apply(row, rows_ev.get(row["id"])))

    for row in ev["newRows"]:
        out.append(apply(row, new_ev.get(row["id"]), is_new=True))

    # ---- sanity gates: fail loudly rather than publish something unsupported ----
    ids = [r["id"] for r in out]
    assert len(ids) == len(set(ids)), "duplicate row ids"
    for r in out:
        if r["verified"]:
            assert r["sourceUrl"].startswith("https://"), r["id"]
            assert r["verification"]["evidence"], f"{r['id']} verified without quoted evidence"
            assert r["verification"]["officialUrl"], r["id"]
        if r["confidence"] == "High":
            assert r["prediction"], f"{r['id']} marked High without a prediction"
            assert len(r["prediction"].split()) >= 30, f"{r['id']} prediction under 30 words"
            assert r["verification"]["status"] == "confirmed", f"{r['id']} High without confirmed fixture"
            assert len(r.get("facts", [])) >= 2, f"{r['id']} High without two verified facts"
        if blank(r["prediction"]):
            assert r["confidence"] != "High", r["id"]
    high_texts = [r["prediction"] for r in out if r["confidence"] == "High"]
    assert len(high_texts) == len(set(high_texts)), "duplicate prediction text"

    (ROOT / "data" / "matches.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    (ROOT / "data" / "board_k" / "withdrawn_predictions.json").write_text(
        json.dumps({
            "session": ev["session"],
            "withdrawnAt": checked,
            "count": len(withdrawn),
            "reason": ev["withdrawn"]["reason_unverifiable"],
            "items": withdrawn,
        }, indent=2, ensure_ascii=False) + "\n")

    verdicts = Counter(r["verdict"] for r in register)
    summary = {
        "schema": "olbg4.board-k.verification/1",
        "session": ev["session"],
        "checkedAt": checked,
        "policy": ev["policy"],
        "counts": {
            "rows": len(register),
            "confirmed": verdicts["confirmed"],
            "partial": verdicts["partial"],
            "unverified": verdicts["unverified"],
            "highConfidence": sum(1 for r in out if r["confidence"] == "High"),
            "predictions": sum(1 for r in out if r["prediction"]),
            "withdrawnPredictions": len(withdrawn),
        },
        "sourcesUsed": ev["sourcesUsed"],
        "checks": register,
    }
    (ROOT / "data" / "board_k" / "verification.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n")

    write_verification_page(summary)
    write_flagged_page(summary, out)
    return summary


NAV = '''<nav class="nav"><a href="index.html">Dashboard</a><a href="verification.html">Verification</a><a href="methodology.html">Methodology</a><a href="sources.html">Sources</a><a href="flagged.html">Flagged for Review</a></nav>'''


def page(title, heading, body):
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="OLBG4 — line-by-line verification register: every row, the official source it was checked against, and the verdict.">
<link rel="stylesheet" href="assets/css/style.css">
</head>
<body>
<header class="topbar">
  <div class="container inner">
    <div class="brand"><div class="logo">OL</div><div><h1>OLBG<span>4</span></h1><p>{html.escape(heading)}</p></div></div>
    {NAV}
  </div>
</header>
<main class="container">
{body}
  <div class="footer">OLBG4 • verified register • data cut-off 2026-10-21 • <a href="index.html">Dashboard</a> • <a href="flagged.html">Flagged for Review</a> • <a href="https://github.com/buffedlizard55-lab/OLBG4" target="_blank" rel="noopener">GitHub repo</a></div>
</main>
<script src="assets/js/main.js"></script>
</body>
</html>
'''


VERDICT_BADGE = {
    "confirmed": '<span class="badge badge-verified">CONFIRMED</span>',
    "partial": '<span class="badge badge-flagged">PARTIAL</span>',
    "unverified": '<span class="badge badge-flagged">UNVERIFIED</span>',
}


def e(x):
    return html.escape(str(x), quote=True)


def write_verification_page(summary):
    c = summary["counts"]
    rows = []
    order = {"confirmed": 0, "partial": 1, "unverified": 2}
    for chk in sorted(summary["checks"], key=lambda r: (order[r["verdict"]], r["sport"], r["id"])):
        link = (f'<a href="{e(chk["officialUrl"])}" target="_blank" rel="noopener">{e(chk["officialSource"])}</a>'
                if chk["officialUrl"] else '<span class="small">none located</span>')
        ev_html = ''.join(f'<div class="small">“{e(x)}”</div>' for x in chk["evidence"]) or \
            '<span class="small">No official page returned these values in this cycle.</span>'
        corrections = ', '.join(chk["fieldsCorrected"]) if chk["fieldsCorrected"] else '—'
        rows.append(f'''<tr>
  <td><strong>{e(chk["id"])}</strong><div class="small">{e(chk["date"])}</div></td>
  <td><span class="tag">{e(chk["sport"])}</span></td>
  <td>{e(chk["match"])}<div class="small">{e(chk["note"])}</div></td>
  <td>{VERDICT_BADGE[chk["verdict"]]}<div class="small">date: {e(chk["dateStatus"])}</div></td>
  <td class="small">{ev_html}</td>
  <td class="small">{link}</td>
  <td class="small">Corrected: {e(corrections)}<div>{e(chk["pick"])}<br>{e(chk["confidence"])}{" · prediction" if chk["hasPrediction"] else ""}</div></td>
</tr>''')

    source_list = ''.join(
        f'<li><a href="{e(s["url"])}" target="_blank" rel="noopener">{e(s["name"])}</a></li>'
        for s in summary["sourcesUsed"])

    body = f'''  <section class="hero">
    <h2>Verification register — every hub row, the official source, and the verdict</h2>
    <p>This page is generated from <code>data/board_k/verification.json</code> by <code>scripts/board_k/build_hub.py</code>. It lists the check performed for each of the {c["rows"]} rows on the dashboard: which official endpoint or page was opened, the exact values it returned, what was corrected, and whether the row is <b>CONFIRMED</b>, <b>PARTIAL</b> or <b>UNVERIFIED</b>.</p>
    <div class="notice"><strong>What the labels mean.</strong> CONFIRMED — participants, date and the published start time were read back from an official league or governing-body source during the 2026-10-21 cycle, and the returned values are quoted in the row. PARTIAL — part of the row was confirmed and the rest was blanked. UNVERIFIED — nothing could be confirmed; time and venue are blank, the pick survives only as our own model output at LOW confidence, and the prediction text is withdrawn rather than reworded.</div>
  </section>

  <section class="kpis">
    <div class="kpi"><div class="label">Rows in register</div><div class="value">{c["rows"]}</div><div class="sub">{c["confirmed"]} confirmed · {c["partial"]} partial · {c["unverified"]} unverified</div></div>
    <div class="kpi"><div class="label">Quoted official checks</div><div class="value">{sum(len(x["evidence"]) for x in summary["checks"])}</div><div class="sub">verbatim values read back from the source in this cycle</div></div>
    <div class="kpi"><div class="label">High-confidence picks</div><div class="value">{c["highConfidence"]}</div><div class="sub">both sides' form verified · each ≥30 words</div></div>
    <div class="kpi"><div class="label">Predictions withdrawn</div><div class="value">{c["withdrawnPredictions"]}</div><div class="sub">claims absent from every official page we could open</div></div>
  </section>

  <section class="table-wrap">
    <div style="padding:10px 14px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;background:#f8fafc">
      <strong style="font-size:13px">Line-by-line register</strong><span class="small">Verdict • quoted evidence • official link • correction</span>
    </div>
    <div style="overflow:auto;max-height:75vh">
      <table>
        <thead><tr><th style="min-width:110px">Row</th><th>Sport</th><th style="min-width:230px">Match (as published)</th><th style="min-width:120px">Verdict</th><th style="min-width:320px">What the official source returned</th><th style="min-width:190px">Official source opened</th><th style="min-width:180px">Correction / pick</th></tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </div>
  </section>

  <section class="grid2" style="margin:16px 0">
    <div class="card">
      <h3>Sources opened in this cycle</h3>
      <ul class="small">{source_list}</ul>
      <p class="small">Every URL above is a league or governing-body property (nhl.com / api-web.nhle.com, mlb.com / statsapi.mlb.com, nba.com, pcb.com.pk, wst.tv). No bookmaker price and no OLBG tip is used as evidence.</p>
    </div>
    <div class="card">
      <h3>How to reproduce one line</h3>
      <ol class="small">
        <li>Pick a row, open the official link in the same line.</li>
        <li>Compare the quoted values with the match you see on the page.</li>
        <li>If they disagree, the row is wrong and the quote is on this page — open an issue with the row id.</li>
        <li>If a field is blank, it was not confirmable; it was not inferred or copied from another build.</li>
      </ol>
      <p class="small">Limits: league feeds answer for their own sport only. Where a page is JavaScript-rendered or behind a consent wall (EuroLeague, PDC, NRL, World Rugby, lolesports, EHF), no value was taken from memory — the row is marked unverified.</p>
    </div>
  </section>'''
    (ROOT / "verification.html").write_text(
        page("Verification register — OLBG4", "Verification register — line by line", body))


def findings(c):
    return [
        ("high", "K-01", f"{c['withdrawnPredictions']} prediction texts withdrawn",
         "Every prediction published by the earlier hub asserted form, injury or head-to-head numbers that appear on no official source "
         "(Board J's audit found the same for NHL01, NHL06, EL02, MLB01 and RL01). None was reworded around its claim: all of them are archived "
         "verbatim with their stated confidence in <code>data/board_k/withdrawn_predictions.json</code>, and only prose rebuilt from quoted official "
         "facts is published.",
         "<a href='https://github.com/buffedlizard55-lab/OLBG4/blob/main/data/board_k/withdrawn_predictions.json'>withdrawn_predictions.json</a>"),
        ("high", "K-02", f"{c['unverified']} of {c['rows']} rows could not be confirmed",
         "Only the rows marked CONFIRMED on the verification register were read back from an official source in this cycle. The rest keep the "
         "participants and date as previously published but lose their start time, venue, prediction and any confidence above LOW. They are not "
         "inferred and not copied from another build; the earlier link is kept only as <code>priorSourceUrl</code> provenance.",
         "<a href='verification.html'>Verification register</a>"),
        ("medium", "K-03", "Fixture fields corrected against governing bodies",
         "CRK03: PCB says this is <b>match 2</b> (Pakistan v England) on 20 Oct at Rawalpindi, not 'match 1' over a 20-29 Oct range at Lahore. "
         "CRK05: the final is <b>31 Oct</b> at Gaddafi Stadium — 29 Oct is Sri Lanka v England. MLB03: MLB's schedule names <b>Tropicana Field</b>, "
         "not Steinbrenner Field. NHL01/NHL02 now carry the official final scores. The six rugby fixtures are titled <b>Nations Championship 2026</b> "
         "by World Rugby, not the Autumn Nations Series.",
         "<a href='https://www.pcb.com.pk/press-release-detail/pakistan-to-host-sri-lanka-and-england-for-t20is-odi-tri-series-and-tests.html' target='_blank' rel='noopener'>PCB release</a> · "
         "<a href='https://statsapi.mlb.com/api/v1/schedule?sportId=1&date=2026-10-26' target='_blank' rel='noopener'>MLB schedule 26 Oct</a> · "
         "<a href='https://www.world.rugby/beta/en/match/1e74b48e-25fe-4ebe-beea-abb6cea010a0' target='_blank' rel='noopener'>World Rugby match page</a>"),
        ("medium", "K-04", "Rows that are not matches",
         "Tennis (6), golf (5), badminton (3), table tennis (3), darts (4), snooker (4), volleyball (2), handball (2), esports (2), the AFL "
         "off-season note and the Pacific Championships note are tournaments, rounds, qualification notes or off-season statements. A head-to-head "
         "pick cannot be originated without a specific fixture, so those picks are LOW and their times, venues and predictions are blank.",
         "<a href='data/matches.json'>data/matches.json</a>"),
        ("medium", "K-05", "Cross-session collision on this hub's files (resolved, nothing discarded)",
         "Two sessions independently claimed 'Board K' and both edited <code>data/matches.json</code>. Session <code>093bfd5e</code> landed first on "
         "<code>main</code>; this session rebuilt the file from a frozen base plus recorded evidence. Their work is preserved: their data file is archived "
         "as <code>data/board_k/prior_session_matches.json</code>, their World Rugby and BWF URLs were re-opened and adopted, and their EuroLeague claim is "
         "disputed below rather than silently kept or silently deleted.",
         "<a href='https://github.com/buffedlizard55-lab/OLBG4/blob/main/data/board_k/prior_session_matches.json'>prior_session_matches.json</a>"),
        ("medium", "K-06", "A prior-session 'confirmed' claim that does not survive re-checking",
         "Session <code>093bfd5e</code> marked EL01 and EL02 as confirmed against the EuroLeague 2026-27 schedule release. That release (29 July 2026) "
         "announces the season and opening-night games on 24-25 September; it does not list the Round 7 fixtures on 22 October. Both rows therefore remain "
         "UNVERIFIED here, and the fixture-level claim is withdrawn pending a Round 7 page.",
         "<a href='https://www.euroleaguebasketball.net/en/euroleague/news/the-2026-27-euroleague-schedule-is-official/' target='_blank' rel='noopener'>EuroLeague release</a>"),
        ("low", "K-07", "Pages that still could not be read back as fixtures",
         "EuroLeague game centre (client-side shell), PDC (consent wall), NRL Pacific Championships (serves the 2025 draw), EHF, lolesports, ATP/WTA, "
         "WTT, FIVB, PGA/LPGA and AFL. Rows that depend on those pages are unverified instead of being given a value from memory.",
         "<a href='https://www.nrl.com/pacific-championships/' target='_blank' rel='noopener'>nrl.com</a> · "
         "<a href='https://www.pdc.tv/tournaments/machineseeker-european-championship' target='_blank' rel='noopener'>pdc.tv</a>"),
        ("low", "K-08", f"Confidence is capped by evidence ({c['highConfidence']} high-confidence picks)",
         "HIGH is used only where both sides' current form was read from an official feed and quoted on the register. This cycle that is true for "
         "NHL05, NHL07 and NHL08. Nothing was promoted to HIGH to fill a quota, and the one medium prediction (MLB01) states explicitly why it is not high.",
         "<a href='methodology.html'>Methodology</a>"),
        ("low", "K-09", "Unresolved on other boards' files: Build A / Build B overwrite",
         "Board J recorded that commit <code>cf9f024</code> replaced Build A's <code>data/rows.json</code> and Build B's <code>data/predictions.json</code>. "
         "This session does not own those files and has not edited them; the request stands with their owning sessions.",
         "<a href='https://github.com/buffedlizard55-lab/OLBG4/blob/main/COORDINATION.md'>COORDINATION.md</a>"),
        ("medium", "K-11", "A second root presentation was published from a different snapshot",
         "Session <code>arena/83451f65-olbg4</code> merged its own static site into this repository while this board was open: "
         "<a href='entries.html'>entries.html</a>, <a href='predictions.html'>predictions.html</a>, <a href='analysis.html'>analysis.html</a>, "
         "<a href='coverage.html'>coverage.html</a>, <a href='archive.html'>archive.html</a> and <a href='sports/ice-hockey.html'>sports/</a>, all generated by its "
         "<code>build_site.py</code> from a 75-row snapshot of its own. Its headline counts therefore differ from this hub's 68 rows and its prices "
         "are Model v1 re-derivations of the same fixtures. Nothing was deleted: those pages are published unchanged and linked from the dashboard, "
         "but the <a href='verification.html'>Verification register</a> and <a href='data/matches.json'>data/matches.json</a> remain the authoritative "
         "record for this hub. Do not add the two sets together.",
         "<a href='entries.html'>entries.html</a> · <a href='verification.html'>our register</a>"),
        ("low", "K-10", "Excluded sports are still excluded",
         "Soccer, boxing, UFC/MMA, football, American football, hurling, horse racing, cycling and specials appear nowhere in the hub. Gaelic football and "
         "greyhounds are not in the hub either; they appear only inside other sessions' builds, which this session did not edit.",
         "<a href='index.html'>Dashboard</a>"),
    ]


def write_flagged_page(summary, rows):
    c = summary["counts"]
    items = ''.join(f'''<tr>
  <td class="small">{e(sev.upper())}</td>
  <td><strong>{e(kid)}</strong><div class="small">{e(title)}</div></td>
  <td class="small">{text}</td>
  <td class="small">{links}</td>
</tr>''' for sev, kid, title, text, links in findings(c))

    body = f'''  <section class="hero">
    <h2>Flagged for Review</h2>
    <p>Everything this cycle could not confirm is collected here, with the official link to check it against. Flagged items do not block publication: the dashboard shows them with an <b>UNVERIFIED</b> badge, blank times and venues where nothing was confirmed, and no prediction.</p>
    <div class="notice"><strong>Policy:</strong> a value that cannot be confirmed from an official source is left blank and flagged. It is never inferred, never copied from a bookmaker, and never carried over silently from an earlier session. Verdicts and quoted evidence for every row are on the <a href="verification.html">Verification register</a>.</div>
    <div class="small" style="margin-top:10px"><strong id="flaggedCount">loading…</strong> • {c["confirmed"]} rows confirmed on an official source this cycle.</div>
  </section>

  <section class="table-wrap">
    <div style="padding:10px 14px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;background:#fffbeb"><strong>Row-level flags from data/matches.json</strong><span class="small">Each row links its official source for manual comparison</span></div>
    <div style="overflow:auto;max-height:60vh">
      <table>
        <thead><tr><th style="min-width:80px">ID</th><th style="min-width:240px">Match (as published)</th><th style="min-width:320px">Why it is flagged</th><th style="min-width:220px">Source link for review</th><th style="min-width:110px">Status</th></tr></thead>
        <tbody id="flaggedTbody"><tr><td colspan="5" style="padding:16px" class="small">Loading…</td></tr></tbody>
      </table>
    </div>
  </section>

  <section class="card" style="margin-top:14px">
    <h3>Session findings — 2026-10-21 remediation</h3>
    <table style="width:100%;border-collapse:collapse">
      <thead><tr><th style="text-align:left;padding:8px;border-bottom:1px solid var(--line)">Severity</th><th style="text-align:left;padding:8px;border-bottom:1px solid var(--line)">Finding</th><th style="text-align:left;padding:8px;border-bottom:1px solid var(--line)">Detail</th><th style="text-align:left;padding:8px;border-bottom:1px solid var(--line)">Check it here</th></tr></thead>
      <tbody>{items}</tbody>
    </table>
  </section>

  <section class="card">
    <h3>Previously logged irregularities (Board D / Board J) — status in this hub</h3>
    <ul class="small">
      <li><b>Board J F-01</b> — 26 rows verified without an official link. <b>Addressed here:</b> no row in this hub carries a "verified" badge unless an official source was opened and quoted in this cycle; the remainder are unverified.</li>
      <li><b>Board J F-02</b> — predictions contradicted by NHL.com, MLB.com and NRL.com. <b>Addressed here:</b> all 15 withdrawn; see K-01.</li>
      <li><b>Board J F-03</b> — CRK03, CRK05, MLB03, EL02 field errors. <b>Addressed here:</b> CRK03, CRK05 and MLB03 corrected from the governing body (K-03). EL02 could not be verified on EuroLeague, so it is now unverified rather than corrected.</li>
      <li><b>Board J F-04</b> — non-match entries. <b>Addressed here:</b> flagged as K-04 and stripped of predictions.</li>
      <li><b>Board J F-11/F-12</b> — Build A/B data overwritten. <b>Not addressed:</b> outside this session's file scope; logged as K-05.</li>
      <li><b>Build D's own claim</b> that every row's source is a governing-body domain was not true of the data. The hub no longer makes that claim; the register shows exactly which rows have official links.</li>
    </ul>
  </section>'''
    (ROOT / "flagged.html").write_text(
        page("Flagged for Review — OLBG4", "Flagged for Review — irregularities & unverified items", body))


if __name__ == "__main__":
    summary = build()
    print(json.dumps(summary["counts"], indent=2))
