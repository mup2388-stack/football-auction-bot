// ===========================================================================
//  MAIN JS — scroll reveals, border glow, table sorting
//  All effects respect prefers-reduced-motion (CSS handles the kill switch)
// ===========================================================================

// ── Scroll Reveal (reactbits.dev "Animated Content" inspired) ──────────────
const revealObserver = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        revealObserver.unobserve(entry.target);
      }
    });
  },
  { threshold: 0.1, rootMargin: '0px 0px -40px 0px' }
);

document.querySelectorAll('.reveal, .reveal-stagger').forEach((el) => {
  revealObserver.observe(el);
});

// ── Border Glow (reactbits.dev "Border Glow" inspired) ─────────────────────
// Tracks mouse position relative to card, sets CSS vars for the radial gradient
document.querySelectorAll('.glow-card').forEach((card) => {
  card.addEventListener('mousemove', (e) => {
    const rect = card.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;
    card.style.setProperty('--mx', x + '%');
    card.style.setProperty('--my', y + '%');
  });
});

// ── Table Sorting ──────────────────────────────────────────────────────────
document.querySelectorAll('.tbl[data-sortable]').forEach((table) => {
  const headers = table.querySelectorAll('th[data-key]');
  headers.forEach((header) => {
    header.addEventListener('click', () => {
      const key = header.dataset.key;
      const isNumeric = header.classList.contains('numeric');
      const tbody = table.querySelector('tbody');
      const rows = Array.from(tbody.querySelectorAll('tr'));

      // toggle direction
      const currentDir = header.classList.contains('sort-asc') ? 'asc' :
                         header.classList.contains('sort-desc') ? 'desc' : null;
      const newDir = currentDir === 'asc' ? 'desc' : 'asc';

      // clear all headers
      headers.forEach((h) => h.classList.remove('sort-asc', 'sort-desc'));
      header.classList.add('sort-' + newDir);

      // sort
      rows.sort((a, b) => {
        const aVal = a.dataset[key] || a.querySelector(`[data-${key}]`)?.dataset[key] || '';
        const bVal = b.dataset[key] || b.querySelector(`[data-${key}]`)?.dataset[key] || '';
        if (isNumeric) {
          return newDir === 'asc' ? (parseFloat(aVal) - parseFloat(bVal)) : (parseFloat(bVal) - parseFloat(aVal));
        }
        return newDir === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      });

      rows.forEach((row) => tbody.appendChild(row));
    });
  });
});

// ── Signing Carousel (auto-rotating top signings) ──────────────────────────
function initCarousel() {
  const carousel = document.getElementById('signing-carousel');
  if (!carousel) return;
  const slides = carousel.querySelectorAll('.signing-slide');
  const dots = document.querySelectorAll('.carousel-dot');
  if (slides.length <= 1) return;

  let current = 0;
  const interval = setInterval(() => {
    slides[current].classList.remove('active');
    dots[current]?.classList.remove('active');
    current = (current + 1) % slides.length;
    slides[current].classList.add('active');
    dots[current]?.classList.add('active');
  }, 4000);

  // click dots to jump
  dots.forEach((dot) => {
    dot.addEventListener('click', () => {
      clearInterval(interval);
      slides[current].classList.remove('active');
      dots[current]?.classList.remove('active');
      current = parseInt(dot.dataset.index);
      slides[current].classList.add('active');
      dots[current]?.classList.add('active');
    });
  });
}
initCarousel();

// ── Number Count-Up (subtle, for hero stats) ───────────────────────────────
function countUp(el, target, duration = 800) {
  const start = 0;
  const startTime = performance.now();
  const isInt = Number.isInteger(target);

  function update(now) {
    const elapsed = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3); // easeOutCubic
    const val = start + (target - start) * eased;
    el.textContent = isInt ? Math.round(val) : val.toFixed(1);
    if (progress < 1) requestAnimationFrame(update);
  }
  requestAnimationFrame(update);
}

document.querySelectorAll('[data-countup]').forEach((el) => {
  const target = parseFloat(el.dataset.countup);
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduced) {
    el.textContent = Number.isInteger(target) ? target : target.toFixed(1);
  } else {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          countUp(el, target);
          observer.unobserve(el);
        }
      });
    });
    observer.observe(el);
  }
});

// ── Image lazy fade-in ────────────────────────────────────────────────────
// Faces/logos fade in smoothly instead of popping. Adds .loaded when the
// image finishes downloading so the shimmer background disappears.
document.querySelectorAll('img').forEach((img) => {
  if (img.complete && img.naturalWidth > 0) {
    img.classList.add('loaded');
  } else {
    img.addEventListener('load', () => img.classList.add('loaded'));
    img.addEventListener('error', () => img.classList.add('loaded'));
  }
});
