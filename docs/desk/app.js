(function(){
  var rows=[].slice.call(document.querySelectorAll('table[data-filter] tbody tr'));
  if(!rows.length) return;
  var q=document.getElementById('q'), c=document.getElementById('conf'), s=document.getElementById('sport');
  function apply(){
    var qv=(q&&q.value||'').toLowerCase(), cv=(c&&c.value||''), sv=(s&&s.value||'');
    rows.forEach(function(tr){
      var text=tr.innerText.toLowerCase();
      var ok=(!qv||text.indexOf(qv)>-1)&&(!cv||tr.dataset.conf===cv)&&(!sv||tr.dataset.sport===sv);
      tr.style.display=ok?'':'none';
    });
    var shown=rows.filter(function(tr){return tr.style.display!=='none'}).length;
    var out=document.getElementById('count');
    if(out) out.textContent=shown+' of '+rows.length+' rows';
  }
  [q,c,s].forEach(function(el){ if(el){ el.addEventListener('input',apply); el.addEventListener('change',apply);} });
  apply();
})();
