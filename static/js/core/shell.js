/*
ARQUIVO: camada essencial do shell autenticado.

POR QUE ELE EXISTE:
- Mantem apenas comportamento indispensavel para operar o shell.
- Deixa interacoes secundarias e efeitos fora do caminho essencial.

O QUE ESTE ARQUIVO FAZ:
1. Sincroniza tema.
2. Controla sidebar.
3. Controla menu de perfil.
4. Mantem Escape e resize basicos de acessibilidade.
*/

(function() {
  var body = document.body;
  if (!body) {
    return;
  }

  var themeToggle = document.querySelector('[data-ui="theme-toggle"]') || document.getElementById('theme-toggle');
  var themeToggleIcon = themeToggle ? themeToggle.querySelector('.theme-toggle-icon') : null;
  var themeToggleLabel = themeToggle ? themeToggle.querySelector('.theme-toggle-label') : null;
  var sidebarToggle = document.querySelector('[data-ui="sidebar-toggle"]') || document.getElementById('sidebar-toggle');
  var sidebarBackdrop = document.querySelector('[data-ui="sidebar-backdrop"]') || document.getElementById('sidebar-backdrop');
  var profileTrigger = document.querySelector('.topbar-profile');
  var profileMenu = document.querySelector('.profile-dropdown');

  function readStorage(storage, key) {
    try {
      return storage.getItem(key);
    } catch (error) {
      return null;
    }
  }

  function writeStorage(storage, key, value) {
    try {
      storage.setItem(key, value);
      return true;
    } catch (error) {
      return false;
    }
  }

  function syncThemeUi() {
    if (!themeToggle) {
      return;
    }

    var isDark = body.dataset.theme === 'dark';
    var themeLabel = isDark ? 'Escuro' : 'Claro';
    var themeIcon = isDark ? '☾' : '☼';
    var nextThemeLabel = isDark ? 'tema claro' : 'tema escuro';

    if (themeToggleIcon) {
      themeToggleIcon.textContent = themeIcon;
    }

    if (themeToggleLabel) {
      themeToggleLabel.textContent = themeLabel;
    }

    themeToggle.setAttribute('data-theme-state', isDark ? 'dark' : 'light');
    themeToggle.setAttribute('aria-pressed', isDark ? 'true' : 'false');
    themeToggle.setAttribute('aria-label', 'Ativar ' + nextThemeLabel);
    themeToggle.setAttribute('title', 'Ativar ' + nextThemeLabel);
  }

  function syncSidebarUi() {
    if (!sidebarToggle) {
      return;
    }

    sidebarToggle.setAttribute('aria-expanded', body.classList.contains('sidebar-open') ? 'true' : 'false');
  }

  function openSidebar() {
    body.classList.add('sidebar-open');
    syncSidebarUi();
  }

  function closeSidebar() {
    body.classList.remove('sidebar-open');
    syncSidebarUi();
  }

  function syncProfileMenuUi(isOpen) {
    if (!profileTrigger || !profileMenu) {
      return;
    }

    profileTrigger.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    profileMenu.classList.toggle('is-open', isOpen);
  }

  function closeProfileMenu() {
    syncProfileMenuUi(false);
  }

  function toggleProfileMenu() {
    if (!profileTrigger || !profileMenu) {
      return;
    }

    syncProfileMenuUi(profileTrigger.getAttribute('aria-expanded') !== 'true');
  }

  if (readStorage(window.localStorage, 'octobox-theme') === 'dark') {
    body.dataset.theme = 'dark';
  }

  syncThemeUi();
  syncSidebarUi();

  if (themeToggle) {
    themeToggle.addEventListener('click', function() {
      var nextTheme = body.dataset.theme === 'dark' ? 'light' : 'dark';
      body.dataset.theme = nextTheme;
      writeStorage(window.localStorage, 'octobox-theme', nextTheme);
      syncThemeUi();
    });
  }

  if (sidebarToggle) {
    sidebarToggle.addEventListener('click', function() {
      if (body.classList.contains('sidebar-open')) {
        closeSidebar();
      } else {
        openSidebar();
      }
    });
  }

  if (sidebarBackdrop) {
    sidebarBackdrop.addEventListener('click', closeSidebar);
  }

  if (profileTrigger && profileMenu) {
    profileTrigger.addEventListener('click', function(event) {
      event.stopPropagation();
      toggleProfileMenu();
    });

    profileMenu.addEventListener('click', function(event) {
      event.stopPropagation();
    });

    document.addEventListener('click', function(event) {
      if (!profileTrigger.contains(event.target) && !profileMenu.contains(event.target)) {
        closeProfileMenu();
      }
    });
  }

  document.addEventListener('keydown', function(event) {
    if (event.key !== 'Escape') {
      return;
    }

    if (body.classList.contains('sidebar-open')) {
      closeSidebar();
    }

    if (profileTrigger && profileTrigger.getAttribute('aria-expanded') === 'true') {
      closeProfileMenu();
      profileTrigger.focus();
    }
  });

  window.addEventListener('resize', function() {
    if (window.innerWidth > 960 && body.classList.contains('sidebar-open')) {
      closeSidebar();
    }
  });
}());
