"""Repository-wide structural audit. Never equates a URL with factual verification.

Run: python scripts/audit_publication.py [--check]
--check fails on broken local targets or stale audit artifacts. External URLs are
listed for manual review, not requested or asserted reachable by this offline tool.
"""
from __future__ import annotations

import argparse
import html
import json
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'audit'
# Domain classification only; this list is not evidence of any row's accuracy.
DOMAINS = ('nba.com', 'nhl.com', 'nhle.com', 'mlb.com', 'atptour.com',
           'wtatennis.com', 'icc-cricket.com', 'nzc.nz', 'pdc.tv', 'wst.tv',
           'unitedrugby.com', 'premiershiprugby.com', 'nrl.com', 'eurohandball.com',
           'volleyballworld.com', 'europeantour.com', 'formula1.com', 'gbgb.org.uk',
           'galwaygaa.ie', 'gaacork.ie')


def load(name):
    return json.loads((ROOT / name).read_text())


def official_candidate(url):
    p = urlsplit(url)
    host = p.hostname or ''
    return p.scheme == 'https' and not p.username and any(
        host == d or host.endswith('.' + d) for d in DOMAINS)


def urls_in(value):
    if isinstance(value, str):
        return [value] if value.startswith(('http://', 'https://')) else []
    if isinstance(value, dict):
        return [u for v in value.values() for u in urls_in(v)]
    if isinstance(value, list):
        return [u for v in value for u in urls_in(v)]
    return []


def rows():
    sources = {s['id']: s['url'] for s in load('data/session-74f9613e/sources.json')['sources']}
    datasets = [
        ('D hub', 'data/matches.json', load('data/matches.json')),
        ('A archive', 'data/rows.json', load('data/rows.json')),
        ('B consensus', 'data/board.json', load('data/board.json')['rows']),
        ('C model', 'data/session-74f9613e/matches.json', load('data/session-74f9613e/matches.json')['matches']),
        ('E feed', 'session-4afef1af/data/fixtures.json', load('session-4afef1af/data/fixtures.json')),
    ]
    out = []
    for build, path, items in datasets:
        for i, r in enumerate(items, 1):
            links = urls_in(r)
            if build == 'C model':
                links += [sources[s] for s in r.get('fixture_sources', []) + r.get('input_sources', []) if s in sources]
            links = sorted(set(links))
            candidates = [u for u in links if official_candidate(u)]
            def team(side):
                t = r.get(side, '')
                return t.get('name', '') if isinstance(t, dict) else t
            match = r.get('match') or f"{team('away')} at {team('home')}"
            issues = ['Facts not independently reverified in this audit; historical verified labels are not adopted.']
            if not candidates:
                issues.append('No recognized official-source URL on this row; official source left blank.')
            if build == 'B consensus':
                issues.append('Prices depend on OLBG tip consensus; not independent team-strength origination. Handicap/total use assumptions.')
            date = r.get('date') or r.get('start_utc') or ''
            if date and date[:10] < '2026-10-21':
                issues.append('Dated before audit day; do not present as an upcoming match without refreshing status.')
            if 'gaelic' in str(r.get('sport', '')).lower():
                issues.append('Scope ambiguity: football excluded by brief; no user confirmation of Gaelic exception located.')
            out.append(dict(build=build, file=path, row=i, id=r.get('id', ''), match=match,
                            sport=r.get('sport', ''), date=date, official_source_candidates=candidates,
                            other_sources=[u for u in links if u not in candidates],
                            verified_values={}, status='unverified', findings=issues))
    return out


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
    def handle_starttag(self, tag, attrs):
        for k, v in attrs:
            if v and ((k == 'href' and tag in ('a', 'link')) or (k == 'src' and tag in ('script', 'img', 'iframe'))):
                self.links.append(v)


def local_links():
    """Check every local file target referenced by a published HTML page.

    Capture desks store raw response bytes gzip-compressed and keep the response's own
    file extension, so a compressed official HTML response lands on disk as `*.html`.
    Those files are data, not pages: they have no outbound links and are not valid UTF-8.
    They are reported as skipped rather than crashing the repo-wide gate (see AJ-F01 in
    COORDINATION.md). No link is ignored and no page is excluded from the check.
    """
    broken, count, skipped = [], 0, []
    for page in sorted(ROOT.rglob('*.html')):
        if any(p in ('.git', 'node_modules', '.venv') for p in page.relative_to(ROOT).parts):
            continue
        raw = page.read_bytes()
        if raw[:2] == b'\x1f\x8b':
            skipped.append({'file': str(page.relative_to(ROOT)),
                            'reason': 'gzip-compressed captured response, not an HTML page'})
            continue
        try:
            text = raw.decode('utf-8')
        except UnicodeDecodeError:
            skipped.append({'file': str(page.relative_to(ROOT)),
                            'reason': 'not UTF-8 decodable; binary artefact, not an HTML page'})
            continue
        parser = Links()
        parser.feed(text)
        for url in parser.links:
            parsed = urlsplit(url)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            path = unquote(parsed.path)
            if path.startswith('/OLBG4/'):
                target = ROOT / path[len('/OLBG4/'):]
            elif path.startswith('/'):
                target = ROOT / path.lstrip('/')
            else:
                target = page.parent / path
            target = target.resolve()
            if target.is_dir():
                target /= 'index.html'
            count += 1
            if not target.is_relative_to(ROOT) or not target.is_file():
                broken.append(dict(page=str(page.relative_to(ROOT)), url=url))
    return count, broken, skipped


