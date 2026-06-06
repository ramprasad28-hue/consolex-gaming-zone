/* ============================================================
   CONSOLEX — hero.js  (Phase 4.2)
   Scroll-reveal + floating particles
   ============================================================ */
(function () {
    'use strict';

    /* ── 1. Scroll-reveal ────────────────────────────────── */
    var animEls = document.querySelectorAll('[data-animate]');

    function reveal(el) {
        var delay = parseInt(el.dataset.delay || '0', 10);
        setTimeout(function () {
            el.classList.add('revealed');
        }, delay);
    }

    if ('IntersectionObserver' in window) {
        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    reveal(entry.target);
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.15 });

        animEls.forEach(function (el) { observer.observe(el); });
    } else {
        /* Fallback — reveal all immediately */
        animEls.forEach(function (el) { reveal(el); });
    }

    /* ── 2. Floating particles ───────────────────────────── */
    var container = document.getElementById('heroParticles');
    if (!container) return;

    var PARTICLE_COUNT = 28;

    var colors = [
        'rgba(0,  240, 255, VAR)',   /* cyan   */
        'rgba(191,  0, 255, VAR)',   /* purple */
        'rgba(255, 107,  0, VAR)',   /* orange */
        'rgba(255, 255, 255, VAR)',  /* white  */
    ];

    function rand(min, max) {
        return Math.random() * (max - min) + min;
    }

    for (var i = 0; i < PARTICLE_COUNT; i++) {
        (function () {
            var p   = document.createElement('span');
            p.className = 'hparticle';

            var size    = rand(2, 5);
            var opacity = rand(0.3, 0.7);
            var color   = colors[Math.floor(Math.random() * colors.length)]
                            .replace('VAR', opacity.toFixed(2));

            var left    = rand(2, 98);
            var startY  = rand(10, 95);
            var dur     = rand(7, 16);
            var delay   = rand(0, dur);

            p.style.cssText = [
                'width:'  + size + 'px',
                'height:' + size + 'px',
                'left:'   + left + '%',
                'top:'    + startY + '%',
                'background:' + color,
                'box-shadow: 0 0 ' + (size * 3) + 'px ' + color,
                '--dur:'         + dur   + 's',
                '--delay: -'     + delay + 's',
                '--max-opacity:' + opacity,
            ].join(';');

            container.appendChild(p);
        }());
    }

    /* ── 3. Smooth scroll for hero anchor links ──────────── */
    document.querySelectorAll('.hero a[href^="#"]').forEach(function (a) {
        a.addEventListener('click', function (e) {
            var id = a.getAttribute('href').slice(1);
            var el = document.getElementById(id);
            if (el) {
                e.preventDefault();
                var top = el.getBoundingClientRect().top + window.scrollY - 76;
                window.scrollTo({ top: top, behavior: 'smooth' });
            }
        });
    });

}());
