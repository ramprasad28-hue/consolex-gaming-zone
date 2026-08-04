/* CONSOLEX — auth.js  (V4 · Ch9)
   Shared behaviours for the auth split-screen templates.
   Password visibility, caps-lock warning, strength meter, loading submit. */
(function () {
    'use strict';

    /* ── Password visibility toggle ─────────────────────── */
    function initPasswordToggles() {
        document.querySelectorAll('[data-cx-pw-toggle]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var wrap = btn.closest('.auth-pw-wrap');
                var input = wrap ? wrap.querySelector('input') : null;
                if (!input) return;
                var eyeOpen = btn.querySelector('.pw-eye-open');
                var eyeClosed = btn.querySelector('.pw-eye-closed');
                if (input.type === 'password') {
                    input.type = 'text';
                    if (eyeOpen) eyeOpen.style.display = 'none';
                    if (eyeClosed) eyeClosed.style.display = 'block';
                    btn.setAttribute('aria-label', 'Hide password');
                } else {
                    input.type = 'password';
                    if (eyeOpen) eyeOpen.style.display = 'block';
                    if (eyeClosed) eyeClosed.style.display = 'none';
                    btn.setAttribute('aria-label', 'Show password');
                }
            });
        });
    }

    /* ── Caps-lock warning ──────────────────────────────── */
    function initCapsLock() {
        document.querySelectorAll('[data-cx-caps]').forEach(function (input) {
            var warn = input.closest('.form-group').querySelector('.caps-warn');
            if (!warn) return;
            function check(e) {
                var on = e.getModifierState && e.getModifierState('CapsLock');
                warn.classList.toggle('is-visible', !!on);
            }
            input.addEventListener('keydown', check);
            input.addEventListener('keyup', check);
        });
    }

    /* ── Password strength meter ────────────────────────── */
    function initStrengthMeter() {
        document.querySelectorAll('[data-cx-strength]').forEach(function (wrap) {
            var input = wrap.closest('.form-group').querySelector('input[type="password"]');
            if (!input) return;
            var bars = wrap.querySelectorAll('.pw-strength-bar');
            var label = wrap.querySelector('.pw-strength-label');
            var levels = [
                { min: 0, text: 'Too short', cls: '' },
                { min: 1, text: 'Weak', cls: 'is-weak' },
                { min: 2, text: 'Fair', cls: 'is-fair' },
                { min: 3, text: 'Good', cls: 'is-good' },
                { min: 4, text: 'Strong', cls: 'is-strong' }
            ];

            function score(value) {
                var s = 0;
                if (value.length >= 8) s++;
                if (/[a-z]/.test(value) && /[A-Z]/.test(value)) s++;
                if (/\d/.test(value)) s++;
                if (/[^A-Za-z0-9]/.test(value)) s++;
                return s;
            }

            input.addEventListener('input', function () {
                var s = score(input.value);
                var level = levels.filter(function (l) { return s >= l.min; }).pop();
                bars.forEach(function (bar, i) {
                    bar.classList.toggle('is-on', i < s);
                });
                wrap.classList.remove('is-weak', 'is-fair', 'is-good', 'is-strong');
                if (level.cls) wrap.classList.add(level.cls);
                if (label) label.textContent = input.value ? level.text : 'Password strength';
                wrap.setAttribute('aria-label', input.value ? 'Password strength: ' + level.text : 'Password strength');
            });
        });
    }

    /* ── Loading submit buttons ─────────────────────────── */
    function initLoadingButtons() {
        document.querySelectorAll('form').forEach(function (form) {
            var btn = form.querySelector('[data-cx-loading]');
            if (!btn) return;
            form.addEventListener('submit', function () {
                var label = btn.querySelector('.btn-label');
                if (label) {
                    btn.setAttribute('data-default-text', label.textContent);
                    label.textContent = btn.getAttribute('data-loading-text') || 'Please wait…';
                }
                btn.disabled = true;
                btn.classList.add('is-loading');
            });
        });
    }

    function init() {
        initPasswordToggles();
        initCapsLock();
        initStrengthMeter();
        initLoadingButtons();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
}());
