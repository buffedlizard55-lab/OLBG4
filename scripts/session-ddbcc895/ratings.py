#!/usr/bin/env python3
"""Board AF — parse the official international rating tables from the capture.

Sources (all captured by .github/workflows/af-ddbcc895.yml):
  * ICC Men's ODI Team Rankings annual-update release (11 May 2026)
  * ICC Men's and Women's T20I Team Rankings annual-update release (5 May 2026)
  * IRL World Rankings (men)
"""
from __future__ import annotations

import html as H
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract import Capture, html_lines  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "session-ddbcc895" / "ratings.json"


def flat(cap: Capture, tid: str) -> str:
    return " | ".join(html_lines(cap.text(tid)))


def icc_table(cap: Capture, tid: str, marker: str, new_at: int) -> dict:
    """Read `Team | old | new | change | old rank | new rank | change` rows."""
    s = flat(cap, tid)
    needle = marker + " | Old rating | New rating | Change | Old ranking | New ranking | Change |"
    i = s.find(needle)
    if i < 0:
        # fall back to the first occurrence of the marker
        i = s.find(marker)
        if i < 0:
            return {}
        i += len(marker)
    else:
        i += len(needle)
    toks = [x.strip() for x in s[i:].split(" | ")]
    out, k = {}, 0
    while k + 6 < len(toks):
        team = toks[k]
        nums = toks[k + 1:k + 7]
        if (all(re.match(r"^[+\-]?\d+$", n) for n in nums)
                and re.match(r"^[A-Za-z][A-Za-z .'&\-]+$", team)
                and team.lower() not in ("old", "new", "change", "rating", "ranking")):
            if team in out:
                break  # the next table starts; keep the first (men's) values
            out[team] = {
                "team": team,
                "rating": int(nums[new_at]),
                "rank": int(nums[new_at + 3]),
                "source": cap.url(tid),
                "as_of": "2026-05-11" if "odi" in tid and "t20" not in tid else "2026-05-05",
            }
            k += 7
        else:
            k += 1
    return out


def irl(cap: Capture) -> dict:
    if not cap.has("irl_world_rankings"):
        return {}
    s = flat(cap, "irl_world_rankings")
    i = s.find("WOMEN | WHEELCHAIR")
    if i < 0:
        return {}
    toks = [x.strip() for x in s[i:].split(" | ")]
    out, k = {}, 0
    while k + 2 < len(toks):
        a = toks[k]
        if not re.match(r"^\d{1,2}$", a):
            k += 1
            continue
        # rank | [previous rank |] team | NN%
        j = k + 1
        while j < len(toks) and re.match(r"^\d{1,2}$", toks[j]):
            j += 1
        if j + 1 < len(toks) and re.match(r"^[A-Za-z][A-Za-z .'&\-]+$", toks[j]) and re.match(r"^\d{1,3}%$", toks[j + 1]):
            team = toks[j]
            if team in out:
                break
            out[team] = {
                "team": team, "rating": int(toks[j + 1].rstrip("%")), "rank": int(a),
                "source": cap.url("irl_world_rankings"), "as_of": "2026-10-22",
            }
            k = j + 2
        else:
            k += 1
    return out


def main() -> int:
    cap = Capture(Path(sys.argv[1]))
    data = {
        "schema": "olbg4.board-af.ratings/1",
        "capture": Path(sys.argv[1]).name,
        "icc_men_odi": icc_table(cap, "icc_release_odi", "Men's ODI - annual update 2026 - summary of movements", 1),
        "icc_men_t20i": icc_table(cap, "icc_release_t20i", "Men's T20I annual update:", 1),
        "icc_women_t20i": icc_table(cap, "icc_release_t20i", "Women's T20I annual update:", 1),
        "irl_men": irl(cap),
    }
    OUT.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print({k: len(v) for k, v in data.items() if isinstance(v, dict)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
