// Board V — dependency-free filter for the fixture tables.
document.querySelectorAll('[data-filter]').forEach(function (el) {
  el.addEventListener('input', apply);
  el.addEventListener('change', apply);
});
function apply() {
  document.querySelectorAll('table.grid').forEach(function (table) {
    var bar = table.closest('main').querySelector('.toolbar');
    if (!bar) return;
    var sport = bar.querySelector('[data-filter=sport]');
    var conf = bar.querySelector('[data-filter=conf]');
    var q = bar.querySelector('[data-filter=q]');
    var rows = table.tBodies[0].rows, shown = 0;
    for (var i = 0; i < rows.length; i++) {
      var r = rows[i], ok = true;
      if (sport && sport.value && r.dataset.sport !== sport.value) ok = false;
      if (conf && conf.value && r.dataset.conf !== conf.value) ok = false;
      if (q && q.value && r.textContent.toLowerCase().indexOf(q.value.toLowerCase()) === -1) ok = false;
      r.style.display = ok ? '' : 'none';
      if (ok) shown++;
    }
    var c = document.getElementById(table.id + '-count');
    if (c) c.textContent = shown + ' rows';
  });
}
