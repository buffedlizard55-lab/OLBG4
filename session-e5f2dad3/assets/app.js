/* Board U table filters. The tables are fully rendered server-side, so this only
   hides rows and updates a counter — no data is fetched and nothing is tracked. */
(function () {
  function apply(box) {
    var table = document.getElementById(box.getAttribute('data-for'));
    if (!table) return;
    var f = {
      sport: box.querySelector('[data-f="sport"]').value,
      ver: box.querySelector('[data-f="ver"]').value,
      conf: box.querySelector('[data-f="conf"]').value,
      q: box.querySelector('[data-f="q"]').value.trim().toLowerCase()
    };
    var rows = table.tBodies[0].rows, shown = 0;
    for (var i = 0; i < rows.length; i++) {
      var r = rows[i];
      var ok = true;
      if (f.sport && r.getAttribute('data-sport') !== f.sport) ok = false;
      if (ok && f.ver && r.getAttribute('data-ver') !== f.ver) ok = false;
      if (ok && f.conf && (r.getAttribute('data-conf') || 'none') !== f.conf) ok = false;
      if (ok && f.q && (r.getAttribute('data-q') || '').indexOf(f.q) === -1) ok = false;
      r.style.display = ok ? '' : 'none';
      if (ok) shown++;
    }
    var c = box.querySelector('[data-count]');
    if (c) c.textContent = shown + ' of ' + rows.length + ' rows';
  }
  var boxes = document.querySelectorAll('.filters');
  for (var i = 0; i < boxes.length; i++) {
    (function (box) {
      box.addEventListener('input', function () { apply(box); });
      box.addEventListener('change', function () { apply(box); });
      apply(box);
    })(boxes[i]);
  }
})();
