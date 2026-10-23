#!/usr/bin/env python3
"""Board ED shared library — capture IO, market maths and provenance helpers.

Everything here is deterministic: the same captured bytes always produce the same
desk. No network access, no random numbers, no hidden inputs.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "session-ed4c358c"
CAP = DATA / "capture"

SPORTS = [
    "Golf", "Volleyball", "Rugby Union", "Cricket", "Snooker", "Darts", "Baseball",
    "Gaelic Sports", "Greyhounds", "Tennis", "Motor Racing", "Handball", "Ice Hockey",
    "Basketball", "Rugby League",
]
SLUG = {s: s.lower().replace(" ", "-") for s in SPORTS}


# --------------------------------------------------------------------------- #
# capture IO
# --------------------------------------------------------------------------- #
class Capture:
    """Reads the newest committed capture stamp, verifying every SHA-256."""

    def __init__(self) -> None:
        stamps = sorted(p.parent for p in CAP.glob("*/manifest.json"))
        if not stamps:
            raise SystemExit("no capture found")
        self.stamp = stamps[-1]
        self.manifest = json.loads((self.stamp / "manifest.json").read_text())
        self.recs = {r["id"]: r for r in self.manifest["records"]}
        self._cache: dict[str, bytes] = {}

    def _raw(self, tid: str) -> bytes:
        rec = self.recs.get(tid)
        if not rec or not rec.get("file"):
            raise KeyError(tid)
        path = self.stamp / rec["file"]
        raw = path.read_bytes()
        body = gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw
        if hashlib.sha256(body).hexdigest() != rec["sha256"]:
            raise RuntimeError(f"SHA-256 mismatch for {tid}")
        return body

    def has(self, tid: str) -> bool:
        rec = self.recs.get(tid)
        return bool(rec and rec.get("status") == 200 and rec.get("file"))

    def text(self, tid: str) -> str:
        if tid not in self._cache:
            self._cache[tid] = self._raw(tid)
        return self._cache[tid].decode("utf-8", "replace")

    def json(self, tid: str):
        return json.loads(self.text(tid))

    def url(self, tid: str) -> str:
        return self.recs[tid]["url"]

    def sha(self, tid: str) -> str:
        return self.recs[tid]["sha256"]


# --------------------------------------------------------------------------- #
# numbers
# --------------------------------------------------------------------------- #
def american_from_decimal(dec: float) -> int:
    if dec >= 2.0:
        return int(round((dec - 1.0) * 100.0))
    return int(round(-100.0 / (dec - 1.0)))


def decimal_from_prob(p: float) -> float:
    p = min(0.999, max(0.001, p))
    return round(1.0 / p, 3)


def american_from_prob(p: float) -> int:
    return american_from_decimal(decimal_from_prob(p))


def poisson_pmf(lam: float, k: int) -> float:
    return math.exp(-lam) * lam ** k / math.factorial(k)


def poisson_matrix(lh: float, la: float, n: int = 25):
    ph = [poisson_pmf(lh, i) for i in range(n)]
    pa = [poisson_pmf(la, i) for i in range(n)]
    return [[ph[i] * pa[j] for j in range(n)] for i in range(n)]


def norm_cdf(x: float, mu: float = 0.0, sigma: float = 1.0) -> float:
    return 0.5 * (1.0 + math.erf((x - mu) / (sigma * math.sqrt(2.0))))


def shrink(rate: float, games: float, prior: float = 1.0, k: float = 12.0) -> float:
    """Sample-size shrinkage towards a neutral 1.0 rating (documented in METHODOLOGY)."""
    if games <= 0:
        return 1.0
    w = games / (games + k)
    return w * rate + (1 - w) * prior


def logistic(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


_BUILD_STAMP: str | None = None


def iso_now() -> str:
    """Build timestamp pinned to the capture, so a rebuild is byte-identical."""
    global _BUILD_STAMP
    if _BUILD_STAMP is None:
        stamps = sorted(p.parent for p in CAP.glob("*/manifest.json"))
        if stamps:
            m = json.loads((stamps[-1] / "manifest.json").read_text())
            finished = m.get("finished_utc", "")
            _BUILD_STAMP = finished[:19].replace("T", "T") + "Z" if finished else "1970-01-01T00:00:00Z"
        else:
            _BUILD_STAMP = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return _BUILD_STAMP


# --------------------------------------------------------------------------- #
# markets
# --------------------------------------------------------------------------- #
def two_way(label_a: str, p_a: float, label_b: str, p_b: float) -> dict:
    """Fair (margin-free) two-way market, probabilities normalised to sum to 1."""
    tot = p_a + p_b
    pa, pb = p_a / tot, p_b / tot
    return {
        "type": "2way",
        "selections": [
            {"label": label_a, "fair_prob": round(pa, 4),
             "fair_decimal": decimal_from_prob(pa), "fair_american": american_from_prob(pa)},
            {"label": label_b, "fair_prob": round(pb, 4),
             "fair_decimal": decimal_from_prob(pb), "fair_american": american_from_prob(pb)},
        ],
        "prob_sum": round(pa + pb, 4),
    }


def three_way(labels: list[str], probs: list[float]) -> dict:
    tot = sum(probs)
    sel = []
    for lab, p in zip(labels, probs):
        q = p / tot
        sel.append({"label": lab, "fair_prob": round(q, 4),
                    "fair_decimal": decimal_from_prob(q), "fair_american": american_from_prob(q)})
    return {"type": "3way", "selections": sel, "prob_sum": round(sum(s["fair_prob"] for s in sel), 4)}


def confidence_for(p: float, caps: list[str] | None = None) -> str:
    """High >= 0.70, Medium 0.58-0.70, Low < 0.58; sample caps force Medium at best."""
    band = "High" if p >= 0.70 else ("Medium" if p >= 0.58 else "Low")
    if caps and band == "High":
        band = "Medium"
    return band


def pick_from_markets(markets: dict, preferred: list[str] | None = None) -> dict:
    """Choose the strongest selection, preferring the 0.700-0.7143 window when it exists.

    The brief asks for High-confidence picks inside -250..+10,000 American. A 70.0%
    chance prices at -233 and 71.43% at -250, so that intersection is p in
    [0.700, 0.7143]; when a selection sits in it we surface that selection first.
    """
    best = None
    for mkey, m in markets.items():
        for s in m["selections"]:
            p = s["fair_prob"]
            if s["label"] == "Draw":
                continue
            # rank: in-window first, then closest to the 70.7% window centre, then probability
            key = (0 if 0.700 <= p <= 0.7143 else 1, abs(p - 0.7071), -p)
            if best is None or key < best[0]:
                best = (key, mkey, m["market_name"], s)
    _, mkey, mname, s = best
    return {
        "market": mkey,
        "market_name": mname,
        "selection": s["label"],
        "fair_prob": s["fair_prob"],
        "fair_decimal": s["fair_decimal"],
        "fair_american": s["fair_american"],
        "in_window": 0.700 <= s["fair_prob"] <= 0.7143,
    }


def clean_line(x: float) -> float:
    return round(x * 2) / 2
