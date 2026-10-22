
(function(){
  document.querySelectorAll('[data-filterable]').forEach(function(table){
    var scope = table.closest('.panel') || document;
    var bar = scope.querySelector('.filterbar');
    if(!bar) return;
    var rows = Array.prototype.slice.call(table.querySelectorAll('tbody tr'));
    var count = bar.querySelector('[data-count]');
    function apply(){
      var conf = (bar.querySelector('[data-filter=conf]')||{}).value || '';
      var mkt = (bar.querySelector('[data-filter=market]')||{}).value || '';
      var shown = 0;
      rows.forEach(function(r){
        var ok = (!conf || r.dataset.conf === conf) && (!mkt || r.dataset.market === mkt);
        r.style.display = ok ? '' : 'none';
        if(ok) shown++;
      });
      if(count) count.textContent = shown + ' of ' + rows.length + ' rows';
    }
    bar.querySelectorAll('select').forEach(function(s){ s.addEventListener('change', apply); });
    apply();
  });
})();
