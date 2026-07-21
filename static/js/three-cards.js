/* ============================================================
   CONSOLEX — three-cards.js
   3D tilt-effect interactive game cards
   Vanilla JS — no Three.js dependency
   ============================================================ */

(function () {
    'use strict';

    const cards = document.querySelectorAll('.game-card-3d');
    if (!cards.length) return;

    const MAX_TILT = 12;    /* degrees */
    const MAX_SHIFT = 8;    /* px for the shine layer */

    cards.forEach(card => {
        const shine = card.querySelector('.card-3d-shine');
        const inner = card.querySelector('.card-3d-inner');

        function handleMove(e) {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            const cx = rect.width / 2;
            const cy = rect.height / 2;

            const rotateY = ((x - cx) / cx) * MAX_TILT;
            const rotateX = ((cy - y) / cy) * MAX_TILT;

            if (inner) {
                inner.style.transform =
                    `perspective(600px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale3d(1.04,1.04,1.04)`;
            }

            if (shine) {
                const shineX = ((x - cx) / cx) * MAX_SHIFT;
                const shineY = ((y - cy) / cy) * MAX_SHIFT;
                shine.style.transform =
                    `translate(${shineX}px, ${shineY}px)`;
                shine.style.opacity = '0.45';
            }
        }

        function handleLeave() {
            if (inner) {
                inner.style.transform =
                    'perspective(600px) rotateX(0) rotateY(0) scale3d(1,1,1)';
                inner.style.transition = 'transform 0.5s cubic-bezier(0.22,1,0.36,1)';
            }
            if (shine) {
                shine.style.transform = 'translate(0,0)';
                shine.style.opacity = '0';
                shine.style.transition = 'transform 0.5s ease, opacity 0.5s ease';
            }
            setTimeout(() => {
                if (inner) inner.style.transition = '';
                if (shine) shine.style.transition = '';
            }, 500);
        }

        card.addEventListener('mousemove', handleMove, { passive: true });
        card.addEventListener('mouseleave', handleLeave);
    });

    /* ── Scroll-triggered 3D entrance for game cards ────── */
    if ('IntersectionObserver' in window) {
        const obs = new IntersectionObserver(entries => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('card-3d-visible');
                    obs.unobserve(entry.target);
                }
            });
        }, { threshold: 0.15 });

        cards.forEach(card => obs.observe(card));
    } else {
        cards.forEach(card => card.classList.add('card-3d-visible'));
    }

}());
