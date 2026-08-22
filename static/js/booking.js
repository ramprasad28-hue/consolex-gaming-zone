/**
 * CONSOLEX — booking.js (V4 Booking Wizard)
 * 6-step wizard: Console → Date → Time (+Duration) → Players → Summary → Payment
 * Step 3 uses the real availability API (/api/v1/bookings/availability/).
 * No dependencies. Vanilla JS. IIFE-wrapped.
 */
(function () {
    'use strict';

    var AVAILABILITY_URL = '/api/v1/bookings/availability/';

    /* ==========================================================
       STATE
       ========================================================== */
    var state = {
        step: 1,
        consoleId: null,
        consoleName: '',
        rateWD: 0,
        rateWE: 0,
        date: null,       // "YYYY-MM-DD"
        time: null,       // "HH:MM"
        players: 1,
        duration: 1,
        slots: [],        // [{start, end, available}] from API
        availLoading: false,
        availError: false,
        availSeq: 0       // guards against stale responses
    };

    /* ==========================================================
       DOM HELPERS
       ========================================================== */
    function $(sel, ctx) { return (ctx || document).querySelector(sel); }
    function $$(sel, ctx) { return Array.from((ctx || document).querySelectorAll(sel)); }

    function hideError(id) {
        var el = document.getElementById(id);
        if (el) { el.textContent = ''; el.style.display = 'none'; }
    }
    function showError(id, msg) {
        var el = document.getElementById(id);
        if (el) { el.textContent = msg; el.style.display = 'block'; }
    }

    /* ==========================================================
       STEP NAVIGATION
       ========================================================== */
    function goToStep(stepNum) {
        if (stepNum < 1 || stepNum > 6) return;

        /* Hide current panel */
        var current = $('#step-' + state.step);
        if (current) current.classList.remove('wiz-panel-active');

        /* Show target panel */
        var target = $('#step-' + stepNum);
        if (target) target.classList.add('wiz-panel-active');

        /* Update step indicators */
        $$('.wiz-step-indicator').forEach(function (ind) {
            var s = parseInt(ind.getAttribute('data-step'), 10);
            ind.classList.remove('wiz-active', 'wiz-done');
            ind.removeAttribute('aria-current');
            if (s < stepNum) {
                ind.classList.add('wiz-done');
                ind.querySelector('.wiz-step-circle').innerHTML =
                    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>';
            } else if (s === stepNum) {
                ind.classList.add('wiz-active');
                ind.setAttribute('aria-current', 'step');
                ind.querySelector('.wiz-step-circle').textContent = s;
            } else {
                ind.querySelector('.wiz-step-circle').textContent = s;
            }
        });

        state.step = stepNum;

        /* Prepare step-specific content */
        if (stepNum === 3) initTimeStep();
        if (stepNum === 5) updateSummary();
        if (stepNum === 6) updateConfirm();

        /* Scroll to top */
        window.scrollTo({ top: 0, behavior: 'smooth' });

        /* Focus management for a11y */
        var heading = target ? target.querySelector('.wiz-panel-title') : null;
        if (heading) {
            heading.setAttribute('tabindex', '-1');
            heading.focus();
        }
    }

    /* ==========================================================
       VALIDATION per step
       ========================================================== */
    function validateStep(stepNum) {
        switch (stepNum) {
            case 1:
                if (!state.consoleId) {
                    showError('err-console', 'Please select a console to continue.');
                    return false;
                }
                hideError('err-console');
                return true;
            case 2:
                if (!state.date) {
                    showError('err-date', 'Please select a date.');
                    return false;
                }
                hideError('err-date');
                return true;
            case 3:
                if (state.availLoading) {
                    showError('err-time', 'Still checking availability — one moment.');
                    return false;
                }
                if (state.availError) {
                    showError('err-time', 'Availability could not be loaded. Please retry.');
                    return false;
                }
                if (!state.time) {
                    showError('err-time', 'Please select a start time.');
                    return false;
                }
                var sel = findSlot(state.time);
                if (!sel || !sel.available) {
                    showError('err-time', 'That time is not available. Please choose another slot.');
                    return false;
                }
                hideError('err-time');
                return true;
            case 4:
                if (!state.players || state.players < 1) {
                    showError('err-players', 'Please select the number of players.');
                    return false;
                }
                hideError('err-players');
                return true;
        }
        return true;
    }

    /* ==========================================================
       STEP 1 — Console Selection
       ========================================================== */
    function initConsoleCards() {
        $$('.wiz-console-card').forEach(function (card) {
            card.addEventListener('click', function (e) {
                var radio = card.querySelector('.wiz-console-radio');
                if (radio && radio.disabled) return;

                /* Deselect all */
                $$('.wiz-console-card').forEach(function (c) {
                    c.classList.remove('wiz-console-selected');
                });

                /* Select this one */
                card.classList.add('wiz-console-selected');
                if (radio) radio.checked = true;

                state.consoleId = card.getAttribute('data-console-id');
                state.consoleName = card.getAttribute('data-console-name');
                state.rateWD = parseFloat(card.getAttribute('data-rate-wd')) || 0;
                state.rateWE = parseFloat(card.getAttribute('data-rate-we')) || 0;

                /* Update hidden field */
                var hf = document.getElementById('hf_console');
                if (hf) hf.value = state.consoleId;

                hideError('err-console');
                updateLiveRail();
            });

            /* Keyboard: Enter/Space to select */
            card.addEventListener('keydown', function (e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    card.click();
                }
            });
        });
    }

    /* ==========================================================
       STEP 2 — Calendar
       ========================================================== */
    var calYear, calMonth;

    function initCalendar() {
        var today = new Date();
        calYear = today.getFullYear();
        calMonth = today.getMonth();

        $('#calPrev').addEventListener('click', function () {
            calMonth--;
            if (calMonth < 0) { calMonth = 11; calYear--; }
            renderCalendar();
        });

        $('#calNext').addEventListener('click', function () {
            calMonth++;
            if (calMonth > 11) { calMonth = 0; calYear++; }
            renderCalendar();
        });

        renderCalendar();
    }

    function renderCalendar() {
        var grid = $('#calGrid');
        var monthLabel = $('#calMonth');
        var today = new Date();
        today.setHours(0, 0, 0, 0);

        var monthNames = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ];
        monthLabel.textContent = monthNames[calMonth] + ' ' + calYear;

        var firstDay = new Date(calYear, calMonth, 1).getDay();
        var daysInMonth = new Date(calYear, calMonth + 1, 0).getDate();

        grid.innerHTML = '';

        /* Empty cells before first day */
        for (var i = 0; i < firstDay; i++) {
            var empty = document.createElement('div');
            empty.className = 'wiz-cal-day wiz-cal-day--empty';
            empty.setAttribute('aria-hidden', 'true');
            grid.appendChild(empty);
        }

        /* Day cells */
        for (var d = 1; d <= daysInMonth; d++) {
            var cellDate = new Date(calYear, calMonth, d);
            cellDate.setHours(0, 0, 0, 0);
            var dateStr = formatDate(calYear, calMonth + 1, d);

            var cell = document.createElement('button');
            cell.type = 'button';
            cell.className = 'wiz-cal-day';
            cell.textContent = d;
            cell.setAttribute('data-date', dateStr);
            cell.setAttribute('aria-label', monthNames[calMonth] + ' ' + d + ', ' + calYear);

            if (cellDate < today) {
                cell.classList.add('wiz-cal-day--disabled');
                cell.disabled = true;
                cell.setAttribute('aria-disabled', 'true');
            }

            if (state.date === dateStr) {
                cell.classList.add('wiz-cal-day--selected');
                cell.setAttribute('aria-pressed', 'true');
            }

            if (cellDate.getTime() === today.getTime()) {
                cell.classList.add('wiz-cal-day--today');
            }

            cell.addEventListener('click', function () {
                var ds = this.getAttribute('data-date');
                state.date = ds;

                $$('.wiz-cal-day').forEach(function (c) {
                    c.classList.remove('wiz-cal-day--selected');
                    c.removeAttribute('aria-pressed');
                });
                this.classList.add('wiz-cal-day--selected');
                this.setAttribute('aria-pressed', 'true');

                /* Update hidden field */
                var hf = document.getElementById('hf_date');
                if (hf) hf.value = ds;

                /* Update display */
                var display = document.getElementById('selectedDateText');
                if (display) display.textContent = formatDateDisplay(ds);

                hideError('err-date');
                updateLiveRail();
            });

            grid.appendChild(cell);
        }

        /* If we're past the end of the month, disable "Next" for far future */
        /* (allow up to 30 days ahead) */
        var maxDate = new Date(today);
        maxDate.setDate(maxDate.getDate() + 30);
        var calNextBtn = $('#calNext');
        if (calYear > maxDate.getFullYear() ||
            (calYear === maxDate.getFullYear() && calMonth > maxDate.getMonth())) {
            calNextBtn.disabled = true;
            calNextBtn.setAttribute('aria-disabled', 'true');
        } else {
            calNextBtn.disabled = false;
            calNextBtn.removeAttribute('aria-disabled');
        }
    }

    function formatDate(y, m, d) {
        return y + '-' + String(m).padStart(2, '0') + '-' + String(d).padStart(2, '0');
    }

    function formatDateDisplay(dateStr) {
        var parts = dateStr.split('-');
        var d = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
        var days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
        var months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        return days[d.getDay()] + ', ' + d.getDate() + ' ' + months[d.getMonth()] + ' ' + d.getFullYear();
    }

    /* ==========================================================
       STEP 3 — Time & Duration (real availability)
       ========================================================== */
    var LOCK_SVG =
        '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>';

    function parseHM(t) {
        var p = t.split(':');
        return parseInt(p[0], 10) * 60 + parseInt(p[1] || '0', 10);
    }

    function fmtTime(hhmm) {
        var mins = parseHM(hhmm) % 1440;
        var h24 = Math.floor(mins / 60);
        var m = mins % 60;
        var suffix = h24 >= 12 ? 'PM' : 'AM';
        var h12 = h24 % 12 || 12;
        return h12 + (m ? ':' + String(m).padStart(2, '0') : ':00') + ' ' + suffix;
    }

    function formatRange(startHHMM, durationHours) {
        var endMins = (parseHM(startHHMM) + durationHours * 60) % 1440;
        var endHHMM = String(Math.floor(endMins / 60)).padStart(2, '0') + ':' + String(endMins % 60).padStart(2, '0');
        return fmtTime(startHHMM) + ' \u2192 ' + fmtTime(endHHMM);
    }

    function findSlot(t) {
        for (var i = 0; i < state.slots.length; i++) {
            if (state.slots[i].start === t) return state.slots[i];
        }
        return null;
    }

    function initTimeStep() {
        setText('ctxConsole', state.consoleName || '\u2014');
        setText('ctxDate', state.date ? formatDateDisplay(state.date) : '\u2014');

        var timeSelect = document.getElementById('timeSelect');
        if (!timeSelect.dataset.wired) {
            timeSelect.addEventListener('change', function () {
                if (this.value) selectTime(this.value);
            });
            timeSelect.dataset.wired = '1';
        }
        var durSelect = document.getElementById('durationSelect');
        if (!durSelect.dataset.wired) {
            durSelect.addEventListener('change', function () {
                state.duration = parseInt(this.value, 10);
                document.getElementById('hf_duration').value = state.duration;
                updateCost();
                loadAvailability();
            });
            durSelect.dataset.wired = '1';
        }

        loadAvailability();
    }

    /* One request per meaningful change; stale responses discarded by seq. */
    function loadAvailability() {
        if (!state.consoleId || !state.date) return;

        var seq = ++state.availSeq;
        state.availLoading = true;
        state.availError = false;

        clearTimeSelection(true);
        setLoadingUI(true);
        hideError('err-time');

        var url = AVAILABILITY_URL +
            '?console=' + encodeURIComponent(state.consoleId) +
            '&date=' + encodeURIComponent(state.date) +
            '&duration=' + encodeURIComponent(state.duration);

        fetch(url, {
            headers: { 'Accept': 'application/json' },
            credentials: 'same-origin'
        })
            .then(function (resp) {
                if (!resp.ok) throw new Error('HTTP ' + resp.status);
                return resp.json();
            })
            .then(function (data) {
                if (seq !== state.availSeq) return;
                state.slots = data.slots || [];
                state.availLoading = false;
                setLoadingUI(false);
                renderAvailability();
                restoreSelectionIfAvailable();
            })
            .catch(function () {
                if (seq !== state.availSeq) return;
                state.slots = [];
                state.availLoading = false;
                state.availError = true;
                setLoadingUI(false);
                renderAvailability();
                var retry = document.getElementById('availRetry');
                if (retry) retry.hidden = false;
                showError('err-time',
                    'We couldn\u2019t check availability right now. Please check your connection and try again.');
            });
    }

    function retryAvailability() {
        if (!state.availError || !state.consoleId || !state.date) return;
        loadAvailability();
    }

    function setLoadingUI(on) {
        var loading = document.getElementById('availLoading');
        var list = document.getElementById('availList');
        var select = document.getElementById('timeSelect');
        var retry = document.getElementById('availRetry');
        if (loading) loading.hidden = !on;
        if (select) select.disabled = on || state.availError;
        if (retry && on) retry.hidden = true;
        if (on && list) list.innerHTML = '';
    }

    function clearTimeSelection(silent) {
        state.time = null;
        var hf = document.getElementById('hf_time');
        if (hf) hf.value = '';
        var sessionCard = document.getElementById('sessionCard');
        if (sessionCard) sessionCard.hidden = true;
        if (!silent) updateLiveRail();
    }

    function restoreSelectionIfAvailable() {
        var hf = document.getElementById('hf_time');
        if (hf && hf.value) {
            var slot = findSlot(hf.value);
            if (slot && slot.available) {
                selectTime(hf.value, true);
                return;
            }
            hf.value = '';
            state.time = null;
        }
        updateLiveRail();
    }

    function renderAvailability() {
        renderTimeSelect();
        renderAvailList();
        updateSessionCard();

        var free = 0;
        state.slots.forEach(function (s) { if (s.available) free++; });
        var meta = document.getElementById('availMeta');
        if (meta) {
            meta.textContent = state.availError
                ? ''
                : (free === 0
                    ? 'No free start times for this duration'
                    : free + ' of ' + state.slots.length + ' times free');
        }
    }

    function renderTimeSelect() {
        var select = document.getElementById('timeSelect');
        if (!select) return;
        select.innerHTML = '';

        var placeholder = document.createElement('option');
        placeholder.value = '';
        placeholder.textContent = state.availError
            ? 'Unavailable'
            : (state.slots.length ? 'Select a start time' : 'No times available');
        placeholder.disabled = true;
        placeholder.selected = true;
        select.appendChild(placeholder);

        state.slots.forEach(function (slot) {
            var opt = document.createElement('option');
            opt.value = slot.start;
            opt.textContent = fmtTime(slot.start) + (slot.available ? '' : ' \u2014 Unavailable');
            opt.disabled = !slot.available;
            select.appendChild(opt);
        });
    }

    function renderAvailList() {
        var list = document.getElementById('availList');
        if (!list) return;
        list.innerHTML = '';

        if (state.availError) return;

        state.slots.forEach(function (slot) {
            var row = document.createElement('button');
            row.type = 'button';
            row.className = 'wiz-avail-slot' + (slot.available ? '' : ' wiz-avail-slot--busy');
            row.setAttribute('data-time', slot.start);
            row.setAttribute('role', 'radio');
            row.setAttribute('aria-checked', 'false');

            var timeSpan = document.createElement('span');
            timeSpan.className = 'wiz-avail-time';
            timeSpan.textContent = fmtTime(slot.start);

            var stateSpan = document.createElement('span');
            stateSpan.className = 'wiz-avail-state ' +
                (slot.available ? 'wiz-avail-state--free' : 'wiz-avail-state--busy');
            stateSpan.innerHTML = slot.available
                ? '<span class="wiz-status-dot" aria-hidden="true"></span> Available'
                : LOCK_SVG + ' Unavailable';

            row.appendChild(timeSpan);
            row.appendChild(stateSpan);

            if (slot.available) {
                row.setAttribute('aria-label', fmtTime(slot.start) + ', available');
            } else {
                row.disabled = true;
                row.setAttribute('aria-disabled', 'true');
                row.setAttribute('aria-label', fmtTime(slot.start) + ', unavailable');
            }

            row.addEventListener('click', function () {
                if (this.disabled) return;
                selectTime(slot.start);
            });

            list.appendChild(row);
        });
    }

    function selectTime(t, skipFocusSync) {
        state.time = t;

        var hf = document.getElementById('hf_time');
        if (hf) hf.value = t;

        var select = document.getElementById('timeSelect');
        if (select) select.value = t;

        $$('.wiz-avail-slot').forEach(function (row) {
            var isSel = row.getAttribute('data-time') === t;
            row.classList.toggle('wiz-avail-slot--selected', isSel);
            row.setAttribute('aria-checked', isSel ? 'true' : 'false');
        });

        updateSessionCard();
        hideError('err-time');
        updateLiveRail();
    }

    function updateSessionCard() {
        var card = document.getElementById('sessionCard');
        var rangeEl = document.getElementById('sessionRange');
        var statusEl = document.getElementById('sessionStatusText');
        if (!card || !rangeEl || !statusEl) return;

        if (!state.time) { card.hidden = true; return; }

        var slot = findSlot(state.time);
        card.hidden = false;
        rangeEl.textContent = formatRange(state.time, state.duration);

        if (state.availLoading) {
            statusEl.textContent = 'Checking availability\u2026';
            statusEl.className = 'wiz-session-status';
        } else if (slot && slot.available) {
            statusEl.textContent = 'Available';
            statusEl.className = 'wiz-session-status wiz-session-status--ok';
        } else {
            statusEl.textContent = 'Unavailable \u2014 please choose another time.';
            statusEl.className = 'wiz-session-status wiz-session-status--bad';
        }
    }

    /* ==========================================================
       STEP 4 — Players (duration now lives in Step 3)
       ========================================================== */
    function initPlayerButtons() {
        $$('.wiz-player-btn').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var p = parseInt(btn.getAttribute('data-players'), 10);
                state.players = p;

                $$('.wiz-player-btn').forEach(function (b) {
                    b.classList.remove('wiz-player-btn--active');
                    b.setAttribute('aria-checked', 'false');
                });
                btn.classList.add('wiz-player-btn--active');
                btn.setAttribute('aria-checked', 'true');

                var hf = document.getElementById('hf_players');
                if (hf) hf.value = p;

                updateCost();
                hideError('err-players');
            });
        });

        /* Select 1 player by default */
        var btn1 = $('.wiz-player-btn[data-players="1"]');
        if (btn1) btn1.click();
    }

    function updateCost() {
        var isWeekend = false;
        if (state.date) {
            var parts = state.date.split('-');
            var d = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
            isWeekend = (d.getDay() === 0 || d.getDay() === 6);
        }

        var rates = isWeekend ? (window.RATE_WEEKEND || {}) : (window.RATE_WEEKDAY || {});
        var hourly = rates[String(state.players)] || 0;
        var total = hourly * state.duration;
        var advance = Math.round(total * 0.30);
        var balance = total - advance;

        var totalEl = document.getElementById('costTotal');
        var advEl = document.getElementById('costAdvance');
        if (totalEl) totalEl.textContent = '₹' + total;
        if (advEl) advEl.textContent = '₹' + advance;

        /* Store for summary */
        state.hourlyRate = hourly;
        state.totalCost = total;
        state.advanceCost = advance;
        state.balanceCost = balance;

        updateLiveRail();
    }

    /* ==========================================================
       STEP 5 — Summary
       ========================================================== */
    function updateSummary() {
        updateCost();

        setText('sumConsole', state.consoleName || '—');
        setText('sumDate', state.date ? formatDateDisplay(state.date) : '—');
        setText('sumTime', state.time ? formatRange(state.time, state.duration) : '—');
        setText('sumPlayers', state.players + (state.players === 1 ? ' Player' : ' Players'));
        setText('sumDuration', state.duration + (state.duration === 1 ? ' Hour' : ' Hours'));
        setText('sumSubtotal', '₹' + (state.totalCost || 0));
        setText('sumAdvance', '₹' + (state.advanceCost || 0));
        setText('sumBalance', '₹' + (state.balanceCost || 0));

        updateLiveRail();
    }

    /* ==========================================================
       LIVE RAIL — sticky booking summary (Ch10)
       ========================================================== */
    function updateLiveRail() {
        setText('railConsole', state.consoleName || '—');
        setText('railDate', state.date ? formatDateDisplay(state.date) : '—');
        setText('railTime', state.time ? formatRange(state.time, state.duration) : '—');
        setText('railPlayers', state.players + (state.players === 1 ? ' Player' : ' Players'));
        setText('railDuration', state.duration + (state.duration === 1 ? ' Hour' : ' Hours'));
        setText('railSubtotal', '₹' + (state.totalCost || 0));
        setText('railAdvance', '₹' + (state.advanceCost || 0));
        setText('railBalance', '₹' + (state.balanceCost || 0));
    }

    /* ==========================================================
       STEP 6 — Confirm
       ========================================================== */
    function updateConfirm() {
        setText('confirmConsole', state.consoleName || '—');
        setText('confirmDateTime',
            (state.date ? formatDateDisplay(state.date) : '—') +
            ' at ' +
            (state.time ? formatRange(state.time, state.duration) : '—')
        );
        setText('confirmPlayers', state.players + (state.players === 1 ? ' Player' : ' Players'));
        setText('confirmDuration', state.duration + (state.duration === 1 ? ' Hour' : ' Hours'));
        setText('confirmAdvance', '₹' + (state.advanceCost || 0));
    }

    function setText(id, val) {
        var el = document.getElementById(id);
        if (el) el.textContent = val;
    }

    /* ==========================================================
       FORM SUBMISSION
       ========================================================== */
    function initForm() {
        var form = document.getElementById('bookingForm');
        var submitBtn = document.getElementById('submitBtn');
        if (!form || !submitBtn) return;

        form.addEventListener('submit', function (e) {
            /* Validate all required hidden fields */
            var hfConsole = document.getElementById('hf_console');
            var hfDate = document.getElementById('hf_date');
            var hfTime = document.getElementById('hf_time');

            if (!hfConsole || !hfConsole.value) {
                e.preventDefault();
                goToStep(1);
                showError('err-console', 'Please select a console.');
                return;
            }
            if (!hfDate || !hfDate.value) {
                e.preventDefault();
                goToStep(2);
                showError('err-date', 'Please select a date.');
                return;
            }
            if (!hfTime || !hfTime.value) {
                e.preventDefault();
                goToStep(3);
                showError('err-time', 'Please select a start time.');
                return;
            }

            /* Show loading state */
            submitBtn.classList.add('cx-btn--loading');
            submitBtn.disabled = true;
            submitBtn.setAttribute('aria-busy', 'true');
        });
    }

    /* ==========================================================
       INIT
       ========================================================== */
    function init() {
        /* Navigation: next buttons */
        $$('[data-wiz-next]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var targetStep = parseInt(btn.getAttribute('data-wiz-next'), 10);
                if (validateStep(state.step)) {
                    goToStep(targetStep);
                }
            });
        });

        /* Navigation: prev buttons */
        $$('[data-wiz-prev]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var targetStep = parseInt(btn.getAttribute('data-wiz-prev'), 10);
                goToStep(targetStep);
            });
        });

        initConsoleCards();
        initCalendar();
        initPlayerButtons();
        initForm();

        /* Keyboard: arrow keys on availability slots */
        var timeslotGrid = document.getElementById('availList');
        if (timeslotGrid) {
            timeslotGrid.addEventListener('keydown', function (e) {
                if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
                    e.preventDefault();
                    var slots = $$('.wiz-avail-slot:not([aria-disabled="true"])');
                    var idx = slots.indexOf(document.activeElement);
                    if (idx < slots.length - 1) slots[idx + 1].focus();
                } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
                    e.preventDefault();
                    var slots2 = $$('.wiz-avail-slot:not([aria-disabled="true"])');
                    var idx2 = slots2.indexOf(document.activeElement);
                    if (idx2 > 0) slots2[idx2 - 1].focus();
                }
            });
        }

        /* Retry button for availability failures */
        var retryBtn = document.getElementById('availRetry');
        if (retryBtn) {
            retryBtn.addEventListener('click', retryAvailability);
        }

        /* Keyboard: arrow keys on player buttons */
        var playerGrid = document.querySelector('.wiz-player-grid');
        if (playerGrid) {
            playerGrid.addEventListener('keydown', function (e) {
                if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
                    e.preventDefault();
                    var btns = $$('.wiz-player-btn');
                    var idx = btns.indexOf(document.activeElement);
                    if (idx < btns.length - 1) btns[idx + 1].focus();
                } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
                    e.preventDefault();
                    var btns2 = $$('.wiz-player-btn');
                    var idx2 = btns2.indexOf(document.activeElement);
                    if (idx2 > 0) btns2[idx2 - 1].focus();
                }
            });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

}());
