document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-filter-table]").forEach((ctrlWrap) => {
    const targetId = ctrlWrap.getAttribute("data-filter-table");
    const table = document.getElementById(targetId);
    if (!table) return;
    const rows = Array.from(table.querySelectorAll("tbody tr"));
    const searchInput = ctrlWrap.querySelector("input[type='search']");
    const selects = Array.from(ctrlWrap.querySelectorAll("select[data-col]"));
    const counter = ctrlWrap.querySelector("[data-row-count]");

    function apply() {
      const q = (searchInput ? searchInput.value : "").trim().toLowerCase();
      let shown = 0;
      rows.forEach((tr) => {
        let ok = true;
        if (q && !tr.textContent.toLowerCase().includes(q)) ok = false;
        selects.forEach((sel) => {
          const val = sel.value;
          const attr = sel.getAttribute("data-col");
          if (val && tr.getAttribute("data-" + attr) !== val) ok = false;
        });
        tr.style.display = ok ? "" : "none";
        if (ok) shown += 1;
      });
      if (counter) counter.textContent = shown + " / " + rows.length + " rows";
    }
    if (searchInput) searchInput.addEventListener("input", apply);
    selects.forEach((s) => s.addEventListener("change", apply));
    apply();
  });
});
