/* ============================================================
   CONSOLEX — booking_wizard.js  (Phase 8 · Step 1)
   Handles: panel navigation, console selection, progress bar,
   live cost preview. Form still submits as one normal POST —
   no fields are renamed or removed.
   ============================================================ */
(function () {
    'use strict';

    var panels = document.querySelectorAll('.wiz-panel');
    var indicators = document.querySelectorAll('.wiz-step-indicator');
    var consoleError = document.getElementById('consoleError');

    function goToPanel(targetStep) {
        panels.forEach(function (panel) {
            var isTarget = panel.dataset.panel === String(targetStep);
            panel.classList.toggle('wiz-panel-active', isTarget);
        });

        indicators.forEach(function (ind) {
            var step = parseInt(ind.dataset.stepIndicator, 10);
            ind.classList.toggle('wiz-active', step === targetStep);
            ind.classList.toggle('wiz-done', step < targetStep);
        });

        // Scroll the wizard back into view on step change
        var wrap = document.querySelector('.wiz-wrap');
        if (wrap) {
            wrap.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }

    // Wire up every button that declares a data-goto target
    document.querySelectorAll('[data-goto]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var target = parseInt(btn.dataset.goto, 10);

            // Guard: don't allow leaving the console step without a selection
            if (target === 2) {
                var selected = document.querySelector('input[name="game_console"]:checked');
                if (!selected) {
                    if (consoleError) consoleError.hidden = false;
                    return;
                }
                if (consoleError) consoleError.hidden = true;
            }

            goToPanel(target);
        });
    });

    // Selecting a console clears any visible validation error
    document.querySelectorAll('input[name="game_console"]').forEach(function (radio) {
        radio.addEventListener('change', function () {
            if (consoleError) consoleError.hidden = true;
        });
    });

    /* ── Live cost preview (unchanged logic from the original form) ── */
    var RATE = { 1: 300, 2: 500, 3: 700, 4: 900 };
    var playersSelect = document.getElementById('playersSelect');
    var durationSelect = document.getElementById('durationSelect');
    var costPreview = document.getElementById('costPreview');

    function updateCost() {
        if (!playersSelect || !durationSelect || !costPreview) return;

        var players = parseInt(playersSelect.value, 10);
        var duration = parseInt(durationSelect.value, 10);
        var total = RATE[players] * duration;
        var advance = Math.round(total * 0.30);

        costPreview.innerHTML =
            'Estimated Total: <strong>\u20B9' + total + '</strong>' +
            '&nbsp;&nbsp;|&nbsp;&nbsp;Advance (30%): <strong>\u20B9' + advance + '</strong>';
    }

    if (playersSelect && durationSelect) {
        playersSelect.addEventListener('change', updateCost);
        durationSelect.addEventListener('change', updateCost);
        updateCost();
    }

}());
