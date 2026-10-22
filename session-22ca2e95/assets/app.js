(function () {
  function applyOddsFormat(fmt) {
    localStorage.setItem('board_ae_odds_fmt', fmt);
    document.querySelectorAll('.odds-toggle button').forEach(function (btn) {
      btn.classList.toggle('active', btn.dataset.fmt === fmt);
    });
    document.querySelectorAll('.odds-chip').forEach(function (el) {
      var am = el.dataset.am || '';
      var dec = el.dataset.dec || '';
      var inner = el.querySelector('.o-both');
      if (!inner) return;
      if (fmt === 'am') {
        inner.textContent = am;
      } else if (fmt === 'dec') {
        inner.textContent = dec;
      } else {
        inner.innerHTML = am + ' <small>(' + dec + ')</small>';
      }
    });
  }

  function applyFilters() {
    var qEl = document.getElementById('ae-search');
    var spEl = document.getElementById('ae-sport');
    var cfEl = document.getElementById('ae-conf');
    var frEl = document.getElementById('ae-fresh');
    var q = qEl ? qEl.value.trim().toLowerCase() : '';
    var sp = spEl ? spEl.value : '';
    var cf = cfEl ? cfEl.value : '';
    var onlyFresh = frEl ? frEl.checked : false;

    var shown = 0;
    document.querySelectorAll('.filterable-item').forEach(function (item) {
      var ok = true;
      if (q && (item.textContent || '').toLowerCase().indexOf(q) === -1) ok = false;
      if (sp && item.dataset.sport !== sp) ok = false;
      if (cf && item.dataset.conf !== cf) ok = false;
      if (onlyFresh && item.dataset.fresh !== '1') ok = false;
      item.style.display = ok ? '' : 'none';
      if (ok) shown += 1;
    });
    var cnt = document.getElementById('ae-visible-count');
    if (cnt) cnt.textContent = shown + ' shown';
  }

  document.addEventListener('DOMContentLoaded', function () {
    var saved = localStorage.getItem('board_ae_odds_fmt') || 'both';
    applyOddsFormat(saved);
    document.querySelectorAll('.odds-toggle button').forEach(function (btn) {
      btn.addEventListener('click', function () { applyOddsFormat(btn.dataset.fmt); });
    });
    ['ae-search', 'ae-sport', 'ae-conf', 'ae-fresh'].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) {
        el.addEventListener('input', applyFilters);
        el.addEventListener('change', applyFilters);
      }
    });
  });
})();
