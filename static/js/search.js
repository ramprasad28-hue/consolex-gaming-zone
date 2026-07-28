/* ============================================================
   CONSOLEX — search.js  (V3 — Batch 6)
   Unified client-side search / filter helpers.
   ============================================================ */

(function () {
    'use strict';

    /* ── Debounce helper ──────────────────────────────────── */
    function debounce(fn, ms) {
        var timer;
        return function () {
            var ctx = this, args = arguments;
            clearTimeout(timer);
            timer = setTimeout(function () { fn.apply(ctx, args); }, ms);
        };
    }

    /* ── Quick card filter (games, tournaments, etc.) ──────── */
    function initCardFilter(config) {
        /* config: { container, input, cardSelector, getTerms } */
        var container = document.querySelector(config.container);
        var input     = document.querySelector(config.input);
        if (!container || !input) return;

        var cards = container.querySelectorAll(config.cardSelector);
        if (!cards.length) return;

        var filter = debounce(function () {
            var q = input.value.trim().toLowerCase();
            var showCount = 0;
            cards.forEach(function (card) {
                var terms = config.getTerms(card);
                var match = !q || terms.indexOf(q) !== -1 || terms.some(function (t) {
                    return t.indexOf(q) !== -1;
                });
                card.style.display = match ? '' : 'none';
                if (match) showCount++;
            });
            /* Emit event for result count display */
            container.dispatchEvent(new CustomEvent('filter', {
                detail: { total: cards.length, shown: showCount }
            }));
        }, 200);

        input.addEventListener('input', filter);
    }

    /* ── Autofocus search on slash key ─────────────────────── */
    document.addEventListener('keydown', function (e) {
        if (e.key === '/' && !e.ctrlKey && !e.metaKey) {
            var target = e.target;
            if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) return;
            e.preventDefault();
            var search = document.querySelector('[role="search"] input[type="search"]');
            if (search) search.focus();
        }
    });

    /* ── Auto-submit select changes ─────────────────────────── */
    document.addEventListener('change', function (e) {
        if (e.target.matches('select[name="category"], select[name="badge"], select[name="sort"], select[name="status"]')) {
            var form = e.target.closest('form');
            if (form) form.submit();
        }
    });

    /* Expose for debugging */
    window.cxSearch = { initCardFilter: initCardFilter, debounce: debounce };

})();
