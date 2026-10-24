#!/usr/bin/env python3
"""Attach the hand-written previews in authored.json to their desk rows.

    python3 scripts/session-e0ca04cf/predictions.py

Writes data/session-e0ca04cf/predictions.json = {row_id: {text, words, selection,
market, decimal, inputs, source_url}}.  Refuses to publish a preview that is
shorter than the brief's 30 words, repeats another preview, or names a selection
that is not the row's pick.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent.parent / "data" / "session-e0ca04cf"
BANNED = ("model", "verified")


def norm(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def similarity(a: str, b: str) -> float:
    A, B = set(norm(a).split()), set(norm(b).split())
    return len(A & B) / max(1, len(A | B))


def main() -> int:
    desk = json.loads((DATA / "desk.json").read_text())
    authored = json.loads((DATA / "authored.json").read_text())
    rows = {r["id"]: r for r in desk["rows"]}
    out, problems = {}, []
    seen: list[tuple[str, str]] = []
    for rid, item in authored.items():
        if rid.startswith("_"):
            continue
        row = rows.get(rid)
        if not row:
            problems.append(f"{rid}: no such row in the desk")
            continue
        pick = row.get("pick")
        if not pick:
            problems.append(f"{rid}: row has no pick")
            continue
        text = item["text"].strip()
        words = len(text.split())
        if words < 30:
            problems.append(f"{rid}: only {words} words")
            continue
        low = text.lower()
        bad = [w for w in BANNED if re.search(rf"\b{w}\b", low)]
        if bad:
            problems.append(f"{rid}: contains banned wording {bad}")
            continue
        if pick["selection"].lower() not in low:
            problems.append(f"{rid}: preview never names the selection ({pick['selection']})")
            continue
        for other, otext in seen:
            s = similarity(text, otext)
            if s > 0.55:
                problems.append(f"{rid}: {s:.2f} overlap with {other}")
        seen.append((rid, text))
        out[rid] = {
            "text": text,
            "words": words,
            "selection": pick["selection"],
            "market": pick["market"],
            "decimal": pick["decimal"],
            "american": pick["american"],
            "confidence": pick["confidence"],
            "inputs": {k: v for k, v in row["inputs"].items()
                       if not isinstance(v, (dict, list))},
            "source_url": row["source_url"],
            "source_name": row["source_name"],
        }
    (DATA / "predictions.json").write_text(json.dumps(out, indent=1) + "\n")
    print(f"{len(out)} predictions written")
    for p in problems:
        print("  PROBLEM", p)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
