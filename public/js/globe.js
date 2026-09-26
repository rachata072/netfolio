/* ==========================================================================
   3D "internet" globe for the home hero. ~6 KB, zero dependencies.
   Plain Canvas 2D with a hand-rolled perspective projection: no WebGL,
   no three.js, nothing to download, nothing third-party (CSP: script-src 'self').

   What it draws
     - ~170 nodes spread evenly over a sphere (Fibonacci lattice) = routers
     - links between near neighbours = the mesh
     - packets that arc between nodes; ~1 in 5 is red, gets inspected at the
       outer "firewall" ring and dropped with a small burst
     - a tilted dashed ring with lock nodes = the security perimeter

   Performance / accessibility
     - pauses when scrolled off screen or when the tab is hidden
     - devicePixelRatio capped, ~30 fps on small screens
     - prefers-reduced-motion: renders one still frame, no animation loop
     - purely decorative: the canvas is aria-hidden and ignores the pointer

   Security (OWASP A03): reads nothing from the URL, storage or user input,
   writes nothing to the DOM except canvas pixels.
   ========================================================================== */
(function () {
  "use strict";

  var canvas = document.querySelector("canvas.globe");
  if (!canvas || !canvas.getContext) return;
  var ctx = canvas.getContext("2d");
  if (!ctx) return;

  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var TAU = Math.PI * 2;

  /* ---------- palette (Cisco) ---------- */
  var BLUE = "4,159,217", BRIGHT = "0,188,235", GREEN = "108,192,74", RED = "255,107,94";

  /* ---------- geometry: Fibonacci sphere ---------- */
  var N = window.innerWidth < 700 ? 120 : 170;
  var pts = [];
  var golden = Math.PI * (3 - Math.sqrt(5));
  for (var i = 0; i < N; i++) {
    var y = 1 - (i / (N - 1)) * 2;
    var rad = Math.sqrt(1 - y * y);
    var th = golden * i;
    pts.push([Math.cos(th) * rad, y, Math.sin(th) * rad]);
  }

  // links: each node to its 3 nearest neighbours (deduplicated)
  var edges = [], seen = {};
  for (i = 0; i < N; i++) {
    var d = [];
    for (var j = 0; j < N; j++) {
      if (i === j) continue;
      var dx = pts[i][0] - pts[j][0], dy = pts[i][1] - pts[j][1], dz = pts[i][2] - pts[j][2];
      d.push([dx * dx + dy * dy + dz * dz, j]);
    }
    d.sort(function (a, b) { return a[0] - b[0]; });
    for (var k = 0; k < 3; k++) {
      var a = Math.min(i, d[k][1]), b = Math.max(i, d[k][1]), key = a + "-" + b;
      if (!seen[key]) { seen[key] = 1; edges.push([a, b]); }
    }
  }

  // a few "core" nodes that pulse green (your lab gear)
  var core = {};
  for (i = 0; i < 9; i++) core[(i * 37 + 11) % N] = 1;

  /* ---------- view state ---------- */
  var rotY = 0.6, tilt = -0.38, W = 0, H = 0, DPR = 1, R = 100, CX = 0, CY = 0, F = 3.2;
  var targetTiltOffset = 0, tiltOffset = 0, targetYawOffset = 0, yawOffset = 0;

  function layout() {
    var r = canvas.getBoundingClientRect();
    W = r.width; H = r.height;
    DPR = Math.min(window.devicePixelRatio || 1, W < 700 ? 1.5 : 1.75);
    canvas.width = Math.round(W * DPR);
    canvas.height = Math.round(H * DPR);
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    if (W >= 960) {            // desktop: sits between the headline and the topology console
      R = Math.min(H * 0.36, W * 0.2);
      CX = W * 0.5; CY = H * 0.47;
    } else if (W >= 600) {     // tablet: behind the headline, right side
      R = Math.min(W * 0.3, 260);
      CX = W * 0.74; CY = R * 1.25;
    } else {                   // phone: top-right, partly off canvas
      R = W * 0.4;
      CX = W * 0.82; CY = R * 1.05;
    }
  }

  /* ---------- projection ---------- */
  var cy_, sy_, cx_, sx_;
  function setRot() {
    var ry = rotY + yawOffset, rx = tilt + tiltOffset;
    cy_ = Math.cos(ry); sy_ = Math.sin(ry); cx_ = Math.cos(rx); sx_ = Math.sin(rx);
  }
  // returns [screenX, screenY, depth(-1 back .. 1 front), scale]
  function project(p, lift) {
    var s = lift || 1;
    var x = p[0] * s, y = p[1] * s, z = p[2] * s;
    var x1 = x * cy_ + z * sy_, z1 = -x * sy_ + z * cy_;
    var y2 = y * cx_ - z1 * sx_, z2 = y * sx_ + z1 * cx_;
    var sc = F / (F - z2);
    return [CX + x1 * R * sc, CY + y2 * R * sc, z2, sc];
  }

  /* ---------- great-circle packets ---------- */
  function slerp(a, b, t) {
    var dot = a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
    dot = Math.max(-1, Math.min(1, dot));
    var om = Math.acos(dot), so = Math.sin(om);
    if (so < 1e-4) return a;
    var k1 = Math.sin((1 - t) * om) / so, k2 = Math.sin(t * om) / so;
    return [a[0] * k1 + b[0] * k2, a[1] * k1 + b[1] * k2, a[2] * k1 + b[2] * k2];
  }

  var packets = [], bursts = [];
  function spawn(now) {
    var a = (Math.random() * N) | 0, b, tries = 0;
    do {
      b = (Math.random() * N) | 0; tries++;
      var dot = pts[a][0] * pts[b][0] + pts[a][1] * pts[b][1] + pts[a][2] * pts[b][2];
    } while ((dot > 0.8 || dot < -0.3) && tries < 20);
    var bad = Math.random() < 0.2;
    packets.push({ a: pts[a], b: pts[b], t0: now, dur: 1700 + Math.random() * 1300, bad: bad, stop: bad ? 0.55 + Math.random() * 0.15 : 1 });
  }

  /* ---------- draw ---------- */
  function frame(now) {
    ctx.clearRect(0, 0, W, H);
    tiltOffset += (targetTiltOffset - tiltOffset) * 0.05;
    yawOffset += (targetYawOffset - yawOffset) * 0.05;
    setRot();

    var P = new Array(N);
    for (var i = 0; i < N; i++) P[i] = project(pts[i]);

    // soft atmosphere
    var g = ctx.createRadialGradient(CX, CY, R * 0.2, CX, CY, R * 1.35);
    g.addColorStop(0, "rgba(" + BLUE + ",0.10)");
    g.addColorStop(0.7, "rgba(" + BLUE + ",0.04)");
    g.addColorStop(1, "rgba(" + BLUE + ",0)");
    ctx.fillStyle = g;
    ctx.beginPath(); ctx.arc(CX, CY, R * 1.35, 0, TAU); ctx.fill();

    // globe rim
    ctx.strokeStyle = "rgba(" + BLUE + ",0.22)";
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.arc(CX, CY, R * (F / (F - 0.0)) * 0.985, 0, TAU); ctx.stroke();

    // links (back first, dim; then front)
    for (var pass = 0; pass < 2; pass++) {
      ctx.beginPath();
      for (var e = 0; e < edges.length; e++) {
        var p = P[edges[e][0]], q = P[edges[e][1]];
        var front = (p[2] + q[2]) > 0;
        if ((pass === 0) === front) continue;
        ctx.moveTo(p[0], p[1]); ctx.lineTo(q[0], q[1]);
      }
      ctx.strokeStyle = pass === 0 ? "rgba(" + BLUE + ",0.10)" : "rgba(" + BLUE + ",0.34)";
      ctx.lineWidth = pass === 0 ? 0.6 : 0.9;
      ctx.stroke();
    }

    // nodes
    var pulse = 0.5 + 0.5 * Math.sin(now / 500);
    for (i = 0; i < N; i++) {
      var n = P[i], front2 = n[2] > 0;
      var alpha = front2 ? 0.45 + n[2] * 0.5 : 0.12;
      var size = (core[i] ? 2.4 : 1.4) * n[3];
      if (core[i] && front2) {
        ctx.fillStyle = "rgba(" + GREEN + "," + (0.15 + pulse * 0.25) + ")";
        ctx.beginPath(); ctx.arc(n[0], n[1], size * 3.2, 0, TAU); ctx.fill();
        ctx.fillStyle = "rgba(" + GREEN + ",0.95)";
      } else {
        ctx.fillStyle = "rgba(" + BRIGHT + "," + alpha + ")";
      }
      ctx.beginPath(); ctx.arc(n[0], n[1], size, 0, TAU); ctx.fill();
    }

    // security perimeter ring (tilted orbit) with lock nodes
    var ringR = 1.28, segs = 120, ringTilt = 0.95;
    var ct = Math.cos(ringTilt), st = Math.sin(ringTilt);
    var spin = now / 9000;
    ctx.setLineDash([2, 5]);
    ctx.lineWidth = 1;
    for (var half = 0; half < 2; half++) {
      ctx.beginPath();
      var started = false;
      for (var s = 0; s <= segs; s++) {
        var ang = (s / segs) * TAU;
        var rp = [Math.cos(ang) * ringR, Math.sin(ang) * ringR * st, Math.sin(ang) * ringR * ct];
        var pr = project(rp);
        var isFront = pr[2] > 0;
        if ((half === 1) !== isFront) { started = false; continue; }
        if (!started) { ctx.moveTo(pr[0], pr[1]); started = true; } else ctx.lineTo(pr[0], pr[1]);
      }
      ctx.strokeStyle = half === 1 ? "rgba(" + RED + ",0.45)" : "rgba(" + RED + ",0.14)";
      ctx.stroke();
    }
    ctx.setLineDash([]);
    for (var l = 0; l < 4; l++) {
      var la = spin + (l / 4) * TAU;
      var lp = project([Math.cos(la) * ringR, Math.sin(la) * ringR * st, Math.sin(la) * ringR * ct]);
      var la2 = lp[2] > 0 ? 0.9 : 0.25;
      ctx.fillStyle = "rgba(5,13,24," + la2 + ")";
      ctx.strokeStyle = "rgba(" + RED + "," + la2 + ")";
      ctx.lineWidth = 1.2;
      var bw = 7 * lp[3], bh = 6 * lp[3];
      ctx.beginPath(); ctx.rect(lp[0] - bw / 2, lp[1] - bh / 2 + 1, bw, bh); ctx.fill(); ctx.stroke();
      ctx.beginPath(); ctx.arc(lp[0], lp[1] - bh / 2 + 1, bw * 0.32, Math.PI, 0); ctx.stroke();
    }

    // packets
    if (!reduced && now - lastSpawn > spawnEvery) { spawn(now); lastSpawn = now; }
    for (var pk = packets.length - 1; pk >= 0; pk--) {
      var pkt = packets[pk];
      var t = (now - pkt.t0) / pkt.dur;
      if (reduced) t = 0.5;
      var head = Math.min(t, pkt.stop);
      var col = pkt.bad ? RED : BRIGHT;
      ctx.beginPath();
      var tail = Math.max(0, head - 0.35);
      var steps = 14, visible = false;
      for (var st2 = 0; st2 <= steps; st2++) {
        var tt = tail + (head - tail) * (st2 / steps);
        var lift = 1 + Math.sin(tt * Math.PI) * (pkt.bad ? 0.34 : 0.22);
        var pp = project(slerp(pkt.a, pkt.b, tt), lift);
        if (st2 === 0) ctx.moveTo(pp[0], pp[1]); else ctx.lineTo(pp[0], pp[1]);
        if (pp[2] > -0.2) visible = true;
      }
      var fade = t > pkt.stop ? Math.max(0, 1 - (t - pkt.stop) * 4) : 1;
      if (visible && fade > 0) {
        ctx.strokeStyle = "rgba(" + col + "," + (0.75 * fade) + ")";
        ctx.lineWidth = 1.4;
        ctx.stroke();
        var hp = project(slerp(pkt.a, pkt.b, head), 1 + Math.sin(head * Math.PI) * (pkt.bad ? 0.34 : 0.22));
        ctx.fillStyle = "rgba(" + col + "," + fade + ")";
        ctx.beginPath(); ctx.arc(hp[0], hp[1], 2.6 * hp[3], 0, TAU); ctx.fill();
        if (pkt.bad && t >= pkt.stop && !pkt.burst) {
          pkt.burst = true;
          bursts.push({ x: hp[0], y: hp[1], t0: now });
        }
      }
      if (t > pkt.stop + 0.3 || t > 1.3) packets.splice(pk, 1);
    }

    // dropped-packet bursts
    for (var bi = bursts.length - 1; bi >= 0; bi--) {
      var bu = bursts[bi], bt = (now - bu.t0) / 600;
      if (bt > 1) { bursts.splice(bi, 1); continue; }
      ctx.strokeStyle = "rgba(" + RED + "," + (1 - bt) + ")";
      ctx.lineWidth = 1.2;
      ctx.beginPath(); ctx.arc(bu.x, bu.y, 3 + bt * 14, 0, TAU); ctx.stroke();
      var xs = 4 * (1 - bt);
      ctx.beginPath();
      ctx.moveTo(bu.x - xs, bu.y - xs); ctx.lineTo(bu.x + xs, bu.y + xs);
      ctx.moveTo(bu.x + xs, bu.y - xs); ctx.lineTo(bu.x - xs, bu.y + xs);
      ctx.stroke();
    }
  }

  /* ---------- loop control ---------- */
  var running = false, onScreen = true, rafId = 0, last = 0, lastSpawn = 0;
  var spawnEvery = window.innerWidth < 700 ? 520 : 360;
  var minFrame = window.innerWidth < 700 ? 1000 / 30 : 0;

  function loop(now) {
    rafId = window.requestAnimationFrame(loop);
    if (now - last < minFrame) return;
    var dt = last ? Math.min(now - last, 50) : 16;
    last = now;
    rotY += dt * 0.00012;
    frame(now);
  }
  function start() {
    if (running || reduced || !onScreen || document.hidden) return;
    running = true; last = 0;
    rafId = window.requestAnimationFrame(loop);
  }
  function stop() {
    running = false;
    window.cancelAnimationFrame(rafId);
  }

  layout();
  if (reduced) {
    // one still, fully drawn frame
    for (var r0 = 0; r0 < 6; r0++) spawn(0);
    frame(0);
  } else {
    start();
  }

  if ("ResizeObserver" in window) {
    new ResizeObserver(function () { layout(); if (reduced || !running) frame(performance.now()); }).observe(canvas);
  } else {
    window.addEventListener("resize", layout);
  }
  if ("IntersectionObserver" in window) {
    new IntersectionObserver(function (entries) {
      onScreen = entries[0].isIntersecting;
      if (onScreen) start(); else stop();
    }).observe(canvas);
  }
  document.addEventListener("visibilitychange", function () {
    if (document.hidden) stop(); else start();
  });

  // gentle parallax: the globe leans toward the pointer (desktop only)
  var hero = canvas.parentElement;
  if (hero && window.matchMedia("(pointer: fine)").matches && !reduced) {
    hero.addEventListener("pointermove", function (ev) {
      var b = hero.getBoundingClientRect();
      targetYawOffset = ((ev.clientX - b.left) / b.width - 0.5) * 0.6;
      targetTiltOffset = ((ev.clientY - b.top) / b.height - 0.5) * 0.35;
    }, { passive: true });
    hero.addEventListener("pointerleave", function () { targetYawOffset = 0; targetTiltOffset = 0; });
  }
})();
