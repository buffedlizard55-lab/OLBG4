document.addEventListener('DOMContentLoaded', () => {
  const q = document.getElementById('searchInput');
  const sp = document.getElementById('sportSelect');
  const cf = document.getElementById('confSelect');
  const st = document.getElementById('statusSelect');
  const rows = Array.from(document.querySelectorAll('tbody tr.match-row'));
  const counter = document.getElementById('rowCount');

  function applyFilter() {
    if (!rows.length) return;
    const term = (q ? q.value : '').toLowerCase().trim();
    const sportVal = sp ? sp.value : 'all';
    const confVal = cf ? cf.value : 'all';
    const statVal = st ? st.value : 'all';
    let shown = 0;
    for (const r of rows) {
      const okSport = sportVal === 'all' || r.dataset.sport === sportVal;
      const okConf = confVal === 'all' || r.dataset.conf === confVal;
      const okStat = statVal === 'all' || r.dataset.status === statVal;
      const okTerm = !term || r.textContent.toLowerCase().includes(term);
      const vis = okSport && okConf && okStat && okTerm;
      r.style.display = vis ? '' : 'none';
      if (vis) shown++;
    }
    if (counter) counter.textContent = `${shown} of ${rows.length} rows shown`;
  }

  for (const el of [q, sp, cf, st]) {
    if (el) el.addEventListener('input', applyFilter);
    if (el) el.addEventListener('change', applyFilter);
  }
  applyFilter();
});
