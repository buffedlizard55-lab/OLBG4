/* OLBG4 dashboard logic — loads data/matches.json + data/sources.json, renders filters + tables
 *
 * Board K (arena/47b1b4e2-olbg4) changes, 2026-10-21:
 *  - F-04: rows carry `entryType` (match / result / tournament / note). The table defaults to
 *    real matches only, with a control to show the other entry kinds, and each row is badged.
 *  - F-01: `sourceClass` distinguishes governing-body sources from secondary ones. Only rows
 *    sourced to a governing body can show VERIFIED; the KPIs report both counts separately.
 *  - F-02: withdrawn predictions are disclosed on the row and on the Flagged page rather than
 *    silently removed, with the reason and the official page that contradicted them.
 *  - F-03/F-08: corrected rows show a "Corrected by Board K" note linking the official source.
 */
const $ = (s, r=document) => r.querySelector(s);
const $$ = (s, r=document) => [...r.querySelectorAll(s)];

const state = { q:"", sport:"all", confidence:"all", status:"all", entry:"match", showFlaggedOnly:false };

const ENTRY_LABEL = {
  match: "Matches",
  result: "Completed results",
  tournament: "Tournaments / rounds",
  note: "Notes (no fixture)"
};

async function loadJSON(path){
  const res = await fetch(path);
  if(!res.ok) throw new Error(`Failed to load ${path}: ${res.status}`);
  return res.json();
}

function badgeConfidence(c){
  const cls = c==="High" ? "badge-high" : c==="Medium" ? "badge-medium" : "badge-low";
  return `<span class="badge ${cls}">${escapeHtml(c||"Low").toUpperCase()}</span>`;
}
function badgeVerify(m){
  if(m.flagged) return `<span class="badge badge-flagged">FLAGGED / UNVERIFIED</span>`;
  return m.verified ? `<span class="badge badge-verified">VERIFIED (official source)</span>`
                    : `<span class="badge badge-flagged">UNVERIFIED</span>`;
}
function badgeEntry(m){
  const t = m.entryType || "match";
  if(t === "match") return "";
  return `<span class="badge badge-flagged" title="${escapeHtml(m.entryTypeLabel||"")}">${escapeHtml(t).toUpperCase()}</span>`;
}
function badgeSourceClass(m){
  if(m.sourceClass === "official") return "";
  return `<div class="small" style="margin-top:4px;color:#92400e">Source class: ${escapeHtml(m.sourceClass||"secondary")} (${escapeHtml(m.sourceDomain||"")}) — not a governing body</div>`;
}

function matchRow(m){
  const oddsML = m.originatedMoneyline ? `${escapeHtml(m.originatedMoneyline.a)} ↔ ${escapeHtml(m.originatedMoneyline.b)}` : "—";
  const oddsSp = escapeHtml(m.originatedSpread || "—");
  const oddsTot = escapeHtml(m.originatedTotal || "—");
  const flagged = m.flagged ? `<div class="small" style="margin-top:6px;color:#92400e">⚠️ Flag: ${escapeHtml(m.flagReason || "See Flagged page")}</div>` : "";
  const pred = m.prediction ? `<div class="detail"><strong>Pick:</strong> ${escapeHtml(m.pick)} — ${escapeHtml(m.prediction)}<div class="small" style="margin-top:6px">Form: ${escapeHtml(m.formNotes || "")}</div></div>`
                            : (m.formNotes ? `<div class="detail"><div class="small">Form / notes: ${escapeHtml(m.formNotes)}</div></div>` : "");
  const source = `<a href="${escapeHtml(m.sourceUrl||"#")}" target="_blank" rel="noopener">${escapeHtml(m.sourceName || "Source")}</a><div class="small">${escapeHtml(m.sourceUrl||"")}</div>`;

  // Board K: disclose corrections and withdrawals inline so nothing disappears silently.
  const kv = m.k_verification ? `<div class="small" style="margin-top:6px;padding:6px 8px;border-left:3px solid #2563eb;background:#eff6ff">
      <strong>Corrected by Board K (${escapeHtml(m.k_verification.checked_utc)}) — ${escapeHtml(m.k_verification.finding)}.</strong>
      ${escapeHtml(m.k_verification.what_was_wrong)}
      <div style="margin-top:4px">Re-verified against <a href="${escapeHtml(m.k_verification.official_source)}" target="_blank" rel="noopener">${escapeHtml(m.k_verification.official_source)}</a></div>
    </div>` : "";
  const kw = m.k_withdrawn ? `<div class="small" style="margin-top:6px;padding:6px 8px;border-left:3px solid #b45309;background:#fffbeb">
      <strong>Prediction withdrawn by Board K.</strong> ${escapeHtml(m.k_withdrawn.reason)}
      <details style="margin-top:4px"><summary style="cursor:pointer">Show the withdrawn text (kept for review)</summary>
      <div style="margin-top:4px;color:#57534e">${escapeHtml(m.k_withdrawn.prediction)}</div></details>
    </div>` : "";
  const ku = m.k_unverified_values ? `<div class="small" style="margin-top:6px;color:#92400e">
      Blanked (not confirmable on a governing-body domain, so not inferred): ${
        Object.keys(m.k_unverified_values).map(k=>`${escapeHtml(k)} was “${escapeHtml(m.k_unverified_values[k].value)}”`).join("; ")}</div>` : "";

  return `<tr>
    <td>
      <div style="font-weight:700">${escapeHtml(m.date)}</div>
      <div class="small">${escapeHtml(m.time || "")}</div>
      <div class="small" style="margin-top:4px">${badgeVerify(m)} ${badgeEntry(m)}</div>
      ${badgeSourceClass(m)}
    </td>
    <td><span class="tag">${escapeHtml(m.sport)}</span><div class="small" style="margin-top:6px">${escapeHtml(m.competition)}</div></td>
    <td>
      <div class="match">${escapeHtml(m.match)}</div>
      <div class="meta">${escapeHtml(m.venue || "")}</div>
      <div class="meta" style="margin-top:4px">ID: ${escapeHtml(m.id)} • Market: ${escapeHtml(m.marketFocus || "")}</div>
      ${flagged}
      ${kv}
      ${ku}
    </td>
    <td>
      <div class="small">Moneyline (our line)</div><div class="odds">${oddsML}</div>
      <div class="small" style="margin-top:6px">Handicap / Spread</div><div class="odds">${oddsSp}</div>
      <div class="small" style="margin-top:6px">Total</div><div class="odds">${oddsTot}</div>
    </td>
    <td>
      <div class="pick">${escapeHtml(m.pick || "")}</div>
      <div style="margin-top:6px">${badgeConfidence(m.confidence)}</div>
      <div class="small" style="margin-top:6px">Status: ${escapeHtml(m.status || "")}</div>
    </td>
    <td>
      ${pred}
      ${kw}
      <div class="small" style="margin-top:6px">${source}</div>
    </td>
  </tr>`;
}

