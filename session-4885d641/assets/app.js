document.addEventListener('DOMContentLoaded', () => {
  const search = document.getElementById('filter-search');
  const sport = document.getElementById('filter-sport');
  const conf = document.getElementById('filter-conf');
  const countEl = document.getElementById('filter-count');
  const targets = [...document.querySelectorAll('[data-filter-item]')];
  if (!targets.length) return;
  function apply() {
    const q = (search ? search.value : '').trim().toLowerCase();
    const s = sport ? sport.value : '';
    const c = conf ? conf.value : '';
    let shown = 0;
    for (const el of targets) {
      const okQ = !q || el.textContent.toLowerCase().includes(q);
      const okS = !s || el.dataset.sport === s;
      const okC = !c || el.dataset.conf === c || el.dataset.tier === c;
      el.hidden = !(okQ && okS && okC);
      if (!el.hidden) shown++;
    }
    if (countEl) countEl.textContent = `${shown} of ${targets.length} shown`;
  }
  if (search) search.addEventListener('input', apply);
  if (sport) sport.addEventListener('change', apply);
  if (conf) conf.addEventListener('change', apply);
  apply();
});
