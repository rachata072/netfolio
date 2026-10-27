/* ==========================================================================
   CCNP Security mock exam. Runs entirely in the browser; stores nothing.

   Security (OWASP A03 / A08):
   - The question bank is fetched from this origin only (/ccnp-security/data/,
     CSP connect-src 'self') and validated field by field before use.
   - All text is written with textContent. `code` and **bold** in question text
     become <code>/<strong> elements created with createElement, never HTML.
   - Review links are used only if they are site-relative paths under
     /ccnp-security/ (allow-list); anything else falls back to the hub.
   - The URL hash (#d2) only pre-selects a domain checkbox that already exists.
   ========================================================================== */
(function () {
  "use strict";

  var app = document.querySelector("[data-exam-app]");
  if (!app) return;
  var DATA_URL = "/ccnp-security/data/questions.json";
  var SECONDS_PER_Q = 72;            // the real exam: about 120 minutes for about 100 items

  var $ = function (s) { return app.querySelector(s); };
  var el = {
    setup: $("[data-ex-setup]"), run: $("[data-ex-run]"), result: $("[data-ex-result]"),
    start: $("[data-ex-start]"), err: $("[data-ex-err]"), plan: $("[data-ex-plan]"),
    pos: $("[data-ex-pos]"), obj: $("[data-ex-obj]"), timer: $("[data-ex-timer]"), prog: $("[data-ex-prog]"),
    stem: $("[data-ex-stem]"), hint: $("[data-ex-hint]"), opts: $("[data-ex-opts]"),
    fb: $("[data-ex-fb]"), verdict: $("[data-ex-verdict]"), expl: $("[data-ex-expl]"), ref: $("[data-ex-ref]"),
    check: $("[data-ex-check]"), next: $("[data-ex-next]"), end: $("[data-ex-end]"),
    score: $("[data-ex-score]"), summary: $("[data-ex-summary]"), doms: $("[data-ex-doms]"),
    review: $("[data-ex-review]"), missed: $("[data-ex-missed]"), again: $("[data-ex-again]"), fresh: $("[data-ex-new]"),
    live: $("[data-ex-live]")
  };

  var bank = null;
  var exam = null;

  // ---------- helpers ----------
  function clear(n) { while (n.firstChild) n.removeChild(n.firstChild); }
  function make(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text;
    return n;
  }
  // `code` and **bold** only, built as elements
  function rich(node, text) {
    clear(node);
    String(text).split(/(`[^`]+`|\*\*[^*]+\*\*)/).forEach(function (part) {
      if (!part) return;
      if (part.charAt(0) === "`" && part.length > 2) node.appendChild(make("code", "", part.slice(1, -1)));
      else if (part.indexOf("**") === 0 && part.length > 4) node.appendChild(make("strong", "", part.slice(2, -2)));
      else node.appendChild(document.createTextNode(part));
    });
    return node;
  }
  function shuffle(a) {
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var t = a[i]; a[i] = a[j]; a[j] = t;
    }
    return a;
  }
  function safeRef(u) {
    return (typeof u === "string" && /^\/ccnp-security\/[a-z0-9-]+(#[a-z0-9-]+)?$/.test(u)) ? u : "/ccnp-security";
  }
  function mmss(s) {
    s = Math.max(0, Math.round(s));
    var m = Math.floor(s / 60), r = s % 60;
    return m + ":" + (r < 10 ? "0" : "") + r;
  }
  function word(n, w) { return n + " " + w + (n === 1 ? "" : "s"); }
  var NUM = ["zero", "one", "two", "three", "four", "five", "six"];

  // ---------- data ----------
  function valid(q) {
    return q && typeof q.id === "string" && typeof q.obj === "string" && /^[1-6]\.\d{1,2}$/.test(q.obj) &&
      (q.type === "single" || q.type === "multi") && typeof q.stem === "string" &&
      Array.isArray(q.options) && q.options.length >= 3 && q.options.length <= 6 &&
      q.options.every(function (o) { return typeof o === "string"; }) &&
      Array.isArray(q.answer) && q.answer.length >= 1 &&
      q.answer.every(function (a) { return a === (a | 0) && a >= 0 && a < q.options.length; }) &&
      typeof q.explanation === "string";
  }
  function loadBank() {
    if (bank) return Promise.resolve(bank);
    return fetch(DATA_URL, { credentials: "same-origin" }).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    }).then(function (d) {
      if (!d || !Array.isArray(d.questions) || !Array.isArray(d.domains)) throw new Error("bad data");
      bank = { domains: d.domains, questions: d.questions.filter(valid) };
      return bank;
    });
  }

  // ---------- setup ----------
  function settings() {
    var f = el.setup;
    var mode = (f.querySelector("input[name='mode']:checked") || {}).value || "exam";
    var len = (f.querySelector("input[name='len']:checked") || {}).value || "25";
    var doms = Array.prototype.filter.call(f.querySelectorAll("input[name='dom']"), function (c) { return c.checked && !c.disabled; })
      .map(function (c) { return c.value; });
    var timed = !!(f.querySelector("input[name='timed']") || {}).checked;
    return { mode: mode, len: len === "all" ? Infinity : parseInt(len, 10), doms: doms, timed: timed && mode === "exam" };
  }

  // blueprint-weighted pick across the chosen domains, capped by what the bank holds
  function pick(s) {
    var pools = {}, weights = {};
    bank.domains.forEach(function (d) { weights[String(d.id)] = d.weight; });
    s.doms.forEach(function (d) { pools[d] = shuffle(bank.questions.filter(function (q) { return q.obj.split(".")[0] === d; })); });
    var avail = s.doms.filter(function (d) { return pools[d].length; });
    var total = avail.reduce(function (n, d) { return n + pools[d].length; }, 0);
    var want = Math.min(s.len, total);
    var take = {}, left = want;
    var wsum = avail.reduce(function (n, d) { return n + (weights[d] || 1); }, 0);
    avail.forEach(function (d) { take[d] = Math.min(pools[d].length, Math.floor(want * (weights[d] || 1) / wsum)); left -= take[d]; });
    // hand out the remainder to domains that still have questions, heaviest first
    var order = avail.slice().sort(function (a, b) { return (weights[b] || 1) - (weights[a] || 1); });
    while (left > 0) {
      var moved = false;
      order.forEach(function (d) { if (left > 0 && take[d] < pools[d].length) { take[d] += 1; left -= 1; moved = true; } });
      if (!moved) break;
    }
    var out = [];
    avail.forEach(function (d) { out = out.concat(pools[d].slice(0, take[d])); });
    return shuffle(out).map(function (q) {
      var idx = shuffle(q.options.map(function (_, i) { return i; }));
      return {
        q: q,
        order: idx,                                   // display position -> original index
        correct: q.answer.map(function (a) { return idx.indexOf(a); }).sort(),
        picked: [], checked: false
      };
    });
  }

  function updatePlan() {
    if (!el.plan) return;
    var s = settings();
    if (!s.doms.length) { el.plan.textContent = "Pick at least one domain."; el.start.disabled = true; return; }
    el.start.disabled = false;
    if (!bank) { el.plan.textContent = ""; return; }
    var n = bank.questions.filter(function (q) { return s.doms.indexOf(q.obj.split(".")[0]) !== -1; }).length;
    var len = Math.min(s.len, n);
    el.plan.textContent = word(len, "question") + (s.timed ? ", " + mmss(len * SECONDS_PER_Q) + " on the clock" : ", untimed") +
      (s.mode === "exam" ? ", one way, results at the end." : ", feedback after every answer.") +
      (len < s.len && s.len !== Infinity ? " The bank only has " + n + " for the domains you picked so far." : "");
  }

  // ---------- run ----------
  var tick = null;
  function startExam(e) {
    if (e) e.preventDefault();
    var s = settings();
    if (!s.doms.length) { updatePlan(); return; }
    el.start.disabled = true;
    el.err.hidden = true;
    loadBank().then(function () {
      var items = pick(s);
      el.start.disabled = false;
      if (!items.length) { el.err.textContent = "No questions in the bank for that selection yet."; el.err.hidden = false; return; }
      exam = { s: s, items: items, i: 0, started: Date.now(), limit: s.timed ? items.length * SECONDS_PER_Q : 0, ended: false };
      el.setup.hidden = true;
      el.result.hidden = true;
      el.run.hidden = false;
      el.end.textContent = "end exam";
      if (s.timed) {
        el.timer.hidden = false;
        clearInterval(tick);
        tick = setInterval(updateTimer, 1000);
        updateTimer();
      } else {
        el.timer.hidden = true;
      }
      render();
      el.stem.focus();
    }, function () {
      el.start.disabled = false;
      el.err.textContent = "Could not load the question bank. Check your connection and try again.";
      el.err.hidden = false;
    });
  }

  function remaining() { return exam.limit - (Date.now() - exam.started) / 1000; }
  function updateTimer() {
    if (!exam || !exam.limit || exam.ended) return;
    var r = remaining();
    el.timer.textContent = mmss(r) + " left";
    el.timer.classList.toggle("low", r < 300);
    if (r <= 0) { if (el.live) el.live.textContent = "Time is up."; finish(); }
  }

  function render() {
    var it = exam.items[exam.i], q = it.q, n = exam.items.length;
    el.pos.textContent = "Question " + (exam.i + 1) + " of " + n;
    el.obj.textContent = "topic " + q.obj;
    el.prog.style.transform = "scaleX(" + (exam.i / n).toFixed(4) + ")";   // CSSOM: CSP-safe
    rich(el.stem, q.stem);
    var k = q.answer.length;
    el.hint.textContent = q.type === "multi" ? "Choose " + (NUM[k] || k) + "." : "Choose one.";
    clear(el.opts);
    var type = q.type === "multi" ? "checkbox" : "radio";
    it.order.forEach(function (orig, pos) {
      var lab = make("label", "opt ex-opt");
      var inp = document.createElement("input");
      inp.type = type;
      inp.name = "ans";
      inp.value = String(pos);
      inp.checked = it.picked.indexOf(pos) !== -1;
      inp.addEventListener("change", function () { onPick(it, k); });
      var letter = make("span", "ex-l", String.fromCharCode(65 + pos));
      var txt = rich(make("span", "ex-t"), q.options[orig]);
      lab.appendChild(inp); lab.appendChild(letter); lab.appendChild(txt);
      el.opts.appendChild(lab);
    });
    onPick(it, k, true);
    el.fb.hidden = true;
    var practice = exam.s.mode === "practice";
    el.check.hidden = !practice;
    el.next.hidden = practice;
    el.next.textContent = exam.i + 1 === n ? "finish" : "next";
    if (practice && it.checked) showFeedback(it);
  }

  function onPick(it, k, silent) {
    var inputs = Array.prototype.slice.call(el.opts.querySelectorAll("input"));
    it.picked = inputs.filter(function (x) { return x.checked; }).map(function (x) { return parseInt(x.value, 10); });
    if (it.q.type === "multi") {
      // like the real exam: you can't tick more than the question asks for
      inputs.forEach(function (x) { x.disabled = it.checked || (!x.checked && it.picked.length >= k); });
    } else {
      inputs.forEach(function (x) { x.disabled = it.checked; });
    }
    el.check.disabled = it.picked.length !== k || it.checked;
    if (!silent && el.live && it.q.type === "multi") el.live.textContent = it.picked.length + " of " + k + " selected";
  }

  function isRight(it) {
    var p = it.picked.slice().sort();
    return p.length === it.correct.length && p.every(function (v, i) { return v === it.correct[i]; });
  }

  function showFeedback(it) {
    var ok = isRight(it);
    el.verdict.textContent = ok ? "Correct." : "Not quite. Correct answer: " + it.correct.map(function (c) { return String.fromCharCode(65 + c); }).join(", ") + ".";
    el.verdict.className = "ex-verdict " + (ok ? "ok" : "bad");
    rich(el.expl, it.q.explanation);
    el.ref.setAttribute("href", safeRef(it.q.ref));
    el.ref.textContent = (typeof it.q.ref_label === "string" ? it.q.ref_label : "Review this in the notes") + " →";
    Array.prototype.forEach.call(el.opts.querySelectorAll(".ex-opt"), function (lab, pos) {
      lab.classList.toggle("is-right", it.correct.indexOf(pos) !== -1);
      lab.classList.toggle("is-wrong", it.picked.indexOf(pos) !== -1 && it.correct.indexOf(pos) === -1);
    });
    el.fb.hidden = false;
    el.check.hidden = true;
    el.next.hidden = false;
    el.next.focus();
  }

  el.check.addEventListener("click", function () {
    var it = exam.items[exam.i];
    if (it.picked.length !== it.q.answer.length) return;
    it.checked = true;
    onPick(it, it.q.answer.length, true);
    showFeedback(it);
  });
  el.next.addEventListener("click", function () {
    if (exam.i + 1 >= exam.items.length) { finish(); return; }
    exam.i += 1;
    render();
    el.stem.focus();
  });
  var endArmed = false, endTimer = null;
  el.end.addEventListener("click", function () {
    if (!endArmed) {
      endArmed = true;
      el.end.textContent = "press again to end and score";
      endTimer = setTimeout(function () { endArmed = false; el.end.textContent = "end exam"; }, 4000);
      return;
    }
    clearTimeout(endTimer);
    endArmed = false;
    finish();
  });

  // ---------- results ----------
  function finish() {
    if (!exam || exam.ended) return;
    exam.ended = true;
    clearInterval(tick);
    var used = (Date.now() - exam.started) / 1000;
    var total = exam.items.length, right = 0, per = {};
    exam.items.forEach(function (it) {
      var d = it.q.obj.split(".")[0];
      per[d] = per[d] || { n: 0, ok: 0 };
      per[d].n += 1;
      it.ok = isRight(it);
      if (it.ok) { right += 1; per[d].ok += 1; }
    });
    var pct = Math.round(100 * right / total);
    el.run.hidden = true;
    el.result.hidden = false;
    el.score.textContent = pct + "%";
    el.score.className = "ex-score " + (pct >= 85 ? "ok" : pct >= 70 ? "mid" : "bad");
    el.summary.textContent = right + " of " + total + " correct · " + mmss(used) + " used" +
      (exam.s.timed ? " of " + mmss(exam.limit) : "") + " · " + (exam.s.mode === "exam" ? "exam mode" : "practice mode");

    clear(el.doms);
    bank.domains.forEach(function (d) {
      var p = per[String(d.id)];
      if (!p) return;
      var row = make("li", "ex-dom");
      var head = make("span", "ex-dn", d.id + ".0 " + d.name);
      var val = make("span", "ex-dv", p.ok + "/" + p.n);
      var bar = make("span", "ex-db");
      var fill = make("span", "ex-df");
      fill.style.transform = "scaleX(" + (p.ok / p.n).toFixed(4) + ")";
      bar.appendChild(fill);
      row.appendChild(head); row.appendChild(val); row.appendChild(bar);
      el.doms.appendChild(row);
    });

    clear(el.review);
    exam.items.forEach(function (it, i) {
      var li = make("li", "ex-rev " + (it.ok ? "ok" : "bad"));
      li.setAttribute("data-ok", it.ok ? "1" : "0");
      var top = make("p", "ex-rev-top");
      top.appendChild(make("span", "st " + (it.ok ? "st-up" : "st-admin"), it.ok ? "correct" : (it.picked.length ? "incorrect" : "unanswered")));
      top.appendChild(make("span", "ex-rev-n", "Q" + (i + 1) + " · topic " + it.q.obj));
      li.appendChild(top);
      li.appendChild(rich(make("p", "ex-rev-stem"), it.q.stem));
      var ol = make("ol", "ex-rev-opts");
      it.order.forEach(function (orig, pos) {
        var o = make("li");
        var mark = it.correct.indexOf(pos) !== -1 ? "is-right" : (it.picked.indexOf(pos) !== -1 ? "is-wrong" : "");
        if (mark) o.className = mark;
        o.appendChild(make("span", "ex-l", String.fromCharCode(65 + pos)));
        o.appendChild(rich(make("span"), it.q.options[orig]));
        if (it.picked.indexOf(pos) !== -1) o.appendChild(make("span", "ex-you", "your answer"));
        ol.appendChild(o);
      });
      li.appendChild(ol);
      li.appendChild(rich(make("p", "ex-rev-expl"), it.q.explanation));
      var a = make("a", "ex-rev-ref", "review in the notes →");
      a.setAttribute("href", safeRef(it.q.ref));
      li.appendChild(a);
      el.review.appendChild(li);
    });
    el.missed.checked = false;
    applyMissed();
    el.score.focus();
    window.scrollTo(0, app.getBoundingClientRect().top + window.pageYOffset - 80);
  }

  function applyMissed() {
    var only = el.missed.checked;
    Array.prototype.forEach.call(el.review.children, function (li) { li.hidden = only && li.getAttribute("data-ok") === "1"; });
  }
  el.missed.addEventListener("change", applyMissed);

  el.again.addEventListener("click", function () {
    // same questions, fresh answers and a fresh option order
    exam.items.forEach(function (it) {
      it.order = shuffle(it.order.slice());
      it.correct = it.q.answer.map(function (a) { return it.order.indexOf(a); }).sort();
      it.picked = []; it.checked = false;
    });
    exam.items = shuffle(exam.items);
    exam.i = 0; exam.started = Date.now(); exam.ended = false;
    el.result.hidden = true; el.run.hidden = false;
    if (exam.limit) { clearInterval(tick); tick = setInterval(updateTimer, 1000); updateTimer(); }
    render();
    el.stem.focus();
  });
  el.fresh.addEventListener("click", function () {
    exam = null;
    el.result.hidden = true;
    el.setup.hidden = false;
    updatePlan();
    el.start.focus();
  });

  // ---------- go ----------
  el.setup.addEventListener("submit", startExam);
  el.setup.addEventListener("change", function () {
    var timed = el.setup.querySelector("input[name='timed']");
    var mode = (el.setup.querySelector("input[name='mode']:checked") || {}).value;
    if (timed) timed.disabled = mode !== "exam";
    updatePlan();
  });
  var h = "";
  try { h = decodeURIComponent(location.hash.slice(1)); } catch (e) { h = ""; }
  if (/^d[1-6]$/.test(h)) {
    var target = el.setup.querySelector("input[name='dom'][value='" + h.slice(1) + "']");
    if (target && !target.disabled) {
      el.setup.querySelectorAll("input[name='dom']").forEach(function (c) { c.checked = c === target; });
    }
  }
  el.setup.hidden = false;
  updatePlan();
  loadBank().then(updatePlan, function () { /* reported when the user presses start */ });
})();
