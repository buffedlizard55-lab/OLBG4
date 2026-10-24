"""Board CL (session arena/3bbe2449-olbg4): render session-3bbe2449/index.html from
data/session-3bbe2449/olbg_snapshot.json.

The JSON file is a hand-captured, timestamped read of OLBG's own sport hub pages for the
15 in-scope sports (see COORDINATION.md Board CL). This script only renders that JSON into
a static page; it does not fetch anything itself (this sandbox's outbound network does not
reach olbg.com from a plain script -- the capture was done through the session's page-fetch
tool and the extracted rows were written into the JSON by hand).

Usage: python3 scripts/session-3bbe2449/build_snapshot_page.py
"""
import json
import html
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_PATH = ROOT / "data/session-3bbe2449/olbg_snapshot.json"
OUT_PATH = ROOT / "session-3bbe2449/index.html"

STYLE = """
body{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;margin:0;background:#f6f7f9;color:#1b1f27;}
header{background:#0f3d5c;color:#fff;padding:18px 24px;}
header a{color:#fff;text-decoration:none;font-weight:600;}
header .sub{opacity:.85;font-size:14px;margin-top:4px;}
main{max-width:1080px;margin:0 auto;padding:24px;}
nav.crumbs{font-size:14px;margin-bottom:16px;}
nav.crumbs a{color:#0f3d5c;}
.card{background:#fff;border:1px solid #e2e5ea;border-radius:10px;padding:18px 20px;margin-bottom:18px;}
.badge{display:inline-block;background:#e6f0fa;color:#0f3d5c;border-radius:999px;padding:2px 10px;font-size:12px;font-weight:700;margin-left:8px;}
.badge.thin{background:#fdf3d8;color:#7a5b00;}
.badge.empty{background:#fde8e8;color:#8a1f1f;}
table{width:100%;border-collapse:collapse;font-size:14px;margin-top:10px;}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid #edf0f3;}
th{color:#555;font-weight:600;background:#fafbfc;}
tr:hover td{background:#fafcff;}
a.ext{color:#0b5fa5;text-decoration:none;}
a.ext:hover{text-decoration:underline;}
.note{font-size:13px;color:#555;background:#f3f6fa;border-left:3px solid #0f3d5c;padding:8px 12px;margin-top:10px;border-radius:4px;}
.foot{font-size:12px;color:#777;margin-top:28px;text-align:center;}
h1{margin:0;font-size:22px;}
h2{font-size:17px;margin:0 0 4px;}
"""


def render() -> str:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    rows = []
    for s in data["sports"]:
        status = s["status"]
        badge_cls = "badge"
        if "No live" in status or "Outrights only" in status:
            badge_cls = "badge empty"
        elif "thin" in status:
            badge_cls = "badge thin"
        sample_rows = "".join(
            f"<tr><td>{html.escape(m['event'])}</td><td>{html.escape(m['when'])}</td>"
            f"<td>{m['event_id']}</td><td><a class='ext' href=\"{html.escape(m['url'])}\" "
            f"target=\"_blank\" rel=\"noopener\">Open on OLBG &rarr;</a></td></tr>"
            for m in s["sample_matches"]
        )
        if not sample_rows:
            sample_rows = (
                "<tr><td colspan='4'><em>No events were listed on the hub's first page "
                "at capture time.</em></td></tr>"
            )
        note_html = f"<div class='note'>{html.escape(s['note'])}</div>" if s.get("note") else ""
        rows.append(f"""
        <div class="card">
          <h2>{html.escape(s['sport'])} <span class="{badge_cls}">{html.escape(status)}</span></h2>
          <div>OLBG hub: <a class="ext" href="{html.escape(s['olbg_hub_url'])}" target="_blank" rel="noopener">{html.escape(s['olbg_hub_url'])}</a> (sport id {s['sport_id']})</div>
          {note_html}
          <table>
            <thead><tr><th>Event</th><th>When (site-local)</th><th>OLBG event id</th><th>Where the pick is</th></tr></thead>
            <tbody>{sample_rows}</tbody>
          </table>
        </div>
        """)

    live_count = len([s for s in data["sports"] if s["sample_matches"]])
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>OLBG live snapshot (15-sport scope) · Board CL</title>
<style>{STYLE}</style></head><body>
<header>
  <div><a href="../index.html">&larr; OLBG4 dashboard</a></div>
  <h1>OLBG.com reverse-engineering: live 15-sport snapshot</h1>
  <div class="sub">Captured directly from olbg.com at {data['captured_utc']} &middot; Board CL &middot; session arena/3bbe2449-olbg4</div>
</header>
<main>
  <nav class="crumbs"><a href="../index.html">Dashboard</a> &rsaquo; OLBG live snapshot</nav>
  <div class="card">
    <h2>What this page is</h2>
    <p>This is a direct, timestamped read of OLBG's own sport hub pages for the exact 15 sports in scope for this project: Golf, Volleyball, Rugby Union, Cricket, Snooker, Darts, Baseball, Gaelic Sports, Greyhounds, Tennis, Motor Racing, Handball, Ice Hockey, Basketball and Rugby League. Each hub is <code>olbg.com/betting-tips/&lt;Sport&gt;/&lt;sport id&gt;</code>; the sport id is OLBG's own internal numbering and is stable across pages (e.g. event pages, tipster pages).</p>
    <p>Every "Where the pick is" link below goes straight to the live OLBG event page for that fixture &mdash; that is literally where OLBG's tipster picks for that match live. This answers the brief's question directly: the picks are on OLBG's own event pages, one per fixture, and the sport hub above is the index that lists them.</p>
    <p><strong>Method note:</strong> this snapshot is a first-page read of each hub (OLBG paginates with a "Load More Tips" control); it is meant to show the taxonomy and a true verification sample per sport, not a complete enumeration. For a fuller per-sport fixture list, see this repository's other session boards linked from the main dashboard, several of which paginated further.</p>
    <p>{live_count} of the 15 sports had at least one live match/event tip at capture time; the rest are flagged below with the exact reason observed on the page (for example Golf showed no tips at all, and Rugby League's near-term match calendar is out of season, leaving only 2027 ante-post markets).</p>
  </div>
  {''.join(rows)}
  <div class="foot">Data file: <a class="ext" href="../data/session-3bbe2449/olbg_snapshot.json">olbg_snapshot.json</a> &middot; Source: olbg.com (not an official governing-body source &mdash; used here only to document OLBG's own taxonomy and listings, per the brief) &middot; Part of Board CL, session arena/3bbe2449-olbg4.</div>
</main>
</body></html>
"""


if __name__ == "__main__":
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(render(), encoding="utf-8")
    print(f"wrote {OUT_PATH} ({OUT_PATH.stat().st_size} bytes)")
