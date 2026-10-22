document.addEventListener('DOMContentLoaded', () => {
  const search = document.querySelector('[data-filter-search]');
  const sportSel = document.querySelector('[data-filter-sport]');
  const confSel = document.querySelector('[data-filter-conf]');
  const catSel = document.querySelector('[data-filter-cat]');
  const countEl = document.querySelector('[data-filter-count]');
  const items = Array.from(document.querySelectorAll('[data-filter-row]'));
  if (!items.length) return;

  function apply() {
    const q = (search ? search.value : '').trim().toLowerCase();
    const sp = sportSel ? sportSel.value : '';
    const cf = confSel ? confSel.value : '';
    const ct = catSel ? catSel.value : '';
    let shown = 0;
    for (const el of items) {
      const okQ = !q || el.textContent.toLowerCase().includes(q);
      const okSp = !sp || el.dataset.sport === sp;
      const okCf = !cf || el.dataset.conf === cf;
      const okCt = !ct || el.dataset.cat === ct;
      const vis = okQ && okSp && okCf && okCt;
      el.hidden = !vis;
      if (vis) shown++;
    }
    if (countEl) countEl.textContent = `${shown} of ${items.length} shown`;
  }

  for (const ctrl of [search, sportSel, confSel, catSel]) {
    if (ctrl) ctrl.addEventListener('input', apply);
    if (ctrl) ctrl.addEventListener('change', apply);
  }
  apply();
});
