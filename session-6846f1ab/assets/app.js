(() => {
  const norm = (value) => (value || '').toLowerCase();
  document.querySelectorAll('[data-filter]').forEach((input) => {
    const table = document.getElementById(input.dataset.filter);
    if (!table) return;
    const rows = [...table.querySelectorAll('tbody tr')];
    input.addEventListener('input', () => {
      const query = norm(input.value);
      rows.forEach((row) => {
        const haystack = norm(row.dataset.search || row.textContent);
        row.hidden = query && !haystack.includes(query);
      });
    });
  });
  document.querySelectorAll('[data-select-sport]').forEach((select) => {
    const target = document.getElementById(select.dataset.selectSport);
    if (!target) return;
    const cards = [...target.querySelectorAll('[data-sport]')];
    select.addEventListener('change', () => {
      cards.forEach((card) => { card.hidden = select.value && card.dataset.sport !== select.value; });
    });
  });
})();
