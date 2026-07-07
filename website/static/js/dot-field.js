// ===========================================================================
//  DOT FIELD — subtle canvas background (reactbits.dev "Dot Field" inspired)
//  Low-opacity gold dots on obsidian. Animated drift. Paused when offscreen.
// ===========================================================================

class DotField {
  constructor(canvas, options = {}) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.dots = [];
    this.density = options.density || 0.00008; // dots per pixel
    this.color = options.color || '255, 206, 96'; // gold
    this.maxRadius = options.maxRadius || 2.2;
    this.driftSpeed = options.driftSpeed || 0.2;
    this.running = false;
    this.resize();
    this.init();
    window.addEventListener('resize', () => this.resize());
  }

  resize() {
    const rect = this.canvas.getBoundingClientRect();
    this.canvas.width = rect.width * window.devicePixelRatio;
    this.canvas.height = rect.height * window.devicePixelRatio;
    this.ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    this.w = rect.width;
    this.h = rect.height;
    this.init();
  }

  init() {
    const count = Math.floor(this.w * this.h * this.density);
    this.dots = [];
    for (let i = 0; i < count; i++) {
      this.dots.push({
        x: Math.random() * this.w,
        y: Math.random() * this.h,
        r: Math.random() * this.maxRadius + 0.8,
        vx: (Math.random() - 0.5) * this.driftSpeed,
        vy: (Math.random() - 0.5) * this.driftSpeed,
        alpha: Math.random() * 0.5 + 0.2,
      });
    }
  }

  draw() {
    if (!this.running) return;
    this.ctx.clearRect(0, 0, this.w, this.h);
    for (const d of this.dots) {
      d.x += d.vx;
      d.y += d.vy;
      if (d.x < 0) d.x = this.w;
      if (d.x > this.w) d.x = 0;
      if (d.y < 0) d.y = this.h;
      if (d.y > this.h) d.y = 0;
      this.ctx.beginPath();
      this.ctx.arc(d.x, d.y, d.r, 0, Math.PI * 2);
      this.ctx.fillStyle = `rgba(${this.color}, ${d.alpha})`;
      this.ctx.fill();
    }
    requestAnimationFrame(() => this.draw());
  }

  start() {
    if (this.running) return;
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduced) {
      // draw once, static
      this.ctx.clearRect(0, 0, this.w, this.h);
      for (const d of this.dots) {
        this.ctx.beginPath();
        this.ctx.arc(d.x, d.y, d.r, 0, Math.PI * 2);
        this.ctx.fillStyle = `rgba(${this.color}, ${d.alpha})`;
        this.ctx.fill();
      }
      return;
    }
    this.running = true;
    this.draw();
  }
}

// auto-init any canvas with data-dot-field
document.querySelectorAll('canvas[data-dot-field]').forEach((canvas) => {
  const field = new DotField(canvas, {
    density: parseFloat(canvas.dataset.density) || 0.00008,
    color: canvas.dataset.color || '255, 206, 96',
  });
  field.start();
});
