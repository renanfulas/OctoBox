/*
ARQUIVO: infraestrutura minima do shell autenticado.

POR QUE ELE EXISTE:
- concentra apenas comportamento universal do shell: tema, sidebar e reveal por hash.
*/

(function() {
  const body = document.body;
  if (!body) {
    return;
  }
  const topbar = document.querySelector('[data-ui="topbar"]');
  const themeToggle = document.querySelector('[data-ui="theme-toggle"]') || document.getElementById('theme-toggle');
  const themeToggleIcon = themeToggle ? themeToggle.querySelector('.theme-toggle-icon') : null;
  const themeToggleLabel = themeToggle ? themeToggle.querySelector('.theme-toggle-label') : null;
  const sidebarToggle = document.querySelector('[data-ui="sidebar-toggle"]') || document.getElementById('sidebar-toggle');
  const sidebarBackdrop = document.querySelector('[data-ui="sidebar-backdrop"]') || document.getElementById('sidebar-backdrop');
  const financeAlert = document.querySelector('[data-ui="topbar-finance-alert"]');
  const intakeAlert = document.querySelector('[data-ui="topbar-intake-alert"]');
  const savedTheme = localStorage.getItem('octobox-theme');
  const shellUserId = body.dataset.shellUserId || 'anonymous';
  const celebrationStorageKey = 'octobox-shell-counts:' + shellUserId;

  function parseCount(element) {
    if (!element) {
      return 0;
    }

    const rawValue = element.getAttribute('data-count-value') || '0';
    const parsedValue = parseInt(rawValue, 10);
    return Number.isFinite(parsedValue) ? parsedValue : 0;
  }

  function ensureCelebrationStack() {
    const existingStack = document.querySelector('[data-ui="shell-celebration-stack"]');
    if (existingStack) {
      return existingStack;
    }

    const stack = document.createElement('div');
    stack.className = 'shell-celebration-stack';
    stack.setAttribute('data-ui', 'shell-celebration-stack');
    document.body.appendChild(stack);
    return stack;
  }

  function emitConfettiBurst(container) {
    const burst = document.createElement('div');
    const colors = ['#10b981', '#34d399', '#f59e0b', '#f97316', '#3b82f6'];
    burst.className = 'shell-celebration-burst';

    for (let index = 0; index < 14; index += 1) {
      const piece = document.createElement('span');
      const direction = index % 2 === 0 ? 1 : -1;
      const distance = 18 + (index * 7);
      const rotation = direction * (40 + index * 12);
      piece.className = 'shell-celebration-piece';
      piece.style.setProperty('--confetti-x', String(direction * distance) + 'px');
      piece.style.setProperty('--confetti-rotate', String(rotation) + 'deg');
      piece.style.setProperty('--confetti-color', colors[index % colors.length]);
      piece.style.left = String(28 + (index % 4) * 18) + 'px';
      piece.style.animationDelay = String(index * 18) + 'ms';
      burst.appendChild(piece);
    }

    container.appendChild(burst);
  }

  function celebrateCountDrop(kind, previousCount, currentCount) {
    if (previousCount <= currentCount) {
      return;
    }

    const stack = ensureCelebrationStack();
    const toast = document.createElement('section');
    const eyebrow = document.createElement('span');
    const copy = document.createElement('span');
    const delta = previousCount - currentCount;
    const messages = {
      'overdue-payments': {
        eyebrow: 'Parabens 🎉',
        copy: delta === 1 ?
          'Um vencimento saiu da pressao. Bom avanço.' :
          delta + ' vencimentos sairam da pressao. Bom avanço.',
      },
      'pending-intakes': {
        eyebrow: 'Boa 👏',
        copy: delta === 1 ?
          'Um intake saiu da fila. Bom avanço.' :
          delta + ' intakes sairam da fila. Bom avanço.',
      },
    };
    const message = messages[kind];

    if (!message) {
      return;
    }

    toast.className = 'shell-celebration-toast';
    eyebrow.className = 'shell-celebration-eyebrow';
    copy.className = 'shell-celebration-copy';
    eyebrow.textContent = message.eyebrow;
    copy.textContent = message.copy;
    toast.appendChild(eyebrow);
    toast.appendChild(copy);
    emitConfettiBurst(toast);
    stack.appendChild(toast);

    window.setTimeout(function() {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(-8px) scale(0.98)';
      toast.style.transition = 'opacity 220ms ease, transform 220ms ease';
      window.setTimeout(function() {
        toast.remove();
      }, 240);
    }, 3200);
  }

  function syncShellCountCelebrations() {
    const currentCounts = {
      overduePayments: parseCount(financeAlert),
      pendingIntakes: parseCount(intakeAlert),
    };
    let previousCounts = null;

    try {
      previousCounts = JSON.parse(sessionStorage.getItem(celebrationStorageKey) || 'null');
    } catch (error) {
      previousCounts = null;
    }

    if (previousCounts) {
      celebrateCountDrop('overdue-payments', previousCounts.overduePayments || 0, currentCounts.overduePayments);
      celebrateCountDrop('pending-intakes', previousCounts.pendingIntakes || 0, currentCounts.pendingIntakes);
    }

    sessionStorage.setItem(celebrationStorageKey, JSON.stringify(currentCounts));
  }

  function shouldIgnoreTopbarScrollClick(target) {
    if (!target) {
      return false;
    }

    return Boolean(target.closest('form, a, button, input, label, select, textarea, summary, [role="button"], [role="link"], [role="option"]'));
  }

  function scrollPageToTop() {
    window.scrollTo({
      top: 0,
      behavior: 'smooth'
    });
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

    window.requestAnimationFrame(function() {
      target.scrollIntoView({
        block: 'start',
        behavior: 'auto'
      });
      target.focus({
        preventScroll: true
      });
    });
  }

  if (savedTheme === 'dark') {
    body.dataset.theme = 'dark';
  }

  syncThemeUi();
  syncSidebarUi();
  syncShellCountCelebrations();

  if (themeToggle) {
    themeToggle.addEventListener('click', function() {
      var nextTheme = body.dataset.theme === 'dark' ? 'light' : 'dark';
      body.dataset.theme = nextTheme;
      localStorage.setItem('octobox-theme', nextTheme);
      syncThemeUi();
    });
  }

  if (sidebarToggle) {
    sidebarToggle.addEventListener('click', function() {
      body.classList.toggle('sidebar-open');
      syncSidebarUi();
    });
  }

  if (sidebarBackdrop) {
    sidebarBackdrop.addEventListener('click', function() {
      body.classList.remove('sidebar-open');
      syncSidebarUi();
    });
  }

  if (topbar) {
    topbar.addEventListener('click', function(event) {
      if (shouldIgnoreTopbarScrollClick(event.target)) {
        return;
      }

      scrollPageToTop();
    });
  }

  revealHashTarget();
  window.addEventListener('hashchange', revealHashTarget);

  document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape' && body.classList.contains('sidebar-open')) {
      body.classList.remove('sidebar-open');
      syncSidebarUi();
    }
  });
}());