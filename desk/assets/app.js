
(function () {
  var table = document.getElementById('fixtures');
  if (!table) return;
  var rows = Array.prototype.slice.call(table.tBodies[0].rows);
  var q = document.getElementById('q'),
      sport = document.getElementById('f-sport'),
      conf = document.getElementById('f-conf'),
      band = document.getElementById('f-band'),
      count = document.getElementById('count');
  function apply() {
    var term = (q.value || '').toLowerCase(), shown = 0;
    rows.forEach(function (tr) {
      var text = tr.innerText.toLowerCase();
      var ok = (!term || text.indexOf(term) !== -1)
        && (!sport.value || tr.getAttribute('data-sport') === sport.value)
        && (!conf.value || tr.getAttribute('data-conf') === conf.value)
        && (!band.value || tr.getAttribute('data-band') === band.value);
      tr.style.display = ok ? '' : 'none';
      if (ok) shown++;
    });
    if (count) count.textContent = shown + ' of ' + rows.length + ' fixtures';
  }
  [q, sport, conf, band].forEach(function (el) { if (el) el.addEventListener('input', apply); });
  apply();
})();
