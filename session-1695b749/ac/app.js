
document.querySelectorAll('input[data-filter]').forEach(function(box){
  var table=document.getElementById(box.dataset.filter);
  box.addEventListener('input',function(){
    var q=box.value.toLowerCase();
    table.querySelectorAll('tbody tr').forEach(function(tr){
      tr.style.display = tr.textContent.toLowerCase().indexOf(q)>-1 ? '' : 'none';
    });
    var vis=table.querySelectorAll('tbody tr:not([style*="none"])').length;
    var out=document.getElementById(box.dataset.filter+'-count');
    if(out){out.textContent=vis+' rows shown';}
  });
});