def render(report):
    e = lambda x: html.escape(str(x), quote=True)
    def links(values):
        return '<br>'.join(f'<a href="{e(u)}">{e(urlsplit(u).hostname)}</a>' for u in values)
    body = []
    for row in report['rows']:
        body.append('<tr>' + ''.join(f'<td>{v}</td>' for v in [
            e(row['build']), e(f"{row['file']} row {row['row']}"), e(row['sport']),
            e(row['match']), e(row['date']), 'UNVERIFIED',
            links(row['official_source_candidates']), links(row['other_sources']),
            '<ul>' + ''.join(f'<li>{e(s)}</li>' for s in row['findings']) + '</ul>'
        ]) + '</tr>')
    return '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Flagged for Review — repository-wide audit</title><style>
body{font:16px/1.55 system-ui;background:#f4f7fb;color:#17263c;margin:0;padding:24px}main{max-width:1500px;margin:auto}a{color:#0758a3}h1{margin-bottom:4px}.notice{padding:20px;background:#fff1d6;border-left:5px solid #b56600;margin:20px 0}.scroll{overflow:auto;background:white}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:12px;border:1px solid #dce2eb;text-align:left;vertical-align:top}th{background:#17263c;color:white}input{padding:12px;width:min(90%,600px);margin:14px 0}td:nth-child(2){overflow-wrap:anywhere;min-width:160px}td:last-child{min-width:290px}
</style><main><a href="../index.html">← Dashboard</a><h1>Flagged for Review</h1>
<p>Repository-wide publication audit · baseline 21 October 2026 · <a href="report.json">Machine-readable report</a></p>
<div class="notice"><strong>No complete official factual verification is claimed.</strong> This inventory preserves every existing row for review, but publishes no newly verified match values, prices or predictions. An official-domain URL is a review candidate, not proof of its contents. Unconfirmed values are blank in <code>verified_values</code>. Existing dashboards retain historical claims and should not be treated as a fully verified current betting list.</div>
<h2>Findings and limitations</h2><ul>
<li>Five overlapping snapshots are not one deduplicated, complete list of every match or market. Their row counts must not be added as unique fixtures.</li>
<li>Build B prices use OLBG tip consensus and assumed scoring constants, which do not satisfy independent, official-input-only line origination.</li>
<li>Model probabilities and confidence labels are estimates, never officially verified facts or assurances of winning. No new picks or prose are generated by this audit.</li>
<li>Scheduled refresh covers only NBA, NHL and MLB. Other sports remain historical snapshots. No market feed proves that every available betting market was investigated.</li>
<li>The official NBA schedule release was reopened: the October 20 opening fixtures are supported, but that page does not establish every numerical form claim in the hub write-ups. <a href="https://www.nba.com/news/2026-27-nba-regular-season-schedule">Official release</a>.</li>
<li>Source classification is a conservative domain allowlist, not a network check. Unknown domains need review, not a conclusion that they are unofficial.</li>
<li>The local-link check checks file targets only, not external URL availability, JavaScript requests or fragment anchors.</li>
</ul><p>''' + e(len(report['rows'])) + ' source rows inventoried. Build counts: ' + e(report['build_counts']) + '''.</p>
<label for="search">Filter by build, sport, match or finding</label><br><input id="search" type="search" placeholder="Search review rows…"><p id="count" aria-live="polite"></p>
<div class="scroll"><table><thead><tr>''' + ''.join('<th scope="col">' + x + '</th>' for x in ['Build','Location','Sport','Match label (historical)','Historical date','Audit status','Official-source candidates','Other sources','Findings']) + '''</tr></thead><tbody>''' + ''.join(body) + '''</tbody></table></div>
<script>const rows=[...document.querySelectorAll('tbody tr')];const input=document.querySelector('#search');function filter(){let n=0;for(const r of rows){r.hidden=!r.textContent.toLowerCase().includes(input.value.toLowerCase());if(!r.hidden)n++}document.querySelector('#count').textContent=n+' rows shown'}input.addEventListener('input',filter);filter();</script></main></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    entries = rows()
    # Audit page itself contains no unique local targets beyond existing homepage/report.
    report = dict(schema='olbg4.publication-audit/1', baseline_date='2026-10-21',
                  factual_verification='not performed; all rows unverified',
                  build_counts=dict(Counter(r['build'] for r in entries)), rows=entries)
    artifacts = {'report.json': json.dumps(report, indent=2, ensure_ascii=False) + '\n',
                 'index.html': render(report)}
    OUTPUT.mkdir(exist_ok=True)
    stale = []
    for name, text in artifacts.items():
        path = OUTPUT / name
        if args.check:
            if not path.exists() or path.read_text() != text:
                stale.append(name)
        else:
            path.write_text(text)
    count, broken, skipped = local_links()
    print(json.dumps(dict(rows=len(entries), build_counts=report['build_counts'],
                          local_targets_checked=count, broken=broken, stale=stale,
                          skipped_non_html=len(skipped), skipped=skipped), indent=2))
    return int(bool(broken or stale))


if __name__ == '__main__':
    raise SystemExit(main())
