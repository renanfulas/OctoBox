/*
ARQUIVO: interacoes globais do shell autenticado.

POR QUE ELE EXISTE:
- Isola interacoes secundarias do nucleo essencial do shell.
- Mantem hash reveal e blink actions fora de `shell.js`.
*/

(function() {
  var body = document.body;
  if (!body) {
    return;
  }

  var topbar = document.querySelector('[data-ui="topbar"]');
  var sidebarToggle = document.querySelector('[data-ui="sidebar-toggle"]') || document.getElementById('sidebar-toggle');

  function syncSidebarUi() {
    if (!sidebarToggle) {
      return;
    }

    sidebarToggle.setAttribute('aria-expanded', body.classList.contains('sidebar-open') ? 'true' : 'false');
  }

  function resolveLegacyHash(hash) {
    if (body.dataset.shellScope === 'dashboard' && hash === '#dashboard') {
      return '#dashboard-sessions-board';
    }

    return hash;
  }

  function revealHashTarget() {
    var hash = window.location.hash;
    var resolvedHash;
    var target = null;
    var parent;

    if (!hash || hash === '#') {
      return;
    }

    resolvedHash = resolveLegacyHash(hash);
    if (resolvedHash !== hash) {
      try {
        window.history.replaceState(null, '', resolvedHash);
      } catch (error) {
        window.location.hash = resolvedHash;
      }
      hash = resolvedHash;
    }

    try {
      target = document.querySelector(hash);
    } catch (error) {
      return;
    }

    if (!target) {
      return;
    }

    parent = target.parentElement;
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

  function blinkTopbarTarget(action) {
    var kind = action.replace(/^blink-topbar-/, '');
    var target;
    var neonDuration = 1000;

    if (!kind) {
      return false;
    }

    target = document.querySelector('[data-ui="topbar-' + kind + '-alert"]');
    if (!target) {
      return false;
    }

    target.classList.add('blink');
    window.setTimeout(function() {
      target.classList.remove('blink');
    }, neonDuration + 120);
    return true;
  }

  function blinkBoardTarget(action) {
    var kind = action.replace(/^blink-board-/, '');
    var sessionsBoard;
    var neonOverlay;
    var target;
    var boardNeonDuration = 1000;
    var quietExtra = 80;

    if (!kind) {
      return false;
    }

    if (kind === 'sessions') {
      sessionsBoard = document.querySelector('#dashboard-sessions-board');
      if (!sessionsBoard) {
        return false;
      }

      neonOverlay = document.createElement('div');
      neonOverlay.className = 'sessions-board-neon-overlay';
      neonOverlay.classList.add('is-active');
      sessionsBoard.appendChild(neonOverlay);
      window.setTimeout(function() {
        neonOverlay.remove();
      }, 1400);
      return true;
    }

    target = document.querySelector('#dashboard-' + kind + '-board');
    if (!target) {
      return false;
    }

    target.classList.add('neon-blink');
    target.classList.add('neon-quiet');
    try {
      target.dataset.neonQuietOwner = 'shell';
    } catch (error) {
      // Keep the blink working even if dataset is unavailable.
    }

    window.setTimeout(function() {
      target.classList.remove('neon-blink');
    }, boardNeonDuration);
    window.setTimeout(function() {
      try {
        if (target.dataset && target.dataset.neonQuietOwner === 'shell') {
          target.classList.remove('neon-quiet');
          delete target.dataset.neonQuietOwner;
        }
      } catch (error) {
        target.classList.remove('neon-quiet');
      }
    }, boardNeonDuration + quietExtra);
    return true;
  }

  function blinkSidebarTarget(action, event) {
    var kind = action.replace(/^blink-sidebar-/, '');
    var selector;
    var targetLink;
    var blinkClass;
    var neonDuration = 1000;

    if (!kind) {
      return false;
    }

    if (event) {
      event.preventDefault();
    }

    selector = '[data-nav-key="' + kind + '"]';
    targetLink = document.querySelector('.sidebar ' + selector) || document.querySelector(selector);
    if (!targetLink) {
      return false;
    }

    blinkClass = kind === 'financeiro' ? 'blink-danger' : 'blink';
    targetLink.classList.add(blinkClass);

    if (!body.classList.contains('sidebar-open') && window.innerWidth <= 1024) {
      body.classList.add('sidebar-open');
      syncSidebarUi();
    }

    window.setTimeout(function() {
      targetLink.classList.remove(blinkClass);
    }, neonDuration + 120);
    return true;
  }

  if (topbar) {
    topbar.classList.add('is-shell-scroll-trigger');
    topbar.addEventListener('click', function(event) {
      if (!event.target.closest('a, button, input, form, .topbar-profile')) {
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }
    });
  }

  document.addEventListener('click', function(event) {
    var trigger = event.target.closest('[data-action^="blink-topbar-"], [data-action^="blink-board-"], [data-action^="blink-sidebar-"]');
    var action;

    if (!trigger) {
      return;
    }

    action = trigger.getAttribute('data-action') || '';
    if (action.indexOf('blink-topbar-') === 0) {
      blinkTopbarTarget(action);
      return;
    }

    if (action.indexOf('blink-board-') === 0) {
      blinkBoardTarget(action);
      return;
    }

    if (action.indexOf('blink-sidebar-') === 0) {
      blinkSidebarTarget(action, event);
    }
  });

  revealHashTarget();
  window.addEventListener('hashchange', revealHashTarget);
}());
