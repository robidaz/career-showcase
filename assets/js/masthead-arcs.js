/*
 * Masthead "instrument arcs": concentric rings centred behind the contact
 * block, each carrying a few arc segments that turn at their own slow speed,
 * one graduated ring like a gauge, and a single glowing ice-cyan accent arc
 * that sweeps back and forth like a needle.
 *
 * Plain 2D canvas, no dependencies. Runs only while the masthead is on screen
 * and the tab is visible; with prefers-reduced-motion it paints one still frame.
 */
(function () {
  "use strict";

  var masthead = document.querySelector(".masthead");
  var canvas = masthead && masthead.querySelector(".masthead__canvas");
  if (!canvas || !canvas.getContext) return;
  var ctx = canvas.getContext("2d");
  if (!ctx) return;

  var RING_COUNT = 11;
  var RING_GAP = 46;            // px between rings
  var INNER_RADIUS = 70;
  var START_TIME = 20;          // seconds in, so the first frame looks settled

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  var rings = makeRings();
  var width = 0, height = 0, dpr = 1;
  var onScreen = true, rafId = 0, lastTime = 0, elapsed = START_TIME;

  // Deterministic layout so the header looks the same on every visit
  function makeRings() {
    var seed = 3;
    function rand() { seed = (seed * 16807) % 2147483647; return seed / 2147483647; }
    var list = [];
    for (var i = 0; i < RING_COUNT; i++) {
      var segs = [], n = 1 + Math.floor(rand() * 3);
      for (var k = 0; k < n; k++) segs.push({ start: rand() * Math.PI * 2, len: 0.3 + rand() * 1.6 });
      list.push({
        radius: INNER_RADIUS + i * RING_GAP,
        speed: (rand() < 0.5 ? -1 : 1) * (0.015 + rand() * 0.05),   // rad/s
        segs: segs,
        ticks: i === 4,
        accent: i === 3
      });
    }
    return list;
  }

  function resize() {
    var rect = masthead.getBoundingClientRect();
    width = Math.max(1, Math.round(rect.width));
    height = Math.max(1, Math.round(rect.height));
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    if (!rafId) draw();
  }

  function draw() {
    var t = elapsed;
    // centre behind the contact block on wide screens, nearer the middle on phones
    var cx = width * (width > 860 ? 0.8 : 0.72), cy = height * 0.52;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);
    ctx.lineCap = "round";

    for (var i = 0; i < rings.length; i++) {
      var ring = rings[i], rot = t * ring.speed;

      ctx.strokeStyle = "rgba(200, 220, 255, 0.07)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(cx, cy, ring.radius, 0, Math.PI * 2);
      ctx.stroke();

      ctx.strokeStyle = "rgba(210, 228, 255, 0.34)";
      ctx.lineWidth = 1.4;
      for (var k = 0; k < ring.segs.length; k++) {
        var sg = ring.segs[k];
        ctx.beginPath();
        ctx.arc(cx, cy, ring.radius, sg.start + rot, sg.start + rot + sg.len);
        ctx.stroke();
      }

      if (ring.ticks) {
        ctx.strokeStyle = "rgba(210, 228, 255, 0.28)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        for (var a = 0; a < 72; a++) {
          var ang = (a / 72) * Math.PI * 2 + rot, len = a % 6 === 0 ? 10 : 4;
          ctx.moveTo(cx + Math.cos(ang) * ring.radius, cy + Math.sin(ang) * ring.radius);
          ctx.lineTo(cx + Math.cos(ang) * (ring.radius - len), cy + Math.sin(ang) * (ring.radius - len));
        }
        ctx.stroke();
      }

      if (ring.accent) {
        // the one accent: a short ice-cyan arc that sweeps like a gauge needle on the
        // ring's inner (left) side, so it stays in view, with a soft glow and a bright tip
        var mid = Math.PI + 0.5 * Math.sin(t * 0.13);
        var from = mid - 0.11, to = mid + 0.11;
        ctx.save();
        ctx.shadowColor = "rgba(120, 214, 255, 0.85)";
        ctx.shadowBlur = 10;
        ctx.strokeStyle = "rgba(150, 226, 255, 0.95)";
        ctx.lineWidth = 2.2;
        ctx.beginPath();
        ctx.arc(cx, cy, ring.radius, from, to);
        ctx.stroke();
        ctx.fillStyle = "rgba(225, 247, 255, 1)";
        ctx.beginPath();
        ctx.arc(cx + Math.cos(to) * ring.radius, cy + Math.sin(to) * ring.radius, 2.4, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      }
    }
  }

  function frame(now) {
    rafId = 0;
    var dt = lastTime ? Math.min((now - lastTime) / 1000, 0.05) : 0;
    lastTime = now;
    elapsed += dt;
    draw();
    schedule();
  }

  function schedule() {
    if (rafId || reduceMotion.matches || !onScreen || document.hidden) {
      if (!rafId) lastTime = 0;
      return;
    }
    rafId = requestAnimationFrame(frame);
  }

  function stop() {
    if (rafId) cancelAnimationFrame(rafId);
    rafId = 0;
    lastTime = 0;
  }

  if ("ResizeObserver" in window) new ResizeObserver(resize).observe(masthead);
  else window.addEventListener("resize", resize);

  if ("IntersectionObserver" in window) {
    new IntersectionObserver(function (entries) {
      onScreen = entries[0].isIntersecting;
      if (onScreen) schedule(); else stop();
    }).observe(masthead);
  }

  document.addEventListener("visibilitychange", function () {
    if (document.hidden) stop(); else schedule();
  });

  var onMotionChange = function () {
    if (reduceMotion.matches) { stop(); draw(); } else schedule();
  };
  if (reduceMotion.addEventListener) reduceMotion.addEventListener("change", onMotionChange);
  else if (reduceMotion.addListener) reduceMotion.addListener(onMotionChange);

  resize();
  schedule();
})();
