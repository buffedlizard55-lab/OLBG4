/* OLBG4 master dashboard — client-side filtering over data/master.json.
   The page works without this file for the static content; the table is the only
   part that needs JavaScript, and it says so if the fetch fails. */
(function () {
  "use strict";

  var DATA_PATH = document.body.getAttribute("data-root") || ".";
  var state = { sport: "", conf: "", verify: "", market: "", q: "", showPast: false, showNotes: false };

  var el = {
    body: document.getElementById("rows-body"),
    count: document.getElementById("row-count"),
    sport: document.getElementById("f-sport"),
    conf: document.getElementById("f-conf"),
    verify: document.getElementById("f-verify"),
    market: document.getElementById("f-market"),
    q: document.getElementById("f-q"),
    past: document.getElementById("f-past"),
    notes: document.getElementById("f-notes")
  };
  if (!el.body) return;

  function esc(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function confClass(c) {
    return c === "High" ? "high" : c === "Medium" ? "medium" : c === "Low" ? "low" : "none";
  }

  function marketsCell(r) {
    var bits = [];
    if (r.win && r.win.odds) {
      var prices = Object.keys(r.win.odds).map(function (k) { return k + " " + r.win.odds[k]; });
      if (prices.length) bits.push("Win: " + prices.join(" / "));
    }
    if (r.handicap) bits.push("Handicap: " + r.handicap);
    if (r.total) bits.push("Total: " + r.total);
    if (!bits.length) return '<span class="small">no market originated</span>';
    return bits.map(function (b) { return esc(b); }).join("<br>");
  }

  function flagsCell(r) {
    var f = r.flags || [];
    if (!f.length) return "";
    var shown = f.slice(0, 3).map(function (x) { return '<span class="f">' + esc(x.kind) + "</span>"; }).join("");
    var more = f.length > 3 ? '<span class="small"> +' + (f.length - 3) + " more</span>" : "";
    return '<div class="flags">' + shown + more + "</div>";
  }

  function verifyBadge(r) {
    if (r.live_contradicted) return '<span class="badge flag">contradicted</span>';
    if (r.live_verified) return '<span class="badge check">re-checked live</span>';
    if (r.verified) return '<span class="badge ok">official source</span>';
    if (r.source_tier === "olbg") return '<span class="badge flag">OLBG only</span>';
    if (r.source_tier === "secondary") return '<span class="badge flag">secondary source</span>';
    return '<span class="badge flag">unverified</span>';
  }

  function passes(r) {
    if (!r.in_scope) return false;            // out-of-scope rows live on the Flagged page only
    if (!state.showNotes && r.row_type !== "fixture") return false;
    if (!state.showPast && r.status === "played-before-cutoff") return false;
    if (state.sport && r.sport_slug !== state.sport) return false;
    if (state.conf && (r.confidence || "none") !== state.conf) return false;
    if (state.verify === "official" && !r.verified) return false;
    if (state.verify === "live" && !r.live_verified) return false;
    if (state.verify === "flagged" && !(r.flags || []).length) return false;
    if (state.market === "win" && !(r.win && r.win.odds)) return false;
    if (state.market === "handicap" && !r.handicap) return false;
    if (state.market === "total" && !r.total) return false;
    if (state.q) {
      var hay = [r.home, r.away, r.pick, r.competition, r.sport, r.source_domain].join(" ").toLowerCase();
      if (hay.indexOf(state.q.toLowerCase()) === -1) return false;
    }
    return true;
  }

  function row(r) {
    var teams = esc(r.home) + ' <span class="vs">vs</span> ' + esc(r.away);
    var pick = r.pick ? esc(r.pick) : '<span class="small">no pick</span>';
    var market = r.pick_market && r.pick ? '<div class="small">' + esc(r.pick_market) + "</div>" : "";
    var src = r.source_url
      ? '<a href="' + esc(r.source_url) + '" rel="noopener nofollow" target="_blank">source</a><span class="dom">' + esc(r.source_domain) + "</span>"
      : '<span class="small">none recorded</span>';
    return "<tr>" +
      '<td class="num">' + esc(r.date || "—") + '</td>' +
      '<td><a href="' + DATA_PATH + "/sports/" + esc(r.sport_slug) + '.html">' + esc(r.sport) + "</a></td>" +
      '<td class="teams">' + teams + (r.competition ? '<span class="vs">' + esc(r.competition).slice(0, 70) + "</span>" : "") + "</td>" +
      '<td class="pick">' + pick + market + "</td>" +
      '<td><span class="badge ' + confClass(r.confidence) + '">' + esc(r.confidence || "none") + "</span></td>" +
      '<td class="markets">' + marketsCell(r) + "</td>" +
      '<td class="src">' + src + "</td>" +
      '<td>' + verifyBadge(r) + flagsCell(r) + "</td>" +
      "</tr>";
  }

  function render() {
    var rows = (window.__ROWS__ || []).filter(passes);
    el.body.innerHTML = rows.map(row).join("");
    if (el.count) {
      el.count.textContent = rows.length + " row" + (rows.length === 1 ? "" : "s") + " shown" +
        (window.__ROWS__ ? " of " + window.__ROWS__.length + " in the master file" : "");
    }
  }

  function bind(node, key, event) {
    if (!node) return;
    node.addEventListener(event || "change", function () {
      state[key] = node.type === "checkbox" ? node.checked : node.value;
      render();
    });
  }

  bind(el.sport, "sport");
  bind(el.conf, "conf");
  bind(el.verify, "verify");
  bind(el.market, "market");
  bind(el.past, "showPast");
  bind(el.notes, "showNotes");
  bind(el.q, "q", "input");

  fetch(DATA_PATH + "/data/master.json")
    .then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    })
    .then(function (d) {
      window.__ROWS__ = d.rows;
      render();
    })
    .catch(function (e) {
      el.body.innerHTML = '<tr><td colspan="8" class="small">Could not load data/master.json (' +
        esc(e.message) + "). The table needs JavaScript and a served page; open the site over http(s) rather than file://.</td></tr>";
    });
})();