function escapeHtml(s){
  if(s===null || s===undefined) return "";
  return String(s).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
}

function filterData(data){
  return data.filter(m=>{
    const et = m.entryType || "match";
    if(state.entry === "match" && et !== "match") return false;
    if(state.entry !== "all" && state.entry !== "match" && et !== state.entry) return false;
    if(state.sport!=="all" && (m.category||"").toLowerCase() !== state.sport) return false;
    if(state.confidence!=="all" && (m.confidence||"Low").toLowerCase() !== state.confidence) return false;
    if(state.status!=="all"){
      const st = (m.status||"").toLowerCase();
      if(state.status==="scheduled" && !st.includes("scheduled")) return false;
      if(state.status==="completed" && !(st.includes("finished")||st.includes("completed")||st.includes("played")||st.includes("final"))) return false;
    }
    if(state.showFlaggedOnly && !m.flagged) return false;
    if(state.q){
      const q = state.q.toLowerCase();
      const hay = `${m.id} ${m.sport} ${m.competition} ${m.match} ${m.venue} ${m.pick} ${m.prediction} ${m.sourceName}`.toLowerCase();
      if(!hay.includes(q)) return false;
    }
    return true;
  });
}

function renderStats(data){
  const el = $("#stats");
  if(!el) return;
  const total = data.length;
  const matches = data.filter(m=>(m.entryType||"match")==="match").length;
  const official = data.filter(m=>m.sourceClass==="official").length;
  const verified = data.filter(m=>m.verified && !m.flagged).length;
  const flagged = data.filter(m=>m.flagged || !m.verified).length;
  const high = data.filter(m=>m.confidence==="High").length;
  const sports = new Set(data.map(m=>m.sport)).size;
  const pct = (n)=> total ? Math.round(n/total*100) : 0;
  el.innerHTML = `
    <div class="kpi"><div class="label">Matches</div><div class="value">${matches} <span class="small">/ ${total}</span></div><div class="sub">single fixtures with named participants; the other ${total-matches} entries are tournaments, results or notes (shown via the Entry filter)</div></div>
    <div class="kpi"><div class="label">Official-source rows</div><div class="value">${official} <span class="small">/ ${total}</span></div><div class="sub">${pct(official)}% link a governing body; the other ${total-official} link a secondary site and are flagged unverified</div></div>
    <div class="kpi"><div class="label">Verified &amp; unflagged</div><div class="value">${verified} <span class="small">/ ${total}</span></div><div class="sub">${pct(verified)}% — a row is only VERIFIED when its own source is a governing body and no field is in dispute</div></div>
    <div class="kpi"><div class="label">High confidence</div><div class="value">${high}</div><div class="sub">each with a ≥30-word prediction built only from officially verified facts</div></div>
    <div class="kpi"><div class="label">Flagged for review</div><div class="value">${flagged}</div><div class="sub">published openly with source links; flagged items do not block deployment</div></div>
    <div class="kpi"><div class="label">Sports covered</div><div class="value">${sports}</div><div class="sub">excl. soccer, boxing, UFC/MMA, football, American football, hurling, horse racing, cycling, specials</div></div>
  `;
}

