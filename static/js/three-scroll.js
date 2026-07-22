/* ============================================================
   CONSOLEX — three-scroll.js
   Scroll-driven 3D animations
   - IntersectionObserver-based reveal system
   - Parallax depth on sections
   - 3D tilt on pricing cards
   - Text character stagger animations
   ============================================================ */

(function () {
    'use strict';

    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReduced) return;

    /* ── Scroll Reveal ──────────────────────────────────── */
    const revealEls = document.querySelectorAll('[data-reveal]');
    if (revealEls.length && 'IntersectionObserver' in window) {
        const revealObs = new IntersectionObserver(
            entries => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('revealed');
                        revealObs.unobserve(entry.target);
                    }
                });
            },
            { threshold: 0.12, rootMargin: '0px 0px -40px 0px' }
        );
        revealEls.forEach(el => revealObs.observe(el));
    } else {
        revealEls.forEach(el => el.classList.add('revealed'));
    }

    /* ── Section Parallax on Scroll ─────────────────────── */
    const parallaxSections = document.querySelectorAll('.parallax-section');
    if (parallaxSections.length) {
        let ticking = false;

        function updateParallax() {
            const scrollY = window.pageYOffset;
            parallaxSections.forEach(section => {
                const rect = section.getBoundingClientRect();
                const center = rect.top + rect.height / 2;
                const viewCenter = window.innerHeight / 2;
                const offset = (center - viewCenter) / window.innerHeight;

                const bg = section.querySelector('.parallax-bg');
                if (bg) {
                    bg.style.transform = `translateY(${offset * -60}px) scale(1.1)`;
                }

                const content = section.querySelector('.parallax-content');
                if (content) {
                    content.style.transform = `translateY(${offset * -20}px)`;
                }
            });
            ticking = false;
        }

        window.addEventListener('scroll', () => {
            if (!ticking) {
                requestAnimationFrame(updateParallax);
                ticking = true;
            }
        }, { passive: true });
    }

    /* ── 3D Pricing Card Tilt ───────────────────────────── */
    const pricingCards = document.querySelectorAll('.pc-card');
    if (pricingCards.length) {
        const MAX_TILT = 8;

        pricingCards.forEach(card => {
            const inner = card;

            function handleMove(e) {
                const rect = card.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                const cx = rect.width / 2;
                const cy = rect.height / 2;

                const rotateY = ((x - cx) / cx) * MAX_TILT;
                const rotateX = ((cy - y) / cy) * MAX_TILT;

                inner.style.transform =
                    `perspective(800px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-8px) scale(1.01)`;
            }

            function handleLeave() {
                inner.style.transform = '';
                inner.style.transition = 'transform 0.5s cubic-bezier(0.22,1,0.36,1)';
                setTimeout(() => { inner.style.transition = ''; }, 500);
            }

            card.addEventListener('mousemove', handleMove, { passive: true });
            card.addEventListener('mouseleave', handleLeave);
        });
    }

    /* ── Staggered Grid Entry ───────────────────────────── */
    const staggerGrids = document.querySelectorAll('[data-stagger]');
    if (staggerGrids.length && 'IntersectionObserver' in window) {
        const gridObs = new IntersectionObserver(
            entries => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const children = entry.target.children;
                        Array.from(children).forEach((child, i) => {
                            child.style.transitionDelay = `${i * 0.08}s`;
                            child.classList.add('revealed');
                        });
                        gridObs.unobserve(entry.target);
                    }
                });
            },
            { threshold: 0.1 }
        );
        staggerGrids.forEach(grid => gridObs.observe(grid));
    }

    /* ── 3D Text Reveal (character split) ───────────────── */
    const textRevealEls = document.querySelectorAll('[data-text-reveal]');
    if (textRevealEls.length && 'IntersectionObserver' in window) {
        const textObs = new IntersectionObserver(
            entries => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const el = entry.target;
                        const text = el.textContent;
                        el.textContent = '';
                        el.style.opacity = '1';

                        [...text].forEach((char, i) => {
                            const span = document.createElement('span');
                            span.textContent = char === ' ' ? '\u00A0' : char;
                            span.style.display = 'inline-block';
                            span.style.opacity = '0';
                            span.style.transform = 'translateY(20px) rotateX(-40deg)';
                            span.style.transition = `opacity 0.5s ${i * 0.03}s cubic-bezier(0.22,1,0.36,1), transform 0.5s ${i * 0.03}s cubic-bezier(0.22,1,0.36,1)`;
                            el.appendChild(span);
                        });

                        requestAnimationFrame(() => {
                            el.querySelectorAll('span').forEach(span => {
                                span.style.opacity = '1';
                                span.style.transform = 'translateY(0) rotateX(0)';
                            });
                        });

                        textObs.unobserve(el);
                    }
                });
            },
            { threshold: 0.3 }
        );
        textRevealEls.forEach(el => textObs.observe(el));
    }

    /* ── Dynamic glow follow cursor ─────────────────────── */
    const glowCursors = document.querySelectorAll('.glow-cursor');
    glowCursors.forEach(el => {
        el.addEventListener('mousemove', e => {
            const rect = el.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            el.style.setProperty('--glow-x', `${x}px`);
            el.style.setProperty('--glow-y', `${y}px`);
        }, { passive: true });
    });

    /* ── Smooth anchor scrolling ────────────────────────── */
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

}());
