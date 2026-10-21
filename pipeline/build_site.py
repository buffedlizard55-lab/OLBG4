"""Static site builder.

Writes plain HTML + CSS + JS to the repository root because GitHub Pages for this
repository is configured to serve `main` `/` (legacy build). No external assets, fonts
or CDNs are used, so the site works offline and behind restrictive networks.
"""
from __future__ import annotations

import json
import shutil
from collections import defaultdict
from pathlib import Path

from . import site_pages
from .site_common import SPORT_META


def build(payload: dict, out_dir: Path) -> list[str]:
    out_dir = Path(out_dir)
    static_dir = Path(__file__).resolve().parent / "static"
    assets = out_dir / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    for name in ("site.css", "site.js"):
        shutil.copyfile(static_dir / name, assets / name)

    rows = sorted(payload["analysis"], key=lambda r: (r["fixture"]["start_utc"], r["fixture"]["id"]))
    preds_by_fixture: dict[str, list[dict]] = defaultdict(list)
    for p in payload["predictions"]:
        if not p.get("withdrawn") and p.get("text"):
            preds_by_fixture[p["fixture_id"]].append(p)

    snapshot = dict(payload["snapshot"])
    snapshot["_flagged_count"] = payload["flagged"]
    ctx = {
        "payload": payload,
        "snapshot": snapshot,
        "rows": rows,
        "preds_by_fixture": preds_by_fixture,
        "models": payload.get("models") or {},
        "flagged": payload["flagged"],
        "taxonomy": payload.get("taxonomy"),
    }

    pages = {
        "index.html": site_pages.render_index(ctx),
        "matches.html": site_pages.render_matches(ctx),
        "picks.html": site_pages.render_picks(ctx),
        "analysis.html": site_pages.render_analysis(ctx),
        "markets.html": site_pages.render_markets(ctx),
        "sources.html": site_pages.render_sources(ctx),
        "flagged.html": site_pages.render_flagged(ctx),
        "methodology.html": site_pages.render_methodology(ctx),
        "olbg.html": site_pages.render_olbg(ctx),
    }
    for sport, meta in SPORT_META.items():
        pages[f"sport-{meta['slug']}.html"] = site_pages.render_sport(ctx, sport)

    for name, html in pages.items():
        (out_dir / name).write_text(html, encoding="utf-8")

    with open(assets / "data.json", "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, ensure_ascii=False)
        fh.write("\n")

    # GitHub Pages legacy build: skip Jekyll so files are served verbatim
    (out_dir / ".nojekyll").write_text("", encoding="utf-8")
    return sorted(pages)
