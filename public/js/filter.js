/* ==========================================================================
   Category filters + text search ("| include") for blog and projects.
   Security (OWASP A03):
   - Filter values come only from data-* attributes hard-coded in the HTML.
   - The URL hash is only honoured if it EXACTLY matches one of those
     hard-coded values (allow-list), so it can never inject anything.
   - Search text is only compared against strings; it is never written
     back into the DOM. All writes use textContent / hidden.
   Progressive enhancement: the toolbar ships [hidden]; without JS every
   item simply stays visible.
   ========================================================================== */
(function () {
  "use strict";

  document.querySelectorAll("[data-filter-group]").forEach(function (group) {
    var bar = group.querySelector(".toolbar");
    if (!bar) return;

    var items = Array.prototype.slice.call(group.querySelectorAll("[data-cat]"));
    var buttons = Array.prototype.slice.call(bar.querySelectorAll(".fbtn"));
    var input = bar.querySelector("input[type='search']");
    var months = group.querySelectorAll("[data-month]");
    var empty = group.querySelector(".empty");
    var status = group.querySelector("[data-status]");
    var allowed = buttons.map(function (b) { return b.getAttribute("data-filter"); });

    var state = { cat: "all", q: "" };

    function apply() {
      var shown = 0;
      var q = state.q;
      items.forEach(function (el) {
        var okCat = state.cat === "all" || el.getAttribute("data-cat") === state.cat;
        var hay = el.getAttribute("data-search") || "";
        var okQ = !q || hay.indexOf(q) !== -1;
        var show = okCat && okQ;
        el.hidden = !show;
        if (show) shown += 1;
      });
      // hide month headings with nothing under them
      months.forEach(function (m) {
        var list = document.getElementById(m.getAttribute("data-month"));
        if (!list) return;
        var any = list.querySelector("[data-cat]:not([hidden])");
        m.hidden = !any;
        list.hidden = !any;
      });
      buttons.forEach(function (b) {
        b.setAttribute("aria-pressed", String(b.getAttribute("data-filter") === state.cat));
      });
      if (empty) empty.hidden = shown !== 0;
      if (status) status.textContent = shown + (shown === 1 ? " entry" : " entries") + " shown";
    }

    buttons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        state.cat = btn.getAttribute("data-filter");
        if (history.replaceState) {
          history.replaceState(null, "", state.cat === "all" ? location.pathname : "#" + state.cat);
        }
        apply();
      });
    });

    if (input) {
      var t = null;
      input.addEventListener("input", function () {
        clearTimeout(t);
        t = setTimeout(function () {
          state.q = input.value.trim().toLowerCase().slice(0, 80);
          apply();
        }, 80);
      });
    }

    // deep link: /blog#sec  (allow-listed values only)
    function fromHash() {
      var h = "";
      try { h = decodeURIComponent(location.hash.slice(1)); } catch (e) { h = ""; }
      if (h && allowed.indexOf(h) !== -1) { state.cat = h; return true; }
      return false;
    }
    fromHash();
    window.addEventListener("hashchange", function () { if (fromHash()) apply(); });

    bar.hidden = false;
    apply();
  });
})();
