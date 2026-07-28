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

})();
