/* ============================================================
   Terminal hero animation.
   Security notes (OWASP A03 Injection / XSS):
   - All rendered content is a hard-coded constant below.
   - Nothing from the URL, query string, or user input is ever
     written to the DOM. If you later render dynamic data, use
     document.createTextNode / textContent - never innerHTML.
   ============================================================ */
(function () {
  "use strict";

  var out = document.getElementById("terminal-output");
  if (!out) return;

  // [cssClass, text] pairs. Edit your details here.
  var LINES = [
    [["prompt", "edge-router>"], ["cmd", " enable"]],
    [["prompt", "edge-router#"], ["cmd", " show portfolio brief"]],
    [["key", "Name       : "], ["val", "Trey"]],
    [["key", "Focus      : "], ["val", "Network Engineering \u00B7 Cybersecurity"]],
    [["key", "Certs      : "], ["val", "CCNA"]],
    [["key", "Learning   : "], ["val", "Python for network automation"]],
    [["key", "Location   : "], ["val", "Vancouver, BC"]],
    [["key", "Status     : "], ["up", "up/up - open to opportunities"]]
  ];

  function span(cls, text) {
    var s = document.createElement("span");
    s.className = cls;
    s.appendChild(document.createTextNode(text)); // safe: text node only
    return s;
  }

  function renderInstant() {
    out.textContent = "";
    LINES.forEach(function (line, i) {
      line.forEach(function (part) { out.appendChild(span(part[0], part[1])); });
      if (i < LINES.length - 1) out.appendChild(document.createTextNode("\n"));
    });
    out.appendChild(document.createTextNode("\n"));
    out.appendChild(span("prompt", "edge-router#"));
    out.appendChild(document.createTextNode(" "));
    out.appendChild(span("cursor", ""));
  }

  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduced) { renderInstant(); return; }

  // Typed animation
  var cursor = span("cursor", "");
  out.textContent = "";
  out.appendChild(cursor);

  var li = 0, pi = 0, ci = 0;
  var current = null;

  function step() {
    if (li >= LINES.length) {
      out.insertBefore(document.createTextNode("\n"), cursor);
      out.insertBefore(span("prompt", "edge-router#"), cursor);
      out.insertBefore(document.createTextNode(" "), cursor);
      return; // done - cursor keeps blinking
    }

    var line = LINES[li];
    var part = line[pi];

    if (ci === 0) {
      current = span(part[0], "");
      out.insertBefore(current, cursor);
    }

    // Command lines type char-by-char; output lines appear whole,
    // like a real router printing its response.
    var isCommand = li < 2;
    if (isCommand) {
      ci += 1;
      current.textContent = part[1].slice(0, ci);
      if (ci < part[1].length) { setTimeout(step, 34); return; }
    } else {
      current.textContent = part[1];
      ci = part[1].length;
    }

    // part finished
    ci = 0;
    pi += 1;
    if (pi >= line.length) {
      pi = 0;
      li += 1;
      out.insertBefore(document.createTextNode("\n"), cursor);
      setTimeout(step, isCommand ? 420 : 90); // pause after "Enter"
      return;
    }
    setTimeout(step, isCommand ? 34 : 15);
  }

  setTimeout(step, 500);
})();
