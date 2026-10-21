/* OLBG4 dashboard logic — loads data/matches.json + data/sources.json, renders filters + tables */
const $ = (s, r=document) => r.querySelector(s);
const $$ = (s, r=document) => [...r.querySelectorAll(s)];

const state = { q:"", sport:"all", confidence:"all", status:"all", showFlaggedOnly:false };

async function loadJSON(path){
  const res = await fetch(path);
  if(!res.ok) throw new Error(`Failed to load ${path}: ${res.status}`);
  return res.json();
}

function badgeConfidence(c){
  const cls = c==="High" ? "badge-high" : c==="Medium" ? "badge-medium" : "badge-low";
  return `<span class="badge ${cls}">${c.toUpperCase()}</span>`;
}
function badgeVerify(v, flagged){
  if(flagged) return `<span class="badge badge-flagged">FLAGGED / UNVERIFIED</span>`;
  return v ? `<span class="badge badge-verified">VERIFIED</span>` : `<span class="badge badge-flagged">UNVERIFIED</span>`;
}

function matchRow(m){
  const oddsML = m.originatedMoneyline ? `${escapeHtml(m.originatedMoneyline.a)} ↔ ${escapeHtml(m.originatedMoneyline.b)}` : "—";
  const oddsSp = escapeHtml(m.originatedSpread || "—");
  const oddsTot = escapeHtml(m.originatedTotal || "—");
  const flagged = m.flagged ? `<div class="small" style="margin-top:6px;color:#92400e">⚠️ Flag: ${escapeHtml(m.flagReason || "See Flagged page")}</div>` : "";
  const pred = m.prediction ? `<div class="detail"><strong>Pick:</strong> ${escapeHtml(m.pick)} — ${escapeHtml(m.prediction)}<div class="small" style="margin-top:6px">Form: ${escapeHtml(m.formNotes || "")}</div></div>` : "";
  const source = `<a href="${m.sourceUrl}" target="_blank" rel="noopener">${escapeHtml(m.sourceName || "Official source")}</a><div class="small">${escapeHtml(m.sourceUrl)}</div>`;
  return `<tr>
    <td>
      <div style="font-weight:700">${escapeHtml(m.date)}</div>
      <div class="small">${escapeHtml(m.time || "")}</div>
      <div class="small" style="margin-top:4px">${badgeVerify(m.verified, m.flagged)}</div>
    </td>
    <td><span class="tag">${escapeHtml(m.sport)}</span><div class="small" style="margin-top:6px">${escapeHtml(m.competition)}</div></td>
    <td>
      <div class="match">${escapeHtml(m.match)}</div>
      <div class="meta">${escapeHtml(m.venue || "")}</div>
      <div class="meta" style="margin-top:4px">ID: ${escapeHtml(m.id)} • Market: ${escapeHtml(m.marketFocus || "")}</div>
      ${flagged}
    </td>
    <td>
      <div class="small">Moneyline (our line)</div><div class="odds">${oddsML}</div>
      <div class="small" style="margin-top:6px">Handicap / Spread</div><div class="odds">${oddsSp}</div>
      <div class="small" style="margin-top:6px">Total</div><div class="odds">${oddsTot}</div>
    </td>
    <td>
      <div class="pick">${escapeHtml(m.pick || "")}</div>
      <div style="margin-top:6px">${badgeConfidence(m.confidence || "Low")}</div>
      <div class="small" style="margin-top:6px">Status: ${escapeHtml(m.status || "")}</div>
    </td>
    <td>
      ${pred}
      <div class="small" style="margin-top:6px">${source}</div>
    </td>
  </tr>`;
}

function escapeHtml(s){
  if(!s) return "";
  return String(s).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
}

