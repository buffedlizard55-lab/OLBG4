
document.addEventListener('DOMContentLoaded',function(){
  function wire(){
    document.querySelectorAll('[data-filter-for]').forEach(function(inp){
      var target=inp.getAttribute('data-filter-for');
      var col=inp.getAttribute('data-filter-col');
      inp.addEventListener('input',function(){
        var q=inp.value.toLowerCase().trim();
        var table=document.getElementById(target);
        if(!table) return;
        var idx=col?parseInt(col,10):null;
        table.querySelectorAll('tbody tr').forEach(function(tr){
          var hay=(idx!==null&&!isNaN(idx))?(tr.cells[idx]?tr.cells[idx].textContent:tr.textContent):tr.textContent;
          tr.style.display=hay.toLowerCase().indexOf(q)>=0?'':'none';
        });
      });
    });
    document.querySelectorAll('[data-select-for]').forEach(function(sel){
      var target=sel.getAttribute('data-select-for');
      var col=parseInt(sel.getAttribute('data-select-col'),10);
      sel.addEventListener('change',function(){
        var v=sel.value.toLowerCase();
        var table=document.getElementById(target);
        if(!table) return;
        table.querySelectorAll('tbody tr').forEach(function(tr){
          var cell=tr.cells[col]?tr.cells[col].textContent.trim().toLowerCase():'';
          tr.style.display=(!v||cell===v)?'':'none';
        });
      });
    });
  }
  wire();
});
