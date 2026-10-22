
const box=document.querySelector('#filter');
if(box){const rows=[...document.querySelectorAll('tbody tr[data-row]')];const count=document.querySelector('#shown');
const run=()=>{const q=box.value.toLowerCase();let n=0;for(const r of rows){const hit=!q||r.dataset.search.includes(q);r.hidden=!hit;if(hit)n++;}if(count)count.textContent=n+' rows shown';};
box.addEventListener('input',run);run();}
