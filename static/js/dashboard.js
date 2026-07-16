/* ─────────────────────────────────────────────
   File: static/js/dashboard.js
   CONSOLEX — Dashboard interactions (vanilla JS, minimal)
   ───────────────────────────────────────────── */
(function () {
  'use strict';

  /* ── Notification dropdown ─────────────────────────────── */
  var bellBtn   = document.getElementById('dashNotifBell');
  var notifPanel = document.getElementById('dashNotifPanel');

  if (bellBtn && notifPanel) {
    var closeOnOutsideClick = function (e) {
      if (!notifPanel.contains(e.target) && !bellBtn.contains(e.target)) {
        notifPanel.classList.remove('is-open');
        bellBtn.setAttribute('aria-expanded', 'false');
        document.removeEventListener('click', closeOnOutsideClick);
      }
    };

    bellBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      var isOpen = notifPanel.classList.toggle('is-open');
      bellBtn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
      if (isOpen) {
        document.addEventListener('click', closeOnOutsideClick);
      }
    });

    bellBtn.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        notifPanel.classList.remove('is-open');
        bellBtn.setAttribute('aria-expanded', 'false');
      }
    });
  }

  /* ── Animated stat counters ─────────────────────────────── */
  var counters = document.querySelectorAll('[data-count-to]');
  if (counters.length && 'IntersectionObserver' in window) {
    var counterObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        var el = entry.target;
        var target = parseFloat(el.getAttribute('data-count-to')) || 0;
        var prefix = el.getAttribute('data-prefix') || '';
        var decimals = el.getAttribute('data-decimals') ? parseInt(el.getAttribute('data-decimals'), 10) : 0;
        var duration = 900;
        var startTime = null;

        function step(ts) {
          if (!startTime) startTime = ts;
          var progress = Math.min((ts - startTime) / duration, 1);
          var eased = 1 - Math.pow(1 - progress, 3);
          var value = target * eased;
          el.textContent = prefix + value.toFixed(decimals);
          if (progress < 1) {
            requestAnimationFrame(step);
          } else {
            el.textContent = prefix + target.toFixed(decimals);
          }
        }
        requestAnimationFrame(step);
        counterObserver.unobserve(el);
      });
    }, { threshold: 0.4 });

    counters.forEach(function (el) { counterObserver.observe(el); });
  }

  /* ── Animate progress bars into view ───────────────────── */
  var bars = document.querySelectorAll('[data-progress-fill]');
  if (bars.length && 'IntersectionObserver' in window) {
    var barObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        var el = entry.target;
        var pct = el.getAttribute('data-progress-fill');
        requestAnimationFrame(function () { el.style.width = pct + '%'; });
        barObserver.unobserve(el);
      });
    }, { threshold: 0.4 });
    bars.forEach(function (el) { barObserver.observe(el); });
  } else {
    bars.forEach(function (el) { el.style.width = (el.getAttribute('data-progress-fill') || 0) + '%'; });
  }

  /* ── Toast for actions not yet wired to a backend view ──── */
  var toast = document.getElementById('dashToast');
  var toastTimer = null;

  window.dashShowStubToast = function (message) {
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add('is-shown');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () {
      toast.classList.remove('is-shown');
    }, 2600);
  };

  document.querySelectorAll('[data-stub-action]').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      window.dashShowStubToast(btn.getAttribute('data-stub-action'));
    });
  });
}());
