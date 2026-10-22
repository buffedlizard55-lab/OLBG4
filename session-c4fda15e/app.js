document.querySelectorAll('input[data-filter]').forEach(function(inp){var t=document.getElementById(inp.dataset.filter);
inp.addEventListener('input',function(){var q=inp.value.toLowerCase();t.querySelectorAll('tbody tr').forEach(function(r){r.style.display=r.textContent.toLowerCase().indexOf(q)>-1?'':'none';});});});