function filterData(data){
  return data.filter(m=>{
    if(state.sport!=="all" && (m.category||"").toLowerCase() !== state.sport) return false;
    if(state.confidence!=="all" && (m.confidence||"Low").toLowerCase() !== state.confidence) return false;
    if(state.status!=="all"){
      const st = (m.status||"").toLowerCase();
      if(state.status==="scheduled" && !st.includes("scheduled")) return false;
      if(state.status==="completed" && !(st.includes("finished")||st.includes("completed")||st.includes("played"))) return false;
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
  const verified = data.filter(m=>m.verified && !m.flagged).length;
  const flagged = data.filter(m=>m.flagged || !m.verified).length;
  const high = data.filter(m=>m.confidence==="High").length;
  const sports = new Set(data.map(m=>m.sport)).size;
  el.innerHTML = `
    <div class="kpi"><div class="label">Total entries</div><div class="value">${total}</div><div class="sub">matches / outrights in window Oct 8 – Nov 8</div></div>
    <div class="kpi"><div class="label">Verified rows</div><div class="value">${verified} <span class="small">/ ${total}</span></div><div class="sub">${Math.round(verified/total*100)}% with official source link — remainder flagged</div></div>
    <div class="kpi"><div class="label">High confidence</div><div class="value">${high}</div><div class="sub">with ≥30-word verified prediction</div></div>
    <div class="kpi"><div class="label">Sports covered</div><div class="value">${sports}</div><div class="sub">excl. soccer, boxing, UFC/MMA, football, horse racing, cycling, hurling, specials</div></div>
    <div class="kpi"><div class="label">Markets originated</div><div class="value">4–5 per match</div><div class="sub">Moneyline, handicap/spread, totals + matchup specials</div></div>
  `;
}

function renderTable(data){
  const tbody = $("#tbody");
  const count = $("#rowCount");
  if(!tbody) return;
  if(data.length===0){
    tbody.innerHTML = `<tr><td colspan="6" class="small" style="text-align:center;padding:22px">No matches match your filters — clear search or change sport/confidence.</td></tr>`;
    if(count) count.textContent = "0 rows";
    return;
  }
  tbody.innerHTML = data.map(matchRow).join("");
  if(count) count.textContent = `${data.length} rows • ${data.filter(m=>m.flagged).length} flagged`;
}

function attachControls(allData){
  const sportSel = $("#filterSport");
  const confSel = $("#filterConfidence");
  const statusSel = $("#filterStatus");
  const qInput = $("#q");
  const flaggedToggle = $("#toggleFlagged");
  const clearBtn = $("#clearBtn");

  if(sportSel) sportSel.addEventListener("change", e=>{ state.sport=e.target.value; renderTable(filterData(allData)); });
  if(confSel) confSel.addEventListener("change", e=>{ state.confidence=e.target.value; renderTable(filterData(allData)); });
  if(statusSel) statusSel.addEventListener("change", e=>{ state.status=e.target.value; renderTable(filterData(allData)); });
  if(qInput) qInput.addEventListener("input", e=>{ state.q=e.target.value.trim(); renderTable(filterData(allData)); });
  if(flaggedToggle) flaggedToggle.addEventListener("change", e=>{ state.showFlaggedOnly=e.target.checked; renderTable(filterData(allData)); });
  if(clearBtn) clearBtn.addEventListener("click", ()=>{
    state.q=""; state.sport="all"; state.confidence="all"; state.status="all"; state.showFlaggedOnly=false;
    if(qInput) qInput.value=""; if(sportSel) sportSel.value="all"; if(confSel) confSel.value="all"; if(statusSel) statusSel.value="all"; if(flaggedToggle) flaggedToggle.checked=false;
    renderTable(filterData(allData));
  });

  // auto-filter by URL ?sport=basketball etc
  const params = new URLSearchParams(location.search);
  if(params.get("sport")){ state.sport=params.get("sport"); if(sportSel) sportSel.value=state.sport; }
  if(params.get("confidence")){ state.confidence=params.get("confidence"); if(confSel) confSel.value=state.confidence; }
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
  toc.innerHTML = cats.map(c=>`<a href="${c}.html">${labels[c]||c} (${matches.filter(m=>m.category===c).length})</a>`).join("") + `<a href="flagged.html">Flagged for Review (${matches.filter(m=>m.flagged).length})</a> <a href="methodology.html">Methodology</a> <a href="sources.html">Sources</a>`;
}

async function boot(){
  try{
    const [matches, sources] = await Promise.all([loadJSON("data/matches.json"), loadJSON("data/sources.json")]);
    // sort by date asc
    matches.sort((a,b)=> (a.date||"").localeCompare(b.date||""));
    renderStats(matches);
    renderToc(matches);
    attachControls(matches);
    renderTable(filterData(matches));

    // category pages: if .category-filter attribute exists, pre-filter
    const cat = document.documentElement.getAttribute("data-category");
    if(cat){
      state.sport = cat;
      const sel = $("#filterSport"); if(sel) sel.value=cat;
      renderTable(filterData(matches));
    }

    // sources page render
    const srcEl = $("#sourcesList");
    if(srcEl && sources){
      srcEl.innerHTML = sources.map(s=>`<tr>
        <td><strong>${escapeHtml(s.sport)}</strong><div class="small">${escapeHtml(s.source)}</div></td>
        <td><a href="${s.url}" target="_blank" rel="noopener">${escapeHtml(s.url)}</a>${s.url2?`<div class="small"><a href="${s.url2}" target="_blank">${escapeHtml(s.url2)}</a></div>`:""}</td>
        <td class="small">${escapeHtml(s.verified)}<div>${escapeHtml(s.notes)}</div></td>
      </tr>`).join("");
    }

    // flagged page
    const flaggedTbody = $("#flaggedTbody");
    if(flaggedTbody){
      const flagged = matches.filter(m=>m.flagged);
      if(flagged.length===0){
        flaggedTbody.innerHTML = `<tr><td colspan="6" class="small" style="text-align:center;padding:18px">No flagged entries — all rows verified.</td></tr>`;
      } else {
        flaggedTbody.innerHTML = flagged.map(m=>`<tr>
          <td>${escapeHtml(m.id)}<div class="small">${escapeHtml(m.sport)}</div></td>
          <td><strong>${escapeHtml(m.match)}</strong><div class="small">${escapeHtml(m.date)} • ${escapeHtml(m.venue||"")}</div></td>
          <td class="small">${escapeHtml(m.flagReason||"Flagged — see source column")}</td>
          <td class="small">${escapeHtml(m.sourceName||"")}<br><a href="${m.sourceUrl}" target="_blank">${escapeHtml(m.sourceUrl)}</a></td>
          <td class="small">${escapeHtml(m.status||"")}</td>
        </tr>`).join("");
      }
      const fc = $("#flaggedCount"); if(fc) fc.textContent = `${flagged.length} flagged entries`;
    }

  } catch(e){
    console.error(e);
    const tbody = $("#tbody"); if(tbody) tbody.innerHTML = `<tr><td colspan="6" style="padding:18px;color:#b91c1c">Failed to load data: ${escapeHtml(e.message)}<br><span class="small">Check that the site is served via HTTP (not file://) and data/*.json exist.</span></td></tr>`;
  }
}

document.addEventListener("DOMContentLoaded", boot);
