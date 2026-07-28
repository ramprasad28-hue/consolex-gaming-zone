/**
 * CONSOLEX — components.js (V3 Batch 2 — Interactive Component Library)
 * Handles: modals, drawers, accordions, tabs, toasts, tooltips, popovers.
 * No dependencies. Vanilla JS. IIFE-wrapped.
 */
(function () {
    'use strict';

    /* ========================================================
       MODAL
       ======================================================== */
    var cxModal = {
        /** Open a modal by element or selector */
        open: function (modalOrSelector) {
            var modal = typeof modalOrSelector === 'string'
                ? document.querySelector(modalOrSelector)
                : modalOrSelector;
            if (!modal) return;
            modal.classList.add('is-active');
            modal.setAttribute('aria-hidden', 'false');
            document.body.style.overflow = 'hidden';

            var firstFocusable = modal.querySelector(
                'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
            );
            if (firstFocusable) firstFocusable.focus();

            modal._cxKeyHandler = function (e) {
                if (e.key === 'Escape') cxModal.close(modal);
                if (e.key === 'Tab') cxModal._trapFocus(modal, e);
            };
            document.addEventListener('keydown', modal._cxKeyHandler);
        },

        /** Close a modal */
        close: function (modalOrSelector) {
            var modal = typeof modalOrSelector === 'string'
                ? document.querySelector(modalOrSelector)
                : modalOrSelector;
            if (!modal) return;
            modal.classList.remove('is-active');
            modal.setAttribute('aria-hidden', 'true');
            document.body.style.overflow = '';
            if (modal._cxKeyHandler) {
                document.removeEventListener('keydown', modal._cxKeyHandler);
                modal._cxKeyHandler = null;
            }
        },

        /** Toggle a modal */
        toggle: function (modalOrSelector) {
            var modal = typeof modalOrSelector === 'string'
                ? document.querySelector(modalOrSelector)
                : modalOrSelector;
            if (!modal) return;
            if (modal.classList.contains('is-active')) {
                cxModal.close(modal);
            } else {
                cxModal.open(modal);
            }
        },

        /** Focus trap */
        _trapFocus: function (modal, e) {
            var focusables = modal.querySelectorAll(
                'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
            );
            if (!focusables.length) return;
            var first = focusables[0];
            var last = focusables[focusables.length - 1];
            if (e.shiftKey) {
                if (document.activeElement === first) {
                    e.preventDefault();
                    last.focus();
                }
            } else {
                if (document.activeElement === last) {
                    e.preventDefault();
                    first.focus();
                }
            }
        }
    };

    /* ========================================================
       DRAWER
       ======================================================== */
    var cxDrawer = {
        open: function (drawerOrSelector) {
            var drawer = typeof drawerOrSelector === 'string'
                ? document.querySelector(drawerOrSelector)
                : drawerOrSelector;
            if (!drawer) return;
            drawer.classList.add('is-active');
            drawer.setAttribute('aria-hidden', 'false');
            document.body.style.overflow = 'hidden';

            drawer._cxKeyHandler = function (e) {
                if (e.key === 'Escape') cxDrawer.close(drawer);
            };
            document.addEventListener('keydown', drawer._cxKeyHandler);
        },
        close: function (drawerOrSelector) {
            var drawer = typeof drawerOrSelector === 'string'
                ? document.querySelector(drawerOrSelector)
                : drawerOrSelector;
            if (!drawer) return;
            drawer.classList.remove('is-active');
            drawer.setAttribute('aria-hidden', 'true');
            document.body.style.overflow = '';
            if (drawer._cxKeyHandler) {
                document.removeEventListener('keydown', drawer._cxKeyHandler);
                drawer._cxKeyHandler = null;
            }
        },
        toggle: function (drawerOrSelector) {
            var drawer = typeof drawerOrSelector === 'string'
                ? document.querySelector(drawerOrSelector)
                : drawerOrSelector;
            if (!drawer) return;
            if (drawer.classList.contains('is-active')) {
                cxDrawer.close(drawer);
            } else {
                cxDrawer.open(drawer);
            }
        }
    };

    /* ========================================================
       ACCORDION
       ======================================================== */
    function initAccordions() {
        document.querySelectorAll('.cx-accordion').forEach(function (accordion) {
            var triggers = accordion.querySelectorAll('.cx-accordion-trigger');
            triggers.forEach(function (trigger) {
                trigger.addEventListener('click', function () {
                    var item = trigger.closest('.cx-accordion-item');
                    var isOpen = item.classList.contains('is-open');

                    /* Close siblings if accordion is single-mode */
                    if (!accordion.hasAttribute('data-multi')) {
                        accordion.querySelectorAll('.cx-accordion-item.is-open').forEach(function (openItem) {
                            if (openItem !== item) {
                                openItem.classList.remove('is-open');
                                openItem.querySelector('.cx-accordion-trigger').setAttribute('aria-expanded', 'false');
                            }
                        });
                    }

                    item.classList.toggle('is-open', !isOpen);
                    trigger.setAttribute('aria-expanded', String(!isOpen));
                });
            });
        });
    }

    /* ========================================================
       TABS
       ======================================================== */
    function initTabs() {
        document.querySelectorAll('.cx-tabs').forEach(function (tabsEl) {
            var tabList = tabsEl.querySelector('.cx-tabs-list');
            var tabs = tabsEl.querySelectorAll('.cx-tab');
            var panels = tabsEl.querySelectorAll('.cx-tab-panel');

            tabs.forEach(function (tab) {
                tab.addEventListener('click', function () {
                    var targetId = tab.getAttribute('data-tab');
                    if (!targetId) return;

                    tabs.forEach(function (t) { t.classList.remove('cx-tab--active'); });
                    panels.forEach(function (p) { p.hidden = true; });

                    tab.classList.add('cx-tab--active');
                    tab.setAttribute('aria-selected', 'true');
                    var targetPanel = tabsEl.querySelector('#' + targetId);
                    if (targetPanel) targetPanel.hidden = false;
                });

                tab.addEventListener('keydown', function (e) {
                    var tabArray = Array.from(tabs);
                    var index = tabArray.indexOf(tab);
                    var next;

                    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
                        e.preventDefault();
                        next = tabArray[(index + 1) % tabArray.length];
                    } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
                        e.preventDefault();
                        next = tabArray[(index - 1 + tabArray.length) % tabArray.length];
                    } else if (e.key === 'Home') {
                        e.preventDefault();
                        next = tabArray[0];
                    } else if (e.key === 'End') {
                        e.preventDefault();
                        next = tabArray[tabArray.length - 1];
                    }

                    if (next) {
                        next.click();
                        next.focus();
                    }
                });
            });
        });
    }

    /* ========================================================
       TOAST NOTIFICATIONS
       ======================================================== */
    var cxToast = {
        _container: null,

        _getContainer: function () {
            if (!this._container) {
                this._container = document.createElement('div');
                this._container.className = 'cx-toast-container';
                this._container.setAttribute('aria-live', 'polite');
                this._container.setAttribute('role', 'status');
                document.body.appendChild(this._container);
            }
            return this._container;
        },

        /**
         * Show a toast notification.
         * @param {string} message
         * @param {object} opts - { type: 'success'|'error'|'warning'|'info', duration: ms }
         */
        show: function (message, opts) {
            opts = opts || {};
            var type = opts.type || 'info';
            var duration = opts.duration || 4000;

            var icons = {
                success: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
                error: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
                warning: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
                info: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>'
            };

            var toast = document.createElement('div');
            toast.className = 'cx-toast cx-toast--' + type;
            toast.innerHTML =
                '<span class="cx-toast-icon">' + (icons[type] || icons.info) + '</span>' +
                '<span class="cx-toast-content">' + message + '</span>' +
                '<button class="cx-toast-dismiss" aria-label="Dismiss">&times;</button>';

            toast.querySelector('.cx-toast-dismiss').addEventListener('click', function () {
                cxToast._dismiss(toast);
            });

            this._getContainer().appendChild(toast);

            setTimeout(function () {
                cxToast._dismiss(toast);
            }, duration);
        },

        _dismiss: function (toast) {
            if (toast.classList.contains('cx-toast--leaving')) return;
            toast.classList.add('cx-toast--leaving');
            setTimeout(function () {
                if (toast.parentNode) toast.parentNode.removeChild(toast);
            }, 250);
        },

        success: function (msg, opts) { this.show(msg, Object.assign({}, opts, { type: 'success' })); },
        error: function (msg, opts) { this.show(msg, Object.assign({}, opts, { type: 'error' })); },
        warning: function (msg, opts) { this.show(msg, Object.assign({}, opts, { type: 'warning' })); },
        info: function (msg, opts) { this.show(msg, Object.assign({}, opts, { type: 'info' })); }
    };

    /* ========================================================
       DATA ATTRIBUTION — Auto-bind data-cx-* triggers
       ======================================================== */
    function initDataBindings() {
        /* data-cx-modal-open / data-cx-modal-close */
        document.addEventListener('click', function (e) {
            var openTrigger = e.target.closest('[data-cx-modal-open]');
            if (openTrigger) {
                e.preventDefault();
                cxModal.open(openTrigger.getAttribute('data-cx-modal-open'));
            }

            var closeTrigger = e.target.closest('[data-cx-modal-close]');
            if (closeTrigger) {
                e.preventDefault();
                cxModal.close(closeTrigger.getAttribute('data-cx-modal-close') || closeTrigger.closest('.cx-modal'));
            }

            var drawerOpen = e.target.closest('[data-cx-drawer-open]');
            if (drawerOpen) {
                e.preventDefault();
                cxDrawer.open(drawerOpen.getAttribute('data-cx-drawer-open'));
            }

            var drawerClose = e.target.closest('[data-cx-drawer-close]');
            if (drawerClose) {
                e.preventDefault();
                cxDrawer.close(drawerClose.getAttribute('data-cx-drawer-close') || drawerClose.closest('.cx-drawer'));
            }
        });

        /* Close modal/drawer on backdrop click */
        document.addEventListener('click', function (e) {
            if (e.target.classList.contains('cx-backdrop')) {
                var activeModal = document.querySelector('.cx-modal.is-active');
                if (activeModal) cxModal.close(activeModal);
                var activeDrawer = document.querySelector('.cx-drawer.is-active');
                if (activeDrawer) cxDrawer.close(activeDrawer);
            }
        });
    }

    /* ========================================================
       DISMISSIBLE ALERTS
       ======================================================== */
    function initAlertDismiss() {
        document.addEventListener('click', function (e) {
            var dismissBtn = e.target.closest('.cx-alert-dismiss');
            if (dismissBtn) {
                var alert = dismissBtn.closest('.cx-alert');
                if (alert) {
                    alert.style.transition = 'opacity 0.2s, transform 0.2s';
                    alert.style.opacity = '0';
                    alert.style.transform = 'translateY(-8px)';
                    setTimeout(function () {
                        if (alert.parentNode) alert.parentNode.removeChild(alert);
                    }, 200);
                }
            }
        });
    }

    /* ========================================================
       INIT
       ======================================================== */
    function init() {
        initAccordions();
        initTabs();
        initDataBindings();
        initAlertDismiss();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    /* Expose public API on window.cx */
    window.cx = window.cx || {};
    window.cx.modal = cxModal;
    window.cx.drawer = cxDrawer;
    window.cx.toast = cxToast;

}());
