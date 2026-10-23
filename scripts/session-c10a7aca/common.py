#!/usr/bin/env python3
"""Board C10 evidence access, OLBG SSR extraction and reconciliation primitives.

The builder never fetches the network.  Every input is read from a committed,
SHA-256-manifested capture.  A later capture of the same target supersedes an
earlier one only when it returned HTTP 200 with non-empty bytes.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import gzip
import hashlib
import html as html_lib
import json
import math
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "session-c10a7aca"
CAPTURES = DATA / "capture"
OUT = ROOT / "session-c10a7aca"
SPORTS = [
    "Golf", "Volleyball", "Rugby Union", "Cricket", "Snooker", "Darts",
    "Baseball", "Gaelic Sports", "Greyhounds", "Tennis", "Motor Racing",
    "Handball", "Ice Hockey", "Basketball", "Rugby League",
]
HUB_SPORTS = {
    "olbg_tennis_3": "Tennis", "olbg_basketball_4": "Basketball",
    "olbg_basketball_nba": "Basketball", "olbg_basketball_euroleague": "Basketball",
    "olbg_basketball_other": "Basketball", "olbg_golf_5": "Golf",
    "olbg_cricket_7": "Cricket", "olbg_snooker_8": "Snooker",
    "olbg_rugby_union_9": "Rugby Union", "olbg_rugby_league_10": "Rugby League",
    "olbg_baseball_12": "Baseball", "olbg_ice_hockey_13": "Ice Hockey",
    "olbg_ice_hockey_nhl": "Ice Hockey", "olbg_ice_hockey_other": "Ice Hockey",
    "olbg_motor_racing_14": "Motor Racing", "olbg_darts_15": "Darts",
    "olbg_handball_20": "Handball", "olbg_volleyball_21": "Volleyball",
    "olbg_gaelic_25": "Gaelic Sports", "olbg_greyhounds_28": "Greyhounds",
}


def utc(value: str) -> datetime:
    """Parse the timestamp variants used by official feeds as aware UTC."""
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", text):
        text = text.replace(" ", "T") + "+00:00"
    dt = datetime.fromisoformat(text)
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def norm(value: str) -> str:
    """Conservative display-name normalisation; no aggressive suffix deletion."""
    value = html_lib.unescape(value or "")
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    value = value.lower().replace("&", " and ")
    value = re.sub(r"\b(nottm)\b", "nottingham", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def words(value: str) -> list[str]:
    return re.findall(r"[^\W_]+", value or "", flags=re.UNICODE)


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", html_lib.unescape(re.sub(r"<[^>]+>", " ", value or ""))).strip()


def american(probability: float) -> int | None:
    if not 0 < probability < 1:
        return None
    return round(-100 * probability / (1 - probability)) if probability >= 0.5 else round(100 * (1 - probability) / probability)


def decimal(probability: float) -> float | None:
    return round(1 / probability, 3) if 0 < probability < 1 else None


def odds_american(text: str | None) -> int | None:
    if text is None:
        return None
    text = str(text).strip().replace("−", "-")
    return int(text) if re.fullmatch(r"[+-]?\d+", text) else None


def logistic(x: float) -> float:
    return 1 / (1 + math.exp(-max(-30, min(30, x))))


def normal_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def balanced_objects(text: str, key: str) -> list[str]:
    """Extract complete objects from a JavaScript/JSON array without eval.

    OLBG's Nuxt payload uses unquoted keys and nested objects.  Bracket and
    brace depth plus string-escape tracking prevents truncated tip objects.
    """
    out: list[str] = []
    pattern = re.compile(rf'(?:\b{re.escape(key)}|"{re.escape(key)}")\s*:\s*\[')
    for match in pattern.finditer(text):
        i = match.end()
        depth = 1
        obj_start = None
        quoted = False
        escaped = False
        while i < len(text) and depth > 0:
            ch = text[i]
            if quoted:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    quoted = False
            elif ch == '"':
                quoted = True
            elif ch == "{":
                if depth == 1:
                    obj_start = i
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 1 and obj_start is not None:
                    out.append(text[obj_start:i + 1])
                    obj_start = None
            elif ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
            i += 1
    return out


def prop(blob: str, key: str, default=None):
    value = r'(?:null|true|false|-?\d+(?:\.\d+)?|"(?:\\.|[^"\\])*")'
    match = re.search(rf'(?:\b{re.escape(key)}|"{re.escape(key)}")\s*:\s*{value}', blob)
    if not match:
        return default
    raw = match.group(0).split(":", 1)[1].strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default


@dataclass
class Evidence:
    target: str
    url: str
    body: bytes
    sha256: str
    captured_utc: str
    file: str
    status: int

    def text(self) -> str:
        return self.body.decode("utf-8", "replace")

    def json(self):
        return json.loads(self.body)

    def citation(self) -> dict:
        return {
            "target": self.target, "url": self.url, "sha256": self.sha256,
            "captured_utc": self.captured_utc, "evidence_file": self.file,
        }


class EvidenceStore:
    def __init__(self) -> None:
        self.manifests: list[dict] = []
        self.records: dict[str, dict] = {}
        self.attempts: list[dict] = []
        for path in sorted(CAPTURES.glob("*/manifest.json")):
            manifest = json.loads(path.read_text())
            manifest["_directory"] = path.parent
            self.manifests.append(manifest)
            for item in manifest["items"]:
                attempt = dict(item)
                attempt["capture"] = path.parent.name
                self.attempts.append(attempt)
                if item.get("status") == 200 and item.get("bytes", 0) > 0:
                    self.records[item["id"]] = attempt
        if not self.manifests:
            raise RuntimeError("No C10 evidence captures found")
        self.cutoff = max(utc(m["generated_utc"]) for m in self.manifests)

    def get(self, target: str, required: bool = False) -> Evidence | None:
        item = self.records.get(target)
        if not item:
            if required:
                raise KeyError(f"No usable captured evidence for {target}")
            return None
        path = CAPTURES / item["capture"] / item["file"]
        body = gzip.decompress(path.read_bytes())
        digest = hashlib.sha256(body).hexdigest()
        if digest != item["sha256"] or len(body) != item["bytes"]:
            raise ValueError(f"Evidence hash/size mismatch: {target}")
        return Evidence(target, item["url"], body, digest, item["fetched_utc"],
                        str(path.relative_to(ROOT)), item["status"])

    def citations(self, targets: list[str]) -> list[dict]:
        return [self.get(t).citation() for t in dict.fromkeys(targets) if self.get(t)]

    def inventory(self) -> list[dict]:
        latest: dict[str, dict] = {}
        for attempt in self.attempts:
            latest[attempt["id"]] = attempt
        return [latest[key] for key in sorted(latest)]


def olbg_events(store: EvidenceStore) -> tuple[list[dict], dict]:
    """Deduplicate by OLBG event ID, retaining every captured in-scope hub."""
    events: dict[str, dict] = {}
    audit = {"raw_objects": 0, "without_event_id": 0, "duplicates": 0,
             "expired_or_started": 0, "hub_counts": {}, "coverage_limit": (
                 "Captured server-rendered OLBG hub objects only. Hidden Load More "
                 "content and disallowed API routes were not accessed; this is not "
                 "represented as an exhaustive event-market inventory.")}
    for target, sport in HUB_SPORTS.items():
        evidence = store.get(target)
        if not evidence:
            audit["hub_counts"][target] = 0
            continue
        count = 0
        for kind in ("tips", "tournaments"):
            for blob in balanced_objects(evidence.text(), kind):
                audit["raw_objects"] += 1
                event_url = prop(blob, "eventUrl", "") or ""
                match = re.search(r"event_id=(\d+)", event_url)
                if not match:
                    audit["without_event_id"] += 1
                    continue
                event_id = match.group(1)
                name = prop(blob, "event_name_alias", "") or ""
                if not name:
                    continue
                if event_id in events:
                    events[event_id]["on_olbg"] = True
                    events[event_id]["olbg_hubs"].append({"target": target, "url": evidence.url,
                                                           "captured_utc": evidence.captured_utc})
                    audit["duplicates"] += 1
                    continue
                timestamp = prop(blob, "event_start_unix_timestamp")
                started = prop(blob, "expired", False)
                start = datetime.fromtimestamp(timestamp, timezone.utc) if isinstance(timestamp, int) else None
                if started is True or (start and start <= store.cutoff):
                    audit["expired_or_started"] += 1
                    continue
                events[event_id] = {
                    "event_id": event_id, "sport": sport, "kind": "outright" if kind == "tournaments" else "match",
                    "event": name, "start_utc": iso(start) if start else None,
                    "start_unverified": start is None,
                    "olbg_url": event_url if event_url.startswith("http") else "https://www.olbg.com" + event_url,
                    "olbg_hubs": [{"target": target, "url": evidence.url,
                                   "captured_utc": evidence.captured_utc}],
                    "olbg_tip": prop(blob, "selection", "") or "",
                    "olbg_market": prop(blob, "market_alias", "") or "",
                    "olbg_american": odds_american(prop(blob, "american_odds")),
                    "olbg_decimal": prop(blob, "odds_decimal"),
                    "olbg_tips": prop(blob, "win_tips"),
                    "olbg_tipsters": prop(blob, "win_tips_count"),
                    "olbg_confidence": prop(blob, "confidence"),
                    "on_olbg": True, "official": False, "verification": "OLBG only — official reconciliation unresolved",
                    "flags": ["No two-sided official fixture/statistical match established yet."],
                }
                count += 1
        audit["hub_counts"][target] = count
    result = sorted(events.values(), key=lambda e: (SPORTS.index(e["sport"]), e["start_utc"] or "9999", e["event_id"]))
    audit["unique_upcoming_or_undated"] = len(result)
    return result, audit


def split_olbg_sides(event: dict) -> tuple[str, str] | None:
    name = event["event"]
    if " @ " in name:
        away, home = name.split(" @ ", 1)
        return away.strip(), home.strip()
    separator = " vs " if " vs " in name else " v " if " v " in name else None
    if separator:
        home, away = name.split(separator, 1)
        # Cricket names can append a match descriptor after the away side.
        away = re.sub(r"\s+(?:One Day Match|2nd T20 Match|T20)$", "", away, flags=re.I)
        return home.strip(), away.strip()
    return None


def alias_variants(name: str, abbreviations: list[str] | None = None,
                   common: str | None = None) -> set[str]:
    aliases = {norm(name)}
    if common:
        aliases.add(norm(common))
    for abbr in abbreviations or []:
        if abbr:
            aliases.add(norm(abbr))
        if common and abbr:
            aliases.add(norm(f"{abbr} {common}"))
    return {a for a in aliases if a}


def side_score(side: str, aliases: set[str], common: str | None = None) -> float:
    n = norm(side)
    if n in aliases:
        return 1.0
    # Official abbreviations and city prefixes vary; a unique full nickname is
    # safe, while arbitrary one-word/subset matches are not.
    c = norm(common or "")
    if len(c) >= 5 and (n.endswith(" " + c) or n == c):
        return 0.92
    return 0.0


def reconcile(events: list[dict], official: list[dict], source_label: str,
              min_score: float = 0.90) -> None:
    """Attach official fixtures only on unambiguous two-sided alias matches."""
    used: set[str] = set()
    for event in events:
        if event["official"] or event["kind"] != "match":
            continue
        sides = split_olbg_sides(event)
        if not sides:
            continue
        candidates = []
        for fixture in official:
            if fixture["official_id"] in used or fixture["sport"] != event["sport"]:
                continue
            if event["start_utc"] and fixture.get("start_utc"):
                delta = abs((utc(event["start_utc"]) - utc(fixture["start_utc"])).total_seconds())
                # OLBG occasionally rounds to five minutes; larger discrepancies
                # remain visible rather than being accepted by names alone.
                if delta > 8 * 3600:
                    continue
            else:
                delta = 0
            scores = []
            for side, key in zip(sides, ("side1", "side2")):
                f = fixture[key]
                scores.append(side_score(side, f["aliases"], f.get("common")))
            # Also test reversed order only when official home/away orientation
            # differs; orientation is retained in the attached fixture.
            reverse = []
            for side, key in zip(sides, ("side2", "side1")):
                f = fixture[key]
                reverse.append(side_score(side, f["aliases"], f.get("common")))
            orientation = "same" if min(scores) >= min(reverse) else "reverse"
            use = scores if orientation == "same" else reverse
            if min(use) >= min_score:
                candidates.append((sum(use), -delta, fixture, orientation, use))
        if len(candidates) == 1 or (len(candidates) > 1 and sorted(candidates, reverse=True, key=lambda c: c[0])[0][0] > sorted(candidates, reverse=True, key=lambda c: c[0])[1][0]):
            _, _, fixture, orientation, scores = max(candidates, key=lambda c: (c[0], c[1]))
            used.add(fixture["official_id"])
            event.update({
                "official": True, "official_id": fixture["official_id"],
                "official_url": fixture["official_url"], "official_start_utc": fixture["start_utc"],
                "official_side1": fixture["side1"]["name"], "official_side2": fixture["side2"]["name"],
                "official_orientation": orientation, "official_match_score": round(min(scores), 3),
                "official_source_label": source_label,
                "competition": fixture.get("competition", ""),
                "official_evidence": fixture.get("evidence", []),
                "official_stats": fixture.get("stats"),
                "official_detail": fixture.get("detail", {}),
                "verification": "Official fixture and captured two-sided evidence reconciled",
            })
            event["flags"] = []
            if event["start_utc"] and fixture.get("start_utc"):
                delta = abs((utc(event["start_utc"]) - utc(fixture["start_utc"])).total_seconds())
                if delta > 900:
                    if (fixture.get("detail") or {}).get("start_timezone_unverified"):
                        event["flags"].append(f"OLBG and official clock values differ by {round(delta / 60)} minutes; UTC is left blank pending timezone confirmation.")
                    else:
                        event["flags"].append(f"OLBG/official start differs by {round(delta / 60)} minutes; official time controls.")
                    event["verification"] = "Official fixture matched; start-time discrepancy flagged"
        elif len(candidates) > 1:
            event["flags"].append(f"Ambiguous official reconciliation: {len(candidates)} candidates retained for review.")


def add_official_only(events: list[dict], fixtures: list[dict], cutoff: datetime,
                      horizon_days: int = 7) -> int:
    """Add unlisted official fixtures inside the declared publication window."""
    matched = {e.get("official_id") for e in events if e.get("official_id")}
    horizon = cutoff.timestamp() + horizon_days * 86400
    added = 0
    for f in fixtures:
        if f["official_id"] in matched or not f.get("start_utc"):
            continue
        start = utc(f["start_utc"])
        if start <= cutoff or start.timestamp() > horizon:
            continue
        events.append({
            "event_id": "official:" + f["official_id"], "sport": f["sport"], "kind": "match",
            "event": f"{f['side1']['name']} v {f['side2']['name']}", "start_utc": f["start_utc"],
            "start_unverified": False, "on_olbg": False, "olbg_url": "", "olbg_hubs": [],
            "olbg_tip": "", "olbg_market": "", "olbg_american": None, "olbg_decimal": None,
            "official": True, "official_id": f["official_id"], "official_url": f["official_url"],
            "official_start_utc": f["start_utc"], "official_side1": f["side1"]["name"],
            "official_side2": f["side2"]["name"], "official_orientation": "same",
            "official_match_score": 1.0, "official_source_label": "Official competition schedule",
            "official_evidence": f.get("evidence", []), "official_stats": f.get("stats"),
            "official_detail": f.get("detail", {}), "competition": f.get("competition", ""),
            "verification": "Official upcoming fixture; not listed on captured OLBG hubs",
            "coverage_note": "Official-only addition inside the seven-day publication window.",
            "flags": [],
        })
        matched.add(f["official_id"])
        added += 1
    events.sort(key=lambda e: (SPORTS.index(e["sport"]), e.get("start_utc") or "9999", str(e["event_id"])))
    return added


def fixture(official_id: str, sport: str, competition: str, start: str, url: str,
            side1: dict, side2: dict, evidence: list[dict], detail: dict | None = None,
            stats: dict | None = None) -> dict:
    return {"official_id": official_id, "sport": sport, "competition": competition,
            "start_utc": start, "official_url": url, "side1": side1, "side2": side2,
            "evidence": evidence, "detail": detail or {}, "stats": stats or {}}


def team_side(name: str, abbreviations: list[str], common: str, **stats) -> dict:
    return {"name": name, "common": common, "aliases": sorted(alias_variants(name, abbreviations, common)),
            **stats}
