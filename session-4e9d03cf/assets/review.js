(() => {
  const REVIEW_URL = '../data/session-4e9d03cf/review.json';
  const $ = (selector) => document.querySelector(selector);
  const esc = (value) => String(value ?? '').replace(/[&<>'"]/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
  }[char]));
  const sourceLink = (row) => row.official_source_url
    ? `<a href="${esc(row.official_source_url)}" target="_blank" rel="noopener noreferrer">Official source ↗</a><small>${esc(row.source_domain || '')}</small>`
    : `<span class="muted">—</span><small>${esc(row.source_status)}</small>`;
  const marketHtml = (markets) => {
    const labels = [['winner', 'Win'], ['handicap', 'Handicap'], ['total', 'Total']];
    const values = labels.filter(([key]) => markets[key]).map(([key, label]) => `<div><b>${label}:</b> ${esc(markets[key])}</div>`);
    return values.length ? values.join('') : '<span class="muted">Blank / not carried</span>';
  };
  const stateLabel = (state) => ({
    'carried-current': 'strict carried',
    'held-source': 'held: source gap',
    'held-verification': 'held: verify gap',
    'held-copy': 'held: copy gap',
    'historical': 'historical',
    'not-a-fixture': 'not a fixture',
    'excluded': 'excluded'
  }[state] || state);
  const matchText = (row) => `${row.home} ${row.away} ${row.competition} ${row.selection} ${row.sport}`.toLowerCase();
  const render = (rows) => {
    const body = $('#rows tbody');
    body.innerHTML = rows.map((row) => `<tr>
      <td><strong>${esc(row.date || '—')}</strong>${row.time ? `<span class="comp">${esc(row.time)}</span>` : ''}</td>
      <td>${esc(row.sport || '—')}<span class="comp">Build ${esc(row.build || '—')}</span></td>
      <td class="match"><strong>${esc(row.home || '—')} <span class="muted">vs</span> ${esc(row.away || '—')}</strong><span class="comp">${esc(row.competition || '—')}</span></td>
      <td><strong>${esc(row.selection || '—')}</strong><span class="comp">${esc(row.selection_market || '')} · ${esc(row.confidence || '—')}</span>${row.prediction_style !== 'none' ? `<span class="comp">Prediction: ${esc(row.prediction_style)} (${esc(row.prediction_words)} words)</span>` : ''}</td>
      <td class="markets">${marketHtml(row.markets)}</td>
      <td class="source">${sourceLink(row)}</td>
      <td><span class="state ${esc(row.review_status)}">${esc(stateLabel(row.review_status))}</span><span class="reason">${esc(row.review_reason)}</span></td>
    </tr>`).join('') || '<tr><td colspan="7">No rows match the selected filters.</td></tr>';
    $('#shown').textContent = `${rows.length} row${rows.length === 1 ? '' : 's'} shown`;
  };
  const filterRows = (allRows) => {
    const view = $('#f-view')?.value || 'all';
    const sport = $('#f-sport')?.value || '';
    const query = ($('#f-query')?.value || '').trim().toLowerCase();
    return allRows.filter((row) => {
      const current = row.in_scope && row.row_type === 'fixture' && row.date >= '2026-10-22';
      const held = ['held-source', 'held-verification', 'held-copy'].includes(row.review_status);
      if (view === 'current' && !current) return false;
      if (view === 'strict' && row.review_status !== 'carried-current') return false;
      if (view === 'held' && !held) return false;
      if (sport && row.sport !== sport) return false;
      return !query || matchText(row).includes(query);
    });
  };
  fetch(REVIEW_URL)
    .then((response) => {
      if (!response.ok) throw new Error(`review data returned ${response.status}`);
      return response.json();
    })
    .then((data) => {
      const update = () => render(filterRows(data.rows));
      ['#f-view', '#f-sport', '#f-query'].forEach((selector) => $(selector)?.addEventListener('input', update));
      document.querySelectorAll('[data-set-view]').forEach((link) => link.addEventListener('click', () => {
        const field = $('#f-view');
        if (field) { field.value = link.dataset.setView; update(); }
      }));
      update();
    })
    .catch((error) => {
      const body = $('#rows tbody');
      if (body) body.innerHTML = `<tr><td colspan="7">Could not load review data: ${esc(error.message)}</td></tr>`;
      const shown = $('#shown');
      if (shown) shown.textContent = 'Review data unavailable.';
    });
})();
