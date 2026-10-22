document.addEventListener('DOMContentLoaded', function(){
var table = document.getElementById('entries-table');
if (!table) return;
var rows = table.querySelectorAll('tbody tr');
var filters = {};
function render(){
  var sport = document.getElementById('fsport').value;
  var conf = document.getElementById('fconf').value;
  rows.forEach(function(tr){
    var show = (!sport || tr.dataset.sport === sport) && (!conf || tr.dataset.conf === conf);
    tr.style.display = show ? '' : 'none';
  });
  var n = 0; rows.forEach(function(tr){ if (tr.style.display !== 'none') n++; });
  var el = document.getElementById('count'); if (el) el.textContent = n + ' of ' + rows.length + ' entries shown';
}
var fsport = document.getElementById('fsport');
if (fsport) fsport.addEventListener('change', render);
var fconf = document.getElementById('fconf');
if (fconf) fconf.addEventListener('change', render);
render();
});