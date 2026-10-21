(function () {
  "use strict";

  function textOf(row) { return (row.dataset.text || row.textContent || "").toLowerCase(); }

  function applyFilters(table) {
    var search = document.querySelector('[data-filter="search"]');
    var sport = document.querySelector('[data-filter="sport"]');
    var conf = document.querySelector('[data-filter="confidence"]');
    var market = document.querySelector('[data-filter="market"]');
    var q = search ? search.value.trim().toLowerCase() : "";
    var s = sport ? sport.value : "";
    var c = conf ? conf.value : "";
    var m = market ? market.value : "";
    var rows = table.tBodies[0] ? Array.prototype.slice.call(table.tBodies[0].rows) : [];
    var shown = 0;
    rows.forEach(function (row) {
      if (row.dataset.summary === "1") return;
      var ok = true;
      if (q && textOf(row).indexOf(q) === -1) ok = false;
      if (s && row.dataset.sport !== s) ok = false;
      if (c && row.dataset.confidence !== c) ok = false;
      if (m && row.dataset.market !== m) ok = false;
      row.style.display = ok ? "" : "none";
      if (ok) shown += 1;
    });
    var out = document.querySelector("[data-count]");
    if (out) out.textContent = shown + " of " + rows.length + " rows";
  }

  function sortBy(table, index, dir) {
    var body = table.tBodies[0];
    if (!body) return;
    var rows = Array.prototype.slice.call(body.rows);
    rows.sort(function (a, b) {
      var av = a.cells[index] ? (a.cells[index].dataset.sort || a.cells[index].textContent) : "";
      var bv = b.cells[index] ? (b.cells[index].dataset.sort || b.cells[index].textContent) : "";
      var an = parseFloat(av), bn = parseFloat(bv);
      if (!isNaN(an) && !isNaN(bn) && av.trim() !== "" && bv.trim() !== "") {
        return dir * (an - bn);
      }
      return dir * String(av).localeCompare(String(bv));
    });
    rows.forEach(function (r) { body.appendChild(r); });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var table = document.querySelector("table[data-filterable]");
    if (table) {
      ["search", "sport", "confidence", "market"].forEach(function (key) {
        var el = document.querySelector('[data-filter="' + key + '"]');
        if (el) el.addEventListener("input", function () { applyFilters(table); });
        if (el) el.addEventListener("change", function () { applyFilters(table); });
      });
      applyFilters(table);
    }

    Array.prototype.forEach.call(document.querySelectorAll("table th[data-sortable]"), function (th) {
      th.addEventListener("click", function () {
        var table2 = th.closest("table");
        var idx = Array.prototype.indexOf.call(th.parentNode.children, th);
        var dir = th.dataset.dir === "asc" ? -1 : 1;
        th.dataset.dir = dir === 1 ? "asc" : "desc";
        sortBy(table2, idx, dir);
      });
    });

    Array.prototype.forEach.call(document.querySelectorAll("[data-expand-all]"), function (btn) {
      btn.addEventListener("click", function () {
        var open = btn.dataset.state !== "open";
        Array.prototype.forEach.call(document.querySelectorAll("details.market-detail"), function (d) {
          d.open = open;
        });
        btn.dataset.state = open ? "open" : "closed";
        btn.textContent = open ? "Collapse all markets" : "Expand all markets";
      });
    });
  });
})();
