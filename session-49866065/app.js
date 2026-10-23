/* Filtering is presentation only. It never changes evidence or claims a live feed. */
const search = document.querySelector('#search');
const sport = document.querySelector('#sport-filter');
const date = document.querySelector('#date-filter');
const count = document.querySelector('#result-count');
function applyFilters() {
  let n = 0;
  document.querySelectorAll('tr[data-search]').forEach(row => {
    let visible = !search || row.dataset.search.toLowerCase().includes(search.value.toLowerCase());
    if (sport?.value) visible &&= row.dataset.sport === sport.value;
    if (date?.value === 'today') visible &&= row.dataset.start?.slice(0,10) === document.body.dataset.cutoff.slice(0,10);
    if (date?.value === 'not-started') visible &&= row.dataset.start && Date.parse(row.dataset.start) > Date.now();
    row.hidden = !visible;
    if (visible) n++;
  });
  if (count) count.textContent = `${n} rows shown`;
}
[search,sport,date].forEach(el => el?.addEventListener(el===search?'input':'change',applyFilters));
if (search) applyFilters();
const age = (Date.now()-Date.parse(document.body.dataset.cutoff))/3600000;
const freshness = document.querySelector('#freshness');
if (freshness) freshness.textContent = age > 24
  ? `Dated snapshot — ${Math.floor(age/24)} day(s) since capture. Refresh official status before using any entry.`
  : 'Snapshot, not live odds. Fixtures may have changed since capture.';
document.querySelector('#mobile-sport')?.addEventListener('change', e => {
  // Options are generated from a fixed local category list, never external input.
  if (e.target.value) window.location.href=e.target.value;
});
const target = document.getElementById(decodeURIComponent(window.location.hash.slice(1)));
if (target?.tagName==='DETAILS') target.open=true;
