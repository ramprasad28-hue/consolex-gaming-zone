/**
 * CONSOLEX — booking.js (V3 Booking Wizard)
 * 6-step wizard: Console → Date → Time → Players → Summary → Payment
 * No dependencies. Vanilla JS. IIFE-wrapped.
 */
(function () {
    'use strict';

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
        duration: 1
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
        if (stepNum === 3) buildTimeSlots();
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
                if (!state.time) {
                    showError('err-time', 'Please select a start time.');
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
       STEP 3 — Time Slots
       ========================================================== */
    function buildTimeSlots() {
        var grid = $('#timeslotGrid');
        if (!grid) return;
        grid.innerHTML = '';

        /* Determine operating hours based on weekend */
        var isWeekend = false;
        if (state.date) {
            var parts = state.date.split('-');
            var d = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
            var dow = d.getDay();
            isWeekend = (dow === 0 || dow === 6);
        }
        var startHour = isWeekend ? 9 : 10;
        var endHour = 23; /* last slot starts at 22 */

        var now = new Date();
        var todayStr = formatDate(now.getFullYear(), now.getMonth() + 1, now.getDate());
        var isToday = (state.date === todayStr);

        for (var h = startHour; h < endHour; h++) {
            var slotTime = String(h).padStart(2, '0') + ':00';
            var displayTime = formatTime12(h, 0);

            var slot = document.createElement('button');
            slot.type = 'button';
            slot.className = 'wiz-timeslot';
            slot.setAttribute('data-time', slotTime);
            slot.setAttribute('role', 'radio');
            slot.setAttribute('aria-checked', 'false');
            slot.setAttribute('aria-label', displayTime);

            /* Disable past slots if today */
            if (isToday && h <= now.getHours()) {
                slot.classList.add('wiz-timeslot--disabled');
                slot.disabled = true;
                slot.setAttribute('aria-disabled', 'true');
            }

            if (state.time === slotTime) {
                slot.classList.add('wiz-timeslot--selected');
                slot.setAttribute('aria-checked', 'true');
            }

            slot.innerHTML =
                '<span class="wiz-timeslot-time">' + displayTime + '</span>' +
                '<span class="wiz-timeslot-status">Available</span>';

            slot.addEventListener('click', function () {
                var t = this.getAttribute('data-time');
                state.time = t;

                $$('.wiz-timeslot').forEach(function (s) {
                    s.classList.remove('wiz-timeslot--selected');
                    s.setAttribute('aria-checked', 'false');
                });
                this.classList.add('wiz-timeslot--selected');
                this.setAttribute('aria-checked', 'true');

                var hf = document.getElementById('hf_time');
                if (hf) hf.value = t;

                var display = document.getElementById('selectedTimeText');
                if (display) display.textContent = formatTimeDisplay(t);

                hideError('err-time');
                updateLiveRail();
            });

            grid.appendChild(slot);
        }
    }

    function formatTime12(h, m) {
        var suffix = h >= 12 ? 'PM' : 'AM';
        var h12 = h % 12 || 12;
        return h12 + ':00 ' + suffix;
    }

    function formatTimeDisplay(timeStr) {
        var parts = timeStr.split(':');
        var h = parseInt(parts[0], 10);
        var suffix = h >= 12 ? 'PM' : 'AM';
        var h12 = h % 12 || 12;
        var endH = h + state.duration;
        var endSuffix = endH >= 12 ? 'PM' : 'AM';
        var endH12 = endH % 12 || 12;
        if (endH > 23) {
            return h12 + ':00 ' + suffix + ' — Midnight';
        }
        return h12 + ':00 ' + suffix + ' — ' + endH12 + ':00 ' + endSuffix;
    }

    /* ==========================================================
       STEP 4 — Players & Duration
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

        var durSelect = document.getElementById('durationSelect');
        if (durSelect) {
            durSelect.addEventListener('change', function () {
                state.duration = parseInt(this.value, 10);
                var hf = document.getElementById('hf_duration');
                if (hf) hf.value = state.duration;
                updateCost();
            });
        }

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
        setText('sumTime', state.time ? formatTimeDisplay(state.time) : '—');
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
        setText('railTime', state.time ? formatTimeDisplay(state.time) : '—');
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
            (state.time ? formatTime12(parseInt(state.time.split(':')[0], 10), 0) : '—')
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

        /* Keyboard: arrow keys on time slots */
        var timeslotGrid = document.getElementById('timeslotGrid');
        if (timeslotGrid) {
            timeslotGrid.addEventListener('keydown', function (e) {
                if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
                    e.preventDefault();
                    var slots = $$('.wiz-timeslot:not(.wiz-timeslot--disabled)');
                    var idx = slots.indexOf(document.activeElement);
                    if (idx < slots.length - 1) slots[idx + 1].focus();
                } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
                    e.preventDefault();
                    var slots2 = $$('.wiz-timeslot:not(.wiz-timeslot--disabled)');
                    var idx2 = slots2.indexOf(document.activeElement);
                    if (idx2 > 0) slots2[idx2 - 1].focus();
                }
            });
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
