/* ==========================================================================
   CCNP Security flashcards: Leitner spaced repetition, all in the browser.

   Security (OWASP A03 / A05):
   - The cards are the server-rendered list on the page. This file clones those
     nodes (cloneNode) into the study stage; it never parses or writes HTML.
     Every other DOM write is textContent, hidden, or an attribute constant.
   - Progress lives in localStorage under one key (bfl-ccnp-cards). It is read
     defensively: anything that is not the exact expected shape is ignored, so
     a tampered value can't do more than reset your own progress.
   - The URL hash is honoured only if it equals one of the filter buttons'
     hard-coded values (allow-list).
   Progressive enhancement: without JS the full card list stays usable.
   ========================================================================== */
(function () {
  "use strict";

  var app = document.querySelector("[data-fc-app]");
  var list = document.querySelector(".fc-list");
  if (!app || !list) return;

  var KEY = "bfl-ccnp-cards";
  var DAY = 86400000;
  var INTERVAL = [0, 0, 1, 3, 7, 16];          // days until due, by box 1..5
  var today = Math.floor(Date.now() / DAY);

  // ---------- cards from the page ----------
  var cards = Array.prototype.map.call(list.querySelectorAll(".fc-item"), function (li) {
    return {
      id: li.getAttribute("data-id"),
      dom: li.getAttribute("data-dom"),
      obj: li.getAttribute("data-obj"),
      front: li.querySelector(".fc-front"),
      back: li.querySelector(".fc-back")
    };
  }).filter(function (c) { return c.id && c.front && c.back; });
  var byId = {};
  cards.forEach(function (c) { byId[c.id] = c; });

  // ---------- storage (never trusted) ----------
  var store = {};
  var storageOk = true;
  function load() {
    var raw = null;
    try { raw = window.localStorage.getItem(KEY); } catch (e) { storageOk = false; return; }
    if (!raw || raw.length > 200000) return;
    var data;
    try { data = JSON.parse(raw); } catch (e) { return; }
    if (!data || data.v !== 1 || typeof data.c !== "object" || data.c === null) return;
    Object.keys(data.c).forEach(function (id) {
      var r = data.c[id];
      if (byId[id] && Array.isArray(r) && r.length === 2 &&
          r[0] >= 1 && r[0] <= 5 && (r[0] | 0) === r[0] &&
          typeof r[1] === "number" && isFinite(r[1])) {
        store[id] = [r[0], Math.floor(r[1])];
      }
    });
  }
  function save() {
    try { window.localStorage.setItem(KEY, JSON.stringify({ v: 1, c: store })); }
    catch (e) { storageOk = false; }
  }
  load();

  // ---------- elements ----------
  var q = function (sel) { return app.querySelector(sel); };
  var el = {
    stats: q("[data-fc-stats]"),
    boxes: app.querySelectorAll("[data-fc-box]"),
    stage: q("[data-fc-stage]"),
    meta: q("[data-fc-meta]"),
    front: q("[data-fc-q]"),
    back: q("[data-fc-a]"),
    flip: q("[data-fc-flip]"),
    rate: q("[data-fc-rate]"),
    done: q("[data-fc-done]"),
    doneMsg: q("[data-fc-done-msg]"),
    cram: q("[data-fc-cram]"),
    reset: q("[data-fc-reset]"),
    note: q("[data-fc-note]"),
    live: q("[data-fc-live]"),
    card: q("[data-fc-card]")
  };
  var buttons = Array.prototype.slice.call(app.querySelectorAll(".fbtn[data-filter]"));
  var allowed = buttons.filter(function (b) { return !b.disabled; }).map(function (b) { return b.getAttribute("data-filter"); });
  var rateBtns = Array.prototype.slice.call(el.rate.querySelectorAll("[data-grade]"));

  var state = { filter: "all", queue: [], current: null, revealed: false, cram: false, reviewed: 0 };

  function inDeck(c) { return state.filter === "all" || c.dom === state.filter; }
  function boxOf(c) { return store[c.id] ? store[c.id][0] : 0; }
  function isDue(c) { return !store[c.id] || store[c.id][1] <= today; }

  function shuffle(a) {
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var t = a[i]; a[i] = a[j]; a[j] = t;
    }
    return a;
  }

  function plural(n, w) { return n + " " + w + (n === 1 ? "" : "s"); }

  function renderStats() {
    var deck = cards.filter(inDeck);
    var due = 0, fresh = 0, counts = [0, 0, 0, 0, 0, 0];
    deck.forEach(function (c) {
      var b = boxOf(c);
      counts[b] += 1;
      if (!store[c.id]) fresh += 1;
      else if (isDue(c)) due += 1;
    });
    el.stats.textContent = plural(deck.length, "card") + " in deck · " + fresh + " new · " +
      due + " due for review · " + (counts[4] + counts[5]) + " well known";
    el.boxes.forEach(function (b) {
      var n = parseInt(b.getAttribute("data-fc-box"), 10);
      var v = b.querySelector("b");
      if (v) v.textContent = String(counts[n] || 0);
    });
  }

  function intervalLabel(box) {
    var d = INTERVAL[box];
    return d === 0 ? "today" : (d === 1 ? "1 day" : d + " days");
  }

  function nextBox(c, grade) {
    var b = boxOf(c) || 1;
    if (grade === "again") return 1;
    if (grade === "good") return Math.min(5, b + 1);
    return Math.min(5, b + 2);
  }

  function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); }

  function show(c) {
    state.current = c;
    state.revealed = false;
    clear(el.front);
    clear(el.back);
    Array.prototype.forEach.call(c.front.childNodes, function (n) { el.front.appendChild(n.cloneNode(true)); });
    Array.prototype.forEach.call(c.back.childNodes, function (n) { el.back.appendChild(n.cloneNode(true)); });
    var b = boxOf(c);
    el.meta.textContent = c.obj + " · " + (b ? "box " + b + " of 5" : "new card") + " · " +
      plural(state.queue.length, "card") + " left after this";
    el.back.hidden = true;
    el.rate.hidden = true;
    el.flip.hidden = false;
    el.stage.hidden = false;
    el.done.hidden = true;
    // keep keyboard focus on a visible control so Space keeps working card after card
    if (app.contains(document.activeElement) || document.activeElement === document.body) el.flip.focus({ preventScroll: true });
    rateBtns.forEach(function (btn) {
      var hint = btn.querySelector("[data-int]");
      if (hint) hint.textContent = intervalLabel(nextBox(c, btn.getAttribute("data-grade")));
    });
  }

  function reveal() {
    if (!state.current || state.revealed) return;
    state.revealed = true;
    el.back.hidden = false;
    el.flip.hidden = true;
    el.rate.hidden = false;
    rateBtns[1].focus();
  }

  function next() {
    var c = state.queue.shift();
    if (c) { show(c); return; }
    state.current = null;
    el.stage.hidden = true;
    el.done.hidden = false;
    var deck = cards.filter(inDeck);
    var soonest = null;
    deck.forEach(function (x) {
      if (store[x.id] && (soonest === null || store[x.id][1] < soonest)) soonest = store[x.id][1];
    });
    var msg = state.reviewed ? "Session done: " + plural(state.reviewed, "card") + " reviewed. " : "";
    if (soonest !== null && soonest > today) {
      var d = soonest - today;
      msg += "Nothing is due in this deck. The next review is in " + plural(d, "day") + ".";
    } else {
      msg += "Nothing left in the queue.";
    }
    el.doneMsg.textContent = msg;
    el.cram.focus();
  }

  function start(cram) {
    state.cram = cram;
    state.reviewed = 0;
    var deck = cards.filter(inDeck);
    var pool = cram ? deck.slice() : deck.filter(isDue);
    // reviews first (oldest due), then new cards in random order
    var reviews = shuffle(pool.filter(function (c) { return store[c.id]; }))
      .sort(function (a, b) { return store[a.id][1] - store[b.id][1]; });
    var fresh = shuffle(pool.filter(function (c) { return !store[c.id]; }));
    state.queue = reviews.concat(fresh);
    renderStats();
    next();
  }

  function grade(g) {
    var c = state.current;
    if (!c || !state.revealed) return;
    var b = nextBox(c, g);
    store[c.id] = [b, today + INTERVAL[b]];
    save();
    state.reviewed += 1;
    if (g === "again") state.queue.push(c);      // see it again this session
    if (el.live) el.live.textContent = "Saved. Card moves to box " + b + ".";
    renderStats();
    next();
  }

  function setFilter(f) {
    if (allowed.indexOf(f) === -1) f = "all";
    state.filter = f;
    buttons.forEach(function (b) { b.setAttribute("aria-pressed", String(b.getAttribute("data-filter") === f)); });
    start(false);
  }

  // ---------- events ----------
  buttons.forEach(function (b) {
    b.addEventListener("click", function () {
      if (b.disabled) return;
      var f = b.getAttribute("data-filter");
      if (history.replaceState) history.replaceState(null, "", f === "all" ? location.pathname : "#" + f);
      setFilter(f);
    });
  });
  el.flip.addEventListener("click", reveal);
  rateBtns.forEach(function (btn) {
    btn.addEventListener("click", function () { grade(btn.getAttribute("data-grade")); });
  });
  el.cram.addEventListener("click", function () { start(true); });

  var armed = false, armTimer = null;
  el.reset.addEventListener("click", function () {
    if (!armed) {
      armed = true;
      el.reset.textContent = "press again to erase all flashcard progress";
      armTimer = setTimeout(function () { armed = false; el.reset.textContent = "reset progress"; }, 4000);
      return;
    }
    clearTimeout(armTimer);
    armed = false;
    store = {};
    try { window.localStorage.removeItem(KEY); } catch (e) { /* blocked: nothing stored anyway */ }
    el.reset.textContent = "reset progress";
    if (el.live) el.live.textContent = "Progress erased.";
    start(false);
  });

  document.addEventListener("keydown", function (e) {
    if (e.altKey || e.ctrlKey || e.metaKey) return;
    var t = e.target;
    if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable)) return;
    if (!state.current || el.stage.hidden) return;
    if (t && t.closest && t.closest(".fc-list")) return;    // browsing the list below
    if (!state.revealed && (e.key === " " || e.key === "Enter") && (t === document.body || app.contains(t))) {
      if (t && t.tagName === "BUTTON" && t !== el.flip) return;
      e.preventDefault();
      reveal();
    } else if (state.revealed && (e.key === "1" || e.key === "2" || e.key === "3")) {
      e.preventDefault();
      grade(["again", "good", "easy"][parseInt(e.key, 10) - 1]);
    }
  });

  window.addEventListener("hashchange", function () {
    var h = "";
    try { h = decodeURIComponent(location.hash.slice(1)); } catch (e) { h = ""; }
    if (allowed.indexOf(h) !== -1) setFilter(h);
  });

  // ---------- go ----------
  if (!storageOk && el.note) el.note.textContent = "Your browser is blocking local storage, so progress will only last until you close this tab.";
  var h0 = "";
  try { h0 = decodeURIComponent(location.hash.slice(1)); } catch (e) { h0 = ""; }
  app.hidden = false;
  setFilter(allowed.indexOf(h0) !== -1 ? h0 : "all");
})();
