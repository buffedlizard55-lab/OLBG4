(function () {
  var btn = document.querySelector('.menu-btn');
  var nav = document.querySelector('nav.main');
  if (btn && nav) {
    btn.addEventListener('click', function () { nav.classList.toggle('open'); });
  }
  function apply() {
    var table = document.getElementById('data');
    if (!table) return;
    var q = (document.getElementById('q') || {}).value || '';
    var sport = (document.getElementById('sport') || {}).value || '';
    var conf = (document.getElementById('conf') || {}).value || '';
    q = q.toLowerCase();
    var rows = table.tBodies[0].rows, shown = 0;
    for (var i = 0; i < rows.length; i++) {
      var r = rows[i];
      var ok = true;
      if (sport && r.getAttribute('data-sport') !== sport) ok = false;
      if (conf && r.getAttribute('data-conf') !== conf) ok = false;
      if (q && r.textContent.toLowerCase().indexOf(q) === -1) ok = false;
      r.style.display = ok ? '' : 'none';
      if (ok) shown++;
    }
    var c = document.getElementById('shown');
    if (c) c.textContent = shown;
  }
  ['q', 'sport', 'conf'].forEach(function (id) {
    var el = document.getElementById(id);
    if (el) { el.addEventListener('input', apply); el.addEventListener('change', apply); }
  });
  apply();
})();
