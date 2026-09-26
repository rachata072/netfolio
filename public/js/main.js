/* ==========================================================================
   breakfixlearn v2 - site behaviour (progressive enhancement only).
   Security (OWASP A03): no innerHTML anywhere. Every DOM write is
   textContent, classList, or an attribute set to a constant. Nothing is
   read from the URL, storage, or user input in this file.
   ========================================================================== */
(function () {
  "use strict";

  var doc = document.documentElement;
  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  doc.classList.add("js");

  /* ---------- blog facility legend: start collapsed on phones ---------- */
  var fac = document.querySelector("details.facilities");
  if (fac && window.matchMedia("(max-width: 48rem)").matches) fac.removeAttribute("open");

  /* ---------- reveal on scroll ---------- */
  var rv = document.querySelectorAll(".rv");
  if (rv.length && "IntersectionObserver" in window && !reduced) {
    var vh = window.innerHeight;
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
      });
    }, { rootMargin: "0px 0px -8% 0px" });
    rv.forEach(function (el) {
      // anything already on screen is shown in the same frame (no flash)
      if (el.getBoundingClientRect().top < vh) el.classList.add("in");
      else io.observe(el);
    });
  } else {
    rv.forEach(function (el) { el.classList.add("in"); });
  }

  /* ---------- reading progress (post pages) ---------- */
  var bar = document.querySelector(".progress");
  var article = document.querySelector(".prose");
  if (bar && article) {
    var ticking = false;
    var update = function () {
      var r = article.getBoundingClientRect();
      var total = r.height - window.innerHeight;
      var p = total > 0 ? Math.min(1, Math.max(0, -r.top / total)) : 1;
      bar.style.transform = "scaleX(" + p.toFixed(4) + ")"; // CSSOM, not inline markup: CSP-safe
      ticking = false;
    };
    window.addEventListener("scroll", function () {
      if (!ticking) { ticking = true; window.requestAnimationFrame(update); }
    }, { passive: true });
    update();
  }

  /* ---------- table of contents: highlight current section ---------- */
  var tocLinks = document.querySelectorAll(".toc a[href^='#']");
  if (tocLinks.length && "IntersectionObserver" in window) {
    var map = {};
    tocLinks.forEach(function (a) { map[a.getAttribute("href").slice(1)] = a; });
    var current = null;
    var setCurrent = function (id) {
      if (current === id || !map[id]) return;
      if (current && map[current]) map[current].removeAttribute("aria-current");
      map[id].setAttribute("aria-current", "true");
      current = id;
    };
    var heads = document.querySelectorAll(".prose h2[id]");
    var tocIO = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { if (e.isIntersecting) setCurrent(e.target.id); });
    }, { rootMargin: "0px 0px -70% 0px" });
    heads.forEach(function (h) { tocIO.observe(h); });
  }

  /* ---------- copy buttons on code blocks ---------- */
  if (navigator.clipboard && window.isSecureContext) {
    document.querySelectorAll(".prose pre").forEach(function (pre) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "copy";
      btn.textContent = "copy";
      btn.setAttribute("aria-label", "Copy code to clipboard");
      btn.addEventListener("click", function () {
        var code = pre.querySelector("code") || pre;
        navigator.clipboard.writeText(code.textContent).then(function () {
          btn.textContent = "copied";
          btn.classList.add("ok");
          setTimeout(function () { btn.textContent = "copy"; btn.classList.remove("ok"); }, 1600);
        }, function () {
          btn.textContent = "error";
        });
      });
      pre.appendChild(btn);
    });
  }
})();
