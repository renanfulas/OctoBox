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
  const shellUserId = body.dataset.shellUserId || 'anonymous';
  const celebrationStorageKey = 'octobox-shell-counts:' + shellUserId;

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

  const savedTheme = readStorage(window.localStorage, 'octobox-theme');

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
    burst.className = 'shell-celebration-burst';

    for (let index = 0; index < 14; index += 1) {
      const piece = document.createElement('span');
      piece.className = 'shell-celebration-piece';
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
      toast.classList.add('is-dismissing');
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
      previousCounts = JSON.parse(readStorage(window.sessionStorage, celebrationStorageKey) || 'null');
    } catch (error) {
      previousCounts = null;
    }

    if (previousCounts) {
      celebrateCountDrop('overdue-payments', previousCounts.overduePayments || 0, currentCounts.overduePayments);
      celebrateCountDrop('pending-intakes', previousCounts.pendingIntakes || 0, currentCounts.pendingIntakes);
    }

    writeStorage(window.sessionStorage, celebrationStorageKey, JSON.stringify(currentCounts));
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
    if (!body.classList.contains('sidebar-open')) {
      body.classList.add('sidebar-open');
    }
    syncSidebarUi();
  }

  function closeSidebar() {
    if (body.classList.contains('sidebar-open')) {
      body.classList.remove('sidebar-open');
    }
    syncSidebarUi();
  }

  function resolveLegacyHash(hash) {
    if (body.dataset.shellScope === 'dashboard' && hash === '#dashboard') {
      return '#dashboard-sessions-board';
    }

    return hash;
  }

  function revealHashTarget() {
    var hash = window.location.hash;
    if (!hash || hash === '#') {
      return;
    }

    var resolvedHash = resolveLegacyHash(hash);
    if (resolvedHash !== hash) {
      try {
        window.history.replaceState(null, '', resolvedHash);
      } catch (error) {
        window.location.hash = resolvedHash;
      }
      hash = resolvedHash;
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
    sidebarBackdrop.addEventListener('click', function() {
      closeSidebar();
    });
  }

  // Topbar scroll-to-top (replaces inline onclick from base.html)
  if (topbar) {
    topbar.classList.add('is-shell-scroll-trigger');
    topbar.addEventListener('click', function(event) {
      if (!event.target.closest('a, button, input, form, .topbar-profile')) {
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }
    });
  }

  // Handle blink actions from metric cards (topbar, board, and sidebar targets)
  document.addEventListener('click', function(event) {
    var trigger = event.target.closest('[data-action^="blink-topbar-"], [data-action^="blink-board-"], [data-action^="blink-sidebar-"]');
    if (!trigger) {
      return;
    }

    var action = trigger.getAttribute('data-action') || '';

    // blink-topbar-<kind> -> [data-ui="topbar-<kind>-alert"]
    if (action.indexOf('blink-topbar-') === 0) {
      var kind = action.replace(/^blink-topbar-/, '');
      if (!kind) {
        return;
      }
      var selector = '[data-ui="topbar-' + kind + '-alert"]';
      var target = document.querySelector(selector);
      if (!target) {
        return;
      }
      var neonDuration = 1000;
      target.classList.add('blink');
      window.setTimeout(function() {
        target.classList.remove('blink');
      }, neonDuration + 120);
      return;
    }

    // blink-board-<kind> -> #dashboard-<kind>-board
    if (action.indexOf('blink-board-') === 0) {
      var bkind = action.replace(/^blink-board-/, '');
      if (!bkind) {
        return;
      }

      // Special case: sessions board uses a DOM overlay approach
      // so we never touch the element itself (avoids sticky/layout glitches)
      if (bkind === 'sessions') {
        var sessionsBoard = document.querySelector('#dashboard-sessions-board');
        if (!sessionsBoard) { return; }
        var neonOverlay = document.createElement('div');
        neonOverlay.className = 'sessions-board-neon-overlay';
        neonOverlay.classList.add('is-active');
        sessionsBoard.appendChild(neonOverlay);
        window.setTimeout(function() {
          neonOverlay.remove();
        }, 1400);
        return;
      }
      var bid = '#dashboard-' + bkind + '-board';
      var btarget = document.querySelector(bid);
      if (!btarget) {
        return;
      }

      // Apply neon to the sessions board article itself (avoid wrapper)
      var applyTarget = btarget;
      // single-run blink animation on the board — do not add a persistent outline.
      // Also add a short-lived "neon-quiet" class to suppress other transitions
      // and animations on the board while the blink runs and slightly after it.
      var boardNeonDuration = 1000; // ms (matches CSS keyframes)
      applyTarget.classList.add('neon-blink');
      // mark that *this* handler added the quiet suppression so we don't
      // remove a pre-existing `neon-quiet` that belonged to another actor.
      applyTarget.classList.add('neon-quiet');
      try {
        applyTarget.dataset.neonQuietOwner = 'shell';
      } catch (e) {
        // ignore if dataset isn't writable for some reason
      }
      // keep quiet only a short time after the visual blink to avoid residual effects
      var quietExtra = 80; // ms (short buffer)
      window.setTimeout(function() {
        applyTarget.classList.remove('neon-blink');
      }, boardNeonDuration);
      window.setTimeout(function() {
        try {
          if (applyTarget.dataset && applyTarget.dataset.neonQuietOwner === 'shell') {
            applyTarget.classList.remove('neon-quiet');
            delete applyTarget.dataset.neonQuietOwner;
          }
        } catch (e) {
          applyTarget.classList.remove('neon-quiet');
        }
      }, boardNeonDuration + quietExtra);
      return;
    }

    // blink-sidebar-<kind> -> a[data-nav-key="<kind>"] in the sidebar or nav
    if (action.indexOf('blink-sidebar-') === 0) {
      event.preventDefault();
      
      var sKind = action.replace(/^blink-sidebar-/, '');
      if (!sKind) return;
      
      var sSelector = '[data-nav-key="' + sKind + '"]';
      var targetLink = document.querySelector('.sidebar ' + sSelector) || 
                       document.querySelector(sSelector);

      if (targetLink) {
        var neonDuration = 1000;
        var blinkClass = (sKind === 'financeiro') ? 'blink-danger' : 'blink';
        
        targetLink.classList.add(blinkClass);
        
        // Ensure sidebar is open on mobile if closed
        if (!document.body.classList.contains('sidebar-open') && window.innerWidth <= 1024) {
          document.body.classList.add('sidebar-open');
        }
        
        window.setTimeout(function() {
          targetLink.classList.remove(blinkClass);
        }, neonDuration + 120);
      }
      return;
    }
  });

  // Sidebar neon behavior removed: no-op handler kept for compatibility
  document.addEventListener('click', function() {
    // Intentionally left blank: sidebar neon/blink handled elsewhere no longer.
  });

  // Finance sidebar highlight removed: no-op for click events to avoid errors
  document.addEventListener('click', function() {
    // Intentionally left blank: finance sidebar neon removed.
  });

  revealHashTarget();
  window.addEventListener('hashchange', revealHashTarget);

  document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape' && body.classList.contains('sidebar-open')) {
      closeSidebar();
      syncSidebarUi();
    }
  });
}());
