"""Read-only review of published master and session desk datasets. No sports facts inferred."""
import hashlib, html, json, re
from pathlib import Path
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'session-7bbc825b'; DATA=ROOT/'data/session-7bbc825b'
def esc(x): return html.escape(str(x),quote=True)
def slug(x): return re.sub('[^a-z0-9]+','-',x.lower()).strip('-') or 'unknown'
rows=[]; inventory=[]
paths=sorted(set([ROOT/'data/master.json',*ROOT.glob('data/session-*/desk.json')]))
for p in paths:
    raw=p.read_bytes(); d=json.loads(raw); records=d.get('rows',[])
    inventory.append({'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(raw).hexdigest(),'rows':len(records)})
    for i,r in enumerate(records):
        if not isinstance(r,dict): continue
        url=r.get('official_url') or r.get('source_url') or ''
        if not isinstance(url,str) or urlparse(url).scheme not in ('https','http'): url=''
        rows.append({'audit_id':f'{len(rows)+1:05}', 'file':str(p.relative_to(ROOT)), 'pointer':f'/rows/{i}',
          'legacy_id':r.get('id',''), 'category_as_recorded':r.get('sport','Unknown'),
          'legacy_verification_claim':r.get('verification',r.get('verified','')),
          'recorded_source_url':url,'verified_match':'','verified_start_utc':'','winner_pick':'',
          'confidence':'','originated_lines':'','prediction':'', 'status':'unverified',
          'reason':'Not independently revalidated in this session. A recorded URL or legacy verified label is not field-level evidence.'})
DATA.mkdir(exist_ok=True);OUT.mkdir(exist_ok=True)
report={'review_date':'2026-10-22','scope':'data/master.json and data/session-*/desk.json /rows only; not a repo-wide factual audit',
 'live_probes':[{'url':'https://www.olbg.com/','result':'curl exit 35: SSL_ERROR_SYSCALL; no content retrieved'}, {'url':'https://api-web.nhle.com/v1/schedule/2026-10-22','result':'curl exit 35: SSL_ERROR_SYSCALL; no content retrieved'}],
 'files':inventory,'rows':rows}
(DATA/'review.json').write_text(json.dumps(report,indent=2)+'\n')
style='''body{font:16px system-ui;background:#f3f6fa;color:#182d40;margin:0}main,header{max-width:1250px;margin:auto;padding:28px}header{background:#102b40;color:white;max-width:none}nav a{color:inherit;margin-right:22px}h1{font-size:34px}section,.notice{background:white;padding:22px;border-radius:10px;margin:20px 0}.notice{border-left:5px solid #bf7520}table{border-collapse:collapse;width:100%;font-size:14px}td,th{text-align:left;padding:12px;border-bottom:1px solid #dce3eb;vertical-align:top}a{color:#12628c}small{color:#536678}input{padding:12px;width:90%;max-width:500px}.scroll{overflow:auto}.badge{color:#895400}code{overflow-wrap:anywhere}'''
def page(name,title,body):
    (OUT/name).write_text(f'<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} · OLBG evidence review</title><style>{style}</style><header><nav><a href="index.html">Overview</a><a href="entries.html">All reviewed rows</a><a href="flagged.html">Flagged for Review</a><a href="methodology.html">Methodology</a><a href="../index.html">Existing site</a></nav><h1>{esc(title)}</h1><p>Evidence integrity desk · Review date 22 October 2026 · No live verified picks</p></header><main>{body}</main></html>')
def table(rs):
    s='<input aria-label="Filter reviewed rows" placeholder="Search category, file or record ID" oninput="for(const r of document.querySelectorAll(\'tbody tr\'))r.hidden=!r.textContent.toLowerCase().includes(this.value.toLowerCase())"><div class="scroll"><table><thead><tr>'+''.join('<th>'+x+'</th>' for x in ['Record / category','Original record','Official-source candidate (unverified)','Confirmed match / start','Own lines / pick / confidence','Status'])+'</tr></thead><tbody>'
    for r in rs:
        source=f'<a rel="noopener" href="{esc(r["recorded_source_url"])}">Recorded source — not validated</a>' if r['recorded_source_url'] else '<span class="badge">No source recorded — flagged</span>'
        s+=f'<tr><td>{esc(r["audit_id"])}<br>{esc(r["category_as_recorded"])}</td><td><a href="../{esc(r["file"])}">{esc(r["legacy_id"] or "Original JSON")}</a><br><small>{esc(r["pointer"])}</small></td><td>{source}</td><td></td><td></td><td class="badge">Unverified<br><small>Not independently revalidated</small></td></tr>'
    return s+'</tbody></table></div>'
cats=sorted(set(r['category_as_recorded'] for r in rows))
links='<ul>'+''.join(f'<li><a href="sport-{slug(c)}.html">{esc(c)}</a> — {sum(r["category_as_recorded"]==c for r in rows)} reviewed records</li>' for c in cats)+'</ul>'
page('index.html','What can actually be verified?',f'<div class="notice"><strong>No refreshed match list or betting recommendations is certified by this review.</strong> Official-site access failed. Historical verification labels are not inherited. Unconfirmed values are blank, not estimated.</div><section><h2>{len(rows):,} legacy records · {len(paths)} datasets · 0 independently confirmed here</h2><p>Counts include duplicate fixtures across builds, historical rows, and possible excluded sports. They are review-record counts, not unique upcoming matches.</p><a href="entries.html">Inspect every reviewed record →</a></section><section><h2>Categories as recorded</h2><p>These are audit categories, not an endorsement of sport eligibility or coverage completeness. Excluded sports, if present, are retained only for review and receive no picks.</p>{links}</section><section><h2>Machine-readable review</h2><a href="../data/session-7bbc825b/review.json">Download review, source probes and SHA-256 file inventory</a></section>')
page('entries.html','All reviewed rows',table(rows))
for c in cats: page('sport-'+slug(c)+'.html',c+' — evidence review',table([r for r in rows if r['category_as_recorded']==c]))
page('flagged.html','Flagged for Review','''<section><h2>Unresolved findings</h2><ol><li>Live OLBG and NHL retrieval failed (TLS error 35). No response body or current fixture evidence was obtained.</li><li>Prior verified labels and source URLs require independent field-level checks. This review neither proves nor disproves those historical sports claims.</li><li>Not all repo datasets are covered. Only the master rows and session desk rows listed in the JSON inventory were inspected structurally.</li><li>A complete current fixture list, full market inventory, and calibrated independent probabilities are unavailable here. Picks and prediction text remain blank.</li><li>Official-source candidates are copied from old records, not independently authenticated. Rows without a source remain flagged rather than receiving an invented official link.</li><li>Root navigation is owned by another session (open PR #102); this isolated dashboard does not replace or certify other published pages.</li></ol></section>'''+table(rows))
page('methodology.html','Verification and pricing boundaries','''<section><h2>Fail-closed evidence policy</h2><p>Every reviewed record identifies its file, JSON pointer, legacy ID and recorded source URL where present. Confirmed fixture, start time, prices, pick, confidence and prediction remain blank until an official source can be fetched and its exact evidence mapped to that field. Source links alone are not verification. File hashes establish which repository bytes were reviewed, not whether sports facts are true.</p><h2>Own lines are estimates, not official facts</h2><p>Origination requires separately verified inputs, an explicit reproducible model, out-of-sample calibration and market settlement rules. A high model probability is not demonstrated confidence without validation. This desk originates no lines on unconfirmed inputs.</p><h2>Odds-window arithmetic</h2><p>At American −250, implied probability is 250 / 350 = 71.43%. At +10000 it is 100 / 10100 = 0.99%. A 70% probability corresponds to fair odds about −233.33. Thus a 70%-plus threshold and fair prices inside this window overlap only from 70% through 71.43%. Model probability and an independently observed bookmaker price can differ, but such a difference is not proof of an edge. Bookmaker margin must be removed before comparisons.</p><h2>Prediction publication gate</h2><p>Any future high-confidence text must exceed 30 words, name the selection, identify relevant verified participants, form and recent results, link the supporting official evidence, and distinguish factual observations from model opinion. No filler predictions are generated to satisfy a quota.</p></section>''')
print(f'Built {len(list(OUT.glob("*.html")))} pages; {len(rows)} review records')
