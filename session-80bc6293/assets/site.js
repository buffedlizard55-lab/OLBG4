
function filterTable(tid){
  var t=document.getElementById(tid); if(!t) return;
  var inputs=t.querySelectorAll('thead select, thead input');
  var rows=t.querySelectorAll('tbody tr');
  rows.forEach(function(r){
    var show=true;
    inputs.forEach(function(inp){
      var idx=parseInt(inp.getAttribute('data-col'),10);
      var cell=r.cells[idx]; if(!cell) return;
      var v=(cell.getAttribute('data-v')||cell.textContent||'').toLowerCase();
      var want=(inp.value||'').toLowerCase();
      if(want && v.indexOf(want)===-1) show=false;
    });
    r.style.display=show?'':'none';
  });
}
