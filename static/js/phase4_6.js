/* ═══════════════════════════════════════════════════════════
   CONSOLEX — PHASE 4.6 JS
   File: static/js/phase4_6.js
   Handles: scroll reveal · counter animation
═══════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {

  /* ── SCROLL REVEAL ─────────────────────────────────────── */
  const revealEls = document.querySelectorAll('[data-reveal]');

  if ('IntersectionObserver' in window) {
    const revealObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry, i) => {
        if (entry.isIntersecting) {
          // Staggered delay for grid children
          const delay = entry.target.closest('.testimonials-grid')
            ? Array.from(entry.target.parentElement.children).indexOf(entry.target) * 100
            : 0;
          setTimeout(() => {
            entry.target.classList.add('revealed');
          }, delay);
          revealObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12 });

    revealEls.forEach(el => revealObserver.observe(el));
  } else {
    // Fallback for old browsers
    revealEls.forEach(el => el.classList.add('revealed'));
  }

  /* ── COUNTER ANIMATION ─────────────────────────────────── */
  const counters = document.querySelectorAll('.stat-number[data-count]');

  if ('IntersectionObserver' in window) {
    const counterObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          animateCounter(entry.target);
          counterObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.5 });

    counters.forEach(el => counterObserver.observe(el));
  }

  function animateCounter(el) {
    const target  = parseInt(el.dataset.count, 10);
    const duration = 1800;
    const step     = 16;
    const increment = target / (duration / step);
    let current = 0;

    el.classList.add('counting');
    const timer = setInterval(() => {
      current += increment;
      if (current >= target) {
        current = target;
        clearInterval(timer);
        el.classList.remove('counting');
      }
      el.textContent = Math.floor(current);
    }, step);
  }

});