function renderTable(data){
  const tbody = $("#tbody");
  const count = $("#rowCount");
  if(!tbody) return;
  if(data.length===0){
    tbody.innerHTML = `<tr><td colspan="6" class="small" style="text-align:center;padding:22px">No entries match your filters — clear the search, or set Entry to “All entry kinds”.</td></tr>`;
    if(count) count.textContent = "0 rows";
    return;
  }
  tbody.innerHTML = data.map(matchRow).join("");
  if(count) count.textContent = `${data.length} rows • ${data.filter(m=>m.flagged).length} flagged • ${data.filter(m=>m.sourceClass==="official").length} official-source`;
}

/* Board K (F-04): inject the Entry-kind control into every page's control bar, so the 16
   hub pages get it without each being hand-edited. */
function injectEntryControl(){
  const left = $(".controls .left");
  if(!left || $("#filterEntry")) return;
  const sel = document.createElement("select");
  sel.id = "filterEntry";
  sel.className = "select";
  sel.innerHTML = `
    <option value="match">Matches only (default)</option>
    <option value="all">All entry kinds</option>
    <option value="tournament">Tournaments / rounds</option>
    <option value="result">Completed results</option>
    <option value="note">Notes (no fixture)</option>`;
  sel.title = "Board J finding F-04: not every published entry is a match. Filter by entry kind.";
  left.appendChild(sel);
  return sel;
}

function attachControls(allData){
  const sportSel = $("#filterSport");
  const confSel = $("#filterConfidence");
  const statusSel = $("#filterStatus");
  const entrySel = injectEntryControl();
  const qInput = $("#q");
  const flaggedToggle = $("#toggleFlagged");
  const clearBtn = $("#clearBtn");

  const rerender = ()=> renderTable(filterData(allData));
  if(sportSel) sportSel.addEventListener("change", e=>{ state.sport=e.target.value; rerender(); });
  if(confSel) confSel.addEventListener("change", e=>{ state.confidence=e.target.value; rerender(); });
  if(statusSel) statusSel.addEventListener("change", e=>{ state.status=e.target.value; rerender(); });
  if(entrySel) entrySel.addEventListener("change", e=>{ state.entry=e.target.value; rerender(); });
  if(qInput) qInput.addEventListener("input", e=>{ state.q=e.target.value.trim(); rerender(); });
  if(flaggedToggle) flaggedToggle.addEventListener("change", e=>{ state.showFlaggedOnly=e.target.checked; rerender(); });
  if(clearBtn) clearBtn.addEventListener("click", ()=>{
    state.q=""; state.sport="all"; state.confidence="all"; state.status="all"; state.entry="match"; state.showFlaggedOnly=false;
    if(qInput) qInput.value=""; if(sportSel) sportSel.value="all"; if(confSel) confSel.value="all";
    if(statusSel) statusSel.value="all"; if(entrySel) entrySel.value="match"; if(flaggedToggle) flaggedToggle.checked=false;
    rerender();
  });

  // auto-filter by URL ?sport=basketboard&entry=all etc
  const params = new URLSearchParams(location.search);
  if(params.get("sport")){ state.sport=params.get("sport"); if(sportSel) sportSel.value=state.sport; }
  if(params.get("confidence")){ state.confidence=params.get("confidence"); if(confSel) confSel.value=state.confidence; }
  if(params.get("entry")){ state.entry=params.get("entry"); if(entrySel) entrySel.value=state.entry; }
  if(params.get("q")){ state.q=params.get("q"); if(qInput) qInput.value=state.q; }
}

function renderToc(matches){
  const toc = $("#toc");
  if(!toc) return;
  const cats = [...new Set(matches.map(m=>m.category).filter(Boolean))].sort();
  const labels = {
    "basketball":"Basketball","baseball":"Baseball","tennis":"Tennis","cricket":"Cricket","rugby":"Rugby Union","ice-hockey":"Ice Hockey",
    "snooker":"Snooker","darts":"Darts","golf":"Golf","badminton":"Badminton","table-tennis":"Table Tennis","volleyball":"Volleyball","handball":"Handball","esports":"Esports","aussie-rules":"Aussie Rules"
  };
  toc.innerHTML = cats.map(c=>`<a href="${c}.html">${labels[c]||c} (${matches.filter(m=>m.category===c).length})</a>`).join("")
    + `<a href="flagged.html">Flagged for Review (${matches.filter(m=>m.flagged).length})</a> `
    + `<a href="methodology.html">Methodology</a> <a href="sources.html">Sources</a> `
    + `<a href="session-47b1b4e2/">Board K remediation report</a>`;
}

