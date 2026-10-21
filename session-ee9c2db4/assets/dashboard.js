(function () {
  "use strict";

  function norm(s) {
    return (s || "").toLowerCase().trim();
  }

  document.querySelectorAll("[data-filter-root]").forEach(function (root) {
    var targetId = root.getAttribute("data-filter-root");
    var container = document.getElementById(targetId);
    if (!container) return;
    var items = Array.prototype.slice.call(container.querySelectorAll("[data-filter-item]"));
    var searchInput = root.querySelector("[data-filter-search]");
    var selects = Array.prototype.slice.call(root.querySelectorAll("select[data-filter-attr]"));
    var countEl = root.querySelector("[data-filter-count]");

    function apply() {
      var q = searchInput ? norm(searchInput.value) : "";
      var shown = 0;
      items.forEach(function (el) {
        var ok = true;
        if (q && norm(el.textContent).indexOf(q) === -1) {
          ok = false;
        }
        if (ok) {
          for (var i = 0; i < selects.length; i++) {
            var sel = selects[i];
            var want = sel.value;
            if (want && want !== "all") {
              var attr = "data-" + sel.getAttribute("data-filter-attr");
              if ((el.getAttribute(attr) || "") !== want) {
                ok = false;
                break;
              }
            }
          }
        }
        el.style.display = ok ? "" : "none";
        if (ok) shown += 1;
      });
      if (countEl) {
        countEl.textContent = "Showing " + shown + " of " + items.length;
      }
    }

    if (searchInput) searchInput.addEventListener("input", apply);
    selects.forEach(function (s) { s.addEventListener("change", apply); });
    apply();
  });

  // Progressive column sorting on all static tables
  document.querySelectorAll("table.sortable").forEach(function (tbl) {
    var headers = tbl.querySelectorAll("thead th");
    var tbody = tbl.querySelector("tbody");
    if (!tbody) return;
    headers.forEach(function (th, idx) {
      var asc = true;
      th.addEventListener("click", function () {
        var rows = Array.prototype.slice.call(tbody.querySelectorAll("tr"));
        rows.sort(function (a, b) {
          var ca = (a.children[idx] ? a.children[idx].textContent : "").trim();
          var cb = (b.children[idx] ? b.children[idx].textContent : "").trim();
          var na = parseFloat(ca.replace(/[^0-9.-]/g, ""));
          var nb = parseFloat(cb.replace(/[^0-9.-]/g, ""));
          if (!isNaN(na) && !isNaN(nb) && /^[0-9+-.%@]/.test(ca) && /^[0-9+-.%@]/.test(cb)) {
            return asc ? na - nb : nb - na;
          }
          return asc ? ca.localeCompare(cb) : cb.localeCompare(ca);
        });
        asc = !asc;
        rows.forEach(function (r) { tbody.appendChild(r); });
      });
    });
  });
})();
