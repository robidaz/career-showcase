/*
 * Masthead particle field, modeled on Holigram's hologram figure: thousands of
 * small round points filling a 3D volume that turns slowly in perspective
 * (bright in front, faint behind), a white scan band sweeping up through it,
 * a per-point twinkle, and a slow upward drift. The volume leans toward the
 * pointer.
 *
 * Plain 2D canvas, no dependencies. Points are batched by colour and
 * brightness so each frame needs only a few dozen state changes.
 * Runs only while the masthead is on screen and the tab is visible; with
 * prefers-reduced-motion it paints one still frame.
 */
(function () {
  "use strict";

  var masthead = document.querySelector(".masthead");
  var canvas = masthead && masthead.querySelector(".masthead__particles");
  if (!canvas || !canvas.getContext) return;
  var ctx = canvas.getContext("2d");
  if (!ctx) return;

  // Holigram palette, back to front: brand cyan, bright cyan, ice white
  var COLORS = ["40,194,242", "95,216,255", "232,246,255"];
  var ALPHA_STEPS = 12;
  var AREA_PER_POINT = 30;      // px² of masthead per point
  var MIN_POINTS = 4000;
  var MAX_POINTS = 14000;
  var SPIN = 0.045;             // rad/s around the vertical axis
  var SCAN_SECONDS = 12;        // one scan pass, bottom to top
  var RISE = 2.5;               // px/s upward drift

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  var dots = COLORS.map(makeDot);
  var fills = COLORS.map(function (rgb) { return "rgb(" + rgb + ")"; });
  var SPRITE_MIN = 2.6;           // sprite boxes smaller than this draw as a plain square (far points)
  // buckets[color * ALPHA_STEPS + alpha] = flat [x, y, size, ...]; tiny = far points as squares
  var buckets = [], tiny = [];
  for (var b = 0; b < COLORS.length * ALPHA_STEPS; b++) { buckets.push([]); tiny.push([]); }

  var points = [];
  var width = 0, height = 0, dpr = 1;
  var onScreen = true, rafId = 0, lastTime = 0, elapsed = 0;
  var tilt = 0, tiltTarget = 0;   // pointer lean, radians

  // A round point with a solid core and a thin soft edge, pre-rendered per colour
  function makeDot(rgb) {
    var size = 16, r = size / 2;
    var dot = document.createElement("canvas");
    dot.width = dot.height = size;
    var g = dot.getContext("2d");
    var grad = g.createRadialGradient(r, r, 0, r, r, r);
    grad.addColorStop(0, "rgba(255,255,255,1)");
    grad.addColorStop(0.25, "rgba(" + rgb + ",1)");
    grad.addColorStop(0.5, "rgba(" + rgb + ",0.75)");
    grad.addColorStop(1, "rgba(" + rgb + ",0)");
    g.fillStyle = grad;
    g.fillRect(0, 0, size, size);
    return dot;
  }

  function makePoint() {
    // volumetric: denser toward the shell, like the revolved figure cloud
    return {
      theta: Math.random() * Math.PI * 2,
      radius: 0.55 + 0.45 * Math.sqrt(Math.random()),
      y: Math.random(),             // 0 = top, 1 = bottom of the volume
      seed: Math.random(),
      hot: Math.random() < 0.08     // a few points always run white, as on the figure
    };
  }

  function resize() {
    var rect = masthead.getBoundingClientRect();
    var w = Math.max(1, Math.round(rect.width));
    var h = Math.max(1, Math.round(rect.height));
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    width = w; height = h;
    var target = Math.max(MIN_POINTS, Math.min(MAX_POINTS, Math.round((w * h) / AREA_PER_POINT)));
    while (points.length < target) points.push(makePoint());
    points.length = target;
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    if (!rafId) draw();
  }

  function draw() {
    var t = elapsed;
    var cx = width * 0.5, cy = height * 0.5;
    var R = Math.max(width * 0.62, 260);        // drum radius: wider than the header
    var camera = R * 2.3;
    var span = height * 1.15;                   // volume height, slightly taller than the header
    var spin = t * SPIN;
    var scanY = 1.15 - ((t / SCAN_SECONDS) % 1) * 1.3;   // sweeps bottom → top, off both ends
    var cosT = Math.cos(tilt), sinT = Math.sin(tilt);

    for (var b = 0; b < buckets.length; b++) { buckets[b].length = 0; tiny[b].length = 0; }

    for (var i = 0; i < points.length; i++) {
      var p = points[i];
      var yN = (p.y - (t * RISE) / span) % 1;
      if (yN < 0) yN += 1;
      var a = p.theta + spin;
      var r = R * p.radius;
      var x3 = Math.sin(a) * r;
      var z3 = Math.cos(a) * r;
      var y3 = (yN - 0.5) * span;
      // lean toward the pointer (rotation about the vertical axis on top of the spin)
      var xr = x3 * cosT + z3 * sinT;
      var zr = z3 * cosT - x3 * sinT;
      var s = camera / (camera - zr);
      var sx = cx + xr * s;
      var sy = cy + y3 * s;
      if (sx < -4 || sx > width + 4 || sy < -4 || sy > height + 4) continue;

      var depth = (zr / R + 1) * 0.5;                    // 0 back, 1 front
      var twinkle = 0.75 + 0.25 * Math.sin(t * (0.7 + p.seed * 1.1) + p.seed * 40);
      var d = (yN - scanY) / 0.06;
      var scan = Math.exp(-d * d);                        // white band of the construction sweep
      var alpha = (0.12 + 0.95 * depth * depth) * twinkle + scan * 0.45;
      var color = (scan > 0.6 && depth > 0.3) || (p.hot && depth > 0.55) ? 2 : depth > 0.62 ? 1 : 0;
      var size = (1.5 + 3 * depth) * s * (1 + scan * 0.35);   // sprite box; the visible core is about half

      var level = Math.min(ALPHA_STEPS - 1, Math.max(0, Math.round(alpha * (ALPHA_STEPS - 1))));
      if (size < SPRITE_MIN) {
        var core = size * 0.45;                        // matches the sprite's visible core
        tiny[color * ALPHA_STEPS + level].push(sx - core / 2, sy - core / 2, core);
      } else {
        buckets[color * ALPHA_STEPS + level].push(sx - size / 2, sy - size / 2, size);
      }
    }

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);
    ctx.globalCompositeOperation = "lighter";
    for (var c = 0; c < COLORS.length; c++) {
      for (var l = 0; l < ALPHA_STEPS; l++) {
        var idx = c * ALPHA_STEPS + l;
        var list = buckets[idx], small = tiny[idx];
        if (!list.length && !small.length) continue;
        ctx.globalAlpha = (l + 1) / ALPHA_STEPS;
        if (small.length) {
          ctx.fillStyle = fills[c];
          for (var j = 0; j < small.length; j += 3) ctx.fillRect(small[j], small[j + 1], small[j + 2], small[j + 2]);
        }
        for (var k = 0; k < list.length; k += 3) ctx.drawImage(dots[c], list[k], list[k + 1], list[k + 2], list[k + 2]);
      }
    }
    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = "source-over";
  }

  function frame(now) {
    rafId = 0;
    var dt = lastTime ? Math.min((now - lastTime) / 1000, 0.05) : 0;
    lastTime = now;
    elapsed += dt;
    tilt += (tiltTarget - tilt) * Math.min(1, dt * 1.2);
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

  masthead.addEventListener("pointermove", function (e) {
    var rect = masthead.getBoundingClientRect();
    tiltTarget = ((e.clientX - rect.left) / rect.width - 0.5) * 0.5;
  }, { passive: true });
  masthead.addEventListener("pointerleave", function () { tiltTarget = 0; });

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

  // Reduced motion: a still frame with the scan band parked at the top edge, clear of the text
  if (reduceMotion.matches) elapsed = SCAN_SECONDS * 0.87;
  resize();
  draw();
  schedule();
})();
