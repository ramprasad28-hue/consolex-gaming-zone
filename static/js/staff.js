(function () {
    'use strict';

    /* ── Sidebar toggle ── */
    var sidebar = document.getElementById('spSidebar');
    var backdrop = document.getElementById('spSidebarBackdrop');
    var toggleBtn = document.getElementById('spSidebarToggle');

    if (sidebar && toggleBtn) {
        function openSidebar() {
            sidebar.classList.add('is-open');
            if (backdrop) backdrop.classList.add('is-shown');
        }

        function closeSidebar() {
            sidebar.classList.remove('is-open');
            if (backdrop) backdrop.classList.remove('is-shown');
        }

        toggleBtn.addEventListener('click', function (e) {
            e.stopPropagation();
            if (sidebar.classList.contains('is-open')) {
                closeSidebar();
            } else {
                openSidebar();
            }
        });

        if (backdrop) {
            backdrop.addEventListener('click', closeSidebar);
        }

        // Close on Escape
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && sidebar.classList.contains('is-open')) {
                closeSidebar();
            }
        });
    }

    /* ── Import dropzone ── */
    var dropzone = document.getElementById('spDropzone');
    var fileInput = document.getElementById('spFileInput');

    if (dropzone && fileInput) {
        dropzone.addEventListener('click', function () {
            fileInput.click();
        });

        dropzone.addEventListener('dragover', function (e) {
            e.preventDefault();
            dropzone.classList.add('is-dragover');
        });

        dropzone.addEventListener('dragleave', function () {
            dropzone.classList.remove('is-dragover');
        });

        dropzone.addEventListener('drop', function (e) {
            e.preventDefault();
            dropzone.classList.remove('is-dragover');
            if (e.dataTransfer.files.length) {
                fileInput.files = e.dataTransfer.files;
                fileInput.dispatchEvent(new Event('change'));
            }
        });

        fileInput.addEventListener('change', function () {
            var fileName = this.files[0] ? this.files[0].name : '';
            var label = dropzone.querySelector('.sp-import-dropzone-text');
            if (label && fileName) {
                label.textContent = fileName;
            }
        });
    }

    /* ── Communication audience chips ── */
    var chips = document.querySelectorAll('.sp-comm-chip');
    chips.forEach(function (chip) {
        chip.addEventListener('click', function () {
            this.classList.toggle('is-selected');
        });
    });

    /* ── Auto-submit filters ── */
    var filterSelects = document.querySelectorAll('.sp-toolbar select[data-auto-submit]');
    filterSelects.forEach(function (sel) {
        sel.addEventListener('change', function () {
            var form = this.closest('form');
            if (form) form.submit();
        });
    });

    /* ── Search debounce ── */
    var searchInputs = document.querySelectorAll('.sp-search-wrap input[type="search"]');
    searchInputs.forEach(function (input) {
        var timer;
        input.addEventListener('input', function () {
            clearTimeout(timer);
            timer = setTimeout(function () {
                var form = input.closest('form');
                if (form) form.submit();
            }, 400);
        });
    });

    /* ── Ch12: Live sessions console (30s poll) ── */
    var POLL_URL = document.querySelector('[data-live-sessions-data-url]');
    var LIVE_URL = POLL_URL ? POLL_URL.getAttribute('data-live-sessions-data-url') : '/staff/live-sessions/data/';

    function liveCountEls() {
        return document.querySelectorAll('[data-live-count], [data-live-count-big], [data-live-nav-count]');
    }

    function setLiveCounts(count) {
        liveCountEls().forEach(function (el) {
            el.textContent = count;
            el.hidden = count === 0;
        });
    }

    function makeSessionRow(s) {
        var item = document.createElement('div');
        item.className = 'sp-activity-item';
        item.setAttribute('data-live-session-id', s.id);

        var dot = document.createElement('span');
        dot.className = 'sp-activity-dot is-success is-pulse';
        dot.setAttribute('aria-hidden', 'true');

        var body = document.createElement('div');
        var text = document.createElement('div');
        text.className = 'sp-activity-text';
        var strong = document.createElement('strong');
        strong.textContent = s.customer;
        text.appendChild(strong);
        text.appendChild(document.createTextNode(' · ' + (s.console || '—') + ' · ' + s.start_time + '–' + s.end_time));

        var meta = document.createElement('div');
        meta.className = 'sp-activity-time';
        var remaining = document.createElement('span');
        remaining.setAttribute('data-live-remaining', '');
        remaining.setAttribute('data-session-end', s.session_end || '');
        remaining.textContent = s.remaining_minutes + ' min left';
        meta.appendChild(remaining);
        meta.appendChild(document.createTextNode(' · checked in ' + s.checked_in_at));

        body.appendChild(text);
        body.appendChild(meta);

        var actions = document.createElement('div');
        actions.className = 'sp-activity-actions';

        var details = document.createElement('a');
        details.className = 'cx-btn cx-btn--ghost cx-btn--sm';
        details.href = '/staff/bookings/' + s.id + '/';
        details.textContent = 'Open';
        actions.appendChild(details);

        item.appendChild(dot);
        item.appendChild(body);
        item.appendChild(actions);
        return item;
    }

    function renderLiveSessions(data) {
        var list = document.querySelector('[data-live-sessions-list]');
        var body = document.querySelector('[data-live-sessions-body]');
        if (!body) return;

        setLiveCounts(data.count);

        if (!list) {
            list = document.createElement('div');
            list.className = 'sp-activity';
            list.setAttribute('data-live-sessions-list', '');
            body.appendChild(list);
        }
        list.innerHTML = '';

        if (data.sessions && data.sessions.length) {
            data.sessions.forEach(function (s) {
                list.appendChild(makeSessionRow(s));
            });
        } else {
            list.remove();
            body.innerHTML = '<div class="cx-empty" role="status">' +
                '<div class="cx-empty-title">No live sessions</div>' +
                '<div class="cx-empty-desc">Checked-in players will appear here.</div>' +
                '</div>';
        }
    }

    function pollLiveSessions() {
        if (!document.querySelector('[data-live-sessions-body]')) return;
        fetch(LIVE_URL, { headers: { 'Accept': 'application/json' } })
            .then(function (resp) { return resp.ok ? resp.json() : null; })
            .then(function (data) { if (data) renderLiveSessions(data); })
            .catch(function () { /* transient — retry next tick */ });
    }

    function refreshCountdowns() {
        var now = new Date();
        document.querySelectorAll('[data-live-remaining]').forEach(function (el) {
            var endStr = el.getAttribute('data-session-end');
            if (!endStr) return;
            var end = new Date(endStr.replace(' ', 'T'));
            var mins = Math.max(0, Math.round((end - now) / 60000));
            el.textContent = mins + ' min left';
        });
    }

    // Poll only on staff pages (endpoint exists there).
    if (document.querySelector('[data-live-sessions-body], [data-live-nav-count], [data-live-count]')) {
        refreshCountdowns();
        setInterval(pollLiveSessions, 30000);
        setInterval(refreshCountdowns, 30000);
    }

    /* ── Desktop sidebar collapse (persisted) ── */
    var shell = document.getElementById('spShell');
    var collapseBtn = document.getElementById('spSidebarCollapse');

    if (shell && collapseBtn) {
        var COLLAPSE_KEY = 'cx-staff-sidebar-collapsed';
        var savedCollapsed = false;
        try { savedCollapsed = localStorage.getItem(COLLAPSE_KEY) === '1'; } catch (e) { /* ignore */ }

        if (savedCollapsed && window.matchMedia('(min-width: 1025px)').matches) {
            shell.classList.add('is-collapsed');
        }

        collapseBtn.addEventListener('click', function () {
            var collapsed = shell.classList.toggle('is-collapsed');
            try { localStorage.setItem(COLLAPSE_KEY, collapsed ? '1' : '0'); } catch (e) { /* ignore */ }
        });
    }

    /* ── Topbar dropdowns ── */
    function closeAllDropdowns(except) {
        document.querySelectorAll('.sp-dropdown.is-open').forEach(function (d) {
            if (except && d === except) return;
            d.classList.remove('is-open');
            var t = d.querySelector('[data-dropdown-toggle]');
            if (t) t.setAttribute('aria-expanded', 'false');
        });
    }

    document.querySelectorAll('[data-dropdown-toggle]').forEach(function (btn) {
        var parent = btn.closest('.sp-dropdown');
        if (!parent) return;

        function closeDropdown() {
            parent.classList.remove('is-open');
            btn.setAttribute('aria-expanded', 'false');
        }

        btn.addEventListener('click', function (e) {
            e.stopPropagation();
            if (parent.classList.contains('is-open')) {
                closeDropdown();
            } else {
                closeAllDropdowns(parent);
                parent.classList.add('is-open');
                btn.setAttribute('aria-expanded', 'true');
            }
        });

        parent.addEventListener('click', function (e) {
            var activated = e.target.closest('.sp-dropdown-item, .sp-dropdown-menu a, .sp-dropdown-menu button');
            if (activated) closeDropdown();
        });
    });

    document.addEventListener('click', function (e) {
        if (!e.target.closest('.sp-dropdown')) closeAllDropdowns();
    });

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') closeAllDropdowns();
    });

    /* ── Animated counters (once, honours reduced motion) ── */
    function animateCount(el) {
        var target = parseInt(el.getAttribute('data-count'), 10);
        if (isNaN(target)) return;

        var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        if (reduced) { el.textContent = target; return; }

        var duration = 900;
        var start = null;

        function frame(ts) {
            if (start === null) start = ts;
            var p = Math.min((ts - start) / duration, 1);
            var eased = 1 - Math.pow(1 - p, 3);
            el.textContent = Math.round(eased * target);
            if (p < 1) requestAnimationFrame(frame);
            else el.textContent = target;
        }

        requestAnimationFrame(frame);
    }

    var counters = document.querySelectorAll('[data-count]');
    if (counters.length) {
        if ('IntersectionObserver' in window) {
            var counterObserver = new IntersectionObserver(function (entries, obs) {
                entries.forEach(function (entry) {
                    if (entry.isIntersecting) {
                        animateCount(entry.target);
                        obs.unobserve(entry.target);
                    }
                });
            }, { threshold: 0.3 });
            counters.forEach(function (el) { counterObserver.observe(el); });
        } else {
            counters.forEach(animateCount);
        }
    }

    /* ── Ripple on .sp-ripple elements ── */
    document.querySelectorAll('.sp-ripple').forEach(function (el) {
        el.addEventListener('click', function (e) {
            var rect = el.getBoundingClientRect();
            var d = Math.max(rect.width, rect.height);
            var ink = document.createElement('span');
            ink.className = 'sp-ripple-ink';
            ink.style.width = d + 'px';
            ink.style.height = d + 'px';
            ink.style.left = (e.clientX - rect.left - d / 2) + 'px';
            ink.style.top = (e.clientY - rect.top - d / 2) + 'px';
            el.appendChild(ink);
            window.setTimeout(function () { if (ink.parentNode) ink.parentNode.removeChild(ink); }, 600);
        });
    });

    /* ── Booking detail drawer ── */
    var drawer = document.getElementById('spBookingDrawer');
    var drawerBackdrop = document.getElementById('spDrawerBackdrop');
    var drawerBody = document.querySelector('[data-sp-drawer-body]');
    var drawerTitle = document.getElementById('spDrawerTitle');
    var lastTrigger = null;

    function closeDrawer() {
        if (!drawer) return;
        drawer.classList.remove('is-open');
        drawer.setAttribute('aria-hidden', 'true');
        if (drawerBackdrop) drawerBackdrop.classList.remove('is-shown');
        document.body.classList.remove('sp-no-scroll');
        if (lastTrigger && typeof lastTrigger.focus === 'function') lastTrigger.focus();
        lastTrigger = null;
    }

    if (drawer) {
        document.querySelectorAll('[data-sp-drawer-open]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var id = btn.getAttribute('data-sp-drawer-open');
                var tpl = document.querySelector('[data-sp-drawer-template="' + id + '"]');
                if (!tpl) return;
                lastTrigger = btn;
                if (drawerBody) {
                    drawerBody.innerHTML = '';
                    drawerBody.appendChild(document.importNode(tpl.content, true));
                }
                if (drawerTitle) {
                    drawerTitle.textContent = btn.getAttribute('data-sp-drawer-title') || 'Booking details';
                }
                drawer.classList.add('is-open');
                drawer.setAttribute('aria-hidden', 'false');
                if (drawerBackdrop) drawerBackdrop.classList.add('is-shown');
                document.body.classList.add('sp-no-scroll');
                var closeBtn = drawer.querySelector('[data-sp-drawer-close]');
                if (closeBtn) closeBtn.focus();
            });
        });

        document.querySelectorAll('[data-sp-drawer-close]').forEach(function (btn) {
            btn.addEventListener('click', closeDrawer);
        });
        if (drawerBackdrop) {
            drawerBackdrop.addEventListener('click', closeDrawer);
        }
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && drawer.classList.contains('is-open')) closeDrawer();
        });
    }

})();
