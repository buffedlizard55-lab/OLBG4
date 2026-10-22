#!/usr/bin/env python3
"""Board AF - parse the official ATP Tour daily-schedule pages committed by the capture runner.

Source pages (both HTTP 200 on the pass-2 capture, sha256 in the manifest):
  https://www.atptour.com/en/scores/current/brussels/7485/daily-schedule
  https://www.atptour.com/en/scores/current/almaty/9410/daily-schedule

Only what the ATP page itself prints is extracted: match date, round, players, published seed
numbers and the official player profile URLs. Doubles ties are detected and excluded.
"""
from __future__ import annotations
import glob, hashlib, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data", "session-80bc6293")
TOURNAMENTS = {
    "atp_scores_br": {"name": "BNP Paribas Fortis European Open", "city": "Brussels, Belgium",
                      "level": "ATP 250", "id": "7485",
                      "url": "https://www.atptour.com/en/scores/current/brussels/7485/daily-schedule"},
    "atp_scores_almaty": {"name": "Almaty Open", "city": "Almaty, Kazakhstan", "level": "ATP 250", "id": "9410",
                          "url": "https://www.atptour.com/en/scores/current/almaty/9410/daily-schedule"},
}
PLAYER_RE = re.compile(
    r'<a href="(/en/players/[a-z0-9\-]+/[a-z0-9]+/overview)">\s*<span>(.*?)</span>\s*(.*?)</a>'
    r'(?:\s*<div class="rank">\s*<span>\((\d{1,2})\)</span>\s*</div>)?', re.S)


def side(block: str) -> dict:
    m = PLAYER_RE.search(block)
    if not m:
        names = re.findall(r'<span>(.*?)</span>\s*([A-Za-z\u00c0-\uffff\-\.\' ]{2,24})\s*</a>', block)
        return {"name": "", "seed": None, "url": "", "doubles": bool(names)}
    url, initial, last, seed = m.group(1), m.group(2), m.group(3), m.group(4)
    last = re.sub(r"<[^>]+>", "", last)
    name = (initial.strip() + " " + last.strip()).strip()
    return {"name": re.sub(r"\s+", " ", name), "seed": int(seed) if seed else None,
            "url": "https://www.atptour.com" + url,
            "doubles": "/" in name or name.count(" ") > 2}


def main() -> int:
    caps = sorted(glob.glob(os.path.join(DATA, "capture", "2*")))
    if not caps:
        print("no capture"); return 1
    latest = caps[-1]
    matches, evidence = [], []
    for tid, tour in TOURNAMENTS.items():
        for sub in ("pass2/raw", "raw"):
            f = os.path.join(latest, sub, tid + ".bin")
            if os.path.exists(f):
                break
        else:
            evidence.append({"id": tid, "error": "not captured"})
            continue
        raw = open(f, "rb").read()
        s = raw.decode("utf-8", "replace")
        evidence.append({"id": tid, "url": tour["url"], "sha256": hashlib.sha256(raw).hexdigest(),
                         "bytes": len(raw), "file": os.path.relpath(f, ROOT)})
        blocks = re.findall(r'<div class="schedule"([^>]*)>(.*?)(?=<div class="schedule"|</main>|$)', s, re.S)
        n = 0
        for attrs, body in blocks:
            date = re.search(r'data-matchdate="([0-9\-]{10})"', attrs)
            rtype = re.search(r'<div class="schedule-type">\s*([A-Za-z0-9 ]{1,12})\s*</div>', body)
            mtime = re.search(r'<span class="matchtime">(.*?)</span>', body, re.S)
            pl = re.search(r'<div class="player">(.*?)</div>\s*</div>\s*<div class="status">', body, re.S)
            op = re.search(r'<div class="opponent">(.*)$', body, re.S)
            if not (date and pl and op):
                continue
            p1 = side(pl.group(1)); p2 = side(op.group(1))
            if not p1["name"] or not p2["name"]:
                continue
            if p1["doubles"] or p2["doubles"]:
                continue
            matches.append({
                "tournament": tour["name"], "tournament_level": tour["level"], "city": tour["city"],
                "tournament_url": tour["url"], "date": date.group(1),
                "round": (rtype.group(1).strip() if rtype else ""),
                "time_local": (re.sub(r"<[^>]+>", "", mtime.group(1)).strip() if mtime else ""),
                "player1": p1["name"], "player1_seed": p1["seed"], "player1_url": p1["url"],
                "player2": p2["name"], "player2_seed": p2["seed"], "player2_url": p2["url"],
                "source_url": tour["url"],
            })
            n += 1
        print(f"  {tid}: {n} singles matches parsed")
    out = {"schema": "olbg4/board-af-atp/v1", "capture": latest, "evidence": evidence, "matches": matches}
    os.makedirs(os.path.join(DATA, "parsed"), exist_ok=True)
    json.dump(out, open(os.path.join(DATA, "parsed", "atp.json"), "w"), indent=1)
    print(f"  total ATP singles matches: {len(matches)} -> data/session-80bc6293/parsed/atp.json")
    for m in matches[:6]:
        print(f"    {m['date']} {m['round']:<4} {m['tournament'][:14]:<15} {m['player1']} ({m['player1_seed']}) v {m['player2']} ({m['player2_seed']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
