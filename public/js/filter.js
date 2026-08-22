/* ============================================================
   Category filters, styled as IOS pipe filters.
   Security notes (OWASP A03):
   - Filter values come only from data attributes hard-coded in
     the HTML - never from the URL or user input.
   - DOM updates use textContent / hidden only. No innerHTML.
   Progressive enhancement:
   - The filter bar ships with [hidden]; JS reveals it. Without
     JS, every post/project simply stays visible.
   ============================================================ */
(function () {
  "use strict";

  document.querySelectorAll("[data-filter-group]").forEach(function (group) {
    var bar = group.querySelector(".filter-bar");
    if (!bar) return;

    var items = group.querySelectorAll("[data-cat]");
    var buttons = bar.querySelectorAll(".filter-btn");
    var headingSuffix = group.querySelector(".filter-current");
    var emptyMsg = group.querySelector(".filter-empty");

    function apply(filter, activeBtn) {
      var shown = 0;
      buttons.forEach(function (b) {
        b.setAttribute("aria-pressed", String(b === activeBtn));
      });
      items.forEach(function (el) {
        var match = filter === "all" || el.getAttribute("data-cat") === filter;
        el.hidden = !match;
        if (match) shown += 1;
      });
      if (headingSuffix) {
        headingSuffix.textContent =
          filter === "all" ? "" : " | include " + filter.toUpperCase();
      }
      if (emptyMsg) emptyMsg.hidden = shown !== 0;
    }

    buttons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        apply(btn.getAttribute("data-filter"), btn);
      });
    });

    bar.hidden = false; // JS is running - reveal the controls
  });
})();
