// Progressive enhancement only: every table is in the HTML and readable without this file.
(function () {
  "use strict";
  var d = document, root = d.documentElement;
  function all(sel, el) { return Array.prototype.slice.call((el || d).querySelectorAll(sel)); }
  function store(k, v) {
    try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; }
  }

  // Theme: auto follows the system; light and dark are remembered on this device.
  function theme(t) {
    if (t === "light" || t === "dark") root.setAttribute("data-theme", t); else { root.removeAttribute("data-theme"); t = "auto"; }
    all("[data-theme-set]").forEach(function (b) { b.setAttribute("aria-pressed", String(b.getAttribute("data-theme-set") === t)); });
  }
  theme(store("theme"));
  all("[data-theme-set]").forEach(function (b) {
    b.addEventListener("click", function () { var t = b.getAttribute("data-theme-set"); store("theme", t); theme(t); });
  });

  // Condition toggles: one table visible per study.
  all(".seg[data-panels]").forEach(function (seg) {
    var btns = all("button", seg);
    function show(id) {
      btns.forEach(function (b) {
        var on = b.getAttribute("data-show") === id, p = d.getElementById(b.getAttribute("data-show"));
        b.setAttribute("aria-pressed", String(on));
        if (p) p.hidden = !on;
      });
    }
    btns.forEach(function (b) { b.addEventListener("click", function () { show(b.getAttribute("data-show")); }); });
    if (btns.length) show(btns[0].getAttribute("data-show"));
  });

  // Column sort: descending, ascending, then back to the paper's order.
  all("th[data-sort]").forEach(function (th) {
    var btn = d.createElement("button");
    btn.type = "button"; btn.className = "sort";
    while (th.firstChild) btn.appendChild(th.firstChild);
    th.appendChild(btn);
    btn.addEventListener("click", function () {
      var table = th.closest("table"), body = table.tBodies[0], idx = th.cellIndex;
      var rows = all("tr", body), cur = th.getAttribute("aria-sort");
      var next = cur === "descending" ? "ascending" : cur === "ascending" ? null : "descending";
      all("th[aria-sort]", table).forEach(function (o) { o.removeAttribute("aria-sort"); });
      rows.forEach(function (r, i) { if (!r.hasAttribute("data-i")) r.setAttribute("data-i", i); });
      if (next) th.setAttribute("aria-sort", next);
      rows.sort(function (a, b) {
        if (!next) return a.getAttribute("data-i") - b.getAttribute("data-i");
        var x = a.cells[idx].getAttribute("data-v"), y = b.cells[idx].getAttribute("data-v");
        var nx = parseFloat(x), ny = parseFloat(y), c;
        c = isNaN(nx) || isNaN(ny) ? String(x).localeCompare(String(y)) : nx - ny;
        return next === "ascending" ? c : -c;
      });
      rows.forEach(function (r) { body.appendChild(r); });
    });
  });

  // Highlight one model in every table it appears in.
  var hl = d.getElementById("hl");
  if (hl) {
    var mark = function () {
      all("tr[data-model]").forEach(function (r) {
        r.classList.toggle("hl", !!hl.value && r.getAttribute("data-model").split(" ").indexOf(hl.value) !== -1);
      });
    };
    hl.addEventListener("change", mark); mark();
  }

  // Copy buttons for the citation blocks and commands.
  all("[data-copy]").forEach(function (b) {
    b.addEventListener("click", function () {
      var el = d.getElementById(b.getAttribute("data-copy")); if (!el) return;
      var text = el.textContent, label = b.textContent;
      var done = function () { b.textContent = "Copied"; setTimeout(function () { b.textContent = label; }, 1600); };
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, function () {});
      else {
        var r = d.createRange(); r.selectNodeContents(el);
        var s = getSelection(); s.removeAllRanges(); s.addRange(r);
        try { d.execCommand("copy"); done(); } catch (e) {}
        s.removeAllRanges();
      }
    });
  });
})();