function renderFlagged(matches){
  const flaggedTbody = $("#flaggedTbody");
  if(!flaggedTbody) return;
  const flagged = matches.filter(m=>m.flagged);
  if(flagged.length===0){
    flaggedTbody.innerHTML = `<tr><td colspan="5" class="small" style="text-align:center;padding:18px">No flagged entries.</td></tr>`;
  } else {
    flaggedTbody.innerHTML = flagged.map(m=>{
      const w = m.k_withdrawn ? `<div style="margin-top:6px;padding:6px 8px;border-left:3px solid #b45309;background:#fffbeb">
          <strong>Prediction withdrawn (was ${escapeHtml(m.k_withdrawn.confidence)} confidence).</strong>
          ${escapeHtml(m.k_withdrawn.reason)}
          <details style="margin-top:4px"><summary style="cursor:pointer">Withdrawn text</summary><div style="margin-top:4px;color:#57534e">${escapeHtml(m.k_withdrawn.prediction)}</div></details>
        </div>` : "";
      const v = m.k_verification ? `<div style="margin-top:6px">Re-verified ${escapeHtml(m.k_verification.checked_utc)} against <a href="${escapeHtml(m.k_verification.official_source)}" target="_blank" rel="noopener">${escapeHtml(m.k_verification.official_source)}</a></div>` : "";
      return `<tr>
        <td>${escapeHtml(m.id)}<div class="small">${escapeHtml(m.sport)}</div><div class="small">${escapeHtml(m.entryType||"match")}</div></td>
        <td><strong>${escapeHtml(m.match)}</strong><div class="small">${escapeHtml(m.date)} • ${escapeHtml(m.venue||"")}</div></td>
        <td class="small">${escapeHtml(m.flagReason||"Flagged — see source column")}${w}${v}</td>
        <td class="small">${escapeHtml(m.sourceName||"")}<br><a href="${escapeHtml(m.sourceUrl||"#")}" target="_blank" rel="noopener">${escapeHtml(m.sourceUrl||"")}</a>
            <div style="margin-top:4px">Source class: <strong>${escapeHtml(m.sourceClass||"")}</strong></div></td>
        <td class="small">${escapeHtml(m.status||"")}<div style="margin-top:4px">${badgeConfidence(m.confidence)}</div></td>
      </tr>`;
    }).join("");
  }
  const fc = $("#flaggedCount");
  if(fc){
    const withdrawn = matches.filter(m=>m.k_withdrawn).length;
    const corrected = matches.filter(m=>m.k_verification).length;
    const nonOfficial = matches.filter(m=>m.sourceClass!=="official").length;
    fc.innerHTML = `${flagged.length} flagged entries • ${nonOfficial} rows whose source is not a governing body • ${corrected} rows corrected against an official source • ${withdrawn} predictions withdrawn`;
  }
}

async function boot(){
  try{
    const [matches, sources] = await Promise.all([loadJSON("data/matches.json"), loadJSON("data/sources.json")]);
    matches.sort((a,b)=> (a.date||"").localeCompare(b.date||""));
    renderStats(matches);
    renderToc(matches);
    attachControls(matches);
    renderTable(filterData(matches));

    // category pages: pre-filter by the data-category attribute on <html>
    const cat = document.documentElement.getAttribute("data-category");
    if(cat){
      state.sport = cat;
      const sel = $("#filterSport"); if(sel) sel.value=cat;
      renderTable(filterData(matches));
    }

    const srcEl = $("#sourcesList");
    if(srcEl && sources){
      srcEl.innerHTML = sources.map(s=>`<tr>
        <td><strong>${escapeHtml(s.sport)}</strong><div class="small">${escapeHtml(s.source)}</div></td>
        <td><a href="${escapeHtml(s.url)}" target="_blank" rel="noopener">${escapeHtml(s.url)}</a>${s.url2?`<div class="small"><a href="${escapeHtml(s.url2)}" target="_blank" rel="noopener">${escapeHtml(s.url2)}</a></div>`:""}</td>
        <td class="small">${escapeHtml(s.verified)}<div>${escapeHtml(s.notes)}</div></td>
      </tr>`).join("");
    }

    renderFlagged(matches);
  } catch(e){
    console.error(e);
    const tbody = $("#tbody"); if(tbody) tbody.innerHTML = `<tr><td colspan="6" style="padding:18px;color:#b91c1c">Failed to load data: ${escapeHtml(e.message)}<br><span class="small">Check that the site is served via HTTP (not file://) and data/*.json exist.</span></td></tr>`;
  }
}

document.addEventListener("DOMContentLoaded", boot);
