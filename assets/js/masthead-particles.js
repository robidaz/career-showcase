/*
 * Masthead particle field — a light 2D-canvas take on Holigram's hologram
 * particles: additive glowing points with a hot core, a per-particle twinkle,
 * and a slow shimmer band that sweeps across. Particles drift on a gentle
 * current, sit at different depths (size, brightness, speed), and ease away
 * from the pointer.
 *
 * Runs only while the masthead is on screen and the tab is visible. With
 * prefers-reduced-motion it paints one still frame. No dependencies.
 */
(function () {
  "use strict";

  var masthead = document.querySelector(".masthead");
  var canvas = masthead && masthead.querySelector(".masthead__particles");
  if (!canvas || !canvas.getContext) return;
  var ctx = canvas.getContext("2d");
  if (!ctx) return;

  // Holigram palette: brand cyan, bright cyan, and an ice-white highlight
  var COLORS = [[40, 194, 242], [95, 216, 255], [232, 243, 255]];
  var DENSITY = 1700;          // px² of masthead per particle
  var MAX_PARTICLES = 420;
  var POINTER_RADIUS = 130;    // CSS px
  var SWEEP_SECONDS = 9;       // one shimmer pass across the header

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  var sprites = COLORS.map(makeSprite);
  var particles = [];
  var width = 0, height = 0, dpr = 1;
  var onScreen = true, rafId = 0, lastTime = 0, elapsed = 0;
  var pointer = { x: -1e4, y: -1e4 };

  // A soft radial glow with a hot centre, pre-rendered once per colour
  function makeSprite(rgb) {
    var size = 64, r = size / 2;
    var sprite = document.createElement("canvas");
    sprite.width = sprite.height = size;
    var g = sprite.getContext("2d");
    var c = rgb.join(",");
    var grad = g.createRadialGradient(r, r, 0, r, r, r);
    grad.addColorStop(0, "rgba(255,255,255,1)");
    grad.addColorStop(0.12, "rgba(" + c + ",0.95)");
    grad.addColorStop(0.35, "rgba(" + c + ",0.28)");
    grad.addColorStop(1, "rgba(" + c + ",0)");
    g.fillStyle = grad;
    g.fillRect(0, 0, size, size);
    return sprite;
  }

  function spawn(x, y) {
    var z = Math.pow(Math.random(), 1.6);          // most particles sit far back
    return {
      x: x, y: y, z: z,
      dx: 0, dy: 0,                                  // pointer displacement, eases back to 0
      seed: Math.random(),
      vx: (0.25 + Math.random() * 0.55) * (0.35 + z), // drift, faster when nearer
      vy: -(0.05 + Math.random() * 0.2) * (0.35 + z),
      sprite: sprites[Math.random() < 0.55 ? 0 : Math.random() < 0.7 ? 1 : 2]
    };
  }

  function resize() {
    var rect = masthead.getBoundingClientRect();
    var w = Math.max(1, Math.round(rect.width));
    var h = Math.max(1, Math.round(rect.height));
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    if (w !== width || h !== height) {
      // keep existing particles where they are (scaled), add or drop to match the new area
      var sx = width ? w / width : 1, sy = height ? h / height : 1;
      particles.forEach(function (p) { p.x *= sx; p.y *= sy; });
      width = w; height = h;
      var target = Math.min(MAX_PARTICLES, Math.round((w * h) / DENSITY));
      while (particles.length < target) particles.push(spawn(Math.random() * w, Math.random() * h));
      particles.length = target;
    }
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    if (!rafId) draw(0);
  }

  function step(dt) {
    var t = elapsed;
    for (var i = 0; i < particles.length; i++) {
      var p = particles[i];
      // a slow current: drift plus a per-particle sway
      p.x += (p.vx + Math.sin(t * 0.35 + p.seed * 12) * 0.12) * dt * 18;
      p.y += (p.vy + Math.cos(t * 0.28 + p.seed * 9) * 0.08) * dt * 18;

      // ease away from the pointer, then settle back
      var ox = p.x + p.dx - pointer.x, oy = p.y + p.dy - pointer.y;
      var d2 = ox * ox + oy * oy;
      if (d2 < POINTER_RADIUS * POINTER_RADIUS && d2 > 0.01) {
        var d = Math.sqrt(d2), push = Math.pow(1 - d / POINTER_RADIUS, 2) * 90 * dt * (0.4 + p.z);
        p.dx += (ox / d) * push;
        p.dy += (oy / d) * push;
      }
      var settle = Math.pow(0.04, dt);
      p.dx *= settle;
      p.dy *= settle;

      // wrap around the edges with a margin so glows never pop
      if (p.x > width + 20) p.x -= width + 40;
      if (p.x < -20) p.x += width + 40;
      if (p.y < -20) p.y += height + 40;
      if (p.y > height + 20) p.y -= height + 40;
    }
  }

  function draw(t) {
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);
    ctx.globalCompositeOperation = "lighter";
    // shimmer band position, sweeping left to right and off the edge
    var sweep = ((t / SWEEP_SECONDS) % 1) * 1.6 - 0.3;
    for (var i = 0; i < particles.length; i++) {
      var p = particles[i];
      var x = p.x + p.dx, y = p.y + p.dy;
      var twinkle = 0.72 + 0.28 * Math.sin(t * (1.6 + p.seed * 2.4) + p.seed * 40);
      var band = (x / width) - sweep;
      var shimmer = 1 + 0.7 * Math.exp(-(band * band) / 0.006);
      var size = (1.4 + p.z * 4.2) * (0.85 + 0.3 * p.seed);
      ctx.globalAlpha = Math.min(1, (0.24 + 0.7 * p.z) * twinkle * shimmer);
      var r = size * 3.2;
      ctx.drawImage(p.sprite, x - r, y - r, r * 2, r * 2);
    }
    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = "source-over";
  }

  function frame(now) {
    rafId = 0;
    var dt = lastTime ? Math.min((now - lastTime) / 1000, 0.05) : 0;
    lastTime = now;
    elapsed += dt;
    step(dt);
    draw(elapsed);
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
    pointer.x = e.clientX - rect.left;
    pointer.y = e.clientY - rect.top;
  }, { passive: true });
  masthead.addEventListener("pointerleave", function () { pointer.x = pointer.y = -1e4; });

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
    if (reduceMotion.matches) { stop(); draw(elapsed); } else schedule();
  };
  if (reduceMotion.addEventListener) reduceMotion.addEventListener("change", onMotionChange);
  else if (reduceMotion.addListener) reduceMotion.addListener(onMotionChange);

  resize();
  draw(elapsed);
  schedule();
})();
