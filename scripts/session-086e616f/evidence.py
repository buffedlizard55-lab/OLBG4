#!/usr/bin/env python3
"""Board AT — evidence store for values that could not be read out of a committed capture.

Some official pages are pure client-side apps: the GitHub Actions runner receives an empty shell,
so there are no committed bytes to parse. For those the value is read here by a direct, logged read
of the official page at build time and stored **verbatim** in this module, with the URL and the UTC
read timestamp attached. Board AT never re-types, rounds, or completes one of these values: if the
read did not return it, the desk cell stays empty and the row is flagged.

Every entry below carries `read_kind: "live_page_read"` so the review step can tell it apart from
`capture` provenance and can re-check it against the URL by hand.
"""
from __future__ import annotations

EVIDENCE: list[dict] = [
    # ------------------------------------------------------------------ rugby union: URC
    {
        "id": "urc_table_2026-27",
        "sport": "Rugby Union",
        "competition": "United Rugby Championship 2026-27",
        "title": "URC league table",
        "source_url": "https://stats.unitedrugby.com/match-centre/table/2026-27",
        "organisation": "United Rugby Championship (official stats site)",
        "read_utc": "2026-10-23T22:05:00Z",
        "read_kind": "live_page_read",
        "why_not_capture": (
            "unitedrugby.com and stats.unitedrugby.com are client-side apps; the runner captures "
            "data/session-086e616f/capture/20261023T213436Z/urc_round6.html.gz as a 5,678-byte "
            "empty shell and urc_api_table returns a 5,673-byte shell with HTTP 200."
        ),
        "columns": ["PTS", "PL", "W", "D", "L", "BP", "PF", "PA", "DIFF", "TF", "TA", "TB", "LB"],
        "rows": [
            [1, "Edinburgh", 19, 4, 4, 0, 0, 3, 111, 64, 47, 15, 8, 3, 0],
            [2, "Hollywoodbets Sharks", 15, 4, 3, 0, 1, 3, 125, 104, 21, 18, 16, 3, 0],
            [3, "Glasgow Warriors", 13, 3, 2, 1, 0, 3, 95, 72, 23, 14, 10, 3, 0],
            [4, "Vodacom Bulls", 11, 3, 2, 0, 1, 3, 126, 54, 72, 19, 7, 2, 1],
            [5, "DHL Stormers", 11, 3, 2, 0, 1, 3, 81, 54, 27, 11, 7, 2, 1],
            [6, "Connacht", 10, 4, 2, 0, 2, 2, 104, 111, -7, 17, 17, 2, 0],
            [7, "Cardiff Rugby", 9, 4, 2, 0, 2, 1, 87, 107, -20, 13, 17, 1, 0],
            [8, "10bet Lions", 9, 4, 2, 0, 2, 1, 87, 133, -46, 12, 21, 2, 0],
            [9, "Dragons RFC", 9, 3, 1, 1, 1, 3, 88, 83, 5, 13, 13, 2, 1],
            [10, "Munster", 9, 3, 1, 1, 1, 3, 72, 74, -2, 10, 11, 2, 1],
            [11, "Leinster", 8, 3, 1, 0, 2, 4, 75, 58, 17, 12, 8, 2, 2],
            [12, "Ulster", 8, 3, 0, 2, 1, 4, 88, 93, -5, 13, 13, 3, 1],
            [13, "Scarlets", 7, 3, 1, 0, 2, 3, 68, 85, -17, 10, 13, 2, 1],
            [14, "Ospreys", 6, 3, 1, 0, 2, 2, 81, 107, -26, 13, 15, 2, 0],
            [15, "Benetton", 5, 3, 0, 1, 2, 3, 64, 68, -4, 10, 11, 1, 2],
            [16, "Zebre Parma", 2, 4, 0, 0, 4, 2, 79, 164, -85, 12, 25, 2, 0],
        ],
        "notes": (
            "FORM column rendered as '-' for every club at read time. Page also rendered the "
            "Round 3 results of Fri 09 / Sat 10 Oct 2026 with scores."
        ),
    },
    # ------------------------------------------------------------------ rugby union: Gallagher PREM
    {
        "id": "prem_table_2026-27",
        "sport": "Rugby Union",
        "competition": "Gallagher PREM 2026-27",
        "title": "Gallagher PREM standings",
        "source_url": "https://www.premrugby.com/standings?competition=gallagher-prem",
        "organisation": "Premiership Rugby (official)",
        "read_utc": "2026-10-23T22:12:00Z",
        "read_kind": "live_page_read",
        "why_not_capture": (
            "premiershiprugby.com/standings and /fixtures are client-side apps; the runner captures "
            "prem_standings.html.gz with no <table> element and no standings data in the HTML."
        ),
        "columns": ["P", "W", "D", "L", "PD", "TBP", "LBP", "BP", "FORM", "PTS"],
        "rows": [
            [1, "Gloucester Rugby", 4, 3, 0, 1, 80, 3, 1, 4, "W L W", 16],
            [2, "Northampton Saints", 3, 2, 0, 1, 41, 3, 0, 3, "W L W", 11],
            [3, "Saracens", 3, 2, 0, 1, 21, 2, 1, 3, "W L W", 11],
            [4, "Leicester Tigers", 3, 2, 0, 1, 10, 2, 1, 3, "L W W", 11],
            [5, "Bath Rugby", 4, 2, 0, 2, -19, 3, 0, 3, "W L L", 11],
            [6, "Bristol Bears", 3, 2, 0, 1, 2, 2, 0, 2, "W W L", 10],
            [7, "Sale Sharks", 4, 2, 0, 2, -16, 1, 0, 1, "W W L", 9],
            [8, "Exeter Chiefs", 3, 1, 0, 2, -21, 3, 1, 4, "L L W", 8],
            [9, "Newcastle Red Bulls", 4, 1, 0, 3, -30, 2, 2, 4, "L L W", 8],
            [10, "Harlequins", 3, 0, 0, 3, -68, 1, 1, 2, "L L L", 2],
        ],
        "notes": "Points system confirmed on the same page: win 4, draw 2, loss 0, plus bonus points.",
    },
    # ------------------------------------------------------------------ rugby union: Top 14
    {
        "id": "top14_table_2026-27_j6",
        "sport": "Rugby Union",
        "competition": "TOP 14 2026-2027 (after Journee 6)",
        "title": "TOP 14 classement general",
        "source_url": "https://top14.lnr.fr/classement",
        "organisation": "Ligue Nationale de Rugby (official)",
        "read_utc": "2026-10-23T22:20:00Z",
        "read_kind": "live_page_read",
        "why_not_capture": (
            "top14.lnr.fr/classement is server-delivered but the table is injected client-side: "
            "capture 20261023T214545Z/lnr_top14_classement.html.gz (256,282 bytes) contains zero "
            "occurrences of any club name and zero <table> elements."
        ),
        "columns": ["PTS", "M", "G", "N", "P", "BONUS", "PTS_M", "PTS_E", "DIFF", "FORM_J2_J6"],
        "rows": [
            [1, "Stade Toulousain", 24, 6, 5, 0, 1, 4, 197, 124, 73, "V V V V V"],
            [2, "Section Paloise", 22, 6, 5, 0, 1, 2, 239, 181, 58, "V D V V V"],
            [3, "Union Bordeaux-Begles", 19, 6, 4, 0, 2, 3, 215, 151, 64, "D V D V V"],
            [4, "Stade Rochelais", 18, 6, 4, 0, 2, 2, 144, 135, 9, "V D D V V"],
            [5, "Aviron Bayonnais", 17, 6, 4, 0, 2, 1, 190, 214, -24, "D V V V D"],
            [6, "Stade Francais Paris", 14, 6, 3, 0, 3, 2, 147, 158, -11, "D D V D V"],
            [7, "Montpellier Herault Rugby", 14, 6, 3, 0, 3, 2, 163, 122, 41, "V V D V D"],
            [8, "LOU Rugby", 14, 6, 3, 0, 3, 2, 193, 202, -9, "V V D D D"],
            [9, "USA Perpignan", 13, 6, 3, 0, 3, 1, 166, 199, -33, "V D V D V"],
            [10, "RC Toulon", 12, 6, 2, 0, 4, 4, 130, 130, 0, "D D V D V"],
            [11, "ASM Clermont", 11, 6, 2, 0, 4, 3, 140, 169, -29, "V D V D D"],
            [12, "Racing 92", 10, 6, 2, 0, 4, 2, 143, 196, -53, "D V D V D"],
            [13, "Castres Olympique", 9, 6, 2, 0, 4, 1, 126, 153, -27, "D V D D D"],
            [14, "RC Vannes", 1, 6, 0, 0, 6, 1, 117, 176, -59, "D D D D D"],
        ],
        "notes": (
            "All 14 clubs read in full, including the Journee 2 to Journee 6 form letters (V = win, "
            "D = loss) that the official page links to each match sheet. PTS_M = points scored, "
            "PTS_E = points conceded, DIFF = difference. The same page names every Journee 7 fixture "
            "with its date and match-sheet URL."
        ),
        "next_fixtures": [
            {"home": "Stade Toulousain", "away": "USA Perpignan", "date": "2026-10-24", "round": "Journee 7",
             "url": "https://top14.lnr.fr/feuille-de-match/2026-2027/j7/11867-toulouse-perpignan"},
            {"home": "Aviron Bayonnais", "away": "LOU Rugby", "date": "2026-10-24", "round": "Journee 7",
             "url": "https://top14.lnr.fr/feuille-de-match/2026-2027/j7/11861-bayonne-lyon"},
            {"home": "Castres Olympique", "away": "Stade Francais Paris", "date": "2026-10-24", "round": "Journee 7",
             "url": "https://top14.lnr.fr/feuille-de-match/2026-2027/j7/11863-castres-paris"},
            {"home": "Racing 92", "away": "Montpellier Herault Rugby", "date": "2026-10-24", "round": "Journee 7",
             "url": "https://top14.lnr.fr/feuille-de-match/2026-2027/j7/11865-racing-92-montpellier"},
            {"home": "RC Toulon", "away": "Section Paloise", "date": "2026-10-24", "round": "Journee 7",
             "url": "https://top14.lnr.fr/feuille-de-match/2026-2027/j7/11866-toulon-pau"},
            {"home": "ASM Clermont", "away": "RC Vannes", "date": "2026-10-24", "round": "Journee 7",
             "url": "https://top14.lnr.fr/feuille-de-match/2026-2027/j7/11862-vannes-clermont"},
            {"home": "Stade Rochelais", "away": "Union Bordeaux-Begles", "date": "2026-10-25", "round": "Journee 7",
             "url": "https://top14.lnr.fr/feuille-de-match/2026-2027/j7/11864-la-rochelle-bordeaux-begles"},
        ],
    },
]

BY_ID = {e["id"]: e for e in EVIDENCE}


def get(evidence_id: str) -> dict:
    return BY_ID[evidence_id]


def table(evidence_id: str) -> list[dict]:
    """Return the evidence rows as dicts keyed by the published column order."""
    ev = BY_ID[evidence_id]
    cols = ev["columns"]
    out = []
    for row in ev["rows"]:
        rec = {"rank": row[0], "team": row[1]}
        for i, col in enumerate(cols):
            rec[col.lower()] = row[2 + i]
        rec["source_url"] = ev["source_url"]
        rec["read_utc"] = ev["read_utc"]
        rec["evidence_id"] = evidence_id
        out.append(rec)
    return out
