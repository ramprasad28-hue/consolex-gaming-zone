/**
 * CONSOLEX ThemeManager
 * Handles dark/light theme with system preference detection,
 * localStorage persistence, and smooth transitions.
 */
(function () {
    'use strict';

    var STORAGE_KEY = 'theme';
    var DARK = 'dark';
    var LIGHT = 'light';

    /** Load saved theme — light is always the default */
    function loadTheme() {
        var saved = localStorage.getItem(STORAGE_KEY);
        return saved || LIGHT;
    }

    /** Apply theme to document */
    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        updateToggleIcon(theme);
    }

    /** Update toggle button icon visibility */
    function updateToggleIcon(theme) {
        var btn = document.getElementById('themeToggle');
        if (!btn) return;
        var sun = btn.querySelector('.icon-sun');
        var moon = btn.querySelector('.icon-moon');
        if (sun) sun.style.display = theme === DARK ? 'block' : 'none';
        if (moon) moon.style.display = theme === LIGHT ? 'block' : 'none';
    }

    /** Save preference */
    function saveTheme(theme) {
        try {
            localStorage.setItem(STORAGE_KEY, theme);
        } catch (e) {
            // localStorage unavailable
        }
    }

    /** Toggle between dark and light */
    function toggleTheme() {
        var current = document.documentElement.getAttribute('data-theme') || getSystemPreference();
        var next = current === LIGHT ? DARK : LIGHT;
        applyTheme(next);
        saveTheme(next);
    }

    /** Listen for system preference changes (only if user has no saved preference) */
    function watchSystemPreference() {
        if (!window.matchMedia) return;
        var mq = window.matchMedia('(prefers-color-scheme: dark)');
        var handler = function (e) {
            if (!localStorage.getItem(STORAGE_KEY)) {
                applyTheme(e.matches ? DARK : LIGHT);
            }
        };
        if (mq.addEventListener) {
            mq.addEventListener('change', handler);
        } else if (mq.addListener) {
            mq.addListener(handler);
        }
    }

    /** Initialize on DOM ready */
    function init() {
        applyTheme(loadTheme());
        watchSystemPreference();

        var btn = document.getElementById('themeToggle');
        if (btn) {
            btn.addEventListener('click', toggleTheme);
        }
    }

    // Run immediately since the script is loaded at end of body
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
