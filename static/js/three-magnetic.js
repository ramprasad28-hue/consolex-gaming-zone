/* ============================================================
   CONSOLEX — three-magnetic.js
   Magnetic hover effects for buttons and interactive elements
   Elements subtly follow the cursor, creating a 3D pull effect
   ============================================================ */

(function () {
    'use strict';

    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReduced) return;

    const MAGNETIC_STRENGTH = 0.3;
    const MAGNETIC_RADIUS = 120;

    const magnetics = document.querySelectorAll('.magnetic');
    if (!magnetics.length) return;

    magnetics.forEach(el => {
        const inner = el.querySelector('.magnetic-inner') || el;

        el.addEventListener('mousemove', e => {
            const rect = el.getBoundingClientRect();
            const x = e.clientX - rect.left - rect.width / 2;
            const y = e.clientY - rect.top - rect.height / 2;

            const moveX = x * MAGNETIC_STRENGTH;
            const moveY = y * MAGNETIC_STRENGTH;

            inner.style.transform = `translate(${moveX}px, ${moveY}px)`;
            inner.style.transition = 'transform 0.15s ease-out';
        }, { passive: true });

        el.addEventListener('mouseleave', () => {
            inner.style.transform = 'translate(0, 0)';
            inner.style.transition = 'transform 0.5s cubic-bezier(0.22, 1, 0.36, 1)';
        });
    });

    /* ── Button ripple effect ────────────────────────────── */
    document.querySelectorAll('.hero-btn-primary, .pc-btn-popular, .gs-cta-btn').forEach(btn => {
        btn.addEventListener('click', function (e) {
            const rect = this.getBoundingClientRect();
            const ripple = document.createElement('span');
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;

            ripple.style.cssText = `
                position: absolute;
                width: ${size}px;
                height: ${size}px;
                left: ${x}px;
                top: ${y}px;
                border-radius: 50%;
                background: rgba(255, 255, 255, 0.3);
                transform: scale(0);
                animation: rippleExpand 0.6s ease-out forwards;
                pointer-events: none;
                z-index: 10;
            `;

            this.style.position = 'relative';
            this.style.overflow = 'hidden';
            this.appendChild(ripple);

            setTimeout(() => ripple.remove(), 700);
        });
    });

    /* Inject ripple keyframes */
    if (!document.getElementById('ripple-keyframes')) {
        const style = document.createElement('style');
        style.id = 'ripple-keyframes';
        style.textContent = `
            @keyframes rippleExpand {
                to { transform: scale(2.5); opacity: 0; }
            }
        `;
        document.head.appendChild(style);
    }

    /* ── Parallax tilt on hero buttons ───────────────────── */
    const heroBtns = document.querySelectorAll('.hero-btn-primary, .hero-btn-ghost');
    heroBtns.forEach(btn => {
        btn.addEventListener('mousemove', e => {
            const rect = btn.getBoundingClientRect();
            const x = (e.clientX - rect.left) / rect.width - 0.5;
            const y = (e.clientY - rect.top) / rect.height - 0.5;
            btn.style.transform = `perspective(400px) rotateY(${x * 8}deg) rotateX(${-y * 8}deg) translateY(-3px)`;
            btn.style.transition = 'transform 0.15s ease-out';
        }, { passive: true });

        btn.addEventListener('mouseleave', () => {
            btn.style.transform = '';
            btn.style.transition = 'transform 0.4s cubic-bezier(0.22, 1, 0.36, 1)';
        });
    });

}());
