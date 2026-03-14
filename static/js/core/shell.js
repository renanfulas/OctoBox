/*
ARQUIVO: infraestrutura minima do shell autenticado.

POR QUE ELE EXISTE:
- concentra apenas comportamento universal do shell: tema, sidebar e reveal por hash.
*/

(function () {
    var body = document.body;
    if (!body) {
        return;
    }

    var themeToggle = document.querySelector('[data-ui="theme-toggle"]') || document.getElementById('theme-toggle');
    var sidebarToggle = document.querySelector('[data-ui="sidebar-toggle"]') || document.getElementById('sidebar-toggle');
    var sidebarBackdrop = document.querySelector('[data-ui="sidebar-backdrop"]') || document.getElementById('sidebar-backdrop');
    var savedTheme = localStorage.getItem('octobox-theme');

    function syncThemeUi() {
        if (!themeToggle) {
            return;
        }

        var isDark = body.dataset.theme === 'dark';
        themeToggle.textContent = isDark ? 'Tema claro' : 'Tema escuro';
        themeToggle.setAttribute('aria-pressed', isDark ? 'true' : 'false');
    }

    function syncSidebarUi() {
        if (!sidebarToggle) {
            return;
        }

        sidebarToggle.setAttribute('aria-expanded', body.classList.contains('sidebar-open') ? 'true' : 'false');
    }

    function revealHashTarget() {
        var hash = window.location.hash;
        if (!hash || hash === '#') {
            return;
        }

        var target = null;
        try {
            target = document.querySelector(hash);
        } catch (error) {
            return;
        }

        if (!target) {
            return;
        }

        var parent = target.parentElement;
        while (parent) {
            if (parent.tagName === 'DETAILS') {
                parent.open = true;
            }
            parent = parent.parentElement;
        }

        if (!target.hasAttribute('tabindex')) {
            target.setAttribute('tabindex', '-1');
        }

        window.requestAnimationFrame(function () {
            target.scrollIntoView({ block: 'start', behavior: 'auto' });
            target.focus({ preventScroll: true });
        });
    }

    if (savedTheme === 'dark') {
        body.dataset.theme = 'dark';
    }

    syncThemeUi();
    syncSidebarUi();

    if (themeToggle) {
        themeToggle.addEventListener('click', function () {
            var nextTheme = body.dataset.theme === 'dark' ? 'light' : 'dark';
            body.dataset.theme = nextTheme;
            localStorage.setItem('octobox-theme', nextTheme);
            syncThemeUi();
        });
    }

    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function () {
            body.classList.toggle('sidebar-open');
            syncSidebarUi();
        });
    }

    if (sidebarBackdrop) {
        sidebarBackdrop.addEventListener('click', function () {
            body.classList.remove('sidebar-open');
            syncSidebarUi();
        });
    }

    revealHashTarget();
    window.addEventListener('hashchange', revealHashTarget);

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && body.classList.contains('sidebar-open')) {
            body.classList.remove('sidebar-open');
            syncSidebarUi();
        }
    });
}());