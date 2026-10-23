"""Build the isolated strict dashboard deterministically from pinned capture bytes.
python scripts/session-49866065/build.py
"""
from __future__ import annotations
import html
import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit
from core import ROOT, DATA, SPORTS, Evidence, slug, instant, olbg_inventory, price, pointer
from parsers import parse_official, reconcile

OUT=ROOT/'session-49866065'
def esc(s): return html.escape(str(s),quote=True)
def link(url,label='Official source'):
    if not url:return ''
    p=urlsplit(url)
    if p.scheme not in ('http','https') and not (not p.scheme and not p.netloc):raise ValueError('Unsafe URL')
    return f'<a href="{esc(url)}">{esc(label)}</a>'
def tag(s,kind=''):return f'<span class="tag {esc(kind)}">{esc(s)}</span>'
def fmt_us(x):return f'{x:+.0f}'
def dump(path,obj):path.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')
def table(headers,body,caption=''):
    return '<div class="table-wrap"><table>'+('<caption class="skip">'+esc(caption)+'</caption>' if caption else '')+'<thead><tr>'+''.join('<th scope="col">'+esc(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join(body)+'</tbody></table></div>'
def tr(cells,search=None,sport='',start=''):
    attrs=f' data-search="{esc(search)}" data-sport="{esc(sport)}" data-start="{esc(start)}"' if search is not None else ''
    return '<tr'+attrs+'>'+''.join('<td>'+str(c)+'</td>' for c in cells)+'</tr>'
def toolbar(sports=True,dates=True):
    return '<div class="toolbar"><label class="skip" for="search">Search table</label><input id="search" type="search" placeholder="Search fixtures, competitions or findings…">'+('<label class="skip" for="sport-filter">Sport</label><select id="sport-filter"><option value="">All 15 sports</option>'+''.join('<option>'+esc(s)+'</option>' for s in SPORTS)+'</select>' if sports else '')+('<label class="skip" for="date-filter">Date</label><select id="date-filter"><option value="">All at capture</option><option value="today">Capture day (UTC)</option><option value="not-started">Not yet started now</option></select>' if dates else '')+'<span id="result-count" class="results" aria-live="polite"></span></div>'

def make_desk(e):
    rows,errors=parse_official(e)
    listings=olbg_inventory(e)
    reconcile(listings,rows)
    review=json.loads((DATA/'review.json').read_text()) if (DATA/'review.json').exists() else {'rows':[],'files':[]}
    flags=[]
    def flag(sport,subject,detail,official_url,olbg_url='',row_id=''):
        flags.append(dict(id=f'FA-{len(flags)+1:04}',sport=sport,subject=subject,detail=detail,official_url=official_url,olbg_url=olbg_url,row_id=row_id))
    for sport,(target,url) in SPORTS.items():
        flag(sport,'Five High-confidence picks not established','0/5: no calibrated High-confidence selections supported by this evidence gate. No quota padding, invented injury reports or generic predictions.',url)
        if not any(r['sport']==sport for r in rows):
            flag(sport,'Official fixture coverage incomplete','Public source capture does not yield an independently supported fixture through the implemented JSON adapters for this category. This is a coverage gap, NOT a claim of no matches.',url)
        flag(sport,'Complete OLBG coverage and posting access not established','Captured hub tips are a visible sample, not a guaranteed full event/market feed. No private/disallowed endpoint was accessed. Account posting eligibility was not tested.',url)
    for l in listings:
        if not l['official_id']:
            flag(l['sport'],'OLBG listing not reconciled',f"OLBG observation only: {l['listed_name']} — {l['listed_start']}. No unique official pairing at the exact same timestamp; official facts, lines and pick left blank. "+('Listing marked expired.' if not l['active'] else ''),SPORTS[l['sport']][1],l['olbg_url'],l['id'])
    for r in rows:
        if not r['olbg_ids']:flag(r['sport'],'Official fixture not found on captured OLBG hubs',r['away']+' v '+r['home']+'. Officially scheduled but OLBG listing/market eligibility not established.',r['official_url'],row_id=r['id'])
        for f in r['flags']:flag(r['sport'],'Research / market limitation',f,r['official_url'],row_id=r['id'])
    for rec in e.records.values():
        if not rec.get('file') or rec.get('status')!=200:
            flag('Source capture',rec['id'],f"HTTP {rec.get('status')} — {rec.get('error','No payload')}. Nothing inferred from this response.",rec['url'])
    if 'Newinn Jolly withdrawn' in e.text('gbgb_champion_stakes'):
        flag('Greyhounds','Official withdrawal report', 'GBGB’s 19 October article states Newinn Jolly was withdrawn from the Coral 100 Champion Stakes Final with a urine infection. Do not select this runner from an old card. This article does not establish a complete current field or trap draw.',e.records['gbgb_champion_stakes']['url'])
    flag('Volleyball','Calendar query returned historical finals','The captured legavolley calendar request includes Anno=2026 but the body lists April/May 2026 finals. It is not adopted as an upcoming October schedule. Standings alone cannot confirm an OLBG pairing.',e.records['legavolley_cal_991']['url'])
    flag('Cross-sport','Odds-window interpretation','For fair lines, 70% is −233.33 and −250 is 71.4286%. A ≥70% estimate and own price ≥−250 overlap only from 70% through 71.4286%. Offered OLBG/bookmaker prices are not these independently calculated fair lines; no offered-price eligibility asserted.','https://www.olbg.com/betting-tips')
    flag('Repository','Stale legacy master publication repaired','Canonical regeneration changed five stale master-board artifacts before release. This repair restores build reproducibility; it does not freshly verify the legacy NBA/MLB facts or predictions. Source inputs and peer generators were not changed.','https://github.com/buffedlizard55-lab/OLBG4/blob/main/tools/build_master.py')
    flag('Repository','Peer factual labels not inherited',f"{len(review['rows'])} rows audited structurally. Their match values are NOT independently re-confirmed in this pass. See the pinned row-level review, which leaves confirmed_values empty.",'https://github.com/buffedlizard55-lab/OLBG4')
    return dict(schema='olbg4.strict-evidence/1',cutoff=e.manifest['finished_at'],window_end=(e.cutoff.date()).isoformat()+' + 16 days',
        sports=list(SPORTS),rows=rows,listings=listings,flags=flags,review=review,
        limitations=['Not a complete OLBG match/market enumeration.','No High-confidence selections pass independent calibration/injury/eligibility gates.',
                     'Fair prices are experimental calculations, not officially sourced facts or offered betting prices.',
                     'No claims that an OLBG account can currently post on a listing.','No verified injury data: blank does not mean no injuries.'],
        high_predictions=[],errors=errors)

class Site:
    def __init__(self,e,desk):self.e=e;self.d=desk;self.rows=desk['rows'];self.listings=desk['listings'];self.flags=desk['flags']
    def page(self,file,title,body):
        nav=[('index.html','Overview'),('fixtures.html','Official fixtures'),('markets.html','Our lines & markets'),('predictions.html','Predictions'),('flagged.html','Flagged for Review'),('review.html','Repository review'),('sources.html','Sources & evidence'),('methodology.html','Methodology')]
        def navlink(f,t):return f'<a href="{f}"'+(' aria-current="page"' if file==f else '')+'>'+esc(t)+'</a>'
        sidebar='<aside class="sidebar"><a class="brand" href="index.html">OLBG<b>4</b><small>INDEPENDENT RESEARCH DESK</small></a><nav aria-label="Main"><div class="nav-section">Research workspace</div>'+''.join(navlink(f,t) for f,t in nav)+'<div class="nav-section">15 covered sports</div><div class="sport-nav">'+''.join(navlink(slug(s)+'.html',s) for s in SPORTS)+'</div></nav><div class="side-foot">Evidence before selections.<br>Sources linked. Gaps visible.<br>Prices independently calculated.</div></aside>'
        mobile='<div class="mobile-nav"><label class="skip" for="mobile-sport">Choose sport</label><select id="mobile-sport"><option value="">Browse a sport…</option>'+''.join('<option value="'+slug(s)+'.html">'+esc(s)+'</option>' for s in SPORTS)+'</select></div>'
        text='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+esc(title)+' · OLBG4 Evidence Desk</title><meta name="description" content="Source-linked 15-sport fixture research, independent fair lines and transparent review flags."><link rel="stylesheet" href="style.css"><script defer src="app.js"></script></head><body data-cutoff="'+esc(self.d['cutoff'])+'"><a class="skip" href="#main">Skip to content</a>'+sidebar+'<div class="layout"><header class="topbar"><strong>SPORTS RESEARCH / '+esc(title.upper())+'</strong><span>Evidence cutoff '+esc(self.d['cutoff'][:19].replace('T',' '))+' UTC</span></header><main id="main">'+mobile+body+'</main><footer>'+link('methodology.html','How prices are calculated')+link('sources.html','Capture evidence')+link('../index.html','Repository landing page')+'<p>18+ · Research, not a guarantee of return. Fair probabilities are estimates; never stake money you cannot afford to lose. All times UTC unless explicitly sourced otherwise. This project is independent of OLBG.</p></footer></div></body></html>'
        (OUT/file).write_text(text)
    def heading(self,title,desc,kicker='Evidence-led research'):
        return '<p class="eyebrow">'+esc(kicker)+'</p><h1>'+esc(title)+'</h1><p class="intro">'+desc+'</p>'
    def source(self,r):return link(r['official_url'])+'<small>'+link('evidence.html#'+r['id'],'Field-by-field evidence')+'</small>'
    def official_table(self,rows):
        body=[]
        for r in rows:
            pick=r['pick'];ptext=''
            if pick:ptext=esc(pick['selection'])+'<small>'+fmt_us(pick['american'])+' fair · '+f"{pick['probability']:.1%}"+' estimate</small>'
            body.append(tr([esc(r['sport']),'<strong>'+esc(r['away'])+' v '+esc(r['home'])+'</strong><small>'+esc(r['competition'])+'</small>',esc(r['start_utc'].replace('T',' ')[:16])+'<small>'+esc(r['status'])+(' · if necessary' if r['conditional'] else '')+'</small>',tag('linked','ok') if r['olbg_ids'] else tag('not established','warn'),ptext,tag(r['confidence'],'low') if r['confidence'] else '',self.source(r)],r['away']+' '+r['home']+' '+r['competition']+' '+r['sport'],r['sport'],r['start_utc']))
        return table(['Sport','Official fixture','Start UTC','OLBG listing','Our fair winner','Confidence','Evidence'],body,'Official source-confirmed fixtures, with separate calculated prices')
    def coverage(self):
        body=[]
        for sport,(_,url) in SPORTS.items():
            ls=[l for l in self.listings if l['sport']==sport];rs=[r for r in self.rows if r['sport']==sport]
            n=sum(bool(r['pick']) for r in rs);matched=sum(bool(r['olbg_ids']) for r in rs)
            body.append(tr([link(slug(sport)+'.html',sport),str(len(ls)),str(len(rs)),str(matched),str(n),'<strong>0 / 5</strong><div class="progress"><i></i></div>',tag('partial' if rs else 'gap','warn'),link(url,'Official review source')]))
        return table(['Category','OLBG sample','Official fixtures','Linked to OLBG','Priced','High / target','Coverage','Official source'],body)
    def build_overview(self):
        priced=[r for r in self.rows if r['pick']];matched=[r for r in self.rows if r['olbg_ids']]
        today=[r for r in self.rows if r['start_utc'][:10]==self.d['cutoff'][:10]]
        b='<div class="hero"><div>'+self.heading('A clearer view of every pick.','A single, source-linked desk for the 15 requested sports. Official fixture facts, independent fair prices and unresolved questions are kept visibly separate.','15 sports · independent lines · transparent evidence')+'</div><div class="stamp">Capture date<b>'+esc(self.d['cutoff'][:10])+'</b>UTC snapshot<div id="freshness"></div></div></div>'
        b+='<div class="notice"><strong>No High-confidence picks cleared the evidence gate.</strong> The daily goal is five per sport (75 total). Missing calibration, injury/line-up coverage and incomplete OLBG matching are disclosed instead of filling the quota with unsupported predictions. '+link('flagged.html','See the limitations →')+'</div>'
        cards=[('Official upcoming fixtures',len(self.rows),'At source-capture cutoff; not a live feed'),('Matched OLBG listings',len(matched),'Pairing and timestamp reconciled'),('Independent winner lines',len(priced),'Experimental estimates · low research confidence'),('High-confidence predictions',0,'0 of 75 daily target · no fabricated write-ups')]
        b+='<div class="cards">'+''.join('<div class="card"><div class="label">'+esc(t)+'</div><div class="number">'+str(n)+'</div><div class="sub">'+esc(note)+'</div></div>' for t,n,note in cards)+'</div>'
        b+='<div class="split"><section class="panel"><p class="eyebrow">Executive summary</p><h2>Today’s High-confidence selections</h2><div class="empty"><h3>No qualifying selections published</h3><p>'+str(len(today))+' official fixtures remain on the capture day (UTC), but none has sufficient evidence for a High-confidence recommendation. A calculated win probability is not the same thing as confidence in the research.</p></div><p>Upcoming summary: '+str(len(self.rows))+' official fixture rows, '+str(len(self.listings))+' observed OLBG listings, '+str(len(matched))+' official fixtures linked to OLBG. Completeness and posting access are not established.</p><div class="links">'+link('fixtures.html','Explore upcoming fixtures →')+link('predictions.html','Prediction coverage →')+'</div></section><section class="panel"><p class="eyebrow">Research standards</p><h2>What a number means</h2><div class="metric-line"><span>Fixture facts</span>'+tag('source-backed','ok')+'</div><div class="metric-line"><span>Our fair lines</span>'+tag('calculated estimates','low')+'</div><div class="metric-line"><span>Missing facts / injuries</span>'+tag('blank + flagged','warn')+'</div><div class="metric-line"><span>OLBG posting eligibility</span>'+tag('not tested','warn')+'</div><p>No bookmaker prices or OLBG tip percentages are used to originate our lines.</p>'+link('methodology.html','Read the pricing and confidence policy →')+'</section></div>'
        b+='<section class="section"><div class="section-head"><h2>Coverage by sport</h2>'+link('flagged.html','Review coverage gaps →')+'</div>'+self.coverage()+'<p class="legend">“OLBG sample” counts distinct event records exposed in captured hub tips, not all events on OLBG. Official fixture counts can include entries absent from that sample. Never add the two columns as unique matches.</p></section>'
        ranked=sorted([r for r in priced if r['olbg_ids'] and not r['conditional']],key=lambda r:r['pick']['probability'],reverse=True)[:5]
        b+='<section class="section"><div class="section-head"><h2>Highest calculated probabilities · OLBG-linked watchlist</h2>'+link('markets.html','See all fair lines →')+'</div><p class="audit-note">These are LOW-confidence research entries, not High-confidence recommendations. Ranking does not promote confidence. The requested odds filter refers here to our own fair line, not a quoted bookmaker price.</p>'
        b+=self.official_table(ranked) if ranked else '<div class="empty">No priced, unambiguous OLBG-linked fixture is available.</div>'
        b+='</section>'
        self.page('index.html','Overview',b)
    def build_sports(self):
        for sport,(_,official) in SPORTS.items():
            rs=[r for r in self.rows if r['sport']==sport];ls=[l for l in self.listings if l['sport']==sport]
            b=self.heading(sport,'Officially sourced fixtures and separate OLBG observations. Blank official cells mean the listing has not been confirmed, not that the value is zero.')
            b+='<div class="notice"><strong>High-confidence target: 0 / 5.</strong> Incomplete form, injury, market and calibration evidence prevents High-confidence publication. '+link('flagged.html','Flagged for Review')+'</div>'
            b+='<h2>Official upcoming fixtures</h2>'+toolbar(False)+self.official_table(rs)
            if not rs:b+='<p class="audit-note">No official fixture adapter produced a supported row for this sport. There may still be upcoming matches. '+link(official,'Review the official source')+'</p>'
            b+='<section class="section"><h2>OLBG observation register</h2><p class="audit-note">Listing titles below are quoted as OLBG observations only. Confirmed participants and start times remain blank for unmatched rows; a federation review link is not proof of that listing.</p>'
            obs=[]
            lookup={r['id']:r for r in rs}
            for l in ls:
                r=lookup.get(l['official_id'])
                obs.append(tr([esc(l['listed_name'])+'<small>OLBG-reported only · '+('unexpired' if l['active'] else 'expired')+'</small>',esc(r['away']+' v '+r['home']) if r else '',esc(r['start_utc']) if r else '',tag('linked','ok') if r else tag('unverified','warn'),link(l['olbg_url'],'OLBG listing')+'<small>'+link(r['official_url'] if r else official,'Official fixture source' if r else 'Official review source (not confirmation)')+'</small>']))
            b+=table(['OLBG observation (not official)','Confirmed participants','Confirmed start UTC','Status','Sources'],obs)+'</section>'
            self.page(slug(sport)+'.html',sport,b)
    def build_fixtures(self):
        b=self.heading('Official fixture register','Every displayed match participant and start has an official raw-source reference. Only events scheduled after the capture cutoff and within 16 days are included. Missing prices and OLBG links are not inferred.')+toolbar()+self.official_table(self.rows)
        self.page('fixtures.html','Official fixtures',b)
    def build_markets(self):
        b=self.heading('Our lines & investigated markets','Winner prices are independently originated fair estimates, without bookmaker margin. Official sources establish inputs, not winning probabilities. Unsupported handicaps, totals and derivatives stay blank.')
        b+='<div class="notice info"><strong>Pricing method:</strong> Beta(2,2)-smoothed win records with Log5 opponent comparison. No fitted home advantage. No bookmaker odds or OLBG consensus inputs. '+link('methodology.html','Formula and limitations →')+'</div>'+toolbar()
        body=[]
        for r in self.rows:
            for m in r['markets']:
                for s in m['selections']:
                    body.append(tr(['<strong>'+esc(r['away']+' v '+r['home'])+'</strong><small>'+esc(r['sport']+' / '+r['competition'])+'</small>',esc(m['name']),esc(s['selection']),f"{s['probability']:.2%}",f"{s['decimal']:.3f}",fmt_us(s['american']),tag('low','low'),self.source(r)],r['away']+' '+r['home']+' '+r['sport']+' '+m['name'],r['sport'],r['start_utc']))
        b+=table(['Fixture','Market scope','Selection','Estimated chance','Fair decimal','Fair American','Confidence','Official inputs'],body)
        b+='<section class="section"><h2>Observed OLBG market investigation</h2><p class="audit-note">Every market/selection found in captured hub tips is listed below, including unsupported markets. This is not proof of every market available on an event page. Availability and settlement equivalence are not established.</p>'
        body=[];lookup={r['id']:r for r in self.rows}
        for l in self.listings:
            r=lookup.get(l['official_id'])
            for m in l['markets']:
                reason='Not priced: official fixture identity/time not reconciled.' if not r else 'OLBG settlement equivalence unconfirmed; only separately labelled winner fair estimate may exist. No direct offered-market price claimed.'
                body.append(tr([esc(l['sport']),esc(l['listed_name'])+'<small>OLBG observation only</small>',esc(m['name']),esc(m['selection']),'',esc(reason),link(l['olbg_url'],'OLBG market listing')+'<small>'+link(r['official_url'] if r else SPORTS[l['sport']][1],'Official fixture source' if r else 'Official review source')+'</small>']))
        b+=table(['Sport','Observed event','Market observed','Selection observed','Adopted official line','Investigation result','Sources'],body)+'</section>'
        self.page('markets.html','Our lines & markets',b)
    def build_evidence(self):
        b=self.heading('Field-by-field evidence','Each source-backed factual field carries an original URL, a JSON pointer (or exact HTML character span) into captured bytes and a SHA-256 digest. Derived prices are deliberately excluded from these official factual fields.')
        for r in self.rows:
            body=[]
            for f in r['facts']:
                if not f:continue
                file=self.e.records[f['target']]['file']
                body.append(tr([esc(f['label']),esc(f['value']),'<code>'+esc(f['target']+':'+f['pointer'])+'</code>',link(f['url'])+'<small>'+link('../data/session-49866065/capture/'+file,'Captured bytes (.gz)')+'</small>','<code>'+esc(f['sha256'])+'</code>']))
            b+='<details id="'+esc(r['id'])+'" class="evidence-card"><summary>'+esc(r['away']+' v '+r['home']+' · '+r['start_utc'])+'</summary>'+table(['Field','Source value','Exact location','Source / bytes','SHA-256'],body)+'</details>'
        self.page('evidence.html','Field evidence',b)
    def build_flags(self):
        b=self.heading('Flagged for Review','Gaps and irregularities remain visible and do not silently become verified facts. No missing values are filled in. Each row links to the source that requires review; a generic official review URL does not confirm a match.')+toolbar(dates=False)
        body=[]
        for f in self.flags:
            body.append(tr([esc(f['id']),esc(f['sport']),'<strong>'+esc(f['subject'])+'</strong>'+esc(f['detail']),tag('needs review','warn'),link(f['official_url'],'Source for review')+('<small>'+link(f['olbg_url'],'OLBG observation')+'</small>' if f['olbg_url'] else '')],f['id']+' '+f['sport']+' '+f['subject']+' '+f['detail'],f['sport']))
        b+=table(['ID','Category','Finding','Status','Source links'],body)
        self.page('flagged.html','Flagged for Review',b)
    def build_review(self):
        review=self.d['review']
        b=self.heading('Repository row-by-row review',f"{len(review['rows'])} rows across {len(review.get('files',[]))} pinned datasets inspected for structural defects. This audit is not a factual re-verification of every peer row; their confirmed values remain blank and no peer probabilities or prose are inherited.")
        b+='<div class="notice"><strong>Scope disclosure:</strong> The fresh official fixture register is field-reconciled to captured source bytes. The legacy repository is audited structurally only; missing official URLs, old dates, scope mismatches and unsupported High labels are review findings, not corrections to another session’s files.</div>'+toolbar(False,False)
        body=[]
        for r in review['rows']:
            body.append(tr([link(r['blob_url'],r['file'])+'<small><code>'+esc(r['pointer'])+'</code></small>',esc(r['id']),'',tag('unverified','warn'),'<br>'.join(esc(x) for x in r['issues']),'<br>'.join(link(u,'Official-source candidate (not rechecked)') for u in r['official_source_candidates'])],r['file']+' '+r['id']+' '+' '.join(r['issues'])))
        b+=table(['Pinned file / row','Row identifier','Confirmed facts','Review status','Findings','Official-source candidates'],body)
        b+='<p class="audit-note">A blank source column means no recognized official-source URL was found on that row. The original file is linked for manual review; no official source is invented. '+link('../data/session-49866065/review.json','Download the pinned review JSON')+'</p>'
        self.page('review.html','Repository review',b)
    def build_sources(self):
        b=self.heading('Sources & capture ledger','Raw public responses are stored as deterministic gzip with SHA-256 over decompressed bytes. HTTP success alone is not factual validation; shells and incomplete payloads are not promoted to fixture facts.')
        b+='<p class="audit-note">Capture began '+esc(self.e.manifest['started_at'])+' and finished '+esc(self.e.manifest['finished_at'])+'. Original source URLs are provided for manual review. '+link('../data/session-49866065/capture/manifest.json','Download manifest')+'</p>'+toolbar(False,False)
        body=[]
        used={f['target'] for r in self.rows for f in r['facts'] if f}
        for rec in self.e.records.values():
            target=rec['id'];status=rec.get('status',0)
            body.append(tr([esc(target),link(rec['url'],urlsplit(rec['url']).hostname or rec['url']),tag(str(status),'ok' if status==200 else 'warn'),str(rec.get('bytes','')),tag('facts extracted','ok') if target in used else tag('capture only'),link('../data/session-49866065/capture/'+rec['file'],'Raw .gz') if rec.get('file') else esc(rec.get('error','')),'<code>'+esc(rec.get('sha256',''))+'</code>'],target+' '+rec['url']+' '+str(status)))
        b+=table(['Target','Original source','HTTP','Bytes','Use in this desk','Capture / error','SHA-256'],body)
        b+='<section class="section panel"><h2>OLBG public-page analysis</h2><p>Captured sport hubs expose SvelteKit <code>tips:[…]</code> data containing event names, timestamps, event links, selections and market names. A non-executing, bounded string parser reads this public payload. Entries are deduplicated by sport, event identifier and timestamp. This sample is not a complete fixture API.</p><p>OLBG robots.txt was fetched before sport pages; disallowed paths or unavailable robots fail closed. No login, private account data, disallowed API, bot challenge bypass or submission test was used.</p>'+link('markets.html','Inspect the captured market taxonomy →')+'</section>'
        self.page('sources.html','Sources & evidence',b)
    def build_predictions(self):
        b=self.heading('Predictions & daily targets','Only supported High-confidence selections qualify for a published prediction. No match-specific factual claim is inferred from a seed, a betting price, a missing injury report or a quota.')
        b+='<div class="empty"><h3>No High-confidence prediction can responsibly be published from this capture</h3><p>Official schedule confirmation is necessary, but not sufficient. There is no independently backtested calibration, complete recent-match research, injury coverage and confirmed OLBG posting eligibility for a High selection. No generic or fabricated 30-word write-ups have been inserted.</p></div><section class="section"><h2>Five-per-sport target</h2>'+self.coverage()+'</section><section class="section panel"><h2>Publication checklist</h2><ol class="steps"><li>Confirm exact upcoming participants, start and status from official sources; reconcile the OLBG listing.</li><li>Originate fair prices from supported inputs with the correct market settlement rules.</li><li>Show out-of-sample calibration and uncertainty; do not assign High merely because p exceeds 70%.</li><li>Research current form, recent match history, relevant match statistics and sourced injury information. Missing injury information stays blank.</li><li>For a qualifying selection, write a unique ≥30-word prediction with a clear betting selection and source links, without internal terminology. Do not fill a five-match quota if evidence is insufficient.</li></ol></section>'
        self.page('predictions.html','Predictions',b)
    def build_methodology(self):
        b=self.heading('Methodology & confidence','Official facts and statistical estimates have different evidence standards. This desk never presents an estimated win probability as a fact established by an official source.')
        b+='<div class="panel"><h2>Independent fair winner lines</h2><p>For each side with a supported season record, smooth its win share using an explicit Beta(2,2) prior: <code>a = (away wins + 2) / (away games + 4)</code>, <code>b = (home wins + 2) / (home games + 4)</code>. Then <code>P(away) = a(1−b) / [a(1−b) + b(1−a)]</code>. The other side receives <code>1−P(away)</code>. NHL records count overtime/shootout losses as losses for a full-game winner estimate. EuroLeague/EuroCup records are derived only from completed, non-tied same-season scores captured before the cutoff.</p><p>Fair decimal = <code>1/p</code>. Fair American = <code>−100p/(1−p)</code> when p ≥ 0.5, otherwise <code>100(1−p)/p</code>. Prices have no bookmaker margin. Calculations are stored unrounded; UI rounding is presentation only. Probabilities are not clamped to force a confidence/odds window.</p><h2>What this method does not establish</h2><p>No adjustment is fitted for home advantage, travel, starting goaltenders/pitchers, injuries, strength of schedule or roster changes. No independent out-of-sample calibration has been demonstrated. These limitations keep all calculated picks at <strong>low research confidence</strong>, regardless of numerical p. Medium/High are reserved, not awarded without evidence. No inference is made about absent factual fields.</p><h2>Handicaps, totals and derivatives</h2><p>Every market/selection visible in the captured OLBG hub sample is inventoried. That is not exhaustive market discovery. Regulation handicaps/totals require regulation-only scoring inputs and fitted dispersion; raw NHL season goals include overtime/shootout effects. MLB full-game totals/run lines require extra-inning and pitcher treatment. Basketball totals/spreads require scoring/variance and lineup inputs. Tennis sets/games, golf outrights, greyhound fields and other derivatives need sport-specific settlement and participant data. Unsupported market prices remain blank with a reason.</p><h2>The −250…+10,000 filter</h2><p>Our own ≥70% fair win estimate implies American ≤−233.33. −250 corresponds to 71.4286%. Hence a fair price within that window and ≥70% probability overlap only on [70%, 71.4286%]. A bookmaker’s offered odds are different from our fair price; no current offered-price eligibility is claimed here.</p><h2>Fixture reconciliation and freshness</h2><p>Only timezone-aware official fixture timestamps after the capture cutoff and within the next 16 days are adopted. The URC article’s explicit IRE & UK times are normalized with Europe/London and its published 2026/27 season; original date, pairing and KO text are retained. Cricket Australia’s public JSON.parse fixture string is decoded without running JavaScript. Pairing aliases must come from the official response. OLBG reconciliation requires both participants and the exact same timestamp; ambiguous matches and date-only approximations are rejected. WTA not-before times are bounds, and unscheduled/estimated entries are excluded rather than interpreting 23:59 placeholders as starts. Conditional MLB games remain flagged and unpriced.</p><p>The site is a dated snapshot, not live advice. The “not yet started now” filter can hide passed times but cannot refresh official statuses. Public source links can change; captured bytes preserve what was inspected. Refresh requires the capture workflow and deterministic rebuild; no all-sport unattended daily publication is claimed.</p><h2>Verification boundary</h2><p>Automated checks prove captured fact equality, hashes, arithmetic, scope, local file/anchor links, blank unconfirmed values and deterministic rendering. They do not prove a sports outcome, external URL availability now, feed completeness or that an OLBG account is able to post. Legacy rows receive a separate structural-only audit and retain blank confirmed values.</p></div>'
        self.page('methodology.html','Methodology',b)
    def build(self):
        OUT.mkdir(exist_ok=True)
        self.build_overview();self.build_sports();self.build_fixtures();self.build_markets();self.build_evidence();self.build_flags();self.build_review();self.build_sources();self.build_predictions();self.build_methodology()

def validate(e,d):
    assert set(d['sports'])==set(SPORTS)
    assert not d['high_predictions']
    assert len({r['id'] for r in d['rows']})==len(d['rows'])
    for r in d['rows']:
        assert r['sport'] in SPORTS and instant(r['start_utc'])>e.cutoff
        for f in r['facts']:
            assert f and e.fact_value(f)==f['value']
            assert f['url']==e.records[f['target']]['url'] and f['sha256']==e.records[f['target']]['sha256']
        if r['conditional']:assert not r['markets'] and not r['pick']
        if r['pick']:assert r['confidence']=='low'
        assert r['injuries'] is None and not r['prediction']
        for m in r['markets']:
            assert abs(sum(s['probability'] for s in m['selections'])-1)<1e-10
            for s in m['selections']:
                expected=price(s['probability'])
                assert abs(expected['american']-s['american'])<1e-10
                assert abs(expected['decimal']-s['decimal'])<1e-10
    lookup={r['id']:r for r in d['rows']}
    for l in d['listings']:
        if l['official_id']:
            r=lookup[l['official_id']]
            assert l['active'] and instant(l['listed_start'])==instant(r['start_utc'])
    for r in d['review']['rows']:assert r['status']=='unverified' and r['confirmed_values']=={}

def main():
    e=Evidence();d=make_desk(e);validate(e,d);dump(DATA/'desk.json',d);Site(e,d).build()
    print(json.dumps(dict(fixtures=len(d['rows']),listings=len(d['listings']),priced=sum(bool(r['pick']) for r in d['rows']),linked=sum(bool(r['olbg_ids']) for r in d['rows']),high=len(d['high_predictions']),flags=len(d['flags']),pages=len(list(OUT.glob('*.html'))))))
if __name__=='__main__':main()
