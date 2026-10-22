(() => {
  const normalise = value => (value || '').toLocaleLowerCase().trim();
  document.querySelectorAll('[data-filter-form]').forEach(form => {
    const target = document.getElementById(form.dataset.filterForm);
    if (!target) return;
    const items = Array.from(target.querySelectorAll('.filterable'));
    const query = form.querySelector('[data-q]');
    const selects = Array.from(form.querySelectorAll('[data-field]'));
    const count = form.querySelector('[data-count]');
    const apply = () => {
      const q = normalise(query && query.value);
      let visible = 0;
      items.forEach(item => {
        const matchesQuery = !q || normalise(item.dataset.search).includes(q);
        const matchesSelects = selects.every(select => !select.value || item.dataset[select.dataset.field] === select.value);
        const show = matchesQuery && matchesSelects;
        item.hidden = !show;
        if (show) visible += 1;
      });
      if (count) count.textContent = `${visible.toLocaleString()} of ${items.length.toLocaleString()} shown`;
    };
    if (query) query.addEventListener('input', apply);
    selects.forEach(select => select.addEventListener('change', apply));
    apply();
  });
})();
