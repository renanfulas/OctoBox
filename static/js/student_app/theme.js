/*
ARQUIVO: controlador de tema do app do aluno.

POR QUE ELE EXISTE:
- separa o runtime de tema do aluno da logica de PWA e do shell principal.
- garante persistencia, sync de toggle e update de meta theme-color sem acoplar o app ao shell.js inteiro.

O QUE ESTE ARQUIVO FAZ:
1. resolve o tema inicial via localStorage ou preferencia do sistema.
2. sincroniza body[data-theme], color-scheme e meta theme-color.
3. controla o toggle do tema do app do aluno.

PONTOS CRITICOS:
- o contrato oficial do app do aluno e body[data-theme="light|dark"].
- este arquivo nao deve virar controlador de sidebar, perfil ou outras concerns do shell principal.
*/

(function () {
  var body = document.body;
  if (!body || body.dataset.studentApp !== 'true') {
    return;
  }

  var STORAGE_KEY = 'octobox-theme';
  var THEME_COLORS = {
    light: '#f5f7fb',
    dark: '#091221'
  };
  var THEME_ICONS = {
    light: '<circle cx="12" cy="12" r="4"></circle><path d="M12 2v2"></path><path d="M12 20v2"></path><path d="m4.93 4.93 1.41 1.41"></path><path d="m17.66 17.66 1.41 1.41"></path><path d="M2 12h2"></path><path d="M20 12h2"></path><path d="m6.34 17.66-1.41 1.41"></path><path d="m19.07 4.93-1.41 1.41"></path>',
    dark: '<path d="M21 12.79A8.5 8.5 0 1 1 11.21 3 6.6 6.6 0 0 0 21 12.79z"></path>'
  };
  var toggleButtons = document.querySelectorAll('[data-ui="student-theme-toggle"]');
  var themeMeta = document.querySelector('meta[name="theme-color"]');
  var mediaQuery = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;

  function readStorage(key) {
    try {
      return window.localStorage.getItem(key);
    } catch (error) {
      return null;
    }
  }

  function writeStorage(key, value) {
    try {
      window.localStorage.setItem(key, value);
      return true;
    } catch (error) {
      return false;
    }
  }

  function normalizeTheme(theme) {
    return theme === 'dark' ? 'dark' : 'light';
  }

  function resolvePreferredTheme() {
    var storedTheme = readStorage(STORAGE_KEY);
    if (storedTheme === 'dark' || storedTheme === 'light') {
      return storedTheme;
    }
    if (mediaQuery && mediaQuery.matches) {
      return 'dark';
    }
    return 'light';
  }

  function syncThemeUi(theme) {
    toggleButtons.forEach(function (button) {
      var icon = button.querySelector('.theme-toggle-icon');
      var label = button.querySelector('.theme-toggle-label');
      var isDark = theme === 'dark';
      var nextThemeLabel = isDark ? 'tema claro' : 'tema escuro';

      button.setAttribute('data-theme-state', theme);
      button.setAttribute('aria-pressed', isDark ? 'true' : 'false');
      button.setAttribute('aria-label', 'Ativar ' + nextThemeLabel);
      button.setAttribute('title', 'Ativar ' + nextThemeLabel);

      if (icon) {
        icon.innerHTML = THEME_ICONS[theme] || THEME_ICONS.light;
      }

      if (label) {
        label.textContent = isDark ? 'Escuro' : 'Claro';
      }
    });
  }

  function syncThemeColor(theme) {
    if (!themeMeta) {
      return;
    }
    themeMeta.setAttribute('content', THEME_COLORS[theme] || THEME_COLORS.light);
  }

  function applyTheme(theme, options) {
    var normalizedTheme = normalizeTheme(theme);
    var persist = !options || options.persist !== false;

    window.__octoboxStudentTheme = normalizedTheme;
    document.documentElement.style.colorScheme = normalizedTheme;
    body.dataset.theme = normalizedTheme;
    body.style.colorScheme = normalizedTheme;

    syncThemeColor(normalizedTheme);
    syncThemeUi(normalizedTheme);

    if (persist) {
      writeStorage(STORAGE_KEY, normalizedTheme);
    }
  }

  toggleButtons.forEach(function (button) {
    button.addEventListener('click', function () {
      var nextTheme = body.dataset.theme === 'dark' ? 'light' : 'dark';
      applyTheme(nextTheme, { persist: true });
    });
  });

  if (mediaQuery) {
    var handleMediaChange = function (event) {
      var storedTheme = readStorage(STORAGE_KEY);
      if (storedTheme === 'dark' || storedTheme === 'light') {
        return;
      }
      applyTheme(event.matches ? 'dark' : 'light', { persist: false });
    };

    if (typeof mediaQuery.addEventListener === 'function') {
      mediaQuery.addEventListener('change', handleMediaChange);
    } else if (typeof mediaQuery.addListener === 'function') {
      mediaQuery.addListener(handleMediaChange);
    }
  }

  applyTheme(body.dataset.theme || resolvePreferredTheme(), { persist: false });

  window.OctoBoxStudentTheme = {
    getTheme: function () {
      return normalizeTheme(body.dataset.theme);
    },
    setTheme: function (theme) {
      applyTheme(theme, { persist: true });
    }
  };
}());
