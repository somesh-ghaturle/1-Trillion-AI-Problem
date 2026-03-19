/* ============================================
   Trust Control Center - Main JavaScript
   Theme toggle, sidebar, drag-drop, table sort
   ============================================ */

document.addEventListener('DOMContentLoaded', function () {

    // ---- Theme Toggle ----
    const themeToggle = document.getElementById('themeToggle');
    const savedTheme = localStorage.getItem('tcc-theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);

    if (themeToggle) {
        themeToggle.addEventListener('click', function () {
            const current = document.documentElement.getAttribute('data-theme');
            const next = current === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', next);
            localStorage.setItem('tcc-theme', next);
            // Update icon
            const icon = themeToggle.querySelector('.theme-icon');
            if (icon) icon.textContent = next === 'dark' ? '\u{1F319}' : '\u{2600}\u{FE0F}';
        });
    }

    // ---- Mobile Sidebar Toggle ----
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');

    function closeSidebar() {
        if (sidebar) sidebar.classList.remove('open');
        if (overlay) overlay.classList.remove('active');
    }

    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function () {
            sidebar.classList.toggle('open');
            overlay.classList.toggle('active');
        });
    }

    if (overlay) {
        overlay.addEventListener('click', closeSidebar);
    }

    // ---- Drag & Drop File Upload ----
    document.querySelectorAll('.file-upload-area').forEach(function (area) {
        const input = area.querySelector('input[type="file"]');
        const fileNameEl = area.querySelector('.file-name');

        ['dragenter', 'dragover'].forEach(function (evt) {
            area.addEventListener(evt, function (e) {
                e.preventDefault();
                area.classList.add('dragover');
            });
        });

        ['dragleave', 'drop'].forEach(function (evt) {
            area.addEventListener(evt, function (e) {
                e.preventDefault();
                area.classList.remove('dragover');
            });
        });

        area.addEventListener('drop', function (e) {
            if (input && e.dataTransfer.files.length) {
                input.files = e.dataTransfer.files;
                showFileName(e.dataTransfer.files[0].name);
            }
        });

        if (input) {
            input.addEventListener('change', function () {
                if (input.files.length) {
                    showFileName(input.files[0].name);
                }
            });
        }

        function showFileName(name) {
            if (fileNameEl) {
                fileNameEl.textContent = '\u{1F4C4} ' + name;
                fileNameEl.classList.add('active');
            }
        }
    });

    // ---- Sortable Tables ----
    document.querySelectorAll('table[data-sortable]').forEach(function (table) {
        const headers = table.querySelectorAll('th[data-sort]');
        headers.forEach(function (th, index) {
            th.style.cursor = 'pointer';
            th.innerHTML += ' <span class="sort-icon">\u2195</span>';
            th.addEventListener('click', function () {
                sortTable(table, index, th);
            });
        });
    });

    function sortTable(table, colIndex, th) {
        const tbody = table.querySelector('tbody');
        if (!tbody) return;
        const rows = Array.from(tbody.querySelectorAll('tr'));
        const isAsc = th.classList.contains('sorted-asc');

        // Remove sorted state from all
        th.closest('thead').querySelectorAll('th').forEach(function (h) {
            h.classList.remove('sorted', 'sorted-asc', 'sorted-desc');
        });

        rows.sort(function (a, b) {
            const aText = a.cells[colIndex] ? a.cells[colIndex].textContent.trim() : '';
            const bText = b.cells[colIndex] ? b.cells[colIndex].textContent.trim() : '';
            const aNum = parseFloat(aText.replace(/[^0-9.\-]/g, ''));
            const bNum = parseFloat(bText.replace(/[^0-9.\-]/g, ''));
            if (!isNaN(aNum) && !isNaN(bNum)) {
                return isAsc ? bNum - aNum : aNum - bNum;
            }
            return isAsc ? bText.localeCompare(aText) : aText.localeCompare(bText);
        });

        rows.forEach(function (row) { tbody.appendChild(row); });
        th.classList.add('sorted', isAsc ? 'sorted-desc' : 'sorted-asc');
    }

    // ---- Auto-dismiss messages after 5s ----
    document.querySelectorAll('.message').forEach(function (msg) {
        setTimeout(function () {
            msg.style.transition = 'opacity 0.5s, transform 0.5s';
            msg.style.opacity = '0';
            msg.style.transform = 'translateY(-10px)';
            setTimeout(function () { msg.remove(); }, 500);
        }, 5000);
    });

    // ---- Animate stat values on scroll ----
    const observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('.stat-card, .dimension-item, .card').forEach(function (el) {
        observer.observe(el);
    });
});
