/**
 * CONSOLEX ThemeManager
 * Handles dark/light/system theme with system preference detection,
 * localStorage persistence, and smooth transitions.
 */
(function () {
    'use strict';

    var STORAGE_KEY = 'theme';
    var DARK = 'dark';
    var LIGHT = 'light';
    var SYSTEM = 'system';

    /** Current mode — light is always the default */
    function currentMode() {
        var saved = LIGHT;
        try {
            saved = localStorage.getItem(STORAGE_KEY) || LIGHT;
        } catch (e) {
            // localStorage unavailable (private mode, blocked storage) — default to light
        }
        return saved;
    }

    /** Get system color scheme preference */
    function getSystemPreference() {
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return DARK;
        }
        return LIGHT;
    }

    /** Resolve a mode ('light' | 'dark' | 'system') to a concrete theme */
    function resolveTheme(mode) {
        if (mode === SYSTEM) return getSystemPreference();
        return mode;
    }

    /** Apply theme to document */
    function applyTheme(mode) {
        var resolved = resolveTheme(mode);
        document.documentElement.setAttribute('data-theme', resolved);
        document.documentElement.setAttribute('data-theme-mode', mode);
        updateToggleIcon(resolved);
        updateThemeOptions(mode);
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

    /** Reflect active state on [data-theme-option] buttons */
    function updateThemeOptions(mode) {
        document.querySelectorAll('[data-theme-option]').forEach(function (btn) {
            var on = btn.getAttribute('data-theme-option') === mode;
            btn.classList.toggle('is-active', on);
            btn.setAttribute('aria-pressed', on ? 'true' : 'false');
        });
    }

    /** Save preference */
    function saveTheme(mode) {
        try {
            localStorage.setItem(STORAGE_KEY, mode);
        } catch (e) {
            // localStorage unavailable
        }
    }

    /** Set and persist a theme mode */
    function setTheme(mode) {
        applyTheme(mode);
        saveTheme(mode);
    }

    /** Toggle between dark and light */
    function toggleTheme() {
        var next = currentMode() === LIGHT ? DARK : LIGHT;
        setTheme(next);
    }

    /** Listen for system preference changes (only relevant in 'system' mode) */
    function watchSystemPreference() {
        if (!window.matchMedia) return;
        var mq = window.matchMedia('(prefers-color-scheme: dark)');
        var handler = function (e) {
            if (currentMode() === SYSTEM) {
                applyTheme(SYSTEM);
            }
        };
        if (mq.addEventListener) {
            mq.addEventListener('change', handler);
        } else if (mq.addListener) {
            mq.addListener(handler);
        }
    }

    /** Bind theme picker buttons ([data-theme-option]) */
    function bindThemeOptions() {
        document.querySelectorAll('[data-theme-option]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                setTheme(btn.getAttribute('data-theme-option'));
            });
        });
    }

    /** Initialize on DOM ready */
    function init() {
        applyTheme(currentMode());
        watchSystemPreference();
        bindThemeOptions();

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

    window.CXTheme = {
        setTheme: setTheme,
        currentMode: currentMode,
        resolveTheme: resolveTheme,
        getSystemPreference: getSystemPreference,
    };
})();
